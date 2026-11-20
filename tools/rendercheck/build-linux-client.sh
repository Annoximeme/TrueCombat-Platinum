#!/bin/bash
# Builds a Linux client for the render check (never shipped): engine (with the render check hook),
# OpenGL 1 and Vulkan renderers (the Vulkan one is the frontend the DX12 renderer is built on), the UI module,
# and the native cgame and qagame. Windows-only cgame calls are stubbed (linux-shim.h, linux-stubs.c).
#
#   tools/rendercheck/build-linux-client.sh <source tree with the hook> <out dir>
#
# Needs: clang, cmake, ninja, SDL2, GLEW, Vulkan headers and glslang, OpenAL, cJSON, freetype, jpeg, png, minizip.
set -euo pipefail
SRC=$(cd "$1" && pwd); OUT=$(mkdir -p "$2" && cd "$2" && pwd); HERE=$(cd "$(dirname "$0")" && pwd)
E="$SRC/reference/etlegacy"; G="$SRC/game_src"
mkdir -p "$OUT/tcetest"
cmake -S "$E" -B "$OUT/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_CLIENT=ON -DBUILD_SERVER=OFF -DBUILD_MOD=ON -DBUILD_CLIENT_MOD=ON -DBUILD_SERVER_MOD=OFF -DBUILD_MOD_PK3=OFF \
  -DBUNDLED_LIBS=OFF -DFEATURE_RENDERER1=ON -DFEATURE_RENDERER_VULKAN=ON -DFEATURE_CURL=OFF -DFEATURE_SSL=OFF \
  -DFEATURE_AUTH=OFF -DFEATURE_AUTOUPDATE=OFF -DFEATURE_LUA=OFF -DFEATURE_OMNIBOT=OFF -DFEATURE_DBMS=OFF \
  -DFEATURE_THEORA=OFF -DFEATURE_OGG_VORBIS=OFF -DFEATURE_IRC_CLIENT=OFF -DINSTALL_EXTRA=OFF -DCROSS_COMPILE32=OFF \
  -DFEATURE_IPV6=OFF ${ENGINE_CMAKE_EXTRA:-} > "$OUT/configure.log"
cmake --build "$OUT/build" --target etl renderer1 renderer_vulkan ui > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 1; }
cp "$OUT/build/etl.x86_64" "$OUT/build/"librenderer_*.so "$OUT/"
cp "$OUT/build/legacy/ui.mp.x86_64.so" "$OUT/tcetest/"
COMBAT=("$G/native/tcp_native_combat.c" "$G/native/tcp_aim.c")
for n in tcp_weapon tcp_inventory tcp_inventory_apply tcp_ballistics tcp_ammo tcp_firing tcp_spread tcp_shotgun \
         tcp_specs tcp_weapon_rules tcp_damage tcp_math tcp_regions tcp_penetration; do COMBAT+=("$G/shared/$n.c"); done
COMBAT+=("$G/native/monocypher/monocypher.c" "$G/native/monocypher/monocypher-ed25519.c")
for m in qagame cgame; do
  clang -std=gnu11 -O2 -g -w -shared -fPIC -fvisibility=hidden -DMODLIB -include "$HERE/linux-shim.h" -I "$E/src" \
    "$G/native/tcp_$( [ $m = qagame ] && echo game || echo cgame ).c" "$G/native/tcp_move.c" "$G/native/tcp_lagpredict.c" \
    "${COMBAT[@]}" "$HERE/linux-stubs.c" -lm -Wl,-z,defs -o "$OUT/tcetest/$m.mp.x86_64.so"
done
echo "built: $OUT"
