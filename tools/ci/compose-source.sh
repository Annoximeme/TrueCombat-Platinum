#!/bin/bash
# Rebuilds a source tree for a cloud build: a published release's source snapshot,
# plus (for a request) the changed files sent by tools/ci/request.py.
#   tools/ci/compose-source.sh <base tag> <out dir> [request draft tag]
set -euo pipefail
BASE=$1; OUT=$2; REQ=${3:-}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=${GITHUB_REPOSITORY:-Annoximeme/TrueCombat-Platinum}
mkdir -p "$OUT" dl
[ -f "dl/$BASE.zip" ] || curl -fsSL --retry 3 -o "dl/$BASE.zip" \
  "https://github.com/$REPO/releases/download/$BASE/f__source__native-sandbox-source.zip"
unzip -q -o "dl/$BASE.zip" -d "$OUT"
if [ -n "$REQ" ]; then
  python3 "$HERE/draft.py" get "$REQ" overlay.zip dl/overlay.zip
  python3 "$HERE/draft.py" get "$REQ" request.json dl/request.json
  python3 - dl/overlay.zip dl/request.json "$OUT" <<'PY'
import hashlib, json, sys, zipfile
from pathlib import Path, PurePosixPath
overlay, request, out = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3])
assert hashlib.sha256(overlay.read_bytes()).hexdigest() == request['overlay_sha256'], 'overlay checksum mismatch'
def safe(name):
    p = PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name, name
    return out.joinpath(*p.parts)
with zipfile.ZipFile(overlay) as z:
    for name in z.namelist():
        if not name.endswith('/'):
            t = safe(name); t.parent.mkdir(parents=True, exist_ok=True); t.write_bytes(z.read(name))
for name in request['deleted']:
    safe(name).unlink(missing_ok=True)
print(f"applied {request['changed']} changed files and {len(request['deleted'])} deletions from {request['name']} onto {request['base']}")
PY
fi
