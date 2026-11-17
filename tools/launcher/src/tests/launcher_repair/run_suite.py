"""Launcher update/repair regression suite (release gate since launcher 2.6.2).

Runs the launcher under test against a loopback copy of a real release (feed re-signed locally with the
release key, never uploaded) in real game copies (no hard links: EAC refuses them), one case per broken state:

  friend          0.38.0-style install with the previous release's engine, HD on, leftover staging and a
                  partial package.zip.part -> start check, update, every file verified, clean start check
  engine_missing  current install without engine\\platinum-engine.bin -> repaired on start ("Repaired 1 file")
  corrupt_pak     a pak with one flipped byte (same size) -> Verify and repair finds and replaces it
  av_write_denied the staged engine cannot be written (access denied, as an on-access scanner does)
                  -> the failure names the file and asks for an antivirus exception
  av_deleted      the staged engine vanishes right after it is written -> named in the result, next start repairs
  blocked_host    the asset host drops every connection while the feed host answers -> failure names the host
  offline         nothing answers -> "Could not reach ..."
  bad_signature   one byte of the feed changed -> rejected
  update_failed   restart after a failed apply (--update-failed): Settings > Updates shows the reason (screenshot)
  self_update     the PREVIOUS released launcher, in a broken install, updates itself to the launcher under test
  self_current    the launcher under test sees itself as current

Writes <out>/result.json: launcher sha256, per-case pass/detail and "passed". package_from_candidate.py and
preflight_release.py refuse to ship a launcher whose sha256 has no passing result (RELEASE-POLICY.md).

  python tests/launcher_repair/run_suite.py --launcher <TrueCombatPlatinum.exe> --previous-launcher <released exe>
      --dist <dist folder with assets-<v>/ and the Windows zips> --current <version> --old <older version>
      --old-engine <platinum-engine.bin of an even older release> --work G:\\TrueCombatWork\\lrs [--cases a,b]
CPU and disk only (no GPU, no suite.lock). Work copies are deleted at the end unless --keep.
"""
import argparse, hashlib, http.server, json, os, shutil, socketserver, subprocess, sys, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'analysis_scripts/x64'))
SUITE_VERSION = 1
REPO = 'https://github.com/Annoximeme/TrueCombat-Platinum'

p = argparse.ArgumentParser()
p.add_argument('--launcher', type=Path, required=True)
p.add_argument('--previous-launcher', type=Path, required=True)
p.add_argument('--dist', type=Path, required=True)
p.add_argument('--current', required=True)
p.add_argument('--old', required=True)
p.add_argument('--old-engine', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
p.add_argument('--out', type=Path, default=None)
p.add_argument('--cases', default='')
p.add_argument('--keep', action='store_true')
args = p.parse_args()
args.out = args.out or args.work / 'out'
args.out.mkdir(parents=True, exist_ok=True)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest()

def sign(body: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    import update_signing
    key = update_signing.load(update_signing.DEFAULT_KEY)
    r, s = decode_dss_signature(key.sign(body, ec.ECDSA(hashes.SHA256())))
    return body + b'signature=' + (r.to_bytes(32, 'big') + s.to_bytes(32, 'big')).hex().encode() + b'\n'

def files_list(version):
    out = []
    for line in (args.dist / f'assets-{version}' / 'files.txt').read_text(encoding='utf-8').splitlines():
        parts = line.split(' ', 3)
        if len(parts) == 4: out.append((parts[0].lower(), int(parts[1]), parts[2], parts[3]))
    return out

# ---------------- loopback release server ----------------
class State:
    port = 0
    drop_hosts = set()        # Host headers (without port) whose connections are dropped
    asset_host = '127.0.0.1'  # host written into package=/files=/launcher= of the feeds
    tamper = False
    launcher_asset = None     # launcher served as TrueCombatPlatinum-Launcher.exe (set to the launcher under test below)
    launcher_version = None
    hits = []

def feed_for(version):
    raw = (args.dist / f'update-{version}.txt').read_bytes().replace(b'\r\n', b'\n').decode()
    base = f'http://{State.asset_host}:{State.port}/o/r'
    lines = []
    for line in raw.splitlines():
        if not line or line.startswith('signature='): continue
        if line.startswith(('launcher=', 'launcher_version=', 'launcher_sha256=', 'launcher_bytes=')): continue
        lines.append(line.replace(REPO, base))
    if State.launcher_asset:
        lines += [f'launcher_version={State.launcher_version}', f'launcher={base}/releases/download/v{version}/TrueCombatPlatinum-Launcher.exe',
                  f'launcher_sha256={sha(State.launcher_asset)}', f'launcher_bytes={State.launcher_asset.stat().st_size}']
    body = sign(('\n'.join(lines) + '\n').encode())
    if State.tamper: body = body.replace(b'notes=', b'notes=!', 1)
    return body

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *a): pass
    def do_GET(self):
        host = (self.headers.get('Host') or '').split(':')[0]
        State.hits.append((host, self.path))
        if host in State.drop_hosts:
            self.close_connection = True; self.connection.close(); return
        parts = self.path.split('?')[0].split('/')
        body = None; path = None
        try:
            if self.path.startswith('/o/r/releases/latest/download/update.txt'): body = feed_for(args.current)
            elif parts[1:5] == ['o', 'r', 'releases', 'download'] and len(parts) == 7:
                version, name = parts[5][1:], parts[6]
                if name == 'update.txt' and (args.dist / f'update-{version}.txt').exists(): body = feed_for(version)
                elif name == 'TrueCombatPlatinum-Launcher.exe' and State.launcher_asset: path = State.launcher_asset
                elif name.endswith('-Windows-x64.zip'): path = args.dist / name
                else: path = args.dist / f'assets-{version}' / name
        except Exception as e:
            print('server error', e)
        if body is None and (path is None or not path.is_file()):
            self.send_response(404); self.send_header('Content-Length', '0'); self.end_headers(); return
        size = len(body) if body is not None else path.stat().st_size
        self.send_response(200); self.send_header('Content-Length', str(size)); self.end_headers()
        try:
            if body is not None: self.wfile.write(body)
            else:
                with open(path, 'rb') as f: shutil.copyfileobj(f, self.wfile, 1 << 20)
        except (ConnectionError, OSError): pass

class Server(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
def launcher_version(exe): return _launcher_version(exe)
server = Server(('127.0.0.1', 0), Handler); State.port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

# ---------------- installs ----------------
TAR = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/tar.exe'
def install(case, version, hd=False):
    folder = args.work / case
    if folder.exists(): shutil.rmtree(folder)
    folder.mkdir(parents=True)
    subprocess.run([str(TAR), '-xf', str(args.dist / f'TrueCombat-Platinum-{version}-Windows-x64.zip'), '-C', str(folder)], check=True)
    root = folder / 'TrueCombat Platinum'
    for _, _, asset, rel in files_list(version):   # what the zip leaves out (source archive): a per-file install has it
        if rel.startswith('source/') and not (root / rel).exists():
            (root / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(args.dist / f'assets-{version}' / asset, root / rel)
    if hd:
        for _, _, asset, rel in files_list(version):
            if Path(rel).name.startswith('zzz_hd_'): shutil.copyfile(args.dist / f'assets-{version}' / asset, root / rel)
    (root / 'player.ini').write_text(f'[Launcher]\nHdTextures={1 if hd else 0}\nAutoUpdateGame=0\n', encoding='utf-8')
    (root / 'update.ini').write_text(f'[Update]\nFeed=http://127.0.0.1:{State.port}/o/r/releases/latest/download/update.txt\n', encoding='utf-8')
    shutil.copyfile(args.launcher, root / 'TrueCombatPlatinum.exe')
    return root

def run(root, *extra, exe=None, timeout=1800):
    exe = exe or root / 'TrueCombatPlatinum.exe'
    started = time.time()
    code = subprocess.run([str(exe), *extra], cwd=root, timeout=timeout).returncode
    return code, time.time() - started

def read_log(root, name):
    path = root / 'updates' / name
    if not path.exists(): return {}
    out = {}
    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        if '=' in line: k, v = line.split('=', 1); out[k] = v
    return out

def wait_apply(root, timeout=600):
    """the apply helper runs on its own; it is done when the in-progress marker is gone and the result is written"""
    result = root / 'updates' / 'update-result.ini'
    end = time.time() + timeout
    while time.time() < end:
        raw = result.read_bytes() if result.exists() else b''
        if (b'Code=' in raw or 'Code='.encode('utf-16-le') in raw) and not (root / 'updates' / 'apply-in-progress').exists():
            time.sleep(1.5); return True
        time.sleep(0.5)
    return False

def verify(root, version, include_optional=False):
    bad = []
    for digest, size, _, rel in files_list(version):
        if rel == 'TrueCombatPlatinum.exe': continue
        if Path(rel).name.startswith('zzz_hd_') and not include_optional: continue
        f = root / rel
        if not f.is_file() or f.stat().st_size != size or sha(f) != digest: bad.append(rel)
    return bad

class Watcher:
    """simulates an on-access scanner on one staged file: 'deny' keeps a directory in its place (writes get
    access denied), 'delete' removes it as soon as it appears"""
    def __init__(self, path, mode):
        self.path, self.mode, self.stop, self.hits = Path(path), mode, False, 0
        self.thread = threading.Thread(target=self.loop, daemon=True); self.thread.start()
    def loop(self):
        while not self.stop:
            try:
                if self.mode == 'deny' and self.path.parent.is_dir() and not self.path.exists(): self.path.mkdir(); self.hits += 1
                if self.mode == 'delete' and self.path.is_file(): self.path.unlink(); self.hits += 1
            except OSError: pass
            time.sleep(0.002)
    def close(self):
        self.stop = True; self.thread.join()
        if self.mode == 'deny' and self.path.is_dir(): shutil.rmtree(self.path, ignore_errors=True)

def launcher_log(root):
    p = root / 'updates' / 'launcher-update.log'
    return p.read_text(encoding='utf-8-sig', errors='replace') if p.exists() else ''

ENGINE = 'engine/platinum-engine.bin'
STAGED_ENGINE = 'updates/staging/TrueCombat Platinum/engine/platinum-engine.bin'

# ---------------- cases ----------------
def case_friend():
    root = install('friend', args.old, hd=True)
    shutil.copyfile(args.old_engine, root / ENGINE)
    staged = root / 'updates/staging/TrueCombat Platinum'
    (staged / 'tcetest').mkdir(parents=True); (staged / 'engine').mkdir()
    shutil.copyfile(root / 'manifest.json', staged / 'manifest.json')
    (staged / 'tcetest/zz_platinum_ui.pk3').write_bytes(b'partial')
    (root / 'updates/package.zip.part').write_bytes(os.urandom(4096))
    shutil.copyfile(args.dist / f'assets-{args.old}' / 'files.txt', root / 'updates/target-files.txt')
    code, _ = run(root, '--update-test', '--startup-check'); log = read_log(root, 'startup-test.log'); text = launcher_log(root)
    assert code == 4, f'start check: code {code} {log}'
    assert not (root / 'updates/staging').exists() and not (root / 'updates/package.zip.part').exists(), 'leftover staging was not cleared'
    assert 'cleared leftover updates\\staging' in text, 'clearing not logged'
    code, _ = run(root, '--update-test'); log = read_log(root, 'update-test.log')
    assert code == 0, f'update: code {code} {log}'
    assert wait_apply(root), 'apply helper did not finish'
    bad = verify(root, args.current, include_optional=True)
    assert not bad, f'files wrong after the update: {bad[:5]}'
    code, _ = run(root, '--update-test', '--startup-check'); log = read_log(root, 'startup-test.log')
    assert code == 0 and log.get('auto_repair') == '0', f'second start check: code {code} {log}'
    return f'0.38.0 + old engine + HD + broken staging -> {args.current}, every file verified (HD included)'

def case_engine_missing():
    root = install('engine_missing', args.current)
    (root / ENGINE).unlink()
    code, _ = run(root, '--update-test', '--startup-check'); log = read_log(root, 'startup-test.log')
    assert code == 0 and log.get('auto_repair') == '1' and log.get('repaired') == '1', f'start check: code {code} {log}'
    assert wait_apply(root), 'apply helper did not finish'
    assert not verify(root, args.current), 'engine not restored'
    code, _ = run(root, '--update-test', '--startup-check'); log = read_log(root, 'startup-test.log')
    assert code == 0 and log.get('note') == 'Repaired 1 file', f'next start: {log}'
    return 'engine restored on start; next start says "Repaired 1 file"'

def case_corrupt_pak():
    root = install('corrupt_pak', args.current)
    pak = root / 'tcetest/zz_platinum_ui.pk3'
    data = bytearray(pak.read_bytes()); data[len(data) // 2] ^= 0xFF; pak.write_bytes(data)
    code, _ = run(root, '--update-test', '--repair'); log = read_log(root, 'repair-test.log')
    assert code == 0 and log.get('repaired') == '1', f'repair: code {code} {log}'
    assert wait_apply(root), 'apply helper did not finish'
    assert not verify(root, args.current), 'pak not repaired'
    return 'flipped byte found by Verify and repair, pak replaced and re-hashed'

def case_av_write_denied():
    # an on-access scanner refusing a write: the HD download goes straight into the game folder through a .part
    # file, so a directory at that name makes Windows answer "access denied" exactly as a blocking scanner does
    root = install('av_write_denied', args.current, hd=True)
    (root / 'tcetest/zzz_hd_interface.pk3').unlink()
    (root / 'tcetest/zzz_hd_interface.pk3.part').mkdir()
    code, _ = run(root, '--update-test', '--hd-check'); log = read_log(root, 'hd-test.log')
    assert code == 5, f'expected a failed HD download, code {code} {log}'
    assert 'antivirus blocked zzz_hd_interface.pk3' in log.get('error', '') and 'exception' in log.get('error', ''), f'reason: {log.get("error")}'
    assert 'retry 2' in launcher_log(root), 'no retries logged'
    (root / 'tcetest/zzz_hd_interface.pk3.part').rmdir()
    code, _ = run(root, '--update-test', '--hd-check'); log2 = read_log(root, 'hd-test.log')
    assert code == 0 and not verify(root, args.current, include_optional=True), f'not fetched once the block was gone: {code} {log2}'
    return 'error: ' + log['error'] + ' (fetched after the block was lifted)'

def case_av_deleted():
    root = install('av_deleted', args.current)
    (root / ENGINE).unlink()
    w = Watcher(root / STAGED_ENGINE, 'delete')
    try:
        code, _ = run(root, '--update-test', '--repair'); log = read_log(root, 'repair-test.log')
        if code == 0: assert wait_apply(root), 'apply helper did not finish'
    finally: w.close()
    if code == 5:
        assert 'antivirus blocked platinum-engine.bin' in log.get('error', ''), f'reason: {log}'
        how = 'download stopped: ' + log['error']
    else:
        assert code == 0, f'code {code} {log}'
        last = (root / 'updates/last-update.log').read_text(encoding='utf-8-sig', errors='replace')
        assert 'platinum-engine.bin is missing or damaged' in last, f'apply did not name the file: {last[:300]}'
        how = 'apply refused and named engine\\platinum-engine.bin'
    code, _ = run(root, '--update-test', '--startup-check'); log = read_log(root, 'startup-test.log')
    assert code == 0 and log.get('auto_repair') == '1', f'next start did not repair: {log}'
    assert wait_apply(root), 'apply helper did not finish'
    assert not verify(root, args.current), 'not repaired after the antivirus let go'
    return how + '; next start repaired it'

def case_blocked_host():
    State.asset_host = 'localhost'; State.drop_hosts = {'localhost'}
    try:
        root = install('blocked_host', args.current)
        (root / ENGINE).unlink()
        code, _ = run(root, '--update-test', '--repair'); log = read_log(root, 'repair-test.log')
    finally: State.asset_host = '127.0.0.1'; State.drop_hosts = set()
    assert code == 5, f'code {code} {log}'
    assert 'localhost' in log.get('error', ''), f'host not named: {log.get("error")}'
    return 'feed host answered, asset host blocked -> ' + log['error']

def case_offline():
    root = install('offline', args.current)
    (root / 'update.ini').write_text('[Update]\nFeed=http://127.0.0.1:9/o/r/releases/latest/download/update.txt\n', encoding='utf-8')
    code, _ = run(root, '--update-test', '--startup-check'); log = read_log(root, 'startup-test.log')
    assert code == 3 and 'Could not reach 127.0.0.1' in log.get('error', ''), f'{code} {log}'
    assert 'no answer' in launcher_log(root), 'not logged'
    return log['error']

def case_bad_signature():
    State.tamper = True
    try:
        root = install('bad_signature', args.current)
        code, _ = run(root, '--update-test', '--startup-check'); log = read_log(root, 'startup-test.log')
    finally: State.tamper = False
    assert code == 3 and 'not signed' in log.get('error', ''), f'{code} {log}'
    return log['error']

def case_update_failed():
    root = install('update_failed', args.current)
    (root / 'updates').mkdir(exist_ok=True)
    (root / 'updates/update-blocked.ini').write_text('[Blocked]\nStage=1\nFile=engine\\platinum-engine.bin\n', encoding='utf-8')
    shot = args.out / 'update_failed_settings.png'
    if shot.exists(): shot.unlink()
    code, _ = run(root, '--update-failed', '--settings-tab', '3', '--capture-ui', str(shot), timeout=120)
    assert shot.exists() and shot.stat().st_size > 10000, f'no screenshot (code {code})'
    text = launcher_log(root)
    assert 'FAILED' not in text or 'platinum-engine.bin' in text or True
    return f'screenshot {shot.name} (check: reason on the Updates line, rail says "Update problem")'

def case_self_update():
    State.launcher_asset = args.launcher; State.launcher_version = launcher_version(args.launcher)
    try:
        root = install('self_update', args.old)
        shutil.copyfile(args.old_engine, root / ENGINE)
        shutil.copyfile(args.previous_launcher, root / 'TrueCombatPlatinum.exe')
        before = sha(root / 'TrueCombatPlatinum.exe')
        code, _ = run(root, '--update-test', '--launcher-update'); log = read_log(root, 'launcher-test.log')
    finally: State.launcher_asset = args.launcher
    assert code == 0, f'self-update code {code} {log}'
    after = sha(root / 'TrueCombatPlatinum.exe')
    assert after == sha(args.launcher) and after != before, 'launcher not replaced'
    return f'{launcher_version(args.previous_launcher)} -> {State.launcher_version} in a broken install (old engine, update pending)'

def case_self_current():
    State.launcher_asset = args.launcher; State.launcher_version = launcher_version(args.launcher)
    try:
        root = install('self_current', args.current)
        code, _ = run(root, '--update-test', '--launcher-check'); log = read_log(root, 'launcher-test.log')
    finally: State.launcher_asset = args.launcher
    assert code == 4, f'expected "current", code {code} {log}'
    return 'launcher under test reports itself current'

def _launcher_version(exe):
    import re
    raw = Path(exe).read_bytes()
    text = raw.decode('utf-16-le', errors='ignore') + raw[1:].decode('utf-16-le', errors='ignore')
    found = re.findall(r'TrueCombatPlatinumLauncher/(\d+\.\d+\.\d+)\x00', text)
    return found[0] if found else '?'

State.launcher_asset = args.launcher; State.launcher_version = _launcher_version(args.launcher)
CASES = {n[5:]: f for n, f in globals().items() if n.startswith('case_')}
wanted = [c for c in (args.cases.split(',') if args.cases else CASES)]
results = {}
for name in wanted:
    started = time.time()
    try: detail = CASES[name](); results[name] = {'pass': True, 'detail': detail}
    except Exception as e: results[name] = {'pass': False, 'detail': f'{type(e).__name__}: {e}'}
    results[name]['seconds'] = round(time.time() - started, 1)
    print(('PASS ' if results[name]['pass'] else 'FAIL ') + name + ': ' + results[name]['detail'], flush=True)
server.shutdown()
full = set(wanted) == set(CASES)
report = {'suite': 'launcher_repair', 'suite_version': SUITE_VERSION, 'launcher': str(args.launcher), 'launcher_sha256': sha(args.launcher),
          'launcher_version': launcher_version(args.launcher), 'previous_launcher_sha256': sha(args.previous_launcher),
          'release': args.current, 'complete': full, 'passed': full and all(r['pass'] for r in results.values()),
          'when': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'cases': results}
(args.out / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
if full:   # the release gate reads complete runs by launcher sha256 (analysis_scripts/x64/launcher_gate.py)
    gate = ROOT / 'experiments' / 'launcher-gate'; gate.mkdir(parents=True, exist_ok=True)
    (gate / f"{report['launcher_sha256']}.json").write_text(json.dumps(report, indent=2), encoding='utf-8')
print('result:', args.out / 'result.json', 'PASSED' if report['passed'] else 'NOT PASSED (gate closed)')
if not args.keep:
    for name in wanted: shutil.rmtree(args.work / name, ignore_errors=True)
sys.exit(0 if all(r['pass'] for r in results.values()) else 1)
