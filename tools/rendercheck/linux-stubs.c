/* Linux build of the native cgame for the cloud render check only (never shipped): Windows-only calls return "not available". */
void *LoadLibraryA(const char *n){(void)n;return 0;}
void *GetProcAddress(void *m,const char *n){(void)m;(void)n;return 0;}
void *LocalFree(void *p){(void)p;return 0;}
void *GetModuleHandleA(const char *n){(void)n;return 0;}
unsigned long GetCurrentThreadId(void){return 1;}
void *CreateThread(void *a,unsigned long b,void *c,void *d,unsigned long e,void *f){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;return 0;}
int CloseHandle(void *h){(void)h;return 1;}
