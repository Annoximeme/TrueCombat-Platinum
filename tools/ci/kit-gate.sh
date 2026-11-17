#!/bin/bash
# Kit gate: what a feature kit must pass before the release integrator takes it (release-speed plan, 2026-11-17).
# Runs in a cloud thread's own container (or any Linux box), never on the VPS, never on the release PC:
#   1. compose the base release source and apply the kit's patches in order (git apply, no fuzz)
#   2. metadata scan of the whole tree (C2PA / tool metadata in images, paks, embedded image arrays)
#   3. Windows cross-build with -Werror flags as the PC uses, plus the native probes under wine
#   4. Linux dedicated server build
#   5. bots soak on the given maps (crash / hang / no join / no combat fail it), with server CPU per map
#
#   tools/ci/kit-gate.sh <base tag> <kit folder> ["obj_village obj_snow"] [minutes per map]
#
# The kit folder holds patches/*.patch (applied in name order) and optionally files/ (copied over the tree
# afterwards, same relative paths). Result: kit-gate/SUMMARY.md and exit 0 only when every step passed.
# Put the SUMMARY.md next to the kit manifest; the integrator only accepts kits with a passing summary
# that names the same base tag and kit checksum.
#
# Environment: as build-windows.sh (LLVM_MINGW, SL_SDK, EOS_INCLUDE); TOOLCHAIN (default ~/toolchain) is set up
# on first use with setup-toolchain.sh. SKIP="windows bots" skips steps (the summary then says NOT a full gate).
set -uo pipefail
BASE=${1:?base tag, e.g. v0.38.0-sandbox34}; KIT=$(cd "${2:?kit folder}" && pwd); MAPS=${3:-"obj_village obj_snow"}; MIN=${4:-3}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
W=${WORK:-$PWD/kit-gate}; mkdir -p "$W"; S="$W/SUMMARY.md"; SKIP=${SKIP:-}
TOOLCHAIN=${TOOLCHAIN:-$HOME/toolchain}
kitsum=$(cd "$KIT" && find . -type f ! -name SUMMARY.md -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -c1-16)
{ echo "# Kit gate: $(basename "$KIT")"; echo; echo "- Base: $BASE"; echo "- Kit checksum: $kitsum"
  echo "- Started: $(date -u +%FT%TZ)"; echo; echo "| Step | Result | Time |"; echo "|---|---|---|"; } > "$S"
fail=0
step() {
  local name=$1; shift; local t0=$SECONDS
  case " $SKIP " in *" $name "*) echo "| $name | skipped | |" >> "$S"; return 0;; esac
  if "$@" > "$W/$name.log" 2>&1; then echo "| $name | pass | $((SECONDS - t0)) s |" >> "$S"; echo "== $name pass"
  else echo "| $name | **FAIL** | $((SECONDS - t0)) s |" >> "$S"; echo "== $name FAIL (log $W/$name.log)"; tail -25 "$W/$name.log"; fail=1; return 1; fi
}

compose() {
  rm -rf "$W/src"; (cd "$W" && "$HERE/compose-source.sh" "$BASE" src) || return 1
  cd "$W/src" || return 1
  git init -q . && git add -A >/dev/null && git -c user.name=gate -c user.email=gate@localhost commit -qm base || return 1
  for p in $(ls "$KIT"/patches/*.patch 2>/dev/null | sort); do
    echo "apply $(basename "$p")"; git apply --whitespace=nowarn "$p" || { echo "does not apply on $BASE: $(basename "$p")"; return 1; }
  done
  [ -d "$KIT/files" ] && cp -r "$KIT/files/." "$W/src/"
  git status --short | wc -l | sed 's/^/files changed by the kit: /'
}
toolchain() {
  [ -x "$TOOLCHAIN/llvm-mingw/bin/x86_64-w64-mingw32-clang" ] || "$HERE/setup-toolchain.sh" "$TOOLCHAIN" || return 1
  command -v wine >/dev/null || echo "wine missing: probes will not run (apt-get install wine64)"
}
windows() {
  LLVM_MINGW=${LLVM_MINGW:-$TOOLCHAIN/llvm-mingw} SL_SDK=${SL_SDK:-$TOOLCHAIN/streamline} "$HERE/build-windows.sh" "$W/src" "$W/win"
}

step compose compose && {
  step scan python3 "$HERE/scan_metadata.py" "$W/src"
  step toolchain toolchain && step windows windows && step scan-built python3 "$HERE/scan_metadata.py" "$W/win/game"
  step linux "$REPO/tools/linux-server/build-linux-server.sh" "$W/src" "$W/linux" && \
    step bots env LOGS="$W/soak-logs" DATA="${DATA:-$W/soak-data}" "$HERE/bots-soak.sh" "$W/linux" "$BASE" "$MAPS" "$MIN"
}
[ -f "$W/soak-logs/summary.md" ] && { echo; echo "## Bots soak"; echo; cat "$W/soak-logs/summary.md"; } >> "$S"
[ -f "$W/win/summary.md" ] && { echo; echo "## Windows build"; echo; cat "$W/win/summary.md"; } >> "$S"
{ echo; [ -n "$SKIP" ] && echo "Skipped: $SKIP (NOT a full kit gate)."
  [ $fail = 0 ] && echo "**KIT GATE PASSED** $(date -u +%FT%TZ)" || echo "**KIT GATE FAILED** $(date -u +%FT%TZ)"; } >> "$S"
cat "$S"; exit $fail
