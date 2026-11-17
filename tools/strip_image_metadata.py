#!/usr/bin/env python3
"""Removes metadata from JPEG, PNG and WebP files without touching the pixels.

Images that pass through some tools and file shares pick up metadata on the way: EXIF (camera,
software, sometimes GPS), XMP, and C2PA "Content Credentials" manifests (JPEG APP11 / JUMBF, the
PNG caBX chunk, a WebP C2PA chunk). None of it belongs in a published game or website file.

The image data itself is copied byte for byte, so the result decodes to exactly the same pixels.
What is kept: JFIF (APP0), the ICC colour profile (APP2 ICC_PROFILE, PNG iCCP, WebP ICCP),
Adobe APP14 and every chunk a decoder needs.

  python tools/strip_image_metadata.py                 # strip everything under docs/ and tools/
  python tools/strip_image_metadata.py path [path ...] # files or folders
  python tools/strip_image_metadata.py --check [...]   # change nothing; exit 1 if anything would be stripped

Standard library only, so it runs on the build machines, in CI and on the release PC as is.
"""
import os
import struct
import sys

EXTS = (".jpg", ".jpeg", ".png", ".webp")
SKIP_DIRS = {".git", "node_modules", "__pycache__"}

PNG_DROP = {b"caBX", b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME", b"dSIG"}
WEBP_KEEP = {b"VP8 ", b"VP8L", b"VP8X", b"ALPH", b"ANIM", b"ANMF", b"ICCP"}


def strip_jpeg(b):
    if b[:2] != b"\xff\xd8":
        return b
    out = [b[:2]]
    i = 2
    while i + 4 <= len(b):
        if b[i] != 0xFF:
            return b  # not a marker where one should be: leave the file alone
        m = b[i + 1]
        if m == 0xFF:  # fill byte
            i += 1
            continue
        if m == 0xDA:  # start of scan: everything from here on is image data
            out.append(b[i:])
            return b"".join(out)
        if m in (0x01,) or 0xD0 <= m <= 0xD7:
            out.append(b[i:i + 2])
            i += 2
            continue
        n = struct.unpack(">H", b[i + 2:i + 4])[0]
        seg = b[i:i + 2 + n]
        payload = seg[4:]
        keep = True
        if 0xE1 <= m <= 0xEF:  # APP1..APP15
            keep = (m == 0xE2 and payload.startswith(b"ICC_PROFILE\x00")) or (m == 0xEE and payload.startswith(b"Adobe"))
        elif m == 0xFE:  # comment
            keep = False
        if keep:
            out.append(seg)
        i += 2 + n
    return b


def strip_png(b):
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return b
    out = [b[:8]]
    i = 8
    while i + 12 <= len(b):
        n = struct.unpack(">I", b[i:i + 4])[0]
        kind = b[i + 4:i + 8]
        chunk = b[i:i + 12 + n]
        if kind not in PNG_DROP:
            out.append(chunk)
        i += 12 + n
        if kind == b"IEND":
            break
    return b"".join(out)


def strip_webp(b):
    if b[:4] != b"RIFF" or b[8:12] != b"WEBP":
        return b
    out = []
    i = 12
    while i + 8 <= len(b):
        kind = b[i:i + 4]
        n = struct.unpack("<I", b[i + 4:i + 8])[0]
        chunk = b[i:i + 8 + n + (n & 1)]
        if kind == b"VP8X":
            flags = chunk[8] & ~0x0C  # no EXIF (0x08), no XMP (0x04)
            chunk = chunk[:8] + bytes([flags]) + chunk[9:]
        if kind in WEBP_KEEP:
            out.append(chunk)
        i += 8 + n + (n & 1)
    body = b"WEBP" + b"".join(out)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def strip(b):
    for f in (strip_jpeg, strip_png, strip_webp):
        r = f(b)
        if r is not b:
            return r
    return b


def files(paths):
    for p in paths:
        if os.path.isdir(p):
            for dp, dn, fn in os.walk(p):
                dn[:] = [d for d in dn if d not in SKIP_DIRS]
                for f in sorted(fn):
                    if f.lower().endswith(EXTS):
                        yield os.path.join(dp, f)
        elif p.lower().endswith(EXTS):
            yield p


def run(paths, check=False):
    """Strips (or with check=True only lists) every image with metadata. Returns the paths found."""
    found = []
    for p in files(paths):
        with open(p, "rb") as fh:
            b = fh.read()
        s = strip(b)
        if s != b:
            found.append(p)
            if not check:
                with open(p, "wb") as fh:
                    fh.write(s)
    return found


def main(argv):
    check = "--check" in argv
    paths = [a for a in argv if a != "--check"]
    if not paths:
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        paths = [os.path.join(root, "docs"), os.path.join(root, "tools")]
    found = run(paths, check)
    for p in found:
        print(("metadata: " if check else "stripped: ") + p)
    if check and found:
        print("%d image(s) carry metadata. Run python tools/strip_image_metadata.py to remove it." % len(found))
        return 1
    print("%d image(s) %s." % (len(found), "need stripping" if check else "stripped"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
