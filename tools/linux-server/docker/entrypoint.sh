#!/bin/sh
# First start: fetch and verify the game data into /data, write server.cfg from the
# environment. Later starts: only refresh the binaries from the image. Your own edits to
# /data/home/tcetest/server.cfg are never overwritten (delete the file to regenerate it).
set -eu
DATA=${DATA_DIR:-/data}
"${KIT_DIR:-/opt/kit}/install.sh" "$DATA" "${RELEASE:-$(cat "${KIT_DIR:-/opt/kit}/RELEASE" 2>/dev/null || echo latest)}"
CFG="$DATA/home/tcetest/server.cfg"
if [ ! -f "$DATA/home/tcetest/.generated" ] || [ "${REGENERATE_CONFIG:-0}" = 1 ]; then
  clean() { printf '%s' "$1" | tr -d '"\;\r\n' | cut -c1-"${2:-64}"; }
  cat > "$CFG" <<CFG
// Written from the container environment. Edit freely; delete .generated to rewrite it from the environment.
set sv_hostname "$(clean "${SERVER_NAME:-TrueCombat: Platinum community server}")"
set sv_maxclients ${MAX_PLAYERS:-16}
set rconpassword "$(clean "${RCON_PASSWORD:-}" 40)"
set g_password "$(clean "${SERVER_PASSWORD:-}" 32)"
set sv_pure 0
set tcp_native_rounds ${MODE:-2}
set tcp_roundtime ${ROUND_TIME:-300}
set g_roundlimit ${ROUND_LIMIT:-10}
set sv_mapRotationTime ${MAP_TIME:-20}
set sv_mapRotation "$(clean "${MAP_ROTATION:-obj_village obj_railhouse obj_snow obj_delta obj_northport obj_stadtrand}" 400)"
set sv_fps 40
set g_antilag 1
set sv_timeout 20
set bot_minplayers ${BOTS:-0}
set bot_skill ${BOT_SKILL:-3}
set g_maxPing ${MAX_PING:-0}
set sv_autoDemo ${RECORD_DEMOS:-0}
$( [ -n "${DOWNLOAD_URL:-}" ] && printf 'set sv_wwwBaseURL "%s"\nset sv_wwwDownload 1\nset sv_allowDownload 1\n' "$(clean "$DOWNLOAD_URL" 200)" )
$( [ "${LIST_PUBLICLY:-1}" = 1 ] || printf 'set sv_master1 ""\n' )
map $(clean "${START_MAP:-obj_village}" 48)
CFG
  : > "$DATA/home/tcetest/.generated"
  echo "server.cfg written from the environment"
fi
export HOME_DIR="$DATA/home"
exec "$DATA/start.sh"
