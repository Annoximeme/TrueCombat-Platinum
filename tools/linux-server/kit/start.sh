#!/bin/sh
# Starts the server in the foreground. Port: PORT=27961 ./start.sh
# HOME_DIR moves configs, logs, stats and demos out of the install folder.
# IPV6=1 also listens on IPv6 (same port) and lists the server over IPv6 too.
cd "$(dirname "$0")"
NET_ENABLED=1
[ "${IPV6:-0}" = 1 ] && NET_ENABLED=3
exec ./server/platinum-server.x86_64 +set dedicated 2 +set net_port "${PORT:-27960}" \
  +set net_enabled "$NET_ENABLED" +set net_port6 "${PORT:-27960}" \
  +set fs_basepath "$PWD" +set fs_homepath "${HOME_DIR:-$PWD/home}" +set fs_game tcetest \
  +set sv_master1 master.truecombat.eu:27950 +set sv_master2 "" +set sv_master3 "" \
  +exec "${CONFIG:-server.cfg}"
