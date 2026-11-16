#!/bin/bash
# Downloads the pinned Windows cross toolchain for tools/ci/build-windows.sh:
#   <dir>/llvm-mingw   LLVM-MinGW (same release as the PC build), Linux host
#   <dir>/streamline   NVIDIA Streamline SDK headers (SHA-256 pinned, as analysis_scripts/dlss/prepare.py)
set -euo pipefail
DIR=$(mkdir -p "$1" && cd "$1" && pwd)
V=${LLVM_MINGW_VERSION:-20261020}; SL=${STREAMLINE_VERSION:-2.14.16}
SLSHA=${STREAMLINE_SHA256:-32041e51db0cab709a271b72a352281b690c2abbd669a827809401a5dd23956b}
cd "$DIR"
curl -fsSL --retry 3 -o lm.tar.xz "https://github.com/mstorsjo/llvm-mingw/releases/download/$V/llvm-mingw-$V-ucrt-ubuntu-22.04-x86_64.tar.xz"
rm -rf llvm-mingw && mkdir llvm-mingw && tar -xf lm.tar.xz -C llvm-mingw --strip-components=1 && rm lm.tar.xz
curl -fsSL --retry 3 -o sl.zip "https://github.com/NVIDIA-RTX/Streamline/releases/download/v$SL/streamline-sdk-v$SL.zip"
echo "$SLSHA  sl.zip" | sha256sum -c --quiet
rm -rf streamline && mkdir streamline && unzip -q sl.zip 'include/*' -d streamline && rm sl.zip
echo "toolchain ready in $DIR"
