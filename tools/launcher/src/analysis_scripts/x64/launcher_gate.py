"""Release gate: no launcher ships without a passing launcher repair suite for its exact bytes.

tests/launcher_repair/run_suite.py records every complete run in experiments/launcher-gate/<sha256>.json.
require(exe) refuses (SystemExit) unless that record exists, covers every case of the current suite version
and passed. Called by package_from_candidate.py (full and --launcher-only packages), make_update_feed.py (every
feed that names a launcher, the launcher-only hotfix included) and preflight_release.py (0.39.0 and later).

  python analysis_scripts/x64/launcher_gate.py <TrueCombatPlatinum.exe>     (exit 0: may ship)
"""
from pathlib import Path
import hashlib, json, sys
ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT/'experiments'/'launcher-gate'
SUITE_VERSION = 1
CASES = {'friend', 'engine_missing', 'corrupt_pak', 'av_write_denied', 'av_deleted', 'blocked_host', 'offline',
         'bad_signature', 'update_failed', 'self_update', 'self_current'}

def status(exe):
    digest = hashlib.sha256(Path(exe).read_bytes()).hexdigest()
    record = GATE/f'{digest}.json'
    if not record.exists(): return digest, False, f'no launcher repair suite run for this launcher ({digest[:12]})'
    r = json.loads(record.read_text(encoding='utf-8'))
    if r.get('launcher_sha256') != digest: return digest, False, 'gate record is for another launcher'
    if r.get('suite_version', 0) < SUITE_VERSION: return digest, False, f'suite version {r.get("suite_version")} is older than {SUITE_VERSION}'
    missing = CASES - set(r.get('cases', {}))
    if missing: return digest, False, f'cases not run: {sorted(missing)}'
    failed = [k for k, v in r['cases'].items() if not v.get('pass')]
    if failed or not r.get('passed'): return digest, False, f'failed cases: {failed}'
    return digest, True, f'passed {r.get("when")} ({len(r["cases"])} cases, release {r.get("release")})'

def require(exe, what='ship'):
    digest, ok, detail = status(exe)
    if not ok:
        sys.exit(f'refusing to {what} {exe}: {detail}.\nRun the gate on exactly this file first:\n'
                 f'  python tests/launcher_repair/run_suite.py --launcher "{exe}" --previous-launcher <released launcher> '
                 f'--dist <dist> --current <release> --old <previous release> --old-engine <older engine> --work G:\\TrueCombatWork\\lrs')
    print(f'launcher gate: {Path(exe).name} {digest[:12]} {detail}')
    return digest

if __name__ == '__main__':
    digest, ok, detail = status(sys.argv[1])
    print(('PASS ' if ok else 'BLOCK ') + digest + ' ' + detail); sys.exit(0 if ok else 1)
