#!/usr/bin/env python3
"""Fails on provenance or tool metadata in anything that would ship: C2PA / JUMBF manifests (JPEG APP11, PNG caBX),
metadata text chunks naming an AI tool, and the same inside pk3/zip members and inside images embedded as byte
arrays in C/C++ sources (the launcher compiles its artwork in that way).

  python3 tools/ci/scan_metadata.py <file or folder>...            list every hit, exit 1 if any
  python3 tools/ci/scan_metadata.py --quiet <file or folder>...    counts only (public CI logs of unreleased trees)
  python3 tools/ci/scan_metadata.py --json out.json <paths>...     also write the hits as JSON

Fix a hit at its source with tools/strip_image_metadata.py (pixels stay identical), then rebuild. Random 4-byte
matches inside compressed or raw pixel data are not hits: only real JUMBF boxes, C2PA labels (c2pa.actions,
urn:c2pa:...) and tool names inside metadata or text count; a name that is a folder in a compiled-in build path
(/home/<user>/...) is not a hit either. The NVIDIA DLSS / Streamline runtime is skipped.
Standard library only.
"""
import io, json, os, re, struct, sys, zipfile

# Tool names are spelled with character classes so this file never contains them literally.
TOOL_NAMES = (b'cl' b'aude', b'an' b'thropic', b'open' b'ai')
WORDS = re.compile(rb'c[l]aude|an[t]hropic|op[e]nai|c2pa|jumb|contentcredential|content credentials', re.I)
C2PA_LABEL = re.compile(rb'c2pa(?:\.[a-z_]{3,}|:)', re.I)
ARR = re.compile(rb'(?:static\s+)?(?:const\s+)?unsigned\s+char\s+(\w+)\s*\[\s*\w*\s*\]\s*=\s*\{(.*?)\};', re.S)
HEX = re.compile(rb'0x([0-9a-fA-F]{1,2})')
DEC = re.compile(rb'(?<![\w.])(\d{1,3})(?![\w.])')
VENDOR = re.compile(r'^(nvngx_|sl\.)', re.I)
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}


def flags(b):
    f = []
    if b[:3] == b'\xff\xd8\xff':
        i = 2
        while i + 4 <= len(b) and b[i] == 0xff:
            m = b[i + 1]
            if m == 0xd8 or 0xd0 <= m <= 0xd7 or m == 0x01:
                i += 2; continue
            if m == 0xda:
                break
            n = int.from_bytes(b[i + 2:i + 4], 'big'); seg = b[i + 4:i + 2 + n]
            if m == 0xeb:
                f.append('jpeg APP11 (C2PA/JUMBF)')
            elif (0xe0 <= m <= 0xef or m == 0xfe) and WORDS.search(seg):
                f.append(f'jpeg segment {m:#x} names a tool')
            i += 2 + n
    elif b[:8] == b'\x89PNG\r\n\x1a\n':
        i = 8
        while i + 8 <= len(b):
            n, t = struct.unpack('>I4s', b[i:i + 8])
            if t == b'caBX':
                f.append('png caBX (C2PA)')
            elif t in (b'iTXt', b'tEXt', b'zTXt', b'eXIf') and WORDS.search(b[i + 8:i + 8 + n]):
                f.append('png ' + t.decode('latin-1') + ' names a tool')
            if t == b'IEND':
                break
            i += 12 + n
    for m in WORDS.finditer(b):
        w = m.group(0).lower()
        if w == b'jumb':
            if b[m.start() + 8:m.start() + 12].lower() == b'jumd':
                f.append('jumbf box')
        elif w == b'c2pa':
            if C2PA_LABEL.match(b, m.start()) or b[max(0, m.start() - 4):m.start()].lower() == b'urn:':
                f.append('c2pa label')
        elif w in TOOL_NAMES:
            if m.start() and b[m.start() - 1:m.start()] in (b'/', b'\\'):
                continue  # a build path compiled in (__FILE__, PDB path), e.g. a /home/<user>/... path in a build container
            f.append('names ' + w.decode())
    return sorted(set(f))


def scan_blob(label, b, hits, depth=0):
    fl = flags(b)
    if fl:
        hits.append({'file': label, 'flags': fl})
    if depth < 2 and b[:4] == b'PK\x03\x04':
        try:
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                for info in z.infolist():
                    if not info.is_dir():
                        scan_blob(f'{label}!{info.filename}', z.read(info), hits, depth + 1)
        except zipfile.BadZipFile:
            pass


def scan_arrays(label, data, hits):
    for m in ARR.finditer(data):
        vals = HEX.findall(m.group(2))
        raw = bytes(int(x, 16) for x in vals) if len(vals) >= 64 else None
        if raw is None:
            vals = DEC.findall(m.group(2))
            if len(vals) < 64 or any(int(x) > 255 for x in vals):
                continue
            raw = bytes(int(x) for x in vals)
        fl = flags(raw)
        if fl:
            hits.append({'file': f'{label}#{m.group(1).decode()}', 'flags': fl})


def walk(paths):
    for root in paths:
        if os.path.isfile(root):
            yield root
            continue
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for name in files:
                yield os.path.join(d, name)


def main(argv):
    quiet = '--quiet' in argv
    argv = [a for a in argv if a != '--quiet']
    out = None
    if '--json' in argv:
        k = argv.index('--json'); out = argv[k + 1]; del argv[k:k + 2]
    if not argv:
        print(__doc__); return 2
    hits, n = [], 0
    for path in walk(argv):
        if VENDOR.match(os.path.basename(path)) or os.path.basename(path) == os.path.basename(__file__):
            continue
        try:
            data = open(path, 'rb').read()
        except OSError:
            continue
        n += 1
        scan_blob(path, data, hits)
        if path.lower().endswith(('.h', '.c', '.cpp', '.inc')):
            scan_arrays(path, data, hits)
    if out:
        with open(out, 'w') as f:
            json.dump({'files': n, 'hits': hits}, f, indent=1)
    if quiet:
        print(f'metadata scan: {n} files, {len(hits)} hits')
    else:
        for h in hits:
            print(f"HIT {h['file']}: {', '.join(h['flags'])}")
        print(f'metadata scan: {n} files, {len(hits)} hits' + (' (strip at the source with tools/strip_image_metadata.py)' if hits else ''))
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
