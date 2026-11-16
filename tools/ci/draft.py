#!/usr/bin/env python3
"""Hidden draft releases as private storage for cloud builds.

Draft releases are only visible to people with write access, so unreleased
source, SDK headers and candidate binaries can live there while the repository
itself stays public. Workflow artifacts and logs of a public repository are
public, so nothing private goes there.

  draft.py ensure <tag> [--title T]          create the draft if it does not exist
  draft.py put <tag> <file> [--name N]       upload (replaces an asset of the same name)
  draft.py get <tag> <asset> <out>           download one asset
  draft.py has <tag> <asset>                 exit 0 if the asset exists
  draft.py list [--prefix ci-]               list drafts (tag, assets, updated)
  draft.py delete <tag>                      delete a draft (never a published release)

Token: GITHUB_TOKEN or GH_TOKEN, or `gh auth token`. Repo: GITHUB_REPOSITORY.
Python standard library only.
"""
import argparse, json, mimetypes, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

REPO = os.environ.get('GITHUB_REPOSITORY', 'Annoximeme/TrueCombat-Platinum')
API = os.environ.get('GITHUB_API_URL', 'https://api.github.com')


def token():
    t = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if not t:
        t = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
    if not t:
        sys.exit('no GitHub token (set GITHUB_TOKEN or log in with gh)')
    return t


def call(method, url, data=None, headers=None, raw=False, tries=4):
    h = {'Authorization': 'Bearer ' + token(), 'Accept': 'application/vnd.github+json',
         'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'truecombat-ci'}
    h.update(headers or {})
    body = data if isinstance(data, (bytes, type(None))) else json.dumps(data).encode()
    if body is not None and not isinstance(data, bytes):
        h.setdefault('Content-Type', 'application/json')
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, body, h, method=method), timeout=600) as r:
                out = r.read()
                return out if raw else (json.loads(out) if out else None)
        except urllib.error.HTTPError as e:
            if e.code in (500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(5 * (attempt + 1)); continue
            raise SystemExit(f'{method} {url}: HTTP {e.code} {e.read()[:300]!r}')
        except urllib.error.URLError:
            if attempt < tries - 1:
                time.sleep(5 * (attempt + 1)); continue
            raise


def releases():
    page = 1
    while True:
        batch = call('GET', f'{API}/repos/{REPO}/releases?per_page=100&page={page}')
        yield from batch
        if len(batch) < 100:
            return
        page += 1


def find(tag, draft_only=True):
    for r in releases():
        if r['tag_name'] == tag and (r['draft'] or not draft_only):
            return r
    return None


def ensure(tag, title=None):
    r = find(tag, draft_only=False)
    if r:
        if not r['draft']:
            sys.exit(f'{tag} is a published release, not a draft')
        return r
    return call('POST', f'{API}/repos/{REPO}/releases',
                {'tag_name': tag, 'name': title or tag, 'draft': True, 'prerelease': True,
                 'body': 'Private cloud build storage (draft, never published).'})


def put(tag, path, name=None):
    r = ensure(tag)
    name = name or os.path.basename(path)
    for a in r['assets']:
        if a['name'] == name:
            call('DELETE', f"{API}/repos/{REPO}/releases/assets/{a['id']}")
    url = r['upload_url'].split('{')[0] + '?' + urllib.parse.urlencode({'name': name})
    with open(path, 'rb') as fh:
        data = fh.read()
    call('POST', url, data, {'Content-Type': mimetypes.guess_type(name)[0] or 'application/octet-stream'})
    print(f'uploaded {name} ({len(data)} bytes) to draft {tag}')


def get(tag, name, out):
    r = find(tag, draft_only=False)
    if not r:
        sys.exit(f'no release or draft {tag}')
    for a in r['assets']:
        if a['name'] == name:
            data = call('GET', f"{API}/repos/{REPO}/releases/assets/{a['id']}",
                        headers={'Accept': 'application/octet-stream'}, raw=True)
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            with open(out, 'wb') as fh:
                fh.write(data)
            print(f'downloaded {name} ({len(data)} bytes)')
            return
    sys.exit(f'{tag} has no asset {name}')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    a = s.add_parser('ensure'); a.add_argument('tag'); a.add_argument('--title')
    a = s.add_parser('put'); a.add_argument('tag'); a.add_argument('file'); a.add_argument('--name')
    a = s.add_parser('get'); a.add_argument('tag'); a.add_argument('asset'); a.add_argument('out')
    a = s.add_parser('has'); a.add_argument('tag'); a.add_argument('asset')
    a = s.add_parser('list'); a.add_argument('--prefix', default='ci-')
    a = s.add_parser('delete'); a.add_argument('tag')
    x = p.parse_args()
    if x.cmd == 'ensure':
        print(ensure(x.tag, x.title)['html_url'])
    elif x.cmd == 'put':
        put(x.tag, x.file, x.name)
    elif x.cmd == 'get':
        get(x.tag, x.asset, x.out)
    elif x.cmd == 'has':
        r = find(x.tag, draft_only=False)
        sys.exit(0 if r and any(a['name'] == x.asset for a in r['assets']) else 1)
    elif x.cmd == 'list':
        for r in releases():
            if r['draft'] and r['tag_name'].startswith(x.prefix):
                print(r['tag_name'], r.get('updated_at') or r['created_at'], ', '.join(a['name'] for a in r['assets']))
    elif x.cmd == 'delete':
        r = find(x.tag)
        if not r:
            sys.exit(f'no draft {x.tag}')
        call('DELETE', f"{API}/repos/{REPO}/releases/{r['id']}")
        print('deleted draft', x.tag)


if __name__ == '__main__':
    main()
