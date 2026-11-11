/* TrueCombat: Platinum master server (public server list).

   Speaks the standard ET / ET:Legacy master protocol over UDP:
     server -> master   "heartbeat EnemyTerritory-1"   (every 5 minutes, on map start)
     master -> server   "getinfo <challenge>"
     server -> master   "infoResponse\n\key\value..."  (must echo the challenge)
     server -> master   "heartbeat ETFlatline-1"       (server shutting down)
     client -> master   "getservers <protocol> [empty] [full]"
     master -> client   "getserversResponse\<ip4><port2>\...\EOT"
     client -> master   "getserversExt <game> <protocol> [empty] [full] [ipv4] [ipv6]"
     master -> client   "getserversExtResponse\<ip4><port2>/<ip6><port2>...\EOT"
   Dual stack: IPv4 and IPv6 are separate sockets on the same port. Servers that
   heartbeat over IPv6 are listed with their IPv6 address; plain getservers
   (older clients) only ever returns IPv4 entries.
   Only servers that answer the challenge, use protocol 84 and run the expected
   game folder (default tcetest) are listed. Entries expire 15 minutes after the
   last verified heartbeat. Requests are rate-limited per source address.

   Build (Windows):  x86_64-w64-mingw32-clang -O2 -Wall -Wextra platinum_master.c -o platinum-master.exe -lws2_32 -lbcrypt
   Build (Linux):    cc -O2 -Wall -Wextra platinum_master.c -o platinum-master
   Run:              platinum-master [--port 27950] [--bind 0.0.0.0] [--bind6 ::|off] [--game tcetest] [--max 512]
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <stdarg.h>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <bcrypt.h>
typedef int socklen_t;
#define close_socket closesocket
#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/select.h>
typedef int SOCKET;
#define INVALID_SOCKET (-1)
#define close_socket close
#endif

#define PROTOCOL 84
#define EXPIRE_SECONDS (15*60)
#define PENDING_SECONDS 10
#define MAX_PENDING 256
#define RATE_SLOTS 1024

/* An address of either family: v6 holds 16 bytes, v4 the first 4. Port in network order. */
typedef struct {int v6;unsigned char ip[16];uint16_t port;} Addr;
typedef struct {Addr a;time_t seen;int used;char name[64],map[32];int clients,slots;} Server;
typedef struct {Addr a;time_t sent;char challenge[24];int used;} Pending;
typedef struct {uint32_t key;time_t window;int count;} Rate;

static Server *servers;static int maxServers=512;
static Pending pending[MAX_PENDING];
static Rate rates[RATE_SLOTS];
static char game[32]="tcetest";
static volatile int running=1;

static void log_line(const char *format,...){
    char stamp[32];time_t now=time(NULL);struct tm *t=gmtime(&now);strftime(stamp,sizeof(stamp),"%Y-%m-%d %H:%M:%S",t);
    va_list args;va_start(args,format);printf("%s ",stamp);vprintf(format,args);printf("\n");va_end(args);fflush(stdout);
}
static int addr_from(const struct sockaddr_storage *ss,Addr *a){
    memset(a,0,sizeof(*a));
    if(ss->ss_family==AF_INET){const struct sockaddr_in *s4=(const struct sockaddr_in*)ss;memcpy(a->ip,&s4->sin_addr,4);a->port=s4->sin_port;return 1;}
    if(ss->ss_family==AF_INET6){const struct sockaddr_in6 *s6=(const struct sockaddr_in6*)ss;
        static const unsigned char mapped[12]={0,0,0,0,0,0,0,0,0,0,0xff,0xff};
        if(!memcmp(&s6->sin6_addr,mapped,12)){memcpy(a->ip,((const unsigned char*)&s6->sin6_addr)+12,4);a->port=s6->sin6_port;return 1;}
        a->v6=1;memcpy(a->ip,&s6->sin6_addr,16);a->port=s6->sin6_port;return 1;}
    return 0;
}
static int addr_eq(const Addr *x,const Addr *y){return x->v6==y->v6&&x->port==y->port&&!memcmp(x->ip,y->ip,x->v6?16:4);}
/* Rate-limit key: the whole IPv4 address, or the /64 prefix for IPv6 (one host usually owns the whole /64). */
static uint32_t addr_key(const Addr *a){
    uint32_t h=2166136261u;int n=a->v6?8:4;for(int i=0;i<n;++i){h^=a->ip[i];h*=16777619u;}return h^(uint32_t)a->v6;
}
static const char *addr_str(const Addr *a){
    static char out[2][64];static int which;char *o=out[which^=1],ip[INET6_ADDRSTRLEN];
    inet_ntop(a->v6?AF_INET6:AF_INET,a->ip,ip,sizeof(ip));
    snprintf(o,64,a->v6?"[%s]:%u":"%s:%u",ip,ntohs(a->port));return o;
}
static int rate_ok(uint32_t key,int limit){
    time_t now=time(NULL);Rate *r=&rates[(key*2654435761u)>>22&(RATE_SLOTS-1)];
    if(r->key!=key||now-r->window>=10){r->key=key;r->window=now;r->count=0;}
    return ++r->count<=limit;
}
static void random_challenge(char *out,size_t size){
    unsigned char bytes[8];
#ifdef _WIN32
    BCryptGenRandom(NULL,bytes,sizeof(bytes),BCRYPT_USE_SYSTEM_PREFERRED_RNG);
#else
    FILE *f=fopen("/dev/urandom","rb");if(!f||fread(bytes,1,sizeof(bytes),f)!=sizeof(bytes)){for(size_t i=0;i<sizeof(bytes);++i)bytes[i]=(unsigned char)rand();}if(f)fclose(f);
#endif
    snprintf(out,size,"%02x%02x%02x%02x%02x%02x%02x%02x",bytes[0],bytes[1],bytes[2],bytes[3],bytes[4],bytes[5],bytes[6],bytes[7]);
}
/* Value of \key\ in an infostring (case-insensitive key). */
static int info_value(const char *info,const char *key,char *out,size_t size){
    const char *p=info;size_t n=strlen(key);out[0]=0;
    while(*p=='\\'){
        const char *k=p+1,*ke=strchr(k,'\\');if(!ke)return 0;
        const char *v=ke+1,*ve=strchr(v,'\\');if(!ve)ve=v+strlen(v);
        if((size_t)(ke-k)==n&&!strncmp(k,key,n)){size_t len=(size_t)(ve-v);if(len>=size)len=size-1;memcpy(out,v,len);out[len]=0;return 1;}
        p=ve;
    }
    return 0;
}
/* Where a reply goes: the socket the request came in on, back to its source. */
typedef struct {SOCKET s;struct sockaddr_storage to;socklen_t len;} Reply;
static void send_raw(const Reply *r,const void *data,int n){sendto(r->s,(const char*)data,n,0,(const struct sockaddr*)&r->to,r->len);}
static void send_text(const Reply *r,const char *text){
    char packet[1400];int n=snprintf(packet,sizeof(packet),"\xff\xff\xff\xff%s",text);
    if(n>0)send_raw(r,packet,n);
}
static Server *find_server(const Addr *a,int create){
    Server *free_slot=NULL;time_t now=time(NULL);
    for(int i=0;i<maxServers;++i){
        Server *e=&servers[i];
        if(e->used&&now-e->seen>EXPIRE_SECONDS){e->used=0;}
        if(e->used&&addr_eq(&e->a,a))return e;
        if(!e->used&&!free_slot)free_slot=e;
    }
    if(create&&free_slot){memset(free_slot,0,sizeof(*free_slot));free_slot->a=*a;free_slot->used=1;return free_slot;}
    return NULL;
}
static void handle_heartbeat(const Reply *r,const Addr *from,const char *name){
    if(!strncmp(name,"ETFlatline",10)){Server *e=find_server(from,0);if(e){e->used=0;log_line("removed %s (shutdown)",addr_str(from));}return;}
    if(strncmp(name,"EnemyTerritory",14))return;
    Pending *slot=&pending[0];time_t now=time(NULL);
    for(int i=0;i<MAX_PENDING;++i){
        if(pending[i].used&&addr_eq(&pending[i].a,from)){slot=&pending[i];break;}
        if(!pending[i].used||now-pending[i].sent>PENDING_SECONDS){slot=&pending[i];}
    }
    slot->used=1;slot->a=*from;slot->sent=now;random_challenge(slot->challenge,sizeof(slot->challenge));
    char request[64];snprintf(request,sizeof(request),"getinfo %s",slot->challenge);send_text(r,request);
}
static void handle_info(const Addr *from,const char *info){
    time_t now=time(NULL);Pending *match=NULL;
    for(int i=0;i<MAX_PENDING;++i)if(pending[i].used&&addr_eq(&pending[i].a,from)&&now-pending[i].sent<=PENDING_SECONDS){match=&pending[i];break;}
    if(!match)return;
    char challenge[64],protocol[16],folder[64],value[64];
    info_value(info,"challenge",challenge,sizeof(challenge));info_value(info,"protocol",protocol,sizeof(protocol));info_value(info,"game",folder,sizeof(folder));
    if(strcmp(challenge,match->challenge))return;
    match->used=0;
    if(atoi(protocol)!=PROTOCOL||strcmp(folder,game)){log_line("ignored %s (protocol %s, game '%s')",addr_str(from),protocol,folder);return;}
    Server *e=find_server(from,1);if(!e){log_line("list full, ignored %s",addr_str(from));return;}
    int fresh=e->seen==0;e->seen=now;
    info_value(info,"hostname",e->name,sizeof(e->name));info_value(info,"mapname",e->map,sizeof(e->map));
    info_value(info,"clients",value,sizeof(value));e->clients=atoi(value);info_value(info,"sv_maxclients",value,sizeof(value));e->slots=atoi(value);
    if(fresh)log_line("listed %s \"%s\" %s %d/%d",addr_str(from),e->name,e->map,e->clients,e->slots);
}
/* getservers <protocol> [flags]            -> IPv4 entries only (classic format)
   getserversExt <game> <protocol> [flags]  -> IPv4 and IPv6; flags ipv4 / ipv6 narrow it to one family */
static void handle_getservers(const Reply *r,const char *args,int extended){
    if(extended){while(*args&&*args!=' ')++args;while(*args==' ')++args;}  /* skip the game name: clients send "et" */
    if(atoi(args)!=PROTOCOL)return;
    int wantEmpty=strstr(args,"empty")!=NULL,wantFull=strstr(args,"full")!=NULL;
    int want4=1,want6=extended;
    if(extended&&strstr(args,"ipv6")&&!strstr(args,"ipv4"))want4=0;
    if(extended&&strstr(args,"ipv4")&&!strstr(args,"ipv6"))want6=0;
    unsigned char packet[1400];const char *head=extended?"\xff\xff\xff\xffgetserversExtResponse":"\xff\xff\xff\xffgetserversResponse";size_t headLength=strlen(head);
    size_t n=headLength;memcpy(packet,head,n);time_t now=time(NULL);
    for(int i=0;i<maxServers;++i){
        Server *e=&servers[i];if(!e->used||now-e->seen>EXPIRE_SECONDS)continue;
        if(e->a.v6?!want6:!want4)continue;
        if(!wantEmpty&&e->clients==0)continue;
        if(!wantFull&&e->slots>0&&e->clients>=e->slots)continue;
        size_t entry=e->a.v6?19:7;
        if(n+entry+7>sizeof(packet)){send_raw(r,packet,(int)n);n=headLength;}
        packet[n++]=e->a.v6?'/':'\\';memcpy(packet+n,e->a.ip,e->a.v6?16:4);n+=e->a.v6?16:4;memcpy(packet+n,&e->a.port,2);n+=2;
    }
    memcpy(packet+n,"\\EOT\0\0\0",7);n+=7;
    send_raw(r,packet,(int)n);
}
static void handle_packet(SOCKET s,const struct sockaddr_storage *ss,socklen_t len,char *buffer,int n){
    Addr from;if(n<5||memcmp(buffer,"\xff\xff\xff\xff",4)||!addr_from(ss,&from))return;
    buffer[n]=0;const char *text=buffer+4;uint32_t key=addr_key(&from);
    if(!rate_ok(key,40))return;
    Reply r;r.s=s;r.to=*ss;r.len=len;
    if(!strncmp(text,"heartbeat ",10)){char name[64]={0};sscanf(text+10,"%63s",name);handle_heartbeat(&r,&from,name);}
    else if(!strncmp(text,"infoResponse",12)){const char *info=strchr(text,'\\');if(info)handle_info(&from,info);}
    else if(!strncmp(text,"getservers ",11)){if(rate_ok(key^0x5bd1e995u,6))handle_getservers(&r,text+11,0);}
    else if(!strncmp(text,"getserversExt ",14)){if(rate_ok(key^0x5bd1e995u,6))handle_getservers(&r,text+14,1);}
}
int main(int argc,char **argv){
    int port=27950;const char *bind_address="0.0.0.0",*bind6="::";
    for(int i=1;i<argc;++i){
        if(!strcmp(argv[i],"--port")&&i+1<argc)port=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--bind")&&i+1<argc)bind_address=argv[++i];
        else if(!strcmp(argv[i],"--bind6")&&i+1<argc)bind6=argv[++i];
        else if(!strcmp(argv[i],"--game")&&i+1<argc){strncpy(game,argv[++i],sizeof(game)-1);}
        else if(!strcmp(argv[i],"--max")&&i+1<argc)maxServers=atoi(argv[++i]);
        else{fprintf(stderr,"usage: %s [--port 27950] [--bind 0.0.0.0|off] [--bind6 ::|off] [--game tcetest] [--max 512]\n",argv[0]);return 2;}
    }
    if(port<1||port>65535||maxServers<1||maxServers>65536)return 2;
    servers=calloc((size_t)maxServers,sizeof(Server));if(!servers)return 3;
#ifdef _WIN32
    WSADATA ws;if(WSAStartup(MAKEWORD(2,2),&ws))return 3;
#endif
    SOCKET s4=INVALID_SOCKET,s6=INVALID_SOCKET;
    if(strcmp(bind_address,"off")){
        s4=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);if(s4==INVALID_SOCKET)return 3;
        struct sockaddr_in address;memset(&address,0,sizeof(address));address.sin_family=AF_INET;address.sin_port=htons((uint16_t)port);
        if(inet_pton(AF_INET,bind_address,&address.sin_addr)!=1){fprintf(stderr,"bad --bind address\n");return 2;}
        if(bind(s4,(struct sockaddr*)&address,sizeof(address))){fprintf(stderr,"cannot bind UDP %s:%d\n",bind_address,port);return 4;}
        log_line("TrueCombat: Platinum master server on UDP %s:%d (game %s, protocol %d)",bind_address,port,game,PROTOCOL);
    }
    if(strcmp(bind6,"off")){
        struct sockaddr_in6 address;memset(&address,0,sizeof(address));address.sin6_family=AF_INET6;address.sin6_port=htons((uint16_t)port);
        if(inet_pton(AF_INET6,bind6,&address.sin6_addr)!=1){fprintf(stderr,"bad --bind6 address\n");return 2;}
        s6=socket(AF_INET6,SOCK_DGRAM,IPPROTO_UDP);
        int only=1;
        if(s6!=INVALID_SOCKET)setsockopt(s6,IPPROTO_IPV6,IPV6_V6ONLY,(const char*)&only,sizeof(only));
        if(s6==INVALID_SOCKET||bind(s6,(struct sockaddr*)&address,sizeof(address))){
            /* No IPv6 on this host is not fatal while IPv4 works */
            log_line("IPv6 unavailable on [%s]:%d, serving IPv4 only",bind6,port);
            if(s6!=INVALID_SOCKET){close_socket(s6);}
            s6=INVALID_SOCKET;
        }else log_line("listening on UDP [%s]:%d as well",bind6,port);
    }
    if(s4==INVALID_SOCKET&&s6==INVALID_SOCKET){fprintf(stderr,"no socket to listen on\n");return 4;}
    static char buffer[2048];
    while(running){
        fd_set set;FD_ZERO(&set);
        if(s4!=INVALID_SOCKET)FD_SET(s4,&set);
        if(s6!=INVALID_SOCKET)FD_SET(s6,&set);
        int top=(int)(s4!=INVALID_SOCKET&&s4>s6?s4:s6);
        if(select(top+1,&set,NULL,NULL,NULL)<=0)continue;
        SOCKET both[2]={s4,s6};
        for(int k=0;k<2;++k){
            if(both[k]==INVALID_SOCKET||!FD_ISSET(both[k],&set))continue;
            struct sockaddr_storage from;socklen_t fromLength=sizeof(from);
            int n=(int)recvfrom(both[k],buffer,sizeof(buffer)-1,0,(struct sockaddr*)&from,&fromLength);
            if(n>0)handle_packet(both[k],&from,fromLength,buffer,n);
        }
    }
    if(s4!=INVALID_SOCKET)close_socket(s4);
    if(s6!=INVALID_SOCKET)close_socket(s6);
    return 0;
}
