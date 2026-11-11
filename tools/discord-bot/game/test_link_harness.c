/* Contract test for tcp_link.h: drives TCP_LinkRequest with a fake engine and
 * writes the request file exactly where the server would. */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "game/g_public.h"
#include "game/bg_public.h"
#undef SystemCall
#define MAX_INFO_STRING_T 1024
typedef int fileHandle_t_unused;
static struct { int connected; } clients[64];
static int maxClients = 64, levelTime = 10000;
static const char *fakeGuid = "0123456789abcdef0123456789ABCDEF";
static char lastPrint[256];
static FILE *files[8];
static void print(const char *s) { fputs(s, stderr); }
static void TCP_InfoValue(const char *info, const char *key, char *out, size_t cap) {
    char pat[64]; snprintf(pat, sizeof pat, "\\%s\\", key);
    const char *p = strstr(info, pat); out[0] = 0; if (!p) return; p += strlen(pat);
    size_t i = 0; while (*p && *p != '\\' && i + 1 < cap) out[i++] = *p++; out[i] = 0;
}
static intptr_t SystemCall(intptr_t cmd, ...) {
    va_list ap; va_start(ap, cmd); intptr_t r = 0;
    switch (cmd) {
    case G_GET_USERINFO: { va_arg(ap, int); char *buf = va_arg(ap, char *); int n = va_arg(ap, int);
        snprintf(buf, n, "\\name\\x\\cl_guid\\%s", fakeGuid); break; }
    case G_GET_CONFIGSTRING: { va_arg(ap, int); char *buf = va_arg(ap, char *); int n = va_arg(ap, int);
        snprintf(buf, n, "\\n\\^1Gia\"nni\\t\\1"); break; }
    case G_FS_FOPEN_FILE: { const char *path = va_arg(ap, const char *); fileHandle_t *f = va_arg(ap, fileHandle_t *);
        char full[256]; snprintf(full, sizeof full, "out/%s", path); files[1] = fopen(full, "wb"); *f = files[1] ? 1 : 0; r = files[1] ? 0 : -1; break; }
    case G_FS_WRITE: { const char *b = va_arg(ap, const char *); int len = va_arg(ap, int); int f = va_arg(ap, int); fwrite(b, 1, len, files[f]); break; }
    case G_FS_FCLOSE_FILE: { int f = va_arg(ap, int); fclose(files[f]); break; }
    case G_SEND_SERVER_COMMAND: { va_arg(ap, int); snprintf(lastPrint, sizeof lastPrint, "%s", va_arg(ap, const char *)); break; }
    }
    va_end(ap); return r;
}
#include "tcp_link.h"
int main(void) {
    clients[3].connected = 1;
    TCP_LinkRequest(3, "nope");          printf("bad:  %s\n", lastPrint);
    TCP_LinkRequest(3, " k7q-4p2 ");     printf("ok:   %s\n", lastPrint);
    levelTime += 1000;
    TCP_LinkRequest(3, "K7Q4P2");        printf("fast: %s\n", lastPrint);
    levelTime += 6000; fakeGuid = "";
    TCP_LinkRequest(3, "K7Q4P2");        printf("noguid: %s\n", lastPrint);
    return 0;
}
