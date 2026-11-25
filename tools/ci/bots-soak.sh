#!/bin/bash
# Headless bots-only soak test of a Linux server build: each map runs with a full
# server of bots for a few minutes; fails on a crash, a fatal error, a server that
# stops answering, or bots that never join.
#   tools/ci/bots-soak.sh <linux build dir> <base tag for game data> "<maps>" <minutes per map>
# Env: BOTS (default 12), EXTRA (extra +set arguments), DATA (game data folder, reused if present),
#      PARALLEL (maps soaked at once, default: all of them; 1 = one after another). Each map gets its own
#      server, port and home folder; the CPU figures stay per server.
set -euo pipefail
BUILD=$(cd "$1" && pwd); TAG=$2; MAPS=$3; MINUTES=${4:-4}
HERE=$(cd "$(dirname "$0")" && pwd); KIT="$HERE/../linux-server/kit"
DATA=${DATA:-$PWD/soak-data}; LOGS=${LOGS:-$PWD/soak-logs}; BOTS=${BOTS:-12}; PORT=${PORT:-28960}
mkdir -p "$LOGS"; SUMMARY="$LOGS/summary.md"
echo "| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |" > "$SUMMARY"; echo "|---|---|---|---|---|---|---|---|" >> "$SUMMARY"

# Game data from the base release (verified by install.sh), then this build's binaries.
STAGE=$(mktemp -d); cp -r "$KIT/." "$STAGE/"; cp -r "$BUILD/server" "$BUILD/tcetest" "$STAGE/"
"$STAGE/install.sh" "$DATA" "$TAG" > "$LOGS/install.log" 2>&1 || { tail -20 "$LOGS/install.log"; exit 1; }
rm -rf "$STAGE"

ticks() { awk '{print $14+$15}' "/proc/$1/stat" 2>/dev/null || echo 0; }   # utime+stime of the server, in clock ticks
HZ=$(getconf CLK_TCK)
status() {  # status <port>; prints: <answered 0/1> <player count>
  python3 - "$1" <<'PY'
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(3)
try:
    s.sendto(b"\xff\xff\xff\xffgetstatus", ("127.0.0.1", int(sys.argv[1])))
    lines = s.recv(65535).decode("latin-1").split("\n")[2:]
    print(1, sum(1 for l in lines if l.strip()))
except OSError:
    print(0, 0)
PY
}

soak_map() {  # soak_map <map> <port>: one server, writes $LOGS/<map>.row and exits 1 on a failure
  local map=$1 port=$2 log="$LOGS/$1.log" home="$LOGS/home-$1"
  rm -rf "$home"; cp -r "$DATA/home" "$home"
  # shellcheck disable=SC2086
  "$DATA/server/platinum-server.x86_64" +set dedicated 1 +set net_port "$port" +set fs_basepath "$DATA" \
    +set fs_homepath "$home" +set fs_game tcetest +set sv_master1 "" +set sv_master2 "" +set sv_master3 "" \
    +set sv_pure 0 +set sv_maxclients 16 +set bot_minplayers "$BOTS" +set bot_skill 3 +set sv_fps 40 \
    +set tcp_roundtime 120 +set g_roundlimit 100 +set sv_mapRotation "" +set developer 0 ${EXTRA:-} \
    +map "$map" > "$log" 2>&1 &
  local pid=$!
  local end=$((SECONDS + MINUTES * 60)) seen=0 answered=0 silent=0 note="" ok n t0 t1 w0 w1 pct cpu_sum cpu_n cpu_max
  local cpu bad hits spawns res
  sleep 20
  # server CPU (one core = 100 %) per 15 s window: the 0.38.0 release spent an hour on the PC chasing a
  # 16-bot CPU burst; this records the same numbers on every soak, off the release's critical path
  t0=$(ticks $pid); w0=$(date +%s%N); cpu_sum=0; cpu_n=0; cpu_max=0
  while [ $SECONDS -lt $end ]; do
    if ! kill -0 $pid 2>/dev/null; then note="server exited"; break; fi
    read -r ok n < <(status "$port")
    if [ "$ok" = 1 ]; then answered=$((answered+1)); silent=0; [ "$n" -gt "$seen" ] && seen=$n
    else silent=$((silent+1)); [ $silent -ge 4 ] && { note="stopped answering for 60 s"; break; }; fi
    sleep 15
    t1=$(ticks $pid); w1=$(date +%s%N)
    if [ "$t1" -gt 0 ]; then
      pct=$(( (t1 - t0) * 100 * 1000000000 / HZ / (w1 - w0 > 0 ? w1 - w0 : 1) ))
      cpu_sum=$((cpu_sum + pct)); cpu_n=$((cpu_n + 1)); [ $pct -gt $cpu_max ] && cpu_max=$pct
    fi
    t0=$t1; w0=$w1
  done
  cpu="n/a"; [ $cpu_n -gt 0 ] && cpu="$((cpu_sum / cpu_n)) % / ${cpu_max} %"
  if kill -0 $pid 2>/dev/null; then kill $pid; wait $pid 2>/dev/null || true; else wait $pid 2>/dev/null || true; fi
  # our own stop is signal 15; anything else fatal counts
  bad=$(sed 's/\x1b\[[0-9;]*m//g' "$log" | grep -P -i -m3 "Sys_Error|Segmentation|Received signal (?!15\b)|^\s*\d*\s*ERROR:|Fatal|Assertion" | tr '|' '/' | tr '\n' ' ' || true)
  hits=$(grep -c "TCP_NATIVE_HIT" "$log" || true); spawns=$(grep -c "TCP_NATIVE_SPAWN" "$log" || true)
  [ "$hits" -lt 1 ] && note="$note no combat"
  [ -n "$bad" ] && note="$note $bad"
  [ "$seen" -lt 2 ] && note="$note bots did not join"
  if [ -n "$note" ]; then res=FAIL; else res=pass; fi
  echo "| $map | $res | $seen | ${answered}x | $hits | $spawns | $cpu | ${note:-} |" > "$LOGS/$map.row"
  echo "== $map: $res (bots $seen, server CPU $cpu) ${note:-}"
  rm -rf "$home"
  [ $res = pass ]
}

fail=0; i=0; pids=()
nmaps=$(echo $MAPS | wc -w); PARALLEL=${PARALLEL:-$nmaps}
for map in $MAPS; do
  rm -f "$LOGS/$map.row"
  soak_map "$map" $((PORT + i * 10)) & pids+=($!); i=$((i + 1))
  if [ ${#pids[@]} -ge "$PARALLEL" ]; then wait "${pids[0]}" || fail=1; pids=("${pids[@]:1}"); fi
done
for pid in "${pids[@]}"; do wait "$pid" || fail=1; done
for map in $MAPS; do
  if [ -f "$LOGS/$map.row" ]; then cat "$LOGS/$map.row" >> "$SUMMARY"
  else echo "| $map | FAIL | | | | | | soak did not finish |" >> "$SUMMARY"; fail=1; fi
done
cat "$SUMMARY"
exit $fail
