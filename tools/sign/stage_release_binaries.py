#!/usr/bin/env python3
"""Turns a tools/ci/build-windows.sh output into the release binary set that gets signed.

    python tools/sign/stage_release_binaries.py <build out dir> <staged dir> [--exe-names] [--strip TOOL]

* copies our own binaries to their shipped paths (etl.exe -> engine/platinum-engine.bin, ...);
  --exe-names uses the 0.40.0 names platinum-engine.exe / platinum-server.exe instead;
* removes debug data and the COFF symbol table (llvm-strip --strip-all, as pe_tidy.py on the PC)
  and writes a valid PE checksum, so the signed files carry the same hygiene as 0.38.x releases;
* writes MANIFEST.json (relative path -> sha256, bytes) for the release gate.

Signing changes only the certificate table, its directory entry and the PE checksum, so
tools/sign/check_signed.py --unsigned-ref <staged dir> can prove later that a signed file is
exactly this staged file plus a signature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

LAYOUT = [  # (built file, shipped path, shipped path from 0.40.0)
    ('game/engine/etl.exe', 'engine/platinum-engine.bin', 'engine/platinum-engine.exe'),
    ('game/engine/etlded.exe', 'server/platinum-server.bin', 'server/platinum-server.exe'),
    ('game/engine/renderer_dx12_x64.dll', 'engine/renderer_dx12_x64.dll', None),
    ('game/engine/renderer_opengl1_x64.dll', 'engine/renderer_opengl1_x64.dll', None),
    ('game/tcetest/qagame_mp_x64.dll', 'tcetest/qagame_mp_x64.dll', None),
    ('game/tcetest/cgame_mp_x64.dll', 'tcetest/cgame_mp_x64.dll', None),
    ('game/tcetest/ui_mp_x64.dll', 'tcetest/ui_mp_x64.dll', None),
    ('game/TrueCombatPlatinum.exe', 'TrueCombatPlatinum.exe', None),
    ('TrueCombat-Platinum-Setup-uncompressed.exe', 'TrueCombat-Platinum-Setup.exe', None),
    ('game/engine/OpenAL64.dll', 'engine/OpenAL64.dll', None),  # upstream library, built from unmodified source
]


def pe_checksum(data: bytearray, checksum_off: int) -> int:
    """The Windows PE checksum (as CheckSumMappedFile / imagehlp)."""
    total = 0
    n = len(data)
    padded = bytes(data) + b'\0' * (n % 2)
    for i in range(0, len(padded), 2):
        if i == checksum_off or i == checksum_off + 2:
            continue
        total += padded[i] | (padded[i + 1] << 8)
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (total + n) & 0xFFFFFFFF


def set_checksum(path: Path) -> int:
    data = bytearray(path.read_bytes())
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    off = pe + 24 + 64
    struct.pack_into('<I', data, off, 0)
    value = pe_checksum(data, off)
    struct.pack_into('<I', data, off, value)
    path.write_bytes(bytes(data))
    return value


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('build', type=Path)
    ap.add_argument('staged', type=Path)
    ap.add_argument('--exe-names', action='store_true', help='0.40.0 layout: engine and server as .exe')
    ap.add_argument('--strip', default=shutil.which('llvm-strip') or 'llvm-strip', help='llvm-strip from the LLVM-MinGW toolchain')
    args = ap.parse_args(argv)
    if args.staged.exists():
        sys.exit(f'{args.staged} already exists')
    manifest = {}
    for built, shipped, shipped_040 in LAYOUT:
        src = args.build / built
        if not src.is_file():
            sys.exit(f'missing build output {src}')
        rel = (shipped_040 if args.exe_names and shipped_040 else shipped)
        dst = args.staged / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        subprocess.run([args.strip, '--strip-all', str(dst)], check=True)
        checksum = set_checksum(dst)
        data = dst.read_bytes()
        manifest[rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'pe_checksum': '%08x' % checksum}
        print(f'{rel:40} {len(data):>10} bytes  {manifest[rel]["sha256"][:16]}')
    (args.staged / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
