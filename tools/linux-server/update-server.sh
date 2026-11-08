#!/bin/sh
# Keeps a Linux dedicated server on the newest TrueCombat: Platinum release.
#
#   update-server.sh <server-dir> <systemd-unit> <port> [<unit> <port> ...]
#
# Run it from cron or a systemd timer, e.g. every 10 minutes. When a newer
# release has a Linux server kit it:
#   1. downloads the kit and checks it against its .sha256 file,
#   2. waits until no human players are on any listed server (bots don't count;
#      gives up for this run after MAX_WAIT seconds, default 30 minutes),
#   3. installs the release into <server-dir>/releases/<tag> and moves the
#      <server-dir>/current link to it, keeping the previous release,
#   4. restarts the listed units and checks that each answers again; if one
#      doesn't within 60 seconds, it switches back to the previous release.
#
# The units should run <server-dir>/current/start.sh with
# Environment=HOME_DIR=<server-dir>/home, so configs, logs, stats and demos
# stay in one place across releases (configs in <server-dir>/home/tcetest).
# Rollback by hand: ln -sfn releases/<old tag> <server-dir>/current, restart.
set -eu
[ $# -ge 3 ] || { sed -n '2,20p' "$0"; exit 2; }
ROOT=$1; shift
REPO=${REPO:-Annoximeme/TrueCombat-Platinum}
KIT=TrueCombat-Platinum-Linux-Server.tar.gz
MAX_WAIT=${MAX_WAIT:-1800}
KEEP=${KEEP:-3}
LOCK="$ROOT/.update.lock"
log() { echo "$(date -u +%FT%TZ) update-server: $*"; }

mkdir -p "$ROOT/releases"
exec 9>"$LOCK"
flock -n 9 || { log "another update is running"; exit 0; }

TAG=$(curl -fsSL "${GITHUB_API:-https://api.github.com}/repos/$REPO/releases/latest" |
      python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')
CUR=""
[ -f "$ROOT/current/RELEASE" ] && CUR=$(cat "$ROOT/current/RELEASE")
[ "$TAG" != "$CUR" ] || exit 0

BASE="${GITHUB_WEB:-https://github.com}/$REPO/releases/download/$TAG"
WORK="$ROOT/releases/.incoming-$TAG"
rm -rf "${WORK:?}"; mkdir -p "$WORK"
if ! curl -fsSL --retry 3 -o "$WORK/$KIT" "$BASE/$KIT"; then
  log "release $TAG has no Linux server kit yet"; rm -rf "${WORK:?}"; exit 0
fi
curl -fsSL --retry 3 -o "$WORK/$KIT.sha256" "$BASE/$KIT.sha256"
(cd "$WORK" && sha256sum -c --quiet "$KIT.sha256") || { log "checksum mismatch for $TAG"; rm -rf "${WORK:?}"; exit 1; }
log "new release $TAG (running: ${CUR:-none})"

# Wait for an empty server: getstatus lists one line per player, bots ping 0.
humans() {
  python3 - "$1" <<'PY'
import socket,sys
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(2)
try:
    s.sendto(b"\xff\xff\xff\xffgetstatus",("127.0.0.1",int(sys.argv[1])))
    lines=s.recv(65535).decode("latin-1").split("\n")[2:]
except OSError:
    print(0); sys.exit()
print(sum(1 for l in lines if l.strip() and l.split()[1:2] != ["0"]))
PY
}
waited=0
while :; do
  busy=0; i=0
  for a in "$@"; do i=$((i+1)); [ $((i%2)) -eq 0 ] && busy=$((busy + $(humans "$a"))); done
  [ "$busy" -eq 0 ] && break
  [ "$waited" -ge "$MAX_WAIT" ] && { log "$busy player(s) still on, trying again next run"; exit 0; }
  sleep 30; waited=$((waited+30))
done

tar -xzf "$WORK/$KIT" -C "$WORK"
NEW="$ROOT/releases/$TAG"
rm -rf "${NEW:?}"
# Reuse the previous release's game paks (hard links): install.sh only
# downloads the ones whose checksums changed.
mkdir -p "$NEW"
if [ -n "$CUR" ] && [ -d "$ROOT/current" ]; then
  for d in etmain tcetest; do [ -d "$ROOT/current/$d" ] && cp -al "$ROOT/current/$d" "$NEW/"; done
fi
"$WORK/linux-server/install.sh" "$NEW" "$TAG"
if [ ! -f "$ROOT/home/tcetest/server.cfg" ]; then
  mkdir -p "$ROOT/home/tcetest"; cp "$NEW/home/tcetest/server.cfg" "$ROOT/home/tcetest/server.cfg"
fi
PREV=$(readlink -f "$ROOT/current" 2>/dev/null || true)
ln -sfn "releases/$TAG" "$ROOT/current.new" && mv -T "$ROOT/current.new" "$ROOT/current"
rm -rf "${WORK:?}"

restart_all() {
  i=0; unit=""
  for a in "$@"; do
    i=$((i+1))
    if [ $((i%2)) -eq 1 ]; then unit=$a; continue; fi
    systemctl restart "$unit" 9>&-
    t=$(date +%s)
    until python3 - "$a" <<'PY'
import socket,sys
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(2)
try: s.sendto(b"\xff\xff\xff\xffgetinfo",("127.0.0.1",int(sys.argv[1]))); s.recv(4096)
except OSError: sys.exit(1)
PY
    do [ $(( $(date +%s) - t )) -ge 60 ] && return 1; sleep 2; done
    log "$unit is up on $(cat "$ROOT/current/RELEASE")"
  done
}
if ! restart_all "$@"; then
  log "a server did not come back on $TAG, switching back"
  if [ -n "$PREV" ]; then ln -sfn "$PREV" "$ROOT/current.new" && mv -T "$ROOT/current.new" "$ROOT/current"; restart_all "$@" || true; fi
  exit 1
fi
# Keep the newest $KEEP releases for rollback.
ls -1dt "$ROOT"/releases/*/ 2>/dev/null | tail -n +$((KEEP+1)) | while read -r d; do
  [ "$(readlink -f "$d")" = "$(readlink -f "$ROOT/current")" ] || rm -rf "${d:?}"
done
log "updated to $TAG"
