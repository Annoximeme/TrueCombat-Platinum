#!/bin/sh
# TrueCombat: Platinum dedicated server for Linux (x86_64).
# Downloads the game data a server needs from the official GitHub release,
# checks every file against the release manifest, and lays out a ready server.
#   ./install.sh [install-dir] [release-tag]
# Default: ./truecombat-server and the release this kit was built for.
# Needs curl and python3.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DIR=${1:-./truecombat-server}
DEFTAG=latest
[ -f "$HERE/RELEASE" ] && DEFTAG=$(cat "$HERE/RELEASE")
TAG=${2:-$DEFTAG}
REPO=${REPO:-Annoximeme/TrueCombat-Platinum}
WEB=${GITHUB_WEB:-https://github.com}
if [ "$TAG" = latest ]; then BASE="$WEB/$REPO/releases/latest/download"; else BASE="$WEB/$REPO/releases/download/$TAG"; fi
mkdir -p "$DIR/server" "$DIR/etmain" "$DIR/tcetest" "$DIR/home/tcetest"
echo "Fetching release manifest..."
curl -fsSL "$BASE/f__manifest.json" -o "$DIR/manifest.json"
# Server-side data only: the stock and Platinum game paks. HD texture packs are client-only.
FILES=$(python3 - "$DIR/manifest.json" <<'PY'
import json,sys
files=json.load(open(sys.argv[1]))["files"]
for name in sorted(files):
    if name.endswith(".pk3") and name.split("/")[0] in ("etmain","tcetest") and "/zzz_hd_" not in name:
        print(name)
PY
)
check() {
  python3 - "$DIR/manifest.json" "$1" "$2" <<'PY'
import hashlib,json,sys
want=json.load(open(sys.argv[1]))["files"][sys.argv[2]]["sha256"]
h=hashlib.sha256()
with open(sys.argv[3],"rb") as fh:
    for chunk in iter(lambda: fh.read(1<<20), b""): h.update(chunk)
sys.exit(h.hexdigest()!=want)
PY
}
for f in $FILES; do
  if [ -f "$DIR/$f" ] && check "$f" "$DIR/$f"; then echo "Up to date: $f"; continue; fi
  asset="f__$(echo "$f" | sed 's#/#__#g')"
  echo "Downloading $f"
  curl -fL --retry 3 -o "$DIR/$f.part" "$BASE/$asset"
  check "$f" "$DIR/$f.part" || { echo "checksum mismatch: $f" >&2; exit 1; }
  rm -f "${DIR:?}/${f:?}"
  mv "$DIR/$f.part" "$DIR/$f"
done
rm -f "${DIR:?}/server/platinum-server.x86_64" "${DIR:?}/tcetest/qagame.mp.x86_64.so"
install -m 755 "$HERE/server/platinum-server.x86_64" "$DIR/server/platinum-server.x86_64"
install -m 644 "$HERE/tcetest/qagame.mp.x86_64.so" "$DIR/tcetest/qagame.mp.x86_64.so"
[ -f "$DIR/home/tcetest/server.cfg" ] || install -m 644 "$HERE/server.cfg" "$DIR/home/tcetest/server.cfg"
install -m 755 "$HERE/start.sh" "$DIR/start.sh"
echo "$TAG" > "$DIR/RELEASE"
echo
echo "Done. Edit $DIR/home/tcetest/server.cfg (name, rcon password), then run $DIR/start.sh"
echo "Open UDP port 27960 (or the port you set) in your firewall."
