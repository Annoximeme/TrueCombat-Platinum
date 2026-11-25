#!/bin/bash
# Render check: proves what a change does to the picture, frame by frame.
#
#   tools/rendercheck/render-check.sh <base> <kit folder | -> ["obj_village obj_railhouse"] ["opengl1 vulkan"]
#
# <base> is a release tag, a source zip or a source folder (as kit-gate.sh and feel-check.sh); "-" checks the base
# against itself. Both trees get the render check hook (rendercheck_hook.py) and are built as Linux clients
# (build-linux-client.sh): OpenGL 1 and the Vulkan renderer, whose frontend is the one the DX12 renderer is built on.
# Everything runs headless on a software GPU (Xvfb, Mesa llvmpipe and lavapipe).
#
# Per map, the base build records one demo of a seeded bot match while the camera visits spawn points spread over
# the map (scenes.py). Then the base plays that demo twice per renderer (if the two runs differ, the check cannot
# be trusted on that map and it fails as "not deterministic") and the kit once. Every demo frame advances exactly
# 1000/FPS ms, and every EVERY-th frame is saved, so the kit's pictures must match the base's pixel for pixel
# (apart from llvmpipe rounding noise: a few dozen pixels off by 1 or 2 levels, see compare_images.py).
# compare_images.py reports every frame that differs, with numbers and a highlighted difference picture.
#
# Env: RC_FX=1 (an explosion and an M83 on every camera spot, for particle work), RC_WEATHER (g_weather for the
#   recording, default clear), WORK (default ./render-check), DATA_TAG (game data release, default latest), DATA (game data folder, reused),
# SPOTS (camera spots per map, default 6), BOTS (default 8), SEED (default 1), FPS (default 20), EVERY (default 15),
# EXPECT=changes (a kit that is meant to change the picture: differences are reported, not failed).
# Result: $WORK/SUMMARY.md and $WORK/report/; exit 0 when every map is deterministic and (unless EXPECT=changes)
# identical.
set -uo pipefail
BASE=${1:?base tag, source zip or folder}; KITARG=${2:?kit folder or -}; MAPS=${3:-"obj_village obj_railhouse"}
RENDERERS=${4:-"opengl1 vulkan"}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
W=${WORK:-$PWD/render-check}; mkdir -p "$W"; W=$(cd "$W" && pwd); S="$W/SUMMARY.md"
SPOTS=${SPOTS:-6}; BOTS=${BOTS:-8}; SEED=${SEED:-1}; FPS=${FPS:-20}; EVERY=${EVERY:-15}; DATA=${DATA:-$W/data}
[ -e "$BASE" ] && BASE=$(cd "$(dirname "$BASE")" && pwd)/$(basename "$BASE")
if [ "$KITARG" = - ]; then KIT=""; else KIT=$(cd "$KITARG" && pwd); fi
DATA_TAG=${DATA_TAG:-$( [ -e "$BASE" ] && echo latest || echo "$BASE")}
PROTOCOL=""

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
  python3 "$HERE/rendercheck_hook.py" "$out"
}
data() {
  [ -f "$DATA/RELEASE" ] && [ "$(cat "$DATA/RELEASE")" = "$DATA_TAG" ] && return 0
  local stage; stage=$(mktemp -d); cp -r "$REPO/tools/linux-server/kit/." "$stage/"
  mkdir -p "$stage/server" "$stage/tcetest"; : > "$stage/server/platinum-server.x86_64"; : > "$stage/tcetest/qagame.mp.x86_64.so"
  "$stage/install.sh" "$DATA" "$DATA_TAG"; local rc=$?; rm -rf "$stage"; return $rc
}
game() {  # <build dir> <renderer> <home> <args...>: the client headless, game data linked into the build folder
  local b=$1 r=$2 home=$3; shift 3
  ln -sfn "$DATA/etmain" "$b/etmain"; for f in "$DATA"/tcetest/*.pk3; do ln -sf "$f" "$b/tcetest/"; done
  (cd "$b" && LIBGL_ALWAYS_SOFTWARE=1 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json timeout 900 \
    xvfb-run -a -s "-screen 0 1280x720x24" ./etl.x86_64 +set fs_basepath "$b" +set fs_homepath "$home" +set fs_game tcetest \
    +set cl_renderer "$r" +set r_mode -1 +set r_customwidth 1280 +set r_customheight 720 +set r_fullscreen 0 \
    +set s_initsound 0 +set in_mouse 0 +set com_introplayed 1 +set cl_allowdownload 0 +setu tcp_native_protocol "$PROTOCOL" "$@")
}
record() {  # <map>: base build records $W/demos/<map>.dm_84
  local map=$1 home="$W/home-rec-$1"
  rm -rf "$home"; mkdir -p "$home/tcetest" "$W/demos" "$W/logs"
  python3 "$HERE/scenes.py" "$DATA" "$map" "$SPOTS" > "$home/tcetest/rcscenes.cfg" || return 1
  game "$W/build-base" opengl1 "$home" +set sv_pure 0 +set bot_minplayers "$BOTS" +set bot_seed "$SEED" \
    +set g_weather "${RC_WEATHER:-clear}" +set sv_master1 "" +set sv_master2 "" +set sv_master3 "" +devmap "$map" +exec rcscenes.cfg \
    > "$W/logs/$map.record.log" 2>&1
  local demo; demo=$(ls "$home"/tcetest/demos/rc.dm_* 2>/dev/null | head -1)
  [ -n "$demo" ] && cp "$demo" "$W/demos/$map.${demo##*.}"
}
play() {  # <build dir> <map> <renderer> <run>  -> $W/shots/<map>/<renderer>/<run>/rc-*.png
  local b=$1 map=$2 r=$3 run=$4 home="$W/home-$4-$3-$2" demo
  demo=$(ls "$W"/demos/"$map".dm_* | head -1)
  rm -rf "$home"; mkdir -p "$home/tcetest/demos" "$W/logs"; cp "$demo" "$home/tcetest/demos/"
  game "$b" "$r" "$home" +set cl_renderCheck "$FPS" +set cl_renderCheckEvery "$EVERY" +set cl_renderCheckFrames 100000 \
    +demo "$(basename "$demo" | sed 's/\.dm_[0-9]*$//')" > "$W/logs/$map.$r.$run.log" 2>&1
  local out="$W/shots/$map/$r/$run"; rm -rf "$out"; mkdir -p "$out"
  mv "$home"/tcetest/screenshots/rc-*.png "$out/" 2>/dev/null
  [ "$(ls "$out" | wc -l)" -gt 0 ] || { echo "no frames written ($W/logs/$map.$r.$run.log)"; tail -15 "$W/logs/$map.$r.$run.log"; return 1; }
}

TITLE="base against itself"; [ -n "$KIT" ] && TITLE=$(basename "$KIT")
log "compose + build base"; compose "$W/src-base" > "$W/compose-base.log" 2>&1 \
  && "$HERE/build-linux-client.sh" "$W/src-base" "$W/build-base" > "$W/build-base.log" 2>&1 \
  || { echo "base build failed: $W/build-base.log"; tail -20 "$W/compose-base.log" "$W/build-base.log"; exit 2; }
PROTOCOL=$(grep -o '#define TCP_NATIVE_VERSION "[^"]*"' "$W/src-base/game_src/native/tcp_native.h" | cut -d'"' -f2)
CAND="$W/build-base"
if [ -n "$KIT" ]; then
  log "compose + build kit"; compose "$W/src-kit" "$KIT" > "$W/compose-kit.log" 2>&1 \
    && "$HERE/build-linux-client.sh" "$W/src-kit" "$W/build-kit" > "$W/build-kit.log" 2>&1 \
    || { echo "kit build failed: $W/build-kit.log"; tail -20 "$W/compose-kit.log" "$W/build-kit.log"; exit 2; }
  CAND="$W/build-kit"
fi
log "game data $DATA_TAG"; data > "$W/data.log" 2>&1 || { echo "game data install failed: $W/data.log"; tail -20 "$W/data.log"; exit 2; }
{ echo "# Render check: $TITLE"; echo
  echo "- Base: $(basename "$BASE"); game data $DATA_TAG; protocol $PROTOCOL"
  echo "- Maps: $MAPS; renderers: $RENDERERS (software GPU: Mesa llvmpipe / lavapipe)"
  echo "- $SPOTS camera spots per map, $BOTS bots (seed $SEED), demo at $FPS frames per second, every $EVERY-th frame compared"
  echo "- Started: $(date -u +%FT%TZ)"; echo; echo "| Map | Renderer | Frames | Base repeat | Result | Changed frames |"; echo "|---|---|---|---|---|---|"; } > "$S"
fail=0
for map in $MAPS; do
  log "$map: record"; record "$map" || { echo "| $map | | | | **FAIL** | could not record the demo |" >> "$S"; fail=1; continue; }
  for r in $RENDERERS; do
    log "$map $r: base 1"; play "$W/build-base" "$map" "$r" base1 || { echo "| $map | $r | | | **FAIL** | base did not play |" >> "$S"; fail=1; continue; }
    log "$map $r: base 2"; play "$W/build-base" "$map" "$r" base2 || { echo "| $map | $r | | | **FAIL** | base repeat did not play |" >> "$S"; fail=1; continue; }
    if [ -n "$KIT" ]; then
      log "$map $r: kit"; play "$CAND" "$map" "$r" kit || { echo "| $map | $r | | | **FAIL** | kit did not play |" >> "$S"; fail=1; continue; }
      KITRUN=kit
    else KITRUN=base2; fi
    python3 "$HERE/compare_images.py" "$W/shots/$map/$r" base1 base2 "$KITRUN" "$W/report/$map-$r" --row "$map" "$r" \
      ${EXPECT:+--expect-changes} >> "$S"; rc=$?
    [ $rc -ne 0 ] && fail=1
  done
done
echo >> "$S"
[ $fail = 0 ] && echo "**RENDER CHECK PASSED** $(date -u +%FT%TZ)" >> "$S" || echo "**RENDER CHECK FAILED** $(date -u +%FT%TZ)" >> "$S"
cat "$S"; exit $fail
