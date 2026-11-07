#!/usr/bin/env python3
"""Bakes the GitHub releases into the website so it is current even without JavaScript.

Run by .github/workflows/website.yml whenever a release is published, edited or
deleted (and once a day), followed by build.py for the Dutch pages. It rewrites:
  - the patch notes between <!--releases--> markers on index.html (newest 5) and news.html (all),
  - the version shown on download buttons and the roadmap ([data-version]),
  - the size, date and link of the newest installer, TrueCombat-Platinum-Setup.exe
    ([data-size], [data-date], [data-download]); releases from before the installer fall back to their zip.

The browser script (docs/js/site.js) renders the same notes the same way, so
visitors see a new release right away, before this workflow has run.

  GITHUB_TOKEN=... python tools/website/release_sync.py
"""
import html
import json
import os
import pathlib
import re
import sys
import urllib.request

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"
REPO = os.environ.get("GITHUB_REPOSITORY", "Annoximeme/TrueCombat-Platinum")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CHEV = ' <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>'

# Section headings as release notes write them (upper case) -> how the site shows them.
TITLES = {"HUD": "HUD", "UI": "UI", "DX12": "DirectX 12", "DIRECTX 12": "DirectX 12", "STATUS": "Known issues",
          "KNOWN ISSUES": "Known issues", "FIXES": "Fixes", "BUG FIXES": "Fixes"}
SKIP = {"DEVELOPMENT"}


def section_title(t):
    t = t.strip()
    if t.upper() in TITLES:
        return TITLES[t.upper()]
    return t[:1].upper() + t[1:].lower()


def clean_summary(text):
    text = re.sub(r"^New download for the native 64-bit sandbox[.,]?\s*(with\s+)?", "", text, flags=re.I)
    return text[:1].upper() + text[1:]


def fetch():
    req = urllib.request.Request("https://api.github.com/repos/%s/releases?per_page=100" % REPO,
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "truecombat-website"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return [x for x in data if not x.get("draft") and not x.get("prerelease")]


def parse(body):
    out = {"num": "", "build": "", "summary": "", "sections": []}
    sec = None
    for raw in (body or "").replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        h = re.match(r"^\*\*([^*]+)\*\*\s*(.*)$", line)
        if h and not h.group(2):
            t = h.group(1).strip()
            num = re.search(r"Patch Notes\s*#(\d+)", t, re.I)
            if num:
                out["num"] = num.group(1)
                continue
            if re.match(r"^TRUECOMBAT", t, re.I):
                continue
            sec = {"title": section_title(t), "items": []}
            if t.upper() not in SKIP:
                out["sections"].append(sec)
            continue
        if h and re.search(r"Packaged Native Sandbox", h.group(1), re.I):
            out["build"] = h.group(2).strip()
            continue
        if h:
            continue
        if re.match(r"^[-*]\s+", line):
            if sec is not None:
                sec["items"].append(re.sub(r"^[-*]\s+", "", line))
            continue
        if sec is None and not out["summary"]:
            out["summary"] = clean_summary(line)
    return out


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", t)


def version(rel):
    m = re.match(r"^v?(\d+\.\d+\.\d+)", rel.get("tag_name", ""))
    return "v" + m.group(1) if m else rel.get("tag_name", "")


def fmt_date(iso):
    y, mo, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    return "%d %s %d" % (d, MONTHS[mo - 1], y)


def release_html(rel, first, link):
    n = parse(rel.get("body"))
    if not n["sections"]:
        return ""
    ver = html.escape(version(rel))
    meta = ("#%s · " % n["num"] if n["num"] else "") + html.escape(n["build"] or rel["tag_name"]) + " · " + fmt_date(rel["published_at"])
    secs = "\n".join(
        '          <section><h3>%s</h3><ul>\n%s\n          </ul></section>' % (
            html.escape(s["title"]), "\n".join("            <li>%s</li>" % inline(i) for i in s["items"]))
        for s in n["sections"])
    gh = '\n          <p class="rel-link"><a href="%s">GitHub ↗</a></p>' % html.escape(rel["html_url"]) if link else ""
    return ('      <details class="release" id="%s" data-ver="%s"%s>\n'
            '        <summary><span class="ver">%s%s</span><span class="sum">%s</span><span class="meta">%s%s</span></summary>\n'
            '        <div class="body">\n%s%s\n        </div>\n      </details>') % (
        ver, ver, " open" if first else "", ver, '<span class="latest">Latest</span>' if first else "",
        inline(n["summary"]), meta, CHEV, secs, gh)


def put(text, rels, limit):
    blocks = [b for b in (release_html(r, i == 0, limit > 5) for i, r in enumerate(rels[:limit])) if b]
    if not blocks:
        return text
    # keep hand-written entries for versions GitHub no longer lists (older releases were removed)
    current = re.search(r"<!--releases-->(.*?)<!--/releases-->", text, re.S)
    seen = {version(r) for r in rels}
    for m in re.finditer(r'[ \t]*<details class="release"[^>]*data-ver="([^"]+)".*?</details>', current.group(1) if current else "", re.S):
        if m.group(1) not in seen and len(blocks) < limit:
            old = re.sub(r'<span class="latest">[^<]*</span>', "", m.group(0)).replace(" open>", ">")
            blocks.append(old)
            seen.add(m.group(1))
    block = "\n\n".join(blocks)
    return re.sub(r"<!--releases-->.*?<!--/releases-->", lambda m: "<!--releases-->\n" + block + "\n<!--/releases-->", text, count=1, flags=re.S)


def main():
    rels = fetch()
    if not rels:
        sys.exit("no releases returned")
    latest = version(rels[0])
    zip_rel, zip_asset = None, None
    for pattern in (r"^TrueCombat-Platinum-Setup\.exe$", r"Windows-x64\.zip$"):
        for r in rels:
            z = [a for a in r.get("assets", []) if re.search(pattern, a["name"], re.I)]
            if z:
                zip_rel, zip_asset = r, z[0]
                break
        if zip_asset:
            break
    for name, limit in (("index.html", 5), ("news.html", 999)):
        path = DOCS / name
        text = put(path.read_text(encoding="utf-8"), rels, limit)
        text = re.sub(r"(<[^>]*\bdata-version\b[^>]*>)[^<]*(</)", lambda m: m.group(1) + latest + m.group(2), text)
        if zip_asset:
            mb = "{:,} MB".format(max(1, round(zip_asset["size"] / 1048576)))
            text = re.sub(r"(<span data-size>)[^<]*(</span>)", lambda m: m.group(1) + mb + m.group(2), text)
            text = re.sub(r"(<span data-date>)[^<]*(</span>)", lambda m: m.group(1) + fmt_date(zip_rel["published_at"]) + m.group(2), text)
            text = re.sub(r'(<a [^>]*data-download[^>]*href=")[^"]*(")', lambda m: m.group(1) + zip_asset["browser_download_url"] + m.group(2), text)
        path.write_text(text, encoding="utf-8")
    print("website synced to %s (%d releases, download %s)" % (latest, len(rels), zip_asset["name"] if zip_asset else "none"))


if __name__ == "__main__":
    main()
