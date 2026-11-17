"""Assemble a sandbox release from a verified integration candidate.

Usage: python analysis_scripts/x64/package_from_candidate.py --candidate <dir> --version 0.28.0-sandbox19

Copies the candidate's game files (engine, renderers incl. optional DLSS runtime
and licenses, server, protocol6 modules, assets) into releases/<version>, then
builds the current launcher from release_src with -DPLATINUM_NATIVE=1 as the one
EXE. Refuses an unverified candidate, an existing release directory, a
protocol mismatch, or any non-AMD64 binary. finalize_sandbox.py writes notes,
source, manifest and zip afterwards.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil, struct, subprocess, zipfile
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--candidate', type=Path, required=True)
parser.add_argument('--version', required=True)
parser.add_argument('--update-feed', default='', help='default feed URL built into the launcher (https)')
parser.add_argument('--hd-packs', action='store_true', help='add the HD world and interface texture packs and the DX12 Ultra '
                    'materials pack to tcetest (HD-TEXTURES.md)')
parser.add_argument('--launcher-only', action='store_true', help='rebuild only the launcher of an existing release folder')
parser.add_argument('--owner-approved', default='', help="required: the owner's own words asking for this package (release policy)")
args = parser.parse_args()
assert re.fullmatch(r'\d+\.\d+\.\d+-sandbox\d+', args.version), 'version must look like 0.28.0-sandbox19'
# Release policy (owner, 2026-11-06): package only on the owner's explicit request, only a
# stable build that passed the full regression, and version numbers that reflect the size
# of the drop (minor bump for big collected releases, patch bump for hotfixes).
if not args.launcher_only:
    assert len(args.owner_approved.strip()) >= 3, 'refusing: packaging needs --owner-approved "<owner request>" (see release policy)'
    def _ver(v): return tuple(int(x) for x in v.split('-')[0].split('.')) + (int(v.rsplit('sandbox', 1)[1]),)
    prior = [p.name for p in (ROOT/'releases').iterdir() if re.fullmatch(r'\d+\.\d+\.\d+-sandbox\d+', p.name)]
    if prior:
        last = max(prior, key=_ver); a, b = _ver(last), _ver(args.version)
        assert b[3] == a[3] + 1, f'sandbox number must follow {last}'
        assert (b[:3] == (a[0], a[1], a[2] + 1)) or (b[:3] == (a[0], a[1] + 1, 0)) or (b[:3] == (a[0] + 1, 0, 0)), \
            f'version must be the next patch (hotfix) or next minor (big drop) after {last}'
    REQUIRED_CASES = 17
GAME = (ROOT/args.candidate).resolve() if not args.candidate.is_absolute() else args.candidate.resolve()
assert GAME.name == 'TrueCombat Platinum' and GAME.is_relative_to((ROOT/'experiments/integration').resolve()), GAME
ready_files = sorted(GAME.parent.glob('*readiness-checkpoint.json'))
assert len(ready_files) == 1, 'expected exactly one readiness checkpoint: ' + str(ready_files)
readiness = json.loads(ready_files[0].read_text(encoding='utf-8'))
assert readiness['status'].startswith('passed'), 'candidate is not verified: ' + readiness['status']
if not args.launcher_only:
    # stability gate: every regression case must have actually run and passed on this candidate
    suite = json.loads((GAME.parent/readiness.get('integration_checkpoint', 'integration-checkpoint.json')).read_text(encoding='utf-8'))
    cases = suite.get('cases', {})
    failed = [k for k, v in cases.items() if v.get('status') != 'passed' or v.get('exit') != 0]
    assert len(cases) >= REQUIRED_CASES and not failed, f'unstable build: {len(cases)} cases, failing {failed} (need all {REQUIRED_CASES} passed)'
    assert set(readiness.get('cases', [])) <= set(cases), 'readiness lists cases the suite did not run'
for name, digest in readiness['binary_sha256'].items():
    if name == 'TrueCombatPlatinum.exe':continue  # replaced by the current launcher below
    assert hashlib.sha256((GAME/name).read_bytes()).hexdigest() == digest, 'candidate drift: ' + name
OUT = ROOT/'releases'/args.version/'TrueCombat Platinum'
assert not args.update_feed or re.fullmatch(r'https://[A-Za-z0-9./_-]+', args.update_feed), 'feed must be a plain https URL'
if args.launcher_only:assert OUT.exists(), 'release folder missing'
else:assert not OUT.parent.exists(), 'release directory already exists: ' + str(OUT.parent)
skip_top = {'profile', 'profile-server', 'server-state', 'updates', 'player.ini', 'update.ini', 'README.txt',
            'PATCH-NOTES-DISCORD.txt', 'TrueCombatPlatinum.exe', 'manifest.json'}
for p in ([] if args.launcher_only else GAME.rglob('*')):
    rel = p.relative_to(GAME)
    if rel.parts[0] in skip_top or not p.is_file():continue
    target = OUT/rel; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, target)
hd_packs = {}
if args.hd_packs and not args.launcher_only:
    for folder in ('out-esrgan', 'out-esrgan-interface'):
        built = json.loads((ROOT/'experiments/hd_textures'/folder/'manifest.json').read_text(encoding='utf-8'))
        pack = ROOT/'experiments/hd_textures'/folder/built['pack']
        assert hashlib.sha256(pack.read_bytes()).hexdigest() == built['pack_sha256'], 'HD pack drift: ' + pack.name
        # Every replaced image must come from the stock file this release ships, or the pack is stale.
        stock = {}
        archives = []
        for pk3 in sorted([*(OUT/'etmain').glob('*.pk3'), *(OUT/'tcetest').glob('*.pk3')], key=lambda q: (q.parent.name != 'etmain', q.name.lower())):
            if pk3.name.lower().startswith('zzz_hd_'):continue  # compare against stock files only
            archive = zipfile.ZipFile(pk3); archives.append(archive)
            stock.update({entry: archive for entry in archive.namelist() if entry in built['entries']})
        try:
            for entry, info in built['entries'].items():
                assert entry in stock, 'HD pack entry missing from stock files: ' + entry
                assert hashlib.sha256(stock[entry].read(entry)).hexdigest() == info['source_sha256'], 'stale HD pack entry: ' + entry
        finally:
            for archive in archives: archive.close()
        shutil.copy2(pack, OUT/'tcetest'/pack.name)
        hd_packs[pack.name] = {'sha256': built['pack_sha256'], 'images': built['images']}
    # DX12 Ultra surface materials (normal/roughness maps; renderer reads zzz_hd_materials.pk3, falls back to
    # the classic surfaces without it). Built by the visuals thread; the shipped engine's anticheat release-pak
    # table (sv_anticheat.c acReleasePaks) must carry this pack's checksum or clients get flagged.
    materials = ROOT/'experiments/materials-0371' if (ROOT/'experiments/materials-0371/manifest.json').exists() else ROOT/'experiments/hd_textures/out-materials'  # 0.37.1: this tree's own pack (specular 7cd64d98), shared folder untouched
    built = json.loads((materials/'manifest.json').read_text(encoding='utf-8'))
    pack = materials/built['pack']
    assert hashlib.sha256(pack.read_bytes()).hexdigest() == built['pack_sha256'], 'materials pack drift: ' + pack.name
    def _md4(data):
        rol = lambda x, n: ((x << n) | (x >> (32 - n))) & 0xffffffff
        message = bytes(data) + b'\x80' + b'\0' * ((55 - len(data)) % 64) + struct.pack('<Q', len(data) * 8)
        state = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476]
        rounds = [(lambda x, y, z: (x & y) | (~x & z), 0, range(16), (3, 7, 11, 19)),
                  (lambda x, y, z: (x & y) | (x & z) | (y & z), 0x5a827999, [i % 4 * 4 + i // 4 for i in range(16)], (3, 5, 9, 13)),
                  (lambda x, y, z: x ^ y ^ z, 0x6ed9eba1, (0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15), (3, 9, 11, 15))]
        for offset in range(0, len(message), 64):
            words = struct.unpack('<16I', message[offset:offset + 64]); a, b, c, d = state
            for function, constant, order, shifts in rounds:
                for i, k in enumerate(order):
                    a, b, c, d = d, rol((a + function(b, c, d) + words[k] + constant) & 0xffffffff, shifts[i % 4]), b, c
            state = [(x + y) & 0xffffffff for x, y in zip(state, (a, b, c, d))]
        return state
    with zipfile.ZipFile(pack) as pak:  # files.c pack->checksum, as build_candidate.py pak_checksum()
        crcs = b''.join(struct.pack('<I', info.CRC) for info in pak.infolist() if info.file_size > 0)
    value = 0
    for word in _md4(crcs): value ^= word
    value = value - (1 << 32) if value >= 1 << 31 else value
    table = GAME.parent/'source/etlegacy/src/server/sv_anticheat.c'
    expected = re.search(r'"tcetest/' + re.escape(pack.stem) + r'",\s*"(-?\d+)"', table.read_text(encoding='utf-8'))
    assert expected and int(expected.group(1)) == value, f'{pack.name} checksum {value} is not the one in the candidate engine ({table})'
    shutil.copy2(pack, OUT/'tcetest'/pack.name)
    hd_packs[pack.name] = {'sha256': built['pack_sha256'], 'textures': built['textures'], 'checksum': value}
# 0.38.0 release hygiene: no debug data or COFF symbols, a valid PE checksum (pe_tidy.py). The launcher's DWARF
# is kept outside the release for crash analysis, never shipped. Launcher 2.6.2: one build function for every
# shipping path (launcher_release_build.py, reproducible), and the launcher repair suite must have passed for
# exactly these bytes (launcher_gate.py) before anything is packaged.
import sys; sys.path.insert(0, str(ROOT/'analysis_scripts')); sys.path.insert(0, str(ROOT/'analysis_scripts/x64'))
import launcher_release_build, launcher_gate, pe_tidy
launcher_release_build.build(OUT/'TrueCombatPlatinum.exe', args.update_feed, ROOT/'experiments'/'symbols'/args.version)
launcher_gate.require(OUT/'TrueCombatPlatinum.exe', 'package')
if not args.launcher_only:
    ours = ['engine/platinum-engine.bin', 'server/platinum-server.bin', 'engine/renderer_dx12_x64.dll', 'engine/renderer_opengl1_x64.dll',
            'tcetest/cgame_mp_x64.dll', 'tcetest/qagame_mp_x64.dll', 'tcetest/ui_mp_x64.dll']
    dirty = [n for n in ours if not pe_tidy.clean(pe_tidy.info(OUT/n))]
    assert not dirty, f'candidate binaries still carry debug data or a bad checksum (build the candidate with the 0.38.0 build_candidate.py): {dirty}'
protocol = readiness['native_protocol'].encode()
for name in ('TrueCombatPlatinum.exe', 'tcetest/qagame_mp_x64.dll', 'tcetest/cgame_mp_x64.dll'):
    data = (OUT/name).read_bytes()
    assert protocol in data or protocol.decode().encode('utf-16-le') in data, 'protocol mismatch in ' + name
components = {}
for p in OUT.rglob('*'):
    if p.suffix.lower() in ('.exe', '.bin', '.dll'):
        data = p.read_bytes()
        if data[:2] != b'MZ': continue  # EasyAntiCheat/Certificates/base.bin: the integrity catalogue, not a program
        offset = struct.unpack_from('<I', data, 60)[0]; rel = str(p.relative_to(OUT)).replace('\\', '/')
        # Easy Anti-Cheat vendor file (Epic): the EOS service setup is 32-bit; everything we build is AMD64.
        vendor = rel == 'EasyAntiCheat/EasyAntiCheat_EOS_Setup.exe'
        assert vendor or struct.unpack_from('<H', data, offset+4)[0] == 0x8664, p
        components[rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'architecture': 'x86 (Epic)' if vendor else 'AMD64'}
assert sorted(str(p.relative_to(OUT)).replace('\\', '/') for p in OUT.rglob('*.exe')) in (['TrueCombatPlatinum.exe'],
    ['EasyAntiCheat/EasyAntiCheat_EOS_Setup.exe', 'TrueCombatPlatinum.exe', 'TrueCombatPlatinum_EAC.exe'])
(OUT.parent/'platinum_launcher.res').unlink(missing_ok=True)
# The website offers only this small installer (0.38.0: nothing embedded). It downloads this release's
# launcher and Easy Anti-Cheat setup from the signed feed and verifies both (see build_setup.py), so it works
# once the release is published with update.txt, files.txt and TrueCombatPlatinum-Launcher.exe.
SETUP = OUT.parent/'TrueCombat-Platinum-Setup.exe'
subprocess.run([sys.executable, str(ROOT/'analysis_scripts/build_setup.py'), '--version', args.version, '--out', str(SETUP),
                '--keep-debug', str(ROOT/'experiments'/'symbols'/args.version)], check=True)
import launcher_version
assert launcher_version.exe_version_ok(OUT/'TrueCombatPlatinum.exe'), 'built launcher lacks the launcher version marker'
record = {'version': args.version, 'launcher_version': launcher_version.read(), 'update_feed': args.update_feed, 'candidate': str(GAME.relative_to(ROOT)), 'native_protocol': readiness['native_protocol'],
          'candidate_status': readiness['status'], 'components': components, 'hd_packs': hd_packs,
          'setup': {'file': SETUP.name, 'sha256': hashlib.sha256(SETUP.read_bytes()).hexdigest(), 'bytes': SETUP.stat().st_size}}
(OUT.parent/'package-components.json').write_text(json.dumps(record, indent=2))
print(OUT)
