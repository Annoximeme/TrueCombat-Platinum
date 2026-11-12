#!/usr/bin/env python3
"""Completes a draft release from the previous release, inside GitHub.

fast_publish.py on the release PC uploads only what changed, plus a plan
(_fill.json) saying where every other asset comes from:

  upload  the PC uploaded it
  copy    byte-identical asset of the previous release (same name)
  patch   previous release's asset `base` + the uploaded patch `patch`
          (see zippatch.py), rebuilt here
  dup     same bytes as another asset of this release (`of`)

This script (run by .github/workflows/release-fill.yml) checks the plan against
the release's own update.txt and files.txt, builds and uploads every missing
asset, downloads EVERY asset of the draft again to check its SHA-256, and only
then removes the plan and patches. It refuses to touch a published release.

    fill_release.py --repo owner/name --tag v0.36.0-sandbox28
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zippatch  # noqa: E402

PLAN = '_fill.json'
STAGING = re.compile(r'^(_fill\.json|_patch__.+)$')


def gh(*args, capture=True):
    for attempt in range(5):
        result = subprocess.run(['gh', *args], capture_output=capture, text=True)
        if result.returncode == 0:
            return result.stdout if capture else ''
        print('gh', args[0], args[1] if len(args) > 1 else '', 'failed, retrying:',
              (result.stderr or '').strip()[-300:], flush=True)
        time.sleep(2 ** attempt * 3)
    sys.exit(f'gh {" ".join(args[:3])} kept failing')


def release(repo, tag):
    out = gh('api', f'repos/{repo}/releases', '--paginate', '--jq',
             f'.[] | select(.tag_name=="{tag}") | {{draft, assets: [.assets[] | {{name, size, state}}]}}')
    found = [json.loads(line) for line in out.splitlines() if line.strip()]
    if len(found) != 1:
        sys.exit(f'expected exactly one release tagged {tag}, found {len(found)}')
    return found[0]


def download(repo, tag, name, folder):
    target = Path(folder) / name
    if target.exists():
        target.unlink()
    gh('release', 'download', tag, '--repo', repo, '--pattern', name, '--dir', str(folder))
    if not target.exists():
        sys.exit(f'{name} did not download from {tag}')
    return target


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def check_plan(plan, folder, repo, tag):
    """The plan must agree with the signed feed (update.txt) and its files.txt."""
    entries = {e['name']: e for e in plan['assets']}
    for name in ('update.txt', 'files.txt'):
        if entries.get(name, {}).get('from') != 'upload':
            sys.exit(f'{name} must be uploaded by the PC')
    feed_path = download(repo, tag, 'update.txt', folder)
    files_path = download(repo, tag, 'files.txt', folder)
    for name, path in (('update.txt', feed_path), ('files.txt', files_path)):
        if sha256(path) != entries[name]['sha256']:
            sys.exit(f'{name} on the draft does not match the plan')
    feed = dict(line.split('=', 1) for line in feed_path.read_text().splitlines() if '=' in line)
    if feed.get('files_sha256') != entries['files.txt']['sha256']:
        sys.exit('files.txt does not match files_sha256 in update.txt')
    package = feed['package'].rsplit('/', 1)[1]
    if (entries.get(package, {}).get('sha256'), entries.get(package, {}).get('bytes')) != (feed['sha256'], int(feed['bytes'])):
        sys.exit(f'{package} in the plan does not match update.txt')
    if 'launcher' in feed:
        launcher = feed['launcher'].rsplit('/', 1)[1]
        if entries.get(launcher, {}).get('sha256') != feed['launcher_sha256']:
            sys.exit(f'{launcher} in the plan does not match update.txt')
    for line in files_path.read_text().splitlines():
        parts = line.split(None, 3)
        if len(parts) < 3:
            continue
        sha, size, asset = parts[0], int(parts[1]), parts[2]
        if (entries.get(asset, {}).get('sha256'), entries.get(asset, {}).get('bytes')) != (sha, size):
            sys.exit(f'{asset} in the plan does not match files.txt')
    for entry in plan['assets']:
        if entry['from'] not in ('upload', 'copy', 'patch', 'dup'):
            sys.exit(f'unknown source for {entry["name"]}')
        if STAGING.match(entry['name']):
            sys.exit(f'{entry["name"]} is a reserved name')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    repo, tag = args.repo, args.tag

    draft = release(repo, tag)
    if not draft['draft']:
        sys.exit(f'{tag} is already published; only drafts are filled')
    work = Path(tempfile.mkdtemp(prefix='fill-'))
    plan = json.loads(download(repo, tag, PLAN, work).read_text())
    if plan.get('format') != 'tcp-fill/1':
        sys.exit('unknown plan format')
    base_tag = plan['base_tag']
    base = release(repo, base_tag)
    if base['draft']:
        sys.exit(f'base release {base_tag} is not published')
    check_plan(plan, work, repo, tag)
    entries = {e['name']: e for e in plan['assets']}
    print(f'{tag}: {len(entries)} assets, base {base_tag}', flush=True)

    present = {a['name']: a['size'] for a in draft['assets'] if a['state'] == 'uploaded'}
    for entry in plan['assets']:
        if entry['from'] == 'upload' and present.get(entry['name']) != entry['bytes']:
            sys.exit(f'{entry["name"]} should have been uploaded by the PC but is missing')

    built = {}  # sha256 -> local file, so duplicates are built once
    order = sorted(plan['assets'], key=lambda e: e['from'] == 'dup')
    for entry in order:
        name, want = entry['name'], entry['sha256']
        if present.get(name) == entry['bytes'] or entry['from'] == 'upload':
            continue
        out = work / 'out' / name
        out.parent.mkdir(parents=True, exist_ok=True)
        if want in built and built[want].exists():
            shutil.copyfile(built[want], out)
        elif entry['from'] == 'copy':
            got = download(repo, base_tag, entry.get('base', name), work / 'base')
            got.replace(out)
        elif entry['from'] == 'patch':
            base_file = download(repo, base_tag, entry['base'], work / 'base')
            patch_file = download(repo, tag, entry['patch'], work / 'patch')
            zippatch.apply(str(base_file), str(patch_file), str(out))
            base_file.unlink()
            patch_file.unlink()
        elif entry['from'] == 'dup':
            source = entries[entry['of']]
            if source['sha256'] != want:
                sys.exit(f'{name} is not the same file as {entry["of"]}')
            got = download(repo, tag, entry['of'], work / 'dup')
            got.replace(out)
        if os.path.getsize(out) != entry['bytes'] or sha256(out) != want:
            sys.exit(f'{name}: built file does not match the plan, nothing uploaded')
        gh('release', 'upload', tag, str(out), '--repo', repo, '--clobber', capture=False)
        print(f'{name}: {entry["from"]} ok ({entry["bytes"]} bytes)', flush=True)
        built[want] = out

    # Final check: every asset of the draft, downloaded again and hashed.
    draft = release(repo, tag)
    final = {a['name']: a for a in draft['assets']}
    problems = [n for n in entries if final.get(n, {}).get('state') != 'uploaded' or final[n]['size'] != entries[n]['bytes']]
    extra = [n for n in final if n not in entries and not STAGING.match(n)]
    if problems or extra:
        sys.exit(f'draft incomplete: missing/wrong {problems}, unexpected {extra}')
    check = work / 'check'
    for name, entry in sorted(entries.items()):
        got = download(repo, tag, name, check)
        if sha256(got) != entry['sha256']:
            sys.exit(f'{name} on the draft has the wrong SHA-256')
        got.unlink()
    print(f'all {len(entries)} assets verified by SHA-256', flush=True)
    for name in final:
        if STAGING.match(name):
            gh('release', 'delete-asset', tag, name, '--repo', repo, '--yes')
    print('staging files removed; the draft is complete and ready to publish', flush=True)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
