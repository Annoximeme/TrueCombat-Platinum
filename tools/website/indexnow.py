#!/usr/bin/env python3
"""Tells Bing, Yandex, Seznam and the other IndexNow search engines which pages changed today,
so they re-crawl them within minutes instead of days. Google does not use IndexNow; it reads
the sitemap.

The key is public by design: search engines fetch https://truecombat.eu/<key>.txt to check
that the request really comes from this site.

  python tools/website/indexnow.py                 pages whose sitemap date is today
  python tools/website/indexnow.py --since REF     pages that are new or re-dated since commit REF
  python tools/website/indexnow.py --all           every page in the sitemap
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"
HOST = "truecombat.eu"
KEY = "f94af4e097b50679640bb180cd207447"


def main():
    if not (DOCS / (KEY + ".txt")).exists():
        sys.exit("docs/%s.txt is missing" % KEY)
    pattern = r"<url><loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>"
    rows = re.findall(pattern, (DOCS / "sitemap.xml").read_text(encoding="utf-8"))
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    before = None
    if "--since" in sys.argv:
        ref = sys.argv[sys.argv.index("--since") + 1]
        old = subprocess.run(["git", "show", ref + ":docs/sitemap.xml"], cwd=DOCS.parent, capture_output=True, text=True)
        if old.returncode == 0:
            before = dict(re.findall(pattern, old.stdout))
        else:
            print("IndexNow: %s not available, falling back to today's pages" % ref)
    if "--all" in sys.argv:
        urls = [u for u, d in rows]
    elif before is not None:
        urls = [u for u, d in rows if before.get(u) != d]
    else:
        urls = [u for u, d in rows if d == today]
    if not urls:
        print("IndexNow: nothing changed today")
        return
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": "https://%s/%s.txt" % (HOST, KEY), "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "truecombat-website"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("IndexNow: sent %d pages (HTTP %d)" % (len(urls), r.status))
    except Exception as e:  # never fail the site build over a ping
        print("IndexNow: not delivered (%s)" % e)


if __name__ == "__main__":
    main()
