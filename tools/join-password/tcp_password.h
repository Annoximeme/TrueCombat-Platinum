/* GPL-3.0-or-later. Join password (thread "Improve online play"). Included by tcp_game.c
 * after tcp_report.h. The native module never checked g_password, so private servers
 * (pickup matches) were open to anyone with the address. A human connecting for the
 * first time must send userinfo "password" equal to g_password when it is set and not
 * "none"; bots and map-change reconnects are let through. g_needpass mirrors it in
 * serverinfo so browsers can show a lock. */
#ifndef TCP_PASSWORD_H
#define TCP_PASSWORD_H
static void TCP_PasswordInit(void){
    SystemCall(G_CVAR_REGISTER,NULL,"g_password","",0);
    SystemCall(G_CVAR_REGISTER,NULL,"g_needpass","0",CVAR_SERVERINFO);
}
static int TCP_PasswordRequired(char *pw,size_t cap){
    pw[0]=0;SystemCall(G_CVAR_VARIABLE_STRING_BUFFER,"g_password",pw,(int)cap);
    return pw[0]&&strcmp(pw,"none");
}
static const char *TCP_PasswordCheck(const char *userinfo,int firstTime,int isBot){
    char want[64],got[64];
    if(isBot||!firstTime||!TCP_PasswordRequired(want,sizeof(want)))return NULL;
    TCP_InfoValue(userinfo,"password",got,sizeof(got));
    if(!strcmp(want,got))return NULL;
    print(got[0]?"TCP_NATIVE_PASSWORD rejected=wrong\n":"TCP_NATIVE_PASSWORD rejected=missing\n");
    return "Invalid password";
}
static void TCP_PasswordFrame(void){
    static int next,last=-1;if(levelTime<next&&next-levelTime<=1000)return;next=levelTime+1000;
    char pw[64];int need=TCP_PasswordRequired(pw,sizeof(pw));
    if(need!=last){last=need;SystemCall(G_CVAR_SET,"g_needpass",need?"1":"0");}
}
#endif
