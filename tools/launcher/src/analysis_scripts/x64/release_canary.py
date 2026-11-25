"""Post-publish canary: check the release exactly as players' launchers see it.

A publish (a full release or a launcher-only hotfix) is not done until this passes. It downloads, from the
public URLs (github.com, redirected to release-assets.githubusercontent.com):
  - releases/latest/download/update.txt: signature valid against the public key built into launchers
    (release_src/platinum_update_key.h), version as expected, every URL https;
  - files.txt: its SHA-256 matches files_sha256;
  - 3 random per-file assets (each under 300 MB): size and SHA-256 match files.txt;
  - the launcher named by the feed (launcher=): size and SHA-256 match, version marker as advertised, and, with
    --launcher, byte-identical to the file that passed the launcher repair suite;
  - TrueCombat-Platinum-Setup.exe answers on releases/latest/download (the website's download button).
Writes experiments/release-canary/<version>-<UTC time>.json; exit 0 only when everything passed.

  python analysis_scripts/x64/release_canary.py --version 0.38.1-sandbox35 [--launcher <shipped exe>] [--seed N]
"""
from pathlib import Path
import argparse, hashlib, json, random, re, sys, time, urllib.request
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--version', required=True)
p.add_argument('--repo', default='Annoximeme/TrueCombat-Platinum')
p.add_argument('--launcher', type=Path, default=None, help='the launcher that passed the gate; the published one must be identical')
p.add_argument('--samples', type=int, default=3)
p.add_argument('--seed', type=int, default=None)
args = p.parse_args()
checks = []
def check(name, ok, detail=''):
    checks.append({'check': name, 'pass': bool(ok), 'detail': detail}); print(('PASS ' if ok else 'FAIL ') + name + (': ' + detail if detail else ''), flush=True)
    return ok
def fetch(url, limit=400 << 20):
    request = urllib.request.Request(url, headers={'User-Agent': 'TrueCombatPlatinumLauncher/canary'})
    with urllib.request.urlopen(request, timeout=60) as r:
        data = r.read(limit + 1); final = r.geturl()
    assert len(data) <= limit, f'{url} is larger than {limit} bytes'
    return data, final
def public_key():
    from cryptography.hazmat.primitives.asymmetric import ec
    raw = bytes(int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]{2})', (ROOT/'release_src/platinum_update_key.h').read_text()))
    assert len(raw) == 64
    return ec.EllipticCurvePublicNumbers(int.from_bytes(raw[:32], 'big'), int.from_bytes(raw[32:], 'big'), ec.SECP256R1()).public_key()
def signature_ok(text):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    from cryptography.exceptions import InvalidSignature
    marker = text.rfind(b'\nsignature=')
    if marker < 0: return False
    body, sig = text[:marker + 1], bytes.fromhex(text[marker + 11:].strip().decode())
    try:
        public_key().verify(encode_dss_signature(int.from_bytes(sig[:32], 'big'), int.from_bytes(sig[32:], 'big')), body, ec.ECDSA(hashes.SHA256())); return True
    except InvalidSignature: return False

base = f'https://github.com/{args.repo}/releases'
try:
    feed, final = fetch(f'{base}/latest/download/update.txt', 64 << 10)
    check('update.txt reachable', True, final.split('?')[0])
    check('update.txt signature', signature_ok(feed))
    fields = dict(l.split('=', 1) for l in feed.decode('utf-8').splitlines() if '=' in l)
    check('latest version', fields.get('version') == args.version, fields.get('version', ''))
    check('https only', all(v.startswith('https://') for k, v in fields.items() if k in ('package', 'files', 'launcher', 'page')))
    listing, final = fetch(fields['files'], 4 << 20)
    check('files.txt sha256', hashlib.sha256(listing).hexdigest() == fields.get('files_sha256', '').lower(), final.split('?')[0].split('/')[2])
    entries = [l.split(' ', 3) for l in listing.decode('utf-8').splitlines() if len(l.split(' ', 3)) == 4]
    pool = [e for e in entries if int(e[1]) < 300 << 20]
    rng = random.Random(args.seed)
    folder = fields['files'].rsplit('/', 1)[0]
    for digest, size, asset, rel in rng.sample(pool, min(args.samples, len(pool))):
        data, final = fetch(f'{folder}/{asset}', int(size) + 1)
        check(f'asset {rel}', len(data) == int(size) and hashlib.sha256(data).hexdigest() == digest.lower(), f'{int(size)} bytes from {final.split("?")[0].split("/")[2]}')
    if 'launcher' in fields:
        data, _ = fetch(fields['launcher'], 64 << 20)
        ok = len(data) == int(fields['launcher_bytes']) and hashlib.sha256(data).hexdigest() == fields['launcher_sha256'].lower()
        marker = f"TrueCombatPlatinumLauncher/{fields.get('launcher_version', '')}\0".encode('utf-16-le')
        check('launcher asset', ok and marker in data, fields.get('launcher_version', ''))
        if args.launcher:
            check('launcher is the gated build', hashlib.sha256(data).hexdigest() == hashlib.sha256(args.launcher.read_bytes()).hexdigest())
    request = urllib.request.Request(f'{base}/latest/download/TrueCombat-Platinum-Setup.exe', method='HEAD', headers={'User-Agent': 'TrueCombatPlatinumLauncher/canary'})
    with urllib.request.urlopen(request, timeout=60) as r: check('website installer', r.status == 200, r.geturl().split('?')[0].split('/')[2])
except Exception as e:
    check('canary run', False, f'{type(e).__name__}: {e}')
passed = bool(checks) and all(c['pass'] for c in checks)
out = ROOT/'experiments'/'release-canary'; out.mkdir(parents=True, exist_ok=True)
stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
(out/f'{args.version}-{stamp}.json').write_text(json.dumps({'version': args.version, 'when': stamp, 'passed': passed, 'checks': checks}, indent=2), encoding='utf-8')
print('canary:', 'PASSED - publish complete' if passed else 'FAILED - the publish is NOT done; fix and re-run')
sys.exit(0 if passed else 1)
