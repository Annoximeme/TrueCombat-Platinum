/* In-launcher updater: feed check, verified download, staged apply.

   Feed: update.ini next to the launcher, [Update] Feed=<url>, or the
   PLATINUM_UPDATE_FEED build default. The feed is a small UTF-8 text file:
       version=0.28.0-sandbox19
       package=https://example/TrueCombat-Platinum-0.28.0-sandbox19-Windows-x64.zip
       sha256=<64 hex>
       bytes=<package size>
       notes=<one line shown in the launcher>
   Only https URLs are accepted (plain http only for 127.0.0.1/localhost tests).
   The package must match bytes and sha256 exactly and contain
   "TrueCombat Platinum/manifest.json" with the advertised version.
   Applying copies the staged folder over this installation, keeping
   profile, profile-server, server-state, updates and player.ini.
   WinHTTP is loaded at run time, so no new link library is needed. */
#include <winhttp.h>
#include "platinum_feed.h"   /* signature, fields and https rule shared with setup */
#include <shlobj.h>
#ifndef PLATINUM_UPDATE_FEED
#define PLATINUM_UPDATE_FEED L""
#endif

enum {UPDATE_OFF,UPDATE_IDLE,UPDATE_CHECKING,UPDATE_CURRENT,UPDATE_AVAILABLE,UPDATE_DOWNLOADING,UPDATE_VERIFYING,UPDATE_READY,UPDATE_FAILED};
static volatile LONG updateState=UPDATE_OFF;
static volatile LONG64 updateDone,updateTotal;
static int updateRepair;           /* Verify and repair: re-check the installed release file by file */
static wchar_t updateRepairNote[160]; /* result of the last repair check, for Settings > Updates */
static volatile LONG updateCancel;static wchar_t updateFilesUrl[1024];static char updateFilesSha[65];
static DWORD updateStartTick;
static wchar_t updatePage[512];
static wchar_t updateFeed[1024],updateCurrent[64]=L"",updateLatest[64],updateNotes[200],updatePackage[1024],updateError[200];
static char updateSha[65];
static HWND updateWindow;
static int updatePreview=-1,updateHeadless;
/* ---- HD textures (0.37.1) ----
   The signed feed may name optional files: optional=<prefix>[,<prefix>...] matches the file name (not the
   folder) of .pk3 files in files.txt, e.g. optional=zzz_hd_. The full zip leaves them out; files.txt still
   lists them, so older launchers (which ignore optional=) keep installing them per file.
   Settings > Updates > HD textures ([Launcher] HdTextures, on by default):
     on:  per-file updates include them; after a zip install the launcher fetches the missing ones into the
          staging folder and checks each against the signed list; while the game is current, missing ones are
          downloaded straight into the game folder.
     off: they are skipped and left out of target-files.txt, so the update prunes them; a check also removes
          any that are installed (never while the game runs, which may have them open). */
static wchar_t updateOptional[128];
static LONG64 updateHdBytes;            /* size of the optional files in the release's list; 0 while unknown */
static volatile LONG updateHdOnly;      /* the running download only fetches missing HD texture files: 1 into staging, 2 into the game */
static int updateHdTest;                /* --update-test --hd-check: the per-launch HD check, on this thread */
static int game_running(void);
static int update_hd_on(void){return GetPrivateProfileIntW(L"Launcher",L"HdTextures",1,ini)!=0;}
static int update_optional_path(const wchar_t *path){
    if(!updateOptional[0])return 0;
    const wchar_t *base=path;for(const wchar_t *c=path;*c;++c)if(*c==L'/'||*c==L'\\')base=c+1;
    size_t length=wcslen(base);if(length<5||_wcsicmp(base+length-4,L".pk3"))return 0;
    for(const wchar_t *p=updateOptional;*p;){
        const wchar_t *end=wcschr(p,L',');size_t n=end?(size_t)(end-p):wcslen(p);
        while(n&&*p==L' '){++p;--n;}while(n&&p[n-1]==L' ')--n;
        if(n>=4&&n<length&&!_wcsnicmp(base,p,n))return 1;
        if(!end)break;p=end+1;
    }
    return 0;
}
/* Install layout and version choice.
   launcherDir: folder of the running launcher. root: the game folder (the same,
   unless launcher.ini next to the launcher names another GameFolder).
   updateLatestFeed: the official feed (latest release). A version switch reads
   the signed update.txt of one specific release instead (updateFeed).
   Pinned (update.ini [Update] Pinned=<version>): the player chose to stay on a
   version; newer releases are still shown, but never pushed. */
static wchar_t launcherDir[2048],updateLatestFeed[1024],updatePinned[64],updateTarget[64];
static volatile LONG updateAutoDownload;static int updateSwitching,updateSkipLauncher;
static char *updateTargetList;static DWORD updateTargetListLength;
#define WM_PLATINUM_UPDATE (WM_APP+5)

typedef HINTERNET (WINAPI *UpOpen)(LPCWSTR,DWORD,LPCWSTR,LPCWSTR,DWORD);
typedef HINTERNET (WINAPI *UpConnect)(HINTERNET,LPCWSTR,INTERNET_PORT,DWORD);
typedef HINTERNET (WINAPI *UpRequest)(HINTERNET,LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR*,DWORD);
typedef BOOL (WINAPI *UpSend)(HINTERNET,LPCWSTR,DWORD,LPVOID,DWORD,DWORD,DWORD_PTR);
typedef BOOL (WINAPI *UpReceive)(HINTERNET,LPVOID);
typedef BOOL (WINAPI *UpQuery)(HINTERNET,DWORD,LPCWSTR,LPVOID,LPDWORD,LPDWORD);
typedef BOOL (WINAPI *UpAvailable)(HINTERNET,LPDWORD);
typedef BOOL (WINAPI *UpRead)(HINTERNET,LPVOID,DWORD,LPDWORD);
typedef BOOL (WINAPI *UpClose)(HINTERNET);
typedef BOOL (WINAPI *UpCrack)(LPCWSTR,DWORD,DWORD,LPURL_COMPONENTS);
typedef BOOL (WINAPI *UpTimeouts)(HINTERNET,int,int,int,int);

static void update_notify(void){if(updateWindow)PostMessageW(updateWindow,WM_PLATINUM_UPDATE,0,0);}
/* 2.6.2: every step of an update, repair or launcher self-update goes to updates\launcher-update.log
   (time, step, host, HTTP status, WinHTTP/Win32 error, file). Kept small: at 256 KB it moves to
   launcher-update.1.log and a new one starts. */
static SRWLOCK updateLogLock=SRWLOCK_INIT;
static void update_log(const wchar_t *format,...){
    if(!root[0])return;
    wchar_t path[2400],old[2400];swprintf(path,2400,L"%ls\\updates",root);CreateDirectoryW(path,NULL);
    swprintf(old,2400,L"%ls\\updates\\launcher-update.1.log",root);wcscat(path,L"\\launcher-update.log");
    AcquireSRWLockExclusive(&updateLogLock);
    WIN32_FILE_ATTRIBUTE_DATA info;
    if(GetFileAttributesExW(path,GetFileExInfoStandard,&info)&&(info.nFileSizeHigh||info.nFileSizeLow>256*1024))MoveFileExW(path,old,MOVEFILE_REPLACE_EXISTING);
    FILE *file=_wfopen(path,L"a, ccs=UTF-8");
    if(file){
        SYSTEMTIME now;GetLocalTime(&now);
        fwprintf(file,L"%04d-%02d-%02d %02d:%02d:%02d [%ls] ",now.wYear,now.wMonth,now.wDay,now.wHour,now.wMinute,now.wSecond,PLATINUM_LAUNCHER_VERSION);
        va_list args;va_start(args,format);vfwprintf(file,format,args);va_end(args);fputwc(L'\n',file);fclose(file);
    }
    ReleaseSRWLockExclusive(&updateLogLock);
}
/* 2.6.2: the last network failure of any request (quiet ones too), so a per-file failure can name the host */
static wchar_t updateNetHost[128];static DWORD updateNetCode,updateNetStatus;
static void update_fail(const wchar_t *message){wcsncpy(updateError,message,199);updateError[199]=0;update_log(L"FAILED: %ls",updateError);InterlockedExchange(&updateState,UPDATE_FAILED);update_notify();}
/* 2.6.2: what went wrong with a game file, so a failure can name it even after the fall-back to the zip. */
static wchar_t updateFileProblem[200];
static const wchar_t *update_base_name(const wchar_t *path){const wchar_t *name=path;for(const wchar_t *c=path;*c;++c)if(*c==L'\\'||*c==L'/')name=c+1;return name;}
static int update_av_error(DWORD code){return code==ERROR_ACCESS_DENIED||code==225||code==226||code==ERROR_FILE_NOT_FOUND||code==ERROR_PATH_NOT_FOUND;}
/* code 0: the file was written and then vanished (an on-access scan removed it). */
static void update_file_problem(const wchar_t *path,DWORD code){
    const wchar_t *name=update_base_name(path);
    if(!code||update_av_error(code))swprintf(updateFileProblem,200,L"Your antivirus blocked %ls. Add the TrueCombat Platinum folder as an exception, then click Try again.",name);
    else if(code==ERROR_SHARING_VIOLATION||code==ERROR_LOCK_VIOLATION)swprintf(updateFileProblem,200,L"%ls is in use by another program (often an antivirus scan). Close it, then click Try again.",name);
    else if(code==ERROR_DISK_FULL||code==ERROR_HANDLE_DISK_FULL)swprintf(updateFileProblem,200,L"The drive is full while writing %ls. Free some space, then click Try again.",name);
    else swprintf(updateFileProblem,200,L"%ls could not be written (Windows error %lu). Click Try again.",name,code);
    updateFileProblem[199]=0;
    update_log(L"file problem: %ls (error %lu%ls)",path,code,code?L"":L", removed after it was written");
}

static void update_read_current(void){
    wchar_t path[2300];swprintf(path,2300,L"%ls\\manifest.json",root);
    FILE *file=_wfopen(path,L"rb");if(!file)return;
    char text[4096]={0};size_t n=fread(text,1,sizeof(text)-1,file);fclose(file);text[n]=0;
    char *key=strstr(text,"\"version\"");if(!key)return;
    char *quote=strchr(key+9,'"');if(!quote)return;
    char *end=strchr(quote+1,'"');if(!end||end-quote-1>=63)return;
    *end=0;MultiByteToWideChar(CP_UTF8,0,quote+1,-1,updateCurrent,64);
}
static void update_load_config(void){
    update_read_current();
    wchar_t ini_path[2300];swprintf(ini_path,2300,L"%ls\\update.ini",root);
    if(!updateFeed[0])GetPrivateProfileStringW(L"Update",L"Feed",PLATINUM_UPDATE_FEED,updateFeed,1024,ini_path);
    wcscpy(updateLatestFeed,updateFeed);
    GetPrivateProfileStringW(L"Update",L"Pinned",L"",updatePinned,64,ini_path);
    InterlockedExchange(&updateState,updateFeed[0]?UPDATE_IDLE:UPDATE_OFF);
    if(updatePreview>=0){
        /* Developer screenshots of each state (--update-preview N); sample text only. */
        wcscpy(updateLatest,L"0.29.0-sandbox20");wcscpy(updateNotes,L"Sample update notes");wcscpy(updatePage,L"https://example.invalid/");
        InterlockedExchange64(&updateTotal,812LL*1048576);InterlockedExchange64(&updateDone,503LL*1048576);
        wcscpy(updateError,L"Could not reach the update server. Check your internet connection.");
    }
}
/* Numeric comparison of "a.b.c-sandboxN" style versions; returns >0 when a is newer. */
static int update_compare(const wchar_t *a,const wchar_t *b){
    long va[4]={0},vb[4]={0};const wchar_t *p[2]={a,b};long *v[2]={va,vb};
    for(int k=0;k<2;++k){
        const wchar_t *s=p[k];int i=0;
        while(*s&&i<3){if(*s>=L'0'&&*s<=L'9'){v[k][i++]=wcstol(s,(wchar_t**)&s,10);}else ++s;if(*s==L'-'||*s==L' ')break;}
        const wchar_t *tail=wcsstr(p[k],L"sandbox");if(tail)v[k][3]=wcstol(tail+7,NULL,10);
    }
    for(int i=0;i<4;++i)if(va[i]!=vb[i])return va[i]>vb[i]?1:-1;
    return 0;
}
static int update_url_ok(const wchar_t *url){return platinum_feed_url_ok(url);}
typedef int (*UpdateSink)(void *context,const void *data,DWORD size);
/* Streams a URL into sink. Returns 0 on success, otherwise writes updateError. */
#define UPDATE_HTTP_FAIL(message) do{if(report)update_fail(message);}while(0)
static int update_http_ex(const wchar_t *url,UpdateSink sink,void *context,LONG64 limit,int report){
    if(!update_url_ok(url)){UPDATE_HTTP_FAIL(L"The update address must use https.");return 1;}
    HMODULE module=LoadLibraryW(L"winhttp.dll");if(!module){UPDATE_HTTP_FAIL(L"Windows networking (WinHTTP) is not available.");return 1;}
    UpOpen open=(UpOpen)(void*)GetProcAddress(module,"WinHttpOpen");UpConnect connect_=(UpConnect)(void*)GetProcAddress(module,"WinHttpConnect");
    UpRequest request=(UpRequest)(void*)GetProcAddress(module,"WinHttpOpenRequest");UpSend send_=(UpSend)(void*)GetProcAddress(module,"WinHttpSendRequest");
    UpReceive receive=(UpReceive)(void*)GetProcAddress(module,"WinHttpReceiveResponse");UpQuery query=(UpQuery)(void*)GetProcAddress(module,"WinHttpQueryHeaders");
    UpAvailable available=(UpAvailable)(void*)GetProcAddress(module,"WinHttpQueryDataAvailable");UpRead read=(UpRead)(void*)GetProcAddress(module,"WinHttpReadData");
    UpClose close_=(UpClose)(void*)GetProcAddress(module,"WinHttpCloseHandle");UpCrack crack=(UpCrack)(void*)GetProcAddress(module,"WinHttpCrackUrl");
    UpTimeouts timeouts=(UpTimeouts)(void*)GetProcAddress(module,"WinHttpSetTimeouts");
    if(!open||!connect_||!request||!send_||!receive||!query||!available||!read||!close_||!crack||!timeouts){FreeLibrary(module);UPDATE_HTTP_FAIL(L"Windows networking (WinHTTP) is incomplete.");return 1;}
    wchar_t host[256],path[2048];URL_COMPONENTS parts;memset(&parts,0,sizeof(parts));parts.dwStructSize=sizeof(parts);
    parts.lpszHostName=host;parts.dwHostNameLength=256;parts.lpszUrlPath=path;parts.dwUrlPathLength=2048;
    wchar_t extra[1024];parts.lpszExtraInfo=extra;parts.dwExtraInfoLength=1024;
    int result=1;
    if(!crack(url,0,0,&parts)){FreeLibrary(module);UPDATE_HTTP_FAIL(L"The update address is not valid.");return 1;}
    if(parts.dwExtraInfoLength&&wcslen(path)+wcslen(extra)<2047)wcscat(path,extra);
    HINTERNET session=open(L"TrueCombatPlatinumLauncher/1.0",WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0);
    HINTERNET connection=NULL,handle=NULL;
    if(session){timeouts(session,10000,10000,15000,30000);connection=connect_(session,host,parts.nPort,0);}
    if(connection)handle=request(connection,L"GET",path,NULL,WINHTTP_NO_REFERER,WINHTTP_DEFAULT_ACCEPT_TYPES,parts.nScheme==INTERNET_SCHEME_HTTPS?WINHTTP_FLAG_SECURE:0);
    DWORD netError=0,httpStatus=0;LONG64 received=0;
    if(handle&&send_(handle,WINHTTP_NO_ADDITIONAL_HEADERS,0,WINHTTP_NO_REQUEST_DATA,0,0,0)&&receive(handle,NULL)){
        DWORD status=0,size=sizeof(status);
        query(handle,WINHTTP_QUERY_STATUS_CODE|WINHTTP_QUERY_FLAG_NUMBER,WINHTTP_HEADER_NAME_BY_INDEX,&status,&size,WINHTTP_NO_HEADER_INDEX);
        httpStatus=status;
        if(status!=200){wcsncpy(updateNetHost,host,127);updateNetHost[127]=0;updateNetStatus=status;updateNetCode=0;wchar_t message[120];swprintf(message,120,tr(L"The update server answered with HTTP %lu."),status);UPDATE_HTTP_FAIL(message);}
        else{
            static char buffer[65536];LONG64 total=0;int ok=1;DWORD began=GetTickCount();
            for(;;){
                DWORD ready=0;if(!available(handle,&ready)){ok=0;netError=GetLastError();break;}
                if(!ready)break;
                while(ready){
                    DWORD chunk=ready>sizeof(buffer)?sizeof(buffer):ready,got=0;
                    if(!read(handle,buffer,chunk,&got)||!got){ok=0;netError=GetLastError();break;}
                    total+=got;ready-=got;received=total;
                    /* Option: download speed limit (per connection). */
                    if(optionSpeeds[options.speed]&&total>262144){LONG64 allowed=(LONG64)optionSpeeds[options.speed]*1048576;
                        while(!updateCancel&&total*1000>allowed*(LONG64)(GetTickCount()-began+50))Sleep(15);}
                    if(limit&&total>limit){ok=0;break;}
                    if(!sink(context,buffer,got)){ok=0;break;}
                }
                if(!ok)break;
            }
            if(ok)result=0;else if(!updateCancel&&InterlockedCompareExchange(&updateState,0,0)!=UPDATE_FAILED)UPDATE_HTTP_FAIL(L"The download was interrupted or too large.");
        }
    }else{netError=GetLastError();wcsncpy(updateNetHost,host,127);updateNetHost[127]=0;updateNetStatus=0;updateNetCode=netError;
        /* 2.6.2: name the server, so a blocked download host (web shield, firewall) is told apart from no internet */
        wchar_t message[200];swprintf(message,200,tr(L"Could not reach %ls (error %lu). Check your connection, or allow it in your antivirus web shield or firewall."),host,netError);
        UPDATE_HTTP_FAIL(message);}
    update_log(L"GET https://%ls%.100ls -> %ls%lu, %lld bytes%ls",host,path,httpStatus?L"HTTP ":L"no answer, error ",httpStatus?httpStatus:netError,(long long)received,
               httpStatus&&netError?L", stopped by a network error":L"");
    if(handle)close_(handle);if(connection)close_(connection);if(session)close_(session);
    FreeLibrary(module);return result;
}
static int update_http(const wchar_t *url,UpdateSink sink,void *context,LONG64 limit){return update_http_ex(url,sink,context,limit,1);}
static int update_http_quiet(const wchar_t *url,UpdateSink sink,void *context,LONG64 limit){return update_http_ex(url,sink,context,limit,0);}
typedef struct {char text[16384];DWORD length;} UpdateText;
static int update_text_sink(void *context,const void *data,DWORD size){
    UpdateText *text=(UpdateText*)context;if(text->length+size>=sizeof(text->text))return 0;
    memcpy(text->text+text->length,data,size);text->length+=size;text->text[text->length]=0;return 1;
}
static void update_field(const char *text,const char *key,wchar_t *out,int capacity){platinum_feed_field(text,key,out,capacity);}
/* Feed signature: last line "signature=<r||s hex>" (ECDSA P-256, SHA-256) over every byte before it (platinum_feed.h). */
static int update_verify_signature(const char *text,DWORD length){return platinum_feed_signature_ok(text,length);}
/* ---- Launcher self-update ----
   The launcher has its own version (platinum_launcher_version.h). The signed
   latest feed may name a newer launcher:
       launcher_version=1.1.0
       launcher=<https url of TrueCombatPlatinum-Launcher.exe>
       launcher_sha256=<64 hex>
       launcher_bytes=<size>
   When it does, game updates leave TrueCombatPlatinum.exe alone and only this
   path replaces it: the new EXE is downloaded next to the running one, checked
   (size, SHA-256 and its embedded version marker), then swapped in. Windows
   lets a running EXE be renamed, so the old one becomes <exe>.old and is
   removed on the next start. Only the official latest feed is used, never the
   feed of an older release picked in Versions. */
enum {LAUNCHER_NONE,LAUNCHER_DOWNLOADING,LAUNCHER_READY,LAUNCHER_FAILED,LAUNCHER_CURRENT,LAUNCHER_CHECKING};
static volatile LONG launcherUpdateState;
static wchar_t launcherLatest[32],launcherUrl[1024],launcherError[200];
static char launcherSha[65];static LONG64 launcherBytes;
static int launcherFeedManaged,launcherJustUpdated;
/* Set by the launcher-update button: its result is reported once, and its fields came from the latest feed. */
static volatile LONG launcherManualCheck,launcherFromLatest;
static void update_read_launcher_fields(const char *text){
    wchar_t version[40],url[1024],sha[80],bytes[32];
    update_field(text,"launcher_version",version,40);update_field(text,"launcher",url,1024);
    update_field(text,"launcher_sha256",sha,80);update_field(text,"launcher_bytes",bytes,32);
    int hex=wcslen(sha)==64;for(int i=0;i<64&&hex;++i)hex=iswxdigit(sha[i]);
    LONG64 size=_wtoi64(bytes);
    int ok=version[0]>=L'0'&&version[0]<=L'9'&&wcslen(version)<32&&!wcspbrk(version,L"/\\?#% ")&&update_url_ok(url)&&hex&&size>0&&size<(LONG64)64*1048576;
    launcherFeedManaged=ok;if(!ok)return;
    wcscpy(launcherLatest,version);wcscpy(launcherUrl,url);launcherBytes=size;
    for(int i=0;i<64;++i)launcherSha[i]=(char)towlower(sha[i]);launcherSha[64]=0;
}
static int launcher_update_offered(void){
    return launcherFeedManaged&&(launcherFromLatest||!wcscmp(updateFeed,updateLatestFeed))&&update_compare(launcherLatest,PLATINUM_LAUNCHER_VERSION)>0;
}
static DWORD WINAPI launcher_update_worker(LPVOID unused);
static void update_start(DWORD (WINAPI *worker)(LPVOID));
static void launcher_update_begin(void){
    if(!launcher_update_offered())return;
    LONG from=InterlockedCompareExchange(&launcherUpdateState,0,0);
    if(from!=LAUNCHER_NONE&&from!=LAUNCHER_FAILED&&from!=LAUNCHER_CURRENT)return;
    if(InterlockedCompareExchange(&launcherUpdateState,LAUNCHER_DOWNLOADING,from)!=from)return;
    update_notify();update_start(launcher_update_worker);
}
static int update_prepare_delta(void);static LONG64 deltaBytes,updateFullBytes;static int deltaReady,deltaCount;
static void update_hd_check(void);
static DWORD WINAPI update_download_worker(LPVOID unused);
/* 2.6.2: the launcher's own update never waits on the game's: it is offered after every feed that was read,
   also when the game update then failed. */
static void update_offer_launcher(void){
    if(updateHeadless)return;
    if(launcher_update_offered()){if(options.autoLauncher)launcher_update_begin();}
    else if(launcherFeedManaged&&InterlockedCompareExchange(&launcherUpdateState,0,0)==LAUNCHER_NONE)InterlockedExchange(&launcherUpdateState,LAUNCHER_CURRENT);
}
static int updateAutoRepairTried,updateAutoRepairWanted,updateForceRepair;
static int update_quick_missing(void);static int update_repair_begin(void);static int game_missing(void);
static DWORD WINAPI update_check_worker(LPVOID unused){
    (void)unused;
    static UpdateText text;text.length=0;text.text[0]=0;
    if(update_http(updateFeed,update_text_sink,&text,16000))return 1;
    if(!update_verify_signature(text.text,text.length)){update_fail(L"The update information is not signed by Team Terminus, so it was ignored.");return 1;}
    wchar_t bytes[32],sha[80];
    update_field(text.text,"version",updateLatest,64);update_field(text.text,"package",updatePackage,1024);
    update_field(text.text,"sha256",sha,80);update_field(text.text,"bytes",bytes,32);update_field(text.text,"notes",updateNotes,200);update_field(text.text,"page",updatePage,512);
    {wchar_t master[256];update_field(text.text,"master",master,256);
     if(master[0]&&wcslen(master)<200&&!wcspbrk(master,L" \"\\;"))WritePrivateProfileStringW(L"Master",L"Address",master,ini);}
    {wchar_t discord[40];update_field(text.text,"discord",discord,40);int digits=discord[0]!=0;for(wchar_t *c=discord;*c;++c)if(*c<L'0'||*c>L'9')digits=0;
     if(digits)WritePrivateProfileStringW(L"Discord",L"ClientId",discord,ini);}
    if(updatePage[0]&&_wcsnicmp(updatePage,L"https://",8))updatePage[0]=0;
    update_field(text.text,"optional",updateOptional,128);
    for(wchar_t *c=updateOptional;*c;++c)if(!(iswalnum(*c)||*c==L'_'||*c==L'-'||*c==L'.'||*c==L','||*c==L' ')||(*c==L'.'&&c[1]==L'.')){updateOptional[0]=0;break;}
    if(!InterlockedCompareExchange(&launcherManualCheck,0,0)){InterlockedExchange(&launcherFromLatest,0);update_read_launcher_fields(text.text);}
    int hex=wcslen(sha)==64;for(int i=0;i<64&&hex;++i)hex=iswxdigit(sha[i]);
    LONG64 size=_wtoi64(bytes);
    {wchar_t files[1024],filesSha[80];update_field(text.text,"files",files,1024);update_field(text.text,"files_sha256",filesSha,80);
     updateFilesUrl[0]=0;if(files[0]&&wcslen(filesSha)==64){wcscpy(updateFilesUrl,files);for(int i=0;i<64;++i)updateFilesSha[i]=(char)towlower(filesSha[i]);updateFilesSha[64]=0;}}
    /* The full zip (package=, sha256=, bytes=) is optional when the feed lists every file (files=): releases are
       moving to per-file installs only. Launchers before this one still require package=, so a release keeps one
       until those are gone. Without a package there is no whole-zip fallback: a failed file download is retried. */
    int hasPackage=update_url_ok(updatePackage)&&hex&&size>0;
    if(!updateLatest[0]||(!hasPackage&&!updateFilesUrl[0])){update_fail(L"The update information is incomplete.");update_offer_launcher();return 1;}
    InterlockedExchange64(&updateDone,0);
    if(hasPackage){for(int i=0;i<64;++i)updateSha[i]=(char)towlower(sha[i]);updateSha[64]=0;InterlockedExchange64(&updateTotal,size);updateFullBytes=size;}
    else{updatePackage[0]=0;updateSha[0]=0;InterlockedExchange64(&updateTotal,0);updateFullBytes=0;}
    if(updateSwitching&&wcscmp(updateLatest,updateTarget)){update_fail(L"That release did not describe the version you picked, so nothing was changed.");update_offer_launcher();return 1;}
    int newer=!updateCurrent[0]||update_compare(updateLatest,updateCurrent)>0;
    if(updateSwitching)newer=!updateCurrent[0]||wcscmp(updateLatest,updateCurrent)!=0;
    /* Only a move to the latest release replaces the launcher itself: an older
       launcher would not offer the way back. */
    updateSkipLauncher=updateSwitching&&updateFeed[0]&&wcscmp(updateFeed,updateLatestFeed)!=0&&updateCurrent[0];
    /* A feed that versions the launcher separately updates it on its own path. */
    if(launcherFeedManaged||updateRepair)updateSkipLauncher=1;   /* a repair never swaps the launcher itself */
    if(updateRepair){
        /* Verify and repair: hash every installed file against the release's signed list;
           only what is missing or damaged is downloaded. No list: reinstall the full package. */
        int damaged=update_prepare_delta();
        if(damaged){newer=1;InterlockedExchange64(&updateTotal,deltaBytes);
            swprintf(updateRepairNote,160,tr(L"%d damaged or missing file%ls found, downloading"),deltaCount,deltaCount==1?L"":L"s");}
        else if(updateTargetList){newer=0;wcscpy(updateRepairNote,L"Every game file checked out");}
        else{newer=1;wcscpy(updateRepairNote,L"Game files reinstalled from the full package");}
        if(!newer){updateRepair=0;updateSwitching=0;InterlockedExchange(&updateAutoDownload,0);wcscpy(updateFeed,updateLatestFeed);}
    }
    else if(newer&&update_prepare_delta())InterlockedExchange64(&updateTotal,deltaBytes);
    update_log(L"check: installed %ls, release %ls -> %ls",updateCurrent[0]?updateCurrent:L"none",updateLatest,newer?(updateRepair?L"repair needed":L"update available"):L"current");
    InterlockedExchange(&updateState,newer?UPDATE_AVAILABLE:UPDATE_CURRENT);
    update_notify();
    /* 2.6.2: without the engine the game cannot start at all, so the newer version is fetched right away */
    if(newer&&!updateRepair&&!updateSwitching&&!updateHeadless&&updateCurrent[0]&&game_missing())InterlockedExchange(&updateAutoDownload,1);
    /* Option: fetch game updates without asking, unless the player chose to stay on a version. */
    int automatic=options.autoGame&&!updateHeadless&&!updateSwitching&&updateCurrent[0]&&!(updatePinned[0]&&!wcscmp(updatePinned,updateCurrent));
    if(newer&&(InterlockedExchange(&updateAutoDownload,0)||automatic))update_start(update_download_worker);
    else InterlockedExchange(&updateAutoDownload,0);
    /* HD textures: on a current game, fetch what is missing or remove what was turned off. */
    if(!newer&&!updateSwitching&&!updateRepair&&updateCurrent[0]&&!updateAutoRepairTried&&(updateForceRepair||game_missing()||update_quick_missing())){
        /* 2.6.2: missing or damaged files on a current game: repair them (once per start) */
        updateAutoRepairTried=1;updateForceRepair=0;update_log(L"startup check: repairing the installation");
        if(updateHeadless)updateAutoRepairWanted=1;else if(update_repair_begin()){update_offer_launcher();return 0;}
    }
    if(!newer&&!updateSwitching&&!updateRepair&&updateCurrent[0]&&updateOptional[0]&&updateFilesUrl[0])update_hd_check();
    update_offer_launcher();
    return 0;
}
typedef struct {HANDLE file;BCRYPT_HASH_HANDLE hash;} UpdateDownload;
static DWORD updateWriteError;   /* 2.6.2: why the last write of a downloaded file failed */
static int update_file_sink(void *context,const void *data,DWORD size){
    UpdateDownload *download=(UpdateDownload*)context;DWORD written=0;
    if(updateCancel)return 0;
    if(!WriteFile(download->file,data,size,&written,NULL)||written!=size){updateWriteError=GetLastError();if(!updateWriteError)updateWriteError=ERROR_WRITE_FAULT;return 0;}
    if(BCryptHashData(download->hash,(PUCHAR)data,size,0))return 0;
    LONG64 done=InterlockedAdd64(&updateDone,size);
    static DWORD lastNotify;if(GetTickCount()-lastNotify>120||done==updateTotal){lastNotify=GetTickCount();update_notify();}
    return 1;
}
static int update_run_hidden(wchar_t *command){
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);si.dwFlags=STARTF_USESHOWWINDOW;si.wShowWindow=SW_HIDE;
    if(!CreateProcessW(NULL,command,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,root,&si,&pi))return -1;
    WaitForSingleObject(pi.hProcess,600000);DWORD code=1;GetExitCodeProcess(pi.hProcess,&code);
    CloseHandle(pi.hThread);CloseHandle(pi.hProcess);return (int)code;
}
static void update_remove_tree(const wchar_t *folder){
    /* SHFileOperation needs a double-NUL terminated path. */
    wchar_t from[2400]={0};wcsncpy(from,folder,2390);
    SHFILEOPSTRUCTW op={0};op.wFunc=FO_DELETE;op.pFrom=from;op.fFlags=FOF_NO_UI;SHFileOperationW(&op);
}
static void update_store_target_list(void);
/* Older releases have no files.txt: describe the unpacked package instead,
   in the same "<sha> <bytes> <asset> <path>" shape (only the path is used). */
static void update_list_tree(const wchar_t *base,const wchar_t *relative,char **text,DWORD *length,DWORD *capacity){
    wchar_t pattern[2600];swprintf(pattern,2600,L"%ls\\%ls%ls*",base,relative,relative[0]?L"\\":L"");
    WIN32_FIND_DATAW item;HANDLE find=FindFirstFileW(pattern,&item);if(find==INVALID_HANDLE_VALUE)return;
    do{
        if(!wcscmp(item.cFileName,L".")||!wcscmp(item.cFileName,L".."))continue;
        wchar_t child[1200];swprintf(child,1200,L"%ls%ls%ls",relative,relative[0]?L"\\":L"",item.cFileName);
        if(item.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY){update_list_tree(base,child,text,length,capacity);continue;}
        char path[1200];WideCharToMultiByte(CP_UTF8,0,child,-1,path,1200,NULL,NULL);for(char *c=path;*c;++c)if(*c=='\\')*c='/';
        char line[1400];int n=snprintf(line,1400,"%064d 0 package %s\n",0,path);
        if(n<=0||*length+n+1>*capacity){char *grown=(char*)realloc(*text,*capacity*2+n+1);if(!grown)continue;*text=grown;*capacity=*capacity*2+n+1;}
        memcpy(*text+*length,line,n);*length+=n;(*text)[*length]=0;
    }while(FindNextFileW(find,&item));
    FindClose(find);
}
typedef int (*UpdateKeepFn)(void *context,const wchar_t *path);
static DWORD update_filter_list(char *list,DWORD length,UpdateKeepFn keep,void *context);
static int update_hd_collect(const char *list,DWORD length,const wchar_t *staging,int verify);
static int update_download_files(const wchar_t *folder,int direct);
static int update_keep_staged_optional(void *context,const wchar_t *path);
static DWORD WINAPI update_download_full(void){
    if(!updatePackage[0]){update_fail(L"Some game files could not be downloaded. Check your connection and try again.");return 1;}
    wchar_t folder[2300],part[2400],zip[2400],staging[2400],command[5200],manifest[2600],exe[2600];
    swprintf(folder,2300,L"%ls\\updates",root);CreateDirectoryW(folder,NULL);
    swprintf(part,2400,L"%ls\\package.zip.part",folder);swprintf(zip,2400,L"%ls\\package.zip",folder);swprintf(staging,2400,L"%ls\\staging",folder);
    BCRYPT_ALG_HANDLE algorithm=NULL;UpdateDownload download={INVALID_HANDLE_VALUE,NULL};
    if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0)||BCryptCreateHash(algorithm,&download.hash,NULL,0,NULL,0,0)){
        if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);update_fail(L"Windows could not start the file check.");return 1;}
    download.file=CreateFileW(part,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(download.file==INVALID_HANDLE_VALUE){DWORD code=GetLastError();BCryptDestroyHash(download.hash);BCryptCloseAlgorithmProvider(algorithm,0);
        update_file_problem(part,code);update_fail(updateFileProblem);return 1;}
    update_log(L"full package: %ls (%lld bytes)",updatePackage,(long long)updateTotal);
    updateWriteError=0;
    InterlockedExchange64(&updateDone,0);InterlockedExchange(&updateCancel,0);updateStartTick=GetTickCount();
    InterlockedExchange(&updateState,UPDATE_DOWNLOADING);update_notify();
    int failed=update_http(updatePackage,update_file_sink,&download,updateTotal+1);
    CloseHandle(download.file);
    unsigned char digest[32];char hex[65];
    BCryptFinishHash(download.hash,digest,32,0);BCryptDestroyHash(download.hash);BCryptCloseAlgorithmProvider(algorithm,0);
    for(int i=0;i<32;++i)sprintf(hex+i*2,"%02x",digest[i]);
    if(failed){DeleteFileW(part);
        if(updateCancel){InterlockedExchange(&updateCancel,0);InterlockedExchange(&updateState,UPDATE_AVAILABLE);update_notify();}
        else if(updateWriteError){update_file_problem(part,updateWriteError);update_fail(updateFileProblem);}
        return 1;}
    InterlockedExchange(&updateState,UPDATE_VERIFYING);update_notify();
    if(updateDone!=updateTotal||strcmp(hex,updateSha)){DeleteFileW(part);update_fail(L"The download did not pass the file check and was removed.");return 1;}
    DeleteFileW(zip);
    if(!MoveFileW(part,zip)){DWORD code=GetLastError();int vanished=GetFileAttributesW(part)==INVALID_FILE_ATTRIBUTES;
        update_file_problem(L"package.zip",vanished?0:code);update_fail(updateFileProblem);return 1;}
    update_remove_tree(staging);CreateDirectoryW(staging,NULL);
    wchar_t system[MAX_PATH];GetSystemDirectoryW(system,MAX_PATH);
    swprintf(command,5200,L"\"%ls\\tar.exe\" -xf \"%ls\" -C \"%ls\"",system,zip,staging);
    {int code=update_run_hidden(command);
     if(code!=0){
        wchar_t message[200];
        if(GetFileAttributesW(zip)==INVALID_FILE_ATTRIBUTES){update_file_problem(L"package.zip",0);wcscpy(message,updateFileProblem);}
        else swprintf(message,200,tr(L"The update could not be unpacked (tar %d). If your antivirus reported a file, add the TrueCombat Platinum folder as an exception, then click Try again."),code);
        update_fail(message);return 1;}}
    swprintf(manifest,2600,L"%ls\\TrueCombat Platinum\\manifest.json",staging);swprintf(exe,2600,L"%ls\\TrueCombat Platinum\\TrueCombatPlatinum.exe",staging);
    FILE *file=_wfopen(manifest,L"rb");char text[4096]={0};
    if(file){size_t n=fread(text,1,sizeof(text)-1,file);text[n]=0;fclose(file);}
    char version[64];WideCharToMultiByte(CP_UTF8,0,updateLatest,-1,version,64,NULL,NULL);
    char needle[100];snprintf(needle,100,"\"version\": \"%s\"",version);
    if(!file||!strstr(text,needle)||GetFileAttributesW(exe)==INVALID_FILE_ATTRIBUTES){update_fail(L"The update package is not a TrueCombat: Platinum release.");return 1;}
    if(updateSkipLauncher)DeleteFileW(exe);
    /* HD textures: the zip leaves the optional files out; fetch the ones not already in place. */
    if(updateTargetList&&updateOptional[0]&&update_hd_on()){
        wchar_t unpacked[2600];swprintf(unpacked,2600,L"%ls\\TrueCombat Platinum",staging);
        if(update_hd_collect(updateTargetList,updateTargetListLength,unpacked,1)>0){
            InterlockedExchange(&updateHdOnly,1);int result=update_download_files(unpacked,0);InterlockedExchange(&updateHdOnly,0);
            if(result<0){InterlockedExchange(&updateCancel,0);InterlockedExchange(&updateState,UPDATE_AVAILABLE);update_notify();return 1;}
            if(!result){updateTargetListLength=update_filter_list(updateTargetList,updateTargetListLength,update_keep_staged_optional,unpacked);update_store_target_list();}
            InterlockedExchange(&updateState,UPDATE_VERIFYING);update_notify();
        }
        deltaCount=0;deltaBytes=0;
    }
    if(!updateTargetList){
        wchar_t unpacked[2600];swprintf(unpacked,2600,L"%ls\\TrueCombat Platinum",staging);
        DWORD length=0,capacity=65536;char *text=(char*)malloc(capacity);
        if(text){text[0]=0;update_list_tree(unpacked,L"",&text,&length,&capacity);updateTargetList=text;updateTargetListLength=length;}
        update_store_target_list();
    }
    InterlockedExchange(&updateState,UPDATE_READY);update_notify();return 0;
}
/* ---- Per-file updates ----
   The signed feed may list files=<url of files.txt> and files_sha256=<hex>.
   files.txt lines: "<sha256> <bytes> <asset name> <relative path>". The launcher
   hashes the installed files, downloads only those that differ into
   updates\staging, checks each one, and applies them with the normal updater.
   Any problem falls back to the full package. */
#define DELTA_MAX 600
typedef struct {wchar_t path[260],asset[200];char sha[65];LONG64 bytes;} DeltaFile;
static DeltaFile *deltaFiles;

static int update_hash_file(const wchar_t *path,char *hex){
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,FILE_FLAG_SEQUENTIAL_SCAN,NULL);
    if(file==INVALID_HANDLE_VALUE)return 0;
    BCRYPT_ALG_HANDLE algorithm=NULL;BCRYPT_HASH_HANDLE hash=NULL;int ok=0;
    if(!BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0)&&!BCryptCreateHash(algorithm,&hash,NULL,0,NULL,0,0)){
        static unsigned char buffer[1<<20];DWORD got=0;ok=1;
        while(ReadFile(file,buffer,sizeof(buffer),&got,NULL)&&got){if(BCryptHashData(hash,buffer,got,0)){ok=0;break;}}
        unsigned char digest[32];if(ok&&!BCryptFinishHash(hash,digest,32,0)){for(int i=0;i<32;++i)sprintf(hex+i*2,"%02x",digest[i]);}else ok=0;
    }
    if(hash)BCryptDestroyHash(hash);if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);CloseHandle(file);return ok;
}
static int update_keep(const wchar_t *relative);
static int update_delta_path_ok(const wchar_t *path){
    if(!path[0]||path[0]==L'\\'||path[0]==L'/'||wcschr(path,L':')||wcsstr(path,L".."))return 0;
    wchar_t relative[260];wcsncpy(relative,path,259);relative[259]=0;for(wchar_t *c=relative;*c;++c)if(*c==L'/')*c=L'\\';
    return !update_keep(relative);
}
typedef struct {char *text;DWORD length,capacity;} DeltaBuffer;
static int update_delta_sink(void *context,const void *data,DWORD size){
    DeltaBuffer *b=(DeltaBuffer*)context;if(b->length+size+1>b->capacity)return 0;memcpy(b->text+b->length,data,size);b->length+=size;b->text[b->length]=0;return 1;
}
/* Fetches the release's files.txt named by the signed feed and checks it against files_sha256. */
static int update_fetch_list(char *text,DWORD capacity,DWORD *length){
    *length=0;text[0]=0;
    if(!updateFilesUrl[0]||!update_url_ok(updateFilesUrl))return 0;
    DeltaBuffer buffer={text,0,capacity};
    if(update_http_quiet(updateFilesUrl,update_delta_sink,&buffer,capacity-1))return 0;
    BCRYPT_ALG_HANDLE a=NULL;BCRYPT_HASH_HANDLE h=NULL;unsigned char d[32];char hex[65];int ok=0;
    if(!BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,NULL,0)&&!BCryptCreateHash(a,&h,NULL,0,NULL,0,0)&&
       !BCryptHashData(h,(PUCHAR)text,buffer.length,0)&&!BCryptFinishHash(h,d,32,0)){for(int i=0;i<32;++i)sprintf(hex+i*2,"%02x",d[i]);ok=!strcmp(hex,updateFilesSha);}
    if(h)BCryptDestroyHash(h);if(a)BCryptCloseAlgorithmProvider(a,0);
    if(ok)*length=buffer.length;
    return ok;
}
/* Calls fn for every well-formed "<sha> <bytes> <asset> <path>" line of a files list (the list is not changed).
   fn returns 0 to stop. */
typedef int (*UpdateEntryFn)(void *context,const char *sha,LONG64 bytes,const wchar_t *asset,const wchar_t *path);
static void update_each_entry(const char *list,DWORD length,UpdateEntryFn fn,void *context){
    const char *line=list,*stop=list+length;
    while(line<stop&&*line){
        const char *end=(const char*)memchr(line,'\n',(size_t)(stop-line));size_t n=end?(size_t)(end-line):(size_t)(stop-line);
        char one[800];
        if(n<sizeof(one)){
            memcpy(one,line,n);one[n]=0;
            char sha[65]={0},asset[200]={0},path[260]={0};long long bytes=0;
            if(sscanf(one,"%64s %lld %199s %259[^\r\n]",sha,&bytes,asset,path)==4&&strlen(sha)==64&&bytes>=0){
                wchar_t wideAsset[200],widePath[260];
                MultiByteToWideChar(CP_UTF8,0,asset,-1,wideAsset,200);MultiByteToWideChar(CP_UTF8,0,path,-1,widePath,260);
                for(int i=0;i<64;++i)sha[i]=(char)tolower((unsigned char)sha[i]);
                if(!fn(context,sha,bytes,wideAsset,widePath))return;
            }
        }
        if(!end)break;line=end+1;
    }
}
/* Keeps the lines of a files list for which keep() says yes (lines that are not entries are kept). */
static DWORD update_filter_list(char *list,DWORD length,UpdateKeepFn keep,void *context){
    DWORD out=0;const char *line=list,*stop=list+length;
    while(line<stop&&*line){
        const char *end=(const char*)memchr(line,'\n',(size_t)(stop-line));size_t n=end?(size_t)(end-line+1):(size_t)(stop-line);
        int kept=1;char one[800];
        if(n<sizeof(one)){
            memcpy(one,line,n);one[n]=0;
            char sha[65],asset[200],path[260];long long bytes;
            if(sscanf(one,"%64s %lld %199s %259[^\r\n]",sha,&bytes,asset,path)==4){
                wchar_t widePath[260];MultiByteToWideChar(CP_UTF8,0,path,-1,widePath,260);kept=keep(context,widePath);}
        }
        if(kept){memmove(list+out,line,n);out+=(DWORD)n;}
        line+=n;
    }
    list[out]=0;return out;
}
static int update_keep_not_optional(void *context,const wchar_t *path){(void)context;return !update_optional_path(path);}
static int update_entry_sum_optional(void *context,const char *sha,LONG64 bytes,const wchar_t *asset,const wchar_t *path){
    (void)sha;(void)asset;if(update_optional_path(path))*(LONG64*)context+=bytes;return 1;
}
static int update_file_size(const wchar_t *path,LONG64 *size){
    WIN32_FILE_ATTRIBUTE_DATA info;if(!GetFileAttributesExW(path,GetFileExInfoStandard,&info))return 0;
    *size=((LONG64)info.nFileSizeHigh<<32)|info.nFileSizeLow;return 1;
}
static void update_local_path(wchar_t *out,const wchar_t *base,const wchar_t *relative){
    swprintf(out,2600,L"%ls\\%ls",base,relative);for(wchar_t *c=out;*c;++c)if(*c==L'/')*c=L'\\';
}
/* Called by the check worker once an update is known: builds the changed-file list. */
static int update_prepare_delta(void){
    deltaReady=0;deltaCount=0;deltaBytes=0;free(updateTargetList);updateTargetList=NULL;updateTargetListLength=0;
    static char text[262144];DWORD length=0;
    if(!update_fetch_list(text,sizeof(text),&length))return 0;
    {LONG64 hd=0;update_each_entry(text,length,update_entry_sum_optional,&hd);updateHdBytes=hd;}
    /* HD textures off: the optional files are neither downloaded nor part of the version being installed,
       so the apply step prunes any installed copies. */
    if(updateOptional[0]&&!update_hd_on())length=update_filter_list(text,length,update_keep_not_optional,NULL);
    free(updateTargetList);updateTargetList=(char*)malloc(length+1);
    if(updateTargetList){memcpy(updateTargetList,text,length+1);updateTargetListLength=length;}
    if(!deltaFiles)deltaFiles=(DeltaFile*)calloc(DELTA_MAX,sizeof(DeltaFile));if(!deltaFiles)return 0;
    for(char *line=text;line&&*line;){
        char *end=strchr(line,'\n');if(end)*end=0;
        char sha[65]={0},asset[200]={0},path[260]={0};long long bytes=0;
        if(sscanf(line,"%64s %lld %199s %259[^\r\n]",sha,&bytes,asset,path)==4&&strlen(sha)==64&&bytes>=0){
            if(deltaCount>=DELTA_MAX)return 0;
            DeltaFile *f=&deltaFiles[deltaCount];memset(f,0,sizeof(*f));
            MultiByteToWideChar(CP_UTF8,0,path,-1,f->path,260);MultiByteToWideChar(CP_UTF8,0,asset,-1,f->asset,200);
            for(int i=0;i<64;++i)f->sha[i]=(char)tolower((unsigned char)sha[i]);f->bytes=bytes;
            if(!update_delta_path_ok(f->path)||wcspbrk(f->asset,L"/\\?#%"))return 0;
            if(updateSkipLauncher&&!_wcsicmp(f->path,L"TrueCombatPlatinum.exe"))goto next_line;
            wchar_t local[2600];update_local_path(local,root,f->path);
            LONG64 size=0;char hex[65]={0};
            int same=update_file_size(local,&size)&&size==bytes&&update_hash_file(local,hex)&&!strcmp(hex,f->sha);
            if(!same){deltaBytes+=bytes;++deltaCount;if(updateRepair||deltaCount<=40)update_log(L"%ls: %ls",updateRepair?L"repair: missing or damaged":L"changed",f->path);}
        }
        next_line:
        line=end?end+1:NULL;
    }
    deltaReady=deltaCount>0;return deltaReady;
}
/* Downloads deltaFiles[0..deltaCount) under folder, each checked against its sha. direct: the files go
   straight into place (folder is the game folder) through a .part copy, so nothing half-written is ever
   seen by the game. Returns 1 when all arrived, 0 on a failure, -1 when cancelled. */
static int update_download_files(const wchar_t *folder,int direct){
    wchar_t base[1024];wcscpy(base,updateFilesUrl);wchar_t *slash=wcsrchr(base,L'/');if(!slash)return 0;slash[1]=0;
    InterlockedExchange64(&updateDone,0);InterlockedExchange64(&updateTotal,deltaBytes);InterlockedExchange(&updateCancel,0);updateStartTick=GetTickCount();
    InterlockedExchange(&updateState,UPDATE_DOWNLOADING);update_notify();
    for(int i=0;i<deltaCount;++i){
        DeltaFile *f=&deltaFiles[i];
        wchar_t target[2600],part[2700],parent[2600],url[1400];update_local_path(target,folder,f->path);
        swprintf(part,2700,direct?L"%ls.part":L"%ls",target);
        wcscpy(parent,target);wchar_t *cut=wcsrchr(parent,L'\\');if(cut){*cut=0;SHCreateDirectoryExW(NULL,parent,NULL);}
        swprintf(url,1400,L"%ls%ls",base,f->asset);
        /* 2.6.2: three tries per file (network hiccups, a scan holding the file), and the reason is kept */
        int done=0;LONG64 start=updateDone;
        for(int attempt=0;attempt<3&&!done;++attempt){
            if(attempt){if(updateCancel)return -1;update_log(L"retry %d: %ls",attempt,f->path);Sleep(attempt==1?1000:3000);}
            InterlockedExchange64(&updateDone,start);
            BCRYPT_ALG_HANDLE algorithm=NULL;UpdateDownload download={INVALID_HANDLE_VALUE,NULL};
            if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0)||BCryptCreateHash(algorithm,&download.hash,NULL,0,NULL,0,0)){if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);return 0;}
            download.file=CreateFileW(part,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
            if(download.file==INVALID_HANDLE_VALUE){DWORD code=GetLastError();BCryptDestroyHash(download.hash);BCryptCloseAlgorithmProvider(algorithm,0);update_file_problem(f->path,code);continue;}
            updateWriteError=0;
            updateNetHost[0]=0;updateNetCode=0;updateNetStatus=0;
            int failed=update_http_quiet(url,update_file_sink,&download,f->bytes+1);
            CloseHandle(download.file);
            unsigned char digest[32];char hex[65];BCryptFinishHash(download.hash,digest,32,0);BCryptDestroyHash(download.hash);BCryptCloseAlgorithmProvider(algorithm,0);
            for(int k=0;k<32;++k)sprintf(hex+k*2,"%02x",digest[k]);
            if(updateCancel){DeleteFileW(part);return -1;}
            if(failed||updateDone-start!=f->bytes||strcmp(hex,f->sha)){
                if(updateWriteError)update_file_problem(f->path,updateWriteError);
                else if(!failed){swprintf(updateFileProblem,200,tr(L"%ls did not pass the file check. Click Try again."),update_base_name(f->path));update_log(L"sha mismatch: %ls",f->path);}
                else{
                    if(updateNetStatus)swprintf(updateFileProblem,200,tr(L"Could not download %ls: %ls answered HTTP %lu. Click Try again later."),update_base_name(f->path),updateNetHost,updateNetStatus);
                    else if(updateNetCode)swprintf(updateFileProblem,200,tr(L"Could not download %ls from %ls (error %lu). Check your connection, or allow it in your antivirus web shield or firewall."),update_base_name(f->path),updateNetHost,updateNetCode);
                    else swprintf(updateFileProblem,200,tr(L"%ls could not be downloaded. Check your connection, then click Try again."),update_base_name(f->path));
                    update_log(L"download failed: %ls",f->path);}
                DeleteFileW(part);continue;}
            /* an on-access scan can remove the file the moment it is closed */
            if(GetFileAttributesW(part)==INVALID_FILE_ATTRIBUTES){update_file_problem(f->path,0);continue;}
            if(direct&&!MoveFileExW(part,target,MOVEFILE_REPLACE_EXISTING)){DWORD code=GetLastError();update_file_problem(f->path,code);DeleteFileW(part);continue;}
            done=1;
        }
        if(!done)return 0;
    }
    return 1;
}
/* 2.6.2: a previous attempt can leave updates\\staging and package.zip(.part) behind (an interrupted download,
   an antivirus that removed a staged file, a failed apply). They are never reused: every attempt and every start
   clears them. Returns 0 and says which item stayed when Windows refused (report: as the update's failure). */
static int update_clear_staging(int report){
    static const wchar_t *items[]={L"staging",L"package.zip",L"package.zip.part"};int ok=1;
    for(unsigned i=0;i<sizeof(items)/sizeof(items[0]);++i){
        wchar_t path[2400];swprintf(path,2400,L"%ls\\updates\\%ls",root,items[i]);
        DWORD attributes=GetFileAttributesW(path);if(attributes==INVALID_FILE_ATTRIBUTES)continue;
        if(attributes&FILE_ATTRIBUTE_DIRECTORY)update_remove_tree(path);else{SetFileAttributesW(path,FILE_ATTRIBUTE_NORMAL);DeleteFileW(path);}
        if(GetFileAttributesW(path)==INVALID_FILE_ATTRIBUTES){update_log(L"cleared leftover updates\\%ls",items[i]);continue;}
        update_log(L"could not clear updates\\%ls (error %lu)",items[i],GetLastError());ok=0;
        if(report){wchar_t message[200];swprintf(message,200,tr(L"Old update files in updates\\%ls could not be removed. Close the game and any program using them (or delete the folder), then click Try again."),items[i]);update_fail(message);return 0;}
    }
    return ok;
}
static int update_download_delta(void){
    wchar_t staging[2400];swprintf(staging,2400,L"%ls\\updates\\staging",root);update_remove_tree(staging);
    wcscat(staging,L"\\TrueCombat Platinum");SHCreateDirectoryExW(NULL,staging,NULL);
    return update_download_files(staging,0);
}
/* HD textures: the optional files of the list that are not in place. staging (may be NULL): a file there
   counts as in place. verify: hash the installed copy too (after a zip install); otherwise its size is
   enough (the per-launch check, which must stay cheap). */
typedef struct {const wchar_t *staging;int verify,overflow;} UpdateHdScan;
static int update_entry_hd_missing(void *context,const char *sha,LONG64 bytes,const wchar_t *asset,const wchar_t *path){
    UpdateHdScan *scan=(UpdateHdScan*)context;
    if(!update_optional_path(path)||!update_delta_path_ok(path)||wcspbrk(asset,L"/\\?#%"))return 1;
    wchar_t local[2600];LONG64 size=0;char hex[65]={0};
    if(scan->staging){update_local_path(local,scan->staging,path);if(update_file_size(local,&size)&&size==bytes)return 1;}
    update_local_path(local,root,path);
    int present=update_file_size(local,&size);
    if(present&&size==bytes&&(!scan->verify||(update_hash_file(local,hex)&&!strcmp(hex,sha))))return 1;
    if(present&&!scan->staging&&game_running())return 1;
    if(deltaCount>=DELTA_MAX){scan->overflow=1;return 0;}
    DeltaFile *f=&deltaFiles[deltaCount++];memset(f,0,sizeof(*f));
    wcsncpy(f->path,path,259);wcsncpy(f->asset,asset,199);memcpy(f->sha,sha,64);f->sha[64]=0;f->bytes=bytes;deltaBytes+=bytes;
    return 1;
}
static int update_hd_collect(const char *list,DWORD length,const wchar_t *staging,int verify){
    deltaReady=0;deltaCount=0;deltaBytes=0;
    if(!updateOptional[0]||!list)return 0;
    if(!deltaFiles)deltaFiles=(DeltaFile*)calloc(DELTA_MAX,sizeof(DeltaFile));if(!deltaFiles)return 0;
    UpdateHdScan scan={staging,verify,0};update_each_entry(list,length,update_entry_hd_missing,&scan);
    if(scan.overflow){deltaCount=0;deltaBytes=0;}
    return deltaCount;
}
/* HD textures off: remove installed optional files (the game may hold them open, so never while it runs). */
static int update_entry_hd_remove(void *context,const char *sha,LONG64 bytes,const wchar_t *asset,const wchar_t *path){
    (void)sha;(void)bytes;(void)asset;
    if(!update_optional_path(path)||!update_delta_path_ok(path))return 1;
    wchar_t local[2600];update_local_path(local,root,path);
    if(GetFileAttributesW(local)!=INVALID_FILE_ATTRIBUTES&&DeleteFileW(local))++*(int*)context;
    return 1;
}
static int update_hd_remove(const char *list,DWORD length){
    int removed=0;if(updateOptional[0]&&list&&!game_running())update_each_entry(list,length,update_entry_hd_remove,&removed);return removed;
}
/* After a zip install with a failed HD download: leave the missing optional files out of the version being
   installed, so a stale copy from the previous version is pruned instead of kept. */
static int update_keep_staged_optional(void *context,const wchar_t *path){
    if(!update_optional_path(path))return 1;
    for(int i=0;i<deltaCount;++i)if(!_wcsicmp(deltaFiles[i].path,path)){
        wchar_t local[2600];update_local_path(local,(const wchar_t*)context,path);return GetFileAttributesW(local)!=INVALID_FILE_ATTRIBUTES;}
    return 1;
}
/* HD textures while the installed game is current (called by the check worker): download the missing optional
   files straight into the game folder, or remove them when the player turned HD textures off. */
static char updateHdList[262144];static DWORD updateHdListLength;
static int update_space_ok(void);
static DWORD WINAPI update_hd_worker(LPVOID unused){
    (void)unused;
    InterlockedExchange64(&updateTotal,deltaBytes);deltaReady=1;
    int result=update_space_ok()?update_download_files(root,1):0;
    if(InterlockedCompareExchange(&updateState,0,0)==UPDATE_FAILED){InterlockedExchange(&updateHdOnly,0);deltaReady=0;deltaCount=0;return 1;}
    InterlockedExchange(&updateHdOnly,0);deltaReady=0;deltaCount=0;deltaBytes=0;InterlockedExchange64(&updateTotal,0);
    if(!result){if(updateFileProblem[0])update_fail(updateFileProblem);else update_fail(L"HD textures could not be downloaded. Check your connection and try again.");return 1;}
    InterlockedExchange(&updateCancel,0);
    if(!update_hd_on())update_hd_remove(updateHdList,updateHdListLength);   /* turned off while downloading */
    InterlockedExchange(&updateState,UPDATE_CURRENT);update_notify();return 0;
}
static void update_hd_check(void){
    if(!update_fetch_list(updateHdList,sizeof(updateHdList),&updateHdListLength))return;
    {LONG64 hd=0;update_each_entry(updateHdList,updateHdListLength,update_entry_sum_optional,&hd);updateHdBytes=hd;}
    if(!update_hd_on()){update_hd_remove(updateHdList,updateHdListLength);update_notify();return;}
    if((updateHeadless&&!updateHdTest)||updatePreview>=0)return;
    if(update_hd_collect(updateHdList,updateHdListLength,NULL,0)>0){InterlockedExchange(&updateHdOnly,2);if(updateHdTest)update_hd_worker(NULL);else update_start(update_hd_worker);}
    update_notify();
}
/* 2.6.2: a current game with files missing or of the wrong size (an antivirus quarantined the engine, a pak went
   missing) is repaired on its own instead of leaving PLAY on a dead INSTALL. Cheap: sizes only, from the release's
   signed list; the repair then hashes everything. HD files are left to the HD check. */
static wchar_t updateMissingFile[260];
static int update_entry_quick(void *context,const char *sha,LONG64 bytes,const wchar_t *asset,const wchar_t *path){
    (void)sha;(void)asset;
    /* the source archive is not in the zip; the game runs without it (a manual repair still fetches it) */
    if(update_optional_path(path)||!update_delta_path_ok(path)||!_wcsicmp(path,L"TrueCombatPlatinum.exe")||!_wcsnicmp(path,L"source/",7))return 1;
    wchar_t local[2600];LONG64 size=0;update_local_path(local,root,path);
    if(update_file_size(local,&size)&&size==bytes)return 1;
    wcsncpy(updateMissingFile,path,259);updateMissingFile[259]=0;++*(int*)context;return 1;
}
static int update_quick_missing(void){
    static char list[262144];DWORD length=0;updateMissingFile[0]=0;
    if(!update_fetch_list(list,sizeof(list),&length))return 0;
    int missing=0;update_each_entry(list,length,update_entry_quick,&missing);
    if(missing)update_log(L"startup check: %d game file(s) missing or the wrong size, e.g. %ls",missing,updateMissingFile);
    return missing;
}
/* Settings > Updates > HD textures was switched: look again, so the files follow the choice right away. */
static void update_begin_check(void);
static void update_hd_toggled(int on){
    LONG state=InterlockedCompareExchange(&updateState,0,0);
    if(updatePreview>=0)return;
    if(!on&&state==UPDATE_DOWNLOADING&&InterlockedCompareExchange(&updateHdOnly,0,0)==2){InterlockedExchange(&updateCancel,1);return;}
    if(state==UPDATE_CURRENT||state==UPDATE_FAILED||state==UPDATE_IDLE||(state==UPDATE_AVAILABLE&&!updateSwitching))update_begin_check();
}
/* ---- Managed file lists ----
   updates\installed-files.txt holds the files.txt of the version on disk and
   updates\target-files.txt the one being installed. After a successful apply,
   files the old version shipped and the new one does not are removed, so moving
   between versions never leaves a newer pak behind (pure servers would refuse
   it). Files the player added (maps, mods) are never on either list. */
static void update_list_path(wchar_t *out,const wchar_t *base,const wchar_t *name){swprintf(out,2400,L"%ls\\updates\\%ls",base,name);}
static int update_write_bytes(const wchar_t *path,const char *data,DWORD length){
    HANDLE file=CreateFileW(path,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);if(file==INVALID_HANDLE_VALUE)return 0;
    DWORD written=0;int ok=WriteFile(file,data,length,&written,NULL)&&written==length;CloseHandle(file);return ok;
}
static int update_sha_matches(const char *data,DWORD length,const char *expected){
    BCRYPT_ALG_HANDLE a=NULL;BCRYPT_HASH_HANDLE h=NULL;unsigned char d[32];char hex[65];int ok=0;
    if(!BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,NULL,0)&&!BCryptCreateHash(a,&h,NULL,0,NULL,0,0)&&
       !BCryptHashData(h,(PUCHAR)data,length,0)&&!BCryptFinishHash(h,d,32,0)){for(int i=0;i<32;++i)sprintf(hex+i*2,"%02x",d[i]);ok=!strcmp(hex,expected);}
    if(h)BCryptDestroyHash(h);if(a)BCryptCloseAlgorithmProvider(a,0);return ok;
}
/* https://github.com/<owner>/<repo>/releases/latest/download/update.txt
   -> .../releases/download/v<version>/update.txt. Fails for any other feed. */
static int update_tag_feed(const wchar_t *version,wchar_t *out,int capacity){
    const wchar_t *marker=wcsstr(updateLatestFeed,L"/releases/latest/download/");
    if(!marker||!version[0]||wcspbrk(version,L"/\\?#% "))return 0;
    int prefix=(int)(marker-updateLatestFeed);
    if(prefix+wcslen(version)+64>=(size_t)capacity)return 0;
    swprintf(out,capacity,L"%.*ls/releases/download/v%ls/%ls",prefix,updateLatestFeed,version,marker+wcslen(L"/releases/latest/download/"));
    return 1;
}
/* Best effort: record which files the installed version shipped, from its own signed release. */
static void update_record_installed(void){
    wchar_t path[2400];update_list_path(path,root,L"installed-files.txt");
    if(!updateCurrent[0]||GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES)return;
    wchar_t feed[1024];if(!update_tag_feed(updateCurrent,feed,1024))return;
    static UpdateText text;text.length=0;text.text[0]=0;
    if(update_http_quiet(feed,update_text_sink,&text,16000)||!update_verify_signature(text.text,text.length))return;
    wchar_t version[64],files[1024],sha[80];char shaA[65];
    update_field(text.text,"version",version,64);update_field(text.text,"files",files,1024);update_field(text.text,"files_sha256",sha,80);
    if(wcscmp(version,updateCurrent)||!update_url_ok(files)||wcslen(sha)!=64)return;
    for(int i=0;i<64;++i)shaA[i]=(char)towlower(sha[i]);shaA[64]=0;
    static char list[262144];DeltaBuffer buffer={list,0,sizeof(list)};list[0]=0;
    if(update_http_quiet(files,update_delta_sink,&buffer,sizeof(list)-1)||!update_sha_matches(list,buffer.length,shaA))return;
    update_write_bytes(path,list,buffer.length);
}
static int update_space_ok(void){
    ULARGE_INTEGER free_bytes;if(!GetDiskFreeSpaceExW(root,&free_bytes,NULL,NULL))return 1;
    /* staging plus the copy, with headroom */
    LONG64 need=updateTotal+(deltaReady?0:updateFullBytes)+(LONG64)256*1048576;
    if((LONG64)free_bytes.QuadPart>=need)return 1;
    wchar_t message[200];swprintf(message,200,tr(L"Not enough free space: %.1f GB needed on this drive, %.1f GB free."),need/1073741824.0,free_bytes.QuadPart/1073741824.0);
    update_fail(message);return 0;
}
static void update_store_target_list(void){
    wchar_t path[2400];update_list_path(path,root,L"target-files.txt");DeleteFileW(path);
    if(updateTargetList)update_write_bytes(path,updateTargetList,updateTargetListLength);
}
static DWORD update_download_any(void){
    if(deltaReady){
        int result=update_download_delta();
        if(result<0){InterlockedExchange(&updateCancel,0);InterlockedExchange(&updateState,UPDATE_AVAILABLE);update_notify();return 1;}
        if(result>0){
            wchar_t manifest[2600];swprintf(manifest,2600,L"%ls\\updates\\staging\\TrueCombat Platinum\\manifest.json",root);
            /* 2.6.2: a repair (or a delta without a new manifest) leaves manifest.json unstaged: the installed one counts */
            if(GetFileAttributesW(manifest)==INVALID_FILE_ATTRIBUTES)swprintf(manifest,2600,L"%ls\\manifest.json",root);
            FILE *file=_wfopen(manifest,L"rb");char text[4096]={0};if(file){size_t n=fread(text,1,sizeof(text)-1,file);text[n]=0;fclose(file);}
            char version[64];WideCharToMultiByte(CP_UTF8,0,updateLatest,-1,version,64,NULL,NULL);
            char needle[100];snprintf(needle,100,"\"version\": \"%s\"",version);
            if(file&&strstr(text,needle)){InterlockedExchange(&updateState,UPDATE_READY);update_notify();return 0;}
        }
        /* Fall back to the full package. */
        update_log(L"per-file download did not finish (%ls); falling back to the full package",updateFileProblem[0]?updateFileProblem:L"no reason recorded");
        deltaReady=0;InterlockedExchange64(&updateTotal,updateFullBytes);
    }
    wchar_t first[200];wcscpy(first,updateFileProblem);
    DWORD result=update_download_full();
    /* the zip failed too: the per-file reason (often the antivirus naming the file) is the more useful one */
    if(result&&first[0]&&InterlockedCompareExchange(&updateState,0,0)==UPDATE_FAILED&&wcscmp(first,updateError))update_fail(first);
    return result;
}
static DWORD WINAPI update_download_worker(LPVOID unused){
    (void)unused;
    {wchar_t folder[2400];swprintf(folder,2400,L"%ls\\updates",root);SHCreateDirectoryExW(NULL,folder,NULL);}
    updateFileProblem[0]=0;
    update_log(L"%ls: %ls -> %ls",updateRepair?L"repair":L"update",updateCurrent[0]?updateCurrent:L"(not installed)",updateLatest);
    if(!update_clear_staging(1))return 1;
    if(!update_space_ok())return 1;
    update_record_installed();
    update_store_target_list();
    return update_download_any();
}
static void update_start(DWORD (WINAPI *worker)(LPVOID)){
    HANDLE thread=CreateThread(NULL,0,worker,NULL,0,NULL);if(thread)CloseHandle(thread);
}
/* Launcher-update button: reads only the launcher fields of the official latest
   feed (even while a Versions choice keeps the game on an older release), and
   downloads a newer launcher straight away. Returns 0 when a newer launcher is
   ready, 4 when this one is current, 3 when the feed failed, 8 when the feed does
   not version the launcher, 5 when the download failed. Runs on its own thread. */
static void launcher_fail(const wchar_t *message);
static DWORD WINAPI launcher_check_worker(LPVOID unused){
    (void)unused;
    static UpdateText text;text.length=0;text.text[0]=0;
    if(!updateLatestFeed[0]){launcher_fail(L"Launcher updates are not set up for this copy.");return 8;}
    if(update_http_quiet(updateLatestFeed,update_text_sink,&text,16000)){launcher_fail(L"The update server could not be reached. Check your connection and try again.");return 3;}
    if(!update_verify_signature(text.text,text.length)){launcher_fail(L"The update information is not signed by Team Terminus, so it was ignored.");return 3;}
    update_read_launcher_fields(text.text);
    if(!launcherFeedManaged){launcher_fail(L"The latest release does not offer launcher updates yet.");return 8;}
    InterlockedExchange(&launcherFromLatest,1);
    if(update_compare(launcherLatest,PLATINUM_LAUNCHER_VERSION)<=0){InterlockedExchange(&launcherUpdateState,LAUNCHER_CURRENT);update_notify();return 4;}
    InterlockedExchange(&launcherUpdateState,LAUNCHER_DOWNLOADING);update_notify();
    return launcher_update_worker(NULL)?5:0;
}
static void launcher_check_begin(void){
    LONG from=InterlockedCompareExchange(&launcherUpdateState,0,0);
    if(from==LAUNCHER_CHECKING||from==LAUNCHER_DOWNLOADING||from==LAUNCHER_READY)return;
    if(InterlockedCompareExchange(&launcherUpdateState,LAUNCHER_CHECKING,from)!=from)return;
    InterlockedExchange(&launcherManualCheck,1);update_notify();update_start(launcher_check_worker);
}
static void update_begin_check(void){
    if(!updateFeed[0])return;
    InterlockedExchange(&updateState,UPDATE_CHECKING);update_notify();update_start(update_check_worker);
}
typedef struct {HANDLE file;BCRYPT_HASH_HANDLE hash;LONG64 done;} LauncherDownload;
static int launcher_file_sink(void *context,const void *data,DWORD size){
    LauncherDownload *download=(LauncherDownload*)context;DWORD written=0;
    if(!WriteFile(download->file,data,size,&written,NULL)||written!=size)return 0;
    if(BCryptHashData(download->hash,(PUCHAR)data,size,0))return 0;
    download->done+=size;return 1;
}
/* The EXE must carry the UTF-16 marker of the version the feed promised. */
static int launcher_has_marker(const wchar_t *path,const wchar_t *version){
    wchar_t marker[96];swprintf(marker,96,L"TrueCombatPlatinumLauncher/%ls",version);
    size_t bytes=(wcslen(marker)+1)*sizeof(wchar_t);
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);if(file==INVALID_HANDLE_VALUE)return 0;
    LARGE_INTEGER size;int found=0;
    if(GetFileSizeEx(file,&size)&&size.QuadPart>64&&size.QuadPart<(LONGLONG)64*1048576){
        unsigned char *data=(unsigned char*)malloc((size_t)size.QuadPart);DWORD got=0;
        if(data&&ReadFile(file,data,(DWORD)size.QuadPart,&got,NULL)&&got==(DWORD)size.QuadPart&&data[0]=='M'&&data[1]=='Z'){
            for(size_t i=0;i+bytes<=got&&!found;i+=2)found=!memcmp(data+i,marker,bytes);
        }
        free(data);
    }
    CloseHandle(file);return found;
}
static void launcher_fail(const wchar_t *message){
    wcsncpy(launcherError,message,199);launcherError[199]=0;InterlockedExchange(&launcherUpdateState,LAUNCHER_FAILED);update_notify();
}
static DWORD WINAPI launcher_update_worker(LPVOID unused){
    (void)unused;
    wchar_t self[2200],fresh[2300],old[2300];
    if(!GetModuleFileNameW(NULL,self,2200)||wcslen(self)>=2190){launcher_fail(L"The launcher could not find itself.");return 1;}
    swprintf(fresh,2300,L"%ls.new",self);swprintf(old,2300,L"%ls.old",self);
    BCRYPT_ALG_HANDLE algorithm=NULL;LauncherDownload download={INVALID_HANDLE_VALUE,NULL,0};
    if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0)||BCryptCreateHash(algorithm,&download.hash,NULL,0,NULL,0,0)){
        if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);launcher_fail(L"Windows could not start the file check.");return 1;}
    download.file=CreateFileW(fresh,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(download.file==INVALID_HANDLE_VALUE){BCryptDestroyHash(download.hash);BCryptCloseAlgorithmProvider(algorithm,0);
        launcher_fail(L"The launcher folder is not writable, so the launcher update was skipped.");return 1;}
    int failed=update_http_quiet(launcherUrl,launcher_file_sink,&download,launcherBytes+1);
    CloseHandle(download.file);
    unsigned char digest[32];char hex[65];
    BCryptFinishHash(download.hash,digest,32,0);BCryptDestroyHash(download.hash);BCryptCloseAlgorithmProvider(algorithm,0);
    for(int i=0;i<32;++i)sprintf(hex+i*2,"%02x",digest[i]);
    if(failed){DeleteFileW(fresh);launcher_fail(L"The launcher update could not be downloaded.");return 1;}
    if(download.done!=launcherBytes||strcmp(hex,launcherSha)||!launcher_has_marker(fresh,launcherLatest)){
        DeleteFileW(fresh);launcher_fail(L"The launcher download did not pass the file check and was removed.");return 1;}
    /* Swap: the running EXE moves aside, the checked one takes its name. */
    SetFileAttributesW(old,FILE_ATTRIBUTE_NORMAL);DeleteFileW(old);
    if(!MoveFileExW(self,old,MOVEFILE_REPLACE_EXISTING)){DeleteFileW(fresh);launcher_fail(L"The launcher could not be replaced. Try again after a restart.");return 1;}
    if(!MoveFileExW(fresh,self,MOVEFILE_REPLACE_EXISTING)){
        MoveFileExW(old,self,MOVEFILE_REPLACE_EXISTING);DeleteFileW(fresh);
        launcher_fail(L"The launcher could not be replaced. Try again after a restart.");return 1;}
    SetFileAttributesW(old,FILE_ATTRIBUTE_HIDDEN);
    /* The game folder keeps a copy when the launcher lives elsewhere (installer choice). */
    wchar_t copy[2400];swprintf(copy,2400,L"%ls\\TrueCombatPlatinum.exe",root);
    if(_wcsicmp(copy,self)&&GetFileAttributesW(copy)!=INVALID_FILE_ATTRIBUTES)CopyFileW(self,copy,FALSE);
    InterlockedExchange(&launcherUpdateState,LAUNCHER_READY);update_notify();return 0;
}
/* On start: remove the EXE a launcher update moved aside, and any unfinished download. */
static void launcher_cleanup(void){
    wchar_t self[2200],path[2300];if(!GetModuleFileNameW(NULL,self,2200)||wcslen(self)>=2190)return;
    swprintf(path,2300,L"%ls.new",self);DeleteFileW(path);
    swprintf(path,2300,L"%ls.old",self);SetFileAttributesW(path,FILE_ATTRIBUTE_NORMAL);
    for(int i=0;i<20&&GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES&&!DeleteFileW(path);++i)Sleep(100);
}
/* The strip offers a launcher restart only while no game update needs it. */
static int launcher_strip_active(LONG state){
    if(InterlockedCompareExchange(&launcherUpdateState,0,0)!=LAUNCHER_READY)return 0;
    int pinned=updatePinned[0]&&updateCurrent[0]&&!wcscmp(updatePinned,updateCurrent)&&!updateSwitching;
    return updateCurrent[0]&&(state==UPDATE_CURRENT||state==UPDATE_IDLE||state==UPDATE_OFF||state==UPDATE_FAILED||(pinned&&state==UPDATE_AVAILABLE));
}
static void launcher_restart(HWND window){
    wchar_t self[2200],command[2400];if(!GetModuleFileNameW(NULL,self,2200))return;
    swprintf(command,2400,L"\"%ls\" --launcher-updated",self);
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
    if(!CreateProcessW(self,command,NULL,NULL,FALSE,0,NULL,launcherDir[0]?launcherDir:root,&si,&pi)){error(L"The launcher could not restart. Close it and open it again.");return;}
    CloseHandle(pi.hThread);CloseHandle(pi.hProcess);
    if(window)DestroyWindow(window);
}
/* Top-level folders and files that belong to the player, never replaced. */
static int update_keep(const wchar_t *relative){
    const wchar_t *keep[]={L"profile",L"profile-server",L"server-state",L"updates",L"player.ini",L"update.ini",L"launcher.ini"};
    for(unsigned i=0;i<sizeof(keep)/sizeof(keep[0]);++i){
        size_t n=wcslen(keep[i]);
        if(!_wcsnicmp(relative,keep[i],n)&&(relative[n]==0||relative[n]==L'\\'))return 1;
    }
    return 0;
}
/* pass 0: check every target can be written; pass 1: copy. Returns failing count. */
static int update_copy_tree(const wchar_t *source,const wchar_t *target,const wchar_t *relative,int pass,FILE *log){
    wchar_t pattern[2600];swprintf(pattern,2600,L"%ls\\%ls%ls*",source,relative,relative[0]?L"\\":L"");
    WIN32_FIND_DATAW item;HANDLE find=FindFirstFileW(pattern,&item);if(find==INVALID_HANDLE_VALUE)return 0;
    int failures=0;
    do{
        if(!wcscmp(item.cFileName,L".")||!wcscmp(item.cFileName,L".."))continue;
        wchar_t child[1200];swprintf(child,1200,L"%ls%ls%ls",relative,relative[0]?L"\\":L"",item.cFileName);
        if(update_keep(child))continue;
        wchar_t from[2600],to[2600];swprintf(from,2600,L"%ls\\%ls",source,child);swprintf(to,2600,L"%ls\\%ls",target,child);
        if(item.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY){
            if(pass)CreateDirectoryW(to,NULL);
            failures+=update_copy_tree(source,target,child,pass,log);
        }else if(!pass){
            if(GetFileAttributesW(to)!=INVALID_FILE_ATTRIBUTES){
                HANDLE handle=CreateFileW(to,GENERIC_WRITE,0,NULL,OPEN_EXISTING,0,NULL);
                if(handle==INVALID_HANDLE_VALUE){++failures;if(log)fwprintf(log,L"in use: %ls\n",child);}else CloseHandle(handle);
            }
        }else if(!CopyFileW(from,to,FALSE)){++failures;if(log)fwprintf(log,L"copy failed: %ls (%lu)\n",child,GetLastError());}
    }while(FindNextFileW(find,&item));
    FindClose(find);return failures;
}
/* Reads the relative paths of a files.txt into one buffer of fixed 260-wide names. */
static wchar_t *update_read_list(const wchar_t *path,int *count){
    *count=0;FILE *file=_wfopen(path,L"rb");if(!file)return NULL;
    static char text[262144];size_t n=fread(text,1,sizeof(text)-1,file);fclose(file);text[n]=0;
    wchar_t *names=(wchar_t*)calloc(DELTA_MAX,260*sizeof(wchar_t));if(!names)return NULL;
    for(char *line=text;line&&*line&&*count<DELTA_MAX;){
        char *end=strchr(line,'\n');if(end)*end=0;
        char sha[65],asset[200],rel[260];long long bytes;
        if(sscanf(line,"%64s %lld %199s %259[^\r\n]",sha,&bytes,asset,rel)==4){
            wchar_t *slot=names+(*count)*260;MultiByteToWideChar(CP_UTF8,0,rel,-1,slot,260);slot[259]=0;
            for(wchar_t *c=slot;*c;++c)if(*c==L'/')*c=L'\\';
            ++*count;
        }
        line=end?end+1:NULL;
    }
    return names;
}
/* After a successful apply: delete files only the previous version shipped. */
static void update_prune(const wchar_t *target,FILE *log){
    wchar_t old_path[2400],new_path[2400];update_list_path(old_path,target,L"installed-files.txt");update_list_path(new_path,target,L"target-files.txt");
    if(GetFileAttributesW(new_path)==INVALID_FILE_ATTRIBUTES)return;
    int old_count=0,new_count=0;wchar_t *old_names=update_read_list(old_path,&old_count),*new_names=update_read_list(new_path,&new_count);
    if(old_names&&new_names&&new_count>0){
        for(int i=0;i<old_count;++i){
            const wchar_t *name=old_names+i*260;int kept=0;
            for(int j=0;j<new_count&&!kept;++j)kept=!_wcsicmp(name,new_names+j*260);
            if(kept||!update_delta_path_ok(name)||!_wcsicmp(name,L"TrueCombatPlatinum.exe"))continue;
            wchar_t full[2600];swprintf(full,2600,L"%ls\\%ls",target,name);
            if(GetFileAttributesW(full)!=INVALID_FILE_ATTRIBUTES){
                if(DeleteFileW(full)){if(log)fwprintf(log,L"removed: %ls\n",name);}
                else if(log)fwprintf(log,L"could not remove: %ls (%lu)\n",name,GetLastError());
            }
        }
    }
    free(old_names);free(new_names);
    if(new_count>0)MoveFileExW(new_path,old_path,MOVEFILE_REPLACE_EXISTING);else DeleteFileW(new_path);
}
/* The DX12 renderer's caches (compressed material maps, reflection probes) are built
   from the installed paks, so a new game version makes them dead weight: clear them
   with every update. They rebuild on the next map load. */
static void update_render_cache_path(const wchar_t *target,wchar_t *out,int size){swprintf(out,size,L"%ls\\profile\\tcetest\\dx12cache",target);}
static void update_render_cache_reset(const wchar_t *target,FILE *log){
    wchar_t cache[2400];update_render_cache_path(target,cache,2400);
    if(GetFileAttributesW(cache)==INVALID_FILE_ATTRIBUTES)return;
    update_remove_tree(cache);
    if(log)fwprintf(log,GetFileAttributesW(cache)==INVALID_FILE_ATTRIBUTES?L"cleared: profile\\tcetest\\dx12cache\n":L"could not fully clear: profile\\tcetest\\dx12cache\n");
}
/* Storage limits: every folder the game keeps writing to has a budget, and on each
   launcher start the oldest files go first until it is back under 90 % of it.
   Replays can be set in player.ini [Storage] ReplaysGB (0 = no limit). The shader
   cache is also cleared on a version change (update_render_cache_housekeeping) and
   pruned per installed pak set by the game itself (FS_PruneHomeCache). */
typedef struct{const wchar_t *folder;LONG64 limit;const wchar_t *keep;}UpdateBudget;
enum{UPDATE_BUDGET_CACHE,UPDATE_BUDGET_REPLAYS,UPDATE_BUDGET_SCREENSHOTS,UPDATE_BUDGET_REPORTS,
     UPDATE_BUDGET_NAVCACHE,UPDATE_BUDGET_HOST_NAVCACHE,UPDATE_BUDGET_HOST_STATS,UPDATE_BUDGET_HOST_REPORTS,UPDATE_BUDGET_HOST_DEMOS,UPDATE_BUDGET_COUNT};
static UpdateBudget updateBudgets[UPDATE_BUDGET_COUNT]={
    {L"profile\\tcetest\\dx12cache",2LL<<30,L"cache-version.txt"},
    {L"profile\\tcetest\\demos",2LL<<30,NULL},
    {L"profile\\tcetest\\screenshots",1LL<<30,NULL},
    {L"profile\\tcetest\\bugreports",200LL<<20,NULL},
    /* bot navigation: one file per map and map checksum, so an updated map leaves the old one behind */
    {L"profile\\tcetest\\navcache",64LL<<20,NULL},
    {L"server-state\\tcetest\\navcache",64LL<<20,NULL},
    /* a server hosted from the launcher: per-match/per-round stats, player and auto reports, server demos */
    {L"server-state\\tcetest\\stats",256LL<<20,NULL},
    {L"server-state\\tcetest\\reports",64LL<<20,NULL},
    {L"server-state\\tcetest\\demos",1LL<<30,NULL},
};
static LONG64 update_budget_limit(int which){
    if(which==UPDATE_BUDGET_REPLAYS){int gb=GetPrivateProfileIntW(L"Storage",L"ReplaysGB",2,ini);return gb<=0?0:(LONG64)(gb>1000?1000:gb)<<30;}
    return which>=0&&which<UPDATE_BUDGET_COUNT?updateBudgets[which].limit:0;
}
typedef struct{FILETIME time;LONG64 bytes;wchar_t *path;}UpdateAged;
static void update_collect_aged(const wchar_t *folder,int depth,const wchar_t *keep,UpdateAged **items,int *count,int *capacity,LONG64 *total){
    if(depth>6)return;
    wchar_t pattern[2600];swprintf(pattern,2600,L"%ls\\*",folder);WIN32_FIND_DATAW item;HANDLE find=FindFirstFileW(pattern,&item);
    if(find==INVALID_HANDLE_VALUE)return;
    do{
        if(!wcscmp(item.cFileName,L".")||!wcscmp(item.cFileName,L"..")||(item.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT))continue;
        wchar_t child[2600];swprintf(child,2600,L"%ls\\%ls",folder,item.cFileName);
        if(item.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY){update_collect_aged(child,depth+1,keep,items,count,capacity,total);continue;}
        LONG64 bytes=((LONG64)item.nFileSizeHigh<<32)|item.nFileSizeLow;*total+=bytes;
        if(keep&&!depth&&!_wcsicmp(item.cFileName,keep))continue;
        if(*count>=*capacity){int grown=*capacity?*capacity*2:256;UpdateAged *more=(UpdateAged*)realloc(*items,grown*sizeof(UpdateAged));if(!more)continue;*items=more;*capacity=grown;}
        UpdateAged *slot=*items+*count;slot->path=_wcsdup(child);if(!slot->path)continue;
        slot->time=item.ftLastWriteTime;slot->bytes=bytes;++*count;
    }while(FindNextFileW(find,&item));
    FindClose(find);
}
static int update_aged_compare(const void *a,const void *b){return CompareFileTime(&((const UpdateAged*)a)->time,&((const UpdateAged*)b)->time);}
static LONG64 update_enforce_budget(int which){
    LONG64 limit=update_budget_limit(which);if(limit<=0)return 0;
    wchar_t folder[2400];swprintf(folder,2400,L"%ls\\%ls",root,updateBudgets[which].folder);
    if(GetFileAttributesW(folder)==INVALID_FILE_ATTRIBUTES)return 0;
    UpdateAged *items=NULL;int count=0,capacity=0;LONG64 total=0,freed=0;
    update_collect_aged(folder,0,updateBudgets[which].keep,&items,&count,&capacity,&total);
    if(total>limit&&count){
        qsort(items,count,sizeof(UpdateAged),update_aged_compare);
        LONG64 target=limit/10*9;
        for(int i=0;i<count&&total-freed>target;++i)if(DeleteFileW(items[i].path))freed+=items[i].bytes;
    }
    for(int i=0;i<count;++i)free(items[i].path);
    free(items);return freed;
}
static void update_enforce_budgets(void){for(int i=0;i<UPDATE_BUDGET_COUNT;++i)update_enforce_budget(i);}
/* On launcher start: keep the render cache tied to the installed version.
   dx12cache\cache-version.txt names the version it was built for; a different (or
   missing) stamp means it predates this install, so it goes. That also removes the
   per-map dx12cache\mat\<checksum> pile older builds left behind (up to 11 GB).
   Its size is bounded by the storage budget above. */
static void update_render_cache_housekeeping(void){
    wchar_t cache[2400],stamp_path[2500];update_render_cache_path(root,cache,2400);
    if(GetFileAttributesW(cache)==INVALID_FILE_ATTRIBUTES)return;
    swprintf(stamp_path,2500,L"%ls\\cache-version.txt",cache);
    wchar_t stamp[64]={0};FILE *file=_wfopen(stamp_path,L"r, ccs=UTF-8");
    if(file){if(!fgetws(stamp,64,file))stamp[0]=0;fclose(file);for(wchar_t *c=stamp;*c;++c)if(*c==L'\r'||*c==L'\n'){*c=0;break;}}
    wchar_t legacy[2500];swprintf(legacy,2500,L"%ls\\mat",cache);
    /* No stamp: stale only when the old per-map mat\ pile is there (an install from before
       this change). A cache the game started after an update (the updater removes the folder,
       so it comes back unstamped) is the current one: stamp it instead of clearing it again. */
    int stale=updateCurrent[0]&&(stamp[0]?wcscmp(stamp,updateCurrent)!=0:GetFileAttributesW(legacy)!=INVALID_FILE_ATTRIBUTES);
    if(stale)update_remove_tree(cache);
    else if(GetFileAttributesW(legacy)!=INVALID_FILE_ATTRIBUTES)update_remove_tree(legacy);
    if(!updateCurrent[0])return;
    CreateDirectoryW(cache,NULL);
    if(wcscmp(stamp,updateCurrent)||GetFileAttributesW(stamp_path)==INVALID_FILE_ATTRIBUTES){
        file=_wfopen(stamp_path,L"w, ccs=UTF-8");if(file){fwprintf(file,L"%ls\n",updateCurrent);fclose(file);}
    }
}
/* 0.38.1: an antivirus program can quarantine a file after the download check passed (in 0.38.0 some took
   the engine out of updates\staging). The copy would then keep the previous version's file next to the new
   data, and the game no longer starts. So the version being installed (updates\target-files.txt) is checked:
   before the copy, every file must be staged with its listed size and SHA-256, or not staged and already
   installed with them; after the copy, every staged file must be in the game folder at its listed size (an
   on-access scan can remove it there too). Lines without a real SHA-256 (the package listing of releases
   without files.txt) only need the staged file. The launcher EXE is left out: a repair or a separately
   updated launcher skips it on purpose. A miss names the file in bad (relative path). */
typedef struct {const wchar_t *source,*target;int after;wchar_t *bad;} UpdateStagedScan;
static int update_entry_staged(void *context,const char *sha,LONG64 bytes,const wchar_t *asset,const wchar_t *path){
    UpdateStagedScan *scan=(UpdateStagedScan*)context;(void)asset;
    if(!update_delta_path_ok(path))return 1;
    wchar_t relative[260];wcsncpy(relative,path,259);relative[259]=0;for(wchar_t *c=relative;*c;++c)if(*c==L'/')*c=L'\\';
    if(!_wcsicmp(relative,L"TrueCombatPlatinum.exe"))return 1;
    int known=0;for(int i=0;i<64&&!known;++i)known=sha[i]!='0';
    wchar_t staged[2600],installed[2600];update_local_path(staged,scan->source,relative);update_local_path(installed,scan->target,relative);
    LONG64 size=0;char hex[65]={0};int ok;
    int isStaged=GetFileAttributesW(staged)!=INVALID_FILE_ATTRIBUTES;
    /* 2.6.2: after the copy every staged file is hashed again in the game folder, not only measured */
    if(scan->after)ok=!isStaged||(update_file_size(installed,&size)&&(!known||(size==bytes&&update_hash_file(installed,hex)&&!strcmp(hex,sha))));
    else if(isStaged)ok=!known||(update_file_size(staged,&size)&&size==bytes&&update_hash_file(staged,hex)&&!strcmp(hex,sha));
    else ok=known&&update_file_size(installed,&size)&&size==bytes&&update_hash_file(installed,hex)&&!strcmp(hex,sha);
    if(ok)return 1;
    wcsncpy(scan->bad,relative,259);scan->bad[259]=0;return 0;
}
static int update_staged_check(const wchar_t *source,const wchar_t *target,int after,wchar_t *bad){
    bad[0]=0;wchar_t path[2400];update_list_path(path,target,L"target-files.txt");
    FILE *file=_wfopen(path,L"rb");if(!file)return 1;
    static char list[262144];size_t n=fread(list,1,sizeof(list)-1,file);fclose(file);list[n]=0;
    UpdateStagedScan scan={source,target,after,bad};update_each_entry(list,(DWORD)n,update_entry_staged,&scan);
    return !bad[0];
}
/* The launcher reads this after --update-failed to say which file went missing (stage: 1 before, 2 after the copy). */
static void update_blocked_path(wchar_t *out,const wchar_t *base){update_list_path(out,base,L"update-blocked.ini");}
static void update_write_blocked(const wchar_t *target,int stage,const wchar_t *file){
    wchar_t path[2400],number[8];update_blocked_path(path,target);swprintf(number,8,L"%d",stage);
    WritePrivateProfileStringW(L"Blocked",L"Stage",number,path);WritePrivateProfileStringW(L"Blocked",L"File",file,path);
}
static int updateRepairOnRetry;     /* the failed update left a file missing in the game folder: Repair fetches it */
static int updateBlockedNotice;     /* show that message once when the launcher window opens */
static int update_repair_begin(void);
static void update_read_blocked(void){
    wchar_t path[2400],file[260];update_blocked_path(path,root);
    int stage=GetPrivateProfileIntW(L"Blocked",L"Stage",0,path);GetPrivateProfileStringW(L"Blocked",L"File",L"",file,260,path);DeleteFileW(path);
    if(!stage||!file[0])return;
    updateBlockedNotice=1;
    const wchar_t *name=file;for(const wchar_t *c=file;*c;++c)if(*c==L'\\')name=c+1;
    if(stage==2){updateRepairOnRetry=1;swprintf(updateError,200,L"Your antivirus removed %ls. Add the TrueCombat Platinum folder as an exception, then click Repair.",name);}
    else swprintf(updateError,200,L"Your antivirus removed %ls. Add the TrueCombat Platinum folder as an exception, then click Try again.",name);
    updateError[199]=0;
}
static int update_count_files(const wchar_t *folder){
    wchar_t pattern[2600];swprintf(pattern,2600,L"%ls\\*",folder);WIN32_FIND_DATAW item;HANDLE find=FindFirstFileW(pattern,&item);int count=0;
    if(find==INVALID_HANDLE_VALUE)return 0;
    do{if(!wcscmp(item.cFileName,L".")||!wcscmp(item.cFileName,L".."))continue;
        if(item.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY){wchar_t child[2600];swprintf(child,2600,L"%ls\\%ls",folder,item.cFileName);count+=update_count_files(child);}else ++count;
    }while(FindNextFileW(find,&item));
    FindClose(find);return count;
}
/* Runs from updates\platinum-updater.exe after the launcher has closed. */
static int update_apply_main(const wchar_t *target,DWORD pid){
    HANDLE parent=OpenProcess(SYNCHRONIZE,FALSE,pid);
    if(parent){WaitForSingleObject(parent,30000);CloseHandle(parent);}
    wchar_t source[2400],log_path[2400];swprintf(source,2400,L"%ls\\updates\\staging\\TrueCombat Platinum",target);
    swprintf(log_path,2400,L"%ls\\updates\\last-update.log",target);
    FILE *log=_wfopen(log_path,L"w, ccs=UTF-8");
    {wchar_t old[2400];update_blocked_path(old,target);DeleteFileW(old);}
    /* 2.6.2: a marker while files are being copied; still there on the next start = the apply was interrupted */
    wchar_t marker[2400];update_list_path(marker,target,L"apply-in-progress");
    {FILE *mark=_wfopen(marker,L"w");if(mark){fputs("copying\n",mark);fclose(mark);}}
    int stagedCount=update_count_files(source);
    update_log(L"apply: %d staged file(s) into %ls",stagedCount,target);
    wchar_t blocked[260];
    int busy=0,code=0;
    if(!update_staged_check(source,target,0,blocked)){
        /* Nothing copied: the installed version stays complete and playable. */
        if(log)fwprintf(log,L"Update not applied: %ls is missing or damaged in the downloaded update (an antivirus program may have removed it).\n",blocked);
        update_write_blocked(target,1,blocked);code=7;
    }else{
    for(int attempt=0;attempt<10;++attempt){busy=update_copy_tree(source,target,L"",0,attempt==9?log:NULL);if(!busy)break;Sleep(1000);}
    if(busy){if(log)fwprintf(log,L"Update not applied: %d file(s) are in use. Close the game and any server, then try again.\n",busy);code=5;}
    else{int failed=update_copy_tree(source,target,L"",1,log);if(log)fwprintf(log,failed?L"Update applied with %d copy failure(s).\n":L"Update applied.\n",failed);code=failed?6:0;}
    if(!code&&!update_staged_check(source,target,1,blocked)){
        if(log)fwprintf(log,L"Update incomplete: %ls is missing from the game folder after the copy (an antivirus program may have removed it).\n",blocked);
        update_write_blocked(target,2,blocked);code=8;
    }
    }
    if(!code){update_prune(target,log);update_render_cache_reset(target,log);}
    DeleteFileW(marker);
    {wchar_t result[2400],number[16];update_list_path(result,target,L"update-result.ini");swprintf(number,16,L"%d",code?0:stagedCount);
     WritePrivateProfileStringW(L"Result",L"Files",number,result);swprintf(number,16,L"%d",code);WritePrivateProfileStringW(L"Result",L"Code",number,result);}
    update_log(code?L"apply failed with code %d%ls%ls":L"apply finished (code %d)%ls%ls",code,code&&blocked[0]?L", file ":L"",code?blocked:L"");
    /* A launcher kept outside the game folder gets the new launcher too. */
    const wchar_t *home=launcherDir[0]?launcherDir:target;
    if(!code&&_wcsicmp(home,target)){
        wchar_t from[2400],to[2400],staged[2600];swprintf(from,2400,L"%ls\\TrueCombatPlatinum.exe",target);swprintf(to,2400,L"%ls\\TrueCombatPlatinum.exe",home);
        swprintf(staged,2600,L"%ls\\TrueCombatPlatinum.exe",source);
        if(GetFileAttributesW(staged)!=INVALID_FILE_ATTRIBUTES){
            int copied=0;for(int attempt=0;attempt<10&&!(copied=CopyFileW(from,to,FALSE));++attempt)Sleep(500);
            if(log)fwprintf(log,copied?L"launcher refreshed: %ls\n":L"launcher not refreshed: %ls\n",to);
        }
    }
    /* The staged copy is no longer needed once everything is in place. */
    if(!code){
        wchar_t spent[2400];swprintf(spent,2400,L"%ls\\updates\\staging",target);update_remove_tree(spent);
        swprintf(spent,2400,L"%ls\\updates\\package.zip",target);DeleteFileW(spent);
    }
    if(log)fclose(log);
    wchar_t launcher[2400],command[2600];swprintf(launcher,2400,L"%ls\\TrueCombatPlatinum.exe",home);
    swprintf(command,2600,L"\"%ls\" %ls",launcher,code?L"--update-failed":L"--updated");
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
    if(!updateHeadless&&CreateProcessW(launcher,command,NULL,NULL,FALSE,0,NULL,home,&si,&pi)){CloseHandle(pi.hThread);CloseHandle(pi.hProcess);}
    return code;
}
/* Called by the launcher: hand over to a copy of itself and close. */
static int update_apply(HWND window){
    if(starting_game&&WaitForSingleObject(starting_game,0)==WAIT_TIMEOUT){MessageBoxW(window,L"Close the game before updating.",TITLE,MB_OK|MB_ICONINFORMATION);return 0;}
    wchar_t self[2200],helper[2400],command[5000];GetModuleFileNameW(NULL,self,2200);
    swprintf(helper,2400,L"%ls\\updates\\platinum-updater.exe",root);
    {wchar_t result[2400];update_list_path(result,root,L"update-result.ini");DeleteFileW(result);
     WritePrivateProfileStringW(L"Result",L"Repair",updateRepair?L"1":L"0",result);WritePrivateProfileStringW(L"Result",L"Version",updateLatest,result);}
    if(!CopyFileW(self,helper,FALSE)){error(L"The updater could not start. Check that the game folder is writable.");return 0;}
    swprintf(command,5000,L"\"%ls\" --apply-update \"%ls\" %lu --launcher-dir \"%ls\"%ls",helper,root,GetCurrentProcessId(),launcherDir[0]?launcherDir:root,updateHeadless?L" --no-relaunch":L"");
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
    if(!CreateProcessW(helper,command,NULL,NULL,FALSE,0,NULL,root,&si,&pi)){error(L"The updater could not start.");return 0;}
    CloseHandle(pi.hThread);CloseHandle(pi.hProcess);
    if(window)DestroyWindow(window);
    return 1;
}
/* Housekeeping on launcher start: remove a finished updater and old staging. */
static int updateForceRepair;   /* 2.6.2: the last apply was interrupted: check every file on this start */
static void update_cleanup(int updated){
    wchar_t path[2400];swprintf(path,2400,L"%ls\\updates\\platinum-updater.exe",root);
    for(int i=0;i<20&&GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES&&!DeleteFileW(path);++i)Sleep(100);
    (void)updated;
    /* 2.6.2 self-healing: nothing in staging is ever resumed (each attempt starts clean), so leftovers of a broken,
       blocked or interrupted update always go; a failure to remove them is logged and reported by the next attempt. */
    update_clear_staging(0);
    update_list_path(path,root,L"apply-in-progress");
    if(GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES){updateForceRepair=1;DeleteFileW(path);update_log(L"start: the last update was interrupted while copying; every file is checked");}
    update_list_path(path,root,L"update-result.ini");
    if(GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES){
        int repair=GetPrivateProfileIntW(L"Result",L"Repair",0,path),files=GetPrivateProfileIntW(L"Result",L"Files",0,path),code=GetPrivateProfileIntW(L"Result",L"Code",-1,path);
        if(repair&&code==0){swprintf(updateRepairNote,160,tr(L"Repaired %d file%ls"),files,files==1?L"":L"s");update_log(L"start: %ls",updateRepairNote);}
        DeleteFileW(path);
    }
    update_render_cache_housekeeping();
    update_enforce_budgets();
}
/* Text for the update strip. */
static void update_describe(wchar_t *title,int title_size,wchar_t *detail,int detail_size,wchar_t *button,int button_size){
    LONG state=updatePreview>=0?updatePreview:InterlockedCompareExchange(&updateState,0,0);
    const wchar_t *current=updateCurrent[0]?updateCurrent:L"development build";
    int fresh=!updateCurrent[0]&&updatePreview<0;
    int pinned=updatePinned[0]&&updateCurrent[0]&&!wcscmp(updatePinned,updateCurrent)&&!updateSwitching;
    detail[0]=0;
    if(fresh&&(state==UPDATE_IDLE||state==UPDATE_CHECKING||state==UPDATE_AVAILABLE||state==UPDATE_READY||state==UPDATE_CURRENT)){
        if(state==UPDATE_AVAILABLE){swprintf(title,title_size,L"Ready to install %ls",updateLatest);
            swprintf(detail,detail_size,L"%.1f GB download  \x00B7  game files are verified as they arrive",updateTotal/1073741824.0);wcsncpy(button,L"Install",button_size);}
        else if(state==UPDATE_READY){swprintf(title,title_size,L"%ls is downloaded",updateLatest);
            swprintf(detail,detail_size,L"The launcher restarts once to finish the installation.");wcsncpy(button,L"Finish install",button_size);}
        else{swprintf(title,title_size,L"Game files not installed");swprintf(detail,detail_size,state==UPDATE_CHECKING?L"Looking up the latest release...":L"The launcher downloads the latest release for you.");
            wcsncpy(button,state==UPDATE_CHECKING?L"Checking...":L"Find release",button_size);}
        title[title_size-1]=0;detail[detail_size-1]=0;button[button_size-1]=0;return;
    }
    if(updatePreview<0&&launcher_strip_active(state)){
        swprintf(title,title_size,L"Launcher %ls is ready",launcherLatest);
        swprintf(detail,detail_size,L"Restart the launcher to finish. Your game files are not affected.");
        wcsncpy(button,L"Restart launcher",button_size);title[title_size-1]=0;detail[detail_size-1]=0;button[button_size-1]=0;return;
    }
    if(pinned&&state==UPDATE_AVAILABLE&&!InterlockedCompareExchange(&updateAutoDownload,0,0)){
        swprintf(title,title_size,L"Staying on %ls",current);
        swprintf(detail,detail_size,L"%ls is available whenever you're ready  \x00B7  Versions lets you switch",updateLatest);
        wcsncpy(button,L"Update now",button_size);title[title_size-1]=0;detail[detail_size-1]=0;button[button_size-1]=0;return;
    }
    switch(state){
    case UPDATE_OFF:swprintf(title,title_size,L"Game %ls",current);swprintf(detail,detail_size,L"Launcher %ls  \x00B7  automatic updates are not set up for this copy",PLATINUM_LAUNCHER_VERSION);wcsncpy(button,L"Updates off",button_size);break;
    case UPDATE_IDLE:swprintf(title,title_size,L"Game %ls",current);swprintf(detail,detail_size,L"Launcher %ls",PLATINUM_LAUNCHER_VERSION);wcsncpy(button,L"Check for updates",button_size);break;
    case UPDATE_CHECKING:swprintf(title,title_size,L"Checking for updates...");swprintf(detail,detail_size,L"Game %ls  \x00B7  Launcher %ls",current,PLATINUM_LAUNCHER_VERSION);wcsncpy(button,L"Checking...",button_size);break;
    case UPDATE_CURRENT:swprintf(title,title_size,pinned?L"Staying on %ls":L"You're up to date",current);
        {LONG launcher=InterlockedCompareExchange(&launcherUpdateState,0,0);
         if(launcher==LAUNCHER_DOWNLOADING)swprintf(detail,detail_size,L"Game %ls  \x00B7  updating the launcher to %ls...",current,launcherLatest);
         else if(launcherJustUpdated)swprintf(detail,detail_size,L"Game %ls  \x00B7  Launcher %ls, just updated",current,PLATINUM_LAUNCHER_VERSION);
         else swprintf(detail,detail_size,pinned?L"You chose this version in Versions  \x00B7  Launcher %ls":L"Game %ls  \x00B7  Launcher %ls",pinned?PLATINUM_LAUNCHER_VERSION:current,PLATINUM_LAUNCHER_VERSION);}
        wcsncpy(button,L"Check again",button_size);break;
    case UPDATE_AVAILABLE:swprintf(title,title_size,updateSwitching?L"Switch to %ls":L"Update available: %ls",updateLatest);
        if(deltaReady)swprintf(detail,detail_size,L"%ls  \x00B7  %.0f MB, only the changed files",updateNotes[0]?updateNotes:L"Your settings are kept",updateTotal/1048576.0);
        else if(updateNotes[0])swprintf(detail,detail_size,L"%ls  \x00B7  %.0f MB",updateNotes,updateTotal/1048576.0);
        else swprintf(detail,detail_size,L"%.0f MB download  \x00B7  your settings are kept",updateTotal/1048576.0);
        wcsncpy(button,L"Update now",button_size);break;
    case UPDATE_DOWNLOADING:
        {LONG64 total=updatePreview>=0?100:updateTotal,done=updatePreview>=0?62:updateDone;int percent=total>0?(int)(100.0*(double)done/(double)total):0;if(percent>100)percent=100;
         if(InterlockedCompareExchange(&updateHdOnly,0,0))swprintf(title,title_size,tr(L"Downloading HD textures  \x00B7  %d%%"),percent);
         else swprintf(title,title_size,L"Downloading %ls  \x00B7  %d%%",updateLatest,percent);}
        {
            double done=updateDone/1048576.0,total=updateTotal/1048576.0,seconds=updatePreview>=0?40.0:(GetTickCount()-updateStartTick)/1000.0;
            double rate=seconds>0.5?done/seconds:0;
            if(updatePreview>=0)rate=12.6;
            if(rate>0.05){double left=(total-done)/rate;
                if(left>=90)swprintf(detail,detail_size,L"%.0f of %.0f MB  \x00B7  %.1f MB/s  \x00B7  about %.0f min left",done,total,rate,left/60+0.5);
                else swprintf(detail,detail_size,L"%.0f of %.0f MB  \x00B7  %.1f MB/s  \x00B7  about %.0f s left",done,total,rate,left<1?1:left);}
            else swprintf(detail,detail_size,L"%.0f of %.0f MB",done,total);
        }
        wcsncpy(button,L"Cancel",button_size);break;
    case UPDATE_VERIFYING:swprintf(title,title_size,L"Checking and unpacking %ls",updateLatest);wcsncpy(button,L"Please wait...",button_size);break;
    case UPDATE_READY:swprintf(title,title_size,updateSwitching?L"%ls is ready":L"%ls is ready to install",updateLatest);swprintf(detail,detail_size,L"The launcher restarts once. Your settings and profile are kept.");wcsncpy(button,L"Restart to update",button_size);break;
    default:swprintf(title,title_size,L"Update problem");wcsncpy(detail,updateError[0]?updateError:L"Something went wrong.",detail_size);wcsncpy(button,updateRepairOnRetry?L"Repair":L"Try again",button_size);break;
    }
    title[title_size-1]=0;detail[detail_size-1]=0;button[button_size-1]=0;
}
static LONG update_visible_state(void){return updatePreview>=0?updatePreview:InterlockedCompareExchange(&updateState,0,0);}
static volatile LONG updateUserAction;   /* 2.6.2: the player started this; a failure is then said in a message, once */
static void update_sync(HWND window){
    wchar_t title[160],detail[260],label[40];update_describe(title,160,detail,260,label,40);
    HWND button=GetDlgItem(window,117);LONG state=update_visible_state();
    if(state==UPDATE_CURRENT||state==UPDATE_READY)InterlockedExchange(&updateUserAction,0);
    if(state==UPDATE_FAILED&&updatePreview<0&&!updateHeadless&&InterlockedExchange(&updateUserAction,0)){
        wchar_t message[600];swprintf(message,600,tr(L"%ls\n\nDetails are in updates\\launcher-update.log in the game folder."),updateError[0]?updateError:L"Something went wrong.");
        MessageBoxW(window,message,L"Update problem",MB_OK|MB_ICONWARNING);
    }
    if(button){SetWindowTextW(button,label);EnableWindow(button,state!=UPDATE_OFF&&state!=UPDATE_CHECKING&&state!=UPDATE_VERIFYING);InvalidateRect(button,NULL,FALSE);}
    HWND self=GetDlgItem(window,127);
    if(self){LONG launcher=InterlockedCompareExchange(&launcherUpdateState,0,0);int manual=InterlockedCompareExchange(&launcherManualCheck,0,0);
        const wchar_t *text=launcher==LAUNCHER_CHECKING?L"Checking...":launcher==LAUNCHER_DOWNLOADING?L"Updating...":launcher==LAUNCHER_READY?L"Restart launcher":
                            manual&&launcher==LAUNCHER_CURRENT?L"Launcher up to date":launcher_update_offered()?L"Update launcher":L"Launcher update";
        SetWindowTextW(self,text);EnableWindow(self,updateLatestFeed[0]&&updatePreview<0&&launcher!=LAUNCHER_CHECKING&&launcher!=LAUNCHER_DOWNLOADING);InvalidateRect(self,NULL,FALSE);
        /* A failure of a check the player asked for is said once, in words. */
        if(manual&&launcher==LAUNCHER_FAILED&&!updateHeadless){InterlockedExchange(&launcherManualCheck,0);MessageBoxW(window,launcherError,L"Launcher update",MB_OK|MB_ICONWARNING);}
    }
    HWND notes=GetDlgItem(window,118);
    /* 0.37.1: the legacy "What's new" child button stays hidden. Settings > Updates > Patch notes is a painted
     * row that sends the same command (118); shown on every page, the child sat on the navigation rail over the
     * Support button (the "WHAT'S NEW" pill on the Play page since launcher 2.1.0). */
    if(notes){ShowWindow(notes,SW_HIDE);(void)state;}
    InvalidateRect(window,NULL,FALSE);
}
static void update_open_page(void){
    if(updatePage[0]&&!_wcsnicmp(updatePage,L"https://",8))ShellExecuteW(NULL,L"open",updatePage,NULL,NULL,SW_SHOWNORMAL);
}
static void update_set_pin(const wchar_t *version);
/* Button 127: check for a newer launcher, or restart into one that is ready. */
static void launcher_button(HWND window){
    if(updatePreview>=0)return;
    LONG launcher=InterlockedCompareExchange(&launcherUpdateState,0,0);
    if(launcher==LAUNCHER_READY){launcher_restart(window);return;}
    launcher_check_begin();
}
/* Button 117 */
static void update_button(HWND window){
    LONG state=update_visible_state();
    if(updatePreview>=0)return;
    if(launcher_strip_active(state)){launcher_restart(window);return;}
    InterlockedExchange(&updateUserAction,1);
    if(state==UPDATE_AVAILABLE){
        /* Choosing Update now while staying on a version ends that choice. */
        if(!updateSwitching&&updatePinned[0])update_set_pin(L"");
        update_start(update_download_worker);return;}
    if(state==UPDATE_DOWNLOADING){InterlockedExchange(&updateCancel,1);return;}
    if(state==UPDATE_READY){update_apply(window);return;}
    if(state==UPDATE_FAILED&&updateRepairOnRetry){updateRepairOnRetry=0;if(update_repair_begin())return;}
    if(state==UPDATE_IDLE||state==UPDATE_CURRENT||state==UPDATE_FAILED)update_begin_check();
}
/* ---- Version choice ----
   The release list comes from the public GitHub API for the repository behind
   the official feed. It is only a menu: whatever the player picks is installed
   from that release's own signed update.txt, so a tampered list cannot install
   anything that Team Terminus did not sign. */
typedef struct {wchar_t version[64],date[40];} UpdateRelease;
#define UPDATE_RELEASES_MAX 40
static UpdateRelease updateReleases[UPDATE_RELEASES_MAX];
static volatile LONG updateReleaseCount,updateReleaseState; /* 0 idle, 1 loading, 2 ready, 3 failed */
static HWND updateReleaseWindow;
#define WM_PLATINUM_RELEASES (WM_APP+11)
static int update_releases_url(wchar_t *out,int capacity){
    const wchar_t *prefix=L"https://github.com/";size_t n=wcslen(prefix);
    if(_wcsnicmp(updateLatestFeed,prefix,n))return 0;
    const wchar_t *owner=updateLatestFeed+n,*slash=wcschr(owner,L'/');if(!slash)return 0;
    const wchar_t *repo=slash+1,*end=wcschr(repo,L'/');if(!end||end-owner>200)return 0;
    swprintf(out,capacity,L"https://api.github.com/repos/%.*ls/releases?per_page=%d",(int)(end-owner),owner,UPDATE_RELEASES_MAX);return 1;
}
static const char *update_json_string(const char *at,const char *limit,const char *key,char *out,int capacity){
    out[0]=0;char needle[48];snprintf(needle,48,"\"%s\"",key);
    const char *p=strstr(at,needle);if(!p||(limit&&p>=limit))return NULL;
    p+=strlen(needle);while(*p==' '||*p=='\t'||*p=='\r'||*p=='\n')++p;if(*p!=':')return NULL;++p;
    while(*p==' '||*p=='\t'||*p=='\r'||*p=='\n')++p;if(*p!='"')return NULL;++p;
    int i=0;while(*p&&*p!='"'&&i<capacity-1){if(*p=='\\'&&p[1])++p;out[i++]=*p++;}out[i]=0;return p;
}
static void update_format_date(const char *iso,wchar_t *out,int capacity){
    static const wchar_t *months[]={L"Jan",L"Feb",L"Mar",L"Apr",L"May",L"Jun",L"Jul",L"Aug",L"Sep",L"Oct",L"Nov",L"Dec"};
    int y=0,m=0,d=0;out[0]=0;if(sscanf(iso,"%d-%d-%d",&y,&m,&d)==3&&m>=1&&m<=12)swprintf(out,capacity,L"%d %ls %d",d,months[m-1],y);
}
static DWORD WINAPI update_releases_worker(LPVOID unused){
    (void)unused;wchar_t url[600];LONG count=0;
    DeltaBuffer buffer={NULL,0,16u<<20};buffer.text=(char*)malloc(buffer.capacity);   /* 0.37.1: ~250 KB per release with per-file assets */
    if(buffer.text&&update_releases_url(url,600)&&!update_http_quiet(url,update_delta_sink,&buffer,buffer.capacity-1)){
        buffer.text[buffer.length]=0;
        for(const char *at=strstr(buffer.text,"\"tag_name\"");at&&count<UPDATE_RELEASES_MAX;){
            const char *next=strstr(at+10,"\"tag_name\"");
            char tag[80],published[40];
            update_json_string(at,next,"tag_name",tag,80);
            /* the segment of one release runs to the next tag_name */
            size_t seg=next?(size_t)(next-at):strlen(at);
            char *copy=(char*)malloc(seg+1);
            if(copy){memcpy(copy,at,seg);copy[seg]=0;
                int draft=strstr(copy,"\"draft\":true")||strstr(copy,"\"draft\": true");
                int signedFeed=strstr(copy,"/update.txt\"")!=NULL;
                update_json_string(copy,NULL,"published_at",published,40);
                const char *v=tag[0]=='v'?tag+1:tag;
                if(!draft&&signedFeed&&v[0]>='0'&&v[0]<='9'&&strlen(v)<60&&!strpbrk(v,"/\\?#% ")){
                    UpdateRelease *r=&updateReleases[count++];
                    MultiByteToWideChar(CP_UTF8,0,v,-1,r->version,64);update_format_date(published,r->date,40);
                }
                free(copy);}
            at=next;
        }
    }
    free(buffer.text);
    InterlockedExchange(&updateReleaseCount,count);
    InterlockedExchange(&updateReleaseState,count>0?2:3);
    if(updateReleaseWindow)PostMessageW(updateReleaseWindow,WM_PLATINUM_RELEASES,0,0);
    return 0;
}
static void update_load_releases(void){
    if(InterlockedCompareExchange(&updateReleaseState,1,1)==1)return;
    InterlockedExchange(&updateReleaseState,1);update_start(update_releases_worker);
}
static void update_set_pin(const wchar_t *version){
    wchar_t ini_path[2300];swprintf(ini_path,2300,L"%ls\\update.ini",root);
    WritePrivateProfileStringW(L"Update",L"Pinned",version&&version[0]?version:NULL,ini_path);
    wcsncpy(updatePinned,version?version:L"",63);updatePinned[63]=0;
}
/* Install another release (older or newer). latest: the newest entry of the list. */
static int update_switch_to(const wchar_t *version,int latest){
    LONG state=InterlockedCompareExchange(&updateState,0,0);
    if(state==UPDATE_DOWNLOADING||state==UPDATE_VERIFYING||state==UPDATE_CHECKING)return 0;
    wchar_t feed[1024];
    if(latest)wcscpy(feed,updateLatestFeed);else if(!update_tag_feed(version,feed,1024))return 0;
    wcscpy(updateFeed,feed);wcsncpy(updateTarget,version,63);updateTarget[63]=0;updateSwitching=1;
    update_set_pin(latest?L"":version);
    InterlockedExchange(&updateAutoDownload,1);update_begin_check();return 1;
}
static int game_missing(void);
/* Settings > Updates > Verify and repair: the installed release, from its own signed feed. */
static int update_repair_ready(void){
    LONG state=update_visible_state();
    return updatePreview<0&&updateCurrent[0]&&updateLatestFeed[0]&&
           state!=UPDATE_DOWNLOADING&&state!=UPDATE_VERIFYING&&state!=UPDATE_CHECKING&&state!=UPDATE_READY;
}
static int update_repair_begin(void){
    if(!update_repair_ready())return 0;
    wchar_t feed[1024];
    if(updateLatest[0]&&!wcscmp(updateLatest,updateCurrent))wcscpy(feed,updateLatestFeed);
    else if(!update_tag_feed(updateCurrent,feed,1024))return 0;
    wcscpy(updateFeed,feed);wcsncpy(updateTarget,updateCurrent,63);updateTarget[63]=0;
    updateSwitching=1;updateRepair=1;updateRepairNote[0]=0;
    InterlockedExchange(&updateAutoDownload,1);update_begin_check();return 1;
}
