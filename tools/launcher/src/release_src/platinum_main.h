/* Main window pages (launcher 2.0): everything right of the navigation rail is
   painted here on a 1280 x 800 design canvas and hit-tested by hand, so the
   pages follow the design mock-ups element for element. Real child windows are
   kept only where Windows has to do the work: dropdowns and text fields.
   Included from platinum_shell.h after the dialog helpers. */
__declspec(dllimport) int WINAPI GdipAddPathEllipse(void*,float,float,float,float);
__declspec(dllimport) int WINAPI GdipCreatePathGradientFromPath(void*,void**);
__declspec(dllimport) int WINAPI GdipSetPathGradientCenterColor(void*,DWORD);
__declspec(dllimport) int WINAPI GdipSetPathGradientSurroundColorsWithCount(void*,DWORD*,int*);
#define UI_X 256            /* left edge of page content */
#define UI_R 1244           /* right edge of page content */
#define UI_LINE TOK_LINE
#define UI_DIM RGB(111,120,136)
#define UI_TRAILER L"https://www.youtube.com/watch?v=pb1IvJOg7Lg"
#define UI_FEED_URL L"https://truecombat.eu/launcher-feed.txt"
static int game_missing(void);
static int nc_has_codes(const wchar_t *raw);static void nc_draw_name(HDC dc,const wchar_t *raw,int x,int y,int w,int h,int kind,float spacing,int upper,COLORREF base);
static void tip_hide(void);static void tip_start(HWND window);static void tip_dpi_changed(void);static void shell_refresh(HWND window);static void ui_window_title(HWND window);static void combos_translate(HWND window);
#include <dxgi.h>
typedef HRESULT (WINAPI *FirstCreateFactory)(REFIID,void**);
typedef HRESULT (WINAPI *FirstCreateDevice)(IUnknown*,int,REFIID,void**);
static const GUID firstIID_IDXGIFactory1={0x770aae78,0xf26f,0x4dba,{0xa8,0x29,0x25,0x3c,0x83,0xd1,0xb3,0x87}};
static const GUID firstIID_ID3D12Device={0x189819f1,0x1db6,0x4b57,{0xbe,0x54,0x18,0x21,0x33,0x9b,0x85,0xf7}};
typedef struct {wchar_t adapter[128];unsigned long long memory;int dx12,rtx,preset;} FirstRunInfo;
static FirstRunInfo firstRun;
static HWND firstRunWindow;
static int firstRunForced,firstRunStep;
static int firstRunStartStep; /* --first-run-step 2|3 opens on that step (captures) */

/* 2.6.0: also used off the UI thread by the anonymous hardware report, so it fills the caller's copy */
static void first_run_detect_into(FirstRunInfo *out){
    FirstRunInfo firstRun;
    memset(&firstRun,0,sizeof(firstRun));wcscpy(firstRun.adapter,L"Unknown graphics card");
    HMODULE dxgi=LoadLibraryW(L"dxgi.dll");IDXGIAdapter1 *best=NULL;
    if(dxgi){
        FirstCreateFactory create=(FirstCreateFactory)(void*)GetProcAddress(dxgi,"CreateDXGIFactory1");IDXGIFactory1 *factory=NULL;
        if(create&&SUCCEEDED(create(&firstIID_IDXGIFactory1,(void**)&factory))&&factory){
            IDXGIAdapter1 *adapter=NULL;
            for(UINT i=0;factory->lpVtbl->EnumAdapters1(factory,i,&adapter)!=DXGI_ERROR_NOT_FOUND;++i){
                DXGI_ADAPTER_DESC1 desc;
                if(SUCCEEDED(adapter->lpVtbl->GetDesc1(adapter,&desc))&&!(desc.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)&&desc.DedicatedVideoMemory>firstRun.memory){
                    firstRun.memory=desc.DedicatedVideoMemory;wcsncpy(firstRun.adapter,desc.Description,127);
                    if(best)best->lpVtbl->Release(best);best=adapter;adapter->lpVtbl->AddRef(adapter);
                }
                adapter->lpVtbl->Release(adapter);
            }
            factory->lpVtbl->Release(factory);
        }
    }
    HMODULE d3d12=LoadLibraryW(L"d3d12.dll");
    if(d3d12){
        FirstCreateDevice create=(FirstCreateDevice)(void*)GetProcAddress(d3d12,"D3D12CreateDevice");IUnknown *device=NULL;
        /* D3D_FEATURE_LEVEL_11_0 = 0xb000, the renderer's minimum. */
        if(create&&SUCCEEDED(create((IUnknown*)best,0xb000,&firstIID_ID3D12Device,(void**)&device))&&device){firstRun.dx12=1;device->lpVtbl->Release(device);}
    }
    if(best)best->lpVtbl->Release(best);
    firstRun.rtx=wcsstr(firstRun.adapter,L"RTX")!=NULL;
    unsigned long long gb=firstRun.memory>>30;
    firstRun.preset=!firstRun.dx12?0:(firstRun.rtx&&gb>=8)?2:gb>=3?1:0;
    *out=firstRun;
}
static void first_run_detect(void){first_run_detect_into(&firstRun);}


/* ---- fonts (design pixels; shell_text scales them to the window) ---- */
enum {F_HERO,F_H1,F_NAV,F_BTN,F_EYEBROW,F_SEC,F_TAG,F_CHIP,F_CARD,F_SEGB,F_WHO,F_PLAY,F_BODY15,F_BODY14,F_ROW,F_DESC,F_SMALL,F_MONO12,F_MONO11,F_PLAYSUB,F_AVA,F_SUP,F_COUNT};
static const struct {const wchar_t *face;int size;} uiFontSpec[F_COUNT]={
    {SHELL_FACE_HEAVY,58},{SHELL_FACE_HEAVY,40},{SHELL_FACE_DISPLAY_SEMI,16},{SHELL_FACE_DISPLAY_SEMI,15},{SHELL_FACE_DISPLAY_SEMI,14},
    {SHELL_FACE_DISPLAY_SEMI,13},{SHELL_FACE_DISPLAY_SEMI,11},{SHELL_FACE_DISPLAY_SEMI,12},{SHELL_FACE_DISPLAY,17},{SHELL_FACE_DISPLAY,16},
    {SHELL_FACE_DISPLAY,18},{SHELL_FACE_HEAVY,32},{SHELL_FACE_BODY,15},{SHELL_FACE_BODY,14},{SHELL_FACE_BODY_MED,14},{SHELL_FACE_BODY,13},
    {SHELL_FACE_BODY,12},{SHELL_FACE_MONO,12},{SHELL_FACE_MONO,11},{SHELL_FACE_BODY_MED,11},{SHELL_FACE_HEAVY,20},{SHELL_FACE_DISPLAY_SEMI,14}};
static HFONT uiFonts[F_COUNT];
static HFONT ui_font(int kind){
    if(!uiFonts[kind])uiFonts[kind]=shell_font(-uiFontSpec[kind].size,FW_NORMAL,uiFontSpec[kind].face);
    return uiFonts[kind];
}
static void ui_fonts_dispose(void){for(int i=0;i<F_COUNT;++i)if(uiFonts[i]){DeleteObject(uiFonts[i]);uiFonts[i]=NULL;}}
/* One line of text with fractional letter spacing, like CSS letter-spacing: the
   spacing is spread over the glyph advances so it does not round up per letter.
   Device coordinates. Returns 0 when the text does not fit and wants an ellipsis. */
static int ui_spaced(HDC dc,const wchar_t *text,RECT r,HFONT face,COLORREF color,UINT flags,float spacing){
    int n=(int)wcslen(text);if(n<=0)return 1;if(n>255)n=255;
    INT extent[256],dx[256];SIZE size={0,0};
    HGDIOBJ previous=SelectObject(dc,face);
    int ok=GetTextExtentExPointW(dc,text,n,0,NULL,extent,&size)!=0;
    int total=ok?(int)(extent[n-1]+spacing*n+0.5f):0;
    if(!ok||(total-(int)spacing>r.right-r.left&&(flags&DT_END_ELLIPSIS))){SelectObject(dc,previous);return 0;}
    int last=0;for(int i=0;i<n;++i){int at=(int)(extent[i]+spacing*(i+1)+0.5f);dx[i]=at-last;last=at;}
    TEXTMETRICW metrics;GetTextMetricsW(dc,&metrics);
    int x=(flags&DT_CENTER)?r.left+(r.right-r.left-total)/2:(flags&DT_RIGHT)?r.right-total+(int)spacing:r.left;
    int y=(flags&DT_VCENTER)?r.top+(r.bottom-r.top-metrics.tmHeight)/2:r.top;
    SetBkMode(dc,TRANSPARENT);SetTextColor(dc,color);
    ExtTextOutW(dc,x,y,0,NULL,text,(UINT)n,dx);
    SelectObject(dc,previous);return 1;
}
/* Text on the design canvas with CSS-style letter spacing (in design pixels). */
static void ui_text(HDC dc,const wchar_t *text,int x,int y,int w,int h,int kind,COLORREF color,UINT flags,float spacing){
    text=tr(text);   /* every painted string passes here: the launcher language applies to all of them */
    if(spacing!=0&&(flags&DT_SINGLELINE)){
        XFORM t;int scaled=shell_transform(dc,&t);float s=scaled?t.eM11:1;
        RECT r={(LONG)(x*s+t.eDx),(LONG)(y*t.eM22+t.eDy),(LONG)((x+w)*s+t.eDx+0.5f),(LONG)((y+h)*t.eM22+t.eDy+0.5f)};
        XFORM identity={1,0,0,1,0,0};if(scaled)SetWorldTransform(dc,&identity);
        int done=ui_spaced(dc,text,r,scaled?shell_scaled_font(ui_font(kind),s):ui_font(kind),color,flags,spacing*s);
        if(scaled)SetWorldTransform(dc,&t);
        if(done)return;
    }
    SetTextCharacterExtra(dc,(int)(spacing*shellScale));
    shell_text(dc,text,x,y,w,h,ui_font(kind),color,flags);
    SetTextCharacterExtra(dc,0);
}
static int ui_width(HDC dc,const wchar_t *text,int kind,float spacing){
    text=tr(text);
    return shell_text_width(dc,text,ui_font(kind))+(int)(spacing*wcslen(text)+0.5f);
}
/* Upper case for every language (towupper only knows ASCII in the C locale). */
static void ui_upper(wchar_t *out,const wchar_t *text,int capacity){
    text=tr(text);
    int n=0;for(;text[n]&&n<capacity-1;++n)out[n]=text[n];out[n]=0;
    if(n)CharUpperBuffW(out,(DWORD)n);
}
#define UI_LINE1 (DT_SINGLELINE|DT_VCENTER|DT_END_ELLIPSIS)

/* ---- painted controls: every clickable thing registers its rectangle while it is drawn ---- */
enum {H_NONE,H_HERO,H_DOT,H_CARD,H_JOIN,H_STAR,H_NEWS,H_WHO,H_SEG,H_PLAY,H_ARROW,H_TAB,H_TOGGLE,H_SWATCH,H_COMMAND,H_CHIP,H_ARTICLE,H_LINK,H_DISABLED,
      H_SORT,H_CLEARF,H_WHATSNEW,H_PRESET,H_WELCOME,H_LANG,H_PAGE,H_TELEMETRY};
/* Profile, Replays and Host a server pages (platinum_pages.h) */
static void ui_paint_profile(HDC dc,HWND window);static void ui_paint_replays(HDC dc);static void ui_paint_host(HDC dc);
static void ui_pages_click(HWND window,int arg,int twice);static int stats_rank_tag(HDC dc,int x,int y);static int stats_rank_tag_short(HDC dc,int x,int y);static int stats_ranked(void);static void stats_refresh(HWND window);static int statsPreview;static void pages_replay_scroll(int delta);static void profile_demos_scan(void);
typedef struct {int x,y,w,h,kind,arg;} UiHit;
static int uiIdentityColumn=219;   /* Profile page: width of the identity buttons' first column */
static UiHit uiHits[160];static int uiHitCount,uiHotKind,uiHotArg=-1;
/* Keyboard focus on a painted control (kind and arg), shown with a ring once the keyboard is used. */
static int uiFocusKind=H_NONE,uiFocusArg=-1,uiKeyboard;
static DWORD uiSavedTick;          /* "Saved" note on the Settings page after a change */
static int ui_hit(int x,int y,int w,int h,int kind,int arg){
    if(uiHitCount<160)uiHits[uiHitCount++]=(UiHit){x,y,w,h,kind,arg};
    return uiHotKind==kind&&uiHotArg==arg;
}
static void ui_saved(void){uiSavedTick=GetTickCount();if(!uiSavedTick)uiSavedTick=1;}
/* The game this launcher started is still running. */
static int game_running(void){return starting_game&&!loading&&WaitForSingleObject(starting_game,0)==WAIT_TIMEOUT;}
static const UiHit *ui_hit_at(int dx,int dy){
    for(int i=uiHitCount-1;i>=0;--i)if(dx>=uiHits[i].x&&dx<uiHits[i].x+uiHits[i].w&&dy>=uiHits[i].y&&dy<uiHits[i].y+uiHits[i].h)return &uiHits[i];
    return NULL;
}
/* The standard button of the design: 36 high, soft vertical gradient, caps label. */
static void ui_button(HDC dc,const wchar_t *label,int x,int y,int w,int h,int style,int kind,int arg,int enabled){
    /* A disabled button still registers, so its tip can say why it is unavailable. */
    int hot=enabled?ui_hit(x,y,w,h,kind,arg):(ui_hit(x,y,w,h,H_DISABLED,arg),0);
    wchar_t caps[80];ui_upper(caps,label,80);
    if(!enabled){
        shell_round(dc,(float)x,(float)y,(float)w,(float)h,6,SHELL_ARGB(255,RGB(21,25,32)),SHELL_ARGB(255,RGB(19,22,29)),SHELL_ARGB(255,RGB(36,42,53)));
        ui_text(dc,caps,x,y,w+1,h,F_BTN,RGB(84,92,106),DT_SINGLELINE|DT_VCENTER|DT_CENTER,1.5f);
        return;
    }
    if(style==1)shell_round(dc,(float)x,(float)y,(float)w,(float)h,6,SHELL_ARGB(255,hot?SHELL_ACCENT_EDGE:SHELL_ACCENT_HOT),SHELL_ARGB(255,hot?SHELL_ACCENT_HOT:SHELL_ACCENT),SHELL_ARGB(255,SHELL_ACCENT_EDGE));
    else if(style==2)shell_round(dc,(float)x,(float)y,(float)w,(float)h,6,SHELL_ARGB(hot?70:0,RGB(60,70,88)),SHELL_ARGB(hot?70:0,RGB(60,70,88)),SHELL_ARGB(255,hot?SHELL_FIELD_HOT:RGB(52,62,78)));
    else shell_round(dc,(float)x,(float)y,(float)w,(float)h,6,SHELL_ARGB(255,hot?RGB(46,54,69):RGB(35,42,54)),SHELL_ARGB(255,hot?RGB(34,41,54):RGB(26,32,43)),SHELL_ARGB(255,hot?SHELL_FIELD_HOT:RGB(52,62,78)));
    ui_text(dc,caps,x,y,w+1,h,F_BTN,enabled?(style==1?RGB(255,255,255):SHELL_TEXT):UI_DIM,DT_SINGLELINE|DT_VCENTER|DT_CENTER,1.5f);
}
static int ui_button_width(HDC dc,const wchar_t *label){wchar_t caps[80];ui_upper(caps,label,80);return ui_width(dc,caps,F_BTN,1.5f)+32;}
static void ui_toggle(HDC dc,int x,int y,int on,int hot){
    shell_round(dc,(float)x,(float)y,42,24,24,SHELL_ARGB(255,on?(hot?SHELL_ACCENT_HOT:SHELL_ACCENT):(hot?RGB(54,64,80):RGB(42,50,64))),SHELL_ARGB(255,on?(hot?SHELL_ACCENT_HOT:SHELL_ACCENT):(hot?RGB(54,64,80):RGB(42,50,64))),0);
    shell_round(dc,(float)(on?x+21:x+3),(float)y+3,18,18,18,SHELL_ARGB(255,on?RGB(255,255,255):RGB(141,150,166)),SHELL_ARGB(255,on?RGB(255,255,255):RGB(141,150,166)),0);
}
static void ui_chip(HDC dc,const wchar_t *label,int x,int y,int w){
    shell_round(dc,(float)x,(float)y,(float)w,22,22,SHELL_ARGB(153,SHELL_BG),SHELL_ARGB(153,SHELL_BG),SHELL_ARGB(255,RGB(56,64,77)));
    ui_text(dc,label,x,y,w+2,22,F_CHIP,RGB(176,184,198),DT_SINGLELINE|DT_VCENTER|DT_CENTER,1.7f);
}
static int ui_tag(HDC dc,const wchar_t *label,int x,int y,int green){
    int w=ui_width(dc,label,F_TAG,1.5f)+12;COLORREF c=green?SHELL_OK:SHELL_ACCENT;
    shell_round(dc,(float)x,(float)y,(float)w,18,3,SHELL_ARGB(green?36:51,c),SHELL_ARGB(green?36:51,c),SHELL_ARGB(green?102:128,c));
    ui_text(dc,label,x,y,w+2,18,F_TAG,green?RGB(127,220,163):shell_mix(SHELL_ACCENT_EDGE,RGB(255,255,255),0.15f),DT_SINGLELINE|DT_VCENTER|DT_CENTER,1.5f);
    return w;
}
/* A picture with rounded corners (design coordinates). */
static void ui_picture(HDC dc,void *image,int x,int y,int w,int h,int radius){
    XFORM t;shell_transform(dc,&t);
    int dx=(int)(x*t.eM11+t.eDx),dy=(int)(y*t.eM22+t.eDy),dw=(int)(w*t.eM11),dh=(int)(h*t.eM22),r=(int)(radius*2*t.eM11);
    if(!image){shell_round(dc,(float)x,(float)y,(float)w,(float)h,(float)radius,SHELL_ARGB(255,RGB(30,36,47)),SHELL_ARGB(255,RGB(22,27,36)),0);
        shell_icon(dc,SHELL_ICON_SERVER,(float)(x+w/2-10),(float)(y+h/2-10),20,UI_DIM);return;}
    XFORM identity={1,0,0,1,0,0};SetWorldTransform(dc,&identity);
    HRGN clip=CreateRoundRectRgn(dx,dy,dx+dw+1,dy+dh+1,r,r);
    SelectClipRgn(dc,clip);shell_image(dc,image,dx,dy,dw,dh);SelectClipRgn(dc,NULL);DeleteObject(clip);
    SetWorldTransform(dc,&t);
}

/* A card under the pointer rises 2 px over a soft shadow (no lift when animations are off). */
static void ui_lift(HDC dc,int x,int y,int w,int h){
    shell_round(dc,(float)x+3,(float)y+4,(float)w-6,(float)h,10,SHELL_ARGB(0,RGB(0,0,0)),SHELL_ARGB(110,RGB(0,0,0)),0);
}
/* A small check mark (design coordinates). */
static void ui_check(HDC dc,int x,int y,int size,COLORREF color){
    XFORM t;int scaled=shell_transform(dc,&t);float s=scaled?t.eM11:1,ox=scaled?t.eDx:0,oy=scaled?t.eDy:0;
    XFORM identity={1,0,0,1,0,0};if(scaled)SetWorldTransform(dc,&identity);
    void *g=NULL;
    if(!GdipCreateFromHDC(dc,&g)){GdipSetSmoothingMode(g,4);void *pen=NULL;GdipCreatePen1(SHELL_ARGB(255,color),2.0f*s,2,&pen);
        if(pen){float k=size*s/12.0f,px=ox+x*s,py=oy+y*s;
            GdipDrawLine(g,pen,px+1*k,py+6.5f*k,px+4.5f*k,py+10*k);GdipDrawLine(g,pen,px+4.5f*k,py+10*k,px+11*k,py+2*k);GdipDeletePen(pen);}
        GdipDeleteGraphics(g);}
    if(scaled)SetWorldTransform(dc,&t);
}
/* Download arrow (or a ring while files are checked) in the PLAY button, left edge at x, centred on y. */
static void ui_icon_download(HDC dc,int x,int y,int checking){
    XFORM t;int scaled=shell_transform(dc,&t);float s=scaled?t.eM11:1,ox=scaled?t.eDx:0,oy=scaled?t.eDy:0;
    XFORM identity={1,0,0,1,0,0};if(scaled)SetWorldTransform(dc,&identity);
    void *g=NULL;
    if(!GdipCreateFromHDC(dc,&g)){GdipSetSmoothingMode(g,4);void *pen=NULL;GdipCreatePen1(0xFFFFFFFF,2.6f*s,2,&pen);
        if(pen){float px=ox+x*s,py=oy+y*s;
            if(checking)GdipDrawEllipse(g,pen,px,py-11*s,22*s,22*s);
            else{GdipDrawLine(g,pen,px+11*s,py-12*s,px+11*s,py+7*s);GdipDrawLine(g,pen,px+3*s,py-1*s,px+11*s,py+7*s);GdipDrawLine(g,pen,px+19*s,py-1*s,px+11*s,py+7*s);
                GdipDrawLine(g,pen,px+1*s,py+12*s,px+21*s,py+12*s);}
            GdipDeletePen(pen);}
        GdipDeleteGraphics(g);}
    if(scaled)SetWorldTransform(dc,&t);
}
/* ---- Play page content: hero slides and news cards ----
   Built-in copy is used until the site's launcher feed has been read once;
   after that the cached feed is shown at once on every start. */
typedef struct {wchar_t eyebrow[48],chip[24],title[96],text[260],label1[32],url1[220],label2[32],url2[220];} UiSlide;
typedef struct {wchar_t tag[28],title[72],text[180],url[220];} UiNews;
static UiSlide uiSlides[4];static UiNews uiNews[3];
static int uiSlideCount,uiNewsCount,uiSlide,uiFeedLoaded,uiMapStep;static DWORD uiSlideTick;
static int ui_url_allowed(const wchar_t *url){
    static const wchar_t *const hosts[]={L"https://truecombat.eu/",L"https://github.com/",L"https://www.youtube.com/",L"https://youtu.be/",L"https://discord.gg/",L"https://ko-fi.com/"};
    for(unsigned i=0;i<sizeof(hosts)/sizeof(hosts[0]);++i)if(!_wcsnicmp(url,hosts[i],wcslen(hosts[i])))return 1;
    return 0;
}
static void ui_feed_defaults(void){
    memset(uiSlides,0,sizeof(uiSlides));memset(uiNews,0,sizeof(uiNews));
    UiSlide *s=&uiSlides[0];uiSlideCount=1;
    wcscpy(s->title,L"Ready when|you are.");
    wcscpy(s->text,PLATINUM_NATIVE?L"Play uses the 64-bit engine with DirectX 12. If your graphics driver has trouble, Safe start launches with OpenGL instead.":
                                   L"Join a server or host your own. If the game has trouble starting, Safe start uses conservative settings.");
    wcscpy(s->label1,L"Read patch notes");wcscpy(s->label2,L"Watch the trailer");wcscpy(s->url2,UI_TRAILER);
    uiNewsCount=3;
    wcscpy(uiNews[0].tag,L"Patch notes");wcscpy(uiNews[0].title,L"What changed in this version");wcscpy(uiNews[0].text,L"Every fix and feature of the latest release.");
    wcscpy(uiNews[1].tag,L"Community");wcscpy(uiNews[1].title,L"Find a match on Discord");wcscpy(uiNews[1].text,L"Players, match nights and the developers.");wcscpy(uiNews[1].url,L"https://discord.gg/8kcHdg2Hch");
    wcscpy(uiNews[2].tag,L"Support");wcscpy(uiNews[2].title,L"Keep the servers running");wcscpy(uiNews[2].text,L"TrueCombat: Platinum is free. See where support goes.");wcscpy(uiNews[2].url,SHELL_SUPPORT_URL);
}
static void ui_feed_field(wchar_t *out,int capacity,const char *value){
    MultiByteToWideChar(CP_UTF8,0,value,-1,out,capacity);out[capacity-1]=0;
}
/* Feed text: [slide] and [news] blocks of key=value lines (UTF-8). Unknown keys are ignored. */
static void ui_feed_parse(char *text){
    UiSlide slides[4];UiNews news[3];int slideCount=0,newsCount=0,section=0;
    memset(slides,0,sizeof(slides));memset(news,0,sizeof(news));
    for(char *line=text;line&&*line;){
        char *end=strchr(line,'\n');if(end)*end=0;
        size_t n=strlen(line);while(n&&(line[n-1]=='\r'||line[n-1]==' '))line[--n]=0;
        if(!strcmp(line,"[slide]")){section=slideCount<4?1:0;if(section)++slideCount;}
        else if(!strcmp(line,"[news]")){section=newsCount<3?2:0;if(section)++newsCount;}
        else{
            char *eq=strchr(line,'=');
            if(eq&&section){
                *eq=0;const char *value=eq+1;
                if(section==1){UiSlide *s=&slides[slideCount-1];
                    if(!strcmp(line,"eyebrow"))ui_feed_field(s->eyebrow,48,value);else if(!strcmp(line,"chip"))ui_feed_field(s->chip,24,value);
                    else if(!strcmp(line,"title"))ui_feed_field(s->title,96,value);else if(!strcmp(line,"text"))ui_feed_field(s->text,260,value);
                    else if(!strcmp(line,"button"))ui_feed_field(s->label1,32,value);else if(!strcmp(line,"url"))ui_feed_field(s->url1,220,value);
                    else if(!strcmp(line,"button2"))ui_feed_field(s->label2,32,value);else if(!strcmp(line,"url2"))ui_feed_field(s->url2,220,value);
                }else{UiNews *item=&news[newsCount-1];
                    if(!strcmp(line,"tag"))ui_feed_field(item->tag,28,value);else if(!strcmp(line,"title"))ui_feed_field(item->title,72,value);
                    else if(!strcmp(line,"text"))ui_feed_field(item->text,180,value);else if(!strcmp(line,"url"))ui_feed_field(item->url,220,value);
                }
            }
        }
        line=end?end+1:NULL;
    }
    /* Links may only lead to the project's own places. */
    for(int i=0;i<slideCount;++i){if(slides[i].url1[0]&&!ui_url_allowed(slides[i].url1))slides[i].url1[0]=0;if(slides[i].url2[0]&&!ui_url_allowed(slides[i].url2))slides[i].url2[0]=slides[i].label2[0]=0;
        if(!slides[i].label1[0])wcscpy(slides[i].label1,L"Read patch notes");}
    for(int i=0;i<newsCount;++i)if(news[i].url[0]&&!ui_url_allowed(news[i].url))news[i].url[0]=0;
    int usable=0;for(int i=0;i<slideCount;++i)if(slides[i].title[0])++usable;
    if(usable==slideCount&&slideCount>0){memcpy(uiSlides,slides,sizeof(slides));uiSlideCount=slideCount;if(uiSlide>=uiSlideCount)uiSlide=0;}
    if(newsCount==3&&news[0].title[0]&&news[1].title[0]&&news[2].title[0]){memcpy(uiNews,news,sizeof(news));uiNewsCount=3;}
}
static void ui_feed_path(wchar_t *out,int capacity){swprintf(out,capacity,L"%ls\\updates\\launcher-feed.txt",root);}
static void ui_feed_load_cache(void){
    wchar_t path[2300];ui_feed_path(path,2300);
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);if(file==INVALID_HANDLE_VALUE)return;
    static char text[16385];DWORD got=0;
    if(ReadFile(file,text,16384,&got,NULL)&&got){text[got]=0;ui_feed_parse(text);}
    CloseHandle(file);
}
typedef struct {char text[16385];DWORD length;} UiFeedBuffer;
static int ui_feed_sink(void *context,const void *data,DWORD size){
    UiFeedBuffer *b=(UiFeedBuffer*)context;if(b->length+size>16384)return 0;
    memcpy(b->text+b->length,data,size);b->length+=size;b->text[b->length]=0;return 1;
}
static int update_http_quiet(const wchar_t *url,UpdateSink sink,void *context,LONG64 limit);
static HWND uiFeedWindow;
static DWORD WINAPI ui_feed_worker(void *unused){
    (void)unused;
    UiFeedBuffer *b=(UiFeedBuffer*)calloc(1,sizeof(UiFeedBuffer));if(!b)return 0;
    if(!update_http_quiet(UI_FEED_URL,ui_feed_sink,b,16384)&&b->length&&strstr(b->text,"[slide]")){
        wchar_t path[2300],folder[2300];ui_feed_path(path,2300);swprintf(folder,2300,L"%ls\\updates",root);CreateDirectoryW(folder,NULL);
        HANDLE file=CreateFileW(path,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
        if(file!=INVALID_HANDLE_VALUE){DWORD wrote=0;WriteFile(file,b->text,b->length,&wrote,NULL);CloseHandle(file);}
        if(uiFeedWindow)PostMessageW(uiFeedWindow,WM_PLATINUM_BROWSER,2,0);
    }
    free(b);return 0;
}
static void ui_feed_start(HWND window,int online){
    if(uiFeedLoaded)return;
    uiFeedLoaded=1;ui_feed_defaults();ui_feed_load_cache();uiSlideTick=GetTickCount();
    if(online){uiFeedWindow=window;HANDLE thread=CreateThread(NULL,0,ui_feed_worker,NULL,0,NULL);if(thread)CloseHandle(thread);}
}

/* Line icons of the navigation rail, drawn on a 24-unit grid like the design's SVGs (device pixels). */
static void shell_nav_icon(HDC dc,int kind,float x,float y,float z,COLORREF color){
    void *g=NULL;if(GdipCreateFromHDC(dc,&g))return;
    GdipSetSmoothingMode(g,4);void *pen=NULL;float k=z/24;GdipCreatePen1(SHELL_ARGB(255,color),1.8f*k>1.2f?1.8f*k:1.2f,2,&pen);
    #define NL(a,b,c,d) GdipDrawLine(g,pen,x+(a)*k,y+(b)*k,x+(c)*k,y+(d)*k)
    if(pen){
        if(kind==0){NL(6,4,20,12);NL(20,12,6,20);NL(6,20,6,4);}
        else if(kind==1){GdipDrawRectangle(g,pen,x+3*k,y+4*k,18*k,6*k);GdipDrawRectangle(g,pen,x+3*k,y+14*k,18*k,6*k);NL(6.6f,7,7.4f,7);NL(6.6f,17,7.4f,17);}
        else if(kind==2){GdipDrawRectangle(g,pen,x+4*k,y+5*k,13*k,14*k);NL(17,9,20,9);NL(20,9,20,17);NL(20,17,18,19);NL(18,19,17,19);NL(8,9,13,9);NL(8,13,13,13);}
        else if(kind==3){GdipDrawEllipse(g,pen,x+8*k,y+4*k,8*k,8*k);GdipDrawArc(g,pen,x+4*k,y+15*k,16*k,12*k,190,160);}
        else if(kind==4){GdipDrawRectangle(g,pen,x+3*k,y+5*k,18*k,14*k);NL(10,9,15,12);NL(15,12,10,15);NL(10,15,10,9);}
        else if(kind==5){GdipDrawEllipse(g,pen,x+3*k,y+3*k,18*k,18*k);NL(12,3,12,21);NL(3,12,21,12);}
        else{GdipDrawEllipse(g,pen,x+9*k,y+9*k,6*k,6*k);
            for(int i=0;i<8;++i){float a=i*0.7853982f;GdipDrawLine(g,pen,x+(12+cosf(a)*7)*k,y+(12+sinf(a)*7)*k,x+(12+cosf(a)*10)*k,y+(12+sinf(a)*10)*k);}}
        GdipDeletePen(pen);
    }
    #undef NL
    GdipDeleteGraphics(g);
}
/* ---- backdrop: page background and the rail, cached per window size ---- */
static HDC uiBackDC;static HBITMAP uiBackBitmap,uiBackOld;static int uiBackW,uiBackH,uiBackKey=-1;
static void ui_back_release(void){
    if(uiBackDC){SelectObject(uiBackDC,uiBackOld);DeleteObject(uiBackBitmap);DeleteDC(uiBackDC);uiBackDC=NULL;}uiBackKey=-1;
}
static int ui_map_index(void){
    if(options.background>0)return options.background-1;
    return (uiMapStep+(int)((shellAnimFrozen>=0?(DWORD)shellAnimFrozen/1000:shellAnimStart)%6))%6;
}
/* The Play page shading over the map: a left-to-right shade for the copy, the fade into the page
   colour at the bottom and the launch bar. Shared by the stills and the hero clips. */
static void ui_back_shade(void *g,int left,int top,int mw,int mh,int bottom){
    const DWORD bg=SHELL_ARGB(0,SHELL_BG)&0x00FFFFFF;float s=shellScale;
    shell_gradient(g,left,top,mw,(int)(96*s),1,bg|0xA0000000,bg);   /* 0.37.1: the window buttons stay readable on bright art */
    int split=mw*45/100;
    shell_gradient(g,left,top,split,mh,0,bg|0xC0000000,bg|0x48000000);
    shell_gradient(g,left+split,top,mw-split,mh,0,bg|0x48000000,bg);
    int a=top+mh*38/100,b=top+mh*70/100;
    shell_gradient(g,left,a,mw,b-a,1,bg,bg|0xBF000000);
    shell_gradient(g,left,b,mw,bottom-b,1,bg|0xBF000000,bg|0xFF000000);
    int bar=bottom-(int)(112*s),knee=bar+(int)(29*s);const DWORD ink=0x000A0C11;
    shell_gradient(g,left,bar,mw,knee-bar,1,ink,ink|0xF5000000);
    shell_gradient(g,left,knee,mw,bottom-knee,1,ink|0xF5000000,ink|0xF5000000);
}
/* The navigation rail's background, its rules and the logo. */
static void ui_back_rail(HDC dc,int width,int height){
    (void)width;float s=shellScale;int page=shellLeft;shellLeft=shellRailLeft;int left=sx_(SHELL_RAIL);void *g=NULL;
    if(image_token&&!GdipCreateFromHDC(dc,&g)){shell_gradient(g,0,0,left,height,1,0xFF0A0C11,SHELL_ARGB(255,SHELL_BG));GdipDeleteGraphics(g);}
    shell_fill(dc,left-1,0,1,height,UI_LINE);
    shell_fill(dc,0,sy_(118),left-1,1,UI_LINE);
    shell_fill(dc,sx_(18),sy_(402),(int)(176*s),1,UI_LINE);
    shell_fill(dc,0,sy_(661)+shellShift,left-1,1,UI_LINE);
    shell_sprite_draw(dc,&shellLogoSprite,shellLogoImage,sx_(29),sy_(15),(int)(154*s),(int)(87*s));
    shellLeft=page;
}
static void ui_back_prepare(HDC reference,int width,int height){
    int key=shellTab==0||shellTab==4?ui_map_index():100;
    /* a hero clip frame (0.37.0): the frame, then the same shading from a cached premultiplied layer */
    if(shellTab==0&&key<6&&heroclip_frame(reference,key)){
        if(!uiBackDC||uiBackW!=width||uiBackH!=height){
            ui_back_release();
            uiBackDC=CreateCompatibleDC(reference);uiBackBitmap=CreateCompatibleBitmap(reference,width,height);uiBackOld=(HBITMAP)SelectObject(uiBackDC,uiBackBitmap);
            uiBackW=width;uiBackH=height;
        }
        uiBackKey=-1;   /* the still is rebuilt when the clip stops */
        int left=shellRail,bottom=sy_(800)+shellShift,mw=width-left,mh=bottom-sy_(0);
        if(!hcShade||hcShadeW!=width||hcShadeH!=height){
            if(hcShade)DeleteObject(hcShade);
            void *bits=NULL;hcShade=shell_pargb_layer(width,height,&bits);hcShadeW=width;hcShadeH=height;
            void *bitmap=NULL,*g=NULL;
            if(hcShade&&!GdipCreateBitmapFromScan0(width,height,width*4,SHELL_PARGB,(BYTE*)bits,&bitmap)){
                if(!GdipGetImageGraphicsContext(bitmap,&g)){if(sy_(0)>0)ui_back_shade(g,left,0,mw,bottom,bottom);else ui_back_shade(g,left,sy_(0),mw,mh,bottom);GdipDeleteGraphics(g);}
                GdipDisposeImage(bitmap);
            }
        }
        shell_fill(uiBackDC,0,0,width,height,SHELL_BG);
        heroclip_draw(uiBackDC,left,sy_(0)>0?0:sy_(0),mw,sy_(0)>0?height:mh);
        if(hcShade)shell_layer_blend(uiBackDC,hcShade,0,0,width,height,0,255,1);
        if(bottom<height)shell_fill(uiBackDC,left,bottom,mw,height-bottom,RGB(10,12,17));
        ui_back_rail(uiBackDC,width,height);
        return;
    }
    if(uiBackDC&&uiBackW==width&&uiBackH==height&&uiBackKey==key)return;
    if(!uiBackDC||uiBackW!=width||uiBackH!=height){
        ui_back_release();
        uiBackDC=CreateCompatibleDC(reference);uiBackBitmap=CreateCompatibleBitmap(reference,width,height);uiBackOld=(HBITMAP)SelectObject(uiBackDC,uiBackBitmap);
        uiBackW=width;uiBackH=height;
    }
    uiBackKey=key;
    HDC dc=uiBackDC;float s=shellScale;
    shell_fill(dc,0,0,width,height,SHELL_BG);
    int left=shellRail,top=sy_(0),bottom=sy_(800)+shellShift,right=width,mw=right-left,mh=bottom-top;
    void *g=NULL;
    if(image_token&&!GdipCreateFromHDC(dc,&g)){
        if(shellTab==0||shellTab==4){
            void *image=shellMapImages[key];
            if(image){
                /* cover: fill the page, keep the aspect, crop what does not fit */
                UINT iw=0,ih=0;GdipGetImageWidth(image,&iw);GdipGetImageHeight(image,&ih);
                float sw=(float)iw,sh=(float)iw*mh/mw;if(sh>ih){sh=(float)ih;sw=(float)ih*mw/mh;}
                GdipSetInterpolationMode(g,7);
                /* a window taller than 16:10: the artwork covers the whole height, not a band in the middle */
                int it=top>0?0:top,ih2=top>0?height:mh;
                sh=(float)iw*ih2/mw;sw=(float)iw;if(sh>ih){sh=(float)ih;sw=(float)ih*mw/ih2;}
                GdipDrawImageRectRectI(g,image,left,it,mw,ih2,(int)((iw-sw)/2),(int)((ih-sh)/2),(int)sw,(int)sh,2,NULL,NULL,NULL);
            }
            if(top>0)ui_back_shade(g,left,0,mw,bottom,bottom);else ui_back_shade(g,left,top,mw,mh,bottom);
            if(bottom<height)shell_gradient(g,left,bottom,mw,height-bottom,1,0xF50A0C11,0xF50A0C11);
        }else{
            /* a faint glow of the accent colour in the top right corner */
            void *path=NULL,*brush=NULL;
            float cx=left+mw*0.8f,cy=top-mh*0.1f,rx=900*s,ry=400*s;
            if(!GdipCreatePath(0,&path)){
                GdipAddPathEllipse(path,cx-rx,cy-ry,rx*2,ry*2);
                if(!GdipCreatePathGradientFromPath(path,&brush)&&brush){
                    DWORD edge=SHELL_ARGB(0,SHELL_ACCENT);int count=1;
                    GdipSetPathGradientCenterColor(brush,SHELL_ARGB(30,SHELL_ACCENT));GdipSetPathGradientSurroundColorsWithCount(brush,&edge,&count);
                    GdipFillPath(g,brush,path);GdipDeleteBrush(brush);
                }
                GdipDeletePath(path);
            }
        }
        GdipDeleteGraphics(g);
    }
    ui_back_rail(dc,width,height);
}

/* ---- server details shared by cards and the list ---- */
static const wchar_t *ui_mode_name(int mode){
    static const wchar_t *const names[7]={L"Practice",L"Elimination",L"Team elimination",L"Point capture",L"Team deathmatch",L"Flag capture",L"Bomb"};
    return mode>=0&&mode<7?names[mode]:NULL;
}
static void ui_map_name(const BrowserEntry *e,wchar_t *out,int capacity){
    const wchar_t *m=!_wcsnicmp(e->map,L"obj_",4)?e->map+4:e->map;wcsncpy(out,m,capacity-1);out[capacity-1]=0;
    if(out[0])out[0]=(wchar_t)towupper(out[0]);
}
/* Connection quality: four bars, green to red, grey when there is no answer. */
static void ui_ping_bars(HDC dc,int x,int y,int ping){
    int lit=ping<0?0:ping<=40?4:ping<=80?3:ping<=150?2:1;
    COLORREF on=ping<0?UI_DIM:ping<=80?SHELL_OK:ping<=150?SHELL_AMBER:RGB(228,84,84);
    for(int i=0;i<4;++i){int h=4+i*3;shell_round(dc,(float)(x+i*5),(float)(y+13-h),3,(float)h,1,SHELL_ARGB(255,i<lit?on:RGB(52,60,74)),SHELL_ARGB(255,i<lit?on:RGB(52,60,74)),0);}
}
/* How full a server is: a thin bar, real players in the accent colour and bots in grey. */
static void ui_fill_bar(HDC dc,int x,int y,int w,const BrowserEntry *e){
    shell_round(dc,(float)x,(float)y,(float)w,3,2,SHELL_ARGB(255,RGB(40,47,60)),SHELL_ARGB(255,RGB(40,47,60)),0);
    if(e->slots<=0)return;
    int humans=browser_humans(e),hw=w*(humans<e->slots?humans:e->slots)/e->slots,bw=w*(e->players<e->slots?e->players:e->slots)/e->slots;
    if(bw>hw)shell_round(dc,(float)x,(float)y,(float)bw,3,2,SHELL_ARGB(255,RGB(88,98,116)),SHELL_ARGB(255,RGB(88,98,116)),0);
    if(hw>0)shell_round(dc,(float)x,(float)y,(float)(hw<3?3:hw),3,2,SHELL_ARGB(255,SHELL_ACCENT_HOT),SHELL_ARGB(255,SHELL_ACCENT_HOT),0);
}
/* Tags in front of a server: ranked, verified, anti-cheat, favorite. Returns the x after them. */
static int ui_server_tags(HDC dc,const BrowserEntry *e,int x,int y,int right){
    const wchar_t *tags[4];int green[4],n=0;
    if(e->ranked){tags[n]=L"RANKED";green[n++]=0;}
    if(e->verified){tags[n]=L"VERIFIED";green[n++]=1;}
    if(e->eac>=2){tags[n]=L"EASY ANTI-CHEAT";green[n++]=1;}else if(e->eac==1){tags[n]=L"ANTI-CHEAT ON";green[n++]=0;}
    if(!e->ranked&&!e->verified&&e->favorite){tags[n]=L"FAVORITE";green[n++]=1;}
    for(int i=0;i<n;++i){if(x+ui_width(dc,tags[i],F_TAG,1.5f)+12>right)break;x+=ui_tag(dc,tags[i],x,y,green[i])+6;}
    return x;
}
/* ---- server cards (Play and Servers pages) ---- */
static void ui_server_card(HDC dc,int i,int x,int y,int w,int h,int star){
    BrowserEntry *e=&browserEntries[i];
    int hot=ui_hit(x,y,w,h,H_CARD,i)||(uiHotArg==i&&(uiHotKind==H_JOIN||uiHotKind==H_STAR)),selected=shellTab==1&&browserSelected==i;
    if(hot&&!shellReduceMotion)ui_lift(dc,x,y,w,h),y-=2;
    shell_round(dc,(float)x,(float)y,(float)w,(float)h,8,SHELL_ARGB(219,hot?RGB(27,33,44):SHELL_CARD),SHELL_ARGB(219,hot?RGB(27,33,44):SHELL_CARD),SHELL_ARGB(255,selected?SHELL_ACCENT:hot?SHELL_FIELD_HOT:UI_LINE));
    int online=e->state==BROWSER_ONLINE,map=online?browser_map_index(e->map):-1;
    ui_picture(dc,map>=0?shellThumbImages[map]:NULL,x+12,y+12,112,66,5);
    int tx=x+136,tw=w-136-12-(star?22:0);
    wchar_t title[100];ui_upper(title,online&&e->name[0]?e->name:e->label[0]?e->label:e->address,100);
    ui_text(dc,title,tx,y+10,tw,24,F_CARD,SHELL_TEXT,UI_LINE1,1.0f);
    wchar_t line[160];
    if(online){wchar_t name[64];ui_map_name(e,name,64);const wchar_t *mode=ui_mode_name(e->mode);
        if(mode)swprintf(line,160,L"%ls \x00B7 %ls",name,tr(mode));else wcscpy(line,name);}
    else wcsncpy(line,e->address,159),line[159]=0;
    ui_text(dc,line,tx,y+35,w-136-12,18,online?F_SMALL:F_MONO12,SHELL_MUTED,UI_LINE1,0);
    int sx=tx,sy=y+60;
    if(online){
        /* tags, then players with a fill bar and the connection bars with the ping */
        ui_server_tags(dc,e,tx,y+57,x+w-12-(star?24:0));
        if(e->bots)swprintf(line,160,tr(L"%d/%d \x00B7 +%d bots"),browser_humans(e),e->slots,e->bots);else swprintf(line,160,L"%d/%d",browser_humans(e),e->slots);
        int lw=ui_width(dc,line,F_SMALL,0);if(lw>104)lw=104;
        ui_text(dc,line,sx,y+80,lw+4,18,F_SMALL,SHELL_SUBTLE,UI_LINE1,0);
        ui_fill_bar(dc,sx+lw+10,y+88,48,e);
        if(!hot){ui_ping_bars(dc,x+w-12-62,y+82,e->ping);
            swprintf(line,160,L"%d ms",e->ping);ui_text(dc,line,x+w-12-42,y+80,42,18,F_SMALL,SHELL_SUBTLE,DT_SINGLELINE|DT_VCENTER|DT_RIGHT,0);}
    }else{
        COLORREF dot=e->state==BROWSER_PENDING?SHELL_MUTED:RGB(150,84,90);
        shell_round(dc,(float)sx,(float)sy+6,7,7,7,SHELL_ARGB(255,dot),SHELL_ARGB(255,dot),0);
        ui_text(dc,e->state==BROWSER_PENDING?L"Checking...":e->local?L"Not hosting right now":L"No reply",sx+14,sy,w-160,18,F_SMALL,SHELL_MUTED,UI_LINE1,0);
    }
    if(star){int over=ui_hit(x+w-36,y+4,32,32,H_STAR,i);
        shell_star(dc,(float)(x+w-20),(float)(y+21),7,e->favorite,e->favorite?RGB(240,190,80):over?SHELL_TEXT:UI_DIM);}
    if(hot){int jw=64,jx=x+w-12-jw,jy=y+h-12-26;int over=ui_hit(jx,jy,jw,26,H_JOIN,i);
        shell_round(dc,(float)jx,(float)jy,(float)jw,26,5,SHELL_ARGB(255,over?SHELL_ACCENT_EDGE:SHELL_ACCENT_HOT),SHELL_ARGB(255,over?SHELL_ACCENT_HOT:SHELL_ACCENT),SHELL_ARGB(255,SHELL_ACCENT_EDGE));
        ui_text(dc,L"JOIN",jx,jy,jw+2,26,F_CHIP,RGB(255,255,255),DT_SINGLELINE|DT_VCENTER|DT_CENTER,1.7f);}
}
/* The three servers worth joining right now: online first, then favorites, verified, recent, players. */
static int ui_play_cards(int out[3]){
    int count=0,score[3]={0,0,0};LONG total=browserCount;
    for(LONG i=0;i<total;++i){
        BrowserEntry *e=&browserEntries[i];if(e->local)continue;
        int s=(e->state==BROWSER_ONLINE?1000:e->state==BROWSER_PENDING?500:0)+(e->favorite?200:0)+(e->verified?100:0)+(e->recent?50:0)+(e->state==BROWSER_ONLINE?browser_humans(e):0);
        int at=count<3?count:-1;
        for(int k=0;k<count;++k)if(s>score[k]){at=k;break;}
        if(at<0)continue;
        if(count<3)++count;
        for(int k=count-1;k>at;--k){out[k]=out[k-1];score[k]=score[k-1];}
        out[at]=(int)i;score[at]=s;
    }
    return count;
}

/* Fills the "Jump back in" slots that have no server yet with something useful to do. */
static void ui_action_card(HDC dc,int slot,int servers,int x,int y,int w,int h){
    static const struct {int id,icon;const wchar_t *title,*text;} actions[3]={
        {121,1,L"BROWSE SERVERS",L"Every server online right now"},
        {126,0,L"PRACTICE OFFLINE",L"Warm up against bots, no connection needed"},
        {116,5,L"HOST A SERVER",L"Play with friends on your own rules"}};
    const wchar_t *title=actions[slot].title,*text=actions[slot].text;
    if(!slot&&!servers)text=browserBusy?L"Looking for servers right now...":L"No server answered yet. See the full list";
    int hot=ui_hit(x,y,w,h,H_COMMAND,actions[slot].id);
    if(hot&&!shellReduceMotion)ui_lift(dc,x,y,w,h),y-=2;
    shell_round(dc,(float)x,(float)y,(float)w,(float)h,8,SHELL_ARGB(hot?219:170,hot?RGB(27,33,44):SHELL_CARD),SHELL_ARGB(hot?219:170,hot?RGB(27,33,44):SHELL_CARD),SHELL_ARGB(255,hot?SHELL_FIELD_HOT:UI_LINE));
    shell_round(dc,(float)x+12,(float)y+12,112,66,5,SHELL_ARGB(255,RGB(26,32,43)),SHELL_ARGB(255,RGB(22,27,36)),SHELL_ARGB(255,UI_LINE));
    /* 0.37.1: GDI+ (shell_nav_icon) also applies the DC world transform, so draw in device coordinates under an
     * identity transform; the hand scaling alone was applied twice and put the icons below the cards above 100%. */
    {XFORM t;int scaled=shell_transform(dc,&t);float sc=scaled?t.eM11:1,ox=scaled?t.eDx:0,oy=scaled?t.eDy:0;
     if(scaled){XFORM identity={1,0,0,1,0,0};SetWorldTransform(dc,&identity);}
     shell_nav_icon(dc,actions[slot].icon,ox+(x+12+56-12)*sc,oy+(y+12+33-12)*sc,24*sc,hot?SHELL_ACCENT_HOT:SHELL_STEEL);
     if(scaled)SetWorldTransform(dc,&t);}
    ui_text(dc,title,x+136,y+10,w-148,24,F_CARD,SHELL_TEXT,UI_LINE1,1.0f);
    ui_text(dc,text,x+136,y+36,w-148,40,F_SMALL,SHELL_MUTED,DT_WORDBREAK,0);
    ui_text(dc,L"Open  \x203A",x+136,y+h-30,w-148,18,F_SMALL,hot?SHELL_ACCENT_HOT:SHELL_STEEL,UI_LINE1,0);
}

/* ---- Play page ---- */
/* What the big button does right now: one button for install, update, download progress and play. */
enum {PB_PLAY,PB_INSTALL,PB_FIND,PB_UPDATE,PB_DOWNLOADING,PB_VERIFYING,PB_RESTART,PB_RUNNING,PB_OFF};
static int ui_play_state(int *percent){
    LONG state=update_visible_state();*percent=-1;
    int pinned=updatePinned[0]&&updateCurrent[0]&&!wcscmp(updatePinned,updateCurrent)&&!updateSwitching;
    if(game_running())return PB_RUNNING;
    if(state==UPDATE_DOWNLOADING&&InterlockedCompareExchange(&updateHdOnly,0,0)==2&&!game_missing())return PB_PLAY;
    if(state==UPDATE_DOWNLOADING){LONG64 total=updatePreview>=0?100:updateTotal,done=updatePreview>=0?62:updateDone;
        *percent=total>0?(int)(100.0*(double)done/(double)total):0;if(*percent>100)*percent=100;if(*percent<0)*percent=0;return PB_DOWNLOADING;}
    if(state==UPDATE_VERIFYING)return PB_VERIFYING;
    if(state==UPDATE_READY)return PB_RESTART;
    if(game_missing()){
        if(state==UPDATE_AVAILABLE)return PB_INSTALL;
        return state==UPDATE_OFF?PB_OFF:PB_FIND;
    }
    if(state==UPDATE_AVAILABLE&&!pinned&&!updateRepair)return PB_UPDATE;
    return PB_PLAY;
}
static void ui_play_label(int kind,int percent,wchar_t *label,int labelSize,wchar_t *sub,int subSize){
    double mb=updateTotal/1048576.0;
    switch(kind){
    case PB_RUNNING:wcsncpy(label,L"RUNNING",labelSize);wcsncpy(sub,L"In the game \x00B7 select to switch to it",subSize);break;
    case PB_DOWNLOADING:{swprintf(label,labelSize,L"%d%%",percent);
        double done=updateDone/1048576.0,seconds=updatePreview>=0?40.0:(GetTickCount()-updateStartTick)/1000.0,rate=updatePreview>=0?12.6:(seconds>0.5?done/seconds:0);
        if(updatePreview>=0){done=503;mb=812;}
        /* 0.37.1: the percentage is the label, so the line under it keeps to sizes and speed and fits the button */
        if(rate>0.05)swprintf(sub,subSize,tr(L"%.0f of %.0f MB \x00B7 %.1f MB/s"),done,mb,rate);
        else swprintf(sub,subSize,tr(L"%.0f of %.0f MB"),done,mb);break;}
    case PB_VERIFYING:wcsncpy(label,L"CHECKING",labelSize);wcsncpy(sub,updateRepair?L"Verifying every game file":L"Verifying the downloaded files",subSize);break;
    case PB_RESTART:wcsncpy(label,L"INSTALL",labelSize);wcsncpy(sub,L"Restarts once to finish the update",subSize);break;
    case PB_INSTALL:wcsncpy(label,L"INSTALL",labelSize);
        if(updateTotal>0)swprintf(sub,subSize,tr(L"%.1f GB download"),updateTotal/1073741824.0);else wcsncpy(sub,L"Download the game files",subSize);break;
    case PB_FIND:wcsncpy(label,L"INSTALL",labelSize);
        wcsncpy(sub,update_visible_state()==UPDATE_CHECKING?L"Looking up the latest release":update_visible_state()==UPDATE_FAILED?L"Last try failed \x00B7 select to try again":L"Download the game files",subSize);break;
    case PB_OFF:wcsncpy(label,L"INSTALL",labelSize);wcsncpy(sub,L"Game files not found in this folder",subSize);break;
    case PB_UPDATE:wcsncpy(label,L"UPDATE",labelSize);
        if(mb>=1024)swprintf(sub,subSize,tr(L"%ls \x00B7 %.1f GB, then play"),updateLatest,mb/1024);else swprintf(sub,subSize,tr(L"%ls \x00B7 %.0f MB, then play"),updateLatest,mb<1?1:mb);break;
    default:wcsncpy(label,L"PLAY",labelSize);sub[0]=0;break;
    }
    label[labelSize-1]=0;sub[subSize-1]=0;
}
static void ui_play_subtitle(wchar_t *out,int capacity){
    out[0]=0;
    if(game_missing()){wcsncpy(out,L"Download the game files",capacity);out[capacity-1]=0;return;}
    if(options.mode==2){wcsncpy(out,L"Offline match with bots",capacity);out[capacity-1]=0;return;}
    if(options.mode==1){
        wchar_t address[256]=L"";if(server_edit)GetWindowTextW(server_edit,address,256);
        wchar_t *start=address;while(*start==L' ')++start;
        if(start[0])swprintf(out,capacity,tr(L"Join %ls"),start);else wcsncpy(out,L"Enter a server address",capacity);
        out[capacity-1]=0;return;
    }
    int pick=browserBusy?-1:browser_quick_pick();
    if(pick>=0&&browserEntries[pick].state==BROWSER_ONLINE){const int humans=browser_humans(&browserEntries[pick]);
        if(humans>0)swprintf(out,capacity,tr(L"%d playing \x00B7 %d ms"),humans,browserEntries[pick].ping);
        else swprintf(out,capacity,tr(L"Best server \x00B7 %d ms"),browserEntries[pick].ping);}
    else wcsncpy(out,browserBusy?L"Finding the best server":L"Best server right now",capacity);
    out[capacity-1]=0;
}
static void ui_paint_play(HDC dc,HWND window){
    UiSlide *s=&uiSlides[uiSlide<uiSlideCount?uiSlide:0];
    LONG state=update_visible_state();
    int updating=state==UPDATE_AVAILABLE||state==UPDATE_READY||state==UPDATE_DOWNLOADING||state==UPDATE_VERIFYING;
    /* viewfinder corner, eyebrow and chip */
    shell_fill(dc,244,62,18,2,SHELL_ACCENT_HOT);shell_fill(dc,244,62,2,18,SHELL_ACCENT_HOT);
    wchar_t eyebrow[80],chip[40];
    if(s->eyebrow[0])ui_upper(eyebrow,s->eyebrow,80);
    else if(updateCurrent[0])swprintf(eyebrow,80,tr(L"VERSION %ls"),updateCurrent);
    else wcscpy(eyebrow,L"TRUECOMBAT: PLATINUM");
    if(updating&&uiSlide==0)wcscpy(chip,state==UPDATE_READY?L"READY TO INSTALL":state==UPDATE_AVAILABLE?(updateCurrent[0]?L"UPDATE AVAILABLE":L"READY TO DOWNLOAD"):L"DOWNLOADING");
    else if(s->chip[0])ui_upper(chip,s->chip,40);
    else wcscpy(chip,state==UPDATE_CURRENT?L"UP TO DATE":L"");
    ui_text(dc,eyebrow,256,74,500,22,F_EYEBROW,SHELL_ACCENT_HOT,DT_SINGLELINE|DT_VCENTER,2.8f);
    if(chip[0]){int ew=ui_width(dc,eyebrow,F_EYEBROW,2.8f),cw=ui_width(dc,chip,F_CHIP,1.7f)+18;ui_chip(dc,chip,256+ew+8,74,cw);}
    /* headline: one or two lines, split at | */
    wchar_t title[96];ui_upper(title,s->title,96);wchar_t *second=wcschr(title,L'|');if(second)*second++=0;
    ui_text(dc,title,254,104,900,60,F_HERO,SHELL_TEXT,DT_SINGLELINE|DT_VCENTER,0.5f);
    int copyTop=second?232:176;
    if(second)ui_text(dc,second,254,161,900,60,F_HERO,SHELL_TEXT,DT_SINGLELINE|DT_VCENTER,0.5f);
    ui_text(dc,s->text,256,copyTop,470,46,F_BODY15,SHELL_SUBTLE,DT_WORDBREAK,0);
    /* hero buttons */
    int by=copyTop+61,bx=256;
    wchar_t action[40]=L"";HWND updateButton=GetDlgItem(window,117);
    if(updating&&updateButton)GetWindowTextW(updateButton,action,40);
    if(action[0]){int w=ui_button_width(dc,action);ui_button(dc,action,bx,by,w,36,1,H_COMMAND,117,IsWindowEnabled(updateButton));bx+=w+10;}
    {int w=ui_button_width(dc,s->label1);ui_button(dc,s->label1,bx,by,w,36,0,H_HERO,0,1);bx+=w+10;}
    if(s->label2[0]&&!action[0]){int w=ui_button_width(dc,s->label2);ui_button(dc,s->label2,bx,by,w,36,2,H_HERO,1,1);}
    /* slide dots */
    if(uiSlideCount>1){int x=256;for(int i=0;i<uiSlideCount;++i){int on=i==uiSlide,w=on?36:22;ui_hit(x,by+30,w,15,H_DOT,i);
        shell_round(dc,(float)x,(float)by+36,(float)w,3,2,SHELL_ARGB(255,on?SHELL_ACCENT_HOT:RGB(58,66,82)),SHELL_ARGB(255,on?SHELL_ACCENT_HOT:RGB(58,66,82)),0);x+=w+6;}}
    /* 0.37.1: no second progress strip under the hero buttons; the launch button shows the download */
    /* jump back in */
    ui_text(dc,L"JUMP BACK IN",256,346,300,20,F_SEC,SHELL_MUTED,DT_SINGLELINE|DT_VCENTER,2.6f);
    int cards[3],count=ui_play_cards(cards);
    for(int k=0;k<3;++k){
        int x=256+k*334,y=372,w=320,h=114;
        if(k<count){ui_server_card(dc,cards[k],x,y,w,h,0);continue;}
        ui_action_card(dc,k-count,count,x,y,w,h);
    }
    /* news */
    static const int newsX[3]={256,590,924},newsW[3]={320,320,320};   /* 0.37.1: same columns as the cards above */
    for(int i=0;i<uiNewsCount&&i<3;++i){
        int x=newsX[i],y=500,w=newsW[i],h=116,hot=ui_hit(x,y,w,h,H_NEWS,i);
        if(hot&&!shellReduceMotion)ui_lift(dc,x,y,w,h),y-=2;
        shell_round(dc,(float)x,(float)y,(float)w,(float)h,8,SHELL_ARGB(hot?215:179,hot?RGB(27,33,44):SHELL_CARD),SHELL_ARGB(hot?215:179,hot?RGB(27,33,44):SHELL_CARD),SHELL_ARGB(255,hot?SHELL_FIELD_HOT:UI_LINE));
        wchar_t caps[80];ui_upper(caps,uiNews[i].tag,80);
        ui_text(dc,caps,x+14,y+15,w-28,18,F_CHIP,SHELL_ACCENT_HOT,UI_LINE1,1.9f);
        ui_upper(caps,uiNews[i].title,80);
        ui_text(dc,caps,x+14,y+36,w-28,24,F_CARD,SHELL_TEXT,UI_LINE1,0.85f);
        ui_text(dc,uiNews[i].text,x+14,y+63,w-28,40,F_DESC,SHELL_MUTED,DT_WORDBREAK|DT_END_ELLIPSIS,0);
    }
    /* launch bar: who plays and with what */
    {
        wchar_t raw[64]=L"",name[64],summary[200],preset[64]=L"",resolution[64]=L"";
        if(name_edit)GetWindowTextW(name_edit,raw,64);
        int n=0;for(const wchar_t *c=raw;*c&&n<63;++c){if(c[0]==L'^'&&c[1]&&c[1]!=L'^'){++c;continue;}name[n++]=*c;}name[n]=0;
        if(!name[0])wcscpy(name,L"Player");
        wchar_t initial[2]={(wchar_t)towupper(name[0]),0};
        for(const wchar_t *c=name;*c;++c)if(iswalnum(*c)){initial[0]=(wchar_t)towupper(*c);break;}
        int hot=ui_hit(256,730,270,54,H_WHO,0);
        shell_round(dc,256,734,46,46,8,SHELL_ARGB(255,RGB(42,49,64)),SHELL_ARGB(255,RGB(26,32,43)),SHELL_ARGB(255,hot?SHELL_FIELD_HOT:RGB(56,64,77)));
        ui_text(dc,initial,256,734,47,46,F_AVA,SHELL_ACCENT_HOT,DT_SINGLELINE|DT_VCENTER|DT_CENTER,0);
        wchar_t caps[64];ui_upper(caps,name,64);
        if(nc_has_codes(raw))nc_draw_name(dc,raw,314,735,206,24,F_WHO,1.1f,1,SHELL_TEXT);   /* name colours */
        else ui_text(dc,caps,314,735,206,24,F_WHO,SHELL_TEXT,UI_LINE1,1.1f);
        if(stats_ranked()){int nw=ui_width(dc,caps,F_WHO,1.1f);if(nw>120)nw=120;stats_rank_tag_short(dc,314+nw+10,738);}   /* rank and rating from the stats service */
        if(preset_combo)GetWindowTextW(preset_combo,preset,64);
        if(resolution_combo)GetWindowTextW(resolution_combo,resolution,64);
        {wchar_t *paren=wcsstr(preset,L" (");if(paren)*paren=0;}
        for(wchar_t *c=resolution;*c;++c)if(*c==L'x'&&c>resolution&&c[-1]==L' ')*c=0x00D7;
        swprintf(summary,200,L"%ls \x00B7 %ls%ls  \x203A",preset,resolution,PLATINUM_NATIVE?L" \x00B7 DirectX 12":L"");
        ui_text(dc,summary,314,759,212,18,F_SMALL,hot?SHELL_SUBTLE:SHELL_MUTED,UI_LINE1,0);
    }
    /* mode switch */
    {
        static const wchar_t *const small[3]={L"MODE",L"JOIN",L"OFFLINE"},*const big[3]={L"QUICK PLAY",L"BY ADDRESS",L"PRACTICE"};
        shell_round(dc,536,716,398,64,8,SHELL_ARGB(230,SHELL_CARD),SHELL_ARGB(230,SHELL_CARD),SHELL_ARGB(255,RGB(52,62,78)));
        for(int i=0;i<3;++i){
            int x=537+i*132,on=options.mode==i,hot=ui_hit(x,717,132,62,H_SEG,i);
            if(on||hot){
                XFORM t;shell_transform(dc,&t);XFORM identity={1,0,0,1,0,0};SetWorldTransform(dc,&identity);
                int dx=(int)(x*t.eM11+t.eDx),dy=(int)(717*t.eM22+t.eDy),dw=(int)(132*t.eM11),dh=(int)(62*t.eM22);
                HRGN clip=CreateRoundRectRgn((int)(537*t.eM11+t.eDx),dy,(int)(933*t.eM11+t.eDx)+1,dy+dh+1,(int)(14*t.eM11),(int)(14*t.eM11));SelectClipRgn(dc,clip);
                void *g=NULL;if(!GdipCreateFromHDC(dc,&g)){
                    if(on)shell_gradient(g,dx,dy,dw,dh,1,SHELL_ARGB(51,SHELL_ACCENT),SHELL_ARGB(15,SHELL_ACCENT));else shell_gradient(g,dx,dy,dw,dh,1,0x10FFFFFF,0x10FFFFFF);
                    GdipDeleteGraphics(g);}
                if(on)shell_fill(dc,dx,dy+dh-(int)(2*t.eM22+0.5f),dw,(int)(2*t.eM22+0.5f),SHELL_ACCENT_HOT);
                SelectClipRgn(dc,NULL);DeleteObject(clip);SetWorldTransform(dc,&t);
            }
            if(i<2)shell_fill(dc,x+131,717,1,62,RGB(42,50,64));
            ui_text(dc,small[i],x+18,731,110,16,F_TAG,UI_DIM,UI_LINE1,2.0f);
            ui_text(dc,big[i],x+18,746,112,22,F_SEGB,SHELL_TEXT,UI_LINE1,1.0f);
        }
    }
    /* PLAY with its menu arrow */
    {
        int percent=-1,kind=ui_play_state(&percent);
        HWND playButton=GetDlgItem(window,104);int arrowOn=!playButton||IsWindowEnabled(playButton),enabled=arrowOn&&kind!=PB_OFF;
        int hot=enabled?ui_hit(950,716,250,64,H_PLAY,0):(ui_hit(950,716,250,64,H_DISABLED,104),0),arrow=arrowOn&&ui_hit(1200,716,44,64,H_ARROW,0);
        for(int i=5;i>=1;--i)shell_round(dc,(float)(950-i*3),(float)(716+10-i*3),(float)(294+i*6),(float)(64+i*6),(float)(8+i*3),SHELL_ARGB(enabled?13:0,SHELL_ACCENT),SHELL_ARGB(enabled?13:0,SHELL_ACCENT),0);
        COLORREF top=enabled?(hot?SHELL_ACCENT_EDGE:SHELL_ACCENT_HOT):RGB(52,58,70),low=enabled?(hot?SHELL_ACCENT_HOT:shell_mix(SHELL_ACCENT,SHELL_ACCENT_DOWN,0.3f)):RGB(40,45,55);
        shell_round(dc,950,716,294,64,8,SHELL_ARGB(255,top),SHELL_ARGB(255,low),0);
        {XFORM t;shell_transform(dc,&t);XFORM identity={1,0,0,1,0,0};SetWorldTransform(dc,&identity);
         int dx=(int)(1200*t.eM11+t.eDx),dy=(int)(716*t.eM22+t.eDy),dr=(int)(1244*t.eM11+t.eDx),db=(int)(780*t.eM22+t.eDy);
         HRGN whole=CreateRoundRectRgn((int)(950*t.eM11+t.eDx),dy,dr+1,db+1,(int)(16*t.eM11),(int)(16*t.eM11)),side=CreateRectRgn(dx,dy,dr+1,db+1);
         CombineRgn(side,side,whole,RGN_AND);SelectClipRgn(dc,side);
         shell_fill(dc,dx,dy,dr-dx+1,db-dy+1,enabled?(arrow?SHELL_ACCENT:shell_mix(SHELL_ACCENT_DOWN,SHELL_ACCENT,0.25f)):(arrow?RGB(50,57,70):RGB(34,38,47)));
         shell_fill(dc,dx,dy,1,db-dy+1,enabled?shell_mix(SHELL_ACCENT_DOWN,RGB(0,0,0),0.25f):RGB(28,32,40));
         SelectClipRgn(dc,NULL);DeleteObject(whole);DeleteObject(side);SetWorldTransform(dc,&t);}
        {HBRUSH brush=CreateSolidBrush(RGB(255,255,255));HPEN none=CreatePen(PS_NULL,0,0);HGDIOBJ ob=SelectObject(dc,brush),op=SelectObject(dc,none);
         POINT tri[]={{1218,746},{1227,746},{1222,752}};Polygon(dc,tri,3);SelectObject(dc,ob);SelectObject(dc,op);DeleteObject(brush);DeleteObject(none);}
        wchar_t label[40]=L"PLAY",sub[160];
        ui_play_label(kind,percent,label,40,sub,160);
        if(kind==PB_PLAY)ui_play_subtitle(sub,160);
        int lw=ui_width(dc,label,F_PLAY,3.8f),sw=ui_width(dc,sub,F_PLAYSUB,0.2f),block=(lw>sw?lw:sw),x=950+(250-block-46)/2;if(x<962)x=962;
        if(kind==PB_DOWNLOADING||kind==PB_VERIFYING){
            /* progress along the foot of the button; verifying runs as a full, calm bar */
            int track=250-24,fill=kind==PB_VERIFYING?track:track*percent/100;
            shell_round(dc,962,774,(float)track,3,3,SHELL_ARGB(70,RGB(0,0,0)),SHELL_ARGB(70,RGB(0,0,0)),0);
            if(fill>2)shell_round(dc,962,774,(float)fill,3,3,SHELL_ARGB(235,RGB(255,255,255)),SHELL_ARGB(235,RGB(255,255,255)),0);
            ui_icon_download(dc,x,748,kind==PB_VERIFYING);
        }else if(kind==PB_RUNNING)shell_round(dc,(float)x-2,742,12,12,12,SHELL_ARGB(255,RGB(127,220,163)),SHELL_ARGB(255,RGB(127,220,163)),0);
        else shell_play_icon(dc,x,748,13,RGB(255,255,255));
        ui_text(dc,label,x+46,722,lw+8,38,F_PLAY,RGB(255,255,255),DT_SINGLELINE|DT_VCENTER,3.8f);
        ui_text(dc,sub,x+46,756,950+250-(x+46)-6,16,F_PLAYSUB,RGB(255,236,236),UI_LINE1,0.2f);
    }
}

/* ---- "What's new": once, on the Play page, the first time the launcher opens after the game was updated ---- */
static int uiWhatsNewForced,uiWhatsNewState=-1;   /* --whats-new shows it for captures; state: -1 unknown, 0 hidden, 1 shown */
static int ui_whats_new_visible(void){
    if(uiWhatsNewForced)return 1;
    if(uiWhatsNewState<0){
        uiWhatsNewState=0;
        if(updateCurrent[0]){wchar_t seen[64];GetPrivateProfileStringW(L"Launcher",L"SeenVersion",L"",seen,64,ini);
            if(!seen[0])WritePrivateProfileStringW(L"Launcher",L"SeenVersion",updateCurrent,ini);   /* first install: nothing to announce */
            else uiWhatsNewState=wcscmp(seen,updateCurrent)!=0;}
    }
    return uiWhatsNewState==1;
}
static void ui_whats_new_done(void){
    uiWhatsNewForced=0;uiWhatsNewState=0;
    if(updateCurrent[0])WritePrivateProfileStringW(L"Launcher",L"SeenVersion",updateCurrent,ini);
}
static void ui_paint_whats_new(HDC dc){
    int x=808,y=62,w=436,h=InterlockedCompareExchange(&newsState,0,0)==2?262:196;   /* 0.37.1: no gap under a short message */
    shell_round(dc,(float)x,(float)y,(float)w,(float)h,10,SHELL_ARGB(236,RGB(17,21,29)),SHELL_ARGB(236,RGB(14,17,24)),SHELL_ARGB(255,shell_mix(UI_LINE,SHELL_ACCENT,0.45f)));
    shell_fill(dc,x+1,y+1,w-2,2,SHELL_ACCENT_HOT);
    ui_text(dc,L"WHAT'S NEW",x+20,y+18,200,20,F_EYEBROW,SHELL_ACCENT_HOT,DT_SINGLELINE|DT_VCENTER,2.4f);
    wchar_t version[64];if(updateCurrent[0]){wcsncpy(version,updateCurrent,63);version[63]=0;wchar_t *dash=wcschr(version,L'-');if(dash)*dash=0;}else wcscpy(version,L"0.38.0");
    {wchar_t chip[80];swprintf(chip,80,L"V%ls",version);int cw=ui_width(dc,chip,F_CHIP,1.7f)+18;ui_chip(dc,chip,x+w-20-cw,y+17,cw);}
    LONG state=InterlockedCompareExchange(&newsState,0,0);
    if(state==2){
        NewsItem *n=&newsItems[0];wchar_t caps[130];ui_upper(caps,n->title,130);
        ui_text(dc,caps,x+20,y+46,w-40,26,F_CARD,SHELL_TEXT,UI_LINE1,0.85f);
        /* the first four bullet points of the release notes */
        int by=y+80,count=0;const wchar_t *line=n->body;
        while(*line&&count<4){
            const wchar_t *end=wcschr(line,L'\n');size_t length=end?(size_t)(end-line):wcslen(line);
            wchar_t text[300];if(length>299)length=299;wcsncpy(text,line,length);text[length]=0;line=end?end+1:line+wcslen(line);
            const wchar_t *p=text;while(*p==L' ')++p;
            if((p[0]==L'-'||p[0]==L'*'||p[0]==0x2022)&&p[1]==L' '){
                wchar_t clean[300];int c=0;for(const wchar_t *q=p+2;*q;++q){if((q[0]==L'*'&&q[1]==L'*')){++q;continue;}if(*q!=L'\r'&&*q!=L'`')clean[c++]=*q;}clean[c]=0;
                shell_round(dc,(float)x+22,(float)by+7,5,5,5,SHELL_ARGB(255,SHELL_ACCENT_HOT),SHELL_ARGB(255,SHELL_ACCENT_HOT),0);
                ui_text(dc,clean,x+36,by,w-56,20,F_DESC,SHELL_SUBTLE,UI_LINE1,0);by+=26;++count;
            }
        }
        if(!count)ui_text(dc,L"Every fix and feature of this release is on the News page.",x+20,by,w-40,40,F_DESC,SHELL_SUBTLE,DT_WORDBREAK,0);
    }else{
        ui_text(dc,L"THE GAME WAS UPDATED",x+20,y+46,w-40,26,F_CARD,SHELL_TEXT,UI_LINE1,0.85f);
        ui_text(dc,state==1?L"Loading the patch notes...":L"The patch notes load here when you are online. They are also on the News page.",x+20,y+80,w-40,60,F_DESC,SHELL_SUBTLE,DT_WORDBREAK,0);
    }
    int bw=ui_button_width(dc,L"Read the patch notes");ui_button(dc,L"Read the patch notes",x+20,y+h-52,bw,34,1,H_WHATSNEW,1,1);
    int gw=ui_button_width(dc,L"Got it");ui_button(dc,L"Got it",x+20+bw+10,y+h-52,gw,34,0,H_WHATSNEW,0,1);
}
/* ---- 2.6.0: anonymous crash and hardware reports, asked once on the Play page ---- */
static void ui_paint_telemetry_card(HDC dc){
    int x=808,y=62,w=436,h=232;
    shell_round(dc,(float)x,(float)y,(float)w,(float)h,10,SHELL_ARGB(236,RGB(17,21,29)),SHELL_ARGB(236,RGB(14,17,24)),SHELL_ARGB(255,shell_mix(UI_LINE,SHELL_ACCENT,0.45f)));
    shell_fill(dc,x+1,y+1,w-2,2,SHELL_ACCENT_HOT);
    ui_text(dc,L"HELP US IMPROVE",x+20,y+18,300,20,F_EYEBROW,SHELL_ACCENT_HOT,DT_SINGLELINE|DT_VCENTER,2.4f);
    ui_text(dc,L"SHARE CRASH AND HARDWARE DATA?",x+20,y+46,w-40,26,F_CARD,SHELL_TEXT,UI_LINE1,0.85f);
    ui_text(dc,L"If the game crashes, the launcher can tell us where, so we can fix it sooner. Once a month it also shares your Windows version, processor, memory and graphics card. It is anonymous: no name, no ID, no IP address.",
            x+20,y+80,w-40,84,F_DESC,SHELL_SUBTLE,DT_WORDBREAK,0);
    /* two equal choices: neither one is the highlighted default */
    int bw=ui_button_width(dc,L"Share"),nw=ui_button_width(dc,L"No thanks");if(bw<nw)bw=nw;
    ui_button(dc,L"Share",x+20,y+h-52,bw,34,0,H_TELEMETRY,1,1);
    ui_button(dc,L"No thanks",x+20+bw+10,y+h-52,bw,34,0,H_TELEMETRY,0,1);
    {const wchar_t *more=L"What is shared";int mw=ui_width(dc,more,F_SMALL,0)+8,hot=ui_hit(x+w-20-mw,y+h-52,mw,34,H_TELEMETRY,2);
     ui_text(dc,more,x+w-20-mw,y+h-52,mw,34,F_SMALL,hot?SHELL_ACCENT_HOT:SHELL_STEEL,DT_SINGLELINE|DT_VCENTER|DT_RIGHT,0);}
    ui_text(dc,L"You can change this any time in Settings > Privacy.",x+20,y+h-14,w-40,14,F_SMALL,SHELL_MUTED,UI_LINE1,0);
}
/* ---- first start: name, graphics and accent on one page, in the launcher itself ---- */
static int uiWelcomePreset=-1;
static void shell_set_tab(HWND window,int tab);
static void ui_welcome_open(HWND window){
    first_run_detect();
    if(uiWelcomePreset<0)uiWelcomePreset=firstRun.preset;
    HWND edit=GetDlgItem(window,156);
    if(edit){wchar_t name[64]=L"";GetWindowTextW(name_edit,name,64);if(!wcscmp(name,L"Player"))name[0]=0;SetWindowTextW(edit,name);}
    shell_set_tab(window,4);
    if(edit&&!capture_ui_path[0])SetFocus(edit);
}
static int save_graphics_preferences(void);static void update_graphics_summary(void);static int valid_name(const wchar_t *s);
static void ui_welcome_finish(HWND window,int how){   /* 0 skip, 1 find a server, 2 practice (or continue) */
    wchar_t name[64]=L"";HWND edit=GetDlgItem(window,156);if(edit)GetWindowTextW(edit,name,64);
    if(name[0]&&!valid_name(name)){
        MessageBoxW(window,tr(L"Use 1 to 24 letters, numbers, spaces or these symbols: _ - * ( ) ."),TITLE,MB_OK|MB_ICONINFORMATION);
        if(edit)SetFocus(edit);return;}
    if(!name[0]&&how){MessageBoxW(window,tr(L"Choose the name other players will see."),TITLE,MB_OK|MB_ICONINFORMATION);if(edit)SetFocus(edit);return;}
    if(name[0]){SetWindowTextW(name_edit,name);WritePrivateProfileStringW(L"Player",L"Name",name,ini);}
    /* 0.37 GPU starting preset: Skip on a fresh install (no saved [Graphics] Preset yet) also takes the preset
       recommended for the graphics card instead of the High default; saved choices are never changed */
    if((how||(int)GetPrivateProfileIntW(L"Graphics",L"Preset",-1,ini)<0)&&uiWelcomePreset>=0&&uiWelcomePreset<=2){
        SendMessageW(preset_combo,CB_SETCURSEL,uiWelcomePreset,0);SendMessageW(resolution_combo,CB_SETCURSEL,0,0);
        save_graphics_preferences();update_graphics_summary();
    }
    WritePrivateProfileStringW(L"Setup",L"Done",L"1",ini);
    shell_set_tab(window,how==1?1:0);
    if(how==2&&!game_missing())PostMessageW(window,WM_COMMAND,126,0);
}
static void ui_paint_welcome(HDC dc){
    shell_fill(dc,244,62,18,2,SHELL_ACCENT_HOT);shell_fill(dc,244,62,2,18,SHELL_ACCENT_HOT);
    ui_text(dc,L"FIRST START",256,74,500,22,F_EYEBROW,SHELL_ACCENT_HOT,DT_SINGLELINE|DT_VCENTER,2.8f);
    {wchar_t title[96];ui_upper(title,L"Welcome to|Platinum.",96);wchar_t *second=wcschr(title,L'|');if(second)*second++=0;
     ui_text(dc,title,254,104,900,60,F_HERO,SHELL_TEXT,DT_SINGLELINE|DT_VCENTER,0.5f);
     if(second)ui_text(dc,second,254,161,900,60,F_HERO,SHELL_TEXT,DT_SINGLELINE|DT_VCENTER,0.5f);}
    ui_text(dc,L"Three quick choices and you are ready. Everything here can be changed later in Settings.",256,232,700,22,F_BODY15,SHELL_SUBTLE,UI_LINE1,0);
    /* left: name and graphics */
    shell_round(dc,256,276,486,420,8,SHELL_ARGB(225,SHELL_CARD),SHELL_ARGB(225,SHELL_CARD),SHELL_ARGB(255,UI_LINE));
    ui_text(dc,L"PLAYER NAME",275,294,400,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
    ui_text(dc,L"What other players see. Up to 24 letters, numbers and _ - * ( ) .",275,368,448,20,F_DESC,SHELL_MUTED,UI_LINE1,0);
    ui_text(dc,L"GRAPHICS",275,410,400,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
    static const wchar_t *const presets[3]={L"LOW",L"HIGH",L"ULTRA"},*const presetText[3]={L"The original look",L"Modern lighting",L"Everything on"};
    for(int i=0;i<3;++i){
        int x=275+i*154,y=436,w=142,h=96,on=uiWelcomePreset==i,hot=ui_hit(x,y,w,h,H_PRESET,i);
        shell_round(dc,(float)x,(float)y,(float)w,(float)h,8,SHELL_ARGB(255,on?shell_mix(SHELL_CARD,SHELL_ACCENT,0.18f):hot?RGB(30,36,48):RGB(24,29,39)),SHELL_ARGB(255,on?shell_mix(SHELL_CARD,SHELL_ACCENT,0.10f):hot?RGB(27,33,44):RGB(21,26,35)),
                    SHELL_ARGB(255,on?SHELL_ACCENT:hot?SHELL_FIELD_HOT:RGB(44,52,66)));
        ui_text(dc,presets[i],x+14,y+12,w-28,24,F_CARD,SHELL_TEXT,UI_LINE1,1.0f);
        ui_text(dc,presetText[i],x+14,y+38,w-28,18,F_SMALL,SHELL_MUTED,UI_LINE1,0);
        if(firstRun.preset==i)ui_tag(dc,L"RECOMMENDED",x+14,y+66,1);
        if(on)ui_check(dc,x+w-26,y+14,12,SHELL_ACCENT_HOT);
    }
    {wchar_t pc[260];swprintf(pc,260,L"%ls \x00B7 %llu GB",firstRun.adapter,firstRun.memory>>30);
     ui_text(dc,pc,275,548,448,20,F_SMALL,SHELL_SUBTLE,UI_LINE1,0);
     ui_text(dc,firstRun.dx12?L"DirectX 12 is ready, so PLAY uses it.":L"DirectX 12 did not start on this PC. Safe start (OpenGL) still works.",275,570,448,20,F_SMALL,firstRun.dx12?SHELL_OK:SHELL_AMBER,UI_LINE1,0);
     ui_text(dc,L"Ultra adds NVIDIA DLAA on RTX cards. The graphics report in Settings shows what your card supports.",275,604,448,40,F_SMALL,SHELL_MUTED,DT_WORDBREAK,0);}
    /* right: accent, language and what to expect */
    shell_round(dc,758,276,486,420,8,SHELL_ARGB(225,SHELL_CARD),SHELL_ARGB(225,SHELL_CARD),SHELL_ARGB(255,UI_LINE));
    ui_text(dc,L"ACCENT COLOUR",777,294,400,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
    for(int i=0;i<OPTION_ACCENTS;++i){
        int sx=777+i*58,sy=324,hot=ui_hit(sx-4,sy-4,48,48,H_SWATCH,i);
        shell_round(dc,(float)sx,(float)sy,40,40,8,SHELL_ARGB(255,optionAccents[i].base),SHELL_ARGB(255,optionAccents[i].base),0);
        if(i==options.accent){shell_round(dc,(float)sx-3,(float)sy-3,46,46,10,0,0,SHELL_ARGB(255,RGB(255,255,255)));ui_check(dc,sx+14,sy+14,12,RGB(255,255,255));}
        else if(hot)shell_round(dc,(float)sx-3,(float)sy-3,46,46,10,0,0,SHELL_ARGB(150,RGB(255,255,255)));
    }
    ui_text(dc,L"LANGUAGE",777,390,400,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
    {static const wchar_t *const names[4]={L"English",L"Deutsch",L"Fran\u00E7ais",L"Polski"};int lx=777;
     for(int i=0;i<4;++i){int lw=ui_width(dc,names[i],F_ROW,0)+28,on=uiLang==i,hot=ui_hit(lx,416,lw,34,H_LANG,i+1);
        shell_round(dc,(float)lx,416,(float)lw,34,17,SHELL_ARGB(255,on?SHELL_ACCENT:hot?RGB(34,41,54):RGB(24,29,39)),SHELL_ARGB(255,on?SHELL_ACCENT:hot?RGB(34,41,54):RGB(24,29,39)),SHELL_ARGB(255,on?SHELL_ACCENT_EDGE:hot?SHELL_FIELD_HOT:RGB(44,52,66)));
        ui_text(dc,names[i],lx,416,lw,34,F_ROW,on?RGB(255,255,255):SHELL_SUBTLE,DT_SINGLELINE|DT_VCENTER|DT_CENTER,0);lx+=lw+8;}}
    ui_text(dc,L"YOUR FIRST MATCH",777,480,400,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
    ui_text(dc,L"TrueCombat: Platinum is a tactical team shooter. Damage is realistic, so cover, positioning and teamwork matter more than speed. A practice match against bots is the best place to start.",
            777,508,448,110,F_BODY14,SHELL_SUBTLE,DT_WORDBREAK,0);
    /* bottom: skip, find a server, and the big way in */
    {int w=ui_button_width(dc,L"Skip for now");ui_button(dc,L"Skip for now",256,730,w,40,2,H_WELCOME,0,1);
     int w2=ui_button_width(dc,L"Find a server");ui_button(dc,L"Find a server",256+w+10,730,w2,40,0,H_WELCOME,1,1);}
    {int missing=game_missing(),hot=ui_hit(950,716,294,64,H_WELCOME,2);
     for(int i=5;i>=1;--i)shell_round(dc,(float)(950-i*3),(float)(716+10-i*3),(float)(294+i*6),(float)(64+i*6),(float)(8+i*3),SHELL_ARGB(13,SHELL_ACCENT),SHELL_ARGB(13,SHELL_ACCENT),0);
     shell_round(dc,950,716,294,64,8,SHELL_ARGB(255,hot?SHELL_ACCENT_EDGE:SHELL_ACCENT_HOT),SHELL_ARGB(255,hot?SHELL_ACCENT_HOT:shell_mix(SHELL_ACCENT,SHELL_ACCENT_DOWN,0.3f)),0);
     wchar_t label[40];ui_upper(label,missing?L"Continue":L"Practice",40);
     const wchar_t *sub=missing?L"Then install the game files":L"Offline against bots on Railhouse";
     int lw=ui_width(dc,label,F_PLAY,3.8f),sw=ui_width(dc,sub,F_PLAYSUB,0.2f),block=lw>sw?lw:sw,x=950+(294-block-46)/2;if(x<962)x=962;
     shell_play_icon(dc,x,748,13,RGB(255,255,255));
     ui_text(dc,label,x+46,722,lw+8,38,F_PLAY,RGB(255,255,255),DT_SINGLELINE|DT_VCENTER,3.8f);
     ui_text(dc,sub,x+46,758,950+294-(x+46)-6,16,F_PLAYSUB,RGB(255,236,236),UI_LINE1,0.2f);}
}
/* ---- language: Settings > Launcher > Language, and the first-start page ---- */
static void ui_language_set(HWND window,int choice){
    if(choice<0||choice>4)return;
    options.lang=choice;options_set(L"Language",choice);
    int before=uiLang;lang_resolve();
    HWND combo=GetDlgItem(window,154);if(combo)SendMessageW(combo,CB_SETCURSEL,choice,0);
    if(before!=uiLang){
        ui_fonts_dispose();shell_fonts_reload();shell_release_scaled_fonts();tip_dpi_changed();combos_translate(window);update_graphics_summary();
        shell_layout(window);ui_window_title(window);
        RedrawWindow(window,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_ERASE);
    }
    ui_saved();
}
/* ---- page header shared by Servers, News and Settings ---- */
static void ui_page_head(HDC dc,const wchar_t *title,const wchar_t *text){
    ui_text(dc,title,254,36,700,58,F_H1,SHELL_TEXT,DT_SINGLELINE|DT_VCENTER,1.6f);
    ui_text(dc,text,256,96,700,22,F_BODY14,SHELL_MUTED,UI_LINE1,0);
}
/* ---- Servers page: a sortable list ----
   Columns: picture and name (with tags), map, mode, players, ping, then favorite and Join.
   The header sorts (ascending, descending, back to the default order); This PC stays first. */
static const struct {const wchar_t *label;int bit;} uiBrowserChips[]={{L"HIDE FULL",BROWSER_HIDE_FULL},{L"HIDE EMPTY",BROWSER_HIDE_EMPTY},{L"RANKED",BROWSER_RANKED_ONLY},{L"NO BOTS",BROWSER_NO_BOTS}};
#define UI_SERVER_ROWS 12
#define UI_ROW_TOP 206
#define UI_ROW_H 44
static const struct {const wchar_t *label;int x,w,sort;} uiColumns[]={
    {L"SERVER",324,316,1},{L"MAP",652,128,2},{L"MODE",792,158,3},{L"PLAYERS",962,104,4},{L"PING",1078,82,5}};
static void ui_sort_arrow(HDC dc,int x,int y,int down,COLORREF color){
    XFORM t;int scaled=shell_transform(dc,&t);float s=scaled?t.eM11:1,ox=scaled?t.eDx:0,oy=scaled?t.eDy:0;
    XFORM identity={1,0,0,1,0,0};if(scaled)SetWorldTransform(dc,&identity);
    HBRUSH brush=CreateSolidBrush(color);HPEN none=CreatePen(PS_NULL,0,0);HGDIOBJ ob=SelectObject(dc,brush),op=SelectObject(dc,none);
    POINT p[3];
    if(down){p[0]=(POINT){(LONG)(ox+x*s),(LONG)(oy+y*s)};p[1]=(POINT){(LONG)(ox+(x+8)*s),(LONG)(oy+y*s)};p[2]=(POINT){(LONG)(ox+(x+4)*s),(LONG)(oy+(y+5)*s)};}
    else{p[0]=(POINT){(LONG)(ox+x*s),(LONG)(oy+(y+5)*s)};p[1]=(POINT){(LONG)(ox+(x+8)*s),(LONG)(oy+(y+5)*s)};p[2]=(POINT){(LONG)(ox+(x+4)*s),(LONG)(oy+y*s)};}
    Polygon(dc,p,3);SelectObject(dc,ob);SelectObject(dc,op);DeleteObject(brush);DeleteObject(none);
    if(scaled)SetWorldTransform(dc,&t);
}
static void ui_server_row(HDC dc,int i,int y){
    BrowserEntry *e=&browserEntries[i];
    int online=e->state==BROWSER_ONLINE,selected=browserSelected==i;
    int hot=ui_hit(256,y,980,UI_ROW_H-4,H_CARD,i)||(uiHotArg==i&&(uiHotKind==H_JOIN||uiHotKind==H_STAR));
    if(hot||selected)shell_round(dc,256,(float)y,988,UI_ROW_H-4,6,SHELL_ARGB(selected?235:200,selected?RGB(30,36,48):RGB(25,31,41)),SHELL_ARGB(selected?235:200,selected?RGB(30,36,48):RGB(25,31,41)),SHELL_ARGB(255,selected?SHELL_ACCENT:SHELL_FIELD_HOT));
    if(selected)shell_round(dc,256,(float)y+8,3,UI_ROW_H-20,2,SHELL_ARGB(255,SHELL_ACCENT_HOT),SHELL_ARGB(255,SHELL_ACCENT_HOT),0);
    int map=online?browser_map_index(e->map):-1;
    ui_picture(dc,map>=0?shellThumbImages[map]:NULL,264,y+4,52,32,4);
    COLORREF ink=online?SHELL_TEXT:SHELL_MUTED;
    wchar_t title[100];wcsncpy(title,online&&e->name[0]?e->name:e->label[0]?e->label:e->address,99);title[99]=0;
    int nw=ui_width(dc,title,F_ROW,0);if(nw>300)nw=300;
    ui_text(dc,title,324,y+3,nw+4,20,F_ROW,ink,UI_LINE1,0);
    if(online)ui_server_tags(dc,e,324+nw+10,y+4,640);
    ui_text(dc,e->address,324,y+22,316,16,F_MONO11,UI_DIM,UI_LINE1,0);
    wchar_t text[120];
    if(online){
        ui_map_name(e,text,120);ui_text(dc,text,652,y,128,UI_ROW_H-4,F_DESC,SHELL_SUBTLE,UI_LINE1,0);
        const wchar_t *mode=ui_mode_name(e->mode);ui_text(dc,mode?tr(mode):L"\x2014",792,y,158,UI_ROW_H-4,F_DESC,SHELL_SUBTLE,UI_LINE1,0);
        if(e->bots)swprintf(text,120,L"%d/%d +%d",browser_humans(e),e->slots,e->bots);else swprintf(text,120,L"%d/%d",browser_humans(e),e->slots);
        ui_text(dc,text,962,y+3,104,20,F_DESC,SHELL_TEXT,UI_LINE1,0);ui_fill_bar(dc,962,y+26,72,e);
        ui_ping_bars(dc,1078,y+13,e->ping);swprintf(text,120,L"%d ms",e->ping);ui_text(dc,text,1102,y,58,UI_ROW_H-4,F_DESC,SHELL_SUBTLE,UI_LINE1,0);
    }else{
        COLORREF dot=e->state==BROWSER_PENDING?SHELL_MUTED:RGB(150,84,90);
        shell_round(dc,652,(float)y+17,7,7,7,SHELL_ARGB(255,dot),SHELL_ARGB(255,dot),0);
        ui_text(dc,e->state==BROWSER_PENDING?L"Checking...":e->local?L"Not hosting right now":L"No reply",666,y,300,UI_ROW_H-4,F_DESC,SHELL_MUTED,UI_LINE1,0);
    }
    {int over=ui_hit(1170,y+4,32,32,H_STAR,i);shell_star(dc,1186,(float)y+20,7,e->favorite,e->favorite?RGB(240,190,80):over?SHELL_TEXT:UI_DIM);}
    if(hot&&!e->local){int over=ui_hit(1206,y+7,36,26,H_JOIN,i);
        shell_round(dc,1206,(float)y+7,36,26,5,SHELL_ARGB(255,over?SHELL_ACCENT_EDGE:SHELL_ACCENT_HOT),SHELL_ARGB(255,over?SHELL_ACCENT_HOT:SHELL_ACCENT),SHELL_ARGB(255,SHELL_ACCENT_EDGE));
        shell_play_icon(dc,1220,y+20,6,RGB(255,255,255));}
}
static void ui_paint_servers(HDC dc){
    wchar_t info[200];LONG online=0,remote=0,count=browserCount;
    for(LONG i=0;i<count;++i){if(browserEntries[i].state==BROWSER_ONLINE&&!browserEntries[i].local)++online;if(!browserEntries[i].local)++remote;}
    int shown=browser_view(),filters=browser_filters(),sort=browser_sort();
    if(browserBusy)wcscpy(info,tr(browserQuickPending?L"Finding the best server...":L"Looking for servers..."));
    else if(browserQuickNote[0])wcsncpy(info,tr(browserQuickNote),199),info[199]=0;
    else if(!online)swprintf(info,200,tr(L"No public servers answered \x00B7 last checked at %02d:%02d"),browserFinishedTime.wHour,browserFinishedTime.wMinute);
    else if(filters)swprintf(info,200,tr(L"%d shown \x00B7 %ld online \x00B7 last checked at %02d:%02d"),shown,online,browserFinishedTime.wHour,browserFinishedTime.wMinute);
    else swprintf(info,200,tr(L"%ld online \x00B7 Quick play picks the best one for you"),online);
    ui_page_head(dc,L"SERVERS",info);
    int x=UI_R;
    {int w=ui_button_width(dc,L"Refresh");x-=w;ui_button(dc,L"Refresh",x,46,w,36,0,H_COMMAND,123,!browserBusy);x-=10;}
    {int w=ui_button_width(dc,L"Quick play");x-=w;ui_button(dc,L"Quick play",x,46,w,36,1,H_COMMAND,128,1);x-=10;}
    /* filter chips, filled while on, and Clear */
    int cx=256;
    for(unsigned c=0;c<sizeof(uiBrowserChips)/sizeof(uiBrowserChips[0]);++c){
        int on=(filters&uiBrowserChips[c].bit)!=0,w=ui_width(dc,uiBrowserChips[c].label,F_CHIP,1.7f)+(on?36:22),hot=ui_hit(cx,126,w,24,H_CHIP,uiBrowserChips[c].bit);
        shell_round(dc,(float)cx,126,(float)w,24,24,SHELL_ARGB(255,on?(hot?SHELL_ACCENT_HOT:SHELL_ACCENT):hot?RGB(30,34,43):RGB(22,25,32)),SHELL_ARGB(255,on?(hot?SHELL_ACCENT_HOT:SHELL_ACCENT):hot?RGB(26,30,38):RGB(19,22,28)),
                    SHELL_ARGB(255,on?SHELL_ACCENT_EDGE:hot?SHELL_FIELD_HOT:RGB(56,64,77)));
        if(on){ui_check(dc,cx+10,132,11,RGB(255,255,255));ui_text(dc,uiBrowserChips[c].label,cx+22,126,w-20,24,F_CHIP,RGB(255,255,255),DT_SINGLELINE|DT_VCENTER|DT_CENTER,1.7f);}
        else ui_text(dc,uiBrowserChips[c].label,cx,126,w+2,24,F_CHIP,SHELL_MUTED,DT_SINGLELINE|DT_VCENTER|DT_CENTER,1.7f);
        cx+=w+8;
    }
    if(filters){int hot=ui_hit(cx+4,126,60,24,H_CLEARF,0);ui_text(dc,L"Clear",cx+6,126,60,24,F_SMALL,hot?SHELL_ACCENT_HOT:SHELL_STEEL,UI_LINE1,0);}
    account_paint_lfs(dc); /* 0.37.0 looking for a squad */
    /* column header */
    shell_fill(dc,256,160,988,1,UI_LINE);
    for(unsigned c=0;c<sizeof(uiColumns)/sizeof(uiColumns[0]);++c){
        int active=sort==uiColumns[c].sort||sort==-uiColumns[c].sort,hot=ui_hit(uiColumns[c].x-4,168,uiColumns[c].w,28,H_SORT,uiColumns[c].sort);
        ui_text(dc,uiColumns[c].label,uiColumns[c].x,168,uiColumns[c].w,28,F_TAG,active?SHELL_TEXT:hot?SHELL_SUBTLE:UI_DIM,UI_LINE1,2.0f);
        if(active){int lw=ui_width(dc,uiColumns[c].label,F_TAG,2.0f);ui_sort_arrow(dc,uiColumns[c].x+lw+6,179,sort<0,SHELL_ACCENT_HOT);}
    }
    shell_fill(dc,256,200,988,1,RGB(31,38,50));
    int visibleRemote=0;for(int v=0;v<shown;++v)if(!browserEntries[browserView[v]].local)++visibleRemote;
    if(browserScroll>shown-UI_SERVER_ROWS)browserScroll=shown-UI_SERVER_ROWS>0?shown-UI_SERVER_ROWS:0;
    int row=0;
    for(int v=browserScroll;v<shown&&row<UI_SERVER_ROWS;++v,++row)ui_server_row(dc,browserView[v],UI_ROW_TOP+row*UI_ROW_H);
    if(browserBusy&&!online){
        /* skeleton rows while the first answers come in */
        for(int k=row;k<row+5&&k<UI_SERVER_ROWS;++k){int y=UI_ROW_TOP+k*UI_ROW_H;BYTE a=(BYTE)(110-(k-row)*18);
            shell_round(dc,264,(float)y+4,52,32,4,SHELL_ARGB(a,RGB(36,43,56)),SHELL_ARGB(a,RGB(36,43,56)),0);
            shell_round(dc,324,(float)y+8,220,10,5,SHELL_ARGB(a,RGB(40,48,62)),SHELL_ARGB(a,RGB(40,48,62)),0);
            shell_round(dc,324,(float)y+25,130,7,4,SHELL_ARGB(a,RGB(32,39,51)),SHELL_ARGB(a,RGB(32,39,51)),0);
            shell_round(dc,652,(float)y+16,90,9,5,SHELL_ARGB(a,RGB(36,43,56)),SHELL_ARGB(a,RGB(36,43,56)),0);
            shell_round(dc,792,(float)y+16,110,9,5,SHELL_ARGB(a,RGB(36,43,56)),SHELL_ARGB(a,RGB(36,43,56)),0);
            shell_round(dc,962,(float)y+16,60,9,5,SHELL_ARGB(a,RGB(36,43,56)),SHELL_ARGB(a,RGB(36,43,56)),0);
            shell_round(dc,1078,(float)y+16,60,9,5,SHELL_ARGB(a,RGB(36,43,56)),SHELL_ARGB(a,RGB(36,43,56)),0);}
    }else if(remote>0&&visibleRemote==0&&filters){
        int ey=UI_ROW_TOP+row*UI_ROW_H+20;
        ui_text(dc,L"NO SERVERS MATCH THESE FILTERS",256,ey,640,26,F_CARD,SHELL_TEXT,UI_LINE1,1.0f);
        ui_text(dc,L"Turn a filter off to see more servers, or use Quick play to join the best one.",256,ey+30,700,22,F_BODY14,SHELL_MUTED,UI_LINE1,0);
        int w=ui_button_width(dc,L"Clear filters");ui_button(dc,L"Clear filters",256,ey+66,w,36,0,H_CLEARF,0,1);
    }else if(!browserBusy&&!online){
        /* nobody answered: say so plainly and offer the two ways to play anyway */
        int ey=UI_ROW_TOP+row*UI_ROW_H+20;
        shell_round(dc,256,(float)ey,988,150,8,SHELL_ARGB(200,SHELL_CARD),SHELL_ARGB(200,SHELL_CARD),SHELL_ARGB(255,UI_LINE));
        ui_text(dc,L"NO PUBLIC SERVERS ANSWERED",280,ey+22,640,26,F_CARD,SHELL_TEXT,UI_LINE1,1.0f);
        ui_text(dc,browserMasterState==2?L"The public server list did not answer. Try again in a moment, host your own server, or practice offline.":
            L"Nobody is hosting a public server right now. Host one for your friends, or warm up offline against bots.",280,ey+52,940,22,F_BODY14,SHELL_MUTED,UI_LINE1,0);
        int bx=280,w=ui_button_width(dc,L"Host a server");ui_button(dc,L"Host a server",bx,ey+92,w,36,1,H_COMMAND,116,1);bx+=w+10;
        w=ui_button_width(dc,L"Practice offline");ui_button(dc,L"Practice offline",bx,ey+92,w,36,0,H_COMMAND,126,!game_missing());bx+=w+10;
        w=ui_button_width(dc,L"Try again");ui_button(dc,L"Try again",bx,ey+92,w,36,2,H_COMMAND,123,1);
    }
    if(shown>UI_SERVER_ROWS){
        int track=UI_SERVER_ROWS*UI_ROW_H-4,thumb=track*UI_SERVER_ROWS/shown,y=UI_ROW_TOP+(track-thumb)*browserScroll/(shown-UI_SERVER_ROWS);
        shell_round(dc,1252,UI_ROW_TOP,4,(float)track,4,SHELL_ARGB(255,RGB(30,34,42)),SHELL_ARGB(255,RGB(30,34,42)),0);
        shell_round(dc,1252,(float)y,4,(float)thumb,4,SHELL_ARGB(255,SHELL_FIELD_HOT),SHELL_ARGB(255,SHELL_FIELD_HOT),0);
    }
}
/* ---- News page: the full notes of a release, in sections, scrolled with the wheel or the keys ---- */
static int uiNewsShown,uiNewsScroll,uiNewsHeight;
#define UI_NEWS_TOP 276
#define UI_NEWS_BOTTOM 762
/* Measures (and with draw=1 paints) the release body; returns its height in design pixels. */
static int ui_news_body(HDC dc,const wchar_t *body,int top,int draw){
    int y=top;const wchar_t *line=body;
    XFORM t;shell_transform(dc,&t);HFONT f=shell_scaled_font(ui_font(F_DESC),t.eM11);
    while(*line){
        const wchar_t *end=wcschr(line,L'\n');size_t length=end?(size_t)(end-line):wcslen(line);
        wchar_t text[800];if(length>799)length=799;wcsncpy(text,line,length);text[length]=0;
        line=end?end+1:line+wcslen(line);
        int indent=0;while(text[indent]==L' ')++indent;
        wchar_t clean[800];int c=0;for(wchar_t *q=text+indent;*q;++q){if(q[0]==L'*'&&q[1]==L'*'){++q;continue;}if(q[0]==L'`')continue;clean[c++]=*q;}clean[c]=0;
        while(c&&(clean[c-1]==L' '||clean[c-1]==L'\r'))clean[--c]=0;
        if(!clean[0]){y+=6;continue;}
        if(!wcsncmp(text,L"**TRUECOMBAT",12)||!wcsncmp(text,L"**Patch Notes",13)||!wcsncmp(text,L"**Full TC",9)||!wcsncmp(text,L"**Packaged",10))continue;
        int heading=(text[indent]==L'*'&&text[indent+1]==L'*'&&c>0&&text[length-1-(text[length-1]==L'\r')]==L'*')||clean[0]==L'#';
        if(heading){
            const wchar_t *h=clean;while(*h==L'#'||*h==L' ')++h;
            wchar_t caps[200];ui_upper(caps,h,200);
            y+=y>top?14:2;
            if(draw&&y+20>UI_NEWS_TOP-30&&y<UI_NEWS_BOTTOM){shell_fill(dc,275,y+3,3,14,SHELL_ACCENT_HOT);ui_text(dc,caps,286,y,560,20,F_SEC,SHELL_TEXT,UI_LINE1,2.0f);}
            y+=28;continue;
        }
        int bullet=(clean[0]==L'-'||clean[0]==L'*'||clean[0]==0x2022)&&clean[1]==L' ';const wchar_t *text_body=bullet?clean+2:clean;
        int left=275+(bullet?20:0)+(indent>=2?18:0),width=846-left;
        RECT measure={0,0,(LONG)(width*t.eM11),0};
        {XFORM identity={1,0,0,1,0,0};SetWorldTransform(dc,&identity);HGDIOBJ old=SelectObject(dc,f);
         DrawTextW(dc,text_body,-1,&measure,DT_WORDBREAK|DT_CALCRECT|DT_NOPREFIX);SelectObject(dc,old);SetWorldTransform(dc,&t);}
        int h=(int)(measure.bottom/t.eM22)+1;
        if(draw&&y+h>UI_NEWS_TOP-30&&y<UI_NEWS_BOTTOM){
            if(bullet)shell_round(dc,(float)left-14,(float)y+7,5,5,5,SHELL_ARGB(255,indent>=2?SHELL_STEEL:SHELL_ACCENT_HOT),SHELL_ARGB(255,indent>=2?SHELL_STEEL:SHELL_ACCENT_HOT),0);
            ui_text(dc,text_body,left,y,width,h,F_DESC,SHELL_SUBTLE,DT_WORDBREAK,0);
        }
        y+=h+6;
    }
    return y-top;
}
static void ui_news_scroll(int delta){
    int room=UI_NEWS_BOTTOM-UI_NEWS_TOP,limit=uiNewsHeight>room?uiNewsHeight-room:0;
    uiNewsScroll+=delta;if(uiNewsScroll>limit)uiNewsScroll=limit;if(uiNewsScroll<0)uiNewsScroll=0;
}
static void ui_paint_news(HDC dc){
    ui_page_head(dc,L"NEWS",L"Patch notes for the latest release and the ones before it.");
    shell_fill(dc,256,152,988,1,UI_LINE);
    LONG state=InterlockedCompareExchange(&newsState,0,0);
    if(uiNewsShown>=newsCount)uiNewsShown=0;
    if(state!=2){
        /* 0.37.1: nothing to list yet, so one empty-state card instead of two empty columns */
        const wchar_t *message=state==1||state==0?L"Loading the latest patch notes...":state==4?L"News appears here once updates are set up for this copy.":L"The patch notes could not be loaded. Check your internet connection.";
        shell_round(dc,256,176,988,96,8,SHELL_ARGB(255,SHELL_CARD),SHELL_ARGB(255,SHELL_CARD),SHELL_ARGB(255,UI_LINE));
        ui_text(dc,L"LATEST RELEASE",280,200,300,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
        ui_text(dc,message,280,228,940,24,F_BODY14,SHELL_MUTED,UI_LINE1,0);return;
    }
    shell_round(dc,256,176,620,598,8,SHELL_ARGB(255,SHELL_CARD),SHELL_ARGB(255,SHELL_CARD),SHELL_ARGB(255,UI_LINE));
    shell_round(dc,892,176,352,598,8,SHELL_ARGB(255,SHELL_CARD),SHELL_ARGB(255,SHELL_CARD),SHELL_ARGB(255,UI_LINE));
    ui_text(dc,uiNewsShown?L"RELEASE NOTES":L"LATEST RELEASE",275,190,300,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
    ui_text(dc,L"EARLIER UPDATES",911,190,300,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
    NewsItem *n=&newsItems[uiNewsShown];
    {wchar_t caps[130];ui_upper(caps,n->title,130);ui_text(dc,caps,275,214,420,30,F_WHO,SHELL_TEXT,UI_LINE1,1.0f);}
    ui_text(dc,n->date,275,244,300,18,F_MONO12,SHELL_MUTED,UI_LINE1,0);
    if(n->url[0]){int w=ui_button_width(dc,L"Open on GitHub");ui_button(dc,L"Open on GitHub",857-w,218,w,36,0,H_ARTICLE,uiNewsShown,1);}
    shell_fill(dc,275,UI_NEWS_TOP-8,582,1,RGB(31,38,50));
    /* body, clipped to the card and shifted by the scroll position */
    uiNewsHeight=ui_news_body(dc,n->body,0,0);ui_news_scroll(0);
    {XFORM t;shell_transform(dc,&t);
     HRGN clip=CreateRectRgn((int)(262*t.eM11+t.eDx),(int)(UI_NEWS_TOP*t.eM22+t.eDy),(int)(870*t.eM11+t.eDx),(int)(UI_NEWS_BOTTOM*t.eM22+t.eDy));
     ExtSelectClipRgn(dc,clip,RGN_AND);
     ui_news_body(dc,n->body,UI_NEWS_TOP-uiNewsScroll,1);
     SelectClipRgn(dc,NULL);DeleteObject(clip);}
    int room=UI_NEWS_BOTTOM-UI_NEWS_TOP;
    if(uiNewsHeight>room){
        int track=room,thumb=track*room/uiNewsHeight,y=UI_NEWS_TOP+(track-thumb)*uiNewsScroll/(uiNewsHeight-room);
        shell_round(dc,864,UI_NEWS_TOP,4,(float)track,4,SHELL_ARGB(255,RGB(30,34,42)),SHELL_ARGB(255,RGB(30,34,42)),0);
        shell_round(dc,864,(float)y,4,(float)thumb,4,SHELL_ARGB(255,SHELL_FIELD_HOT),SHELL_ARGB(255,SHELL_FIELD_HOT),0);
    }
    /* every release in the list; the one on the left is marked */
    for(LONG i=0;i<newsCount&&i<6;++i){
        int x=904,yy=222+(int)i*90,hot=ui_hit(x,yy,328,80,H_LINK,(int)i),on=i==uiNewsShown;
        shell_round(dc,(float)x,(float)yy,328,80,8,SHELL_ARGB(255,hot||on?RGB(34,41,54):RGB(26,32,43)),SHELL_ARGB(255,hot||on?RGB(34,41,54):RGB(26,32,43)),SHELL_ARGB(255,on?SHELL_ACCENT:hot?SHELL_FIELD_HOT:UI_LINE));
        wchar_t caps[130];ui_upper(caps,newsItems[i].title,130);
        ui_text(dc,caps,x+14,yy+10,300,24,F_CARD,SHELL_TEXT,UI_LINE1,0.85f);
        ui_text(dc,newsItems[i].date,x+14,yy+34,200,18,F_MONO11,SHELL_MUTED,UI_LINE1,0);
        ui_text(dc,on?L"Showing on the left":L"Read the notes  \x203A",x+14,yy+53,250,18,F_SMALL,on?SHELL_MUTED:hot?SHELL_ACCENT_HOT:SHELL_STEEL,UI_LINE1,0);
    }
}

/* ---- Settings page ---- */
enum {O_REOPEN,O_STARTUP,O_ANIM,O_AUTOGAME,O_AUTOLAUNCHER,O_DISCORD,O_NOTIFY,O_CRASH,O_VSYNC,O_TRAY,O_HDTEX,O_PLAYING,O_TELEMETRY};
static int telemetry_choice(void);static int telemetry_card_visible(void);static void telemetry_set(int on);static void telemetry_start(void);static void open_telemetry_view(HWND parent);static int telemetryForcedCard;
enum {R_TOGGLE,R_COMBO,R_SWATCH,R_BUTTON,R_EDIT,R_INFO};
typedef struct {const wchar_t *title,*text;int kind,arg;const wchar_t *label;} UiRow;
typedef struct {const wchar_t *title;int column,first,count;} UiPanel;   /* column 0 left, 1 right; rows index uiRows */
static int uiSettingsTab;       /* 0 Launcher, 1 Graphics, 2 Controls, 3 Updates, 4 Privacy, 5 Storage */
static const wchar_t *const uiSettingsTabs[6]={L"LAUNCHER",L"GRAPHICS",L"CONTROLS",L"UPDATES",L"PRIVACY",L"STORAGE"};
static const UiRow uiRows[]={
    /* 0 Launcher: when the game starts */
    {L"Launcher window",L"What the launcher does while you play",R_COMBO,146,NULL},
    {L"Come back after the match",L"Reopen the launcher when the game closes",R_TOGGLE,O_REOPEN,NULL},
    {L"Open on",L"The page shown at start-up",R_COMBO,145,NULL},
    {L"Start with Windows",L"Quietly, in the tray, so updates are ready",R_TOGGLE,O_STARTUP,NULL},
    /* 4 appearance */
    {L"Accent colour",L"Buttons, highlights and the active page",R_SWATCH,0,NULL},
    {L"Background",L"The artwork behind the Play page",R_COMBO,147,NULL},
    {L"Interface size",L"Scales text and buttons",R_COMBO,148,NULL},
    {L"Animations",L"Turn off for a still, faster interface",R_TOGGLE,O_ANIM,NULL},
    /* 8 updates */
    {L"Update the game automatically",L"Download in the background, install when you choose",R_TOGGLE,O_AUTOGAME,NULL},
    {L"Update the launcher automatically",L"Small, separate from the game",R_TOGGLE,O_AUTOLAUNCHER,NULL},
    {L"Download speed limit",L"Keeps your connection free in game",R_COMBO,149,NULL},
    /* 11 privacy and notifications */
    {L"Discord Rich Presence",L"Show friends your server and map",R_TOGGLE,O_DISCORD,NULL},
    {L"Tell me when an update is ready",L"A Windows notification, never a pop-up",R_TOGGLE,O_NOTIFY,NULL},
    {L"Send crash reports",L"Only with your approval. Reports stay on this PC.",R_TOGGLE,O_CRASH,NULL},
    /* 14 Graphics: display */
    {L"Quality preset",L"Low, High, Ultra or your own Custom mix",R_COMBO,107,NULL},
    {L"Resolution",L"The size the game renders at",R_COMBO,108,NULL},
    {L"Display mode",L"Windowed, borderless or fullscreen",R_COMBO,109,NULL},
    {L"Vertical sync",L"Stops tearing, adds a little input delay",R_TOGGLE,O_VSYNC,NULL},
    /* 18 graphics: advanced */
    {L"Every graphics option",L"Textures, shadows, anti-aliasing and DX12 effects",R_BUTTON,113,L"Open"},
    {L"Graphics report",L"Your graphics card, driver and DirectX 12 support",R_BUTTON,115,L"View"},
    {L"Launch options",L"Extra console commands for every start",R_EDIT,151,NULL},
    {L"Save for the next launch",L"Preset, resolution and display mode",R_BUTTON,114,L"Save"},
    /* 22 Controls */
    {L"Key bindings",L"Movement, weapons, chat and voting",R_BUTTON,125,L"Change keys"},
    {L"Player name",L"Shown to other players in the game",R_EDIT,102,NULL},
    {L"Name colours",L"Colour each letter of your name",R_BUTTON,171,L"Colours"},
    {L"Profile and replays",L"Back up your identity and watch recorded matches",R_BUTTON,129,L"Open"},
    /* 25 Updates */
    {L"Game",L"",R_BUTTON,117,NULL},
    {L"Installed version",L"Go back to an older release, or to the latest",R_BUTTON,119,L"Versions"},
    {L"Patch notes",L"What changed in the latest release",R_BUTTON,118,L"Read"},
    {L"Verify and repair",L"Replaces missing or damaged game files",R_BUTTON,152,L"Verify"},
    {L"Launcher",L"",R_BUTTON,127,NULL},
    /* 30 Privacy */
    {L"Player identity",L"A key file on this PC. No account, no e-mail address.",R_BUTTON,158,L"Back up"},
    {L"Usage tracking",L"None. The launcher and the website do not track you.",R_INFO,0,L"Off"},
    /* 32 Storage */
    {L"Game folder",L"",R_BUTTON,9101,L"Open folder"},
    {L"Move the game",L"To another folder or drive. Takes a few minutes.",R_BUTTON,153,L"Move"},
    {L"Disk use",L"",R_INFO,1,NULL},
    {L"Clear caches",L"Shader cache and leftovers. Kept under a size limit.",R_BUTTON,161,L"Clear"},
    {L"Screenshots, replays and settings",L"Your profile folder inside the game folder",R_BUTTON,9102,L"Open folder"},
    {L"Server hosting",L"Your own server's name, map and favorites",R_BUTTON,116,L"Open"},
    /* 38 Launcher: language */
    {L"Language",L"Launcher text in your language",R_COMBO,154,NULL},
    /* 40 Launcher: window (2.5.0) */
    {L"Keep in the tray",L"Minimize and close keep the launcher running in the tray",R_TOGGLE,O_TRAY,NULL},
    /* 41 Updates: game content (0.37.1) */
    {L"HD textures",L"Sharper textures up close. A larger download.",R_TOGGLE,O_HDTEX,NULL},
    /* 42 Privacy: players online (0.38.0) */
    {L"Tell me when people are playing",L"A Windows notification, at most once in six hours",R_TOGGLE,O_PLAYING,NULL},
    /* 43-45 Privacy: your data (2.6.0) */
    {L"Player identity",L"A key file on this PC. No account, no e-mail address.",R_BUTTON,158,L"Back up"},
    {L"Share crash and hardware data",L"Anonymous. Helps us fix crashes and tune performance.",R_TOGGLE,O_TELEMETRY,NULL},
    {L"What is shared",L"The exact report this PC would send next",R_BUTTON,172,L"View"},
};
static const UiPanel uiPanels[]={
    {L"WHEN THE GAME STARTS",0,0,4},{L"APPEARANCE",1,4,4},{L"UPDATES",0,8,3},{L"LANGUAGE AND WINDOW",1,39,2},
    {L"DISPLAY",0,14,4},{L"ADVANCED",1,18,4},
    {L"KEYS",0,22,1},{L"PLAYER",1,23,3},
    {L"GAME",0,26,4},{L"LAUNCHER",1,30,1},{L"AUTOMATIC UPDATES",1,8,3},{L"GAME CONTENT",0,41,1},
    {L"YOUR DATA",0,43,3},{L"PRIVACY AND NOTIFICATIONS",1,11,3},{L"PLAYERS ONLINE",0,42,1},
    {L"FILES",0,33,5},{L"HOSTING",1,38,1},
};
static const struct {int first,count;} uiTabPanels[6]={{0,4},{4,2},{6,2},{8,4},{12,3},{15,2}};
static int ui_option_get(int option){
    switch(option){
    case O_REOPEN:return options.reopen;case O_STARTUP:return options_startup();case O_ANIM:return options.animations;
    case O_AUTOGAME:return options.autoGame;case O_AUTOLAUNCHER:return options.autoLauncher;
    case O_DISCORD:return GetPrivateProfileIntW(L"Discord",L"Enabled",1,ini)!=0;
    case O_NOTIFY:return options.notify;case O_CRASH:return options.crash;
    case O_TRAY:return GetPrivateProfileIntW(L"Launcher",L"TrayOnClose",0,ini)!=0;
    case O_HDTEX:return update_hd_on();
    case O_PLAYING:return GetPrivateProfileIntW(L"Launcher",L"PlayingAlert",1,ini)!=0;
    case O_TELEMETRY:return telemetry_choice()==1;
    default:return vsync_check&&SendMessageW(vsync_check,BM_GETCHECK,0,0)==BST_CHECKED;
    }
}
/* Where a row's control sits (design coordinates): rows are 62 apart inside a panel. */
static void ui_panel_rect(int tab,int index,int *x,int *y,int *w,int *h){
    const UiPanel *p=&uiPanels[uiTabPanels[tab].first+index];
    int top=176;
    for(int k=0;k<index;++k){const UiPanel *q=&uiPanels[uiTabPanels[tab].first+k];if(q->column==p->column)top+=48+62*q->count+16;}
    *x=p->column?758:256;*y=top;*w=486;*h=48+62*p->count;
}
static int ui_row_position(int tab,int row,int *right,int *center){
    for(int k=0;k<uiTabPanels[tab].count;++k){
        const UiPanel *p=&uiPanels[uiTabPanels[tab].first+k];
        if(row>=p->first&&row<p->first+p->count){int x,y,w,h;ui_panel_rect(tab,k,&x,&y,&w,&h);*right=x+w-19;*center=y+72+62*(row-p->first);return 1;}
    }
    return 0;
}
/* Control id -> the settings tab and row that hosts it (for placing the real dropdowns and the name field). */
/* A control can live on more than one Settings tab (the speed limit is on Launcher and Updates). */
static int ui_control_place_in(int id,int t,int *x,int *y,int *w,int *h){
    for(int k=0;k<uiTabPanels[t].count;++k){
        const UiPanel *p=&uiPanels[uiTabPanels[t].first+k];
        for(int r=p->first;r<p->first+p->count;++r)if((uiRows[r].kind==R_COMBO||uiRows[r].kind==R_EDIT)&&uiRows[r].arg==id){
            int right,center;ui_row_position(t,r,&right,&center);*w=190;*h=32;*x=right-190;*y=center-16;return 1;}
    }
    return 0;
}
static int ui_control_place(int id,int *tab,int *x,int *y,int *w,int *h){
    for(int t=0;t<6;++t)if(ui_control_place_in(id,t,x,y,w,h)){*tab=t;return 1;}
    return 0;
}
/* Update state in a few words, and the installed game version, shared by the rail and Settings > Updates. */
static const wchar_t *ui_update_words(LONG state){
    return state==UPDATE_READY?L"Ready to install":state==UPDATE_DOWNLOADING?L"Downloading...":state==UPDATE_VERIFYING?L"Verifying files...":state==UPDATE_AVAILABLE?(updateCurrent[0]?L"Update available":L"Ready to download"):
           state==UPDATE_CHECKING?L"Checking for updates...":state==UPDATE_FAILED?L"Update problem":state==UPDATE_CURRENT?L"Up to date":L"Updates off";
}
static void ui_game_version(wchar_t game[64]){
    if(updateCurrent[0]){wcsncpy(game,updateCurrent,63);game[63]=0;wchar_t *dash=wcschr(game,L'-');if(dash)*dash=0;}else wcscpy(game,updateFeed[0]?L"Not installed":L"Dev build");
}
/* ---- Settings > Storage: what the game takes on disk, and the caches that can go ---- */
static LONG64 uiDiskGame,uiDiskReplays,uiDiskCache;static int uiDiskKnown;
static LONG64 ui_folder_size(const wchar_t *folder,int depth){
    if(depth>12)return 0;
    wchar_t pattern[2600];swprintf(pattern,2600,L"%ls\\*",folder);WIN32_FIND_DATAW item;HANDLE find=FindFirstFileW(pattern,&item);LONG64 total=0;
    if(find==INVALID_HANDLE_VALUE)return 0;
    do{if(!wcscmp(item.cFileName,L".")||!wcscmp(item.cFileName,L".."))continue;
        if(item.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)continue;
        if(item.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY){wchar_t child[2600];swprintf(child,2600,L"%ls\\%ls",folder,item.cFileName);total+=ui_folder_size(child,depth+1);}
        else total+=((LONG64)item.nFileSizeHigh<<32)|item.nFileSizeLow;
    }while(FindNextFileW(find,&item));
    FindClose(find);return total;
}
static const wchar_t *const uiCacheFolders[]={L"profile\\tcetest\\dx12cache",L"profile\\tcetest\\navcache",L"updates\\staging"};
static void ui_disk_use_refresh(void){
    wchar_t path[2600];uiDiskGame=ui_folder_size(root,0);
    swprintf(path,2600,L"%ls\\profile\\tcetest\\demos",root);uiDiskReplays=ui_folder_size(path,0);
    uiDiskCache=0;for(unsigned i=0;i<sizeof(uiCacheFolders)/sizeof(uiCacheFolders[0]);++i){swprintf(path,2600,L"%ls\\%ls",root,uiCacheFolders[i]);uiDiskCache+=ui_folder_size(path,0);}
    swprintf(path,2600,L"%ls\\updates\\package.zip",root);WIN32_FILE_ATTRIBUTE_DATA info;
    if(GetFileAttributesExW(path,GetFileExInfoStandard,&info))uiDiskCache+=((LONG64)info.nFileSizeHigh<<32)|info.nFileSizeLow;
    uiDiskKnown=1;
}
static void ui_size_text(LONG64 bytes,wchar_t *out,int capacity){
    if(bytes>=1073741824LL)swprintf(out,capacity,L"%.1f GB",bytes/1073741824.0);else swprintf(out,capacity,L"%.0f MB",bytes/1048576.0);
}
static void update_remove_tree(const wchar_t *folder);
static void ui_clear_caches(HWND window){
    LONG state=update_visible_state();
    if(game_running()||state==UPDATE_DOWNLOADING||state==UPDATE_VERIFYING||state==UPDATE_READY){
        MessageBoxW(window,tr(L"Close the game and wait for any download to finish, then clear the caches."),TITLE,MB_OK|MB_ICONINFORMATION);return;}
    wchar_t size[32],question[300];ui_size_text(uiDiskCache,size,32);
    swprintf(question,300,tr(L"Clear %ls of caches? The shader cache rebuilds the next time you play, so the first match may load a little slower."),size);
    if(MessageBoxW(window,question,TITLE,MB_OKCANCEL|MB_ICONQUESTION)!=IDOK)return;
    wchar_t path[2600];
    for(unsigned i=0;i<sizeof(uiCacheFolders)/sizeof(uiCacheFolders[0]);++i){swprintf(path,2600,L"%ls\\%ls",root,uiCacheFolders[i]);update_remove_tree(path);}
    swprintf(path,2600,L"%ls\\updates\\package.zip",root);DeleteFileW(path);
    ui_disk_use_refresh();ui_saved();shell_refresh(window);
}
static void ui_paint_settings(HDC dc,HWND window){
    {static const wchar_t *const heads[6]={L"How the launcher behaves, looks and updates. Game graphics live under Graphics.",
        L"Quality, resolution and display mode for the next launch.",L"Your keys, your player name and its colours.",
        L"Game and launcher versions, downloads and HD textures.",L"Your identity, notifications and what stays on this PC.",
        L"Where the game lives and what it takes on disk."};
     ui_page_head(dc,L"SETTINGS",heads[uiSettingsTab>=0&&uiSettingsTab<6?uiSettingsTab:0]);}
    int tx=256;
    for(int i=0;i<6;++i){
        int w=ui_width(dc,uiSettingsTabs[i],F_NAV,1.9f),on=i==uiSettingsTab,hot=ui_hit(tx-6,124,w+12,34,H_TAB,i);   /* 0.37.1: 6 px more air under the subtitle */
        ui_text(dc,uiSettingsTabs[i],tx,125,w+4,26,F_NAV,on?RGB(255,255,255):hot?SHELL_TEXT:SHELL_MUTED,DT_SINGLELINE|DT_VCENTER,1.9f);
        if(on)shell_fill(dc,tx,156,w-2,2,SHELL_ACCENT_HOT);
        tx+=w+26;
    }
    shell_fill(dc,256,158,988,1,UI_LINE);
    for(int k=0;k<uiTabPanels[uiSettingsTab].count;++k){
        const UiPanel *p=&uiPanels[uiTabPanels[uiSettingsTab].first+k];int x,y,w,h;ui_panel_rect(uiSettingsTab,k,&x,&y,&w,&h);
        shell_round(dc,(float)x,(float)y,(float)w,(float)h,8,SHELL_ARGB(255,SHELL_CARD),SHELL_ARGB(255,SHELL_CARD),SHELL_ARGB(255,UI_LINE));
        ui_text(dc,p->title,x+19,y+18,w-38,20,F_SEC,SHELL_ACCENT_HOT,UI_LINE1,2.6f);
        for(int r=0;r<p->count;++r){
            const UiRow *row=&uiRows[p->first+r];int center=y+72+62*r,right=x+w-19,controlLeft=right;
            if(r)shell_fill(dc,x+19,y+42+62*r,w-38,1,RGB(31,38,50));
            wchar_t text[300];wcsncpy(text,row->text,299);text[299]=0;wchar_t label[64]=L"";int enabled=1;
            if(row->label)wcscpy(label,row->label);
            if(row->kind==R_BUTTON&&(row->arg==117||row->arg==127)){
                /* live rows: the state in words, the action on the button */
                HWND source=GetDlgItem(window,row->arg);if(source){GetWindowTextW(source,label,64);enabled=IsWindowEnabled(source);}
                if(row->arg==117){
                    LONG state=update_visible_state();wchar_t game[64];ui_game_version(game);
                    if(state==UPDATE_OFF)swprintf(text,300,tr(L"%ls \x00B7 updates are not set up for this copy"),tr(game));
                    /* 2.6.2: a failure says why (2.6.1 only said "Update check failed") */
                    else if(state==UPDATE_FAILED&&updateError[0]){wcsncpy(text,updateError,299);text[299]=0;}
                    else swprintf(text,300,tr(L"Version %ls \x00B7 %ls"),tr(game),tr(ui_update_words(state)));
                    if(!wcscmp(label,L"Updates off"))wcscpy(label,L"Not set up");
                }else{
                    swprintf(text,300,tr(L"Version %ls"),PLATINUM_LAUNCHER_VERSION);
                    if(!wcscmp(label,L"Launcher update"))wcscpy(label,L"Check now");
                    else if(!wcscmp(label,L"Launcher up to date"))wcscpy(label,L"Up to date");
                }
            }
            if(row->kind==R_BUTTON&&row->arg==9101)wcsncpy(text,root,299);
            if(row->kind==R_INFO&&row->arg==1){
                if(!uiDiskKnown)ui_disk_use_refresh();
                wchar_t a[32],b[32],c[32];ui_size_text(uiDiskGame,a,32);ui_size_text(uiDiskReplays,b,32);ui_size_text(uiDiskCache,c,32);
                wcscpy(label,a);LONG64 replayLimit=update_budget_limit(UPDATE_BUDGET_REPLAYS);wchar_t d[32],e[32];ui_size_text(update_budget_limit(UPDATE_BUDGET_CACHE),e,32);
                if(replayLimit>0){ui_size_text(replayLimit,d,32);swprintf(text,300,tr(L"Replays %ls of %ls \x00B7 caches %ls of %ls"),b,d,c,e);}
                else swprintf(text,300,tr(L"Replays %ls \x00B7 caches %ls of %ls"),b,c,e);}
            if(row->kind==R_TOGGLE&&row->arg==O_HDTEX){
                LONG state=update_visible_state();
                if(state==UPDATE_DOWNLOADING&&InterlockedCompareExchange(&updateHdOnly,0,0)){
                    LONG64 total=updateTotal,done=updateDone;int percent=total>0?(int)(100.0*(double)done/(double)total):0;if(percent>100)percent=100;
                    swprintf(text,300,tr(L"Downloading \x00B7 %d%% of %.1f GB"),percent,total/1073741824.0);}
                else if(updateHdBytes>0)swprintf(text,300,tr(L"Sharper textures up close \x00B7 %.1f GB"),updateHdBytes/1073741824.0);}
            if(row->kind==R_BUTTON&&row->arg==161)enabled=uiDiskCache>0;
            if(row->kind==R_BUTTON&&row->arg==152){enabled=update_repair_ready()&&!game_running();
                if(updateRepair){LONG state=update_visible_state();wcscpy(text,state==UPDATE_CHECKING?L"Checking every file against the release...":L"Repairing: see the PLAY button for progress");}
                else if(updateRepairNote[0])wcsncpy(text,updateRepairNote,299);}
            if(row->kind==R_BUTTON&&row->arg==153){LONG state=update_visible_state();
                enabled=!game_running()&&state!=UPDATE_DOWNLOADING&&state!=UPDATE_VERIFYING&&state!=UPDATE_READY&&updatePreview<0;}
            if(row->kind==R_BUTTON&&row->arg==114){HWND source=GetDlgItem(window,114);wchar_t state[64]=L"";if(source)GetWindowTextW(source,state,64);if(wcsstr(state,L"saved"))wcscpy(label,L"Saved");}
            if(row->kind==R_TOGGLE){int hot=ui_hit(x+8,center-28,w-16,56,H_TOGGLE,row->arg);ui_toggle(dc,right-40,center-11,ui_option_get(row->arg),hot);controlLeft=right-40;}
            else if(row->kind==R_SWATCH){
                controlLeft=right-(OPTION_ACCENTS*26+(OPTION_ACCENTS-1)*8);
                for(int i=0;i<OPTION_ACCENTS;++i){int sx=controlLeft+i*34,sy=center-13,hot=ui_hit(sx-3,sy-3,32,32,H_SWATCH,i);
                    shell_round(dc,(float)sx,(float)sy,26,26,6,SHELL_ARGB(255,optionAccents[i].base),SHELL_ARGB(255,optionAccents[i].base),0);
                    if(i==options.accent)shell_round(dc,(float)sx,(float)sy,26,26,6,0,0,SHELL_ARGB(255,RGB(255,255,255))),shell_round(dc,(float)sx+1,(float)sy+1,24,24,5,0,0,SHELL_ARGB(255,RGB(255,255,255)));
                    else if(hot)shell_round(dc,(float)sx,(float)sy,26,26,6,0,0,SHELL_ARGB(160,RGB(255,255,255)));}
            }
            else if(row->kind==R_BUTTON){int bw=ui_button_width(dc,label);if(bw<96)bw=96;controlLeft=right-bw;ui_button(dc,label,controlLeft,center-18,bw,36,row->arg==117&&enabled&&(update_visible_state()==UPDATE_AVAILABLE||update_visible_state()==UPDATE_READY),H_COMMAND,row->arg,enabled);}
            else if(row->kind==R_INFO){int lw=ui_width(dc,label,F_ROW,0);controlLeft=right-lw;ui_text(dc,label,controlLeft,center-12,lw+4,24,F_ROW,SHELL_OK,UI_LINE1,0);}
            else controlLeft=right-190;
            ui_text(dc,row->title,x+19,center-23,controlLeft-x-35,22,F_ROW,SHELL_TEXT,UI_LINE1,0);
            {wchar_t current[64]=L"";if(row->arg==171&&name_edit)GetWindowTextW(name_edit,current,64);
             if(row->arg==171&&nc_has_codes(current))nc_draw_name(dc,current,x+19,center-1,controlLeft-x-35,20,F_DESC,0,0,SHELL_TEXT);   /* your name in its colours */
             /* 2.6.2: an update problem gets two lines, so the reason is read in full */
             else if(row->kind==R_BUTTON&&row->arg==117&&update_visible_state()==UPDATE_FAILED&&updateError[0])ui_text(dc,text,x+19,center-3,controlLeft-x-35,36,F_DESC,SHELL_AMBER,DT_WORDBREAK|DT_END_ELLIPSIS,0);
             else ui_text(dc,text,x+19,center-1,controlLeft-x-35,20,F_DESC,SHELL_MUTED,UI_LINE1,0);}
        }
    }
    /* Graphics keeps its own Save button: everything else saves as it changes */
    const wchar_t *footer=uiSettingsTab==1?L"Graphics changes take effect when you select Save.":L"Changes save as you make them.";
    ui_text(dc,footer,256,745,500,22,F_DESC,UI_DIM,UI_LINE1,0);
    if(uiSavedTick&&GetTickCount()-uiSavedTick<2400){
        int at=256+ui_width(dc,footer,F_DESC,0)+14;
        ui_check(dc,at,750,12,SHELL_OK);ui_text(dc,L"Saved",at+18,745,120,22,F_DESC,SHELL_OK,UI_LINE1,0);
    }
    if(uiSettingsTab==0){int w=ui_button_width(dc,L"Restore launcher defaults");ui_button(dc,L"Restore launcher defaults",UI_R-w,738,w,36,0,H_COMMAND,150,1);}
}

/* ---- navigation rail: status and versions at the foot (the rest is in the cached backdrop) ---- */
static void ui_paint_rail(HDC dc){
    LONG state=update_visible_state();
    const wchar_t *label=ui_update_words(state);
    COLORREF dot=state==UPDATE_FAILED?SHELL_AMBER:state==UPDATE_CURRENT?SHELL_OK:state==UPDATE_OFF?UI_DIM:SHELL_ACCENT_HOT;
    /* the whole status block opens Settings > Updates */
    if(ui_hit(10,712,192,80,H_COMMAND,160))shell_round(dc,10,712,192,80,6,SHELL_ARGB(18,RGB(255,255,255)),SHELL_ARGB(18,RGB(255,255,255)),0);
    shell_round(dc,15,722,13,13,13,SHELL_ARGB(46,dot),SHELL_ARGB(46,dot),0);
    shell_round(dc,18,725,7,7,7,SHELL_ARGB(255,dot),SHELL_ARGB(255,dot),0);
    ui_text(dc,label,33,719,160,20,F_SMALL,UI_DIM,UI_LINE1,0);
    wchar_t game[64];ui_game_version(game);
    ui_text(dc,L"Game",18,742,80,20,F_SMALL,UI_DIM,UI_LINE1,0);
    ui_text(dc,game,80,742,114,20,F_MONO11,SHELL_MUTED,DT_SINGLELINE|DT_VCENTER|DT_RIGHT,0);
    ui_text(dc,L"Launcher",18,766,80,20,F_SMALL,UI_DIM,UI_LINE1,0);
    ui_text(dc,PLATINUM_LAUNCHER_VERSION,80,766,114,20,F_MONO11,SHELL_MUTED,DT_SINGLELINE|DT_VCENTER|DT_RIGHT,0);
}
/* ---- hover tips for painted controls (shown by platinum_tips.h) ---- */
static const wchar_t *tip_main(int id);
static const wchar_t *ui_tip(int kind,int arg){
    static wchar_t text[400];
    switch(kind){
    case H_HERO:return arg==1?L"Opens the trailer in your browser.":L"Every fix and feature of the latest release.";
    case H_DOT:return L"Show this story.";
    case H_CARD:return shellTab==1?L"Select to fill in the address. Double-click to join straight away.":L"Select to join this server by address. Double-click to join straight away.";
    case H_JOIN:return L"Join this server now.";
    case H_STAR:return arg>=0&&arg<browserCount&&browserEntries[arg].favorite?L"Remove from favorites.":L"Keep this server at the top of the list.";
    case H_NEWS:return arg>=0&&arg<3&&uiNews[arg].url[0]?L"Opens in your browser.":L"Opens the News page.";
    case H_WHO:return L"Your player name and graphics. Select to change them in Settings.";
    case H_SEG:return arg==0?L"PLAY joins the best public server: real players first, then a free slot, then the lowest ping.":
                     arg==1?L"PLAY joins the address you type or pick from your recent and saved servers.":
                     L"PLAY starts an offline match against bots on this PC. Nothing is sent online.";
    case H_PLAY:{int percent,state=ui_play_state(&percent);
        switch(state){
        case PB_RUNNING:return L"The game is running. Select to bring it to the front.";
        case PB_DOWNLOADING:return L"Downloading. You can keep using the launcher. To stop, use the arrow next to this button.";
        case PB_VERIFYING:return L"Checking the files before they are installed. This takes a moment.";
        case PB_RESTART:return L"The update is downloaded. The launcher restarts once to install it, then you can play.";
        case PB_UPDATE:return L"Downloads only the files that changed. Your settings and profile are kept.";
        case PB_INSTALL:case PB_FIND:return L"Downloads the latest release into this folder. Every file is verified as it arrives.";
        case PB_OFF:return L"This folder has no game files and no update source. Install the game with the official setup.";
        default:return tip_main(104);}}
    case H_ARROW:return L"More ways to start: Safe start, the game menu, practice, hosting, file repair and the game folder.";
    case H_TAB:return NULL;
    case H_TOGGLE:{static const int ids[]={140,0,143,141,142,144,0,0,110};
        if(arg==O_STARTUP)return L"Starts the launcher quietly in the tray when you sign in to Windows, so updates are ready when you are.";
        if(arg==O_NOTIFY)return L"A Windows notification when an update is ready. Never a pop-up window.";
        if(arg==O_PLAYING)return L"While the launcher runs in the background, a Windows notification when two or more players are on a public server. Click it to join.";
        if(arg==O_CRASH)return L"After a crash, the launcher offers to save a report. Nothing is sent without your approval.";
        if(arg==O_TELEMETRY)return L"Once a day at most: how often the game started, where it crashed, and once a month your Windows version, processor, memory and graphics card. No name, no ID.";
        return arg>=0&&arg<9&&ids[arg]?tip_main(ids[arg]):NULL;}
    case H_SWATCH:swprintf(text,400,tr(L"%ls accent for buttons, highlights and the active page."),tr(optionAccents[arg>=0&&arg<OPTION_ACCENTS?arg:0].name));return text;
    case H_CHIP:return arg==BROWSER_HIDE_FULL?L"Hide servers with no free slot.":arg==BROWSER_HIDE_EMPTY?L"Hide servers nobody is playing on.":
                       arg==BROWSER_RANKED_ONLY?L"Only show ranked servers.":L"Hide servers that fill up with bots.";
    case H_ARTICLE:case H_LINK:return L"Opens the full patch notes on GitHub.";
    case H_DISABLED:{LONG state=update_visible_state();
        if(arg==117)return state==UPDATE_OFF?L"Updates are not set up for this copy. Copies installed with the official setup update themselves.":
                           state==UPDATE_CHECKING?L"Already checking for a new version.":L"Wait until the downloaded files are checked.";
        if(arg==127)return !updateLatestFeed[0]?L"This copy has no update source, so the launcher cannot look for a newer version of itself.":L"The launcher is already checking for, or downloading, a newer version.";
        if(arg==123)return L"Already asking every server. The list fills in a moment.";
        if(arg==104)return L"This folder has no game files and no update source. Install the game with the official setup. The arrow still offers hosting and the game folder.";
        if(arg==152)return game_running()?L"Close the game first.":L"Available once the game is installed and nothing else is downloading.";
        if(arg==153)return game_running()?L"Close the game first.":L"Available while nothing is downloading or being installed.";
        return L"Not available right now.";}
    case H_COMMAND:
        switch(arg){
        case 121:return L"Every public server, with map, players and ping.";
        case 160:if(update_visible_state()==UPDATE_FAILED&&updateError[0]){swprintf(text,400,tr(L"%ls Select to open Settings > Updates."),updateError);return text;}
            return L"Update status and versions. Select to open Settings > Updates.";
        case 161:return L"Removes the shader cache and leftover update files. The game rebuilds what it needs.";
        case 162:return L"Your player name is under Settings > Controls.";
        case 150:return L"Puts every launcher setting on this page back to its default. Graphics, keys and your profile are not touched.";
        case 152:return L"Checks every game file against the release and downloads any that are missing or damaged. Your settings and profile are kept.";
        case 153:return L"Moves the game files to another folder or drive. The launcher restarts from the new place.";
        case 9101:return L"Opens the game folder in Explorer.";
        case 9102:return L"Opens your profile folder: screenshots, recorded matches and in-game settings.";
        default:return tip_main(arg);}
    default:return NULL;
    }
}
/* ---- page fades: the previous frame dissolves into the new page over 140 ms ---- */
#define UI_FADE_MS 140
static HDC uiFadeDC;static HBITMAP uiFadeBitmap,uiFadeOld;static int uiFadeW,uiFadeH,uiFadeActive;static DWORD uiFadeStart;
static void ui_fade_release(void){if(uiFadeDC){SelectObject(uiFadeDC,uiFadeOld);DeleteObject(uiFadeBitmap);DeleteDC(uiFadeDC);uiFadeDC=NULL;}uiFadeActive=0;}
static void ui_fade_begin(HWND window){
    if(shellReduceMotion||shellAnimFrozen>=0||loading||!shellFrameDC||!IsWindowVisible(window)||IsIconic(window))return;
    if(!uiFadeDC||uiFadeW!=shellFrameW||uiFadeH!=shellFrameH){
        ui_fade_release();uiFadeDC=CreateCompatibleDC(shellFrameDC);uiFadeBitmap=CreateCompatibleBitmap(shellFrameDC,shellFrameW,shellFrameH);
        if(!uiFadeDC||!uiFadeBitmap){ui_fade_release();return;}
        uiFadeOld=(HBITMAP)SelectObject(uiFadeDC,uiFadeBitmap);uiFadeW=shellFrameW;uiFadeH=shellFrameH;
    }
    BitBlt(uiFadeDC,0,0,uiFadeW,uiFadeH,shellFrameDC,0,0,SRCCOPY);
    uiFadeStart=GetTickCount();uiFadeActive=1;
}
/* ---- keyboard focus ring around the focused painted control ---- */
static const UiHit *ui_hit_find(int kind,int arg){
    for(int i=0;i<uiHitCount;++i)if(uiHits[i].kind==kind&&uiHits[i].arg==arg)return &uiHits[i];
    return NULL;
}
static void ui_paint_focus(HDC dc,HWND window){
    if(!uiKeyboard||GetFocus()!=window||uiFocusKind==H_NONE)return;
    const UiHit *h=ui_hit_find(uiFocusKind,uiFocusArg);if(!h)return;
    shell_round(dc,(float)h->x-3,(float)h->y-3,(float)h->w+6,(float)h->h+6,9,0,0,SHELL_ARGB(255,SHELL_ACCENT_HOT));
    shell_round(dc,(float)h->x-2,(float)h->y-2,(float)h->w+4,(float)h->h+4,8,0,0,SHELL_ARGB(150,RGB(255,255,255)));
}
/* The page name in the title bar, for Alt+Tab and the taskbar. */
static void ui_window_title(HWND window){
    static const wchar_t *const pages[8]={L"Play",L"Servers",L"News",L"Settings",L"Welcome",L"Profile",L"Replays",L"Host a server"};
    wchar_t title[96];swprintf(title,96,L"TrueCombat: Platinum \x2014 %ls",tr(pages[shellTab>=0&&shellTab<8?shellTab:0]));
    SetWindowTextW(window,title);
}
/* Timers only run while somebody can see the launcher: hidden, minimized, in the tray or
   behind a running game it uses no CPU at all. */
static void shell_timers(HWND window){
    static int running=-1;
    int active=!loading&&shellAnimFrozen<0&&!capture_ui_path[0]&&IsWindowVisible(window)&&!IsIconic(window)&&(!game_running()||GetForegroundWindow()==window);
    if(active==running)return;
    running=active;
    if(active){SetTimer(window,7,33,NULL);tip_start(window);}
    else{KillTimer(window,7);KillTimer(window,11);tip_hide();ui_fade_release();heroclip_stop();}
}
/* RUNNING on the PLAY button: bring the game window to the front. */
static BOOL CALLBACK ui_game_window(HWND candidate,LPARAM found){
    DWORD pid=0;GetWindowThreadProcessId(candidate,&pid);
    if(pid==starting_pid&&IsWindowVisible(candidate)&&!GetWindow(candidate,GW_OWNER)){*(HWND*)found=candidate;return FALSE;}
    return TRUE;
}
static void ui_focus_game(void){
    HWND game=NULL;EnumWindows(ui_game_window,(LPARAM)&game);
    if(game){if(IsIconic(game))ShowWindow(game,SW_RESTORE);SetForegroundWindow(game);}
}
/* One part of the main window: the page (rail=0) or the rail (rail=1), in its own offset. With a cut (design
   y), the part is painted unshifted, the band above the cut kept, then painted again moved down by shellShift
   over a clean background, and the kept band put back on top. */
static void shell_paint_body(HDC dc,HWND window,int rail){
    if(rail){ui_paint_rail(dc);return;}
    if(shellTab==4)ui_paint_welcome(dc);
    else if(shellTab==5)ui_paint_profile(dc,window);
    else if(shellTab==6)ui_paint_replays(dc);
    else if(shellTab==7)ui_paint_host(dc);
    else if(shellTab==0){ui_paint_play(dc,window);if(ui_whats_new_visible())ui_paint_whats_new(dc);else if(telemetry_card_visible())ui_paint_telemetry_card(dc);}
    else if(shellTab==1)ui_paint_servers(dc);
    else if(shellTab==2)ui_paint_news(dc);
    else ui_paint_settings(dc,window);
}
static void shell_paint_part(HDC dc,HWND window,int rail,int cut,int width,int height){
    int page=shellLeft,top=shellTop;if(rail)shellLeft=shellRailLeft;
    int x0=rail?0:shellRail,x1=rail?shellRail:width,cutY=shellTop+(int)(cut*shellScale);
    XFORM t={shellScale,0,0,shellScale,(FLOAT)shellLeft,(FLOAT)shellTop};SetWorldTransform(dc,&t);
    shell_paint_body(dc,window,rail);
    if(cut&&shellShift>0&&cutY>0&&cutY<height){
        XFORM identity={1,0,0,1,0,0};SetWorldTransform(dc,&identity);
        HDC keep=CreateCompatibleDC(dc);HBITMAP band=CreateCompatibleBitmap(dc,x1-x0,cutY);HGDIOBJ old=SelectObject(keep,band);
        BitBlt(keep,0,0,x1-x0,cutY,dc,x0,0,SRCCOPY);
        BitBlt(dc,x0,0,x1-x0,height,uiBackDC,x0,0,SRCCOPY);
        shellTop=top+shellShift;
        XFORM s={shellScale,0,0,shellScale,(FLOAT)shellLeft,(FLOAT)shellTop};SetWorldTransform(dc,&s);
        shell_paint_body(dc,window,rail);
        SetWorldTransform(dc,&identity);
        BitBlt(dc,x0,cutY,x1-x0,shellShift,uiBackDC,x0,cutY,SRCCOPY);
        BitBlt(dc,x0,0,x1-x0,cutY,keep,0,0,SRCCOPY);
        SelectObject(keep,old);DeleteObject(band);DeleteDC(keep);
    }
    shellLeft=page;shellTop=top;
}
static void shell_paint(HWND window,HDC target){
    RECT bounds;GetClientRect(window,&bounds);
    if(!shellFrameDC||shellFrameW!=bounds.right||shellFrameH!=bounds.bottom){
        if(shellFrameDC){SelectObject(shellFrameDC,shellFrameOld);DeleteObject(shellFrameBitmap);DeleteDC(shellFrameDC);}
        shellFrameDC=CreateCompatibleDC(target);shellFrameBitmap=CreateCompatibleBitmap(target,bounds.right,bounds.bottom);
        shellFrameOld=(HBITMAP)SelectObject(shellFrameDC,shellFrameBitmap);shellFrameW=bounds.right;shellFrameH=bounds.bottom;shellBodyDirty=1;
    }
    HDC dc=shellFrameDC;
    if(shellBodyDirty){
        shellBodyDirty=0;
        ui_back_prepare(target,bounds.right,bounds.bottom);
        BitBlt(dc,0,0,bounds.right,bounds.bottom,uiBackDC,0,0,SRCCOPY);
        int saved=SaveDC(dc);
        SetGraphicsMode(dc,GM_ADVANCED);
        uiHitCount=0;
        /* 0.37.1: a window taller than 16:10 (Snap to half a screen, 5:4 and 4:3 monitors) keeps the layout at the
           top and moves the foot of the rail and of the Play and welcome pages (launch bar, Support, status) down
           to the window's bottom edge: each part is painted twice, unshifted above its cut and shifted below it. */
        int pageCut=shellShift?shell_cut(shellTab):0;
        shell_paint_part(dc,window,0,pageCut,bounds.right,bounds.bottom);
        shell_paint_part(dc,window,1,shellShift?SHELL_RAIL_CUT:0,bounds.right,bounds.bottom);
        {const UiHit *f=uiFocusKind!=H_NONE?ui_hit_find(uiFocusKind,uiFocusArg):NULL;
         if(f){int rail=f->x<SHELL_RAIL,cut=rail?(shellShift?SHELL_RAIL_CUT:0):pageCut,page=shellLeft,top=shellTop;
          shellLeft=rail?shellRailLeft:shellLeft;if(cut&&f->y>=cut)shellTop+=shellShift;
          XFORM t={shellScale,0,0,shellScale,(FLOAT)shellLeft,(FLOAT)shellTop};SetWorldTransform(dc,&t);
          ui_paint_focus(dc,window);shellLeft=page;shellTop=top;}}
        XFORM identity={1,0,0,1,0,0};SetWorldTransform(dc,&identity);
        RestoreDC(dc,saved);
    }
    if(uiFadeActive&&uiFadeDC&&uiFadeW==bounds.right&&uiFadeH==bounds.bottom){
        DWORD elapsed=GetTickCount()-uiFadeStart;
        if(elapsed<UI_FADE_MS){
            /* compose new page + fading old page off-screen, then one copy to the window */
            HDC mix=CreateCompatibleDC(target);HBITMAP bitmap=CreateCompatibleBitmap(target,bounds.right,bounds.bottom);
            if(mix&&bitmap){HGDIOBJ old=SelectObject(mix,bitmap);BitBlt(mix,0,0,bounds.right,bounds.bottom,dc,0,0,SRCCOPY);
                float t=elapsed/(float)UI_FADE_MS;t=t*t*(3-2*t);
                BLENDFUNCTION blend={AC_SRC_OVER,0,(BYTE)(255*(1-t)),0};
                GdiAlphaBlend(mix,0,0,bounds.right,bounds.bottom,uiFadeDC,0,0,bounds.right,bounds.bottom,blend);
                BitBlt(target,0,0,bounds.right,bounds.bottom,mix,0,0,SRCCOPY);SelectObject(mix,old);}
            if(bitmap)DeleteObject(bitmap);if(mix)DeleteDC(mix);
            return;
        }
        uiFadeActive=0;
    }else uiFadeActive=0;
    BitBlt(target,0,0,bounds.right,bounds.bottom,dc,0,0,SRCCOPY);
}
