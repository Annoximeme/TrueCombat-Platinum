#!/bin/bash
# Kit gate: what a feature kit must pass before the release integrator takes it (release-speed plan, 2026-11-17).
# Runs in a cloud thread's own container (or any Linux box), never on the VPS, never on the release PC:
#   1. compose the base release source and apply the kit's patches in order (git apply, no fuzz)
#   2. metadata scan of the whole tree (C2PA / tool metadata in images, paks, embedded image arrays)
#   3. Windows cross-build with -Werror flags as the PC uses, plus the native probes under wine
#   4. Linux dedicated server build
#   5. bots soak on the given maps (crash / hang / no join / no combat fail it), with server CPU per map
#
#   tools/ci/kit-gate.sh <base> <kit folder> ["obj_village obj_snow"] [minutes per map]
#
# <base> is a published release tag (v0.38.0-sandbox34), or, before that release is published, a frozen
# candidate's source as a zip or folder (the integrator keeps the newest one in
# /mnt/project-files/release-speed/base/). With a local base the bots soak uses the game data of DATA_TAG
# (default: the newest published release) under this build's server and game modules.
#
# The kit folder holds patches/*.patch (applied in name order) and optionally files/ (copied over the tree
# afterwards, same relative paths). Result: kit-gate/SUMMARY.md and exit 0 only when every step passed.
# Put the SUMMARY.md next to the kit manifest; the integrator only accepts kits with a passing summary
# that names the same base tag and kit checksum.
#
# Environment: as build-windows.sh (LLVM_MINGW, SL_SDK, EOS_INCLUDE, BUILD_CACHE); TOOLCHAIN (default ~/toolchain) is set up
# on first use with setup-toolchain.sh. SKIP="windows bots" skips steps (the summary then says NOT a full gate).
# SCAN_CHANGED=1 scans only the files the kit changes (for a base that already passed a full scan); DATA
# shares the soak game data between runs (downloaded once).
set -uo pipefail
BASE=${1:?base tag (v0.38.0-sandbox34) or a source zip/folder}; KIT=$(cd "${2:?kit folder}" && pwd); MAPS=${3:-"obj_village obj_snow"}; MIN=${4:-3}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
W=${WORK:-$PWD/kit-gate}; mkdir -p "$W"; S="$W/SUMMARY.md"; SKIP=${SKIP:-}
TOOLCHAIN=${TOOLCHAIN:-$HOME/toolchain}
if [ -e "$BASE" ]; then
  BASE=$(cd "$(dirname "$BASE")" && pwd)/$(basename "$BASE")
  basesum=$( [ -f "$BASE" ] && sha256sum "$BASE" | cut -c1-16 || echo folder)
  DATA_TAG=${DATA_TAG:-$(curl -fsSL https://api.github.com/repos/${GITHUB_REPOSITORY:-Annoximeme/TrueCombat-Platinum}/releases/latest 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])' 2>/dev/null || echo v0.37.3-sandbox33)}
  BASE_LABEL="$(basename "$BASE") (sha256 $basesum; game data $DATA_TAG)"
else
  DATA_TAG=${DATA_TAG:-$BASE}; BASE_LABEL=$BASE
fi
kitsum=$(cd "$KIT" && find . -type f ! -name SUMMARY.md -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -c1-16)
{ echo "# Kit gate: $(basename "$KIT")"; echo; echo "- Base: $BASE_LABEL"; echo "- Kit checksum: $kitsum"
  echo "- Started: $(date -u +%FT%TZ)"; echo; echo "| Step | Result | Time |"; echo "|---|---|---|"; } > "$S"
fail=0
step() {
  local name=$1; shift; local t0=$SECONDS
  case " $SKIP " in *" $name "*) echo "| $name | skipped | |" >> "$S"; return 0;; esac
  if "$@" > "$W/$name.log" 2>&1; then echo "| $name | pass | $((SECONDS - t0)) s |" >> "$S"; echo "== $name pass"
  else echo "| $name | **FAIL** | $((SECONDS - t0)) s |" >> "$S"; echo "== $name FAIL (log $W/$name.log)"; tail -25 "$W/$name.log"; fail=1; return 1; fi
}

compose() {
  rm -rf "$W/src"
  if [ -f "$BASE" ]; then mkdir -p "$W/src" && unzip -q "$BASE" -d "$W/src" || return 1
  elif [ -d "$BASE" ]; then cp -r "$BASE/." "$W/src/" || return 1
  else (cd "$W" && "$HERE/compose-source.sh" "$BASE" src) || return 1; fi
  # a candidate snapshot (experiments/integration/<run>/source) keeps the engine at etlegacy/; releases ship it as reference/etlegacy/
  if [ -d "$W/src/etlegacy" ] && [ ! -d "$W/src/reference/etlegacy" ]; then mkdir -p "$W/src/reference" && mv "$W/src/etlegacy" "$W/src/reference/"; fi
  cd "$W/src" || return 1
  git init -q . && git add -A >/dev/null && git -c user.name=gate -c user.email=gate@localhost commit -qm base || return 1
  for p in $(ls "$KIT"/patches/*.patch 2>/dev/null | sort); do
    echo "apply $(basename "$p")"; git apply --whitespace=nowarn "$p" || { echo "does not apply on $BASE_LABEL: $(basename "$p")"; return 1; }
  done
  [ -d "$KIT/files" ] && cp -r "$KIT/files/." "$W/src/"
  git status --short | wc -l | sed 's/^/files changed by the kit: /'
}
scan_changed() {  # the kit's files only: the base passed a full scan before
  (cd "$W/src" && git add -A >/dev/null && git diff --cached --name-only --diff-filter=d -z) > "$W/changed.lst" || return 1
  echo "scan of the $(tr -cd '\0' < "$W/changed.lst" | wc -c) files the kit changes (base scanned in full before)"
  [ -s "$W/changed.lst" ] || return 0
  (cd "$W/src" && xargs -0 python3 "$HERE/scan_metadata.py" < "$W/changed.lst")
}
toolchain() {
  [ -x "$TOOLCHAIN/llvm-mingw/bin/x86_64-w64-mingw32-clang" ] || "$HERE/setup-toolchain.sh" "$TOOLCHAIN" || return 1
  command -v wine >/dev/null || echo "wine missing: probes will not run (apt-get install wine64)"
}
windows() {
  LLVM_MINGW=${LLVM_MINGW:-$TOOLCHAIN/llvm-mingw} SL_SDK=${SL_SDK:-$TOOLCHAIN/streamline} "$HERE/build-windows.sh" "$W/src" "$W/win"
}

step compose compose && {
  if [ "${SCAN_CHANGED:-0}" = 1 ]; then
    step scan scan_changed
  else
    step scan python3 "$HERE/scan_metadata.py" "$W/src"
  fi
  step toolchain toolchain && step windows windows && step scan-built python3 "$HERE/scan_metadata.py" "$W/win/game"
  step linux "$REPO/tools/linux-server/build-linux-server.sh" "$W/src" "$W/linux" && \
    step bots env LOGS="$W/soak-logs" DATA="${DATA:-$W/soak-data}" "$HERE/bots-soak.sh" "$W/linux" "$DATA_TAG" "$MAPS" "$MIN"
}
[ -f "$W/soak-logs/summary.md" ] && { echo; echo "## Bots soak"; echo; cat "$W/soak-logs/summary.md"; } >> "$S"
[ -f "$W/win/summary.md" ] && { echo; echo "## Windows build"; echo; cat "$W/win/summary.md"; } >> "$S"
{ echo; [ -n "$SKIP" ] && echo "Skipped: $SKIP (NOT a full kit gate)."
  [ $fail = 0 ] && echo "**KIT GATE PASSED** $(date -u +%FT%TZ)" || echo "**KIT GATE FAILED** $(date -u +%FT%TZ)"; } >> "$S"
cat "$S"; exit $fail
