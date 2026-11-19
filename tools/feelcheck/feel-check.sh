#!/bin/bash
# Feel check: proves that a change leaves movement, timing and hits exactly as they were.
#
#   tools/feelcheck/feel-check.sh <base> <kit folder | -> ["obj_village obj_snow"] [seconds per map]
#
# <base> is a release tag, a source zip or a source folder (as kit-gate.sh). The kit folder holds
# patches/*.patch and optionally files/ (as kit-gate.sh); "-" checks the base against itself.
# Both trees get the trace hook (feeltrace.py, engine) and fakeclock.c (game module), are built as Linux dedicated
# servers, and play the same seeded bot match on each map with every server frame at exactly 8 ms of
# game time. The base plays twice first: if those two runs differ the test itself is not trustworthy
# on that map and it fails as "not deterministic". Then the kit build's trace must match the base
# frame for frame (positions, velocities, view angles, weapon, ammo, health, all other entities).
#
# Env: WORK (default ./feel-check), DATA_TAG (game data release, default latest), DATA (game data
# folder, reused), BOTS (default 12), SEED (default 1), PORT (default 28970).
# Result: $WORK/SUMMARY.md; exit 0 only when every map matches.
set -uo pipefail
BASE=${1:?base tag, source zip or folder}; KITARG=${2:?kit folder or -}; MAPS=${3:-"obj_village obj_snow"}; SECS=${4:-90}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
W=${WORK:-$PWD/feel-check}; mkdir -p "$W"; W=$(cd "$W" && pwd); S="$W/SUMMARY.md"
BOTS=${BOTS:-12}; SEED=${SEED:-1}; PORT=${PORT:-28970}; DATA=${DATA:-$W/data}
FRAMES=$((SECS * 128))
[ -e "$BASE" ] && BASE=$(cd "$(dirname "$BASE")" && pwd)/$(basename "$BASE")
if [ "$KITARG" = - ]; then KIT=""; else KIT=$(cd "$KITARG" && pwd); fi
DATA_TAG=${DATA_TAG:-$( [ -e "$BASE" ] && echo latest || echo "$BASE")}

log() { echo "== $*"; }
compose() {  # <out dir> [kit]
  local out=$1 kit=${2:-}
  rm -rf "$out"; mkdir -p "$out"
  if [ -f "$BASE" ]; then unzip -q "$BASE" -d "$out" || return 1
  elif [ -d "$BASE" ]; then cp -r "$BASE/." "$out/" || return 1
  else (cd "$W" && "$REPO/tools/ci/compose-source.sh" "$BASE" "$out") || return 1; fi
  if [ -d "$out/etlegacy" ] && [ ! -d "$out/reference/etlegacy" ]; then mkdir -p "$out/reference" && mv "$out/etlegacy" "$out/reference/"; fi
  if [ -n "$kit" ]; then
    for p in $(ls "$kit"/patches/*.patch 2>/dev/null | sort); do
      (cd "$out" && git apply --whitespace=nowarn "$p") || { echo "kit patch does not apply: $(basename "$p")"; return 1; }
    done
    [ -d "$kit/files" ] && cp -r "$kit/files/." "$out/"
  fi
  python3 "$HERE/feeltrace.py" "$out" || return 1
}
build() {  # <src> <out>
  GAME_EXTRA="$HERE/fakeclock.c -Wl,--wrap=clock_gettime -Wl,--wrap=time" \
    "$REPO/tools/linux-server/build-linux-server.sh" "$1" "$2"
}
data() {
  [ -f "$DATA/RELEASE" ] && [ "$(cat "$DATA/RELEASE")" = "$DATA_TAG" ] && return 0
  local stage; stage=$(mktemp -d); cp -r "$REPO/tools/linux-server/kit/." "$stage/"
  cp -r "$W/build-base/server" "$W/build-base/tcetest" "$stage/"
  "$stage/install.sh" "$DATA" "$DATA_TAG"; local rc=$?; rm -rf "$stage"; return $rc
}
play() {  # <build dir> <map> <run name>  -> $W/traces/<map>.<run>.trace
  local b=$1 map=$2 run=$3 home="$W/home-$3"
  rm -rf "$home"; mkdir -p "$W/traces" "$W/logs"
  cp "$b/server/platinum-server.x86_64" "$DATA/server/" && cp "$b/tcetest/qagame.mp.x86_64.so" "$DATA/tcetest/" || return 1
  timeout $((SECS * 2 + 120)) "$DATA/server/platinum-server.x86_64" +set dedicated 1 +set net_port "$PORT" \
    +set fs_basepath "$DATA" +set fs_homepath "$home" +set fs_game tcetest +set sv_master1 "" +set sv_master2 "" \
    +set sv_master3 "" +set sv_pure 0 +set sv_maxclients 16 +set bot_minplayers "$BOTS" +set bot_skill 3 \
    +set bot_seed "$SEED" +set sv_fps 128 +set g_weather clear +set tcp_roundtime 120 +set g_roundlimit 100 \
    +set sv_mapRotation "" +set developer 0 +set sv_feelTrace feel.trace +set sv_feelTraceFrames "$FRAMES" \
    +map "$map" > "$W/logs/$map.$run.log" 2>&1
  mv "$home/tcetest/feel.trace" "$W/traces/$map.$run.trace" 2>/dev/null || { echo "no trace written ($W/logs/$map.$run.log)"; tail -15 "$W/logs/$map.$run.log"; return 1; }
}

TITLE="base against itself"; [ -n "$KIT" ] && TITLE=$(basename "$KIT")
{ echo "# Feel check: $TITLE"; echo
  echo "- Base: $(basename "$BASE"); game data $DATA_TAG"; echo "- Maps: $MAPS, $SECS s each at 128 Hz, $BOTS bots, seed $SEED"
  echo "- Started: $(date -u +%FT%TZ)"; echo; echo "| Map | Base repeat | Result | First difference |"; echo "|---|---|---|---|"; } > "$S"
fail=0
log "compose + build base"; compose "$W/src-base" && build "$W/src-base" "$W/build-base" > "$W/build-base.log" 2>&1 || { echo "base build failed: $W/build-base.log"; tail -20 "$W/build-base.log"; exit 2; }
CAND="$W/build-base"
if [ -n "$KIT" ]; then
  log "compose + build kit"; compose "$W/src-kit" "$KIT" && build "$W/src-kit" "$W/build-kit" > "$W/build-kit.log" 2>&1 || { echo "kit build failed: $W/build-kit.log"; tail -20 "$W/build-kit.log"; exit 2; }
  CAND="$W/build-kit"
fi
log "game data $DATA_TAG"; data > "$W/data.log" 2>&1 || { echo "game data install failed: $W/data.log"; tail -20 "$W/data.log"; exit 2; }
for map in $MAPS; do
  log "$map: base run 1"; play "$W/build-base" "$map" base1 || { echo "| $map | | **FAIL** | server did not run (base) |" >> "$S"; fail=1; continue; }
  log "$map: base run 2"; play "$W/build-base" "$map" base2 || { echo "| $map | | **FAIL** | server did not run (base repeat) |" >> "$S"; fail=1; continue; }
  if ! python3 "$HERE/compare.py" "$W/traces/$map.base1.trace" "$W/traces/$map.base2.trace" --md "$W/$map.repeat.md"; then
    echo "| $map | **not deterministic** | **FAIL** | $(head -1 "$W/$map.repeat.md" | tr '|' '/') |" >> "$S"; fail=1; continue
  fi
  run=base2
  if [ -n "$KIT" ]; then log "$map: kit run"; play "$CAND" "$map" kit || { echo "| $map | identical | **FAIL** | server did not run (kit) |" >> "$S"; fail=1; continue; }; run=kit; fi
  if python3 "$HERE/compare.py" "$W/traces/$map.base1.trace" "$W/traces/$map.$run.trace" --md "$W/$map.md"; then
    echo "| $map | identical | pass | none in $((FRAMES)) frames |" >> "$S"
  else
    echo "| $map | identical | **FAIL** | $(grep -v '^$' "$W/$map.md" | head -4 | tr '|' '/' | paste -sd ' ' -) |" >> "$S"; fail=1
  fi
done
{ echo; [ $fail = 0 ] && echo "**FEEL CHECK PASSED** $(date -u +%FT%TZ)" || echo "**FEEL CHECK FAILED** $(date -u +%FT%TZ)"; } >> "$S"
cat "$S"; exit $fail
