#!/usr/bin/env python3
"""Checks how a search engine crawler sees truecombat.eu: DNS, mail DNS (Zoho), redirects, robots.txt, the sitemap,
status codes, robots headers and meta tags, and whether each page's canonical is its own address.
Runs from GitHub Actions (workflow "Search visibility check"); prints a report and fails on errors.

  python tools/website/seo_probe.py            sample of sitemap pages
  python tools/website/seo_probe.py --all      every page in the sitemap
  python tools/website/seo_probe.py --mail     only the mail DNS records (MX, SPF, DKIM, DMARC, CAA)
"""
import http.client
import re
import socket
import ssl
import subprocess
import sys
import urllib.parse

HOST = "truecombat.eu"
UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
ERR, WARN = [], []


def fetch(url, method="GET", ua=UA):
    u = urllib.parse.urlsplit(url)
    cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
    kw = {"context": ssl.create_default_context()} if u.scheme == "https" else {}
    c = cls(u.hostname, u.port, timeout=20, **kw)
    c.request(method, (u.path or "/") + ("?" + u.query if u.query else ""), headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    r = c.getresponse()
    body = r.read(600000) if method == "GET" else b""
    h = {k.lower(): v for k, v in r.getheaders()}
    c.close()
    return r.status, h, body.decode("utf-8", "replace")


def chain(url, ua=UA):
    hops = []
    for _ in range(8):
        s, h, b = fetch(url, ua=ua)
        hops.append((s, url))
        if s in (301, 302, 303, 307, 308) and "location" in h:
            url = urllib.parse.urljoin(url, h["location"])
            continue
        return hops, s, h, b
    return hops, s, h, b


def dig(name, rtype):
    try:
        out = subprocess.run(["dig", "+short", rtype, name, "@1.1.1.1"], capture_output=True, text=True, timeout=15).stdout.split()
    except Exception as e:
        out = ["(dig failed: %s)" % e]
    return out


ZOHO_MX = {"mx.zoho.eu.", "mx2.zoho.eu.", "mx3.zoho.eu."}
DKIM_SELECTORS = ("zmail", "zoho")


def check_mail():
    """Mail DNS for Zoho Mail (EU). Missing records are warnings, so the weekly search check stays green."""
    print("== Mail DNS")
    mx = dig(HOST, "MX")
    print("  %-28s MX    %s" % (HOST, " ".join(mx) or "-"))
    hosts = {h.lower() for h in mx[1::2]}
    if not ZOHO_MX <= hosts:
        say("WARN", "MX should be mx.zoho.eu (10), mx2.zoho.eu (20), mx3.zoho.eu (50); found %s" % (" ".join(mx) or "none"))
    txt = " ".join(dig(HOST, "TXT"))
    spf = re.findall(r'"(v=spf1[^"]*)"', txt)
    print("  %-28s SPF   %s" % (HOST, " | ".join(spf) or "-"))
    if len(spf) != 1 or "include:zohomail.eu" not in spf[0]:
        say("WARN", "need exactly one SPF record containing include:zohomail.eu; found %d" % len(spf))
    found = False
    for sel in DKIM_SELECTORS:
        name = "%s._domainkey.%s" % (sel, HOST)
        d = " ".join(dig(name, "TXT"))
        print("  %-28s DKIM  %s" % (name, (d[:70] + "...") if len(d) > 70 else d or "-"))
        found = found or "p=" in d
    if not found:
        say("WARN", "no DKIM key at %s._domainkey" % "/".join(DKIM_SELECTORS))
    dm = " ".join(dig("_dmarc." + HOST, "TXT"))
    print("  %-28s DMARC %s" % ("_dmarc." + HOST, dm or "-"))
    if "v=DMARC1" not in dm:
        say("WARN", "no DMARC record at _dmarc.%s" % HOST)
    caa = " ".join(dig(HOST, "CAA"))
    print("  %-28s CAA   %s" % (HOST, caa or "-"))
    if "letsencrypt.org" not in caa:
        say("WARN", "CAA should allow letsencrypt.org (the VPS certificate issuer)")


def say(tag, msg):
    print("%-5s %s" % (tag, msg))
    (ERR if tag == "ERROR" else WARN if tag == "WARN" else []).append(msg)


def check_page(url, s, h, b):
    if s != 200:
        say("ERROR", "%s -> HTTP %d" % (url, s))
        return
    xr = h.get("x-robots-tag", "")
    if "noindex" in xr.lower() or "none" in xr.lower():
        say("ERROR", "%s X-Robots-Tag: %s" % (url, xr))
    meta = re.findall(r'<meta[^>]+name="(?:robots|googlebot)"[^>]*content="([^"]*)"', b, re.I)
    if any("noindex" in m.lower() for m in meta):
        say("ERROR", "%s meta robots %s" % (url, meta))
    can = re.findall(r'<link rel="canonical" href="([^"]+)"', b)
    if len(can) != 1:
        say("ERROR", "%s has %d canonical tags" % (url, len(can)))
    elif can[0] != url:
        say("ERROR", "%s canonical points elsewhere: %s" % (url, can[0]))
    if not re.search(r"<title>[^<]{10,}</title>", b):
        say("WARN", "%s title missing or short" % url)
    if not re.search(r'<meta name="description" content="[^"]{50,}"', b):
        say("WARN", "%s description missing or short" % url)
    if "text/html" not in h.get("content-type", ""):
        say("WARN", "%s content-type %s" % (url, h.get("content-type")))


def main():
    if "--mail" in sys.argv:
        check_mail()
        print("\n%d warnings" % len(WARN))
        for w in WARN:
            print("  WARN  " + w)
        sys.exit(0)
    print("== DNS")
    for name in (HOST, "www." + HOST):
        for t in ("A", "AAAA", "CNAME"):
            print("  %-16s %-5s %s" % (name, t, " ".join(dig(name, t)) or "-"))
    print("  %-16s %-5s %s" % (HOST, "CAA", " | ".join(" ".join(dig(HOST, "CAA")).split("0 issue")) or "-"))
    print("  %-16s %-5s %s" % (HOST, "TXT", " ".join(dig(HOST, "TXT")) or "-"))
    aaaa = dig(HOST, "AAAA")
    if aaaa:
        say("WARN", "AAAA record %s exists: Googlebot may crawl over IPv6, make sure it reaches the same server" % aaaa)
        try:
            s = socket.create_connection((aaaa[0], 443), timeout=10)
            s.close()
            print("  IPv6 443 reachable")
        except Exception as e:
            say("ERROR", "AAAA %s not reachable on 443 (%s)" % (aaaa[0], e))

    check_mail()

    print("== Redirects")
    for start, want in (("http://truecombat.eu/", "https://truecombat.eu/"), ("http://www.truecombat.eu/", "https://truecombat.eu/"),
                        ("https://www.truecombat.eu/", "https://truecombat.eu/"), ("https://truecombat.eu/maps.html", "https://truecombat.eu/maps"),
                        ("https://truecombat.eu/index.html", "https://truecombat.eu/")):
        try:
            hops, s, h, b = chain(start)
            print("  %s" % " -> ".join("%s [%d]" % (u, c) for c, u in hops))
            if hops[-1][1] != want or s != 200:
                say("ERROR", "%s ends at %s (%d), expected %s" % (start, hops[-1][1], s, want))
            elif len(hops) > 3:
                say("WARN", "%s takes %d hops" % (start, len(hops) - 1))
        except Exception as e:
            say("ERROR", "%s failed: %s" % (start, e))
    s, h, b = fetch("https://truecombat.eu/this-page-does-not-exist-%d" % 7)
    print("  missing page -> HTTP %d" % s)
    if s != 404:
        say("ERROR", "a missing page answers %d, not 404 (soft 404)" % s)

    print("== GitHub Pages copy")
    for u in ("https://annoximeme.github.io/TrueCombat-Platinum/", "https://annoximeme.github.io/TrueCombat-Platinum/maps.html"):
        try:
            hops, s, h, b = chain(u)
            print("  %s" % " -> ".join("%s [%d]" % (x, c) for c, x in hops))
            if s == 200 and urllib.parse.urlsplit(hops[-1][1]).hostname != HOST:
                say("WARN", "duplicate copy served at %s (canonical tags point to truecombat.eu, so it should be folded in)" % hops[-1][1])
        except Exception as e:
            print("  %s: %s" % (u, e))

    print("== robots.txt")
    s, h, robots = fetch("https://truecombat.eu/robots.txt")
    print("  HTTP %d %s" % (s, h.get("content-type")))
    print("  " + robots.strip().replace("\n", "\n  "))
    if s != 200:
        say("ERROR", "robots.txt answers %d" % s)
    if re.search(r"(?im)^disallow:\s*/\s*$", robots):
        say("ERROR", "robots.txt disallows the whole site")

    print("== Home page as Googlebot and as a browser")
    for ua in (UA, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"):
        s, h, b = fetch("https://truecombat.eu/", ua=ua)
        print("  %s... HTTP %d, %d bytes, x-robots-tag=%s, cache-control=%s" % (ua[:24], s, len(b), h.get("x-robots-tag", "-"), h.get("cache-control", "-")))
    check_page("https://truecombat.eu/", s, h, b)
    print("  headers: " + ", ".join("%s=%s" % (k, v[:60]) for k, v in sorted(h.items()) if k not in ("content-security-policy",)))

    print("== Sitemap")
    s, h, sm = fetch("https://truecombat.eu/sitemap.xml")
    locs = re.findall(r"<url><loc>([^<]+)</loc>", sm)
    dates = sorted(set(re.findall(r"<lastmod>([^<]+)</lastmod>", sm)))
    print("  HTTP %d %s, %d pages, %d distinct lastmod dates (%s .. %s)" % (s, h.get("content-type"), len(locs), len(dates), dates[0] if dates else "-", dates[-1] if dates else "-"))
    if s != 200 or not locs:
        say("ERROR", "sitemap unusable")
    if len(locs) > 20 and len(dates) == 1:
        say("WARN", "every sitemap page carries the same lastmod, so search engines learn to ignore it")
    sample = locs if "--all" in sys.argv else locs[::max(1, len(locs) // 40)]
    print("  checking %d pages" % len(sample))
    for u in sample:
        try:
            s, h, b = fetch(u)
            check_page(u, s, h, b)
        except Exception as e:
            say("ERROR", "%s failed: %s" % (u, e))

    print("== IndexNow key")
    s, h, b = fetch("https://truecombat.eu/f94af4e097b50679640bb180cd207447.txt")
    print("  HTTP %d %r" % (s, b.strip()[:40]))

    print("\n%d errors, %d warnings" % (len(ERR), len(WARN)))
    for e in ERR:
        print("  ERROR " + e)
    for w in WARN:
        print("  WARN  " + w)
    sys.exit(1 if ERR else 0)


if __name__ == "__main__":
    main()
