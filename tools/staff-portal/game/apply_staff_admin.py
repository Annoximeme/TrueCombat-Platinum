#!/usr/bin/env python3
"""Adds the staff portal commands to a game_src tree (tcp_staff_admin.h + three hooks in tcp_game.c).

    python apply_staff_admin.py <path to game_src>          apply (idempotent)
    python apply_staff_admin.py <path to game_src> --check  only report whether every anchor is found

Anchors, not line numbers, so it applies to 0.35.0 and later trees. Keeps the file's own line endings."""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOKS = [
    ('#include "tcp_report.h"{nl}', '#include "tcp_report.h"{nl}#include "tcp_staff_admin.h" /* TCP_STAFF_ADMIN: staff portal commands */{nl}'),
    ('if(TCP_StaffCommand(n,cmd))return 0;', 'if(TCP_StaffCommand(n,cmd))return 0;if(TCP_StaffMuteFilter(n,cmd))return 0;'),
    ('case GAME_CONSOLE_COMMAND:{char cmd[64];SystemCall(G_ARGV,0,cmd,sizeof(cmd));',
     'case GAME_CONSOLE_COMMAND:{char cmd[64];SystemCall(G_ARGV,0,cmd,sizeof(cmd));if(TCP_StaffAdminConsole(cmd))return 1;'),
]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    native = Path(sys.argv[1]) / "native"
    game = native / "tcp_game.c"
    text = game.read_bytes().decode("latin-1")
    nl = "\r\n" if "\r\n" in text else "\n"
    if "TCP_STAFF_ADMIN" in text:
        print("already applied")
        return
    missing = [a for a, _ in HOOKS if text.count(a.replace("{nl}", nl)) != 1]
    if missing:
        raise SystemExit("anchor not found exactly once: %s" % missing)
    if "--check" in sys.argv:
        print("all anchors found")
        return
    for anchor, new in HOOKS:
        text = text.replace(anchor.replace("{nl}", nl), new.replace("{nl}", nl))
    game.write_bytes(text.encode("latin-1"))
    shutil.copyfile(HERE / "tcp_staff_admin.h", native / "tcp_staff_admin.h")
    print("applied: tcp_game.c (3 hooks) + tcp_staff_admin.h")


if __name__ == "__main__":
    main()
