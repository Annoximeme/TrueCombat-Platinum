"""Applies the join-password check to game_src/native/tcp_game.c (anchored, CRLF-safe).
usage: python apply_join_password.py <path to game_src>  (copies tcp_password.h next to tcp_game.c)"""
import pathlib, shutil, sys
src = pathlib.Path(sys.argv[1]) / "native"
here = pathlib.Path(__file__).resolve().parent
shutil.copyfile(here / "tcp_password.h", src / "tcp_password.h")
p = src / "tcp_game.c"
s = p.read_bytes().decode("latin-1")
nl = "\r\n" if "\r\n" in s else "\n"
edits = [
    ('#include "tcp_report.h"', '#include "tcp_report.h"' + nl + '#include "tcp_password.h"'),
    ('older native builds and RC8 cannot join.";',
     'older native builds and RC8 cannot join.";' + nl +
     '        {const char *deny=TCP_PasswordCheck(values,(int)a1,(int)a2);if(deny)return (intptr_t)deny;}'),
    ('TCP_AfkFrame();', 'TCP_AfkFrame();TCP_PasswordFrame();'),
    ('SystemCall(G_CVAR_REGISTER,NULL,"gamename",TCP_NATIVE_VERSION,CVAR_SERVERINFO|CVAR_ROM);',
     'SystemCall(G_CVAR_REGISTER,NULL,"gamename",TCP_NATIVE_VERSION,CVAR_SERVERINFO|CVAR_ROM);TCP_PasswordInit();'),
]
for old, new in edits:
    n = s.count(old)
    if n != 1:
        sys.exit("anchor found %d times: %s" % (n, old[:60]))
    s = s.replace(old, new)
p.write_bytes(s.encode("latin-1"))
print("join password applied")
