#!/usr/bin/env python3
"""Uploads a release to its GitHub draft, sending only what changed.

Instead of uploading every asset from the release PC (about 4.3 GB, 2.5+ hours
on a slow uplink), this compares the release with the previous one:

  * files that are byte-identical to the previous release (same name, same
    SHA-256 in its files.txt) are copied by GitHub itself;
  * the full Windows zip, the source zip and big changed .pk3/.zip files are
    sent as a small patch (zippatch.py) and rebuilt by GitHub;
  * files with the same bytes as another asset are uploaded once;
  * everything else is uploaded as before.

It writes the plan to _fill.json, uploads it with the changed files, starts the
"Release fill" workflow and waits for it. That workflow checks the plan against
update.txt and files.txt, builds the rest, re-hashes every asset on the draft
and removes the staging files. Then this script checks names and sizes once
more. It never publishes unless --publish is given (owner's go required).

    python -X utf8 tools/release/fast_publish.py --version 0.36.0-sandbox28 \
        --base-version 0.35.0-sandbox27 --root <project root> --feed <update.txt> [--dry-run] [--publish]

The draft release must already exist. --full uploads everything the old way.
"""
import argparse
import calendar
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zippatch  # noqa: E402

PATCH_MIN_BYTES = 16 << 20   # smaller files are just uploaded
PATCH_WORTH = 0.7            # use a patch only if it is under 70% of the file
GIB2 = 2147483648


def gh(*args, check=True):
    result = subprocess.run(['gh', *args], capture_output=True, text=True)
    if check and result.returncode:
        sys.exit(f'gh {" ".join(args[:3])} failed: {result.stderr.strip()[-400:]}')
    return result


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def remote_assets(repo, tag):
    out = gh('api', f'repos/{repo}/releases', '--paginate', '--jq',
             f'.[] | select(.tag_name=="{tag}") | .assets[] | select(.state=="uploaded") | [.name,.size] | @tsv').stdout
    return {line.split('\t')[0]: int(line.split('\t')[1]) for line in out.splitlines() if line.strip()}


def upload(repo, tag, path):
    for attempt in range(6):
        result = gh('release', 'upload', tag, str(path), '--repo', repo, '--clobber', check=False)
        if result.returncode == 0:
            return
        print('  retry:', result.stderr.strip()[-200:], flush=True)
        time.sleep(2 ** attempt)
    sys.exit(f'could not upload {path.name}')


def base_files(repo, base_tag, workdir):
    folder = workdir / 'base'
    folder.mkdir(exist_ok=True)
    gh('release', 'download', base_tag, '--repo', repo, '--pattern', 'files.txt', '--dir', str(folder), '--clobber')
    text = (folder / 'files.txt').read_text()
    result = {}
    for line in text.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 3:
            result[parts[2]] = (parts[0], int(parts[1]))
    return result


def plan_release(args, files, workdir):
    repo, base_tag = args.repo, f'v{args.base_version}'
    base_index = base_files(repo, base_tag, workdir)
    base_names = set(remote_assets(repo, base_tag))
    renamed = {  # this release's name -> previous release's name
        f'TrueCombat-Platinum-{args.version}-Windows-x64.zip': f'TrueCombat-Platinum-{args.base_version}-Windows-x64.zip',
        f'TrueCombat-Platinum-{args.version}-source.zip': f'TrueCombat-Platinum-{args.base_version}-source.zip',
    }
    plan, sends, seen = [], [], {}
    for path in files:
        name, size = path.name, path.stat().st_size
        digest = sha256(path)
        entry = {'name': name, 'sha256': digest, 'bytes': size}
        if digest in seen:
            entry.update({'from': 'dup', 'of': seen[digest]})
        elif name in base_index and base_index[name] == (digest, size):
            entry.update({'from': 'copy', 'base': name})
        else:
            base_name = renamed.get(name, name)
            patched = False
            if (size >= PATCH_MIN_BYTES and base_name in base_names
                    and name.lower().endswith(('.zip', '.pk3'))):
                patch = workdir / f'_patch__{name}'
                try:
                    local = Path(args.base_dir) / base_name if args.base_dir else None
                    url = str(local) if local and local.exists() else \
                        f'https://github.com/{repo}/releases/download/{base_tag}/{base_name}'
                    if zippatch.make(url, str(path), str(patch)) < size * PATCH_WORTH:
                        entry.update({'from': 'patch', 'base': base_name, 'patch': patch.name})
                        sends.append(patch)
                        patched = True
                except Exception as error:  # a bad patch only costs time: upload instead
                    print(f'  {name}: no patch ({error}), uploading in full')
            if not patched:
                entry['from'] = 'upload'
                sends.append(path)
        seen.setdefault(digest, name)
        plan.append(entry)
    return {'format': 'tcp-fill/1', 'version': args.version, 'base_tag': base_tag, 'assets': plan}, sends


def run_fill(repo, tag):
    started = time.time()
    gh('workflow', 'run', 'release-fill.yml', '--repo', repo, '--ref', 'main', '-f', f'tag={tag}')
    run_id = None
    for _ in range(30):
        time.sleep(5)
        out = gh('run', 'list', '--repo', repo, '--workflow', 'release-fill.yml', '--event', 'workflow_dispatch',
                 '--limit', '5', '--json', 'databaseId,createdAt').stdout
        for run in json.loads(out):
            created = calendar.timegm(time.strptime(run['createdAt'], '%Y-%m-%dT%H:%M:%SZ'))
            if created >= started - 60:
                run_id = run['databaseId']
                break
        if run_id:
            break
    if not run_id:
        sys.exit('the Release fill workflow did not start')
    print(f'Release fill running: https://github.com/{repo}/actions/runs/{run_id}', flush=True)
    result = subprocess.run(['gh', 'run', 'watch', str(run_id), '--repo', repo, '--exit-status', '--interval', '20'])
    if result.returncode:
        subprocess.run(['gh', 'run', 'view', str(run_id), '--repo', repo, '--log-failed'])
        sys.exit('Release fill failed; the draft is not complete (nothing was published)')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', required=True)
    parser.add_argument('--base-version', required=True, help='the previous PUBLISHED release, e.g. 0.35.0-sandbox27')
    parser.add_argument('--repo', default='Annoximeme/TrueCombat-Platinum')
    parser.add_argument('--root', default='.', help='project root (holds dist/)')
    parser.add_argument('--feed', required=True, help='the signed update.txt for this release')
    parser.add_argument('--tag', help='draft tag (default v<version>); a different tag allows a test draft')
    parser.add_argument('--base-dir', help='optional local copy of the previous release assets (saves range reads)')
    parser.add_argument('--dry-run', action='store_true', help='make the plan and patches, upload nothing')
    parser.add_argument('--full', action='store_true', help='upload every asset from this PC (old way)')
    parser.add_argument('--publish', action='store_true', help="publish after verifying (owner's go only)")
    args = parser.parse_args()
    root, tag = Path(args.root).resolve(), args.tag or f'v{args.version}'

    assets = sorted((root / f'dist/assets-{args.version}').iterdir(), key=lambda p: p.stat().st_size)
    files = assets + [root / f'dist/TrueCombat-Platinum-{args.version}-source.zip',
                      root / f'dist/TrueCombat-Platinum-{args.version}-Windows-x64.zip', Path(args.feed)]
    names = [f.name for f in files]
    assert files[-1].name == 'update.txt' and 'files.txt' in names, 'feed assets missing'
    assert 'TrueCombat-Platinum-Setup.exe' in names and 'TrueCombatPlatinum-Launcher.exe' in names, 'installer or launcher missing'
    assert len(set(names)) == len(names), 'duplicate asset names'
    assert all(f.stat().st_size < GIB2 for f in files), 'an asset is over the GitHub 2 GiB limit'

    if not args.dry_run and gh('release', 'view', tag, '--repo', args.repo, check=False).returncode:
        sys.exit(f'create the draft release {tag} first')

    if args.full:
        sends = list(files)
        plan = None
    else:
        workdir = root / f'dist/fill-{args.version}'
        workdir.mkdir(parents=True, exist_ok=True)
        plan, sends = plan_release(args, files, workdir)
        plan_path = workdir / '_fill.json'
        plan_path.write_text(json.dumps(plan, indent=1))
        sends.append(plan_path)
        counts = {}
        for e in plan['assets']:
            counts[e['from']] = counts.get(e['from'], 0) + 1
        total = sum(f.stat().st_size for f in files)
        sent = sum(p.stat().st_size for p in sends)
        print(f'plan: {counts}; upload {sent / 1e6:.1f} MB instead of {total / 1e6:.1f} MB '
              f'({plan_path})', flush=True)
    if args.dry_run:
        return

    have = remote_assets(args.repo, tag)
    complete = all(have.get(f.name) == f.stat().st_size for f in files) and set(have) == set(names)
    if complete:
        print('the draft already holds every asset, nothing to upload', flush=True)
        sends, plan = [], None
    for number, path in enumerate(sorted(sends, key=lambda p: p.stat().st_size), 1):
        name = path.name
        if have.get(name) == path.stat().st_size and name not in ('_fill.json', 'update.txt', 'files.txt'):
            print(f'[{number}/{len(sends)}] {name} already on the draft', flush=True)
            continue
        upload(args.repo, tag, path)
        print(f'[{number}/{len(sends)}] {name} upload ok', flush=True)

    if plan:
        run_fill(args.repo, tag)

    have = remote_assets(args.repo, tag)
    missing = [f.name for f in files if have.get(f.name) != f.stat().st_size]
    extra = sorted(set(have) - set(names))
    if missing or extra:
        sys.exit(f'draft incomplete, not publishing. missing/wrong: {missing} unexpected: {extra}')
    print(f'all {len(files)} assets on the draft and verified', flush=True)
    if not args.publish:
        return
    result = gh('release', 'edit', tag, '--repo', args.repo, '--draft=false', '--prerelease=false', '--latest', check=False)
    print('publish', result.returncode, result.stdout.strip(), result.stderr.strip())
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
