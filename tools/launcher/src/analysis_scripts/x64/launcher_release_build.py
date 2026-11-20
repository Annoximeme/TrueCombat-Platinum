"""Build the release launcher (TrueCombatPlatinum.exe) exactly as it ships.

One function for every path that ships a launcher, so the binary the launcher repair suite tested is the
binary that ships: package_from_candidate.py (full and --launcher-only packages) and the launcher-only
hotfix (make_update_feed.py --launcher-hotfix). Icon resource, release flags, the default feed built in,
then release hygiene (pe_tidy: no debug data, valid PE checksum; the DWARF goes to <symbols>).
The build is reproducible (--no-insert-timestamp, no PDB): same source, same bytes.

  python analysis_scripts/x64/launcher_release_build.py --out <dir>\\TrueCombatPlatinum.exe --symbols <dir>
      [--update-feed https://github.com/<repo>/releases/latest/download/update.txt]
"""
from pathlib import Path
import argparse, hashlib, re, subprocess, sys
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEED = 'https://github.com/Annoximeme/TrueCombat-Platinum/releases/latest/download/update.txt'
LIBS = ('user32', 'gdi32', 'shell32', 'ws2_32', 'bcrypt', 'gdiplus', 'shlwapi', 'ole32', 'dwmapi')

def build(out, update_feed, symbols):
    sys.path.insert(0, str(ROOT/'analysis_scripts')); sys.path.insert(0, str(ROOT/'analysis_scripts/x64'))
    import launcher_icon, launcher_version, pe_tidy
    assert not update_feed or re.fullmatch(r'https://[A-Za-z0-9./_-]+', update_feed), 'feed must be a plain https URL'
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    cc = ROOT/'tools/renderer_build/llvm-mingw-20261020-ucrt-x86_64/bin/x86_64-w64-mingw32-clang.exe'
    icon = launcher_icon.build(out.parent)
    subprocess.run([str(cc), '-municode', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-Wl,--subsystem,windows',
                    '-Wl,--no-insert-timestamp', '-DPLATINUM_NATIVE=1'] + ([f'-DPLATINUM_UPDATE_FEED=L"{update_feed}"'] if update_feed else []) +
                   [str(ROOT/'release_src/platinum_launcher.c'), str(icon), '-o', str(out)] + ['-l' + n for n in LIBS], check=True)
    icon.unlink(missing_ok=True)
    assert pe_tidy.clean(pe_tidy.tidy(out, Path(symbols))), 'launcher hygiene failed'
    assert launcher_version.exe_version_ok(out), 'built launcher lacks the launcher version marker'
    return hashlib.sha256(out.read_bytes()).hexdigest()

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--symbols', type=Path, required=True)
    p.add_argument('--update-feed', default=DEFAULT_FEED)
    a = p.parse_args()
    print(a.out, build(a.out, a.update_feed, a.symbols))
