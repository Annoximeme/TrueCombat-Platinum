#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#ifndef PLATINUM_NATIVE
#define PLATINUM_NATIVE 0
#endif
#define PLATINUM_PORT (PLATINUM_NATIVE?27971:27960)
#define PLATINUM_HOST_NAME L"TrueCombat: Platinum Server"
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <bcrypt.h>
#include <shellapi.h>
#include <wchar.h>
#include <stdio.h>
#include <string.h>
#include <objidl.h>
#include <shlwapi.h>
#include <dwmapi.h>
#include <dxgi.h>
#include "platinum_banner.h"
#include "platinum_graphics_report.h"
#include "platinum_launcher_version.h"
#include "platinum_tokens.h"   /* shared design tokens (0.37.0) */

/* GDI+ flat API: PNG decoding is provided by Windows, not a shipped runtime. */
typedef struct { UINT32 version; void *debug_callback; BOOL suppress_thread,suppress_codecs; } PlatinumGdiStartup;
__declspec(dllimport) int WINAPI GdiplusStartup(ULONG_PTR*,const PlatinumGdiStartup*,void*);
__declspec(dllimport) void WINAPI GdiplusShutdown(ULONG_PTR);
__declspec(dllimport) int WINAPI GdipLoadImageFromStream(IStream*,void**);
__declspec(dllimport) int WINAPI GdipDisposeImage(void*);
__declspec(dllimport) int WINAPI GdipCreateBitmapFromHBITMAP(HBITMAP,HPALETTE,void**);
__declspec(dllimport) int WINAPI GdipSaveImageToFile(void*,const wchar_t*,const CLSID*,const void*);
__declspec(dllimport) int WINAPI GdipCreateFromHDC(HDC,void**);
__declspec(dllimport) int WINAPI GdipDeleteGraphics(void*);
__declspec(dllimport) int WINAPI GdipSetInterpolationMode(void*,int);
__declspec(dllimport) int WINAPI GdipDrawImageRectI(void*,void*,int,int,int,int);
#define BANNER_HEIGHT 267
#define LAUNCHER_HEADER_HEIGHT 183

static const wchar_t *TITLE=L"TrueCombat: Platinum";
static void error(const wchar_t *message);
static void account_paint_lfs(HDC dc);static void account_paint_profile(HDC dc);static int account_page_click(HWND window,int arg); /* 0.37.0 accounts, platinum_account.h */
static wchar_t root[2048], ini[2200];
static HWND server_edit,name_edit,preset_combo,resolution_combo,display_combo,vsync_check,preset_description;
static HBRUSH background_brush,field_brush;
static int forced_preset=-1,forced_resolution=-1,forced_display=-1;
static int forced_texture=-1,forced_filter=-1,forced_aa=-1,forced_brightness=-1;
static int forced_refresh=-1,advanced_refresh;
static int forced_compression=-1,advanced_compression;
static int forced_overlay=-1,advanced_overlay;
static int advanced_effects;   /* 0 follow preset, 1 off */
static int advanced_framegen,forced_framegen=-1; /* DLSS Frame Generation: 0 off (default), 1 on; opt-in, never part of a preset */
static int advanced_texture,advanced_filter,advanced_aa,advanced_brightness,safe_launch,graphics_options;
static HWND advanced_window;
static HWND report_window;
static wchar_t report_text[8192];
static int report_only,graphics_info;
static wchar_t capture_ui_path[2200];
static int captureWidth,captureHeight; /* --capture-size WxH: offscreen shots at any window size */
static int compact_ui,verify_chrome;
static void open_graphics_report(HWND parent);
static const int resolutions[][2]={{0,0},{1280,720},{1600,900},{1920,1080},{2560,1440},{1920,1200},{1024,768},{3840,2160}};
static HFONT font;
static HFONT logo_font,platinum_font;
static ULONG_PTR image_token;
static IStream *banner_stream;
static void *banner_image;
static HANDLE starting_game;
static DWORD starting_pid,starting_tick;
static int loading,banner_preview;
static int auto_run,no_sound,menu_launch,wait_game,stop_only,native_stop_pending,verify_stop_ui;
static unsigned native_stop_ui_ticks;
static wchar_t local_map[32];
static int practice_mode; /* 1 practice with bots: offline team deathmatch against bots; 2 firing range (0.38.0): no bots, still targets */
static wchar_t profile_demo_play[300]; /* Profile & demos: play this demo on the next launch */
static int start_in_tray;
static int save_only,process_result,initial_tab,controls_open,versions_open,install_now,switch_latest;
static wchar_t switch_version[64],list_versions_path[2200],version_file_path[2200];
static int launcher_update_test,launcher_preview;
/* Keeps the version marker in the EXE for tooling and the self-updater. */
__attribute__((used)) static const wchar_t launcher_marker[]=PLATINUM_LAUNCHER_MARKER;
static wchar_t forced_server[256], forced_name[64], forced_config[128];
static unsigned server_port=PLATINUM_PORT;
static wchar_t server_bind[64]=L"0.0.0.0";
#include "platinum_options.h"
#include "platinum_lang.h"
#include "platinum_session.h"
#include "platinum_join.h"
#include <wctype.h>
#include "platinum_update.h"
#include "platinum_shortcut.h" /* 0.37.1 desktop / Start menu shortcut care */
#include "platinum_instance.h" /* 0.37.1 one launcher per install */
#include "platinum_ranked.h"
#include "platinum_shell.h"
#include "platinum_binds.h"
#include "platinum_firstrun.h"
#include "platinum_crash.h"
#include "platinum_report.h"
#include "platinum_telemetry.h" /* 2.6.0 anonymous crash and hardware reports, only when the player chose to share */
#include <time.h>
#include "platinum_presence.h"
#include "platinum_eac.h"

static void paint_banner(HDC dc,int width,int height) {
    if(banner_image){
        RECT background={0,0,width,height};FillRect(dc,&background,background_brush);
        void *graphics=NULL;
        if(GdipCreateFromHDC(dc,&graphics)==0){
            GdipSetInterpolationMode(graphics,7);
            /* The supplied image is 1672 x 941; fit all of it without distortion. */
            int w=width,h=(int)((long long)width*941/1672);
            if(h>height){h=height;w=(int)((long long)height*1672/941);}
            GdipDrawImageRectI(graphics,banner_image,(width-w)/2,(height-h)/2,w,h);
            GdipDeleteGraphics(graphics);return;
        }
    }
    RECT rect={0,0,width,height};
    for(int y=0;y<height;y++){
        int shade=18+(height-y)*12/height;
        HBRUSH brush=CreateSolidBrush(RGB(shade,shade+3,shade+7));
        RECT line={0,y,width,y+1};FillRect(dc,&line,brush);DeleteObject(brush);
    }
    HPEN edge=CreatePen(PS_SOLID,1,RGB(97,111,121));HGDIOBJ old_pen=SelectObject(dc,edge);
    MoveToEx(dc,24,height-17,NULL);LineTo(dc,width-24,height-17);
    MoveToEx(dc,24,20,NULL);LineTo(dc,55,20);LineTo(dc,55,23);
    MoveToEx(dc,width-24,20,NULL);LineTo(dc,width-55,20);LineTo(dc,width-55,23);
    SelectObject(dc,old_pen);DeleteObject(edge);
    SetBkMode(dc,TRANSPARENT);HGDIOBJ old_font=SelectObject(dc,logo_font);
    SetTextColor(dc,RGB(237,241,243));rect=(RECT){20,21,width-20,63};
    DrawTextW(dc,L"TRUECOMBAT:",-1,&rect,DT_CENTER|DT_SINGLELINE|DT_VCENTER);
    SelectObject(dc,platinum_font);SetTextColor(dc,RGB(174,192,204));
    rect=(RECT){20,65,width-20,99};DrawTextW(dc,L"P L A T I N U M",-1,&rect,DT_CENTER|DT_SINGLELINE|DT_VCENTER);
    SelectObject(dc,old_font);
}

static BOOL CALLBACK find_game_window(HWND window,LPARAM found) {
    DWORD pid=0;GetWindowThreadProcessId(window,&pid);
    if(pid==starting_pid && IsWindowVisible(window) && !GetWindow(window,GW_OWNER)){
        *(int*)found=1;return FALSE;
    }return TRUE;
}

static BOOL CALLBACK hide_control(HWND child,LPARAM unused){(void)unused;ShowWindow(child,SW_HIDE);return TRUE;}

static RECT loadingRestore;
static void show_loading(HWND window) {
    GetWindowRect(window,&loadingRestore);
    loading=1;starting_tick=GetTickCount();EnumChildWindows(window,hide_control,0);
    for(int i=0;i<3;++i)ShowWindow(shellCaptionButtons[i],SW_SHOW);
    SetWindowPos(window,NULL,0,0,474,BANNER_HEIGHT+75+shell_caption_height(),SWP_NOMOVE|SWP_NOZORDER|SWP_NOACTIVATE);
    shell_caption_layout(window);
    InvalidateRect(window,NULL,TRUE);UpdateWindow(window);
    if(!banner_preview)SetTimer(window,1,100,NULL);
}

static int server_responds(unsigned port) {
    SOCKET sock=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);if(sock==INVALID_SOCKET)return 0;
    DWORD timeout=800;setsockopt(sock,SOL_SOCKET,SO_RCVTIMEO,(const char*)&timeout,sizeof(timeout));
    struct sockaddr_in address={0};address.sin_family=AF_INET;address.sin_port=htons((u_short)port);
    /* Wildcard listeners accept loopback; address-bound listeners must be probed there. */
    const wchar_t *probe=!wcscmp(server_bind,L"0.0.0.0")?L"127.0.0.1":server_bind;
    if(InetPtonW(AF_INET,probe,&address.sin_addr)!=1){closesocket(sock);return 0;}
    unsigned char request[]={255,255,255,255,'g','e','t','s','t','a','t','u','s','\n'};
    char reply[8192];int ok=0;
    if(connect(sock,(struct sockaddr*)&address,sizeof(address))==0 && send(sock,(const char*)request,sizeof(request),0)>0){
        int received=recv(sock,reply,sizeof(reply),0);ok=received>18 && !memcmp(reply,"\xff\xff\xff\xffstatusResponse",18);
    }
    closesocket(sock);return ok;
}

#include "platinum_native_host.h"

static int run_supervised_server(void) {
    wchar_t mutex_name[80], engine[2200],home[2200],dir[2300],private_cfg[2400],cmd[8192],secret[65];
    swprintf(mutex_name,80,L"Local\\TrueCombatPlatinumServer-%u",server_port);
    HANDLE mutex=CreateMutexW(NULL,TRUE,mutex_name);
    if(!mutex || GetLastError()==ERROR_ALREADY_EXISTS){if(mutex)CloseHandle(mutex);return 3;}
    WSADATA ws;if(WSAStartup(MAKEWORD(2,2),&ws)){CloseHandle(mutex);return 7;}
    SOCKET check=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    struct sockaddr_in address={0};address.sin_family=AF_INET;address.sin_port=htons((u_short)server_port);
    InetPtonW(AF_INET,server_bind,&address.sin_addr);
    BOOL exclusive=TRUE;setsockopt(check,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,(const char*)&exclusive,sizeof(exclusive));
    int available=check!=INVALID_SOCKET && bind(check,(struct sockaddr*)&address,sizeof(address))==0;
    if(check!=INVALID_SOCKET)closesocket(check);
    if(!available){CloseHandle(mutex);WSACleanup();return 8;}
    swprintf(engine,2200,L"%ls\\server\\platinum-server.bin",root);
    swprintf(home,2200,L"%ls\\server-state",root);CreateDirectoryW(home,NULL);
    swprintf(dir,2300,L"%ls\\tcetest",home);CreateDirectoryW(dir,NULL);
    swprintf(private_cfg,2400,L"%ls\\platinum-private.cfg",dir);
    FILE *file=_wfopen(private_cfg,L"r");int valid=0;
    if(file){char line[160];if(fgets(line,sizeof(line),file)){
        char hex[65]={0};if(sscanf(line,"set rconPassword \"%64[0-9a-f]\"",hex)==1 && strlen(hex)==64){
            for(int i=0;i<64;i++)secret[i]=(wchar_t)hex[i];secret[64]=0;valid=1;}}
        fclose(file);}
    if(!valid){
        unsigned char random[32];if(BCryptGenRandom(NULL,random,32,BCRYPT_USE_SYSTEM_PREFERRED_RNG)!=0){CloseHandle(mutex);return 4;}
        const wchar_t *hex=L"0123456789abcdef";
        for(int i=0;i<32;i++){secret[2*i]=hex[random[i]>>4];secret[2*i+1]=hex[random[i]&15];}secret[64]=0;
        file=_wfopen(private_cfg,L"w");if(!file){CloseHandle(mutex);return 5;}
        fwprintf(file,L"set rconPassword \"%ls\"\n",secret);fclose(file);
    }
    wchar_t log_path[2300];swprintf(log_path,2300,L"%ls\\supervisor.log",home);
    {   /* appended on every server start and exit: keep one previous file past 1 MB */
        WIN32_FILE_ATTRIBUTE_DATA info;wchar_t previous[2310];swprintf(previous,2310,L"%ls.1",log_path);
        if(GetFileAttributesExW(log_path,GetFileExInfoStandard,&info)&&(info.nFileSizeHigh||info.nFileSizeLow>1048576))MoveFileExW(log_path,previous,MOVEFILE_REPLACE_EXISTING);
    }
    if(!write_host_config(dir)){CloseHandle(mutex);WSACleanup();return 9;}
    unsigned failures=0;DWORD last_code=0;
    if(PLATINUM_NATIVE)ranked_upload_start();
    for(;;){
        if(PLATINUM_NATIVE&&native_host_stopping()){last_code=0;break;}
        swprintf(cmd,8192,L"\"%ls\" +set dedicated 2 +set net_ip %ls +set net_port %u "
            L"+set fs_basepath \"%ls\" +set fs_homepath \"%ls\" +set fs_game tcetest "
            L"+set sv_punkbuster 0 +exec platinum-private.cfg %ls +exec platinum-host.cfg",engine,server_bind,server_port,root,home,
            PLATINUM_NATIVE?L"+set dedicated 1 +set net_port6 0 +set sv_pure 0":L"+exec platinum_server.cfg");
        wchar_t master_now[256];master_address(master_now,256);int public_now=(host_public_forced>=0?host_public_forced:host_public)&&master_now[0];
        if(PLATINUM_NATIVE)swprintf(cmd,8192,L"\"%ls\" +set dedicated %d +set net_ip %ls +set net_port %u "
            L"+set net_port6 0 +set net_enabled 1 +set fs_basepath . +set fs_homepath server-state +set fs_game tcetest "
            L"+set sv_pure 0 +set logfile 1 +set com_recommendedSet 1 +exec platinum-private.cfg +exec platinum-host.cfg",engine,public_now?2:1,server_bind,server_port);
        STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);si.dwFlags=STARTF_USESHOWWINDOW;si.wShowWindow=SW_HIDE;
        if(!CreateProcessW(engine,cmd,NULL,NULL,FALSE,CREATE_NO_WINDOW|(PLATINUM_NATIVE?CREATE_SUSPENDED:0),NULL,root,&si,&pi)){
            file=_wfopen(log_path,L"a");if(file){fwprintf(file,L"Server start failed: Windows error %lu\n",GetLastError());fclose(file);}CloseHandle(mutex);return 6;}
        if(PLATINUM_NATIVE&&!native_host_adopt(&pi)){
            TerminateProcess(pi.hProcess,11);WaitForSingleObject(pi.hProcess,5000);
            CloseHandle(pi.hThread);CloseHandle(pi.hProcess);CloseHandle(mutex);WSACleanup();return 11;
        }
        file=_wfopen(log_path,L"a");if(file){fwprintf(file,L"Server PID %lu started on UDP %u (thread %lu)\n",pi.dwProcessId,server_port,pi.dwThreadId);fclose(file);}
        DWORD started=GetTickCount(),next_probe=60000;unsigned misses=0;CloseHandle(pi.hThread);
        for(;;){
            HANDLE waits[]={pi.hProcess,nativeHostStop};
            DWORD result=PLATINUM_NATIVE?WaitForMultipleObjects(2,waits,FALSE,5000):WaitForSingleObject(pi.hProcess,5000);
            if(PLATINUM_NATIVE&&result==WAIT_OBJECT_0+1){native_host_stop_child(pi.hProcess,pi.dwProcessId);break;}
            if(result!=WAIT_TIMEOUT)break;
            DWORD elapsed=GetTickCount()-started;
            if(elapsed>=next_probe){
                next_probe=elapsed+15000;
                if(server_responds(server_port))misses=0;
                else if(++misses>=3){TerminateProcess(pi.hProcess,98);WaitForSingleObject(pi.hProcess,5000);break;}
            }
        }
        DWORD code=0;GetExitCodeProcess(pi.hProcess,&code);CloseHandle(pi.hProcess);
        file=_wfopen(log_path,L"a");if(file){fwprintf(file,L"Server PID %lu exited %lu after %lu ms\n",pi.dwProcessId,code,GetTickCount()-started);fclose(file);}
        last_code=code;
        if(code==0||(PLATINUM_NATIVE&&native_host_stopping()))break;
        if(GetTickCount()-started>300000)failures=0;
        if(++failures>=5)break;
        if(PLATINUM_NATIVE){if(WaitForSingleObject(nativeHostStop,2000*failures)==WAIT_OBJECT_0){last_code=0;break;}}
        else Sleep(2000*failures);
    }
    if(PLATINUM_NATIVE)ranked_upload_stop();
    CloseHandle(mutex);WSACleanup();return PLATINUM_NATIVE?(int)last_code:0;
}
static int server_main(void){
    if(!PLATINUM_NATIVE)return run_supervised_server();
    int code=native_host_begin();
    if(!code)code=run_supervised_server();
    native_host_finish();return code;
}

static int start_host(HWND window) {
    wchar_t exe[2200],cmd[2500];GetModuleFileNameW(NULL,exe,2200);
    swprintf(cmd,2500,L"\"%ls\" --serve --server-port %u --server-bind %ls%ls%ls%ls",exe,server_port,server_bind,
        host_public_forced>=0?(host_public_forced?L" --host-public 1":L" --host-public 0"):L"",master_override[0]?L" --master ":L"",master_override);
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);si.dwFlags=STARTF_USESHOWWINDOW;si.wShowWindow=SW_HIDE;
    if(!CreateProcessW(exe,cmd,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,root,&si,&pi)){error(L"The server could not start.");return 0;}
    if(WaitForSingleObject(pi.hProcess,2000)==WAIT_OBJECT_0){ /* 0.37.1: was 500 ms, too short to see a port or mutex failure */DWORD code=0;GetExitCodeProcess(pi.hProcess,&code);CloseHandle(pi.hThread);CloseHandle(pi.hProcess);
        if(code==3)MessageBoxW(window,PLATINUM_NATIVE?L"This game folder is already hosting a server, or the selected UDP port is already managed. Stop it before starting another.":L"A server is already running on the selected UDP port.",TITLE,MB_OK);
        else error(L"The server could not start. The selected UDP port may be in use, or the server files may be missing.");return 0;}
    CloseHandle(pi.hThread);CloseHandle(pi.hProcess);wchar_t local[100],message[500];
    const wchar_t *address=!wcscmp(server_bind,L"0.0.0.0")?L"127.0.0.1":server_bind;
    swprintf(local,100,L"%ls:%u",address,server_port);SetWindowTextW(server_edit,local);
    swprintf(message,500,tr(L"Your native Windows server is starting on UDP %u.\n\nSelect Play to join locally. Other players need your server address and firewall/router forwarding for this port.\n\nHosting preferences apply on the next server start."),server_port);MessageBoxW(window,message,TITLE,MB_OK);return 1;
}

static DWORD WINAPI native_stop_worker(LPVOID target){
    int code=native_host_stop_local();
    PostMessageW((HWND)target,WM_APP+3,(WPARAM)code,0);return 0;
}
static int stop_host(HWND window) {
    if(PLATINUM_NATIVE){
        if(!window)return native_host_stop_local()==0;
        if(native_stop_pending)return 1;
        native_stop_pending=1;
        EnableWindow(GetDlgItem(window,105),FALSE);EnableWindow(GetDlgItem(window,106),FALSE);
        SetWindowTextW(GetDlgItem(window,106),L"Stopping...");
        HANDLE worker=CreateThread(NULL,0,native_stop_worker,window,0,NULL);
        if(worker){CloseHandle(worker);return 1;}
        native_stop_pending=0;
        EnableWindow(GetDlgItem(window,105),TRUE);EnableWindow(GetDlgItem(window,106),TRUE);
        SetWindowTextW(GetDlgItem(window,106),L"Stop server");
        error(L"The stop request could not start. Try again.");return 0;
    }
    wchar_t path[2400];swprintf(path,2400,L"%ls\\server-state\\tcetest\\platinum-private.cfg",root);
    FILE *file=_wfopen(path,L"r");char line[160],secret[65]={0};
    if(!file){error(L"No native server credentials were found in this folder.");return 0;}
    if(!fgets(line,sizeof(line),file)||sscanf(line,"set rconPassword \"%64[0-9a-f]\"",secret)!=1||strlen(secret)!=64){fclose(file);error(L"The local server credentials could not be read.");return 0;}fclose(file);
    WSADATA ws;if(WSAStartup(MAKEWORD(2,2),&ws))return 0;
    SOCKET sock=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    struct sockaddr_in address={0};address.sin_family=AF_INET;address.sin_port=htons((u_short)server_port);
    InetPtonW(AF_INET,!wcscmp(server_bind,L"0.0.0.0")?L"127.0.0.1":server_bind,&address.sin_addr);
    char packet[160];memset(packet,255,4);int count=snprintf(packet+4,sizeof(packet)-4,"rcon %s quit",secret);
    sendto(sock,packet,count+4,0,(struct sockaddr*)&address,sizeof(address));closesocket(sock);WSACleanup();
    if(window)MessageBoxW(window,L"A stop request was sent to the native server on this PC.",TITLE,MB_OK);
    return 1;
}

static void error(const wchar_t *message) { MessageBoxW(NULL,message,TITLE,MB_OK|MB_ICONERROR); }
/* [IPv6 literal] with an optional :port, e.g. [2a02:4780:83:c9f9::1]:27960 */
static int valid_server6(const wchar_t *s){
    if(s[0]!=L'[')return 0;
    const wchar_t *end=wcschr(s,L']');
    if(!end||end-s<3||end-s>46)return 0;
    int colons=0;for(const wchar_t *p=s+1;p<end;p++){if(*p==L':')colons++;else if(!iswxdigit(*p)&&*p!=L'.')return 0;}
    if(colons<2)return 0;
    if(!end[1])return 1;
    if(end[1]!=L':'||!end[2])return 0;
    unsigned port=0;for(const wchar_t *p=end+2;*p;p++){if(*p<L'0'||*p>L'9')return 0;port=port*10+(*p-L'0');if(port>65535)return 0;}
    return port!=0;
}
static int valid_server(const wchar_t *s) {
    if(s[0]==L'[')return valid_server6(s);
    size_t n=wcslen(s); if(!n || n>253) return 0;
    for(size_t i=0;i<n;i++) if(!((s[i]>=L'a'&&s[i]<=L'z')||(s[i]>=L'A'&&s[i]<=L'Z')||
        (s[i]>=L'0'&&s[i]<=L'9')||s[i]==L'.'||s[i]==L'-'||s[i]==L':'))return 0;
    const wchar_t *colon=wcschr(s,L':');
    if(colon) { if(wcschr(colon+1,L':') || !colon[1])return 0;
        unsigned port=0; for(const wchar_t *p=colon+1;*p;p++){if(*p<L'0'||*p>L'9')return 0;port=port*10+(*p-L'0');if(port>65535)return 0;}
        if(!port)return 0;
    }
    return s[0]!=L':' && s[0]!=L'.' && s[0]!=L'-';
}
/* 1-24 visible letters, numbers, spaces and _ - * ( ) . plus ^ colour codes (name colours; a name
   coloured in the game keeps its codes), at most 35 characters with the codes (ET MAX_NAME_LENGTH 36). */
static int valid_name(const wchar_t *s) {
    if(!*s || wcslen(s)>35)return 0;
    int visible=0,count=0;
    for(;*s;s++){
        if(s[0]==L'^'&&s[1]&&s[1]!=L'^'&&s[1]>L' '&&s[1]<0x7F&&s[1]!=L'"'&&s[1]!=L';'&&s[1]!=L'\\'){s++;continue;}
        if(!((*s>=L'a'&&*s<=L'z')||(*s>=L'A'&&*s<=L'Z')||(*s>=L'0'&&*s<=L'9')||
            *s==L' '||*s==L'_'||*s==L'-'||*s==L'*'||*s==L'('||*s==L')'||*s==L'.'))return 0;
        if(*s!=L' ')visible=1;
        if(++count>24)return 0;
    }
    return visible;
}
static void display_dimensions(int resolution,int *width,int *height){
    *width=resolutions[resolution][0];*height=resolutions[resolution][1];
    if(!*width){*width=GetSystemMetrics(SM_CXSCREEN);*height=GetSystemMetrics(SM_CYSCREEN);}
}
static int display_rates(int width,int height,int *rates){
    int count=1;rates[0]=0;
    for(DWORD i=0;;i++){
        DEVMODEW mode={0};mode.dmSize=sizeof(mode);
        if(!EnumDisplaySettingsW(NULL,i,&mode))break;
        int hz=(int)mode.dmDisplayFrequency;
        if((int)mode.dmPelsWidth!=width||(int)mode.dmPelsHeight!=height||mode.dmBitsPerPel<24||
           (mode.dmDisplayFlags&DM_INTERLACED)||hz<30||hz>480)continue;
        int found=0;for(int j=1;j<count;j++)if(rates[j]==hz){found=1;break;}
        if(!found&&count<128)rates[count++]=hz;
    }
    for(int i=1;i<count;i++)for(int j=i+1;j<count;j++)if(rates[j]<rates[i]){int t=rates[i];rates[i]=rates[j];rates[j]=t;}
    return count;
}
/* Presets: 0 Low (original look), 1 High (default), 2 Ultra (modern look). DX12 effect
   values come from the graphics thread's engine checks; OpenGL ignores the r_dx12 cvars.
   Ultra: AgX filmic tone mapping, eye adaptation, color grade, GTAO, DLAA or TAA (ULTRA_AA_POLICY
   below; with DLAA the renderer turns TAA off), softer bloom, sharpen 0.3,
   and surface materials (normal/roughness maps from zzz_hd_materials.pk3, highlights and
   reflection probes; without the pack the renderer draws the classic surfaces). */
typedef struct {int picmip,anis,samples;const wchar_t *filter;int hdr,ssao,tonemap,bloom,a2c,dlss;float bloomIntensity,sharpen;
    int taa,autoExposure,grade;float bloomThreshold;int materials,reflex,frameGen;
    int shadows,contactShadows,volumetrics,dynamicLights,flares,detailTextures,impacts;} GraphicsQuality;
/* Custom preset (Preset=3): every option on its own, in [Custom] of player.ini. The fields are all int so the
   table below can address them by index; CUSTOM_KEYS, custom_maximum and the dialog rows follow this order. */
typedef struct {int texture,filter,aa,sharpen,dynamicLights,flares,detailTextures,impacts,
    hdr,tonemap,ao,bloom,eyeAdaptation,grade,materials,shadows,contactShadows,volumetrics,foliage,reflex,frameGen;} CustomGraphics;
#define CUSTOM_FIELDS 21
static const wchar_t *const CUSTOM_KEYS[CUSTOM_FIELDS]={L"TextureDetail",L"Filtering",L"AntiAliasing",L"Sharpen",L"DynamicLights",
    L"LightFlares",L"DetailTextures",L"ImpactEffects",L"Hdr",L"ToneMapping",L"AmbientOcclusion",L"Bloom",L"EyeAdaptation",
    L"ColorGrade",L"Materials",L"SunShadows",L"ContactShadows",L"Volumetrics",L"FoliageSmoothing",L"Reflex",L"FrameGeneration"};
/* texture Full/Half/Quarter; filter Bilinear, Trilinear, 2x..16x anisotropic; aa Off, TAA, DLAA, 2x/4x/8x MSAA;
   tonemap Off, roll-off, filmic, AgX; ao Off, SSAO, GTAO; shadows Off, medium (2 x 1024), high (3 x 2048); reflex Off, On, Boost */
static const int custom_maximum[CUSTOM_FIELDS]={2,5,5,1,1,1,1,1,1,3,2,1,1,1,1,2,1,1,1,2,1};
static CustomGraphics custom_graphics,forced_custom;static int custom_saved,shown_preset=1,forced_custom_set;
static int *custom_field(CustomGraphics *c,int i){return &((int*)c)[i];}
/* Ultra's anti-aliasing: ONE rule. DLSS/DLAA costs about 1.2 GB of video memory at 1080p on top of everything
   else, so by default only cards with room for it use it:
     ULTRA_AA_POLICY 0  DLAA on an NVIDIA RTX card with at least ULTRA_DLAA_MIN_MB of dedicated video memory
                        (DXGI), otherwise TAA (default)
     ULTRA_AA_POLICY 1  TAA always
     ULTRA_AA_POLICY 2  DLAA always (the renderer falls back to TAA where DLSS can't run)
   Low and High never use either. */
#define ULTRA_AA_POLICY 0
#define ULTRA_DLAA_MIN_MB 11500 /* "12 GB" cards report a little under 12 GiB */
#define ULTRA_VOLUMETRICS 0 /* 1: Ultra also turns on the volumetric sun shafts (off: on hazy maps they read as distance fog) */
/* Dedicated video memory (MiB) of the adapter with the most, as the renderer picks it (DXGI); 0 if unknown. */
static unsigned long long ultra_video_memory_mb(void){
    static long long cached=-1;
    if(cached>=0)return (unsigned long long)cached;
    cached=0;
    typedef HRESULT (WINAPI *CreateFactory)(REFIID,void**);
    static const GUID iidFactory1={0x770aae78,0xf26f,0x4dba,{0xa8,0x29,0x25,0x3c,0x83,0xd1,0xb3,0x87}};
    HMODULE dxgi=LoadLibraryW(L"dxgi.dll");
    CreateFactory create=dxgi?(CreateFactory)(void*)GetProcAddress(dxgi,"CreateDXGIFactory1"):NULL;
    IDXGIFactory1 *factory=NULL;
    if(create&&SUCCEEDED(create(&iidFactory1,(void**)&factory))&&factory){
        IDXGIAdapter1 *adapter=NULL;
        for(UINT i=0;factory->lpVtbl->EnumAdapters1(factory,i,&adapter)!=DXGI_ERROR_NOT_FOUND;++i){
            DXGI_ADAPTER_DESC1 desc;
            if(SUCCEEDED(adapter->lpVtbl->GetDesc1(adapter,&desc))&&!(desc.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)&&
               (long long)(desc.DedicatedVideoMemory>>20)>cached)cached=(long long)(desc.DedicatedVideoMemory>>20);
            adapter->lpVtbl->Release(adapter);
        }
        factory->lpVtbl->Release(factory);
    }
    return (unsigned long long)cached;
}
static int gpu_detected,gpu_rtx_mb,gpu_frame_gen; /* dedicated MiB of an NVIDIA RTX adapter (0 otherwise); RTX 40 or newer */
static int gpu_name_has(const wchar_t *name,const wchar_t *series){
    /* "RTX 4060", "RTX 5090 Laptop GPU": the series digit followed by three more digits */
    for(const wchar_t *p=wcsstr(name,series);p;p=wcsstr(p+1,series)){const wchar_t *d=p+wcslen(series);
        if(d[0]>=L'0'&&d[0]<=L'9'&&d[1]>=L'0'&&d[1]<=L'9'&&d[2]>=L'0'&&d[2]<=L'9')return 1;}
    return 0;
}
static void detect_gpu(void){
    if(gpu_detected)return;
    gpu_detected=1;
    typedef HRESULT (WINAPI *CreateFactory)(REFIID,void**);
    static const GUID iidFactory1={0x770aae78,0xf26f,0x4dba,{0xa8,0x29,0x25,0x3c,0x83,0xd1,0xb3,0x87}};
    HMODULE dxgi=LoadLibraryW(L"dxgi.dll");
    CreateFactory create=dxgi?(CreateFactory)(void*)GetProcAddress(dxgi,"CreateDXGIFactory1"):NULL;
    IDXGIFactory1 *factory=NULL;
    if(create&&SUCCEEDED(create(&iidFactory1,(void**)&factory))&&factory){
        IDXGIAdapter1 *adapter=NULL,*best=NULL;DXGI_ADAPTER_DESC1 bestDesc;memset(&bestDesc,0,sizeof(bestDesc));
        for(UINT i=0;factory->lpVtbl->EnumAdapters1(factory,i,&adapter)!=DXGI_ERROR_NOT_FOUND;++i){
            DXGI_ADAPTER_DESC1 desc;
            if(SUCCEEDED(adapter->lpVtbl->GetDesc1(adapter,&desc))&&!(desc.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)&&
               desc.DedicatedVideoMemory>bestDesc.DedicatedVideoMemory){bestDesc=desc;best=adapter;}
            adapter->lpVtbl->Release(adapter);
        }
        (void)best; /* the renderer also takes the adapter with the most dedicated memory */
        if(bestDesc.VendorId==0x10DE&&wcsstr(bestDesc.Description,L"RTX")!=NULL){
            gpu_rtx_mb=(int)(bestDesc.DedicatedVideoMemory>>20);if(!gpu_rtx_mb)gpu_rtx_mb=1;
            /* Frame Generation: GeForce RTX 40/50 (Ada, Blackwell) and the Ada/Blackwell workstation cards. The
               renderer makes the final call through Streamline and stays at one frame where it can't run. */
            gpu_frame_gen=wcsstr(bestDesc.Description,L"Quadro")==NULL&&(gpu_name_has(bestDesc.Description,L"RTX 4")||
                gpu_name_has(bestDesc.Description,L"RTX 5")||wcsstr(bestDesc.Description,L" Ada")||wcsstr(bestDesc.Description,L"RTX PRO"));
        }
        factory->lpVtbl->Release(factory);
    }
}
static int ultra_uses_dlaa(void){
    if(ULTRA_AA_POLICY!=0)return ULTRA_AA_POLICY==2;
    detect_gpu();
    return gpu_rtx_mb>=ULTRA_DLAA_MIN_MB;
}
/* Frame Generation is offered only where DLSS/DLAA runs: DX12 (never Safe Start), the Ultra preset with DLAA,
   DirectX 12 effects on, and an RTX 40 or newer card. It adds a little latency, so it is opt-in and no preset turns it on. */
static int frame_gen_hardware(void){detect_gpu();return gpu_frame_gen&&ultra_uses_dlaa();}
static int frame_gen_possible(int preset,int effects){return preset==2&&effects!=1&&frame_gen_hardware();}
/* A custom set as the cvars it writes. Dependencies the renderer would ignore anyway are cleared here, so the
   game, the summary and the in-game page agree: sun/contact shadows and volumetrics need TAA or DLAA, eye
   adaptation needs HDR, Frame Generation needs DLAA on an RTX 40 or newer card and brings Reflex with it. */
static GraphicsQuality custom_quality(const CustomGraphics *c){
    GraphicsQuality q;memset(&q,0,sizeof(q));
    const int anis[]={0,0,2,4,8,16};
    q.picmip=c->texture;q.anis=anis[c->filter];q.filter=c->filter?L"GL_LINEAR_MIPMAP_LINEAR":L"GL_LINEAR_MIPMAP_NEAREST";
    q.samples=c->aa>=3?2<<(c->aa-3):0;q.taa=c->aa==1||c->aa==2;q.dlss=c->aa==2;
    q.hdr=c->hdr;q.tonemap=c->tonemap;q.ssao=c->ao==2?3:c->ao;q.bloom=c->bloom;
    q.bloomIntensity=c->bloom?(c->tonemap==3?0.2f:0.25f):0;q.bloomThreshold=c->tonemap==3?0.8f:0.75f;
    q.sharpen=c->sharpen?0.3f:0;q.a2c=c->foliage;q.autoExposure=c->eyeAdaptation&&c->hdr;q.grade=c->grade;q.materials=c->materials;
    q.shadows=q.taa?c->shadows:0;q.contactShadows=q.shadows?c->contactShadows:0;q.volumetrics=q.taa?c->volumetrics:0;
    q.reflex=c->reflex;q.frameGen=c->frameGen&&q.dlss&&frame_gen_hardware();if(q.frameGen&&!q.reflex)q.reflex=1;
    q.dynamicLights=c->dynamicLights;q.flares=c->flares;q.detailTextures=c->detailTextures;q.impacts=c->impacts;
    return q;
}
/* The other way round: what a preset (or the game's saved cvars) looks like as a custom set. */
static CustomGraphics quality_custom(const GraphicsQuality *q){
    CustomGraphics c;memset(&c,0,sizeof(c));
    c.texture=q->picmip<0?0:q->picmip>2?2:q->picmip;
    c.filter=q->anis>=16?5:q->anis>=8?4:q->anis>=4?3:q->anis>=2?2:(q->filter&&!wcscmp(q->filter,L"GL_LINEAR_MIPMAP_NEAREST"))?0:1;
    c.aa=q->samples>=8?5:q->samples>=4?4:q->samples>=2?3:q->dlss?2:q->taa?1:0;
    c.sharpen=q->sharpen>0.001f;c.hdr=q->hdr!=0;c.tonemap=q->tonemap<0?0:q->tonemap>3?3:q->tonemap;
    c.ao=q->ssao>=3?2:q->ssao?1:0;c.bloom=q->bloom!=0;c.eyeAdaptation=q->autoExposure!=0;c.grade=q->grade!=0;c.materials=q->materials!=0;
    c.shadows=q->shadows<0?0:q->shadows>2?2:q->shadows;c.contactShadows=q->contactShadows!=0;c.volumetrics=q->volumetrics!=0;
    c.foliage=q->a2c!=0;c.reflex=q->reflex<0?0:q->reflex>2?2:q->reflex;c.frameGen=q->frameGen!=0;
    c.dynamicLights=q->dynamicLights!=0;c.flares=q->flares!=0;c.detailTextures=q->detailTextures!=0;c.impacts=q->impacts!=0;
    return c;
}
static GraphicsQuality effective_quality(int preset,int safe_start){
    if(safe_start)preset=0;
    if(preset==3){
        GraphicsQuality quality=custom_quality(&custom_graphics);
        /* developer checks may still force single overrides on the command line */
        if(forced_texture>0)quality.picmip=forced_texture-1;
        if(forced_aa>0){const int levels[]={0,0,2,4,8};quality.samples=levels[forced_aa];if(quality.samples)quality.taa=quality.dlss=0;}
        return quality;
    }
    GraphicsQuality quality={preset==0?1:0,preset==2?16:(preset==1?8:0),preset==1?4:0,
        preset==0?L"GL_LINEAR_MIPMAP_NEAREST":L"GL_LINEAR_MIPMAP_LINEAR",
        preset>=1,preset==2?3:preset>=1,preset==2?3:preset>=1,preset>=1,preset>=1,preset==2&&ultra_uses_dlaa(),preset==2?0.2f:0.25f,0.3f,
        preset==2,preset==2,preset==2,preset==2?0.8f:0.75f,preset==2,0,0,0,0,0,0,0,0,0};
    if(preset==0||(!safe_start&&advanced_effects==1)){quality.hdr=quality.ssao=quality.tonemap=quality.bloom=quality.a2c=quality.dlss=0;quality.bloomIntensity=0;quality.sharpen=0;
        quality.taa=quality.autoExposure=quality.grade=0;quality.bloomThreshold=0.75f;quality.materials=0;}
    /* NVIDIA Reflex low latency rides with DLSS in Ultra; Frame Generation needs it and turns it on */
    quality.reflex=preset==2&&quality.hdr;
    quality.frameGen=!safe_start&&advanced_framegen&&quality.dlss&&frame_gen_possible(preset,advanced_effects);
    if(quality.frameGen)quality.reflex=1;
    if(!safe_start){
        if(advanced_texture)quality.picmip=advanced_texture-1;
        if(advanced_filter){const int levels[]={0,0,0,2,4,8,16};quality.anis=levels[advanced_filter];
            quality.filter=advanced_filter==1?L"GL_LINEAR_MIPMAP_NEAREST":L"GL_LINEAR_MIPMAP_LINEAR";}
        if(advanced_aa){const int levels[]={0,0,2,4,8};quality.samples=levels[advanced_aa];}
    }
    if(quality.samples)quality.taa=0; /* MSAA chosen in Graphics options: TAA cannot run with it */
    /* real-time lighting with Ultra's look (quality.materials: Ultra, not "effects off"): sun shadows at quality 2
       with ULTRA_DLAA_MIN_MB of video memory, else 1; contact shadows; volumetric sun shafts (ULTRA_VOLUMETRICS) */
    quality.shadows=quality.materials?(ultra_video_memory_mb()>=ULTRA_DLAA_MIN_MB?2:1):0;
    quality.contactShadows=quality.materials;quality.volumetrics=quality.materials&&ULTRA_VOLUMETRICS;
    quality.dynamicLights=quality.flares=quality.detailTextures=quality.impacts=1;
    return quality;
}
static int effective_refresh(int width,int height,int display,int safe_start){
    if(safe_start||display!=2||!advanced_refresh)return 0;
    int rates[128],count=display_rates(width,height,rates);
    for(int i=1;i<count;i++)if(rates[i]==advanced_refresh)return advanced_refresh;
    return 0;
}
static int save_graphics_preferences(void){
    int preset=(int)SendMessageW(preset_combo,CB_GETCURSEL,0,0);
    int resolution=(int)SendMessageW(resolution_combo,CB_GETCURSEL,0,0);
    int display=(int)SendMessageW(display_combo,CB_GETCURSEL,0,0);
    if(preset<0||preset>3||resolution<0||resolution>7||display<0||display>2)return 0;
    const wchar_t *keys[]={L"Preset",L"Resolution",L"Display",L"VSync",L"RefreshHz",L"TextureDetail",L"Filtering",L"AntiAliasing",L"Brightness",L"TextureCompression",L"PerformanceOverlay",L"Effects",L"FrameGeneration"};
    const int values[]={preset,resolution,display,SendMessageW(vsync_check,BM_GETCHECK,0,0)==BST_CHECKED,
        advanced_refresh,advanced_texture,advanced_filter,advanced_aa,advanced_brightness,advanced_compression,advanced_overlay,advanced_effects,advanced_framegen};
    for(int i=0;i<13;i++){wchar_t value[16];swprintf(value,16,L"%d",values[i]);
        if(!WritePrivateProfileStringW(L"Graphics",keys[i],value,ini))return 0;}
    if(custom_saved)for(int i=0;i<CUSTOM_FIELDS;i++){wchar_t value[16];swprintf(value,16,L"%d",*custom_field(&custom_graphics,i));
        if(!WritePrivateProfileStringW(L"Custom",CUSTOM_KEYS[i],value,ini))return 0;}
    /* when these choices were made: the game's own saved settings win only if they are newer (custom_import) */
    FILETIME now;GetSystemTimeAsFileTime(&now);wchar_t stamp[32];
    swprintf(stamp,32,L"%llu",((unsigned long long)now.dwHighDateTime<<32)|now.dwLowDateTime);
    return WritePrivateProfileStringW(L"Graphics",L"SavedAt",stamp,ini)!=0;
}
/* [Custom] of player.ini; 0 when there is none yet. */
static int custom_load(void){
    wchar_t probe[16];GetPrivateProfileStringW(L"Custom",CUSTOM_KEYS[0],L"",probe,16,ini);if(!probe[0])return 0;
    for(int i=0;i<CUSTOM_FIELDS;i++){int value=(int)GetPrivateProfileIntW(L"Custom",CUSTOM_KEYS[i],0,ini);
        *custom_field(&custom_graphics,i)=value<0?0:value>custom_maximum[i]?custom_maximum[i]:value;}
    return 1;
}
/* The name the player last set in the game (seta name in profile/tcetest/etconfig.cfg, colour codes and all). */
static int game_config_name(wchar_t *out,int capacity){
    wchar_t path[2300];swprintf(path,2300,L"%ls\\profile\\tcetest\\etconfig.cfg",root);
    FILE *file=_wfopen(path,L"r");if(!file)return 0;
    char line[512],found[128]="";
    while(fgets(line,sizeof(line),file)){char key[64],value[128];if(sscanf(line,"seta %63s \"%127[^\"]\"",key,value)==2&&!_stricmp(key,"name"))strcpy(found,value);}
    fclose(file);if(!found[0])return 0;
    if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,found,-1,out,capacity)&&!MultiByteToWideChar(CP_ACP,0,found,-1,out,capacity))return 0;
    return out[0]!=0;
}
/* 0.36.0: network updates the player picked in Options > System (seta snaps in etconfig.cfg): 128 stays 128,
   anything else (none yet, 0.35.0's 40, the engine's old 20) starts at 64. The server caps it to its sv_fps. */
static int game_config_snaps(void){
    wchar_t path[2300];swprintf(path,2300,L"%ls\\profile\\tcetest\\etconfig.cfg",root);
    FILE *file=_wfopen(path,L"r");if(!file)return 64;
    char line[512];int snaps=64;
    while(fgets(line,sizeof(line),file)){char key[64],value[32];if(sscanf(line,"seta %63s \"%31[^\"]\"",key,value)==2&&!_stricmp(key,"snaps"))snaps=atoi(value)>=128?128:64;}
    fclose(file);return snaps;
}
/* An in-game name wins while the launcher field still holds the name the launcher last started with
   (the player did not type a new one in the launcher since). Updates name and player.ini; 1 when adopted. */
static int adopt_game_name(wchar_t *name,int capacity){
    wchar_t last[64],game[64];GetPrivateProfileStringW(L"Player",L"LastStartedName",L"",last,64,ini);
    if(!last[0]||wcscmp(name,last)||!game_config_name(game,64)||!wcscmp(game,name))return 0;
    wcsncpy(name,game,capacity-1);name[capacity-1]=0;WritePrivateProfileStringW(L"Player",L"Name",name,ini);return 1;
}
/* What the player last chose in the game: profile/tcetest/etconfig.cfg, if it was written after the launcher
   last saved its own choices and it names a preset (ui_platinumPreset, set by the launcher and the in-game
   Graphics page). Returns that preset (0-3) or -1; for Custom the cvars become the custom set. */
static int custom_import(void){
    wchar_t path[2300];swprintf(path,2300,L"%ls\\profile\\tcetest\\etconfig.cfg",root);
    WIN32_FILE_ATTRIBUTE_DATA info;if(!GetFileAttributesExW(path,GetFileExInfoStandard,&info))return -1;
    wchar_t stamp[32];GetPrivateProfileStringW(L"Graphics",L"SavedAt",L"0",stamp,32,ini);
    unsigned long long saved=wcstoull(stamp,NULL,10),written=((unsigned long long)info.ftLastWriteTime.dwHighDateTime<<32)|info.ftLastWriteTime.dwLowDateTime;
    if(written<=saved)return -1;
    FILE *file=_wfopen(path,L"r");if(!file)return -1;
    GraphicsQuality q=effective_quality(1,0);int preset=-1,specular=-1;char line[512];
    static wchar_t filter[40];wcscpy(filter,q.filter);q.filter=filter;
    while(fgets(line,sizeof(line),file)){
        char name[64],value[128];
        if(sscanf(line,"seta %63s \"%127[^\"]\"",name,value)!=2&&sscanf(line,"set %63s \"%127[^\"]\"",name,value)!=2)continue;
        int n=atoi(value);float f=(float)atof(value);
        if(!_stricmp(name,"ui_platinumPreset"))preset=n;
        else if(!_stricmp(name,"r_picmip"))q.picmip=n;
        else if(!_stricmp(name,"r_textureMode"))MultiByteToWideChar(CP_UTF8,0,value,-1,filter,40);
        else if(!_stricmp(name,"r_ext_texture_filter_anisotropic"))q.anis=n;
        else if(!_stricmp(name,"r_dx12Msaa"))q.samples=n;
        else if(!_stricmp(name,"r_dx12Taa"))q.taa=n;
        else if(!_stricmp(name,"r_dx12Dlss"))q.dlss=n!=0;
        else if(!_stricmp(name,"r_dx12Hdr"))q.hdr=n;
        else if(!_stricmp(name,"r_dx12Tonemap"))q.tonemap=n;
        else if(!_stricmp(name,"r_dx12Ssao"))q.ssao=n==2?1:n==4?3:n; /* 2 and 4 only show the occlusion */
        else if(!_stricmp(name,"r_dx12Bloom"))q.bloom=n;
        else if(!_stricmp(name,"r_dx12Sharpen"))q.sharpen=f;
        else if(!_stricmp(name,"r_dx12AlphaToCoverage"))q.a2c=n;
        else if(!_stricmp(name,"r_dx12AutoExposure"))q.autoExposure=n;
        else if(!_stricmp(name,"r_dx12Grade"))q.grade=n;
        else if(!_stricmp(name,"r_dx12Materials"))q.materials=n;
        else if(!_stricmp(name,"r_dx12Specular"))specular=n;
        else if(!_stricmp(name,"r_dx12Shadows"))q.shadows=n;
        else if(!_stricmp(name,"r_dx12ContactShadows"))q.contactShadows=n;
        else if(!_stricmp(name,"r_dx12Volumetrics"))q.volumetrics=n;
        else if(!_stricmp(name,"r_dx12Reflex"))q.reflex=n;
        else if(!_stricmp(name,"r_dx12FrameGen"))q.frameGen=n;
        else if(!_stricmp(name,"r_dynamiclight"))q.dynamicLights=n;
        else if(!_stricmp(name,"r_flares"))q.flares=n;
        else if(!_stricmp(name,"r_detailtextures"))q.detailTextures=n;
        else if(!_stricmp(name,"cg_impactEffects"))q.impacts=n;
    }
    fclose(file);
    if(preset<0||preset>3)return -1;
    if(!specular)q.materials=0; /* materials ride with highlights and reflections */
    if(preset==3){custom_graphics=quality_custom(&q);custom_saved=1;}
    return preset;
}
/* The quality cvars of one preset. The native renderers (renderer_vk frontend and renderer1) read
   r_ext_texture_filter_anisotropic as the level itself. ui_platinumPreset tells the in-game Graphics page which
   preset is active (3 Custom; -1 none, Safe Start); the launcher reads it back from etconfig.cfg. */
static void write_quality_block(FILE *config,const GraphicsQuality *quality,int marker){
    fprintf(config,"set r_picmip %d\nset r_textureMode %ls\nset r_ext_texture_filter_anisotropic %d\nset r_ext_max_anisotropy %d\n"
        "set r_ext_multisample %d\nset r_dx12Msaa %d\n",quality->picmip,quality->filter,quality->anis,quality->anis?quality->anis:2,
        quality->samples,quality->samples);
    fprintf(config,"set r_dx12Hdr %d\nset r_dx12Ssao %d\nset r_dx12Tonemap %d\nset r_dx12Bloom %d\nset r_dx12BloomIntensity %.2f\n"
        "set r_dx12Sharpen %.2f\nset r_dx12Fxaa 0\nset r_dx12AlphaToCoverage %d\nset r_dx12Dlss %d\n",
        quality->hdr,quality->ssao,quality->tonemap,quality->bloom,quality->bloomIntensity,quality->sharpen,quality->a2c,quality->dlss);
    fprintf(config,"set r_dx12BloomThreshold %.2f\nset r_dx12Taa %d\nset r_dx12AutoExposure %d\nset r_dx12Grade %d\n",
        quality->bloomThreshold,quality->taa,quality->autoExposure,quality->grade);
    fprintf(config,"set r_dx12Materials %d\nset r_dx12Specular %d\nset r_dx12Probes %d\n",quality->materials,quality->materials,quality->materials);
    fprintf(config,"set r_dx12Reflex %d\nset r_dx12FrameGen %d\n",quality->reflex,quality->frameGen);
    fprintf(config,"set r_dx12Shadows %d\nset r_dx12ContactShadows %d\nset r_dx12Volumetrics %d\n",
        quality->shadows,quality->contactShadows,quality->volumetrics);
    fprintf(config,"set r_dynamiclight %d\nset r_flares %d\nset r_detailtextures %d\nseta cg_impactEffects %d\nseta ui_platinumPreset %d\n",
        quality->dynamicLights,quality->flares,quality->detailTextures,quality->impacts,marker);
    /* what each row of the in-game Graphics page shows (ui_gfx<N>, CUSTOM_KEYS order): latched renderer cvars
       change only after vid_restart, so the page reads these instead */
    CustomGraphics shown=quality_custom(quality);
    for(int i=0;i<CUSTOM_FIELDS;i++)fprintf(config,"seta ui_gfx%d %d\n",i,*custom_field(&shown,i));
}
/* The in-game Graphics page applies a preset with "exec platinum-preset-N.cfg"; these files hold exactly what
   the launcher would start with (Ultra's anti-aliasing and shadow quality follow this PC's graphics card). */
static void write_preset_files(const wchar_t *dir){
    for(int preset=0;preset<4;++preset){
        wchar_t path[2400];swprintf(path,2400,L"%ls\\platinum-preset-%d.cfg",dir,preset);
        FILE *file=_wfopen(path,L"w");if(!file)continue;
        /* no custom set saved yet: Custom starts from High, as it does in the launcher */
        GraphicsQuality quality=effective_quality(preset==3&&!custom_saved?1:preset,0);
        fprintf(file,"// TrueCombat: Platinum graphics preset, written by the launcher\n");
        write_quality_block(file,&quality,preset);
        fclose(file);
    }
}
/* ---- Launch options (Settings > Graphics): extra console commands chosen by the player ----
   "+set cg_fov 100 +set cl_maxpackets 125" or "cg_fov 100; com_hunkmegs 256". They go into
   platinum-launch.cfg, one command per line, so the engine's 32-argument command line stays short. */
#define LAUNCH_OPTIONS_MAX 300
#ifndef EM_SETCUEBANNER
#define EM_SETCUEBANNER 0x1501
#endif
static void launch_options_clean(wchar_t *text){
    int n=0;for(int i=0;text[i];++i)if(text[i]>=0x20&&text[i]!=0x7F)text[n++]=text[i];text[n]=0;
    while(n&&text[n-1]==L' ')text[--n]=0;
    int start=0;while(text[start]==L' ')++start;if(start)memmove(text,text+start,(wcslen(text+start)+1)*sizeof(wchar_t));
}
static void launch_options_write(FILE *config){
    wchar_t extra[LAUNCH_OPTIONS_MAX];GetPrivateProfileStringW(L"Launch",L"Options",L"",extra,LAUNCH_OPTIONS_MAX,ini);
    launch_options_clean(extra);if(!extra[0])return;
    char text[LAUNCH_OPTIONS_MAX*3];WideCharToMultiByte(CP_UTF8,0,extra,-1,text,sizeof(text),NULL,NULL);
    /* a command starts at the beginning, after ';', or at '+' that follows a space */
    char *p=text;
    while(*p){
        while(*p==' '||*p==';'||*p=='+')++p;
        if(!*p)break;
        char *end=p;
        while(*end&&*end!=';'&&!(*end=='+'&&end>p&&end[-1]==' '))++end;
        char saved=*end;*end=0;
        size_t n=strlen(p);while(n&&p[n-1]==' ')p[--n]=0;
        if(n)fprintf(config,"%s\n",p);
        *end=saved;p=end;
    }
}
/* ---- Settings > Storage > Move the game ----
   Moves everything the game owns to <folder>\TrueCombat Platinum. The launcher itself, its
   launcher.ini and the uninstaller stay where Windows knows them; launcher.ini and the setup's
   registry entry then point at the new folder, and the launcher restarts from there. */
static int move_keep(const wchar_t *name){
    wchar_t self[2200];const wchar_t *base=L"TrueCombatPlatinum.exe";
    if(GetModuleFileNameW(NULL,self,2200)){const wchar_t *slash=wcsrchr(self,L'\\');if(slash)base=slash+1;}
    if(_wcsicmp(root,launcherDir))return 0;   /* game already separate: all of it moves */
    return !_wcsicmp(name,base)||!_wcsicmp(name,L"TrueCombatPlatinum.exe")||!_wcsicmp(name,L"launcher.ini")||!_wcsnicmp(name,L"Uninstall ",10)||
           !_wcsicmp(name,L"TrueCombatPlatinum.exe.old")||!_wcsicmp(name,L"TrueCombatPlatinum.exe.new");
}
static void move_game(HWND window){
    LONG state=update_visible_state();
    if(game_running()||state==UPDATE_DOWNLOADING||state==UPDATE_VERIFYING||state==UPDATE_READY){
        MessageBoxW(window,L"Close the game and your server, and wait for any download to finish, then move the game.",TITLE,MB_OK|MB_ICONINFORMATION);return;}
    BROWSEINFOW browse={0};wchar_t picked[MAX_PATH]=L"";
    browse.hwndOwner=window;browse.pszDisplayName=picked;browse.lpszTitle=L"Choose where TrueCombat: Platinum should live. A \"TrueCombat Platinum\" folder is created there.";
    browse.ulFlags=BIF_RETURNONLYFSDIRS|BIF_NEWDIALOGSTYLE;
    PIDLIST_ABSOLUTE list=SHBrowseForFolderW(&browse);if(!list)return;
    int ok=SHGetPathFromIDListW(list,picked);CoTaskMemFree(list);if(!ok||!picked[0])return;
    wchar_t target[2300];size_t n=wcslen(picked);while(n>3&&picked[n-1]==L'\\')picked[--n]=0;
    swprintf(target,2300,picked[n-1]==L'\\'?L"%lsTrueCombat Platinum":L"%ls\\TrueCombat Platinum",picked);
    size_t rl=wcslen(root);
    if(!_wcsicmp(target,root)||(!_wcsnicmp(target,root,rl)&&target[rl]==L'\\')){MessageBoxW(window,L"Choose a folder outside the current game folder.",TITLE,MB_OK|MB_ICONINFORMATION);return;}
    if(GetFileAttributesW(target)!=INVALID_FILE_ATTRIBUTES){
        wchar_t probe[2400];swprintf(probe,2400,L"%ls\\*",target);WIN32_FIND_DATAW item;HANDLE find=FindFirstFileW(probe,&item);int empty=1;
        if(find!=INVALID_HANDLE_VALUE){do{if(wcscmp(item.cFileName,L".")&&wcscmp(item.cFileName,L".."))empty=0;}while(empty&&FindNextFileW(find,&item));FindClose(find);}
        if(!empty){MessageBoxW(window,L"That folder already has a \"TrueCombat Platinum\" folder with files in it. Choose another place.",TITLE,MB_OK|MB_ICONINFORMATION);return;}
    }
    {   /* enough room on the target drive? */
        ULARGE_INTEGER free;wchar_t drive[2300];wcscpy(drive,picked);
        if(GetDiskFreeSpaceExW(drive,&free,NULL,NULL)&&free.QuadPart<(ULONGLONG)3*1073741824&&towupper(drive[0])!=towupper(root[0])){
            MessageBoxW(window,L"The chosen drive has less than 3 GB free. Make room or choose another drive.",TITLE,MB_OK|MB_ICONWARNING);return;}
    }
    wchar_t question[2700];swprintf(question,2700,tr(L"Move the game to\n%ls ?\n\nYour settings, profile and replays move with it. The launcher restarts when it is done."),target);
    if(MessageBoxW(window,question,TITLE,MB_OKCANCEL|MB_ICONQUESTION)!=IDOK)return;
    {int made=SHCreateDirectoryExW(window,target,NULL);
     if(made!=ERROR_SUCCESS&&made!=ERROR_ALREADY_EXISTS&&made!=ERROR_FILE_EXISTS){error(L"The new folder could not be created. Check that you may write there.");return;}}
    /* double-NUL list of everything that moves */
    size_t capacity=1<<16,used=0;wchar_t *from=(wchar_t*)calloc(capacity,sizeof(wchar_t));if(!from)return;
    wchar_t pattern[2400];swprintf(pattern,2400,L"%ls\\*",root);WIN32_FIND_DATAW item;HANDLE find=FindFirstFileW(pattern,&item);int count=0;
    if(find!=INVALID_HANDLE_VALUE){do{
        if(!wcscmp(item.cFileName,L".")||!wcscmp(item.cFileName,L"..")||move_keep(item.cFileName))continue;
        wchar_t path[2600];int len=swprintf(path,2600,L"%ls\\%ls",root,item.cFileName);
        if(len<=0||used+len+2>=capacity)continue;
        wcscpy(from+used,path);used+=len+1;++count;
    }while(FindNextFileW(find,&item));FindClose(find);}
    from[used]=0;
    if(!count){free(from);error(L"There is nothing to move in this folder.");return;}
    wchar_t to[2400]={0};wcsncpy(to,target,2390);
    SHFILEOPSTRUCTW op={0};op.hwnd=window;op.wFunc=FO_MOVE;op.pFrom=from;op.pTo=to;op.fFlags=FOF_NOCONFIRMMKDIR|FOF_NOCONFIRMATION;
    op.lpszProgressTitle=L"Moving TrueCombat: Platinum";
    int result=SHFileOperationW(&op);free(from);
    if(result||op.fAnyOperationsAborted){error(L"The move did not finish. Files that were already moved are in the new folder; select Move again to finish, or move them back.");return;}
    wchar_t layout[2300];swprintf(layout,2300,L"%ls\\launcher.ini",launcherDir);
    WritePrivateProfileStringW(L"Install",L"GameFolder",target,layout);
    HKEY key;if(!RegCreateKeyExW(HKEY_CURRENT_USER,L"Software\\Team Terminus\\TrueCombat Platinum",0,NULL,0,KEY_WRITE,NULL,&key,NULL)){
        RegSetValueExW(key,L"GameFolder",0,REG_SZ,(const BYTE*)target,(DWORD)((wcslen(target)+1)*sizeof(wchar_t)));RegCloseKey(key);}
    /* from here on this process writes (window placement) into the new folder */
    wcsncpy(root,target,2047);root[2047]=0;swprintf(ini,2200,L"%ls\\player.ini",root);
    /* restart from the same launcher, now pointing at the new folder */
    wchar_t self[2200],command[2400];GetModuleFileNameW(NULL,self,2200);swprintf(command,2400,L"\"%ls\"",self);
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
    if(CreateProcessW(self,command,NULL,NULL,FALSE,0,NULL,launcherDir,&si,&pi)){CloseHandle(pi.hThread);CloseHandle(pi.hProcess);}
    DestroyWindow(window);
}
static int launch(HWND window,int safe_start,int menu_only) {
    wchar_t server[256],name[64],engine[2200],home[2200],cmd[8192];
    wchar_t raw_server[256];GetWindowTextW(server_edit,raw_server,256);server[0]=0;normalize_server(raw_server,server);GetWindowTextW(name_edit,name,64);
    if(adopt_game_name(name,64))SetWindowTextW(name_edit,name); /* keep a name set in the game */
    if(!menu_only&&!local_map[0]&&!valid_server(server)){error(PLATINUM_NATIVE?L"Enter a server IP or hostname, optionally followed by :27971.":L"Enter a server IP or hostname, optionally followed by :27960.");return 0;}
    if(!valid_name(name)){error(wcschr(name,L'^')?L"A colour code in your name is incomplete. Open Settings > Controls > Name colours to fix it.":L"Use 1 to 24 letters, numbers, spaces or these symbols: _ - * ( ) .");return 0;}
    swprintf(engine,2200,L"%ls\\engine\\platinum-engine.bin",root);
    swprintf(home,2200,L"%ls\\profile",root);
    if(GetFileAttributesW(engine)==INVALID_FILE_ATTRIBUTES){error(L"Game files are missing. Extract the entire TrueCombat Platinum folder before starting.");return 0;}
    if(crashPromptAllowed)crash_prompt(window);
    int join_packetdup=0;
    if(PLATINUM_NATIVE&&!menu_only&&!local_map[0]&&valid_server(server)&&!join_prepare(window,server,&join_packetdup))return 0;
    CreateDirectoryW(home,NULL);
    wchar_t probe[2300];swprintf(probe,2300,L"%ls\\.write-check",home);
    HANDLE file=CreateFileW(probe,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_TEMPORARY|FILE_FLAG_DELETE_ON_CLOSE,NULL);
    if(file==INVALID_HANDLE_VALUE){error(L"This folder is read-only. Extract the game to a writable folder, such as Documents or Games.");return 0;} CloseHandle(file);
    int preset=(int)SendMessageW(preset_combo,CB_GETCURSEL,0,0);
    int resolution=(int)SendMessageW(resolution_combo,CB_GETCURSEL,0,0);
    int display=(int)SendMessageW(display_combo,CB_GETCURSEL,0,0);
    int vsync=SendMessageW(vsync_check,BM_GETCHECK,0,0)==BST_CHECKED;
    if(preset<0||preset>3||resolution<0||resolution>7||display<0||display>2){error(L"Select valid graphics settings.");return 0;}
    if(safe_start){preset=0;resolution=1;display=0;vsync=0;}
    int width,height;display_dimensions(resolution,&width,&height);
    int aspect=width*3==height*4?2:(width*10==height*16?1:0);
    GraphicsQuality quality=effective_quality(preset,safe_start);
    swprintf(cmd,8192,L"\"%ls\" +set fs_basepath . +set fs_homepath profile +set fs_game tcetest "
        L"+set cl_punkbuster 0 +set cl_allowDownload 0 +set logfile 1 +set net_port 0 +set net_port6 0 +set in_mouse 1 +set s_initsound %d "
        L"+set r_fullscreen %d +set r_noborder %d +set r_mode -1 +set r_customwidth %d +set r_customheight %d "
        L"+set cg_aspectMode %d +set r_picmip %d +set r_textureMode %ls "
        L"+set r_ext_texture_filter_anisotropic %d +set r_ext_max_anisotropy %d +set r_ext_multisample %d "
        L"+set r_swapInterval %d +set name \"%ls\"",engine,no_sound?0:1,
        display==2,display==1,width,height,aspect,quality.picmip,quality.filter,
        quality.anis!=0,quality.anis?quality.anis:2,quality.samples,vsync,name);
    if(advanced_compression){wcscat(cmd,L" +set r_ext_compressed_textures ");wcscat(cmd,safe_start||advanced_compression==1?L"1":L"0");}
    if(advanced_overlay){
        wcscat(cmd,L" +set cg_drawFPS ");wcscat(cmd,!safe_start&&advanced_overlay>=2?L"1":L"0");
        wcscat(cmd,L" +set cg_netGraph ");wcscat(cmd,!safe_start&&advanced_overlay==3?L"2":L"0"); /* 0.37.0: cg_lagometer is not read; cg_netGraph 2 = ping + graph */
    }
    if(advanced_brightness){
        const wchar_t *gamma[]={L"",L"1.0",L"1.1",L"1.2",L"1.3",L"1.4",L"1.5"};
        wcscat(cmd,L" +set r_gamma ");wcscat(cmd,safe_start?L"1.0":gamma[advanced_brightness]);
    }
    int refresh=effective_refresh(width,height,display,safe_start);
    wchar_t refresh_arg[64];swprintf(refresh_arg,64,L" +set r_displayRefresh %d",refresh);wcscat(cmd,refresh_arg);
    /* 0.38.0: com_maxfps only when Safe Start or the launcher's own frame limit asks for one; otherwise the game keeps its Options choice */
    wchar_t session_args[120];if(safe_start||session_fps>0)swprintf(session_args,120,L" +set com_maxfps %d +set com_maxfpsUnfocused %d",safe_start?125:session_fps,safe_start?30:session_idle_fps);
    else swprintf(session_args,120,L" +set com_maxfpsUnfocused %d",session_idle_fps);wcscat(cmd,session_args);
    wchar_t launch_dir[2300],launch_path[2400];swprintf(launch_dir,2300,L"%ls\\tcetest",home);CreateDirectoryW(launch_dir,NULL);
    swprintf(launch_path,2400,L"%ls\\platinum-launch.cfg",launch_dir);
    FILE *config=_wfopen(launch_path,L"w");if(!config){error(L"Launch settings could not be written. Check that this game folder is writable.");return 0;}
    char endpoint[256],test_config[128];WideCharToMultiByte(CP_UTF8,0,server,-1,endpoint,256,NULL,NULL);WideCharToMultiByte(CP_UTF8,0,forced_config,-1,test_config,128,NULL,NULL);
    if(PLATINUM_NATIVE){
        /* The engine accepts only 32 startup commands and 1024 command-line
           bytes. Keep this short; apply the full profile from a config. */
        fprintf(config,"setu tcp_native_protocol tcp-native-capture-7\nsetu rate 250000\nsetu snaps %d\n"
            "set name \"%ls\"\nset r_fullscreen %d\nset r_noborder %d\nset r_mode -1\n"
            "set r_customwidth %d\nset r_customheight %d\nset r_swapInterval %d\n"
            "set r_displayRefresh %d\nset com_maxfpsUnfocused %d\nset com_maxfpsMinimized %d\n",
            game_config_snaps(),name,display==2,display==1,width,height,vsync,refresh,
            safe_start?30:session_idle_fps,safe_start?30:session_idle_fps);
        if(safe_start||session_fps>0)fprintf(config,"set com_maxfps %d\n",safe_start?125:session_fps);
        if(advanced_brightness||safe_start){const char *gamma[]={"1.0","1.0","1.1","1.2","1.3","1.4","1.5"};
            fprintf(config,"set r_gamma %s\n",gamma[safe_start?0:advanced_brightness]);}
        if(advanced_compression)fprintf(config,"set r_ext_compressed_textures %d\n",safe_start||advanced_compression==1);
        if(advanced_overlay)fprintf(config,"set cg_drawFPS %d\nset cg_netGraph %d\n",!safe_start&&advanced_overlay>=2,!safe_start&&advanced_overlay==3?2:0);
        /* every quality cvar, the same block as the in-game presets (profile/tcetest/platinum-preset-N.cfg);
           Safe Start marks no preset, so the game's page shows none and its cvars are not read back as Custom */
        write_quality_block(config,&quality,safe_start?-1:preset);
        write_preset_files(launch_dir);
        binds_write(config);
        fprintf(config,"vid_restart\n");
        swprintf(cmd,8192,L"\"%ls\" +set fs_basepath . +set fs_homepath profile +set fs_game tcetest "
            L"+set cl_renderer %ls +set cl_allowDownload 0 +set logfile 1 +set net_port 0 +set net_port6 0 "
            L"+set net_ip 0.0.0.0 +set net_enabled %d +set s_initsound %d +set com_recommendedSet 1 "
            L"+set r_fullscreen %d +set r_noborder %d +set r_mode -1 +set r_customwidth %d +set r_customheight %d",
            engine,safe_start?L"opengl1":L"dx12",server[0]==L'['&&!local_map[0]?11:1,no_sound?0:1,display==2,display==1,width,height);
        /* Practice: team deathmatch (tcp_native_rounds 4) filled to 6 players with skill 2
           bots. A listen server never reports to the master list. */
        if(local_map[0]&&practice_mode)fprintf(config,"set sv_maxclients 8\nset sv_pure 0\nset sv_hostname \"Practice\"\n"
            "set tcp_native_rounds %d\nset bot_minplayers %d\nset bot_skill 2\nset g_practice 1\nset g_firingRange %d\n",practice_mode==2?0:4,practice_mode==2?0:6,practice_mode==2);
        /* Firing range: free play (rounds 0, so a lone player is never held in warm-up) without bots; the server sets up a lane of still targets (tcp_range.h). */
        if(local_map[0]&&practice_mode==2)fprintf(config,"set sv_hostname \"Firing range\"\n");
        /* 0.37.2: the map starts after the intro; the UI runs ui_platinumStart once the intro is over or skipped */
        if(local_map[0])fprintf(config,"%sset ui_platinumStart \"map %ls; wait 10; set sv_fps 128\"\n",practice_mode?"":"set sv_maxclients 4\nset sv_pure 0\n",local_map);
    }
    if(PLATINUM_NATIVE){
        /* one-click join extras: server password and pickup team (userinfo tcp_team, read with g_pugTeams 1) */
        fprintf(config,"set password \"%s\"\nsetu tcp_team \"%s\"\n",join_password,join_team=='r'?"r":join_team=='b'?"b":"");
        if(join_packetdup)fprintf(config,"set cl_packetdup %d\n",join_packetdup);
    }
    if(valid_server(server)&&!local_map[0]){
        /* IPv4 stays forced for names and IPv4 addresses; an [IPv6] address connects over IPv6 (net_enabled 11 above) */
        const char *family=!PLATINUM_NATIVE?"":endpoint[0]=='['?"-6 ":"-4 ";
        fprintf(config,"set tcp_hasServer 1\nset tcp_rejoin \"disconnect; wait 2; connect %s%s\"\n",family,endpoint);if(!menu_only)fprintf(config,PLATINUM_NATIVE?"set ui_platinumStart \"connect %s%s\"\n":"connect %s%s\n",family,endpoint);}   /* native: after the intro */
    else fprintf(config,"set tcp_hasServer 0\nset tcp_rejoin \"\"\n");
    if(!safe_start)launch_options_write(config);   /* Safe start leaves the player's extra commands out */
    if(test_config[0])fprintf(config,"exec %s\n",test_config);
    if(profile_demo_play[0]){fprintf(config,"demo \"%ls\"\n",profile_demo_play);profile_demo_play[0]=0;}
    if(fclose(config)){error(L"Launch settings could not be saved.");return 0;}
    wcscat(cmd,L" +exec platinum-launch.cfg");
    /* Easy Anti-Cheat: start through the bootstrapper when the package has it. */
    wchar_t eac_exe[2300];const wchar_t *program=engine;eac_following=0;
    if(PLATINUM_NATIVE&&!local_map[0]&&eac_bootstrapper(root,ini,eac_exe,2300)&&eac_retarget(cmd,8192,eac_exe)){program=eac_exe;eac_following=1;}
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
    if(!CreateProcessW(program,cmd,NULL,NULL,FALSE,0,NULL,root,&si,&pi)){
        wchar_t message[256];swprintf(message,256,tr(L"The game could not start (Windows error %lu)."),GetLastError());error(message);return 0;}
    if(!menu_only&&!local_map[0]){WritePrivateProfileStringW(L"Player",L"Server",server,ini);remember_server(server);}
    WritePrivateProfileStringW(L"Player",L"Name",name,ini);WritePrivateProfileStringW(L"Player",L"LastStartedName",name,ini);
    if(!safe_start)save_graphics_preferences();
    if(PLATINUM_NATIVE){
        /* Discord presence follows the game process: under Easy Anti-Cheat that is the bootstrapper's child. */
        eac_presence_keep((!menu_only&&!local_map[0])?server:L"");
        if(!eac_following)presence_start(pi.dwProcessId,eac_presence_server);}
    CloseHandle(pi.hThread);starting_game=pi.hProcess;starting_pid=pi.dwProcessId;
    if(!local_map[0]||practice_mode)telemetry_count_launch(safe_start);
    shellLaunchSafe=safe_start;show_loading(window);return 1;
}
static HWND control(HWND parent,const wchar_t *kind,const wchar_t *text,DWORD style,int x,int y,int w,int h,int id){
    /* Retain the body coordinates while shortening only the main header.
       Owned advanced-dialog controls and the startup splash keep their layout. */
    if(shell_main(parent)&&y>=285)y-=BANNER_HEIGHT-LAUNCHER_HEADER_HEIGHT;
    else if(!shell_main(parent)){if(shell_is_class(parent,L"TrueCombatPlatinumSession")&&x>=600&&y>=152)y+=SHELL_MAP_ROW;y+=SHELL_DIALOG_HEADER;}
    if(wcscmp(kind,L"STATIC")==0)style|=SS_NOPREFIX;
    style=shell_adjust_style(kind,style);
    /* labels and buttons appear in the launcher language; fields keep exactly what they were given */
    HWND c=CreateWindowExW(wcscmp(kind,L"EDIT")==0?WS_EX_CLIENTEDGE:0,kind,!shell_main(parent)&&wcscmp(kind,L"EDIT")&&wcscmp(kind,L"COMBOBOX")?tr(text):text,WS_CHILD|WS_VISIBLE|style,
                          x,y,w,h,parent,(HMENU)(INT_PTR)id,GetModuleHandleW(NULL),NULL);
    HFONT face=font;
    if(!shell_main(parent)&&!wcscmp(kind,L"STATIC")&&text&&text[0]&&shellCaptionFont){
        /* Dialog section headings (all caps) use the display face, like the website's eyebrows. */
        int caps=1;for(const wchar_t *p=text;*p;++p)if(*p>=L'a'&&*p<=L'z')caps=0;
        if(caps)face=shellCaptionFont;
    }
    SendMessageW(c,WM_SETFONT,(WPARAM)face,TRUE);
    shell_style_control(c,kind);
    if(shell_main(parent))shell_register(c,kind,text,x,y,w,h,id);
    return c;
}
static int preference(const wchar_t *key,int fallback,int maximum){
    int value=(int)GetPrivateProfileIntW(L"Graphics",key,fallback,ini);
    return value>=0&&value<=maximum?value:fallback;
}
/* Items show in the launcher language; the English text stays in the item data so a language change can refill them. */
static void combo_item(HWND combo,const wchar_t *text){LRESULT at=SendMessageW(combo,CB_ADDSTRING,0,(LPARAM)tr(text));if(at>=0)SendMessageW(combo,CB_SETITEMDATA,(WPARAM)at,(LPARAM)text);}
static void combos_translate(HWND window){
    static const int ids[]={107,108,109,145,146,147,148,149,154};
    for(unsigned k=0;k<sizeof(ids)/sizeof(ids[0]);++k){HWND combo=GetDlgItem(window,ids[k]);if(!combo)continue;
        int count=(int)SendMessageW(combo,CB_GETCOUNT,0,0),selected=(int)SendMessageW(combo,CB_GETCURSEL,0,0);if(count<=0||count>40)continue;
        const wchar_t *keys[40];for(int i=0;i<count;++i)keys[i]=(const wchar_t*)SendMessageW(combo,CB_GETITEMDATA,(WPARAM)i,0);
        SendMessageW(combo,WM_SETREDRAW,FALSE,0);SendMessageW(combo,CB_RESETCONTENT,0,0);
        for(int i=0;i<count;++i)if(keys[i]&&keys[i]!=(const wchar_t*)CB_ERR)combo_item(combo,keys[i]);
        SendMessageW(combo,CB_SETCURSEL,selected,0);SendMessageW(combo,WM_SETREDRAW,TRUE,0);InvalidateRect(combo,NULL,TRUE);}
}
static void update_graphics_summary(void){
    if(!preset_description)return;
    int preset=(int)SendMessageW(preset_combo,CB_GETCURSEL,0,0),resolution=(int)SendMessageW(resolution_combo,CB_GETCURSEL,0,0);
    int display=(int)SendMessageW(display_combo,CB_GETCURSEL,0,0);
    if(preset<0||preset>3||resolution<0||resolution>7||display<0||display>2)return;
    GraphicsQuality quality=effective_quality(preset,0);
    const wchar_t *textures[]={L"Full",L"Half",L"Quarter"},*gamma[]={L"Game",L"1.0",L"1.1",L"1.2",L"1.3",L"1.4",L"1.5"};
    const wchar_t *compression[]={L"Game",L"On",L"Off"};
    wchar_t filtering[40],aa[24],refresh_text[32],text[360];
    if(quality.anis)swprintf(filtering,40,L"%dx filtering",quality.anis);
    else wcscpy(filtering,!wcscmp(quality.filter,L"GL_LINEAR_MIPMAP_LINEAR")?L"Trilinear":L"Bilinear");
    if(quality.samples)swprintf(aa,24,L"%dx",quality.samples);else wcscpy(aa,quality.taa?(quality.dlss?L"DLAA":L"TAA"):L"Off");
    int width,height;display_dimensions(resolution,&width,&height);
    int refresh=effective_refresh(width,height,display,0);
    if(display!=2)wcscpy(refresh_text,L"Windows");else if(refresh)swprintf(refresh_text,32,L"%d Hz",refresh);else wcscpy(refresh_text,L"Auto");
    const wchar_t *overlays[]={L"Game HUD",L"Stats off",L"FPS",L"FPS+Net"};
    wchar_t effects[160];
    int effectCount=!!quality.hdr+!!quality.tonemap+!!quality.ssao+!!quality.bloom+!!quality.autoExposure+!!quality.grade+!!quality.materials+
        !!quality.shadows+!!quality.contactShadows+!!quality.volumetrics+!!quality.a2c+!!quality.reflex+!!quality.frameGen;
    if(preset==3)swprintf(effects,160,L"Custom: %d of 13 DirectX 12 effects on%ls",effectCount,quality.shadows?L"  \x00B7  Sun shadows":L"");
    else if(!quality.hdr&&!quality.bloom&&!quality.ssao)wcscpy(effects,L"Original look, no extra effects");
    else if(quality.grade||quality.autoExposure)swprintf(effects,160,L"Modern look: filmic color  \x00B7  Eye adaptation  \x00B7  GTAO shadows  \x00B7  Bloom%ls",
        quality.frameGen?L"  \x00B7  Frame Generation":L"");
    else swprintf(effects,120,L"HDR  \x00B7  Ambient shadows  \x00B7  Bloom  \x00B7  Sharpen%ls",quality.dlss?L"  \x00B7  DLAA":L"");
    swprintf(text,360,L"%ls textures  \x00B7  %ls  \x00B7  AA %ls\n%ls\nGamma %ls  \x00B7  %ls  \x00B7  Compression %ls  \x00B7  Refresh %ls",
        textures[quality.picmip],filtering,aa,effects,gamma[advanced_brightness],overlays[advanced_overlay],compression[advanced_compression],refresh_text);
    SetWindowTextW(preset_description,text);
    {   /* the same facts as a label/value grid (shell_paint) */
        const wchar_t *look=preset==3?L"Custom":quality.materials?L"Ultra lighting":(quality.grade||quality.autoExposure)?L"Modern":(quality.hdr||quality.bloom||quality.ssao)?L"Enhanced":L"Original";
        wchar_t lookText[64],aaText[32],filterText[40],brightText[32],refreshValue[32];
        if(preset==3)swprintf(lookText,64,L"Custom, %d effects",effectCount);
        else swprintf(lookText,64,L"%ls%ls",look,quality.frameGen?L" + Frame Gen":L"");
        if(quality.samples)swprintf(aaText,32,L"%ls MSAA",aa);else wcscpy(aaText,aa);
        if(quality.anis)swprintf(filterText,40,L"%dx anisotropic",quality.anis);else wcscpy(filterText,filtering);
        if(advanced_brightness)swprintf(brightText,32,L"Gamma %ls",gamma[advanced_brightness]);else wcscpy(brightText,L"In-game setting");
        if(display!=2)wcscpy(refreshValue,L"Follows desktop");else wcscpy(refreshValue,refresh_text);
        const wchar_t *labels[SHELL_SPEC_MAX]={L"TEXTURES",L"FILTERING",L"ANTI-ALIASING",L"LOOK",L"BRIGHTNESS",L"REFRESH RATE"};
        const wchar_t *values[SHELL_SPEC_MAX]={textures[quality.picmip],filterText,aaText,lookText,brightText,refreshValue};
        for(int i=0;i<SHELL_SPEC_MAX;++i){wcsncpy(shellSpecLabel[i],labels[i],23);shellSpecLabel[i][23]=0;wcsncpy(shellSpecValue[i],values[i],63);shellSpecValue[i][63]=0;}
        shellSpecCount=SHELL_SPEC_MAX;shellBodyDirty=1;
        HWND owner=GetParent(preset_description);if(owner)InvalidateRect(owner,NULL,FALSE);
    }
    SetWindowTextW(GetDlgItem(GetParent(preset_description),113),
        (advanced_texture||advanced_filter||advanced_aa||advanced_brightness||advanced_refresh||advanced_compression||advanced_overlay||advanced_effects||advanced_framegen)?L"Graphics options *":L"Graphics options");
}
/* Graphics settings dialog: a quality preset and every option it sets, one row each. Choosing a preset fills the
   rows; changing any row makes the preset Custom. Ids: 220 preset, 230+field (CUSTOM_KEYS order), 203 brightness,
   204 refresh, 205 compression, 208 overlay. */
static CustomGraphics dialog_custom;static int dialog_filling;
static const wchar_t *const custom_labels[CUSTOM_FIELDS]={L"Texture detail",L"Texture filtering",L"Anti-aliasing",L"Sharpening",
    L"Dynamic lights",L"Light flares",L"Detail textures",L"Bullet impact effects",
    L"HDR lighting",L"Tone mapping",L"Ambient occlusion",L"Bloom",L"Eye adaptation",L"Color grade",L"Surface materials",
    L"Sun shadows",L"Contact shadows",L"Volumetric light",L"Foliage smoothing",L"NVIDIA Reflex",L"Frame Generation"};
#include "platinum_tips.h"
static void custom_dialog_fill(HWND window,const CustomGraphics *c){
    dialog_filling=1;
    for(int i=0;i<CUSTOM_FIELDS;i++)SendMessageW(GetDlgItem(window,230+i),CB_SETCURSEL,*custom_field((CustomGraphics*)c,i),0);
    dialog_filling=0;
}
static void custom_dialog_read(HWND window,CustomGraphics *c){
    for(int i=0;i<CUSTOM_FIELDS;i++){int value=(int)SendMessageW(GetDlgItem(window,230+i),CB_GETCURSEL,0,0);
        *custom_field(c,i)=value<0?0:value>custom_maximum[i]?custom_maximum[i]:value;}
}
/* Rows whose effect needs another one stay visible but are greyed out, as custom_quality ignores them. */
static void custom_dialog_enable(HWND window){
    CustomGraphics c;custom_dialog_read(window,&c);
    detect_gpu();
    const int temporal=c.aa==1||c.aa==2;
    const int enabled[CUSTOM_FIELDS]={1,1,1,1,1,1,1,1, 1,1,1,1,c.hdr,1,1, temporal,temporal&&c.shadows,temporal,1,gpu_rtx_mb>0,c.aa==2&&frame_gen_hardware()};
    for(int i=0;i<CUSTOM_FIELDS;i++){HWND combo=GetDlgItem(window,230+i);
        if(IsWindowEnabled(combo)!=(enabled[i]!=0)){EnableWindow(combo,enabled[i]);InvalidateRect(combo,NULL,TRUE);}}
}
static void custom_dialog_preset(HWND window,int preset){
    if(preset==3)dialog_custom=custom_saved?custom_graphics:dialog_custom;
    else{GraphicsQuality q=effective_quality(preset,0);dialog_custom=quality_custom(&q);}
    custom_dialog_fill(window,&dialog_custom);custom_dialog_enable(window);
}
static LRESULT CALLBACK advanced_proc(HWND window,UINT message,WPARAM w,LPARAM l){
    {LRESULT handled;if(shell_dialog_message(window,message,w,&handled))return handled;}
    if(message==WM_CREATE){
        static const wchar_t *const options[CUSTOM_FIELDS][7]={
            {L"Full detail",L"Half detail",L"Quarter detail"},
            {L"Bilinear",L"Trilinear",L"2x anisotropic",L"4x anisotropic",L"8x anisotropic",L"16x anisotropic"},
            {L"Off",L"TAA",L"DLAA (NVIDIA RTX)",L"2x MSAA",L"4x MSAA",L"8x MSAA"},
            {L"Off",L"On"},{L"Off",L"On"},{L"Off",L"On"},{L"Off",L"On"},{L"Off",L"On - dust, sparks and marks"},
            {L"Off",L"On"},{L"Off",L"Highlight roll-off",L"Filmic",L"AgX (modern filmic)"},{L"Off",L"SSAO",L"GTAO (ground truth)"},
            {L"Off",L"On"},{L"Off",L"On"},{L"Off",L"On"},{L"Off",L"On - normal and reflection maps"},
            {L"Off",L"Medium",L"High"},{L"Off",L"On"},{L"Off",L"On - sun shafts"},{L"Off",L"On"},
            {L"Off",L"On - low latency",L"On + Boost"},{L"Off",L"On - DLSS 2x frames"}};
        int preset=(int)SendMessageW(preset_combo,CB_GETCURSEL,0,0);if(preset<0||preset>3)preset=1;
        control(window,L"STATIC",L"Quality preset",0,20,13,170,24,0);
        HWND preset_list=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,196,10,290,160,220);
        combo_item(preset_list,L"Low (original look)");combo_item(preset_list,L"High");combo_item(preset_list,L"Ultra");combo_item(preset_list,L"Custom");
        SendMessageW(preset_list,CB_SETCURSEL,preset,0);
        control(window,L"STATIC",L"Change any setting below and the preset becomes Custom.",0,516,13,466,24,0);
        control(window,L"STATIC",L"IMAGE",0,20,50,300,22,0);
        control(window,L"STATIC",L"DIRECTX 12 EFFECTS",0,516,50,300,22,0);
        for(int i=0;i<CUSTOM_FIELDS;i++){
            int left=i<8,row=left?i:i-8,x=left?20:516,y=76+row*38;
            control(window,L"STATIC",custom_labels[i],0,x,y+3,170,24,0);
            HWND combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,x+176,y,290,220,230+i);
            for(int j=0;j<7&&options[i][j];j++)combo_item(combo,options[i][j]);
        }
        control(window,L"STATIC",L"GENERAL",0,20,384,300,22,0);
        control(window,L"STATIC",L"Brightness (gamma)",0,20,411,170,24,0);
        HWND gamma_combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,196,408,290,220,203);
        {const wchar_t *gamma[]={L"Keep in-game calibration",L"1.0 - neutral",L"1.1",L"1.2",L"1.3",L"1.4",L"1.5 - brighter"};
         for(int j=0;j<7;j++)combo_item(gamma_combo,gamma[j]);}
        SendMessageW(gamma_combo,CB_SETCURSEL,advanced_brightness,0);
        control(window,L"STATIC",L"Fullscreen refresh rate",0,20,449,170,24,0);
        HWND refresh_combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,196,446,290,220,204);
        combo_item(refresh_combo,L"Automatic");SendMessageW(refresh_combo,CB_SETITEMDATA,0,0);
        int resolution=(int)SendMessageW(resolution_combo,CB_GETCURSEL,0,0),width,height,rates[128];
        display_dimensions(resolution>=0&&resolution<=7?resolution:3,&width,&height);
        int count=display_rates(width,height,rates),selection=0;
        for(int i=1;i<count;i++){wchar_t label[40];swprintf(label,40,L"%d Hz",rates[i]);combo_item(refresh_combo,label);
            SendMessageW(refresh_combo,CB_SETITEMDATA,i,rates[i]);if(rates[i]==advanced_refresh)selection=i;}
        SendMessageW(refresh_combo,CB_SETCURSEL,selection,0);
        control(window,L"STATIC",L"Texture compression",0,20,487,170,24,0);
        HWND compression_combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,196,484,290,160,205);
        combo_item(compression_combo,L"Keep in-game setting");combo_item(compression_combo,L"On - lower memory use");combo_item(compression_combo,L"Off - uncompressed textures");
        SendMessageW(compression_combo,CB_SETCURSEL,advanced_compression,0);
        control(window,L"STATIC",L"Performance overlay",0,20,525,170,24,0);
        HWND overlay_combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,196,522,290,180,208);
        combo_item(overlay_combo,L"Keep in-game choice");combo_item(overlay_combo,L"Off");combo_item(overlay_combo,L"FPS counter");combo_item(overlay_combo,L"FPS + connection graph");
        SendMessageW(overlay_combo,CB_SETCURSEL,advanced_overlay,0);
        control(window,L"STATIC",L"Sun shadows and volumetric light need TAA or DLAA. Frame Generation needs DLAA on an\nNVIDIA RTX 40 or newer card. OpenGL (Safe Start) uses only the Image settings.",0,20,573,962,46,0);
        control(window,L"BUTTON",L"Graphics info",BS_OWNERDRAW|WS_TABSTOP,20,626,140,36,207);
        control(window,L"BUTTON",L"Restore defaults",BS_OWNERDRAW|WS_TABSTOP,172,626,160,36,206);
        control(window,L"BUTTON",L"Cancel",BS_OWNERDRAW|WS_TABSTOP,716,626,128,36,IDCANCEL);
        control(window,L"BUTTON",L"Save",BS_OWNERDRAW|WS_TABSTOP,856,626,126,36,IDOK);
        memset(&dialog_custom,0,sizeof(dialog_custom));
        {GraphicsQuality q=effective_quality(preset==3?1:preset,0);dialog_custom=quality_custom(&q);}
        custom_dialog_preset(window,preset);
        return 0;
    }
    if(message==WM_CTLCOLORSTATIC||message==WM_CTLCOLOREDIT||message==WM_CTLCOLORLISTBOX||message==WM_DRAWITEM||message==WM_MEASUREITEM)
        return window_proc(window,message,w,l);
    if(message==WM_COMMAND&&LOWORD(w)==207){open_graphics_report(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==220&&HIWORD(w)==CBN_SELCHANGE){
        int preset=(int)SendMessageW(GetDlgItem(window,220),CB_GETCURSEL,0,0);
        if(preset>=0&&preset<=3)custom_dialog_preset(window,preset);return 0;
    }
    if(message==WM_COMMAND&&LOWORD(w)>=230&&LOWORD(w)<230+CUSTOM_FIELDS&&HIWORD(w)==CBN_SELCHANGE&&!dialog_filling){
        custom_dialog_read(window,&dialog_custom);
        HWND preset_list=GetDlgItem(window,220);
        if(SendMessageW(preset_list,CB_GETCURSEL,0,0)!=3){SendMessageW(preset_list,CB_SETCURSEL,3,0);InvalidateRect(preset_list,NULL,TRUE);}
        custom_dialog_enable(window);return 0;
    }
    if(message==WM_COMMAND&&LOWORD(w)==206){
        SendMessageW(GetDlgItem(window,220),CB_SETCURSEL,1,0);custom_dialog_preset(window,1);
        const int ids[]={203,204,205,208};for(int i=0;i<4;i++)SendMessageW(GetDlgItem(window,ids[i]),CB_SETCURSEL,0,0);
        return 0;
    }
    if(message==WM_COMMAND&&LOWORD(w)==IDOK){
        int preset=(int)SendMessageW(GetDlgItem(window,220),CB_GETCURSEL,0,0);if(preset<0||preset>3)return 0;
        int previous[]={advanced_texture,advanced_filter,advanced_aa,advanced_brightness,advanced_refresh,advanced_compression,advanced_overlay,advanced_effects,advanced_framegen};
        int previous_preset=(int)SendMessageW(preset_combo,CB_GETCURSEL,0,0),previous_saved=custom_saved;CustomGraphics previous_custom=custom_graphics;
        int brightness=(int)SendMessageW(GetDlgItem(window,203),CB_GETCURSEL,0,0);advanced_brightness=brightness>=0&&brightness<=6?brightness:0;
        HWND refresh_combo=GetDlgItem(window,204);int selection=(int)SendMessageW(refresh_combo,CB_GETCURSEL,0,0);
        int refresh=(int)SendMessageW(refresh_combo,CB_GETITEMDATA,selection,0);
        advanced_refresh=refresh>=0&&refresh<=480?refresh:0;
        int compression=(int)SendMessageW(GetDlgItem(window,205),CB_GETCURSEL,0,0);advanced_compression=compression>=0&&compression<=2?compression:0;
        int overlay=(int)SendMessageW(GetDlgItem(window,208),CB_GETCURSEL,0,0);advanced_overlay=overlay>=0&&overlay<=3?overlay:0;
        /* the old per-preset overrides are part of the Custom set now */
        advanced_texture=advanced_filter=advanced_aa=advanced_effects=advanced_framegen=0;
        if(preset==3){custom_dialog_read(window,&custom_graphics);custom_saved=1;}
        SendMessageW(preset_combo,CB_SETCURSEL,preset,0);shown_preset=preset;
        if(!save_graphics_preferences()){
            advanced_texture=previous[0];advanced_filter=previous[1];advanced_aa=previous[2];advanced_brightness=previous[3];advanced_refresh=previous[4];advanced_compression=previous[5];advanced_overlay=previous[6];advanced_effects=previous[7];advanced_framegen=previous[8];
            custom_graphics=previous_custom;custom_saved=previous_saved;SendMessageW(preset_combo,CB_SETCURSEL,previous_preset,0);shown_preset=previous_preset;
            error(L"Graphics settings could not be saved. Check that the game folder is writable.");return 0;}
        update_graphics_summary();
        SetWindowTextW(GetDlgItem(GetWindow(window,GW_OWNER),114),L"Graphics settings saved");
        SendMessageW(window,WM_CLOSE,0,0);return 0;
    }
    if(message==WM_COMMAND&&LOWORD(w)==IDCANCEL){SendMessageW(window,WM_CLOSE,0,0);return 0;}
    if(message==WM_CLOSE){HWND parent=GetWindow(window,GW_OWNER);EnableWindow(parent,TRUE);DestroyWindow(window);advanced_window=NULL;SetActiveWindow(parent);return 0;}
    return DefWindowProcW(window,message,w,l);
}
static LRESULT CALLBACK report_proc(HWND window,UINT message,WPARAM w,LPARAM l){
    {LRESULT handled;if(shell_dialog_message(window,message,w,&handled))return handled;}
    if(message==WM_CREATE){
        platinum_graphics_report(root,report_text,8192);
        HWND text=control(window,L"EDIT",L"",ES_MULTILINE|ES_READONLY|ES_AUTOVSCROLL|WS_VSCROLL|WS_TABSTOP,20,18,706,400,301);
        SendMessageW(text,EM_SETLIMITTEXT,8192,0);SetWindowTextW(text,report_text);
        control(window,L"BUTTON",L"Save report",BS_OWNERDRAW|WS_TABSTOP,20,435,230,36,303);control(window,L"BUTTON",L"Report a problem",BS_OWNERDRAW|WS_TABSTOP,266,435,230,36,304);
        control(window,L"BUTTON",L"Close",BS_OWNERDRAW|WS_TABSTOP,516,435,210,36,IDCANCEL);return 0;
    }
    if(message==WM_CTLCOLORSTATIC||message==WM_CTLCOLOREDIT||message==WM_CTLCOLORLISTBOX||message==WM_DRAWITEM||message==WM_MEASUREITEM)
        return window_proc(window,message,w,l);
    if(message==WM_COMMAND&&LOWORD(w)==304){report_problem(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==303){
        if(platinum_save_graphics_report(root,report_text))SetWindowTextW(GetDlgItem(window,303),L"Saved to profile folder");
        else error(L"The graphics report could not be saved. Check that the game folder is writable.");return 0;
    }
    if(message==WM_COMMAND&&(LOWORD(w)==IDCANCEL||LOWORD(w)==IDOK)){SendMessageW(window,WM_CLOSE,0,0);return 0;}
    if(message==WM_CLOSE){HWND parent=GetWindow(window,GW_OWNER);EnableWindow(parent,TRUE);DestroyWindow(window);SetActiveWindow(parent);return 0;}
    if(message==WM_DESTROY){report_window=NULL;return 0;}
    return DefWindowProcW(window,message,w,l);
}
static void open_graphics_report(HWND parent){
    if(report_window){SetForegroundWindow(report_window);return;}
    RECT bounds;GetWindowRect(parent,&bounds);MONITORINFO monitor={0};monitor.cbSize=sizeof(monitor);
    GetMonitorInfoW(MonitorFromWindow(parent,MONITOR_DEFAULTTONEAREST),&monitor);
    int x=bounds.left+(bounds.right-bounds.left-760)/2,y=bounds.top+(bounds.bottom-bounds.top-(530+SHELL_DIALOG_HEADER))/2;
    if(x+760>monitor.rcWork.right)x=monitor.rcWork.right-760;if(x<monitor.rcWork.left)x=monitor.rcWork.left;
    if(y+530+SHELL_DIALOG_HEADER>monitor.rcWork.bottom)y=monitor.rcWork.bottom-530-SHELL_DIALOG_HEADER;if(y<monitor.rcWork.top)y=monitor.rcWork.top;
    report_window=CreateWindowExW(WS_EX_DLGMODALFRAME,L"TrueCombatPlatinumGraphicsReport",tr(L"TrueCombat: Platinum - Graphics report"),
        WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU,x,y,760,530+SHELL_DIALOG_HEADER,parent,NULL,GetModuleHandleW(NULL),NULL);
    if(!report_window)return;
    BOOL dark=TRUE;DwmSetWindowAttribute(report_window,20,&dark,sizeof(dark));
    EnableWindow(parent,FALSE);ShowWindow(report_window,SW_SHOW);SetFocus(GetDlgItem(report_window,301));
}
static void open_advanced(HWND parent){
    if(advanced_window){SetForegroundWindow(advanced_window);return;}
    RECT bounds;GetWindowRect(parent,&bounds);MONITORINFO monitor={0};monitor.cbSize=sizeof(monitor);
    GetMonitorInfoW(MonitorFromWindow(parent,MONITOR_DEFAULTTONEAREST),&monitor);
    int x=bounds.left+(bounds.right-bounds.left-1000)/2,y=bounds.top+(bounds.bottom-bounds.top-(700+SHELL_DIALOG_HEADER))/2;
    if(x+1000>monitor.rcWork.right)x=monitor.rcWork.right-1000;if(x<monitor.rcWork.left)x=monitor.rcWork.left;
    if(y+700+SHELL_DIALOG_HEADER>monitor.rcWork.bottom)y=monitor.rcWork.bottom-700-SHELL_DIALOG_HEADER;if(y<monitor.rcWork.top)y=monitor.rcWork.top;
    advanced_window=CreateWindowExW(WS_EX_DLGMODALFRAME,L"TrueCombatPlatinumGraphics",tr(L"TrueCombat: Platinum - Graphics settings"),
        WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU,x,y,1000,700+SHELL_DIALOG_HEADER,parent,NULL,GetModuleHandleW(NULL),NULL);
    if(!advanced_window)return;
    BOOL dark=TRUE;DwmSetWindowAttribute(advanced_window,20,&dark,sizeof(dark));
    EnableWindow(parent,FALSE);ShowWindow(advanced_window,SW_SHOW);SetFocus(GetDlgItem(advanced_window,220));
}
static int game_missing(void){
    wchar_t engine[2300];swprintf(engine,2300,L"%ls\\engine\\platinum-engine.bin",root);
    return GetFileAttributesW(engine)==INVALID_FILE_ATTRIBUTES;
}
#include "platinum_versions.h"
#include "platinum_profile.h"
#include "platinum_staffkey.h" /* 0.36.0 truecombat://staffkey/ */
#include "platinum_namecolour.h"
#include "platinum_pages.h"
#include "platinum_account.h" /* 0.37.0 player accounts: truecombat://account/, link with phone, profiles, looking for a squad */
#include "platinum_pad.h"   /* 0.37.0 controller navigation */
/* The launcher reopens where the player left it, in normal interactive use only
   (never for captures, checks or automated launches). */
static int window_placement_allowed(void){
    return !capture_ui_path[0]&&!compact_ui&&!verify_chrome&&!verify_stop_ui&&!auto_run&&!save_only&&!graphics_options&&!graphics_info&&!banner_preview;
}
static int window_placement_restore(int *x,int *y,int *width,int *height,int *maximized){
    if(!window_placement_allowed())return 0;
    wchar_t value[96];GetPrivateProfileStringW(L"Launcher",L"Window3",L"",value,96,ini);
    long left,top,w,h;int zoomed=0;
    if(swscanf(value,L"%ld,%ld,%ld,%ld,%d",&left,&top,&w,&h,&zoomed)!=5||w<960||h<600||w>16384||h>16384)return 0;
    RECT r={left,top,left+w,top+h};HMONITOR monitor=MonitorFromRect(&r,MONITOR_DEFAULTTONULL);if(!monitor)return 0;
    MONITORINFO info={sizeof(info),{0},{0},0};if(!GetMonitorInfoW(monitor,&info))return 0;
    RECT visible;if(!IntersectRect(&visible,&r,&info.rcWork)||visible.right-visible.left<200||visible.bottom-visible.top<120)return 0;
    if(w>info.rcWork.right-info.rcWork.left)w=info.rcWork.right-info.rcWork.left;
    if(h>info.rcWork.bottom-info.rcWork.top)h=info.rcWork.bottom-info.rcWork.top;
    *x=left;*y=top;*width=(int)w;*height=(int)h;*maximized=zoomed!=0;return 1;
}
/* Quick Play: join the best public server, or say why nothing was picked. */
/* ---- notification-area icon: "minimize to tray", start with Windows, update notices ---- */
#define WM_PLATINUM_TRAY (WM_APP+40)
static int trayShown,trayTemporary;
static int trayNoticeKind; /* 1 = the players-online notice (platinum_playalert.h) is the one showing */
static void tray_data(HWND window,NOTIFYICONDATAW *data){
    memset(data,0,sizeof(*data));data->cbSize=sizeof(*data);data->hWnd=window;data->uID=1;
}
static void tray_add(HWND window){
    if(trayShown)return;
    NOTIFYICONDATAW data;tray_data(window,&data);
    data.uFlags=NIF_MESSAGE|NIF_ICON|NIF_TIP;data.uCallbackMessage=WM_PLATINUM_TRAY;
    data.hIcon=LoadIconW(GetModuleHandleW(NULL),MAKEINTRESOURCEW(1));if(!data.hIcon)data.hIcon=LoadIconW(NULL,IDI_APPLICATION);
    wcscpy(data.szTip,L"TrueCombat: Platinum");
    trayShown=Shell_NotifyIconW(NIM_ADD,&data)!=0;
}
static void tray_remove(HWND window){
    if(!trayShown)return;
    NOTIFYICONDATAW data;tray_data(window,&data);Shell_NotifyIconW(NIM_DELETE,&data);trayShown=trayTemporary=0;
}
static void tray_restore(HWND window){
    ShowWindow(window,IsIconic(window)?SW_RESTORE:SW_SHOW);SetForegroundWindow(window);tray_remove(window);
}
/* A Windows notification from the launcher's own icon; never a pop-up window. */
static void tray_notify(HWND window,const wchar_t *title,const wchar_t *text){
    if(!trayShown){tray_add(window);trayTemporary=trayShown;}
    if(!trayShown)return;
    trayNoticeKind=0;
    NOTIFYICONDATAW data;tray_data(window,&data);data.uFlags=NIF_INFO;data.dwInfoFlags=NIIF_INFO;
    wcsncpy(data.szInfoTitle,title,63);wcsncpy(data.szInfo,text,255);
    Shell_NotifyIconW(NIM_MODIFY,&data);
}
/* Launcher 2.5.0 "Keep in the tray" ([Launcher] TrayOnClose, off by default): minimize and close hide the main
 * window in the notification area; a click on the icon brings it back, Quit in the tray panel ends it. */
static int tray_keep(void){return GetPrivateProfileIntW(L"Launcher",L"TrayOnClose",0,ini)!=0;}
static int tray_hide(HWND window){
    if(!tray_keep()||!shell_main(window)||loading)return 0;
    tray_add(window);if(!trayShown)return 0;trayTemporary=0;ShowWindow(window,SW_HIDE);
    static int told;if(!told){told=1;tray_notify(window,L"TrueCombat: Platinum",tr(L"The launcher is still running in the tray. Right-click the icon to quit."));}
    return 1;
}
#include "platinum_playalert.h" /* 0.38.0: players-online notice */
/* Tray quick panel (0.37.0): the version and update state, players online, and the ways to start
   without opening the launcher. Server counts come from the last list read (no network from here
   unless Quick Play needs a fresh list). */
static void tray_panel(HWND window){
    HMENU menu=CreatePopupMenu();
    LONG state=update_visible_state();int busy=game_missing()||game_running();
    wchar_t line[160];
    const wchar_t *status=state==UPDATE_READY?L"update ready to install":state==UPDATE_AVAILABLE?L"update available":
        state==UPDATE_DOWNLOADING||state==UPDATE_VERIFYING?L"downloading an update":state==UPDATE_CURRENT?L"up to date":L"";
    swprintf(line,160,status[0]?L"TrueCombat: Platinum %ls  \x00B7  %ls":L"TrueCombat: Platinum %ls",updateCurrent[0]?updateCurrent:L"",tr(status));
    AppendMenuW(menu,MF_STRING|MF_DISABLED,0,line);
    if(browserUpdated&&GetTickCount()-browserUpdated<10*60*1000&&!browserBusy){
        int servers=0,players=0;LONG total=browserCount;
        for(LONG i=0;i<total;++i)if(browserEntries[i].state==BROWSER_ONLINE&&!browserEntries[i].local){++servers;players+=browser_humans(&browserEntries[i]);}
        swprintf(line,160,tr(L"%d playing on %d servers"),players,servers);AppendMenuW(menu,MF_STRING|MF_DISABLED,0,line);
    }
    AppendMenuW(menu,MF_SEPARATOR,0,NULL);
    if(game_running())AppendMenuW(menu,MF_STRING,9201,L"Back to the game");
    else{
        AppendMenuW(menu,MF_STRING|(busy?MF_GRAYED:0),9202,L"Quick Play: join the best server");
        if(PLATINUM_NATIVE)AppendMenuW(menu,MF_STRING|(busy?MF_GRAYED:0),9203,L"Practice offline with bots");
        if(PLATINUM_NATIVE)AppendMenuW(menu,MF_STRING|(busy?MF_GRAYED:0),9210,L"Firing range");
        AppendMenuW(menu,MF_STRING|(busy?MF_GRAYED:0),9204,L"Open the game menu");
    }
    if(state==UPDATE_AVAILABLE||state==UPDATE_READY)AppendMenuW(menu,MF_STRING|(game_running()?MF_GRAYED:0),9205,state==UPDATE_READY?L"Install the update":L"Download the update");
    AppendMenuW(menu,MF_SEPARATOR,0,NULL);
    AppendMenuW(menu,MF_STRING,9206,L"Servers");AppendMenuW(menu,MF_STRING,9207,L"News");
    AppendMenuW(menu,MF_SEPARATOR,0,NULL);
    AppendMenuW(menu,MF_STRING,9208,L"Open TrueCombat: Platinum");AppendMenuW(menu,MF_STRING,9209,L"Quit");
    SetMenuDefaultItem(menu,9208,FALSE);
    POINT p;GetCursorPos(&p);SetForegroundWindow(window);
    int id=TrackPopupMenu(menu,TPM_RIGHTALIGN|TPM_BOTTOMALIGN|TPM_RETURNCMD,p.x,p.y,0,window,NULL);DestroyMenu(menu);
    PostMessageW(window,WM_NULL,0,0);   /* lets the menu close when the user clicks elsewhere */
    switch(id){
    case 9201:ui_focus_game();break;
    case 9202:PostMessageW(window,WM_COMMAND,128,0);break;
    case 9203:PostMessageW(window,WM_COMMAND,126,0);break;
    case 9210:PostMessageW(window,WM_COMMAND,9310,0);break;
    case 9204:PostMessageW(window,WM_COMMAND,112,0);break;
    case 9205:tray_restore(window);shell_set_tab(window,0);PostMessageW(window,WM_COMMAND,117,0);break;
    case 9206:tray_restore(window);shell_set_tab(window,1);break;
    case 9207:tray_restore(window);shell_set_tab(window,2);break;
    case 9208:tray_restore(window);break;
    case 9209:DestroyWindow(window);break;
    }
}
/* The game window is up and the launcher was asked to stay: bring the main window back, out of the way. */
static void shell_resume(HWND window){
    loading=0;
    SetWindowPos(window,NULL,loadingRestore.left,loadingRestore.top,loadingRestore.right-loadingRestore.left,loadingRestore.bottom-loadingRestore.top,SWP_NOZORDER|SWP_NOACTIVATE);
    shell_layout(window);shell_set_tab(window,shellTab);
    SetTimer(window,12,1000,NULL);
    if(options.window==1){tray_add(window);ShowWindow(window,SW_HIDE);}
    else ShowWindow(window,SW_MINIMIZE);
}
/* Interface size: the whole design scales with the window, so the option is a window size. */
static void interface_size_apply(HWND window){
    if(IsZoomed(window)||IsIconic(window)||loading)return;
    RECT r;GetWindowRect(window,&r);
    UINT dpi=shell_window_dpi(window);
    int width=MulDiv(1280*optionSizes[options.size]/100,dpi,96),height=MulDiv(800*optionSizes[options.size]/100,dpi,96);
    HMONITOR monitor=MonitorFromWindow(window,MONITOR_DEFAULTTONEAREST);MONITORINFO info;memset(&info,0,sizeof(info));info.cbSize=sizeof(info);
    if(GetMonitorInfoW(monitor,&info)){
        int maxWidth=info.rcWork.right-info.rcWork.left,maxHeight=info.rcWork.bottom-info.rcWork.top;
        if(width>maxWidth){width=maxWidth;height=width*800/1280;}
        if(height>maxHeight){height=maxHeight;width=height*1280/800;}
    }
    int x=(r.left+r.right-width)/2,y=(r.top+r.bottom-height)/2;
    if(GetMonitorInfoW(monitor,&info)){if(x<info.rcWork.left)x=info.rcWork.left;if(y<info.rcWork.top)y=info.rcWork.top;}
    SetWindowPos(window,NULL,x,y,width,height,SWP_NOZORDER|SWP_NOACTIVATE);
}
/* PLAY's arrow: the other ways to start. */
static void ui_play_menu(HWND window){
    HMENU menu=CreatePopupMenu();int busy=game_missing()||game_running();
    LONG state=update_visible_state();
    if(state==UPDATE_DOWNLOADING){AppendMenuW(menu,MF_STRING,117,L"Cancel the download");AppendMenuW(menu,MF_SEPARATOR,0,NULL);}
    AppendMenuW(menu,MF_STRING|(busy?MF_GRAYED:0),111,PLATINUM_NATIVE?L"Safe start  (OpenGL, 1280 x 720 window)":L"Safe start  (1280 x 720 window)");
    AppendMenuW(menu,MF_STRING|(busy?MF_GRAYED:0),112,L"Open the game menu");
    AppendMenuW(menu,MF_SEPARATOR,0,NULL);
    if(PLATINUM_NATIVE)AppendMenuW(menu,MF_STRING|(busy?MF_GRAYED:0),126,L"Practice offline with bots");
    if(PLATINUM_NATIVE)AppendMenuW(menu,MF_STRING|(busy?MF_GRAYED:0),9310,L"Firing range  (targets at 10 to 100 m)");
    AppendMenuW(menu,MF_STRING,116,L"Host a server...");
    AppendMenuW(menu,MF_SEPARATOR,0,NULL);
    AppendMenuW(menu,MF_STRING|(update_repair_ready()&&!game_running()?0:MF_GRAYED),152,L"Verify and repair game files");
    AppendMenuW(menu,MF_STRING,9101,L"Open the game folder");
    POINT p={sx_(1244),sy_(710)};ClientToScreen(window,&p);
    int id=TrackPopupMenu(menu,TPM_RIGHTALIGN|TPM_BOTTOMALIGN|TPM_RETURNCMD,p.x,p.y,0,window,NULL);DestroyMenu(menu);
    if(id)PostMessageW(window,WM_COMMAND,(WPARAM)id,0);
}
static void quick_play(HWND window){
    int pick=browser_quick_pick();
    if(pick<0){wcscpy(browserQuickNote,L"No public server to join right now. Refresh in a moment, or host one.");return;}
    browserQuickNote[0]=0;BrowserEntry *e=&browserEntries[pick];
    browserSelected=pick;SetWindowTextW(server_edit,e->address);
    PostMessageW(window,WM_COMMAND,104,0);
}
static LRESULT CALLBACK window_proc(HWND window,UINT message,WPARAM w,LPARAM l){
    if(message==WM_NCCALCSIZE&&w){
        if(IsZoomed(window)){
            RECT *client=&((NCCALCSIZE_PARAMS*)l)->rgrc[0];
            int padding=GetSystemMetrics(SM_CXPADDEDBORDER);
            InflateRect(client,-(GetSystemMetrics(SM_CXSIZEFRAME)+padding),
                               -(GetSystemMetrics(SM_CYSIZEFRAME)+padding));
        }
        return 0;
    }
    if(message==WM_NCHITTEST)return shell_hit_test(window,l);
    if(message==WM_NCACTIVATE)return TRUE;
    if(message==WM_NCPAINT)return 0;
    if(message==WM_GETMINMAXINFO){
        MINMAXINFO *limits=(MINMAXINFO*)l;UINT dpi=shell_window_dpi(window);
        limits->ptMinTrackSize.x=loading?474:MulDiv(960,dpi,96);limits->ptMinTrackSize.y=loading?BANNER_HEIGHT+75+shell_caption_height():MulDiv(600,dpi,96);
        MONITORINFO monitor={sizeof(monitor),{0},{0},0};
        if(GetMonitorInfoW(MonitorFromWindow(window,MONITOR_DEFAULTTONEAREST),&monitor)){
            limits->ptMaxPosition.x=monitor.rcWork.left-monitor.rcMonitor.left;
            limits->ptMaxPosition.y=monitor.rcWork.top-monitor.rcMonitor.top;
            limits->ptMaxSize.x=monitor.rcWork.right-monitor.rcWork.left;
            limits->ptMaxSize.y=monitor.rcWork.bottom-monitor.rcWork.top;
        }
        return 0;
    }
    if(message==WM_SIZE){shell_layout(window);shell_timers(window);return 0;}
    if(message==0x02E0&&shell_main(window)){   /* WM_DPICHANGED: take the size Windows suggests for the new monitor */
        const RECT *r=(const RECT*)l;tip_dpi_changed();
        SetWindowPos(window,NULL,r->left,r->top,r->right-r->left,r->bottom-r->top,SWP_NOZORDER|SWP_NOACTIVATE);return 0;}
    if((message==WM_SHOWWINDOW||message==WM_ACTIVATE||message==WM_WINDOWPOSCHANGED)&&shell_main(window))shell_timers(window);
    if((message==WM_SETFOCUS||message==WM_KILLFOCUS)&&shell_main(window)&&uiKeyboard&&!loading)shell_refresh(window);
    if(message==WM_ERASEBKGND)return 1;
    if(message==WM_CREATE){
        shellControlCount=0;
        const wchar_t *captions[]={L"Minimize",L"Maximize",L"Close",L"Support the project"};
        for(int i=0;i<4;++i){
            HWND button=CreateWindowExW(0,L"BUTTON",captions[i],WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_OWNERDRAW,
                0,0,i==3?SHELL_SUPPORT_W:46,i==3?30:shell_caption_height(),window,(HMENU)(INT_PTR)(SHELL_MINIMIZE+i),GetModuleHandleW(NULL),NULL);
            shellCaptionButtons[i]=button;
            WNDPROC original=(WNDPROC)SetWindowLongPtrW(button,GWLP_WNDPROC,(LONG_PTR)shell_button_proc);
            if(!shellButtonOriginal)shellButtonOriginal=original;
        }
        wchar_t server[256],name[64];
        GetPrivateProfileStringW(L"Player",L"Server",L"",server,256,ini);
        GetPrivateProfileStringW(L"Player",L"Name",L"Player",name,64,ini);
        if(forced_server[0])wcscpy(server,forced_server);if(forced_name[0])wcscpy(name,forced_name);else adopt_game_name(name,64);
        advanced_texture=forced_texture>=0?forced_texture:preference(L"TextureDetail",0,3);
        advanced_filter=forced_filter>=0?forced_filter:preference(L"Filtering",0,6);
        advanced_aa=forced_aa>=0?forced_aa:preference(L"AntiAliasing",0,4);
        advanced_brightness=forced_brightness>=0?forced_brightness:preference(L"Brightness",0,6);
        advanced_refresh=forced_refresh>=0?forced_refresh:preference(L"RefreshHz",0,480);
        advanced_compression=forced_compression>=0?forced_compression:preference(L"TextureCompression",0,2);
        advanced_overlay=forced_overlay>=0?forced_overlay:preference(L"PerformanceOverlay",0,3);
        advanced_effects=preference(L"Effects",0,1);
        advanced_framegen=forced_framegen>=0?forced_framegen:preference(L"FrameGeneration",0,1);
        control(window,L"STATIC",L"PLAY",0,24,285,328,23,0);
        control(window,L"STATIC",L"DISPLAY & QUALITY",0,390,285,328,23,0);
        control(window,L"STATIC",L"Server address / recent servers",0,24,320,328,22,0);
        server_edit=control(window,L"COMBOBOX",L"",CBS_DROPDOWN|WS_TABSTOP|WS_VSCROLL,24,346,328,180,101);
        for(int i=1;i<=5;i++){wchar_t key[20],recent[256];swprintf(key,20,L"Server%d",i);GetPrivateProfileStringW(L"Recent",key,L"",recent,256,ini);if(valid_server(recent))combo_item(server_edit,recent);}
        SendMessageW(server_edit,CB_LIMITTEXT,253,0);SetWindowTextW(server_edit,server);
        control(window,L"STATIC",L"Player name",0,24,397,328,22,0);
        name_edit=control(window,L"EDIT",name,ES_AUTOHSCROLL|WS_TABSTOP,24,423,328,30,102);
        SendMessageW(name_edit,EM_SETLIMITTEXT,35,0); /* ET MAX_NAME_LENGTH 36, colour codes count */
        control(window,L"STATIC",L"Quality preset",0,390,320,328,22,0);
        preset_combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,390,346,328,160,107);
        combo_item(preset_combo,L"Low (original look)");combo_item(preset_combo,L"High");combo_item(preset_combo,L"Ultra");combo_item(preset_combo,L"Custom");
        custom_saved=custom_load();
        if(forced_custom_set){custom_graphics=forced_custom;custom_saved=1;}
        int preset=forced_preset>=0?forced_preset:preference(L"Preset",1,3);
        if(forced_preset<0&&preset<3&&(advanced_texture||advanced_filter||advanced_aa||advanced_effects||advanced_framegen)&&
           forced_texture<0&&forced_filter<0&&forced_aa<0&&forced_framegen<0){
            /* launchers before 1.2 kept these as overrides on top of a preset: the same choices are now a Custom set */
            GraphicsQuality q=effective_quality(preset,0);custom_graphics=quality_custom(&q);custom_saved=1;preset=3;
            advanced_texture=advanced_filter=advanced_aa=advanced_effects=advanced_framegen=0;
        }
        if(forced_preset<0){int imported=custom_import();if(imported>=0)preset=imported;}
        if(preset==3&&!custom_saved){GraphicsQuality q=effective_quality(1,0);custom_graphics=quality_custom(&q);custom_saved=1;}
        shown_preset=preset;
        SendMessageW(preset_combo,CB_SETCURSEL,preset,0);
        control(window,L"STATIC",L"Resolution",0,390,397,328,22,0);
        resolution_combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,390,423,328,240,108);
        const wchar_t *modes[]={L"Desktop resolution",L"1280 x 720",L"1600 x 900",L"1920 x 1080",L"2560 x 1440",L"1920 x 1200 (16:10)",L"1024 x 768 (4:3)",L"3840 x 2160 (4K)"};
        for(int i=0;i<8;i++)combo_item(resolution_combo,modes[i]);
        SendMessageW(resolution_combo,CB_SETCURSEL,forced_resolution>=0?forced_resolution:preference(L"Resolution",3,7),0);
        control(window,L"STATIC",L"Display mode",0,390,474,328,22,0);
        display_combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,390,500,328,150,109);
        combo_item(display_combo,L"Windowed");combo_item(display_combo,L"Borderless window");combo_item(display_combo,L"Fullscreen");
        SendMessageW(display_combo,CB_SETCURSEL,forced_display>=0?forced_display:preference(L"Display",0,2),0);
        preset_description=control(window,L"STATIC",L"",0,24,474,328,68,0);
        vsync_check=control(window,L"BUTTON",L"Vertical sync",BS_AUTOCHECKBOX|WS_TABSTOP,390,549,328,26,110);
        SendMessageW(vsync_check,BM_SETCHECK,preference(L"VSync",0,1)?BST_CHECKED:BST_UNCHECKED,0);
        control(window,L"BUTTON",L"Graphics options",BS_OWNERDRAW|WS_TABSTOP,390,580,328,28,113);
        control(window,L"BUTTON",L"PLAY",BS_OWNERDRAW|WS_TABSTOP,24,555,212,44,104);
        control(window,L"BUTTON",L"Safe start",BS_OWNERDRAW|WS_TABSTOP,248,555,104,44,111);
        control(window,L"BUTTON",L"Host a server",BS_OWNERDRAW|WS_TABSTOP,24,616,212,38,105);
        if(PLATINUM_NATIVE)control(window,L"BUTTON",L"Practice offline with bots",BS_OWNERDRAW|WS_TABSTOP,24,616,328,38,126);
        control(window,L"BUTTON",L"Stop server",BS_OWNERDRAW|WS_TABSTOP,248,616,104,38,106);
        control(window,L"BUTTON",L"Open game menu",BS_OWNERDRAW|WS_TABSTOP,390,616,328,38,112);
        control(window,L"BUTTON",L"Servers, hosting & frame rate...",BS_OWNERDRAW|WS_TABSTOP,24,674,328,34,116);
        control(window,L"BUTTON",L"Save graphics settings",BS_OWNERDRAW|WS_TABSTOP,390,674,328,34,114);
        control(window,L"BUTTON",L"Graphics report",BS_OWNERDRAW|WS_TABSTOP,20,346,148,42,115);
        control(window,L"BUTTON",L"Check for updates",BS_OWNERDRAW|WS_TABSTOP,20,700,148,30,117);
        ShowWindow(control(window,L"BUTTON",L"What's new",BS_OWNERDRAW|WS_TABSTOP,20,740,100,30,118),SW_HIDE);
        control(window,L"BUTTON",L"Versions",BS_OWNERDRAW|WS_TABSTOP,20,780,100,30,119);
        control(window,L"BUTTON",L"Launcher update",BS_OWNERDRAW|WS_TABSTOP,20,820,140,30,127);
        control(window,L"BUTTON",L"Play",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,120);
        control(window,L"BUTTON",L"Servers",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,121);
        control(window,L"BUTTON",L"News",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,122);
        ShowWindow(control(window,L"BUTTON",L"Refresh",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,123),SW_HIDE);
        ShowWindow(control(window,L"BUTTON",L"Quick play",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,128),SW_HIDE);
        ShowWindow(control(window,L"BUTTON",L"Open on GitHub",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,124),SW_HIDE);
        control(window,L"BUTTON",L"Controls",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,125);
        control(window,L"BUTTON",L"Profile & demos",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,129);
        control(window,L"BUTTON",L"Settings",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,130);
        control(window,L"BUTTON",L"Replays",BS_OWNERDRAW|WS_TABSTOP,20,20,100,30,131);
        /* Launcher options (Settings page): dropdowns are real controls, the rest is painted. Each saves the moment it changes. */
        {HWND combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,20,20,190,150,145);
         const wchar_t *pages[]={L"Play",L"Servers",L"News"};
         for(int i=0;i<3;++i)combo_item(combo,pages[i]);SendMessageW(combo,CB_SETCURSEL,options.startTab,0);
         combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,20,20,190,150,146);
         for(int i=0;i<3;++i)combo_item(combo,optionWindowNames[i]);SendMessageW(combo,CB_SETCURSEL,options.window,0);
         combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,20,20,190,240,147);
         combo_item(combo,L"Rotate maps");for(int i=0;i<6;++i)combo_item(combo,shellMapNames[i]);SendMessageW(combo,CB_SETCURSEL,options.background,0);
         combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,20,20,190,200,148);
         for(int i=0;i<5;++i)combo_item(combo,optionSizeNames[i]);SendMessageW(combo,CB_SETCURSEL,options.size,0);
         combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,20,20,190,220,149);
         for(int i=0;i<6;++i)combo_item(combo,optionSpeedNames[i]);SendMessageW(combo,CB_SETCURSEL,options.speed,0);
         /* Launch options: extra console commands, written into the launch config (not the command line). */
         wchar_t extra[LAUNCH_OPTIONS_MAX];GetPrivateProfileStringW(L"Launch",L"Options",L"",extra,LAUNCH_OPTIONS_MAX,ini);
         HWND edit=control(window,L"EDIT",extra,ES_AUTOHSCROLL|WS_TABSTOP,20,20,190,32,151);SendMessageW(edit,EM_SETLIMITTEXT,LAUNCH_OPTIONS_MAX-1,0);
         SendMessageW(edit,EM_SETCUEBANNER,TRUE,(LPARAM)L"+set cg_fov 100");
         /* Language (Settings > Launcher); names of languages are written in their own language */
         combo=control(window,L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,20,20,190,200,154);
         {const wchar_t *names[]={L"Automatic (Windows)",L"English",L"Deutsch",L"Fran\u00E7ais",L"Polski"};for(int i=0;i<5;++i)combo_item(combo,names[i]);}
         SendMessageW(combo,CB_SETCURSEL,options.lang,0);
         /* first start: the player name field of the welcome page */
         HWND welcome=control(window,L"EDIT",L"",ES_AUTOHSCROLL|WS_TABSTOP,20,20,448,36,156);SendMessageW(welcome,EM_SETLIMITTEXT,24,0);}
        updateWindow=window;
        if(!auto_run&&!save_only&&!verify_stop_ui&&updatePreview<0&&InterlockedCompareExchange(&updateState,0,0)==UPDATE_IDLE)update_begin_check();
        /* 2.6.2: after a failed apply the game check waits for Try again, but a newer launcher is still fetched */
        else if(!auto_run&&updatePreview<0&&InterlockedCompareExchange(&updateState,0,0)==UPDATE_FAILED&&options.autoLauncher&&updateLatestFeed[0])update_start(launcher_check_worker);
        shell_layout(window);
        update_graphics_summary();
        update_sync(window);
        if(!initial_tab&&!capture_ui_path[0]&&!auto_run)initial_tab=options.startTab;
        shell_set_tab(window,initial_tab);
        if(!auto_run&&!save_only&&!verify_stop_ui&&!verify_chrome&&!session_options&&!graphics_options&&!graphics_info&&(firstRunForced||!game_missing())&&(firstRunForced||(!capture_ui_path[0]&&first_run_needed())))
            PostMessageW(window,WM_APP+7,0,0);
        else if(crashPromptAllowed)PostMessageW(window,WM_APP+9,0,0);
        if(updateBlockedNotice&&!capture_ui_path[0]&&!auto_run)PostMessageW(window,WM_APP+12,0,0); /* 0.38.1: say which file the antivirus removed */
        if(controls_open)PostMessageW(window,WM_APP+8,0,0);
        if(versions_open)PostMessageW(window,WM_COMMAND,119,0);
        shell_timers(window);
        SetFocus(GetDlgItem(window,104));SendMessageW(window,WM_CHANGEUISTATE,MAKEWPARAM(UIS_SET,UISF_HIDEFOCUS|UISF_HIDEACCEL),0);SendMessageW(server_edit,CB_SETEDITSEL,0,MAKELPARAM(-1,0));
        if(verify_stop_ui){SetTimer(window,3,50,NULL);PostMessageW(window,WM_COMMAND,106,0);}
        if(session_options)PostMessageW(window,WM_COMMAND,157,0);
        SetTimer(window,PLAYALERT_TIMER,60000,NULL); /* 0.38.0 players-online notice, checked once a minute */
        if(save_only)PostMessageW(window,WM_COMMAND,114,0);
        else{
            if(banner_preview)PostMessageW(window,WM_APP,0,0);
            if(graphics_info)PostMessageW(window,WM_COMMAND,115,0);
            else if(graphics_options)PostMessageW(window,WM_COMMAND,113,0);
            if(auto_run)PostMessageW(window,WM_COMMAND,safe_launch?111:(menu_launch?112:104),0);
        }return 0;
    }
    if(message==WM_PLATINUM_UPDATE){
        update_sync(window);
        /* One notice per new state, and only while the launcher is not what the player is looking at. */
        static LONG noticed=-1;LONG state=update_visible_state();
        if(state!=noticed){
            if(options.notify&&noticed!=-1&&shell_main(window)&&!updateHeadless&&(GetForegroundWindow()!=window||!IsWindowVisible(window))&&
               (state==UPDATE_READY||(state==UPDATE_AVAILABLE&&!options.autoGame)))
                tray_notify(window,L"TrueCombat: Platinum",state==UPDATE_READY?L"An update is downloaded and ready to install.":L"A new version is available.");
            noticed=state;
        }
        return 0;}
    if(message==WM_APP+7){open_first_run(window);return 0;}
    if(message==WM_APP+9){crash_prompt(window);return 0;}
    if(message==WM_APP+12){updateBlockedNotice=0;MessageBoxW(window,updateError,TITLE,MB_OK|MB_ICONWARNING);return 0;}
    if(message==WM_APP+8||(message==WM_COMMAND&&LOWORD(w)==125)){open_binds(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==129){shell_set_tab(window,5);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==171&&shell_main(window)){open_name_colours(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==158&&shell_main(window)){profile_backup(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==172&&shell_main(window)){open_telemetry_view(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==157&&shell_main(window)){open_session(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==160&&shell_main(window)){uiSettingsTab=3;shell_set_tab(window,3);shell_show_page(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==162&&shell_main(window)){uiSettingsTab=2;shell_set_tab(window,3);shell_show_page(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==161&&shell_main(window)){ui_clear_caches(window);return 0;}
    if(message==WM_PLATINUM_BROWSER){
        if(!browserBusy&&InterlockedExchange(&browserQuickPending,0))quick_play(window);
        if(w==2)ui_feed_load_cache();
        {HWND nav=GetDlgItem(window,121);if(nav)InvalidateRect(nav,NULL,FALSE);}
        shellBodyDirty=1;InvalidateRect(window,NULL,FALSE);return 0;}
    if(message==WM_TIMER&&w==7){shell_animate(window);pad_poll(window);return 0;}
    if(message==WM_MOUSEWHEEL&&shell_main(window)&&shellTab==1){
        int rows=browser_view(),before=browserScroll;
        browserScroll+=GET_WHEEL_DELTA_WPARAM(w)>0?-3:3;if(browserScroll>rows-UI_SERVER_ROWS)browserScroll=rows-UI_SERVER_ROWS;if(browserScroll<0)browserScroll=0;
        if(browserScroll!=before){browserHot=-1;shellBodyDirty=1;InvalidateRect(window,NULL,FALSE);}return 0;}
    if(message==WM_MOUSEWHEEL&&shell_main(window)&&shellTab==6){
        pages_replay_scroll(GET_WHEEL_DELTA_WPARAM(w)>0?-3:3);shellBodyDirty=1;InvalidateRect(window,NULL,FALSE);return 0;}
    if(message==WM_MOUSEWHEEL&&shell_main(window)&&shellTab==2){
        int before=uiNewsScroll;ui_news_scroll(GET_WHEEL_DELTA_WPARAM(w)>0?-72:72);
        if(uiNewsScroll!=before){shellBodyDirty=1;InvalidateRect(window,NULL,FALSE);}return 0;}
    if((message==WM_MOUSEMOVE||message==WM_MOUSELEAVE||message==WM_LBUTTONDOWN||message==WM_LBUTTONDBLCLK)&&shell_main(window)){shell_body_mouse(window,message,l);if(message!=WM_MOUSEMOVE)return 0;}
    if(message==WM_SETCURSOR&&shell_main(window)&&LOWORD(l)==HTCLIENT&&(HWND)w==window&&uiHotKind!=H_NONE)return TRUE;
    /* The PLAY subtitle names the server it will join. */
    if(message==WM_COMMAND&&LOWORD(w)==101&&(HIWORD(w)==CBN_EDITCHANGE||HIWORD(w)==CBN_SELCHANGE||HIWORD(w)==CBN_CLOSEUP)&&shell_main(window)){
        shell_refresh(window);return 0;}
    /* Enter in the server address or player name plays (IsDialogMessage sends IDOK). */
    if(message==WM_COMMAND&&LOWORD(w)==IDOK&&shell_main(window)){
        HWND focus=GetFocus();
        if(focus&&(focus==name_edit||focus==server_edit||GetParent(focus)==server_edit)&&IsWindowEnabled(GetDlgItem(window,104)))
            PostMessageW(window,WM_COMMAND,104,0);
        return 0;}
    if(message==WM_COMMAND&&LOWORD(w)>=120&&LOWORD(w)<=122){shell_set_tab(window,LOWORD(w)-120);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==130){shell_set_tab(window,3);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==131){shell_set_tab(window,6);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)>=145&&LOWORD(w)<=149&&HIWORD(w)==CBN_SELCHANGE&&shell_main(window)){
        int value=(int)SendMessageW((HWND)l,CB_GETCURSEL,0,0);if(value<0)return 0;
        switch(LOWORD(w)){
        case 145:if(value<=2){options.startTab=value;options_set(L"StartTab",value);}break;
        case 146:if(value<=2){options.window=value;options_set(L"WhilePlaying",value);}break;
        case 147:if(value<=6){options.background=value;options_set(L"Background",value);}break;
        case 148:if(value<=4){options.size=value;options_set(L"InterfaceSize",value);interface_size_apply(window);}break;
        default:if(value<=5){options.speed=value;options_set(L"SpeedLimit",value);}break;
        }
        ui_saved();shell_refresh(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==154&&HIWORD(w)==CBN_SELCHANGE&&shell_main(window)){
        int value=(int)SendMessageW((HWND)l,CB_GETCURSEL,0,0);if(value>=0)ui_language_set(window,value);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==156&&shell_main(window))return 0;
    if(message==WM_COMMAND&&LOWORD(w)==151&&shell_main(window)&&!loading){
        if(HIWORD(w)==EN_CHANGE){wchar_t extra[LAUNCH_OPTIONS_MAX];GetWindowTextW((HWND)l,extra,LAUNCH_OPTIONS_MAX);
            launch_options_clean(extra);WritePrivateProfileStringW(L"Launch",L"Options",extra[0]?extra:NULL,ini);ui_saved();shell_refresh(window);}
        return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==152&&shell_main(window)){
        if(game_running()){MessageBoxW(window,L"Close the game first, then verify the files.",TITLE,MB_OK|MB_ICONINFORMATION);return 0;}
        InterlockedExchange(&updateUserAction,1);
        if(!update_repair_begin())MessageBoxW(window,L"The files can be checked once the game is installed from an official release and nothing else is downloading.",TITLE,MB_OK|MB_ICONINFORMATION);
        update_sync(window);shell_refresh(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==153&&shell_main(window)){move_game(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==150&&shell_main(window)){
        options_reset();
        const int ids[]={145,146,147,148,149},values[]={options.startTab,options.window,options.background,options.size,options.speed};
        for(int i=0;i<5;++i)SendMessageW(GetDlgItem(window,ids[i]),CB_SETCURSEL,values[i],0);
        shellReduceMotion=!shellSystemMotion;ui_back_release();interface_size_apply(window);
        shellBodyDirty=1;RedrawWindow(window,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN);return 0;}
    if(message==WM_COMMAND&&(LOWORD(w)==9101||LOWORD(w)==9102)&&shell_main(window)){
        wchar_t folder[2300];if(LOWORD(w)==9101)wcsncpy(folder,root,2299),folder[2299]=0;else swprintf(folder,2300,L"%ls\\profile",root);
        ShellExecuteW(window,L"open",folder,NULL,NULL,SW_SHOWNORMAL);return 0;}
    /* The launch bar shows the player name as it is typed. */
    if(message==WM_COMMAND&&LOWORD(w)==102&&HIWORD(w)==EN_CHANGE&&shell_main(window)&&!loading){shell_refresh(window);return 0;}
    if(message==WM_SIZING&&shell_main(window)&&!loading){
        /* Keep the 16:10 shape of the design while the window is dragged larger or smaller. */
        RECT *r=(RECT*)l;int width=r->right-r->left,height=r->bottom-r->top;
        if(w==WMSZ_TOP||w==WMSZ_BOTTOM){width=height*SHELL_CANVAS_W/SHELL_CANVAS_H;r->right=r->left+width;}
        else{height=width*SHELL_CANVAS_H/SHELL_CANVAS_W;if(w==WMSZ_TOPLEFT||w==WMSZ_TOPRIGHT)r->top=r->bottom-height;else r->bottom=r->top+height;}
        return TRUE;}
    if(message==WM_COPYDATA)return instance_receive(window,(const COPYDATASTRUCT*)l);
    if(message==WM_PLATINUM_INSTANCE){
        /* a truecombat://join link opened while this launcher was already running */
        if(game_running()||loading){tray_notify(window,L"TrueCombat: Platinum",tr(L"The game is already running. Close it first to join another server."));return 0;}
        wchar_t server[256];join_password[0]=0;join_team=0;
        if(!join_parse_url(instancePending,server,256))return 0;
        wcscpy(forced_server,server);SendMessageW(window,WM_COMMAND,104,0);
        forced_server[0]=0;join_password[0]=0;join_team=0;return 0;}
    if(message==WM_PLATINUM_TRAY){
        if(l==WM_LBUTTONUP||l==WM_LBUTTONDBLCLK)tray_restore(window);
        else if(l==WM_RBUTTONUP||l==WM_CONTEXTMENU)tray_panel(window);
        else if(l==NIN_BALLOONUSERCLICK)playalert_clicked(window);
        else if(l==NIN_BALLOONTIMEOUT)trayNoticeKind=0;
        return 0;}
    if(message==WM_TIMER&&w==PLAYALERT_TIMER){playalert_tick(window);return 0;}
    if(message==WM_ACTIVATE&&LOWORD(w)!=WA_INACTIVE&&trayTemporary&&shell_main(window)){tray_remove(window);}
    if(message==WM_TIMER&&w==12){
        /* The launcher stayed alive while the game ran: come back when it closes, if asked to. */
        if(!starting_game||WaitForSingleObject(starting_game,0)==WAIT_OBJECT_0){KillTimer(window,12);if(options.reopen)tray_restore(window);}
        shell_timers(window);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==123){browser_refresh(window);shellBodyDirty=1;InvalidateRect(window,NULL,FALSE);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==128){
        /* Use the list on screen when it is fresh, otherwise refresh first and pick when it lands. */
        if(!browserBusy&&browserUpdated&&GetTickCount()-browserUpdated<60000)quick_play(window);
        else{InterlockedExchange(&browserQuickPending,1);browser_refresh(window);}
        shellBodyDirty=1;InvalidateRect(window,NULL,FALSE);return 0;}
    if(message==WM_COMMAND&&LOWORD(w)==124){if(newsItems[0].url[0])ShellExecuteW(NULL,L"open",newsItems[0].url,NULL,NULL,SW_SHOWNORMAL);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==118){update_open_page();return 0;}
    if(message==WM_COMMAND && LOWORD(w)==119){open_versions(window);return 0;}
    if(message==WM_COMMAND&&(LOWORD(w)==104||LOWORD(w)==105||LOWORD(w)==111||LOWORD(w)==112)&&game_missing()){
        if(auto_run){process_result=3;DestroyWindow(window);return 0;}
        LONG state=InterlockedCompareExchange(&updateState,0,0);
        MessageBoxW(window,state==UPDATE_DOWNLOADING||state==UPDATE_VERIFYING?L"The game files are still downloading. You can play as soon as the installation finishes.":
            L"The game files aren't installed yet. Select Install on the bar above PLAY to download them.",TITLE,MB_OK|MB_ICONINFORMATION);
        if(state==UPDATE_AVAILABLE)update_button(window);update_sync(window);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==127){launcher_button(window);if(IsWindow(window))update_sync(window);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==117){update_button(window);if(IsWindow(window))update_sync(window);return 0;}
    if(message==WM_APP+3&&PLATINUM_NATIVE){
        if(verify_stop_ui){process_result=w?(int)w:(native_stop_ui_ticks?0:12);DestroyWindow(window);return 0;}
        native_stop_pending=0;
        EnableWindow(GetDlgItem(window,105),TRUE);EnableWindow(GetDlgItem(window,106),TRUE);
        SetWindowTextW(GetDlgItem(window,106),L"Stop server");
        MessageBoxW(window,w==0?L"Your local server has stopped.":w==4?L"No server from this game folder is running.":w==5?L"The server has not finished stopping. Check server-state/supervisor.log.":L"The server did not close cleanly. Check server-state/supervisor.log.",TITLE,MB_OK|(w?MB_ICONWARNING:MB_ICONINFORMATION));
        return 0;
    }
    if(message==WM_APP+2){
        int chrome_result=verify_chrome?shell_verify_chrome(window):0;
        if(chrome_result){
            process_result=chrome_result;DestroyWindow(window);return 0;
        }
        RedrawWindow(window,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);
        HWND capture=bindsWindow?bindsWindow:firstRunWindow?firstRunWindow:advanced_window?advanced_window:report_window?report_window:session_window?session_window:window;
        RedrawWindow(capture,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);
        for(int frame=0;frame<8;++frame){GdiFlush();DwmFlush();Sleep(30);}
        RECT r;GetWindowRect(capture,&r);
        if(capture!=window){GetClientRect(capture,&r);MapWindowPoints(capture,NULL,(POINT*)&r,2);}
        HDC dc=GetDC(capture),memory=CreateCompatibleDC(dc);
        HBITMAP bitmap=CreateCompatibleBitmap(dc,r.right-r.left,r.bottom-r.top);
        HGDIOBJ previous=SelectObject(memory,bitmap);
        int capture_children;
        if(capture!=window){
            /* Owned dialogs: copy what is on screen, so every child control is captured
               fully drawn (PrintWindow raced the dialog's own painting). */
            SetWindowPos(capture,HWND_TOPMOST,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_SHOWWINDOW);SetForegroundWindow(capture);
            RedrawWindow(capture,NULL,NULL,RDW_INVALIDATE|RDW_ERASE|RDW_ALLCHILDREN|RDW_UPDATENOW);
            for(int frame=0;frame<10;++frame){MSG pending;while(PeekMessageW(&pending,NULL,0,0,PM_REMOVE)){TranslateMessage(&pending);DispatchMessageW(&pending);}GdiFlush();DwmFlush();Sleep(30);}
            HDC screen=GetDC(NULL);
            capture_children=BitBlt(memory,0,0,r.right-r.left,r.bottom-r.top,screen,r.left,r.top,SRCCOPY|CAPTUREBLT)?2:0;
            ReleaseDC(NULL,screen);
        }else capture_children=PrintWindow(capture,memory,2)?1:0;
        if(capture_children==1){POINT origin={0,0};ClientToScreen(capture,&origin);
            for(HWND child=GetWindow(capture,GW_CHILD);child;child=GetWindow(child,GW_HWNDNEXT)){if(!IsWindowVisible(child))continue;RECT c;GetWindowRect(child,&c);
                HDC cdc=CreateCompatibleDC(dc);HBITMAP cb=CreateCompatibleBitmap(dc,c.right-c.left,c.bottom-c.top);HGDIOBJ old=SelectObject(cdc,cb);
                if(PrintWindow(child,cdc,0))BitBlt(memory,c.left-r.left,c.top-r.top,c.right-c.left,c.bottom-c.top,cdc,0,0,SRCCOPY);
                SelectObject(cdc,old);DeleteObject(cb);DeleteDC(cdc);}(void)origin;}
        if(capture_children&&(capture_children==2||shell_print_buttons(capture,memory))){
            GdiFlush();
            void *image=NULL;
            CLSID png={0x557cf406,0x1a04,0x11d3,{0x9a,0x73,0x00,0x00,0xf8,0x1e,0xf3,0x2e}};
            if(!GdipCreateBitmapFromHBITMAP(bitmap,NULL,&image)){
                process_result=GdipSaveImageToFile(image,capture_ui_path,&png,NULL)?3:0;
                GdipDisposeImage(image);
            }else process_result=3;
        }else process_result=3;
        SelectObject(memory,previous);DeleteObject(bitmap);DeleteDC(memory);ReleaseDC(capture,dc);
        DestroyWindow(window);return 0;
    }
    if(message==WM_APP){show_loading(window);return 0;}
    if(message==WM_CTLCOLORSTATIC||message==WM_CTLCOLOREDIT||message==WM_CTLCOLORLISTBOX){
        HDC dc=(HDC)w;HWND child=(HWND)l;
        if(message!=WM_CTLCOLORSTATIC||shell_is_class(child,L"Edit")){
            SetTextColor(dc,SHELL_TEXT);SetBkColor(dc,SHELL_FIELD);return (LRESULT)field_brush;
        }
        int main=shell_main(window)&&!loading;
        wchar_t text[48]=L"";GetWindowTextW(child,text,48);
        int heading=!main&&text[0];for(const wchar_t *p=text;*p;++p)if(*p>=L'a'&&*p<=L'z')heading=0;
        SetTextColor(dc,heading?SHELL_ACCENT_HOT:main?(child==preset_description?SHELL_SUBTLE:SHELL_MUTED):SHELL_SUBTLE);
        int panel=main||shell_is_class(window,L"TrueCombatPlatinumSession")||shell_is_class(window,L"TrueCombatPlatinumGraphics")||shell_is_class(window,L"TrueCombatPlatinumFirstRun")||shell_is_class(window,L"TrueCombatPlatinumBinds")||shell_is_class(window,L"TrueCombatPlatinumProfile")||shell_is_class(window,L"TrueCombatPlatinumNameColour");
        SetBkColor(dc,panel?SHELL_CARD:SHELL_BG);
        return (LRESULT)(panel?shellCardBrush:background_brush);
    }
    if(message==WM_MEASUREITEM){shell_measure(window,(MEASUREITEMSTRUCT*)l);return TRUE;}
    if(message==WM_DRAWITEM){
        DRAWITEMSTRUCT *item=(DRAWITEMSTRUCT*)l;
        if(item->CtlType==ODT_BUTTON||item->CtlType==ODT_COMBOBOX){
            shell_draw_button(item);return TRUE;
        }
    }
    if(message==WM_PAINT||message==WM_PRINTCLIENT){
        if(!loading&&shell_main(window)){RECT u;if(message==WM_PRINTCLIENT||!GetUpdateRect(window,&u,FALSE)||u.bottom>shell_hero_bottom())shellBodyDirty=1;}
        PAINTSTRUCT ps;HDC dc=message==WM_PAINT?BeginPaint(window,&ps):(HDC)w;RECT bounds;GetClientRect(window,&bounds);
        if(loading){
            HDC memory=CreateCompatibleDC(dc);HBITMAP bitmap=CreateCompatibleBitmap(dc,bounds.right,bounds.bottom);
            HGDIOBJ previous=SelectObject(memory,bitmap);
            if(shellLogoImage)shell_loading_paint(window,memory);
            else{int saved=SaveDC(memory);SetViewportOrgEx(memory,0,shell_caption_height(),NULL);
                paint_banner(memory,bounds.right,BANNER_HEIGHT);RestoreDC(memory,saved);shell_caption_paint(window,memory);}
            BitBlt(dc,0,0,bounds.right,bounds.bottom,memory,0,0,SRCCOPY);
            SelectObject(memory,previous);DeleteObject(bitmap);DeleteDC(memory);
        }else shell_paint(window,dc);
        if(message==WM_PAINT)EndPaint(window,&ps);return 0;
    }
    if(message==WM_TIMER && w==3){native_stop_ui_ticks++;return 0;}
    if(message==WM_TIMER && w==2){KillTimer(window,2);SendMessageW(window,WM_APP+2,0,0);return 0;}
    if(message==WM_TIMER && w==1){
        DWORD elapsed=GetTickCount()-starting_tick;
        if(eac_following){HANDLE child;DWORD child_pid;
            if(eac_adopt_child(starting_pid,&child,&child_pid)){CloseHandle(starting_game);starting_game=child;starting_pid=child_pid;eac_following=0;
                if(PLATINUM_NATIVE)presence_start(child_pid,eac_presence_server);}
            else if(WaitForSingleObject(starting_game,0)==WAIT_OBJECT_0){DWORD code=1;GetExitCodeProcess(starting_game,&code);
                if(code==0&&elapsed<20000){InvalidateRect(window,NULL,FALSE);return 0;}
                eac_following=0;KillTimer(window,1);process_result=code?(int)code:4;
                error(L"Easy Anti-Cheat could not start the game. Repair the game files, or set Enabled=0 under [AntiCheat] in player.ini to play on servers that do not require it.");
                DestroyWindow(window);return 0;}
            else if(elapsed>30000){eac_following=0; /* bootstrapper still open: follow it */
                if(PLATINUM_NATIVE)presence_start(starting_pid,eac_presence_server);}
            else{InvalidateRect(window,NULL,FALSE);return 0;}}
        if(WaitForSingleObject(starting_game,0)==WAIT_OBJECT_0){
            DWORD code;GetExitCodeProcess(starting_game,&code);KillTimer(window,1);
            process_result=(int)code;
            if(code!=0)error(L"The game closed during startup. See profile/tcetest/etconsole.log for details.");
            DestroyWindow(window);return 0;
        }
        InvalidateRect(window,NULL,FALSE);
        int ready=0;EnumWindows(find_game_window,(LPARAM)&ready);
        if(!wait_game&&((ready && elapsed>=600)||elapsed>=15000)){KillTimer(window,1);
            if(options.window&&window_placement_allowed())shell_resume(window);else DestroyWindow(window);}return 0;
    }
    if(message==WM_COMMAND && LOWORD(w)==SHELL_MINIMIZE){if(!tray_hide(window))ShowWindow(window,SW_MINIMIZE);return 0;}
    if(message==WM_SYSCOMMAND&&(w&0xFFF0)==SC_MINIMIZE&&tray_hide(window))return 0; /* taskbar and Win+Down minimize */
    if(message==WM_COMMAND && LOWORD(w)==SHELL_MAXIMIZE){ShowWindow(window,IsZoomed(window)?SW_RESTORE:SW_MAXIMIZE);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==SHELL_SUPPORT){ShellExecuteW(window,L"open",SHELL_SUPPORT_URL,NULL,NULL,SW_SHOWNORMAL);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==SHELL_CLOSE){SendMessageW(window,WM_CLOSE,0,0);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==104){if(!launch(window,0,0)&&auto_run){process_result=3;DestroyWindow(window);}return 0;}
    if(message==WM_COMMAND && LOWORD(w)==111){launch(window,1,0);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==112){launch(window,0,1);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==113){open_advanced(window);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==116){if(shell_main(window)&&!loading)shell_set_tab(window,7);else open_session(window);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==115){open_graphics_report(window);return 0;}
    if(message==WM_COMMAND && LOWORD(w)==114){
        int saved=save_graphics_preferences();
        if(save_only){process_result=saved?0:3;DestroyWindow(window);return 0;}
        if(saved)SetWindowTextW(GetDlgItem(window,114),L"Graphics settings saved");
        else error(L"Graphics settings could not be saved. Check that the game folder is writable.");return 0;
    }
    if(message==WM_COMMAND && LOWORD(w)==107 && HIWORD(w)==CBN_SELCHANGE){
        /* Custom the first time: start from the preset that was showing */
        int preset=(int)SendMessageW(preset_combo,CB_GETCURSEL,0,0);
        if(preset==3&&!custom_saved&&shown_preset>=0&&shown_preset<3){GraphicsQuality q=effective_quality(shown_preset,0);custom_graphics=quality_custom(&q);custom_saved=1;}
        if(preset>=0&&preset<=3)shown_preset=preset;
    }
    if(message==WM_COMMAND && (((LOWORD(w)>=107&&LOWORD(w)<=109)&&HIWORD(w)==CBN_SELCHANGE)||
                              (LOWORD(w)==110&&HIWORD(w)==BN_CLICKED))){
        SetWindowTextW(GetDlgItem(window,114),L"Save graphics settings");
        update_graphics_summary();return 0;
    }
    if(message==WM_COMMAND && LOWORD(w)==105){start_host(window);return 0;}
    if(message==WM_COMMAND && (LOWORD(w)==126||LOWORD(w)==9310) && PLATINUM_NATIVE && !loading){
        /* Offline practice on Railhouse (9310: firing range); saved server and [Hosting] choices stay untouched. */
        wcscpy(local_map,L"obj_railhouse");practice_mode=LOWORD(w)==9310?2:1;
        if(!launch(window,0,0)){local_map[0]=0;practice_mode=0;}
        return 0;
    }
    if(message==WM_COMMAND && LOWORD(w)==106){stop_host(window);return 0;}
    if(message==WM_CLOSE){if(!tray_hide(window))DestroyWindow(window);return 0;}
    if(message==WM_DESTROY){
        RemovePropW(window,INSTANCE_PROP);
        if(window_placement_allowed()&&!loading){
            WINDOWPLACEMENT place;memset(&place,0,sizeof(place));place.length=sizeof(place);
            if(GetWindowPlacement(window,&place)&&place.showCmd!=SW_SHOWMINIMIZED){
                wchar_t value[96];RECT r=place.rcNormalPosition;
                swprintf(value,96,L"%ld,%ld,%ld,%ld,%d",r.left,r.top,r.right-r.left,r.bottom-r.top,place.showCmd==SW_SHOWMAXIMIZED||IsZoomed(window));
                WritePrivateProfileStringW(L"Launcher",L"Window3",value,ini);
            }
        }
        tray_remove(window);heroclip_dispose();
        if(starting_game){CloseHandle(starting_game);starting_game=NULL;}PostQuitMessage(0);return 0;}
    return DefWindowProcW(window,message,w,l);
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,LPWSTR command,int show){
    (void)previous;(void)command;
    if(!GetModuleFileNameW(NULL,root,2048)||wcslen(root)>=2047)return 1;
    wchar_t *slash=wcsrchr(root,L'\\');if(!slash)return 1;*slash=0;
    wcscpy(launcherDir,root);
    /* launcher.ini next to the launcher may place the game files elsewhere (installer choice). */
    {wchar_t layout[2300],game[2048];swprintf(layout,2300,L"%ls\\launcher.ini",launcherDir);
     if(GetPrivateProfileStringW(L"Install",L"GameFolder",L"",game,2048,layout)&&wcslen(game)>3&&wcslen(game)<1800&&
        ((game[1]==L':'&&game[2]==L'\\')||(game[0]==L'\\'&&game[1]==L'\\'))&&!wcsstr(game,L"..")){
         size_t n=wcslen(game);while(n>3&&game[n-1]==L'\\')game[--n]=0;
         SHCreateDirectoryExW(NULL,game,NULL);
         if(GetFileAttributesW(game)&FILE_ATTRIBUTE_DIRECTORY&&GetFileAttributesW(game)!=INVALID_FILE_ATTRIBUTES)wcscpy(root,game);
     }}
    swprintf(ini,2200,L"%ls\\player.ini",root);options_load();lang_resolve();
    load_session_preferences();
    wchar_t apply_target[2048]={0};DWORD apply_pid=0;int update_test=0,repair_test=0,hd_check_test=0,update_done_flag=0,make_report=0,crash_report=0,crash_prompt_forced=0,telemetry_send_now=0;static wchar_t telemetry_preview_path[2200];
    SetEnvironmentVariableW(L"TCP_LAUNCHER",L"1"); /* the game skips its own crash prompt when started from here */DWORD presence_pid=0;wchar_t presence_server[256]={0};
    int argc,serve=0;LPWSTR *argv=CommandLineToArgvW(GetCommandLineW(),&argc);
    /* A truecombat:// link (from a browser, chat app or document) must carry nothing but the link:
       a quote in a badly escaped link could otherwise smuggle extra launcher options onto the command line. */
    for(int i=1;i<argc;i++)if(!wcscmp(argv[i],L"--url")||!_wcsnicmp(argv[i],L"truecombat:",11)){
        int linkOnly=(!wcscmp(argv[i],L"--url")&&i==1&&argc==3)||(!_wcsnicmp(argv[i],L"truecombat:",11)&&i==1&&argc==2)||(i==2&&argc==3&&!wcscmp(argv[1],L"--url"));
        if(!linkOnly)return 2;
    }
    /* Shortcut care runs only on plain starts (double-click, tray at sign-in, after an update), never for tools and checks. */
    int plain_start=1;
    for(int i=1;i<argc;i++)if(wcscmp(argv[i],L"--tray")&&wcscmp(argv[i],L"--updated")&&wcscmp(argv[i],L"--update-failed")&&wcscmp(argv[i],L"--install"))plain_start=0;
    for(int i=1;i<argc;i++){
        if(PLATINUM_NATIVE&&(!wcscmp(argv[i],L"--host")||!wcscmp(argv[i],L"--host-rounds")||!wcscmp(argv[i],L"--host-teams")||!wcscmp(argv[i],L"--host-capture")||!wcscmp(argv[i],L"--host-tdm")||!wcscmp(argv[i],L"--host-flags")||!wcscmp(argv[i],L"--host-bomb"))){
            serve=1;host_mode=!wcscmp(argv[i],L"--host-rounds")?1:!wcscmp(argv[i],L"--host-teams")?2:!wcscmp(argv[i],L"--host-capture")?3:!wcscmp(argv[i],L"--host-tdm")?4:!wcscmp(argv[i],L"--host-flags")?5:!wcscmp(argv[i],L"--host-bomb")?6:0;
        }
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--verify-stop-ui"))verify_stop_ui=1;
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--wait-game"))wait_game=1;
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--stop-server"))stop_only=1;
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--host-mode")&&i+1<argc){
            wchar_t *end;long mode=wcstol(argv[++i],&end,10);if(!argv[i][0]||*end||mode<0||mode>6)return 2;host_mode=(int)mode;
        }
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--local-map")&&i+1<argc){
            const wchar_t *maps[]={L"obj_railhouse",L"obj_northport",L"obj_delta",L"obj_stadtrand",L"obj_snow",L"obj_village"};
            const wchar_t *map=argv[++i];int found=0;for(int j=0;j<6;j++)if(!wcscmp(map,maps[j]))found=1;
            if(!found)return 2;wcscpy(local_map,map);auto_run=1;
        }
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--join")&&i+1<argc){wcsncpy(forced_server,argv[++i],255);auto_run=1;}
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--url")&&i+1<argc){int s=staffkey_parse_url(argv[++i]);if(s<0)return 2;if(!s){if(!join_parse_url(argv[i],forced_server,256))return 2;auto_run=1;wcsncpy(instanceLink,argv[i],511);}}
        else if(PLATINUM_NATIVE&&!_wcsnicmp(argv[i],L"truecombat:",11)){int s=staffkey_parse_url(argv[i]);if(s<0)return 2;if(!s){if(!join_parse_url(argv[i],forced_server,256))return 2;auto_run=1;wcsncpy(instanceLink,argv[i],511);}}
#if PLATINUM_STAFFKEY_TEST
        else if(!wcscmp(argv[i],L"--staffkey-endpoint")&&i+1<argc)wcsncpy(staffkeyEndpoint,argv[++i],299);
        else if(!wcscmp(argv[i],L"--staffkey-yes"))staffkeyYes=1;
#endif
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--password")&&i+1<argc){if(!join_valid_password(argv[++i]))return 2;join_set_password(argv[i]);}
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--team")&&i+1<argc)join_set_team(argv[++i]);
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--practice")){wcscpy(local_map,L"obj_railhouse");practice_mode=1;auto_run=1;}
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--range")){wcscpy(local_map,L"obj_railhouse");practice_mode=2;auto_run=1;}
        else if(!wcscmp(argv[i],L"--verify-chrome"))verify_chrome=1;
        else if((!wcscmp(argv[i],L"--shortcut-check")||!wcscmp(argv[i],L"--shortcut-check-version"))&&i+1<argc){shortcutForce=!wcscmp(argv[i],L"--shortcut-check");wcsncpy(shortcutReport,argv[++i],2199);shortcutReport[2199]=0;}
        else if(!wcscmp(argv[i],L"--shortcut-root")&&i+1<argc){wcsncpy(shortcutRoot,argv[++i],1023);shortcutRoot[1023]=0;}
        else if(!wcscmp(argv[i],L"--apply-update")&&i+2<argc){wcsncpy(apply_target,argv[i+1],2047);apply_pid=wcstoul(argv[i+2],NULL,10);i+=2;}
        else if(!wcscmp(argv[i],L"--no-relaunch"))updateHeadless=1;
        else if(!wcscmp(argv[i],L"--launcher-dir")&&i+1<argc){wcsncpy(launcherDir,argv[++i],2047);launcherDir[2047]=0;}
        else if(!wcscmp(argv[i],L"--install"))install_now=1;
        else if(!wcscmp(argv[i],L"--switch-latest"))switch_latest=1;
        else if(!wcscmp(argv[i],L"--versions"))versions_open=1;
        else if(!wcscmp(argv[i],L"--switch-version")&&i+1<argc){wcsncpy(switch_version,argv[++i],63);switch_version[63]=0;}
        else if(!wcscmp(argv[i],L"--list-versions")&&i+1<argc){wcsncpy(list_versions_path,argv[++i],2199);list_versions_path[2199]=0;}
        else if(!wcscmp(argv[i],L"--update-feed")&&i+1<argc){wcsncpy(updateFeed,argv[++i],1023);}
        else if(!wcscmp(argv[i],L"--update-preview")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>UPDATE_FAILED)return 2;updatePreview=(int)value;}
        else if(!wcscmp(argv[i],L"--update-test"))update_test=1;
        else if(!wcscmp(argv[i],L"--hd-check"))hd_check_test=1;
        else if(!wcscmp(argv[i],L"--launcher-update"))launcher_update_test=1;
        else if(!wcscmp(argv[i],L"--launcher-check"))launcher_update_test=2;
        else if(!wcscmp(argv[i],L"--repair"))repair_test=1;            /* 2.6.2: --update-test --repair: Verify and repair, headless */
        else if(!wcscmp(argv[i],L"--startup-check"))repair_test=2;     /* 2.6.2: --update-test --startup-check: the start check, auto-repair included */
        else if(!wcscmp(argv[i],L"--launcher-updated"))launcherJustUpdated=1;
        else if(!wcscmp(argv[i],L"--launcher-preview"))launcher_preview=1;
        else if(!wcscmp(argv[i],L"--version-file")&&i+1<argc){wcsncpy(version_file_path,argv[++i],2199);version_file_path[2199]=0;}
        else if(!wcscmp(argv[i],L"--first-run"))firstRunForced=1;
        else if(!wcscmp(argv[i],L"--first-run-step")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<1||value>3)return 2;firstRunForced=1;firstRunStartStep=(int)value-1;}
        else if(!wcscmp(argv[i],L"--controls"))controls_open=1;
        else if(!wcscmp(argv[i],L"--presence")&&i+2<argc){presence_pid=wcstoul(argv[i+1],NULL,10);wcsncpy(presence_server,argv[i+2],255);i+=2;}
        else if(!wcscmp(argv[i],L"--make-report"))make_report=1;
        else if(!wcscmp(argv[i],L"--crash-report"))crash_report=1;
        else if(!wcscmp(argv[i],L"--crash-prompt"))crash_prompt_forced=1;
        else if(!wcscmp(argv[i],L"--telemetry-preview")&&i+1<argc){wcsncpy(telemetry_preview_path,argv[++i],2199);telemetry_preview_path[2199]=0;}
        else if(!wcscmp(argv[i],L"--telemetry-send"))telemetry_send_now=1;
        else if(!wcscmp(argv[i],L"--telemetry-url")&&i+1<argc){const wchar_t *u=argv[++i];if(wcsncmp(u,L"http://127.0.0.1:",17)||wcslen(u)>=300)return 2;wcscpy(telemetryUrl,u);}
        else if(!wcscmp(argv[i],L"--telemetry-card"))telemetryForcedCard=1;
        else if(!wcscmp(argv[i],L"--master")&&i+1<argc){wcsncpy(master_override,argv[++i],255);}
        else if(!wcscmp(argv[i],L"--host-public")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>1)return 2;host_public_forced=(int)value;}
        else if(!wcscmp(argv[i],L"--tab")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>7||value==4)return 2;initial_tab=(int)value;}
        else if(!wcscmp(argv[i],L"--settings-tab")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>5)return 2;uiSettingsTab=(int)value;initial_tab=3;}
        else if(!wcscmp(argv[i],L"--tray"))start_in_tray=1;
        else if(!wcscmp(argv[i],L"--whats-new"))uiWhatsNewForced=1;
        else if(!wcscmp(argv[i],L"--stats-preview"))statsPreview=1;
        else if(!wcscmp(argv[i],L"--language")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>4)return 2;options.lang=(int)value;lang_resolve();}
        else if(!wcscmp(argv[i],L"--anim-time")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0)return 2;shellAnimFrozen=(int)value;}
        else if(!wcscmp(argv[i],L"--updated"))update_done_flag=1;
        else if(!wcscmp(argv[i],L"--update-failed"))update_done_flag=2;
        else if(!wcscmp(argv[i],L"--compact-ui"))compact_ui=1;
        else if(!wcscmp(argv[i],L"--capture-ui")&&i+1<argc){wcsncpy(capture_ui_path,argv[++i],2199);}
        else if(!wcscmp(argv[i],L"--capture-size")&&i+1<argc){if(swscanf(argv[++i],L"%dx%d",&captureWidth,&captureHeight)!=2||captureWidth<640||captureHeight<400||captureWidth>7680||captureHeight>4320)return 2;}
        else if(!wcscmp(argv[i],L"--name-colours")){ncOpenAtStart=1;}
        else if(!wcscmp(argv[i],L"--session-options"))session_options=1;
        else if(!wcscmp(argv[i],L"--save-session"))session_save_only=1;
        else if(!wcscmp(argv[i],L"--query-server")&&i+1<argc){query_only=1;wcsncpy(forced_server,argv[++i],253);}
        else if((!wcscmp(argv[i],L"--frame-limit")||!wcscmp(argv[i],L"--background-fps")||!wcscmp(argv[i],L"--host-slots")||!wcscmp(argv[i],L"--host-map"))&&i+1<argc){
            int which=!wcscmp(argv[i],L"--frame-limit")?0:(!wcscmp(argv[i],L"--background-fps")?1:(!wcscmp(argv[i],L"--host-slots")?2:3));
            wchar_t *end;long value=wcstol(argv[++i],&end,10);const int low[]={0,5,2,0},high[]={500,125,32,5};if(*end||value<low[which]||value>high[which]||(which==0&&value>0&&value<30))return 2;
            if(which==0)session_fps=value;else if(which==1)session_idle_fps=value;else if(which==2)host_slots=value;else host_map=value;
        }
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--host-bots")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>32)return 2;host_bots=(int)value;}
        else if(PLATINUM_NATIVE&&!wcscmp(argv[i],L"--host-bot-skill")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<1||value>5)return 2;host_bot_skill=(int)value;}
        else if(!wcscmp(argv[i],L"--map-rotation")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>1)return 2;host_rotation=value;}
        else if(!wcscmp(argv[i],L"--favorite-name")&&i+1<argc){const wchar_t *value=argv[++i];if(!valid_favorite_name(value))return 2;wcscpy(favorite_name,value);}
        else if(!wcscmp(argv[i],L"--use-recent")&&i+1<argc){wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<1||value>5)return 2;recent_use=value;}
        else if(!wcscmp(argv[i],L"--host-name")&&i+1<argc){const wchar_t *value=argv[++i];if(!valid_host_name(value))return 2;wcscpy(host_name,value);}
        else if((!wcscmp(argv[i],L"--save-favorite")||!wcscmp(argv[i],L"--use-favorite")||!wcscmp(argv[i],L"--remove-favorite"))&&i+1<argc){
            int which=!wcscmp(argv[i],L"--save-favorite")?0:(!wcscmp(argv[i],L"--use-favorite")?1:2);wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<1||value>10)return 2;if(which==0)favorite_save=value;else if(which==1)favorite_use=value;else favorite_remove=value;
        }
        else if(!wcscmp(argv[i],L"--launch"))auto_run=1;
        else if(!wcscmp(argv[i],L"--safe-start")){auto_run=1;safe_launch=1;}
        else if(!wcscmp(argv[i],L"--graphics-options"))graphics_options=1;
        else if(!wcscmp(argv[i],L"--graphics-report"))report_only=1;
        else if(!wcscmp(argv[i],L"--graphics-info"))graphics_info=1;
        else if(!wcscmp(argv[i],L"--save-graphics"))save_only=1;
        else if(!wcscmp(argv[i],L"--menu")){auto_run=1;menu_launch=1;}
        /* Discord "Join": start straight to the game menu; Discord then hands the
           join secret to the game over IPC and the game connects by itself. */
        else if(!wcscmp(argv[i],L"--discord-launch")){auto_run=1;menu_launch=1;}
        else if(!wcscmp(argv[i],L"--banner-preview"))banner_preview=1;
        else if(!wcscmp(argv[i],L"--serve"))serve=1;
        else if(!wcscmp(argv[i],L"--server-port")&&i+1<argc){
            wchar_t *end=NULL;unsigned long port=wcstoul(argv[++i],&end,10);if(*end||port<1||port>65535)return 2;server_port=(unsigned)port;
        }
        else if(!wcscmp(argv[i],L"--server-bind")&&i+1<argc){
            struct in_addr ip;const wchar_t *bind=argv[++i];if(InetPtonW(AF_INET,bind,&ip)!=1||wcslen(bind)>63)return 2;wcscpy(server_bind,bind);
        }
        else if(!wcscmp(argv[i],L"--no-sound"))no_sound=1;
        else if(!wcscmp(argv[i],L"--performance-overlay")&&i+1<argc){
            wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>3)return 2;forced_overlay=(int)value;
        }
        else if(!wcscmp(argv[i],L"--frame-generation")&&i+1<argc){
            wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>1)return 2;forced_framegen=(int)value;
        }
        else if(!wcscmp(argv[i],L"--texture-compression")&&i+1<argc){
            wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>2)return 2;forced_compression=(int)value;
        }
        else if(!wcscmp(argv[i],L"--refresh-rate")&&i+1<argc){
            wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>480)return 2;forced_refresh=(int)value;
        }
        else if((!wcscmp(argv[i],L"--texture-detail")||!wcscmp(argv[i],L"--filtering")||!wcscmp(argv[i],L"--anti-aliasing")||!wcscmp(argv[i],L"--brightness"))&&i+1<argc){
            int option=!wcscmp(argv[i],L"--texture-detail")?0:(!wcscmp(argv[i],L"--filtering")?1:(!wcscmp(argv[i],L"--anti-aliasing")?2:3));
            const int maximum[]={3,6,4,6};wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>maximum[option])return 2;
            if(option==0)forced_texture=(int)value;else if(option==1)forced_filter=(int)value;else if(option==2)forced_aa=(int)value;else forced_brightness=(int)value;
        }
        else if((!wcscmp(argv[i],L"--graphics-preset")||!wcscmp(argv[i],L"--resolution")||!wcscmp(argv[i],L"--display-mode"))&&i+1<argc){
            int option=!wcscmp(argv[i],L"--graphics-preset")?0:(!wcscmp(argv[i],L"--resolution")?1:2);
            wchar_t *end;long value=wcstol(argv[++i],&end,10);if(*end||value<0||value>(option==1?7:option==0?3:2))return 2;
            if(option==0)forced_preset=(int)value;else if(option==1)forced_resolution=(int)value;else forced_display=(int)value;
        }
        else if(!wcscmp(argv[i],L"--custom-graphics")&&i+1<argc){
            /* developer checks: the 21 custom values in CUSTOM_KEYS order, comma separated (implies --graphics-preset 3) */
            const wchar_t *p=argv[++i];
            for(int field=0;field<CUSTOM_FIELDS;field++){wchar_t *end;long value=wcstol(p,&end,10);
                if(end==p||value<0||value>custom_maximum[field]||(field<CUSTOM_FIELDS-1?*end!=L',':*end!=0))return 2;
                *custom_field(&forced_custom,field)=(int)value;p=end+1;}
            forced_custom_set=1;forced_preset=3;
        }
        else if(!wcscmp(argv[i],L"--connect")&&i+1<argc){wcsncpy(forced_server,argv[++i],255);}
        else if(!wcscmp(argv[i],L"--name")&&i+1<argc){wcsncpy(forced_name,argv[++i],63);}
        else if(!wcscmp(argv[i],L"--test-config")&&i+1<argc){
            const wchar_t *p=argv[++i];size_t n=wcslen(p);
            if(n>100 || !n)return 2;for(size_t j=0;j<n;j++)if(!((p[j]>=L'a'&&p[j]<=L'z')||(p[j]>=L'0'&&p[j]<=L'9')||p[j]==L'_'||p[j]==L'.'))return 2;
            wcscpy(forced_config,p);
        }else{return 2;}
    }LocalFree(argv);
    if(apply_target[0])return update_apply_main(apply_target,apply_pid);
    if(presence_pid)return presence_main(presence_pid,presence_server);
    update_load_config();
    update_cleanup(update_done_flag==1);
    launcher_cleanup();
    if(shortcutReport[0])return shortcut_check_main();
    if(plain_start)shortcut_care_start();
    if(launcher_preview){wcscpy(launcherLatest,L"1.1.0");InterlockedExchange(&launcherUpdateState,LAUNCHER_READY);}
    if(version_file_path[0]){
        /* tooling: which launcher and game this copy is */
        FILE *file=_wfopen(version_file_path,L"w, ccs=UTF-8");if(!file)return 3;
        fwprintf(file,L"launcher=%ls\ngame=%ls\n",PLATINUM_LAUNCHER_VERSION,updateCurrent);fclose(file);return 0;
    }
    if(install_now&&updateFeed[0]&&(!updateCurrent[0]||game_missing()))InterlockedExchange(&updateAutoDownload,1);
    if(update_done_flag==2&&updateFeed[0]){wcscpy(updateError,L"The update could not be applied. Close the game and server, then try again.");update_read_blocked();InterlockedExchange(&updateState,UPDATE_FAILED);}
    if(make_report){updateHeadless=1;return report_problem(NULL)?0:3;}
    if(crash_report)return crash_report_main();
    if(telemetry_preview_path[0])return telemetry_preview_main(telemetry_preview_path);
    if(telemetry_send_now)return telemetry_send(1);
    if(staffkeyCode[0]){updateHeadless=1;return staffkey_main();} /* 0.36.0: never with auto_run (a staffkey link sets no server) */
    /* ask about new crash reports only in normal interactive use, never in
       automated launches (--launch/--join/--local-map, captures, checks) */
    if(PLATINUM_NATIVE&&!serve&&!stop_only&&!query_only&&!capture_ui_path[0]&&!verify_chrome&&!verify_stop_ui&&!update_test&&!list_versions_path[0]&&!make_report&&!crash_report)join_register_protocol();
    crashPromptAllowed=crash_prompt_forced||(!auto_run&&!serve&&!stop_only&&!query_only&&!capture_ui_path[0]&&!verify_chrome&&!verify_stop_ui
        &&!save_only&&!session_options&&!session_save_only&&!graphics_options&&!graphics_info&&!report_only&&!banner_preview&&!controls_open&&!wait_game);
    if(!options.crash&&!crash_prompt_forced)crashPromptAllowed=0;
    if(list_versions_path[0]){
        /* developer check: write the release list the Versions dialog would show */
        update_releases_worker(NULL);
        FILE *file=_wfopen(list_versions_path,L"w, ccs=UTF-8");if(!file)return 3;
        for(LONG i=0;i<updateReleaseCount;++i)fwprintf(file,L"%ls\t%ls\n",updateReleases[i].version,updateReleases[i].date);
        fclose(file);return updateReleaseCount>0?0:4;
    }
    if(update_test&&launcher_update_test){
        /* headless launcher self-update: --update-test --launcher-update */
        updateHeadless=1;int code=0;
        if(launcher_update_test==2)code=(int)launcher_check_worker(NULL); /* --update-test --launcher-check: the button's path */
        else if(update_check_worker(NULL))code=3;
        else if(!launcherFeedManaged)code=8;
        else if(!launcher_update_offered())code=9;
        else{InterlockedExchange(&launcherUpdateState,LAUNCHER_DOWNLOADING);code=launcher_update_worker(NULL)?5:0;}
        wchar_t path[2400];swprintf(path,2400,L"%ls\\updates",root);CreateDirectoryW(path,NULL);wcscat(path,L"\\launcher-test.log");
        FILE *file=_wfopen(path,L"w, ccs=UTF-8");
        if(file){fwprintf(file,L"code=%d\nrunning=%ls\nfeed=%ls\nmanaged=%d\nerror=%ls\n",code,PLATINUM_LAUNCHER_VERSION,launcherLatest,launcherFeedManaged,(code==5||(launcher_update_test==2&&code))?launcherError:(code==3?updateError:L""));fclose(file);}
        return code;
    }
    if(update_test&&repair_test){
        /* 2.6.2 headless repair checks (tests/launcher_repair). Codes: 0 nothing to do or update applied/handed over,
           3 check failed, 4 an update is available (startup check), 5 download failed, 6 apply could not start, 7 not installed */
        updateHeadless=1;int code=0,repaired=0;
        if(repair_test==2){if(update_check_worker(NULL))code=3;else if(!updateAutoRepairWanted&&InterlockedCompareExchange(&updateState,0,0)==UPDATE_AVAILABLE)code=4;}
        if(!code&&(repair_test==1||updateAutoRepairWanted)){
            if(!updateCurrent[0])code=7;
            else{
                wchar_t feed[1024];if(!update_tag_feed(updateCurrent,feed,1024))wcscpy(feed,updateLatestFeed);
                wcscpy(updateFeed,feed);wcsncpy(updateTarget,updateCurrent,63);updateTarget[63]=0;updateSwitching=1;updateRepair=1;updateRepairNote[0]=0;
                if(update_check_worker(NULL))code=3;
                else if(InterlockedCompareExchange(&updateState,0,0)==UPDATE_AVAILABLE){repaired=deltaReady?deltaCount:-1;
                    if(update_download_worker(NULL))code=5;else code=update_apply(NULL)?0:6;}
            }
        }
        wchar_t path[2400];swprintf(path,2400,L"%ls\\updates",root);CreateDirectoryW(path,NULL);wcscat(path,repair_test==1?L"\\repair-test.log":L"\\startup-test.log");
        FILE *file=_wfopen(path,L"w, ccs=UTF-8");
        if(file){fwprintf(file,L"code=%d\ncurrent=%ls\nauto_repair=%d\nrepaired=%d\nnote=%ls\nmissing=%ls\nerror=%ls\n",code,updateCurrent,updateAutoRepairWanted,repaired,updateRepairNote,updateMissingFile,code?updateError:L"");fclose(file);}
        return code;
    }
    if(update_test&&hd_check_test){
        /* headless HD textures check of a current game: --update-test --hd-check (fetches or removes, never updates) */
        updateHeadless=1;updateHdTest=1;
        int code=update_check_worker(NULL)?3:InterlockedCompareExchange(&updateState,0,0)==UPDATE_CURRENT?0:InterlockedCompareExchange(&updateState,0,0)==UPDATE_AVAILABLE?4:5;
        wchar_t path[2400];swprintf(path,2400,L"%ls\\updates",root);CreateDirectoryW(path,NULL);wcscat(path,L"\\hd-test.log");
        FILE *file=_wfopen(path,L"w, ccs=UTF-8");
        if(file){fwprintf(file,L"code=%d\ncurrent=%ls\nhd_textures=%d\noptional=%ls\nhd_bytes=%lld\nerror=%ls\n",code,updateCurrent,update_hd_on(),updateOptional,(long long)updateHdBytes,code?updateError:L"");fclose(file);}
        return code;
    }
    if(update_test){
        updateHeadless=1;
        if(switch_version[0]){
            /* headless Versions switch: --update-test --switch-version <v> [--switch-latest] */
            wchar_t feed[1024];
            if(switch_latest)wcscpy(feed,updateLatestFeed);else if(!update_tag_feed(switch_version,feed,1024))return 7;
            wcscpy(updateFeed,feed);wcscpy(updateTarget,switch_version);updateSwitching=1;update_set_pin(switch_latest?L"":switch_version);
        }
        int code=0;
        if(update_check_worker(NULL))code=3;
        else if(InterlockedCompareExchange(&updateState,0,0)!=UPDATE_AVAILABLE)code=4;
        else if(update_download_worker(NULL))code=5;
        else code=update_apply(NULL)?0:6;
        {wchar_t path[2400];swprintf(path,2400,L"%ls\\updates",root);CreateDirectoryW(path,NULL);wcscat(path,L"\\update-test.log");
         FILE *file=_wfopen(path,L"w, ccs=UTF-8");
         if(file){fwprintf(file,L"code=%d\ncurrent=%ls\ntarget=%ls\ndelta=%d files, %lld bytes\nskip_launcher=%d\nerror=%ls\nhd_textures=%d\noptional=%ls\nhd_bytes=%lld\n",code,updateCurrent,updateLatest,deltaReady?deltaCount:0,(long long)updateTotal,updateSkipLauncher,code?updateError:L"",update_hd_on(),updateOptional,(long long)updateHdBytes);fclose(file);}}
        return code;
    }
    if((!!favorite_save+!!favorite_remove+!!favorite_use+!!recent_use)>1)return 2;
    if(favorite_save||favorite_remove){wchar_t raw[256];
        if(favorite_remove)return store_favorite(favorite_remove,NULL,L"")?0:3;
        if(forced_server[0])wcscpy(raw,forced_server);else GetPrivateProfileStringW(L"Player",L"Server",L"",raw,256,ini);
        wchar_t normalized[256];if(!normalize_server(raw,normalized))return 2;return store_favorite(favorite_save,normalized,favorite_name)?0:3;
    }
    if(favorite_use||recent_use){wchar_t key[20],raw[256];swprintf(key,20,L"Server%d",favorite_use?favorite_use:recent_use);GetPrivateProfileStringW(favorite_use?L"Favorites":L"Recent",key,L"",raw,256,ini);if(!normalize_server(raw,forced_server))return 2;}
    if(session_save_only)return save_session_preferences()?0:3;
    if(query_only){wchar_t report[1400],path[2400];int ok=connection_report(forced_server,report,1400);swprintf(path,2400,L"%ls\\profile",root);CreateDirectoryW(path,NULL);wcscat(path,L"\\server-status.txt");FILE *file=_wfopen(path,L"w, ccs=UTF-8");if(!file)return 3;fwprintf(file,L"%ls\n",report);fclose(file);return ok?0:4;}
    if(stop_only)return native_host_stop_local();
    if(serve)return server_main();
    if(report_only){platinum_graphics_report(root,report_text,8192);return platinum_save_graphics_report(root,report_text)?0:3;}
    {   /* 0.37.1: one launcher per install (platinum_instance.h) */
        int kind=argc==1?INSTANCE_SHOW:(argc==2&&start_in_tray)?INSTANCE_TRAY:(instanceLink[0]&&argc<=3)?INSTANCE_LINK:-2;
        if(kind==-2&&window_placement_allowed())kind=-1;
        if(kind>=-1&&instance_forward(kind,kind==INSTANCE_LINK?instanceLink:NULL))return 0;
    }
    CoInitializeEx(NULL,COINIT_APARTMENTTHREADED);
    PlatinumGdiStartup image_startup={1,NULL,FALSE,FALSE};
    if(GdiplusStartup(&image_token,&image_startup,NULL)==0){
        banner_stream=SHCreateMemStream(platinum_banner_png,sizeof(platinum_banner_png));
        if(banner_stream)GdipLoadImageFromStream(banner_stream,&banner_image);
    }
    /* Per-monitor DPI v2: the window rescales itself when it moves to a monitor with other scaling. */
    {typedef BOOL (WINAPI *DpiContext)(HANDLE);DpiContext context=(DpiContext)(void*)GetProcAddress(GetModuleHandleW(L"user32.dll"),"SetProcessDpiAwarenessContext");
     if(!context||!context((HANDLE)-4))SetProcessDPIAware();}
    shell_dark_menus();
    shell_fonts_register();font=CreateFontW(-16,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,SHELL_FACE_BODY);
    logo_font=CreateFontW(-40,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,SHELL_FACE_HEAVY);
    platinum_font=CreateFontW(-22,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,SHELL_FACE_DISPLAY_SEMI);
    background_brush=CreateSolidBrush(SHELL_BG);field_brush=CreateSolidBrush(SHELL_FIELD);
    shell_init();
    WNDCLASSW cls={0};cls.lpfnWndProc=window_proc;cls.hInstance=instance;cls.lpszClassName=L"TrueCombatPlatinumLauncher";
    cls.hCursor=LoadCursorW(NULL,IDC_ARROW);cls.hbrBackground=background_brush;cls.style=CS_DBLCLKS;RegisterClassW(&cls);
    if(capture_ui_path[0]&&shellAnimFrozen<0)shellAnimFrozen=3000;
    WNDCLASSW advanced_class=cls;advanced_class.lpfnWndProc=advanced_proc;advanced_class.lpszClassName=L"TrueCombatPlatinumGraphics";RegisterClassW(&advanced_class);
    WNDCLASSW versions_class=cls;versions_class.lpfnWndProc=versions_proc;versions_class.lpszClassName=L"TrueCombatPlatinumVersions";RegisterClassW(&versions_class);
    WNDCLASSW report_class=cls;report_class.lpfnWndProc=report_proc;report_class.lpszClassName=L"TrueCombatPlatinumGraphicsReport";RegisterClassW(&report_class);
    WNDCLASSW telemetry_class=cls;telemetry_class.lpfnWndProc=telemetry_proc;telemetry_class.lpszClassName=L"TrueCombatPlatinumTelemetry";RegisterClassW(&telemetry_class);
    WNDCLASSW session_class=cls;session_class.lpfnWndProc=session_proc;session_class.lpszClassName=L"TrueCombatPlatinumSession";RegisterClassW(&session_class);
    WNDCLASSW first_class=cls;first_class.lpfnWndProc=first_run_proc;first_class.lpszClassName=L"TrueCombatPlatinumFirstRun";RegisterClassW(&first_class);
    WNDCLASSW binds_class=cls;binds_class.lpfnWndProc=binds_proc;binds_class.lpszClassName=L"TrueCombatPlatinumBinds";RegisterClassW(&binds_class);
    WNDCLASSW profile_class=cls;profile_class.lpfnWndProc=profile_proc;profile_class.lpszClassName=L"TrueCombatPlatinumProfile";RegisterClassW(&profile_class);
    WNDCLASSW namecolour_class=cls;namecolour_class.lpfnWndProc=namecolour_proc;namecolour_class.lpszClassName=L"TrueCombatPlatinumNameColour";RegisterClassW(&namecolour_class);
    RECT work={0};SystemParametersInfoW(SPI_GETWORKAREA,0,&work,0);
    int windowWidth=compact_ui?1024:1280*optionSizes[options.size]/100,windowHeight=compact_ui?640:800*optionSizes[options.size]/100;
    {
        typedef UINT (WINAPI *DpiForSystem)(void);
        DpiForSystem dpiForSystem=(DpiForSystem)(void*)GetProcAddress(GetModuleHandleW(L"user32.dll"),"GetDpiForSystem");
        UINT dpi=dpiForSystem?dpiForSystem():96;
        if(dpi>96&&!capture_ui_path[0]){windowWidth=MulDiv(windowWidth,dpi,96);windowHeight=MulDiv(windowHeight,dpi,96);}
    }
    if(windowWidth>work.right-work.left)windowWidth=work.right-work.left;
    if(windowHeight>work.bottom-work.top)windowHeight=work.bottom-work.top;
    int x=work.left+(work.right-work.left-windowWidth)/2,y=work.top+(work.bottom-work.top-windowHeight)/2;
    if(x<work.left)x=work.left;if(y<work.top)y=work.top;
    int restore_maximized=0;window_placement_restore(&x,&y,&windowWidth,&windowHeight,&restore_maximized);
    if(capture_ui_path[0]&&captureWidth){windowWidth=captureWidth;windowHeight=captureHeight;x=work.left;y=work.top;}
    HWND window=CreateWindowExW(0,cls.lpszClassName,TITLE,WS_OVERLAPPEDWINDOW|WS_CLIPCHILDREN,
        x,y,windowWidth,windowHeight,NULL,NULL,instance,NULL);
    SetWindowPos(window,NULL,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_FRAMECHANGED);
    if(window_placement_allowed())SetPropW(window,INSTANCE_PROP,(HANDLE)(ULONG_PTR)instance_hash());   /* findable by a second start */
    MARGINS shadow={1,1,1,1};DwmExtendFrameIntoClientArea(window,&shadow);
    BOOL dark_title=TRUE;DwmSetWindowAttribute(window,20,&dark_title,sizeof(dark_title));
    {int round_corners=2;DwmSetWindowAttribute(window,33,&round_corners,sizeof(round_corners));}
    {   /* Created on a monitor whose scaling differs from the primary one: size for that monitor. */
        UINT dpi=shell_window_dpi(window),system=shell_window_dpi(NULL);wchar_t saved[96];
        int placed=GetPrivateProfileStringW(L"Launcher",L"Window3",L"",saved,96,ini)>0;
        if(dpi!=system&&!capture_ui_path[0]&&!restore_maximized&&!placed){RECT r;GetWindowRect(window,&r);
            int w=MulDiv(r.right-r.left,dpi,system),h=MulDiv(r.bottom-r.top,dpi,system);
            SetWindowPos(window,NULL,r.left,r.top,w,h,SWP_NOZORDER|SWP_NOACTIVATE);}
    }
    if(start_in_tray&&window_placement_allowed()){tray_add(window);show=SW_HIDE;}
    ShowWindow(window,restore_maximized&&(show==SW_SHOWNORMAL||show==SW_SHOWDEFAULT||show==SW_SHOW)?SW_SHOWMAXIMIZED:show);
    if(capture_ui_path[0])SetTimer(window,2,initial_tab?4500:2500,NULL);
    if(ncOpenAtStart)PostMessageW(window,WM_COMMAND,171,0);
    account_link_open(window); /* 0.37.0 truecombat://account/<code> */
    MSG msg;
    while(GetMessageW(&msg,NULL,0,0)>0){if(ui_key(window,&msg))continue;if(!IsDialogMessageW(ncWindow?ncWindow:session_window?session_window:(report_window?report_window:(advanced_window?advanced_window:window)),&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);}}
    shell_dispose();
    DeleteObject(font);DeleteObject(logo_font);DeleteObject(platinum_font);
    if(banner_image)GdipDisposeImage(banner_image);
    if(banner_stream)banner_stream->lpVtbl->Release(banner_stream);
    if(image_token)GdiplusShutdown(image_token);CoUninitialize();return process_result;
}
