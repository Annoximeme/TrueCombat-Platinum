#!/usr/bin/env python3
"""Small patches between two versions of a zip or pk3 file.

Our release zips and game packs change very little between versions, but the
whole file has to be re-uploaded every time. A patch stores only the bytes that
changed: every entry whose compressed data is the same as in the base file is
copied from the base when the patch is applied, everything else (changed
entries, headers, the central directory) is stored in the patch.

    zippatch.py make  <base zip | https URL> <new zip> <patch>
    zippatch.py apply <base zip> <patch> <output zip>

The base can be a release asset URL when making a patch: only its directory is
read (a few HTTP range requests), so the old file does not have to be on disk.
apply always checks that the result has exactly the size and SHA-256 of the new
file and fails otherwise, so a wrong base can never produce a wrong file.
Standard library only, so it runs the same on Windows and in GitHub Actions.
"""
import hashlib
import io
import json
import os
import struct
import sys
import urllib.request
import zipfile
import zlib

FORMAT = 'tcp-zippatch/1'
MAGIC = b'TCPZPATCH1\n'
CHUNK = 1 << 20


class RangeFile(io.RawIOBase):
    """Read-only, seekable view of an HTTPS file through range requests."""

    def __init__(self, url):
        # Release downloads redirect to short-lived signed URLs, so every
        # request goes through the original URL again.
        self.url = url
        first = urllib.request.urlopen(urllib.request.Request(url, headers={'Range': 'bytes=0-0'}), timeout=60)
        self.size = int(first.headers['Content-Range'].rsplit('/', 1)[1])
        self.pos = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def readinto(self, buffer):
        if self.pos >= self.size:
            return 0
        end = min(self.size, self.pos + len(buffer)) - 1
        request = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{end}'})
        data = urllib.request.urlopen(request, timeout=120).read()
        buffer[:len(data)] = data
        self.pos += len(data)
        return len(data)


def open_any(path):
    if path.startswith('https://'):
        return io.BufferedReader(RangeFile(path), 1 << 16)
    return open(path, 'rb')


def entry_key(info):
    return (info.filename, info.CRC, info.compress_size, info.file_size, info.compress_type)


def data_spans(handle):
    """Yields (zipinfo, offset of the compressed data) for every entry, in file order."""
    infos = sorted(zipfile.ZipFile(handle).infolist(), key=lambda i: i.header_offset)
    for info in infos:
        handle.seek(info.header_offset)
        header = handle.read(30)
        if header[:4] != b'PK\x03\x04':
            raise ValueError(f'bad local header for {info.filename}')
        name_len, extra_len = struct.unpack('<HH', header[26:30])
        yield info, info.header_offset + 30 + name_len + extra_len


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(CHUNK), b''):
            digest.update(block)
    return digest.hexdigest()


def make(base, new, out):
    with open_any(base) as handle:
        base_size = handle.seek(0, 2)
        handle.seek(0)
        base_keys = {entry_key(i) for i in zipfile.ZipFile(handle).infolist()}
    ops, copied, literal_bytes = [], 0, 0
    compressor = zlib.compressobj(6)
    target_size = os.path.getsize(new)
    with open(new, 'rb') as src, open(out + '.tmp', 'wb') as blob:
        def literal(start, end):
            nonlocal literal_bytes
            if end <= start:
                return
            src.seek(start)
            left = end - start
            while left:
                block = src.read(min(CHUNK, left))
                left -= len(block)
                blob.write(compressor.compress(block))
            if ops and ops[-1][0] == 'L':
                ops[-1][1] += end - start
            else:
                ops.append(['L', end - start])
            literal_bytes += end - start

        cursor = 0
        for info, start in list(data_spans(src)):
            if entry_key(info) not in base_keys or info.compress_size == 0:
                continue
            literal(cursor, start)
            ops.append(['E', info.filename, info.CRC, info.compress_size])
            copied += info.compress_size
            cursor = start + info.compress_size
        literal(cursor, target_size)
        blob.write(compressor.flush())
    header = json.dumps({
        'format': FORMAT,
        'base_bytes': base_size,
        'target_bytes': target_size,
        'target_sha256': sha256_file(new),
        'ops': ops,
    }, separators=(',', ':')).encode()
    with open(out, 'wb') as patch, open(out + '.tmp', 'rb') as blob:
        patch.write(MAGIC + struct.pack('<Q', len(header)) + header)
        for block in iter(lambda: blob.read(CHUNK), b''):
            patch.write(block)
    os.remove(out + '.tmp')
    size = os.path.getsize(out)
    print(f'{os.path.basename(new)}: {target_size} bytes, {copied} copied from base, '
          f'{literal_bytes} new -> patch {size} bytes')
    return size


def read_header(patch):
    if patch.read(len(MAGIC)) != MAGIC:
        raise ValueError('not a tcp-zippatch file')
    (length,) = struct.unpack('<Q', patch.read(8))
    header = json.loads(patch.read(length))
    if header.get('format') != FORMAT:
        raise ValueError('unknown patch format')
    return header


def apply(base, patch_path, out):
    with open(patch_path, 'rb') as patch:
        header = read_header(patch)
        if os.path.getsize(base) != header['base_bytes']:
            raise ValueError(f'base is {os.path.getsize(base)} bytes, patch expects {header["base_bytes"]}')
        with open(base, 'rb') as base_file:
            spans = {info.filename: (info, start) for info, start in data_spans(base_file)}
            decompressor = zlib.decompressobj()
            pending = bytearray()

            def take(count):
                while len(pending) < count:
                    block = patch.read(CHUNK)
                    if block:
                        pending.extend(decompressor.decompress(block))
                    else:
                        pending.extend(decompressor.flush())
                        if len(pending) < count:
                            raise ValueError('patch data is truncated')
                data = bytes(pending[:count])
                del pending[:count]
                return data

            digest = hashlib.sha256()
            written = 0
            with open(out + '.part', 'wb') as dst:
                def emit(data):
                    nonlocal written
                    dst.write(data)
                    digest.update(data)
                    written += len(data)

                for op in header['ops']:
                    if op[0] == 'L':
                        left = op[1]
                        while left:
                            block = take(min(CHUNK, left))
                            left -= len(block)
                            emit(block)
                    else:
                        _, name, crc, size = op
                        info, start = spans.get(name, (None, 0))
                        if info is None or info.CRC != crc or info.compress_size != size:
                            raise ValueError(f'base has no matching entry {name}')
                        base_file.seek(start)
                        left = size
                        while left:
                            block = base_file.read(min(CHUNK, left))
                            if not block:
                                raise ValueError('base file is truncated')
                            left -= len(block)
                            emit(block)
    if written != header['target_bytes'] or digest.hexdigest() != header['target_sha256']:
        os.remove(out + '.part')
        raise ValueError('patched file does not match the expected size and SHA-256')
    os.replace(out + '.part', out)
    print(f'{os.path.basename(out)}: {written} bytes, sha256 {header["target_sha256"]} OK')
    return header['target_sha256']


def main(argv):
    if len(argv) == 5 and argv[1] == 'make':
        make(argv[2], argv[3], argv[4])
    elif len(argv) == 5 and argv[1] == 'apply':
        apply(argv[2], argv[3], argv[4])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
