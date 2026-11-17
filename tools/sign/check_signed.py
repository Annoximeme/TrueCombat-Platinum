#!/usr/bin/env python3
"""Release gate check: every Windows program we build must carry a valid Authenticode signature.

    python tools/sign/check_signed.py <game folder or files...> [options]

Checks, per file (our own binaries only; vendor files are listed in VENDOR and skipped):
  1. the PE has an Authenticode signature (a PKCS#7 WIN_CERTIFICATE in the security directory);
  2. the signer is the expected publisher (--publisher, default "SignPath Foundation");
  3. the signature is cryptographically valid: PowerShell Get-AuthenticodeSignature on Windows,
     osslsigncode elsewhere (--structure-only skips this, for machines that have neither);
  4. the version resource names the product (--product) and every file carries the same product
     version (SignPath Foundation requires both);
  5. with --unsigned-ref DIR: the signed file differs from the gated unsigned file of the same
     relative path ONLY by the signature (certificate table, security directory entry and PE
     checksum). This is what lets the release gate run on unsigned binaries and package the
     signed ones without a second full regression.

Exit code 0 = all checked files pass. --json writes a machine-readable report.
Standard library only; runs on the PC (Windows) and on Linux CI runners.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

# Files we do not build and therefore never sign (their vendors sign them).
VENDOR = re.compile(r'(?i)(^|/)(EasyAntiCheat/|EOSSDK-Win64-Shipping\.dll$|msvcp140[^/]*\.dll$|vcruntime140[^/]*\.dll$|'
                    r'engine/dlss/|nvngx[^/]*\.dll$|sl\.[^/]*\.dll$)')
# Upstream library we build from unmodified source; SignPath allows it unsigned (signed when possible).
UPSTREAM = re.compile(r'(?i)(^|/)OpenAL64\.dll$')
PROGRAM_SUFFIXES = ('.exe', '.dll', '.bin')
CERT_DIR_INDEX = 4  # IMAGE_DIRECTORY_ENTRY_SECURITY


class PE:
    def __init__(self, data: bytes):
        if data[:2] != b'MZ':
            raise ValueError('not a PE file')
        self.data = data
        self.pe = struct.unpack_from('<I', data, 0x3C)[0]
        if data[self.pe:self.pe + 4] != b'PE\0\0':
            raise ValueError('bad PE signature')
        self.opt = self.pe + 24
        magic = struct.unpack_from('<H', data, self.opt)[0]
        if magic == 0x20B:
            self.dirs = self.opt + 112
        elif magic == 0x10B:
            self.dirs = self.opt + 96
        else:
            raise ValueError('unknown optional header magic %#x' % magic)
        self.checksum_off = self.opt + 64
        self.sec_off = self.dirs + 8 * CERT_DIR_INDEX
        self.cert_offset, self.cert_size = struct.unpack_from('<II', data, self.sec_off)

    def certificates(self):
        """Yield (revision, type, payload) for each WIN_CERTIFICATE entry."""
        pos, end = self.cert_offset, self.cert_offset + self.cert_size
        while self.cert_size and pos + 8 <= end:
            length, revision, ctype = struct.unpack_from('<IHH', self.data, pos)
            if length < 8:
                break
            yield revision, ctype, self.data[pos + 8:pos + length]
            pos += (length + 7) & ~7

    def without_signature(self) -> bytes:
        """The file as it was before signing: certificate table cut off, its directory entry and the
        PE checksum zeroed. An unsigned file passed through this only loses its checksum."""
        data = bytearray(self.data)
        if self.cert_size:
            data = data[:self.cert_offset]
        struct.pack_into('<II', data, self.sec_off, 0, 0)
        struct.pack_into('<I', data, self.checksum_off, 0)
        return bytes(data)


def only_signature_differs(signed: bytes, unsigned: bytes) -> bool:
    """True when `signed` is `unsigned` plus an Authenticode signature: identical image once both lose
    their signature and checksum, apart from up to 7 zero bytes the signer adds to align the table."""
    s, u = PE(signed).without_signature(), PE(unsigned).without_signature()
    extra = s[len(u):]
    return s[:len(u)] == u and len(extra) < 8 and not extra.strip(b'\0')


def version_strings(data: bytes) -> dict:
    """ProductName / ProductVersion / FileDescription / OriginalFilename from the VS_VERSIONINFO
    string table (UTF-16LE). A pragmatic scan, not a full resource-tree parser."""
    out = {}
    for key in ('ProductName', 'ProductVersion', 'FileDescription', 'OriginalFilename', 'CompanyName'):
        needle = (key + '\0').encode('utf-16-le')
        i = data.find(needle)
        if i < 0:
            continue
        j = i + len(needle)
        j += (-j) % 4  # value is DWORD-aligned
        end = j
        while end + 1 < len(data) and data[end:end + 2] != b'\0\0':
            end += 2
        try:
            out[key] = data[j:end].decode('utf-16-le').strip()
        except UnicodeDecodeError:
            pass
    return out


def signer_subjects(pkcs7: bytes) -> list[str]:
    """Certificate subjects inside the PKCS#7 blob, via openssl when it is available."""
    openssl = shutil.which('openssl')
    if not openssl:
        return []
    r = subprocess.run([openssl, 'pkcs7', '-inform', 'DER', '-print_certs', '-noout'], input=pkcs7,
                       capture_output=True)
    if r.returncode:
        return []
    return [line.split('=', 1)[1].strip() for line in r.stdout.decode('latin-1').splitlines() if line.startswith('subject')]


def verify_crypto(path: Path) -> tuple[bool | None, str]:
    """(ok, detail); ok is None when no verifier is available on this machine."""
    if os.name == 'nt':
        ps = ("$s = Get-AuthenticodeSignature -LiteralPath $env:TCP_SIGNED_FILE; "
              "Write-Output ($s.Status.ToString() + '|' + $s.SignerCertificate.Subject)")
        r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], capture_output=True, text=True,
                           env={**os.environ, 'TCP_SIGNED_FILE': str(path)})
        status, _, subject = r.stdout.strip().partition('|')
        return status == 'Valid', f'{status}: {subject}'
    tool = shutil.which('osslsigncode')
    if tool:
        r = subprocess.run([tool, 'verify', '-in', str(path)], capture_output=True, text=True)
        text = r.stdout + r.stderr
        ok = r.returncode == 0 and 'Signature verification: ok' in text
        signer = next((l.split(':', 1)[1].strip() for l in text.splitlines() if l.strip().startswith('Subject:')), '')
        return ok, ('ok' if ok else 'failed') + (f': {signer}' if signer else '')
    return None, 'no verifier (needs Windows PowerShell or osslsigncode)'


def collect(paths: list[Path]) -> list[tuple[Path, str]]:
    files = []
    for p in paths:
        if p.is_dir():
            for f in sorted(p.rglob('*')):
                if f.is_file() and f.suffix.lower() in PROGRAM_SUFFIXES:
                    files.append((f, f.relative_to(p).as_posix()))
        elif p.is_file():
            files.append((p, p.name))
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='+', type=Path)
    ap.add_argument('--publisher', default='SignPath Foundation', help='text the signer subject must contain')
    ap.add_argument('--product', default='TrueCombat: Platinum', help='required ProductName in the version resource')
    ap.add_argument('--no-version-check', action='store_true', help='skip the product name/version check (pre-0.40.0 builds)')
    ap.add_argument('--unsigned-ref', type=Path, help='folder with the gated unsigned binaries (same relative paths)')
    ap.add_argument('--structure-only', action='store_true', help='do not require a cryptographic verifier')
    ap.add_argument('--include-upstream', action='store_true', help='also require OpenAL64.dll to be signed')
    ap.add_argument('--json', type=Path)
    args = ap.parse_args(argv)

    report, failures, versions = [], 0, set()
    for path, rel in collect(args.paths):
        data = path.read_bytes()
        if data[:2] != b'MZ':
            continue  # e.g. EasyAntiCheat/Certificates/base.bin is a catalogue, not a program
        entry = {'file': rel, 'problems': []}
        if VENDOR.search(rel) or (UPSTREAM.search(rel) and not args.include_upstream):
            entry['skipped'] = 'vendor file' if VENDOR.search(rel) else 'upstream library (unsigned allowed)'
            report.append(entry)
            continue
        try:
            pe = PE(data)
        except ValueError as e:
            entry['problems'].append(str(e))
            report.append(entry); failures += 1
            continue
        certs = [c for c in pe.certificates() if c[1] == 0x0002]  # WIN_CERT_TYPE_PKCS_SIGNED_DATA
        if not certs:
            entry['problems'].append('not signed')
        else:
            subjects = signer_subjects(certs[0][2])
            entry['subjects'] = subjects
            if subjects and not any(args.publisher.lower() in s.lower() for s in subjects):
                entry['problems'].append(f'signer is not {args.publisher!r}: {subjects}')
            if not args.structure_only:
                ok, detail = verify_crypto(path)
                entry['verify'] = detail
                if ok is None:
                    entry['problems'].append(detail + ' (use --structure-only to accept structure checks)')
                elif not ok:
                    entry['problems'].append('signature invalid: ' + detail)
                elif args.publisher.lower() not in detail.lower() and not subjects:
                    entry['problems'].append(f'signer is not {args.publisher!r}: {detail}')
        if not args.no_version_check:
            vs = version_strings(data)
            entry['version'] = vs
            if vs.get('ProductName') != args.product:
                entry['problems'].append(f"ProductName {vs.get('ProductName')!r} is not {args.product!r}")
            if not vs.get('ProductVersion'):
                entry['problems'].append('no ProductVersion')
            else:
                versions.add(vs['ProductVersion'])
        if args.unsigned_ref:
            ref = args.unsigned_ref / rel
            if not ref.is_file():
                entry['problems'].append(f'no gated unsigned file at {ref}')
            elif not only_signature_differs(data, ref.read_bytes()):
                entry['problems'].append('differs from the gated unsigned file by more than the signature')
            else:
                entry['matches_gated'] = True
        failures += bool(entry['problems'])
        report.append(entry)

    if not args.no_version_check and len(versions) > 1:
        failures += 1
        report.append({'file': '*', 'problems': [f'product versions differ between files: {sorted(versions)}']})

    for e in report:
        state = 'skip' if 'skipped' in e else ('FAIL' if e['problems'] else 'ok')
        extra = e.get('skipped') or '; '.join(e['problems']) or e.get('verify', 'signed')
        print(f'{state:4}  {e["file"]}  {extra}')
    checked = sum(1 for e in report if 'skipped' not in e and e['file'] != '*')
    print(f'{checked} files checked, {failures} failing')
    if args.json:
        args.json.write_text(json.dumps({'checked': checked, 'failures': failures, 'files': report}, indent=2))
    return 1 if failures or not checked else 0


if __name__ == '__main__':
    sys.exit(main())
