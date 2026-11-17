#!/usr/bin/env python3
"""Send a source tree to the cloud for building and testing, and fetch the results.

Only the files that differ from a published release's source snapshot are sent
(usually a few MB instead of 50), into a hidden draft release `ci-<name>`.
GitHub then builds and tests it (.github/workflows/cloud-build.yml) and puts the
results back into the same draft. Nothing is published and nothing runs on the PC
or the VPS.

  request.py send --root <source root> --base v0.37.3-sandbox33 --name integ038 \
                  [--jobs scan,windows,linux,eac,bots] [--maps "obj_village obj_snow"] [--minutes 4]
  request.py status --name integ038
  request.py fetch  --name integ038 --out <folder>     downloads results, logs and binaries
  request.py clean  --name integ038                    deletes the draft when you are done

<source root> holds game_src, release_src, reference/etlegacy and analysis_scripts
(a candidate's frozen `source` folder, or a work tree such as integ038\\src).
Python standard library only; token from GITHUB_TOKEN/GH_TOKEN or `gh auth token`.
"""
import argparse, hashlib, io, json, os, sys, time, urllib.request, zipfile, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import draft  # noqa: E402

FOLDERS = ('game_src', 'release_src', 'reference/etlegacy', 'analysis_scripts')
SKIP_DIRS = {'.git', '.vs', '__pycache__', 'build', 'out', '.cache'}
SKIP_EXT = {'.obj', '.o', '.pdb', '.ilk', '.exe', '.dll', '.lib', '.a', '.log', '.pyc'}
SOURCE_ASSET = 'f__source__native-sandbox-source.zip'
CACHE = Path(os.environ.get('TCP_CI_CACHE', Path.home() / '.cache' / 'truecombat-ci'))


def base_zip(tag):
    path = CACHE / f'{tag}-source.zip'
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        url = f'https://github.com/{draft.REPO}/releases/download/{tag}/{SOURCE_ASSET}'
        print('downloading base source', url)
        tmp = path.with_suffix('.part')
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(path)
    return path


def crc(path):
    value = 0
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            value = zlib.crc32(chunk, value)
    return value


def local_files(root):
    for folder in FOLDERS:
        top = root / folder
        if not top.is_dir():
            sys.exit(f'{top} is missing: --root must hold {", ".join(FOLDERS)}')
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix.lower() not in SKIP_EXT:
                    yield p.relative_to(root).as_posix(), p


def send(a):
    root = Path(a.root).resolve()
    with zipfile.ZipFile(base_zip(a.base)) as z:
        base = {i.filename: i for i in z.infolist() if not i.is_dir()}
    changed, seen = [], set()
    for rel, p in local_files(root):
        seen.add(rel)
        info = base.get(rel)
        if info is None or info.file_size != p.stat().st_size or info.CRC != crc(p):
            changed.append((rel, p))
    deleted = sorted(n for n in base if n.startswith(tuple(f + '/' for f in FOLDERS)) and n not in seen
                     and not any(part in SKIP_DIRS for part in n.split('/'))
                     and Path(n).suffix.lower() not in SKIP_EXT)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, p in changed:
            z.write(p, rel)
    overlay = buf.getvalue()
    request = {'name': a.name, 'base': a.base, 'jobs': a.jobs.split(','), 'maps': a.maps.split(),
               'minutes': a.minutes, 'deleted': deleted, 'changed': len(changed),
               'overlay_sha256': hashlib.sha256(overlay).hexdigest(),
               'sent': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    print(f'{len(changed)} changed/new files ({len(overlay)/1e6:.1f} MB), {len(deleted)} deleted, vs {a.base}')
    if a.dry_run:
        for rel, _ in changed[:200]:
            print('  ', rel)
        return
    deps(a.eos_include)
    tag = 'ci-' + a.name
    draft.ensure(tag, f'Cloud build: {a.name}')
    for asset in draft.find(tag)['assets']:  # a new request starts without old results
        if asset['name'] != 'overlay.zip':
            draft.call('DELETE', f"{draft.API}/repos/{draft.REPO}/releases/assets/{asset['id']}")
    tmp = CACHE / f'{tag}-overlay.zip'
    tmp.write_bytes(overlay)
    draft.put(tag, str(tmp), 'overlay.zip')
    (CACHE / f'{tag}-request.json').write_text(json.dumps(request, indent=1))
    draft.put(tag, str(CACHE / f'{tag}-request.json'), 'request.json')
    start(tag)


def deps(include):
    """One-time: EOS SDK headers (not redistributable) into the hidden draft ci-deps."""
    r = draft.find('ci-deps')
    if r and any(x['name'] == 'eos-sdk-include.zip' for x in r['assets']):
        return
    inc = Path(include)
    if not (inc / 'eos_sdk.h').exists():
        print(f'note: no EOS SDK headers at {inc}; cloud builds run without Easy Anti-Cheat until ci-deps has them')
        return
    zpath = CACHE / 'eos-sdk-include.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in inc.rglob('*'):
            if p.is_file():
                z.write(p, 'Include/' + p.relative_to(inc).as_posix())
    draft.ensure('ci-deps', 'Cloud build: private SDK headers')
    draft.put('ci-deps', str(zpath), 'eos-sdk-include.zip')


def start(tag):
    # repository_dispatch is the trigger every token with repo write access can use.
    draft.call('POST', f'{draft.API}/repos/{draft.REPO}/dispatches',
               {'event_type': 'cloud-build', 'client_payload': {'request': tag}})
    print(f'started cloud build for {tag}; check with: request.py status --name {tag[3:]}')


def results(tag):
    r = draft.find(tag)
    if not r:
        sys.exit(f'no draft {tag}')
    return r, {a['name']: a for a in r['assets']}


def status(a):
    tag = 'ci-' + a.name
    deadline = time.time() + a.wait * 60
    while True:
        r, assets = results(tag)
        req = json.loads(draft.call('GET', f"{draft.API}/repos/{draft.REPO}/releases/assets/{assets['request.json']['id']}",
                                    headers={'Accept': 'application/octet-stream'}, raw=True))
        done = {}
        for job in req['jobs']:
            name = f'{job}-result.json'
            if name in assets:
                done[job] = json.loads(draft.call('GET', f"{draft.API}/repos/{draft.REPO}/releases/assets/{assets[name]['id']}",
                                                  headers={'Accept': 'application/octet-stream'}, raw=True))
        if len(done) == len(req['jobs']) or time.time() >= deadline:
            break
        time.sleep(30)
    for job in req['jobs']:
        res = done.get(job)
        print(f"{job:8} {res['result'] if res else 'running/queued'}" + (f"  {res.get('note','')}" if res else ''))
    if len(done) < len(req['jobs']):
        sys.exit(2)
    sys.exit(0 if all(r['result'] == 'pass' for r in done.values()) else 1)


def fetch(a):
    tag = 'ci-' + a.name
    _, assets = results(tag)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for name in assets:
        if name not in ('overlay.zip',):
            draft.get(tag, name, str(out / name))


def clean(tag):
    r = draft.find(tag)
    if not r:
        sys.exit(f'no draft {tag}')
    draft.call('DELETE', f"{draft.API}/repos/{draft.REPO}/releases/{r['id']}")
    print('deleted draft', tag)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    x = s.add_parser('send'); x.add_argument('--root', required=True); x.add_argument('--base', required=True)
    x.add_argument('--name', required=True); x.add_argument('--jobs', default='scan,windows,linux,bots')
    x.add_argument('--maps', default='obj_village obj_railhouse obj_snow obj_northport'); x.add_argument('--minutes', type=int, default=4)
    x.add_argument('--dry-run', action='store_true')
    x.add_argument('--eos-include', default=r'C:/TrueCombatWork/eac/sdk/SDK/Include')
    x = s.add_parser('status'); x.add_argument('--name', required=True); x.add_argument('--wait', type=int, default=0, help='minutes to wait for all jobs')
    x = s.add_parser('fetch'); x.add_argument('--name', required=True); x.add_argument('--out', required=True)
    x = s.add_parser('clean'); x.add_argument('--name', required=True)
    x = s.add_parser('restart'); x.add_argument('--name', required=True)
    a = p.parse_args()
    if not all(c.isalnum() or c in '-_.' for c in a.name):
        sys.exit('--name: letters, digits, - _ . only')
    {'send': send, 'status': status, 'fetch': fetch,
     'clean': lambda a: clean('ci-' + a.name),
     'restart': lambda a: start('ci-' + a.name)}[a.cmd](a)


if __name__ == '__main__':
    main()
