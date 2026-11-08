#!/bin/sh
# Builds the native Linux dedicated server from a release's source snapshot.
#   tools/linux-server/build-linux-server.sh <unpacked source dir> <out dir>
# Output: <out>/server/platinum-server.x86_64 and <out>/tcetest/qagame.mp.x86_64.so
set -eu
SRC=$(cd "$1" && pwd); OUT=$(mkdir -p "$2" && cd "$2" && pwd)
E="$SRC/reference/etlegacy"; G="$SRC/game_src"
mkdir -p "$OUT/server" "$OUT/tcetest" "$OUT/build"
cmake -S "$E" -B "$OUT/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_CLIENT=OFF -DBUILD_SERVER=ON -DBUILD_MOD=OFF -DBUILD_CLIENT_MOD=OFF -DBUILD_SERVER_MOD=OFF -DBUILD_MOD_PK3=OFF \
  -DFEATURE_CURL=OFF -DFEATURE_SSL=OFF -DFEATURE_AUTH=OFF -DFEATURE_AUTOUPDATE=OFF -DFEATURE_LUA=OFF -DFEATURE_OMNIBOT=OFF \
  -DFEATURE_DBMS=OFF -DINSTALL_EXTRA=OFF -DCROSS_COMPILE32=OFF -DBUNDLED_LIBS=ON -DBUNDLED_CURL=OFF -DBUNDLED_SSL=OFF
cmake --build "$OUT/build" --target etlded
install -m 755 "$OUT/build/etlded.x86_64" "$OUT/server/platinum-server.x86_64"
clang -std=gnu11 -O2 -g -Wall -Wextra -Wno-unused-parameter -Wno-implicit-const-int-float-conversion \
  -shared -fPIC -fvisibility=hidden -DMODLIB -I "$E/src" \
  "$G/native/tcp_game.c" "$G/native/tcp_move.c" "$G/native/tcp_lagpredict.c" "$G/native/tcp_native_combat.c" "$G/native/tcp_aim.c" \
  "$G/shared/tcp_weapon.c" "$G/shared/tcp_inventory.c" "$G/shared/tcp_inventory_apply.c" "$G/shared/tcp_ballistics.c" "$G/shared/tcp_ammo.c" \
  "$G/shared/tcp_firing.c" "$G/shared/tcp_spread.c" "$G/shared/tcp_shotgun.c" "$G/shared/tcp_specs.c" "$G/shared/tcp_weapon_rules.c" \
  "$G/shared/tcp_damage.c" "$G/shared/tcp_math.c" "$G/shared/tcp_regions.c" "$G/shared/tcp_penetration.c" \
  "$G/native/monocypher/monocypher.c" "$G/native/monocypher/monocypher-ed25519.c" \
  -lm -Wl,-z,defs -o "$OUT/tcetest/qagame.mp.x86_64.so"
strip "$OUT/server/platinum-server.x86_64" "$OUT/tcetest/qagame.mp.x86_64.so"
rm -rf "$OUT/build"
