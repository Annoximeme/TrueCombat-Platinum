#!/bin/bash
# Cross-compiles the full Windows x64 game from a source snapshot on Linux,
# with the same LLVM-MinGW release and flags as the PC candidate build
# (analysis_scripts/integration/build_candidate.py). Compile check only:
# nothing here packages, signs or publishes.
#
#   tools/ci/build-windows.sh <unpacked source> <out dir>
#
# Environment:
#   LLVM_MINGW   LLVM-MinGW root (bin/x86_64-w64-mingw32-clang)          required
#   EOS_INCLUDE  EOS SDK Include folder; without it EAC support is off       optional
#   SL_SDK       Streamline SDK folder (include/); without it DLSS is off    optional
#   RUN_PROBES   1 = run the native probes under wine (default 1 if wine exists)
#   JOBS         parallel jobs (default: nproc)
#   QUIET        1 = never print compiler output (public CI logs of unreleased code)
#   ENGINE_CMAKE_EXTRA  extra engine CMake flags, e.g. -DFEATURE_PROFILER=ON for a development build
#   BUILD_CACHE  ccache folder shared between builds (default: off); same sources in another folder still hit
#
# Accepts both source layouts: a release source snapshot, and a checkout of the development repository, where
# the shipped renderer files listed in analysis_scripts/dlss/patch-manifest.json live in
# experiments/dlss/source/ and are copied into the engine first, as the PC candidate build does.
set -euo pipefail
SRC=$(cd "$1" && pwd); OUT=$(mkdir -p "$2" && cd "$2" && pwd)
: "${LLVM_MINGW:?set LLVM_MINGW}"
CC="$LLVM_MINGW/bin/x86_64-w64-mingw32-clang"
JOBS=${JOBS:-$(nproc)}
E="$SRC/reference/etlegacy"; G="$SRC/game_src"; R="$SRC/release_src"
BUILD="$OUT/build"; GAME="$OUT/game"; LOGS="$OUT/logs"; PROBES="$OUT/probes"
mkdir -p "$BUILD" "$GAME/engine" "$GAME/tcetest" "$LOGS" "$PROBES"
SUMMARY="$OUT/summary.md"; : > "$SUMMARY"
if [ -z "${RUN_PROBES:-}" ]; then command -v wine >/dev/null && RUN_PROBES=1 || RUN_PROBES=0; fi

step() {  # step <label> <command...>: quiet log per step, tail on failure
  local label=$1; shift
  local t0=$SECONDS
  if "$@" > "$LOGS/$label.log" 2>&1; then
    echo "| $label | pass | $((SECONDS-t0)) s |" >> "$SUMMARY"; echo "== $label passed ($((SECONDS-t0)) s)"
  else
    echo "| $label | **FAIL** | $((SECONDS-t0)) s |" >> "$SUMMARY"; echo "== $label FAILED"
    if [ "${QUIET:-0}" = 1 ]; then echo "(log kept in logs/$label.log, not printed)"; else tail -n 60 "$LOGS/$label.log"; fi
    exit 1
  fi
}
echo "| Step | Result | Time |" >> "$SUMMARY"; echo "|---|---|---|" >> "$SUMMARY"

# Toolchain file for this host (the snapshot's own one expects Windows .exe paths).
TC="$BUILD/llvm-mingw-x64.cmake"
cat > "$TC" <<CMAKE
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)
set(CMAKE_C_COMPILER "$LLVM_MINGW/bin/x86_64-w64-mingw32-clang")
set(CMAKE_CXX_COMPILER "$LLVM_MINGW/bin/x86_64-w64-mingw32-clang++")
set(CMAKE_RC_COMPILER "$LLVM_MINGW/bin/x86_64-w64-mingw32-windres")
set(CMAKE_AR "$LLVM_MINGW/bin/llvm-ar")
set(CMAKE_RANLIB "$LLVM_MINGW/bin/llvm-ranlib")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-static")
CMAKE

# Windows headers are case-insensitive, the Linux file system is not: map includes
# such as <Softpub.h> onto LLVM-MinGW's lower-case headers.
SHIM="$BUILD/case-shim"; mkdir -p "$SHIM"
python3 - "$LLVM_MINGW/x86_64-w64-mingw32/include" "$SHIM" "$SRC" ${SL_SDK:+"$SL_SDK/include"} <<'PY'
import os, re, sys
inc, shim, roots = sys.argv[1], sys.argv[2], sys.argv[3:]
have = {}
for d, _, files in os.walk(inc):
    for f in files:
        rel = os.path.relpath(os.path.join(d, f), inc).replace(os.sep, '/')
        have.setdefault(rel.lower(), rel)
want = set()
pat = re.compile(rb'#\s*include\s*[<"]([^>"]+)[>"]')
for root in roots:
    for d, _, files in os.walk(root):
        for f in files:
            if f.endswith(('.c', '.cpp', '.h', '.hpp', '.inl', '.rc')):
                try: data = open(os.path.join(d, f), 'rb').read()
                except OSError: continue
                want.update(m.decode('latin-1').replace('\\', '/') for m in pat.findall(data))
n = 0
for name in sorted(want):
    real = have.get(name.lower())
    if real and real != name and not os.path.exists(os.path.join(inc, name)):
        link = os.path.join(shim, name); os.makedirs(os.path.dirname(link), exist_ok=True)
        if not os.path.lexists(link): os.symlink(os.path.join(inc, real), link); n += 1
print(f'case shim: {n} headers')
PY
cat >> "$TC" <<CMAKE
set(CMAKE_C_FLAGS_INIT "-idirafter $SHIM")
set(CMAKE_CXX_FLAGS_INIT "-idirafter $SHIM")
CMAKE

# Snapshot fix-ups, the same ones build_candidate.py makes in its frozen copy.
# Source snapshots up to 0.37.3 leave out the engine icon the .rc file needs.
[ -f "$E/misc/platinum.ico" ] || { mkdir -p "$E/misc"; cp "$(dirname "$0")/platinum.ico" "$E/misc/platinum.ico"; echo "note: engine icon missing from snapshot, used tools/ci/platinum.ico" | tee -a "$OUT/options.txt"; }
# The installer's artwork header is generated: build_setup.py on the PC regenerates it when it is missing (a kit
# that changes release_src/setup_art deletes it), so do the same here.
if [ ! -f "$R/platinum_setup_art.h" ] && [ -f "$SRC/analysis_scripts/make_setup_art.py" ]; then
  python3 "$SRC/analysis_scripts/make_setup_art.py" > /dev/null && echo "note: platinum_setup_art.h regenerated from release_src/setup_art" | tee -a "$OUT/options.txt"
fi
# Development repository layout: put the shipped renderer files into the engine tree (build_candidate.py does
# the same). A release snapshot already has them in place and has no experiments/ folder.
DLSS_PRIVATE="$SRC/experiments/dlss/source"; DLSS_MANIFEST="$SRC/analysis_scripts/dlss/patch-manifest.json"
if [ -d "$DLSS_PRIVATE/src" ] && [ -f "$DLSS_MANIFEST" ]; then
  n=0
  for f in $(python3 -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["files"]))' "$DLSS_MANIFEST"); do
    [ -f "$DLSS_PRIVATE/$f" ] || { echo "repo layout: $f missing from experiments/dlss/source" >&2; exit 1; }
    mkdir -p "$(dirname "$E/$f")"; cp "$DLSS_PRIVATE/$f" "$E/$f"; n=$((n + 1))
  done
  echo "note: development repository layout, $n renderer files taken from experiments/dlss/source" | tee -a "$OUT/options.txt"
fi
CACHE_FLAGS=()
if [ -n "${BUILD_CACHE:-}" ] && command -v ccache >/dev/null; then
  mkdir -p "$BUILD_CACHE"
  # paths under the common parent of source and output are hashed relative, so another work folder still hits
  export CCACHE_DIR="$BUILD_CACHE" CCACHE_NOHASHDIR=1
  CCACHE_BASEDIR=$(python3 -c 'import os,sys; print(os.path.commonpath(sys.argv[1:]))' "$SRC" "$OUT"); export CCACHE_BASEDIR CCACHE_MAXSIZE=${CCACHE_MAXSIZE:-5G}
  CACHE_FLAGS=(-DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache)
  ccache -z >/dev/null
fi
DLSS=OFF
if [ -n "${SL_SDK:-}" ] && [ -f "$SRC/analysis_scripts/dlss/overlay.cmake" ]; then
  DLSS=ON
  printf 'set(TCP_DLSS_SOURCE "%s")\nset(TCP_DLSS_SDK "%s")\ninclude("%s")\n' \
    "$E" "$SL_SDK" "$SRC/analysis_scripts/dlss/overlay.cmake" > "$E/cmake/ETLPlatinumDLSS.cmake"
fi
EAC=OFF; EOS_FLAGS=()
if [ -n "${EOS_INCLUDE:-}" ] && [ -f "$EOS_INCLUDE/eos_sdk.h" ]; then
  EAC=ON; mkdir -p "$BUILD/eos"; ln -sfn "$EOS_INCLUDE" "$BUILD/eos/Include"
  EOS_FLAGS=(-DFEATURE_EAC=ON "-DEOS_SDK_DIR=$BUILD/eos")
fi
echo "Options: DLSS=$DLSS EAC=$EAC probes=$RUN_PROBES jobs=$JOBS cache=${CACHE_FLAGS:+on}" | tee -a "$OUT/options.txt"

# OpenAL Soft (engine/OpenAL64.dll at run time).
step openal-configure cmake -S "$E/libs/openal" -B "$BUILD/openal" -G Ninja -DCMAKE_TOOLCHAIN_FILE="$TC" "${CACHE_FLAGS[@]}" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release -DLIBTYPE=SHARED -DALSOFT_UTILS=OFF \
  -DALSOFT_NO_CONFIG_UTIL=ON -DALSOFT_EXAMPLES=OFF -DALSOFT_TESTS=OFF -DALSOFT_CONFIG=OFF \
  -DALSOFT_HRTF_DEFS=OFF -DALSOFT_AMBDEC_PRESETS=OFF -DALSOFT_INSTALL=OFF -DALSOFT_BUILD_IMPORT_LIB=OFF \
  "-DCMAKE_SHARED_LINKER_FLAGS=-static -Wl,--no-insert-timestamp"
step openal-build cmake --build "$BUILD/openal" --parallel "$JOBS"

# Engine: client, dedicated server, DX12 + OpenGL renderers, native UI.
step engine-configure cmake -S "$E" -B "$BUILD/engine" -G Ninja -DCMAKE_TOOLCHAIN_FILE="$TC" "${CACHE_FLAGS[@]}" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_POLICY_VERSION_MINIMUM=3.10 \
  -DBUILD_CLIENT=ON -DBUILD_SERVER=ON -DBUILD_MOD=ON -DBUILD_CLIENT_MOD=ON -DBUILD_SERVER_MOD=OFF -DBUILD_MOD_PK3=OFF \
  -DFEATURE_RENDERER1=ON -DFEATURE_RENDERER2=OFF -DFEATURE_RENDERER_DX12=ON -DFEATURE_RENDERER_DLSS=$DLSS \
  -DFEATURE_RENDERER_VULKAN=OFF -DRENDERER_DYNAMIC=ON -DFEATURE_CURL=OFF -DFEATURE_SSL=OFF -DFEATURE_AUTH=OFF \
  -DFEATURE_AUTOUPDATE=OFF -DFEATURE_THEORA=OFF -DFEATURE_OPENAL=ON -DBUNDLED_OPENAL=OFF \
  "-DOPENAL_INCLUDE_DIR=$E/libs/openal/include" "-DOPENAL_LIBRARY=$BUILD/openal/libOpenAL32.dll.a" \
  -DFEATURE_OGG_VORBIS=ON -DFEATURE_LUA=OFF -DFEATURE_LUAJIT=OFF -DFEATURE_OMNIBOT=OFF -DINSTALL_EXTRA=OFF \
  -DFEATURE_WINDOWS_CONSOLE=ON -DFEATURE_WINDOWS_PDB=ON -DCROSS_COMPILE32=OFF "${EOS_FLAGS[@]}" ${ENGINE_CMAKE_EXTRA:-}
step engine-build cmake --build "$BUILD/engine" --parallel "$JOBS" --target etl etlded renderer_dx12 renderer1 ui

# Game modules, probes, launcher, installer, master server: same flags as the PC.
COMMON=(-std=gnu11 -O2 -g -static -Wall -Wextra -Werror -Wno-unused-parameter -Wl,--no-insert-timestamp -gcodeview -Wl,--pdb=)
COMBAT=("$G/native/tcp_native_combat.c" "$G/native/tcp_aim.c")
for n in tcp_weapon tcp_inventory tcp_inventory_apply tcp_ballistics tcp_ammo tcp_firing tcp_spread tcp_shotgun \
         tcp_specs tcp_weapon_rules tcp_damage tcp_math tcp_regions tcp_penetration; do COMBAT+=("$G/shared/$n.c"); done
COMBAT+=("$G/native/monocypher/monocypher.c" "$G/native/monocypher/monocypher-ed25519.c")
for m in qagame cgame; do
  step "$m-build" "$CC" "${COMMON[@]}" -shared -DMODLIB -I "$E/src" "$G/native/tcp_$( [ $m = qagame ] && echo game || echo cgame ).c" \
    "$G/native/tcp_move.c" "$G/native/tcp_lagpredict.c" "${COMBAT[@]}" -o "$GAME/tcetest/${m}_mp_x64.dll"
done
probe() {  # probe <name> <sources...>
  local name=$1; shift
  step "$name-probe-build" "$CC" "${COMMON[@]}" "$@" -o "$PROBES/native-$name-probe.exe"
  if [ "$RUN_PROBES" = 1 ]; then step "$name-probe" wine "$PROBES/native-$name-probe.exe"; fi
}
probe move -DMODLIB -I "$E/src" "$G/tests/native_move_probe.c" "$G/native/tcp_move.c"
probe combat "$G/tests/native_combat_probe.c" "${COMBAT[@]}"
[ -f "$G/tests/native_prediction_probe.c" ] && probe prediction "$G/tests/native_prediction_probe.c"
[ -f "$G/tests/native_entity_lifecycle_probe.c" ] && probe entity-lifecycle "$G/tests/native_entity_lifecycle_probe.c"
[ -f "$G/tests/native_content_probe.c" ] && probe content -DMODLIB -I "$E/src" "$G/tests/native_content_probe.c" "$G/native/tcp_move.c"
WINLIBS=(-luser32 -lgdi32 -lshell32 -lws2_32 -lbcrypt -lgdiplus -lshlwapi -lole32 -ldwmapi)
step launcher-build "$CC" -municode -O2 -Wall -Wextra -Werror -static -Wl,--subsystem,windows -Wl,--no-insert-timestamp \
  -DPLATINUM_NATIVE=1 -I "$G/native" "$R/platinum_launcher.c" -o "$GAME/TrueCombatPlatinum.exe" "${WINLIBS[@]}"
step installer-build "$CC" -municode -O2 -Wall -Wextra -static -Wl,--subsystem,windows -Wl,--no-insert-timestamp \
  -I "$G/native" "$R/platinum_setup.c" -o "$OUT/TrueCombat-Platinum-Setup-uncompressed.exe" "${WINLIBS[@]}" -luuid -lcomctl32 -lwininet -lwinhttp -lcrypt32 -lwintrust
[ -f "$R/platinum_master.c" ] && step master-build "$CC" -O2 -Wall -Wextra "$R/platinum_master.c" -o "$OUT/platinum-master.exe" -lws2_32 -lbcrypt

# Collect what the PC candidate ships from this build.
for f in etl.exe etlded.exe renderer_dx12_x64.dll renderer_opengl1_x64.dll; do
  cp "$BUILD/engine/$f" "$GAME/engine/" 2>/dev/null || { echo "missing $f" | tee -a "$SUMMARY"; exit 1; }
done
cp "$BUILD/openal/OpenAL32.dll" "$GAME/engine/OpenAL64.dll"
cp "$(find "$BUILD/engine" -name ui_mp_x64.dll | head -1)" "$GAME/tcetest/"
( cd "$OUT" && find game probes -type f \( -name '*.exe' -o -name '*.dll' \) -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt )
CACHE_NOTE=""
if [ ${#CACHE_FLAGS[@]} -gt 0 ]; then
  CACHE_NOTE=", cache $(ccache --print-stats 2>/dev/null | awk -F'\t' '/^direct_cache_hit|^preprocessed_cache_hit/{h+=$2} /^cache_miss/{m+=$2} END{printf "%d hits / %d misses", h, m}')"
fi
{ echo; echo "Options: DLSS=$DLSS, EAC=$EAC, probes run=$RUN_PROBES$CACHE_NOTE"; echo; echo '```'; cat "$OUT/SHA256SUMS.txt"; echo '```'; } >> "$SUMMARY"
echo "All Windows builds passed."
