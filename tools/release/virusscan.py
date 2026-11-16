#!/usr/bin/env python3
"""Virus scans every release with VirusTotal and records the SHA-256 of each download.

Runs on GitHub Actions (.github/workflows/virus-scan.yml) when a release is published,
when fast_publish.py asks for a draft to be checked, and once a day. For each release it
looks at the installer (TrueCombat-Platinum-Setup.exe) and every program file the
launcher installs (.exe and .dll assets):

  * the SHA-256 comes from GitHub's own asset digest (no download needed);
  * VirusTotal is asked about that hash first. Files it already knows cost one lookup;
  * unknown files are downloaded from the release and uploaded to VirusTotal
    (files over 32 MB go through VirusTotal's large-file upload URL), then polled
    until all engines have reported.

Results go to tools/website/scans.json, which build.py turns into the scan badge next
to the download buttons, the checksum panel on the download page and the check on each
release page. Without a VT_API_KEY the checksums are still recorded and shown.

The free VirusTotal API allows 4 requests a minute and 500 a day; this script waits
16 s between requests and stops at --budget requests, leaving the rest for the next run.

    VT_API_KEY=... GITHUB_TOKEN=... python tools/release/virusscan.py            # published releases
    VT_API_KEY=... GITHUB_TOKEN=... python tools/release/virusscan.py --tag v0.38.0-sandbox34   # also a draft
    VT_API_KEY=... python tools/release/virusscan.py --file TrueCombat-Platinum-Setup.exe       # one local file
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = ROOT / "tools" / "website" / "scans.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Annoximeme/TrueCombat-Platinum")
VT = "https://www.virustotal.com/api/v3"
SETUP = "TrueCombat-Platinum-Setup.exe"
PROGRAM = re.compile(r"\.(exe|dll)$", re.I)
GAP = 16.0                    # seconds between VirusTotal requests (free tier: 4 a minute)
DIRECT_MAX = 32 * 1024 * 1024  # bigger uploads need /files/upload_url
VT_MAX = 650 * 1024 * 1024     # VirusTotal does not take bigger files
REFRESH = datetime.timedelta(hours=72)  # re-read the newest release's results this often
SETTLE = datetime.timedelta(hours=6)    # a fresh analysis is re-read once after this, as late engines report


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def load():
    if STORE.exists():
        data = json.loads(STORE.read_text(encoding="utf-8"))
    else:
        data = {}
    data.setdefault("format", "tcp-scans/1")
    data.setdefault("files", {})
    data.setdefault("releases", {})
    return data


def save(data):
    data["releases"] = dict(sorted(data["releases"].items(), key=lambda kv: kv[1].get("published") or "9", reverse=True))
    data["files"] = dict(sorted(data["files"].items()))
    STORE.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- GitHub
def github(path):
    req = urllib.request.Request("https://api.github.com/" + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "truecombat-release-tools"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def releases(tags):
    """Published releases, plus the drafts named in tags (drafts need a token that can see them)."""
    out = []
    for page in range(1, 6):
        batch = github("repos/%s/releases?per_page=100&page=%d" % (REPO, page))
        out += batch
        if len(batch) < 100:
            break
    return [r for r in out if (not r.get("draft") and not r.get("prerelease")) or r.get("tag_name") in tags]


def download_asset(asset, folder):
    """Downloads a release asset through the API (works for drafts too)."""
    req = urllib.request.Request(asset["url"], headers={"Accept": "application/octet-stream", "User-Agent": "truecombat-release-tools"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    path = pathlib.Path(folder) / asset["name"]
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        while True:
            block = r.read(1 << 20)
            if not block:
                break
            f.write(block)
    return path


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# ---------------------------------------------------------------- VirusTotal
class Budget(Exception):
    pass


class VirusTotal:
    def __init__(self, key, budget):
        self.key, self.left, self.last = key, budget, 0.0

    def call(self, method, url, body=None, headers=None, timeout=120):
        if self.left <= 0:
            raise Budget()
        for attempt in range(4):
            wait = self.last + GAP - time.time()
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            self.left -= 1
            req = urllib.request.Request(url if url.startswith("http") else VT + url, data=body, method=method,
                                         headers={"x-apikey": self.key, "Accept": "application/json", **(headers or {})})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.load(r)
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    return None
                if error.code == 429 and attempt < 3:   # quota: back off a minute, then try again
                    print("  VirusTotal rate limit, waiting 60 s", flush=True)
                    time.sleep(60)
                    if self.left <= 0:
                        raise Budget()
                    continue
                raise RuntimeError("VirusTotal %s %s: HTTP %d %s" % (method, url[:60], error.code, error.read()[:200]))
        raise Budget()

    def report(self, sha):
        """The file's latest analysis, or None if VirusTotal has never seen it."""
        data = self.call("GET", "/files/" + sha)
        if not data:
            return None
        attrs = data["data"]["attributes"]
        stats = attrs.get("last_analysis_stats") or {}
        if not attrs.get("last_analysis_date") or not stats:
            return None
        return {"malicious": stats.get("malicious", 0), "suspicious": stats.get("suspicious", 0),
                "engines": sum(stats.get(k, 0) for k in ("malicious", "suspicious", "undetected", "harmless")),
                "analysed": iso(datetime.datetime.fromtimestamp(attrs["last_analysis_date"], datetime.timezone.utc))}

    def upload(self, path):
        size = path.stat().st_size
        if size > VT_MAX:
            raise RuntimeError("%s is too large for VirusTotal" % path.name)
        target = "/files"
        if size > DIRECT_MAX:
            target = self.call("GET", "/files/upload_url")["data"]
        boundary = uuid.uuid4().hex
        head = ('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\n'
                'Content-Type: application/octet-stream\r\n\r\n' % (boundary, path.name)).encode()
        body = head + path.read_bytes() + ("\r\n--%s--\r\n" % boundary).encode()
        data = self.call("POST", target, body, {"Content-Type": "multipart/form-data; boundary=" + boundary}, timeout=900)
        return data["data"]["id"]

    def analysis_done(self, analysis_id):
        data = self.call("GET", "/analyses/" + analysis_id)
        return bool(data) and data["data"]["attributes"].get("status") == "completed"

    def reanalyse(self, sha):
        data = self.call("POST", "/files/%s/analyse" % sha, b"")
        return data["data"]["id"] if data else None


def flagged(entry):
    return entry.get("malicious", 0) + entry.get("suspicious", 0)


# ---------------------------------------------------------------- the scan
def record_releases(data, rels):
    """Writes the asset -> SHA-256 map of every release. Needs no VirusTotal key."""
    for rel in rels:
        wanted = [a for a in rel.get("assets", []) if a.get("state", "uploaded") == "uploaded"
                  and (a["name"] == SETUP or PROGRAM.search(a["name"]))]
        if not any(a["name"] == SETUP for a in wanted):
            continue   # releases from before the installer are not shown with a scan
        files = {}
        for a in wanted:
            digest = (a.get("digest") or "")
            if digest.startswith("sha256:"):
                files[a["name"]] = digest[7:]
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    files[a["name"]] = sha256_file(download_asset(a, tmp))
            data["files"].setdefault(files[a["name"]], {"name": a["name"].replace("f__", "").split("__")[-1], "bytes": a["size"]})
        data["releases"][rel["tag_name"]] = {
            "published": rel.get("published_at") or "", "draft": bool(rel.get("draft")),
            "setup": files[SETUP], "files": dict(sorted(files.items())),
            "assets": {name: next(a for a in wanted if a["name"] == name) for name in files}}


def todo(data, order, latest):
    """Hashes in the order they should be looked at: installers first, newest release first."""
    seen, out = set(), []
    for setup_first in (True, False):
        for tag in order:
            rel = data["releases"][tag]
            for name, sha in rel["files"].items():
                if (name == SETUP) != setup_first or sha in seen:
                    continue
                seen.add(sha)
                entry = data["files"][sha]
                checked = entry.get("checked")
                if entry.get("too_large"):
                    continue
                if "engines" not in entry or entry.get("pending"):
                    out.append((tag, name, sha))
                elif tag in latest and checked:
                    age = now() - parse_iso(checked)
                    settle = entry.get("settle") and age > SETTLE
                    if age > REFRESH or settle:
                        out.append((tag, name, sha))
    return out


def scan(data, vt, order, latest):
    queue, pending = todo(data, order, latest), {}
    print("VirusTotal: %d file(s) to look at, %d requests allowed this run" % (len(queue), vt.left), flush=True)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for tag, name, sha in queue:
                entry = data["files"][sha]
                if entry.get("pending"):
                    pending[sha] = entry["pending"]
                    continue
                result = vt.report(sha)
                if result:
                    if "engines" in entry and flagged(result) != flagged(entry):
                        print("  %s: detections changed %d -> %d" % (name, flagged(entry), flagged(result)), flush=True)
                    fresh = now() - parse_iso(result["analysed"]) < SETTLE
                    entry.update(result, checked=iso(now()), settle=fresh)
                    print("  %s %s: %d/%d" % (tag, name, flagged(result), result["engines"]), flush=True)
                    continue
                asset = data["releases"][tag]["assets"][name]
                if asset["size"] > VT_MAX:
                    print("  %s: too large for VirusTotal, checksum only" % name, flush=True)
                    entry.update({"too_large": True, "checked": iso(now())})
                    continue
                print("  %s %s: new to VirusTotal, uploading %.1f MB" % (tag, name, asset["size"] / 1e6), flush=True)
                path = download_asset(asset, tmp)
                if sha256_file(path) != sha:
                    raise RuntimeError("%s: downloaded file does not match its GitHub digest" % name)
                entry["pending"] = pending[sha] = vt.upload(path)
                path.unlink()
            deadline = time.time() + 20 * 60
            while pending and time.time() < deadline:
                for sha, analysis in list(pending.items()):
                    if vt.analysis_done(analysis):
                        result = vt.report(sha)
                        if result:
                            entry = data["files"][sha]
                            entry.pop("pending", None)
                            entry.update(result, checked=iso(now()), settle=True)
                            print("  %s: %d/%d" % (entry["name"], flagged(result), result["engines"]), flush=True)
                            del pending[sha]
                if pending:
                    time.sleep(30)
    except Budget:
        print("request budget used up; the next run carries on", flush=True)
    if pending:
        print("%d analysis(es) still running; the next run reads them" % len(pending), flush=True)


def summary(data, tag):
    rel = data["releases"].get(tag)
    if not rel:
        return None
    files = [data["files"][sha] for sha in dict.fromkeys(rel["files"].values())]
    setup = data["files"][rel["setup"]]
    done = [f for f in files if "engines" in f and not f.get("pending")]
    return {"tag": tag, "setup_sha256": rel["setup"], "setup_flagged": flagged(setup) if "engines" in setup else None,
            "setup_engines": setup.get("engines"), "files": len(files), "files_scanned": len(done),
            "files_flagged": sum(1 for f in done if flagged(f)),
            "flagged": sorted("%s (%d/%d)" % (f["name"], flagged(f), f["engines"]) for f in done if flagged(f)),
            "report": "https://www.virustotal.com/gui/file/" + rel["setup"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", action="append", default=[], help="also scan this release, even as a draft")
    parser.add_argument("--file", help="scan one local file and print the result (no store update)")
    parser.add_argument("--budget", type=int, default=110, help="most VirusTotal requests this run (about 30 min)")
    parser.add_argument("--summary", help="write the --tag release's result as JSON to this file")
    args = parser.parse_args()
    key = os.environ.get("VT_API_KEY", "").strip()

    if args.file:
        if not key:
            sys.exit("set VT_API_KEY")
        vt, path = VirusTotal(key, args.budget), pathlib.Path(args.file)
        sha = sha256_file(path)
        result = vt.report(sha)
        if not result:
            analysis = vt.upload(path)
            while not vt.analysis_done(analysis):
                time.sleep(30)
            result = vt.report(sha)
        print(json.dumps({"file": path.name, "sha256": sha, **result, "flagged": flagged(result),
                          "report": "https://www.virustotal.com/gui/file/" + sha}, indent=1))
        return

    data = load()
    rels = releases(set(args.tag))
    for tag in args.tag:
        if not any(r["tag_name"] == tag for r in rels):
            sys.exit("release %s not found" % tag)
    # drafts that were deleted or published under another tag drop out of the store
    live = {r["tag_name"] for r in rels}
    for tag in [t for t, r in data["releases"].items() if r.get("draft") and t not in live]:
        del data["releases"][tag]
    record_releases(data, rels)
    order = [r["tag_name"] for r in sorted(rels, key=lambda r: (not r.get("draft"), r.get("published_at") or ""), reverse=True)
             if r["tag_name"] in data["releases"]]
    order = [t for t in order if t in args.tag] + [t for t in order if t not in args.tag]
    latest = set(args.tag) | {next((t for t in order if not data["releases"][t]["draft"]), None)}
    if key:
        scan(data, VirusTotal(key, args.budget), order, latest)
    else:
        print("no VT_API_KEY: checksums recorded, virus scan skipped", flush=True)
    for rel in data["releases"].values():
        rel.pop("assets", None)
    # hashes no release uses any more are dropped
    used = {sha for rel in data["releases"].values() for sha in rel["files"].values()}
    data["files"] = {sha: f for sha, f in data["files"].items() if sha in used}
    save(data)
    for tag in args.tag:
        result = summary(data, tag)
        print("RESULT " + json.dumps(result), flush=True)
        if args.summary:
            pathlib.Path(args.summary).write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
