/* GPL-3.0-or-later. Server-side commands for the staff portal (staff.truecombat.eu).
 * Included by tcp_game.c after tcp_report.h. All commands are console / rcon only.
 *
 *   tcp_staffcaps                       prints TCP_STAFF_CAPS <version> <features>, so the portal can tell
 *                                       whether a server has these commands
 *   tcp_players                         one TCP_STAFF_PLAYER line per connected client (name last)
 *   mute <slot> [minutes] [reason]      blocks say, say_team and voice commands for that player
 *                                       (0 or no minutes = until the map ends; the portal re-applies
 *                                       longer mutes after a map change or reconnect)
 *   unmute <slot>
 *   warn <slot> <text>                  private staff warning, shown in the player's chat and console
 *   putteam <slot> <r|b|s>              moves a player; a living player in a live round moves at the
 *                                       next deploy, exactly like a player's own team change
 *   staffsay <staff name> <text>        chat line to everyone, marked as staff
 *
 * A mute is bound to the player's cl_guid, so it never carries over to whoever takes the slot next. */
#ifndef TCP_STAFF_ADMIN_H
#define TCP_STAFF_ADMIN_H
#define TCP_STAFF_ADMIN_VERSION 1
static int staffMuteUntil[TCP_MAX_PLAYERS];   /* levelTime the mute ends; -1 = until the map ends */
static char staffMuteGuid[TCP_MAX_PLAYERS][40];

static void staffGuid(int n,char *out,size_t cap){
    char info[MAX_INFO_STRING];out[0]=0;SystemCall(G_GET_USERINFO,n,info,sizeof(info));TCP_InfoValue(info,"cl_guid",out,(int)cap);
}
static int TCP_StaffMuted(int n){
    if(n<0||n>=TCP_MAX_PLAYERS||!staffMuteUntil[n])return 0;
    char g[40];staffGuid(n,g,sizeof(g));
    if(Q_stricmpn_native(g,staffMuteGuid[n])||(staffMuteUntil[n]>0&&levelTime>=staffMuteUntil[n])){staffMuteUntil[n]=0;staffMuteGuid[n][0]=0;return 0;}
    return 1;
}
/* Client commands a muted player may not use. Returns 1 when the command was swallowed. */
static int TCP_StaffMuteFilter(int n,const char *cmd){
    if(strcmp(cmd,"say")&&strcmp(cmd,"say_team")&&Q_stricmpn_native(cmd,"vsay")&&Q_stricmpn_native(cmd,"vsay_team")&&Q_stricmpn_native(cmd,"vsay_buddy"))return 0;
    if(!TCP_StaffMuted(n))return 0;
    SystemCall(G_SEND_SERVER_COMMAND,n,"print \"You are muted by server staff.\n\"");
    return 1;
}
static void staffArgsFrom(int first,char *out,size_t cap){
    char word[MAX_STRING_CHARS];out[0]=0;
    for(int i=first;i<SystemCall(G_ARGC);i++){SystemCall(G_ARGV,i,word,sizeof(word));
        if(strlen(out)+strlen(word)+2<cap){if(out[0])strcat(out," ");strcat(out,word);}}
    for(char *c=out;*c;c++)if(*c=='"'||*c=='\\'||*c==';'||(unsigned char)*c<32)*c='\'';
}
static int staffSlotArg(int index){
    char a[16];SystemCall(G_ARGV,index,a,sizeof(a));if(!a[0])return -1;
    for(const char *p=a;*p;p++)if(*p<'0'||*p>'9')return -1;
    int s=atoi(a);return s>=0&&s<maxClients&&clients[s].connected?s:-1;
}
static void staffPlayers(void){
    char s[400],name[48],pid[17];
    snprintf(s,sizeof(s),"TCP_STAFF_MATCH map_time=%d round_phase=%d team_mode=%d\n",levelTime,roundPhase,teamMode);print(s);
    for(int i=0;i<maxClients;i++){
        if(!clients[i].connected)continue;
        const client_t *c=&clients[i];TCP_PlayerName(i,name,sizeof(name));TCP_PlayerPid(i,pid);
        int left=TCP_StaffMuted(i)?(staffMuteUntil[i]<0?-1:(staffMuteUntil[i]-levelTime+999)/1000):0;
        snprintf(s,sizeof(s),"TCP_STAFF_PLAYER slot=%d begun=%d team=%d spec=%d bot=%d alive=%d muted=%d kills=%u deaths=%u team_kills=%d damage=%d pid=%s name=%s\n",
            i,c->begun,c->team,c->spectator,bots[i].active?1:0,c->begun&&!c->spectator&&c->health.health>0,left,c->kills,c->deaths,c->teamKills,c->damageGiven,pid[0]?pid:"-",name);
        print(s);
    }
    print("TCP_STAFF_END\n");
}
static int TCP_StaffAdminConsole(const char *cmd){
    char m[400],text[256],name[48];
    if(!strcmp(cmd,"tcp_staffcaps")){snprintf(m,sizeof(m),"TCP_STAFF_CAPS %d players mute warn putteam staffsay\n",TCP_STAFF_ADMIN_VERSION);print(m);return 1;}
    if(!strcmp(cmd,"tcp_players")){staffPlayers();return 1;}
    if(!strcmp(cmd,"mute")){
        int n=staffSlotArg(1);if(n<0){print("usage: mute <slot> [minutes] [reason]\n");return 1;}
        char a[16];SystemCall(G_ARGV,2,a,sizeof(a));int minutes=atoi(a);staffArgsFrom(3,text,sizeof(text));
        staffGuid(n,staffMuteGuid[n],sizeof(staffMuteGuid[n]));staffMuteUntil[n]=minutes>0?levelTime+minutes*60000:-1;
        TCP_PlayerName(n,name,sizeof(name));
        snprintf(m,sizeof(m),"print \"^3You have been muted by server staff%s%s.\n\"",text[0]?": ":"",text);SystemCall(G_SEND_SERVER_COMMAND,n,m);
        snprintf(m,sizeof(m),"TCP_STAFF_MUTE slot=%d minutes=%d reason=%s\n",n,minutes,text);print(m);return 1;}
    if(!strcmp(cmd,"unmute")){
        int n=staffSlotArg(1);if(n<0){print("usage: unmute <slot>\n");return 1;}
        int was=TCP_StaffMuted(n);staffMuteUntil[n]=0;staffMuteGuid[n][0]=0;
        if(was)SystemCall(G_SEND_SERVER_COMMAND,n,"print \"^2Server staff lifted your mute.\n\"");
        snprintf(m,sizeof(m),"TCP_STAFF_UNMUTE slot=%d was=%d\n",n,was);print(m);return 1;}
    if(!strcmp(cmd,"warn")){
        int n=staffSlotArg(1);staffArgsFrom(2,text,sizeof(text));
        if(n<0||!text[0]){print("usage: warn <slot> <text>\n");return 1;}
        snprintf(m,sizeof(m),"chat \"^8STAFF WARNING^7: ^3%s\" -1 0",text);SystemCall(G_SEND_SERVER_COMMAND,n,m);
        snprintf(m,sizeof(m),"print \"^8STAFF WARNING^7: %s\n\"",text);SystemCall(G_SEND_SERVER_COMMAND,n,m);
        snprintf(m,sizeof(m),"TCP_STAFF_WARN slot=%d text=%s\n",n,text);print(m);return 1;}
    if(!strcmp(cmd,"putteam")){
        int n=staffSlotArg(1);char a[8];SystemCall(G_ARGV,2,a,sizeof(a));
        if(n<0||(a[0]!='r'&&a[0]!='b'&&a[0]!='s')){print("usage: putteam <slot> <r|b|s>\n");return 1;}
        client_t *c=&clients[n];
        if(!c->begun){print("TCP_STAFF_PUTTEAM refused=loading\n");return 1;}
        if(a[0]=='s'){specEnter(n,"staff");snprintf(m,sizeof(m),"TCP_STAFF_PUTTEAM slot=%d team=s\n",n);print(m);return 1;}
        if(!teamMode){print("TCP_STAFF_PUTTEAM refused=no_teams\n");return 1;}
        int want=a[0]=='r'?TCP_TEAM_RED:TCP_TEAM_BLUE;const char *label=want==TCP_TEAM_RED?"Terrorists":"Specops";int pending=0;
        if(c->spectator){c->spectator=0;c->team=want;c->pendingTeam=0;announceTeam(n);c->spectator=1;specLeave(n);}
        else if(want==c->team){c->pendingTeam=0;}
        else if(roundPhase==TCP_ROUND_LIVE&&c->inRound&&c->health.health>0){c->pendingTeam=want;pending=1;}
        else{c->team=want;c->pendingTeam=0;announceTeam(n);if(roundPhase==TCP_ROUND_OFF&&c->health.health>0)spawn(n);}
        snprintf(m,sizeof(m),pending?"print \"^3Server staff moved you to the %s. You switch when you next deploy.\n\"":"print \"^3Server staff moved you to the %s.\n\"",label);
        SystemCall(G_SEND_SERVER_COMMAND,n,m);
        snprintf(m,sizeof(m),"TCP_STAFF_PUTTEAM slot=%d team=%d pending=%d\n",n,want,pending);print(m);return 1;}
    if(!strcmp(cmd,"staffsay")){
        char who[48];SystemCall(G_ARGV,1,who,sizeof(who));staffArgsFrom(2,text,sizeof(text));
        for(char *c=who;*c;c++)if(*c=='"'||*c=='^'||*c=='\\'||*c==';'||(unsigned char)*c<32)*c=' ';
        if(!who[0]||!text[0]){print("usage: staffsay <staff name> <text>\n");return 1;}
        snprintf(m,sizeof(m),"chat \"^8[STAFF] %s^7: ^7%s\" -1 0",who,text);
        for(int i=0;i<maxClients;i++)if(clients[i].connected)SystemCall(G_SEND_SERVER_COMMAND,i,m);
        snprintf(m,sizeof(m),"TCP_STAFF_SAY by=%s text=%s\n",who,text);print(m);return 1;}
    return 0;
}
#endif
