/* Staff badge keys made in the staff portal (staff.truecombat.eu). Included by tcp_staff.h right after
 * tcp_staff_keys.h, before the first use of the key table.
 *
 * The portal writes one line per staff member to g_staffKeyFile (default "staffkeys/staffkeys.txt" in the
 * game folder, e.g. /var/lib/tcpgame/home/tcetest/staffkeys/staffkeys.txt):
 *     TCPSTAFFKEY1 <key id> <role> <64 hex Ed25519 public key> <name, rest of the line>
 * Lines starting with '#' and anything malformed are skipped. The keys built into the game
 * (tcp_staff_keys.h) always count as well. The file holds public keys only.
 *
 * The list is read when the game starts, before every tcp_staffauth (it is a few hundred bytes), and on the
 * console / rcon command "staffkeys_reload", which also takes the badge off anyone whose key is no longer
 * listed. The portal sends that command after every change, so a revoked key stops at once.
 * A server without the file behaves exactly as before. */
#ifndef TCP_STAFF_FILEKEYS_H
#define TCP_STAFF_FILEKEYS_H
#define TCP_STAFF_FILE_MAX 64

typedef struct {char id[32],name[40];int role;unsigned char key[32];} tcpStaffFileKey_t;
static tcpStaffFileKey_t staffFileKeys[TCP_STAFF_FILE_MAX];
static int staffFileKeyCount;
static char staffBadgeId[MAX_CLIENTS][32];   /* key id behind each badge, "" = none */

static int TCP_StaffHexNibble(char c){
    return c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;
}
/* Parses the whole file text; returns the number of keys taken. Pure, so it can be tested on its own. */
static int TCP_StaffParseKeys(const char *text,tcpStaffFileKey_t *out,int max){
    int count=0;const char *p=text;
    while(p&&*p&&count<max){
        const char *end=strchr(p,'\n');size_t len=end?(size_t)(end-p):strlen(p);
        char line[256];
        if(len<sizeof(line)){
            memcpy(line,p,len);line[len]=0;
            if(len&&line[len-1]=='\r')line[len-1]=0;
            char tag[16],id[32],hex[80];int role=0,used=0;
            if(line[0]!='#'&&sscanf(line,"%15s %31s %d %79s %n",tag,id,&role,hex,&used)==4&&!strcmp(tag,"TCPSTAFFKEY1")
               &&role>0&&role<16&&strlen(hex)==64){
                tcpStaffFileKey_t k;int ok=1;memset(&k,0,sizeof(k));
                for(int i=0;i<32&&ok;i++){int a=TCP_StaffHexNibble(hex[i*2]),b=TCP_StaffHexNibble(hex[i*2+1]);if(a<0||b<0)ok=0;else k.key[i]=(unsigned char)(a*16+b);}
                for(const char *c=id;*c&&ok;c++)if(!((*c>='a'&&*c<='z')||(*c>='0'&&*c<='9')||*c=='_'||*c=='-'))ok=0;
                if(ok){
                    snprintf(k.id,sizeof(k.id),"%s",id);k.role=role;
                    const char *name=used>0&&used<=(int)strlen(line)?line+used:"";
                    int n=0;for(const char *c=name;*c&&n<(int)sizeof(k.name)-1;c++)if((unsigned char)*c>=32&&*c!='"'&&*c!='\\'&&*c!=';')k.name[n++]=*c;
                    k.name[n]=0;
                    out[count++]=k;
                }
            }
        }
        p=end?end+1:NULL;
    }
    return count;
}
static void TCP_StaffLoadFile(void){
    char path[128];int f=0;
    SystemCall(G_CVAR_VARIABLE_STRING_BUFFER,"g_staffKeyFile",path,sizeof(path));
    if(!path[0])snprintf(path,sizeof(path),"staffkeys/staffkeys.txt");
    int len=(int)SystemCall(G_FS_FOPEN_FILE,path,&f,FS_READ);
    if(len<=0||!f){if(f)SystemCall(G_FS_FCLOSE_FILE,f);staffFileKeyCount=0;return;}
    if(len>16*1024)len=16*1024;
    static char buf[16*1024+1];
    SystemCall(G_FS_READ,buf,len,f);SystemCall(G_FS_FCLOSE_FILE,f);buf[len]=0;
    staffFileKeyCount=TCP_StaffParseKeys(buf,staffFileKeys,TCP_STAFF_FILE_MAX);
}
/* Finds a key by id: built-in keys first, then the portal's list. */
static int TCP_StaffFindKey(const char *id,const unsigned char **key,const char **name,int *role){
    for(int i=0;i<TCP_STAFF_KEYS;i++)if(tcpStaffKeys[i].id[0]&&!strcmp(tcpStaffKeys[i].id,id)){*key=tcpStaffKeys[i].key;*name=tcpStaffKeys[i].name;*role=tcpStaffKeys[i].role;return 1;}
    for(int i=0;i<staffFileKeyCount;i++)if(!strcmp(staffFileKeys[i].id,id)){*key=staffFileKeys[i].key;*name=staffFileKeys[i].name;*role=staffFileKeys[i].role;return 1;}
    return 0;
}
/* "staffkeys_reload": re-read the list and drop badges whose key is gone. Returns 1 when it was this command. */
static int TCP_StaffKeysConsole(const char *cmd){
    if(strcmp(cmd,"staffkeys_reload"))return 0;
    TCP_StaffLoadFile();
    int dropped=0;
    for(int n=0;n<MAX_CLIENTS;n++){
        const unsigned char *k;const char *nm;int role;
        if(!staffBadge[n]||!staffBadgeId[n][0]||TCP_StaffFindKey(staffBadgeId[n],&k,&nm,&role))continue;
        char m[120];snprintf(m,sizeof(m),"TCP_STAFF_REVOKED slot=%d key=%s\n",n,staffBadgeId[n]);print(m);
        staffBadge[n]=0;staffBadgeId[n][0]=0;dropped++;
        if(clients[n].connected)playerConfig(n);
    }
    char m[96];snprintf(m,sizeof(m),"TCP_STAFF_KEYS file=%d builtin=%d dropped=%d\n",staffFileKeyCount,TCP_STAFF_KEYS,dropped);print(m);
    return 1;
}
#endif
