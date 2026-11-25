"""Write the update.txt feed for a packaged release (GitHub Releases layout).

Usage: python analysis_scripts/x64/make_update_feed.py --version 0.28.0-sandbox19 --repo Annoximeme/TrueCombat-Platinum [--notes "..."]

Output: dist/update-<version>.txt. Upload it to the GitHub release as
"update.txt" next to the zip.

The launcher is versioned on its own (release_src/platinum_launcher_version.h).
The feed always names it (launcher_version=, launcher=, launcher_sha256=,
launcher_bytes=), and dist/assets-<version>/TrueCombatPlatinum-Launcher.exe
must be uploaded under exactly that name. Launchers that read such a feed
update themselves from that asset and leave the EXE out of game updates.

Launcher-only update (no new game release):
  python analysis_scripts/x64/make_update_feed.py --version <current release> --repo <repo> --launcher-hotfix <new TrueCombatPlatinum.exe>
rewrites that release's update.txt with the new launcher fields only (game
fields unchanged), re-signs it and stages the new launcher asset. Replace both
assets on the current latest release (gh release upload --clobber). The launcher reads
https://github.com/<repo>/releases/latest/download/update.txt, so the newest
published (non-prerelease) release is always the one offered.
"""
from pathlib import Path
import argparse, hashlib, re, shutil, subprocess, sys
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--version', required=True)
parser.add_argument('--repo', required=True)
parser.add_argument('--notes', default='')
parser.add_argument('--master', default='', help='public master server host:port announced to launchers')
parser.add_argument('--discord', default='', help='Discord application id for Rich Presence')
parser.add_argument('--unsigned', action='store_true', help='skip signing (launchers with a key will reject it)')
parser.add_argument('--delta', action='store_true', help='also publish per-file assets + files.txt for smaller updates')
parser.add_argument('--launcher-hotfix', type=Path, default=None, help='launcher-only update: new launcher EXE for the existing release feed')
parser.add_argument('--optional', default='zzz_hd_', help='with --delta: comma-separated file-name prefixes of .pk3 files players may skip '
                    '(Settings > Updates > HD textures, launcher 2.5.0+); signed as optional=. Empty: none')
args = parser.parse_args()
sys.path.insert(0, str(ROOT/'analysis_scripts')); import launcher_version
LAUNCHER_ASSET = 'TrueCombatPlatinum-Launcher.exe'
def launcher_fields(exe, version, tag):
    assert launcher_version.exe_version_ok(exe, version), f'{exe} is not launcher {version} (version marker missing)'
    # launcher 2.6.2 release gate: the launcher repair suite passed for exactly this file (launcher_gate.py)
    sys.path.insert(0, str(ROOT/'analysis_scripts/x64')); import launcher_gate; launcher_gate.require(exe, 'put in a feed')
    assets = ROOT/'dist'/f'assets-{args.version}'; assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exe, assets/LAUNCHER_ASSET)
    data = (assets/LAUNCHER_ASSET).read_bytes()
    print('launcher asset:', assets/LAUNCHER_ASSET, version, '- upload it to the release under this exact name')
    return (f'launcher_version={version}\n'
            f'launcher=https://github.com/{args.repo}/releases/download/{tag}/{LAUNCHER_ASSET}\n'
            f'launcher_sha256={hashlib.sha256(data).hexdigest()}\n'
            f'launcher_bytes={len(data)}\n')
def sign(out):
    if not args.unsigned:
        subprocess.run([sys.executable, str(ROOT/'analysis_scripts/x64/update_signing.py'), '--sign', str(out)], check=True)
        subprocess.run([sys.executable, str(ROOT/'analysis_scripts/x64/update_signing.py'), '--verify', str(out)], check=True)
    print(out); print(out.read_text(encoding='utf-8'))
assert re.fullmatch(r'\d+\.\d+\.\d+-sandbox\d+', args.version)
assert re.fullmatch(r'[A-Za-z0-9-]+/[A-Za-z0-9._-]+', args.repo)
if args.launcher_hotfix:
    # Launcher-only update: same game fields, new launcher fields, new signature.
    lv = launcher_version.read()
    base = ROOT/'dist'/f'update-{args.version}.txt'
    assert base.exists(), f'{base} missing: a launcher hotfix rewrites the feed of the current release'
    lines = base.read_text(encoding='utf-8').splitlines()
    kept = [l for l in lines if l and not l.startswith(('launcher', 'signature='))]
    old = next((l.split('=', 1)[1] for l in lines if l.startswith('launcher_version=')), '0.0.0')
    as_tuple = lambda v: tuple(int(x) for x in v.split('.'))
    assert as_tuple(lv) > as_tuple(old), f'launcher {lv} must be newer than the {old} this release already offers (bump platinum_launcher_version.h)'
    out = ROOT/'dist'/f'update-{args.version}-launcher-{lv}.txt'
    out.write_text('\n'.join(kept) + '\n' + launcher_fields(args.launcher_hotfix, lv, 'v' + args.version), encoding='utf-8', newline='\n')
    sign(out); print(f'upload {out.name} as "update.txt" and {LAUNCHER_ASSET}, both with --clobber, to release v{args.version}')
    print(f'then: python analysis_scripts/x64/release_canary.py --version {args.version} --repo {args.repo} --launcher "{args.launcher_hotfix}" '
          '(the publish is done only when the canary passes)'); sys.exit(0)
name = f'TrueCombat-Platinum-{args.version}-Windows-x64.zip'
package = ROOT/'dist'/name
data_hash = hashlib.sha256()
with open(package, 'rb') as f:
    for chunk in iter(lambda: f.read(1 << 20), b''): data_hash.update(chunk)
tag = 'v' + args.version
notes = args.notes.replace('\n', ' ').strip() or f'TrueCombat: Platinum {args.version}'
text = (f'version={args.version}\n'
        f'package=https://github.com/{args.repo}/releases/download/{tag}/{name}\n'
        f'sha256={data_hash.hexdigest()}\n'
        f'bytes={package.stat().st_size}\n'
        f'notes={notes}\n'
        f'page=https://github.com/{args.repo}/releases/tag/{tag}\n'
        + (f'master={args.master}\n' if args.master else '')
        + (f'discord={args.discord}\n' if args.discord.isdigit() else ''))
if args.delta:
    import json, os
    game = ROOT/'releases'/args.version/'TrueCombat Platinum'
    manifest = json.loads((game/'manifest.json').read_text(encoding='utf-8'))
    assets = ROOT/'dist'/f'assets-{args.version}'
    assets.mkdir(exist_ok=True)
    lines = []
    entries = dict(manifest['files'])
    mdata = (game/'manifest.json').read_bytes()
    entries['manifest.json'] = {'bytes': len(mdata), 'sha256': hashlib.sha256(mdata).hexdigest()}
    for rel, e in sorted(entries.items()):
        asset = 'f__' + re.sub(r'[^A-Za-z0-9._-]', '_', rel.replace('/', '__'))
        target = assets/asset
        if target.exists(): target.unlink()
        os.link(game/rel, target)
        lines.append(f"{e['sha256']} {e['bytes']} {asset} {rel}")
    files_text = ('\n'.join(lines) + '\n').encode()
    (assets/'files.txt').write_bytes(files_text)
    text += (f'files=https://github.com/{args.repo}/releases/download/{tag}/files.txt\n'
             f'files_sha256={hashlib.sha256(files_text).hexdigest()}\n')
    # HD textures (0.37.1): the zip leaves these files out; files.txt still lists them, so launchers before 2.5.0
    # (which ignore optional=) keep installing them per file, and 2.5.0+ fetch them only with HD textures on.
    prefixes = [x.strip() for x in args.optional.split(',') if x.strip()]
    for x in prefixes: assert re.fullmatch(r'[A-Za-z0-9_.-]{4,}', x) and '..' not in x, f'bad --optional prefix {x!r}'
    optional = [rel for rel in entries if rel.lower().endswith('.pk3') and any(rel.rsplit('/', 1)[-1].lower().startswith(x.lower()) for x in prefixes)]
    if optional:
        text += f"optional={','.join(prefixes)}\n"
        print('optional (HD textures):', len(optional), 'files,', sum(entries[r]['bytes'] for r in optional), 'bytes')
    elif prefixes:
        print('WARNING: --optional', args.optional, 'matches no .pk3 file in this release; no optional= line written')
    print('delta assets:', len(lines) + 1, 'in', assets)
# The installer the website links to (releases/latest/download/TrueCombat-Platinum-Setup.exe).
setup = ROOT/'releases'/args.version/'TrueCombat-Platinum-Setup.exe'
if setup.exists():
    setup_assets = ROOT/'dist'/f'assets-{args.version}'; setup_assets.mkdir(exist_ok=True)
    shutil.copy2(setup, setup_assets/setup.name)
    print('installer asset:', setup_assets/setup.name, '- upload it to the release under this exact name')
else:
    print('WARNING: no installer at', setup, '- the website download button needs TrueCombat-Platinum-Setup.exe on every release')
text += launcher_fields(ROOT/'releases'/args.version/'TrueCombat Platinum'/'TrueCombatPlatinum.exe', launcher_version.read(), tag)
out = ROOT/'dist'/f'update-{args.version}.txt'
out.write_text(text, encoding='utf-8', newline='\n')
sign(out)
