#!/usr/bin/env python3
"""TrueCombat: Platinum website insights, without cookies and without tracking anyone.

Answers three questions for the studio: which pages people read, which channels
(Reddit, ModDB, itch.io, YouTube, Discord, ...) bring visitors, and which of those
visitors go on to download the game.

  POST /insights/hit    {"p": "/maps", "r": "<referring site>", "s": "<utm_source>", "m": "<utm_medium>",
                         "c": "<utm_campaign>", "t": "<utm_content>", "l": "en", "d": "phone|tablet|desktop"}
                        (older pages send "w": screen width instead of "d"; "r" may be a full URL, only the host is kept)
                        one page view
  POST /insights/event  {"e": "download", "k": "installer", "p": "/download"}
                        a click on a download button
  POST /insights/launcher  anonymous crash and hardware report from the game launcher, only when the
                        player chose to share it (see LAUNCHER REPORTS below)
  GET  /insights/stats.json?days=30   figures for the studio (Authorization: Bearer <key>)
  GET  /insights/health

Privacy: no cookies, nothing stored in the visitor's browser, no IP addresses, no
user agents, no full referrer URLs. To count a visitor once per day, and to credit
a download to the channel that brought that visitor in the same day, the service
keeps a keyed hash of (IP address, user agent) made with a random secret that only
lives for the current UTC day. At midnight the secret, every hash and the channel
noted next to it are deleted, so nobody can link one day to the next. What stays is
daily totals per page, channel, campaign, referring site, country, screen class and
language. Browsers that send Global Privacy Control or Do Not Track are not counted.

LAUNCHER REPORTS (launcher 2.6.0+, only after the player picked "Share" in the launcher):
the launcher sends at most one report a day, made of
  "hw"      (at most once a calendar month) Windows version, processor model and thread count,
            memory and video memory in whole GB, graphics card model, DirectX 12 yes/no,
            desktop resolution, refresh rate and launcher language;
  "use"     how many times the game was started since the last report, and how many of those
            were Safe starts (OpenGL);
  "crashes" up to five crash signatures: which program crashed, the Windows exception code and
            the code location as module+offset (plus up to five stack frames the same way) and
            the minutes it had been running.
There is no install ID, player ID, name, GUID, key, file path or IP address in it, and nothing
links one report to another. Hardware is kept as monthly counts per value, starts and crashes
as daily counts per game version, crash signatures for 90 days after they were last seen and
hardware months for 13 months. The sender's address is only used, as a keyed hash made with
the day secret, to cap how many reports one address can send per day.

Country (optional): with --geoip pointing at the free DB-IP "IP to Country Lite"
CSV (https://db-ip.com, CC BY 4.0), the service looks up the country code in
memory and keeps only that code. No outside lookups are made.

GitHub downloads (optional): with --github-repo, the service reads the public
download counts of the release assets every six hours.

Python 3.8+ standard library only. Run it behind the same HTTPS proxy as the
stats bridge, for example with Caddy on api.truecombat.eu:

  handle /insights/* { reverse_proxy 127.0.0.1:8094 }
"""
import argparse
import array
import bisect
import csv
import datetime as dt
import gzip
import hashlib
import hmac
import ipaddress
import io
import json
import os
import pathlib
import re
import secrets
import sqlite3
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SCHEMA = "tcp-insights/1"
MAX_BODY = 1024
MAX_LAUNCHER_BODY = 6144
LAUNCHER_PER_IP = 8     # launcher reports per address per day (one per PC per day; a LAN cafe gets a few)
CRASH_DAYS = 90         # crash signatures and daily start/crash counts are kept this long
HW_MONTHS = 13          # monthly hardware counts are kept this long
HW_DIMS = ("os", "cpu", "threads", "ram", "gpu", "gpuvendor", "vram", "dx12", "display", "refresh", "lang", "country",
           "launcher", "game")
VERSION = re.compile(r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?:-[a-z0-9]{1,16})?$")
MODULE_AT = re.compile(r"^([A-Za-z0-9_.+-]{1,64})\+0x([0-9a-fA-F]{1,12})$")
RATE_WINDOW = 60
RATE_MAX = 60           # requests per IP per minute; a person browsing never gets near it
IP_VISITORS = 30       # new visitors per IP address per day (a household, office or campus behind one address)
MAX_VALUES = 400        # distinct values per dimension per day; the rest are folded into "(other)"
OTHER = "(other)"
BOTS = re.compile(r"bot|crawl|spider|slurp|preview|fetch|headless|lighthouse|python|curl|wget|monitor|scan", re.I)
TOKEN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")
PAGE = re.compile(r"^/(?:[a-z]{2}/)?[a-z0-9-]{0,64}(?:\.html)?$")
HOST = re.compile(r"^[a-z0-9.-]{1,80}$")
OWN_HOSTS = ("truecombat.eu", "annoximeme.github.io", "localhost", "127.0.0.1")
DIMS = ("page", "source", "campaign", "referrer", "country", "device", "lang")
DOWNLOAD_KINDS = ("installer", "zip", "launcher", "other")
LANGS = ("en", "nl", "de", "fr", "pl")

# referring sites grouped into the channel names used in the campaign links (truecombat.eu/go/<channel>)
CHANNELS = (
    (re.compile(r"(^|\.)(reddit\.com|redd\.it)$"), "reddit"),
    (re.compile(r"(^|\.)moddb\.com$"), "moddb"),
    (re.compile(r"(^|\.)indiedb\.com$"), "indiedb"),
    (re.compile(r"(^|\.)itch\.io$"), "itch"),
    (re.compile(r"(^|\.)gamejolt\.com$"), "gamejolt"),
    (re.compile(r"(^|\.)(youtube\.com|youtu\.be)$"), "youtube"),
    (re.compile(r"(^|\.)(discord\.com|discord\.gg|discordapp\.com)$"), "discord"),
    (re.compile(r"(^|\.)(twitter\.com|x\.com|t\.co)$"), "x"),
    (re.compile(r"(^|\.)(facebook\.com|fb\.com|instagram\.com)$"), "meta"),
    (re.compile(r"(^|\.)(tiktok\.com)$"), "tiktok"),
    (re.compile(r"(^|\.)(twitch\.tv)$"), "twitch"),
    (re.compile(r"(^|\.)(steamcommunity\.com|steampowered\.com)$"), "steam"),
    (re.compile(r"(^|\.)github\.com$"), "github"),
    (re.compile(r"(^|\.)google\.[a-z.]+$"), "google"),
    (re.compile(r"(^|\.)bing\.com$"), "bing"),
    (re.compile(r"(^|\.)duckduckgo\.com$"), "duckduckgo"),
    (re.compile(r"(^|\.)(ecosia\.org|qwant\.com|startpage\.com|search\.brave\.com|yandex\.[a-z]+)$"), "search-other"),
)


def today():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def token(v):
    """A campaign tag as typed in a link, cleaned up, or '' when it does not look like one."""
    v = str(v or "").strip().lower().replace(" ", "-")[:40]
    return v if TOKEN.match(v) else ""


def ref_host(ref):
    ref = str(ref or "")[:512]
    if ref and "//" not in ref:
        ref = "//" + ref  # the site sends just the host name; older pages sent the full address
    try:
        h = (urlparse(ref).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    if h.startswith("www."):
        h = h[4:]
    if not h or not HOST.match(h) or any(h == o or h.endswith("." + o) for o in OWN_HOSTS):
        return ""
    return h


def channel_of(host):
    for rx, name in CHANNELS:
        if rx.search(host):
            return name
    return host


def page_of(p):
    p = str(p or "").split("?")[0].split("#")[0].lower()
    if p.endswith("/index.html"):
        p = p[:-10]
    if p.endswith(".html"):
        p = p[:-5]
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p if PAGE.match(p) else ""


def device_of(w):
    try:
        w = int(w)
    except (TypeError, ValueError):
        return "unknown"
    if w <= 0:
        return "unknown"
    return "phone" if w < 700 else "tablet" if w < 1100 else "desktop"


class GeoIP:
    """Country lookup from the DB-IP Lite CSV, kept compact in memory (about 12 MB)."""

    def __init__(self, path=None):
        self.v4s, self.v4e, self.v4c = array.array("Q"), array.array("Q"), bytearray()
        self.v6s, self.v6e, self.v6c = array.array("Q"), array.array("Q"), bytearray()
        if path:
            self.load(path)

    def load(self, path):
        """Streams the CSV straight into compact arrays (the DB-IP file is sorted by address)."""
        opener = gzip.open if str(path).endswith(".gz") else open
        s4, e4, c4 = array.array("Q"), array.array("Q"), bytearray()
        s6, e6, c6 = array.array("Q"), array.array("Q"), bytearray()
        with opener(path, "rt", encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if len(row) < 3 or len(row[2].strip()) != 2:
                    continue
                try:
                    a, b = ipaddress.ip_address(row[0].strip()), ipaddress.ip_address(row[1].strip())
                except ValueError:
                    continue
                cc = row[2].strip().upper().encode("ascii", "replace")[:2]
                if a.version == 4:
                    s4.append(int(a)); e4.append(int(b)); c4.extend(cc)
                else:  # a /64 is plenty of precision for a country
                    s6.append(int(a) >> 64); e6.append(int(b) >> 64); c6.extend(cc)
        for s, e, c in ((s4, e4, c4), (s6, e6, c6)):
            if any(s[i] > s[i + 1] for i in range(len(s) - 1)):
                order = sorted(range(len(s)), key=s.__getitem__)
                s[:] = array.array("Q", (s[i] for i in order))
                e[:] = array.array("Q", (e[i] for i in order))
                c[:] = b"".join(bytes(c[2 * i:2 * i + 2]) for i in order)
        self.v4s, self.v4e, self.v4c, self.v6s, self.v6e, self.v6c = s4, e4, c4, s6, e6, c6

    def country(self, ip):
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            return "??"
        if a.version == 6 and a.ipv4_mapped:
            a = a.ipv4_mapped
        if a.version == 4:
            s, e, c, n = self.v4s, self.v4e, self.v4c, int(a)
        else:
            s, e, c, n = self.v6s, self.v6e, self.v6c, int(a) >> 64
        i = bisect.bisect_right(s, n) - 1
        if i < 0 or n > e[i]:
            return "??"
        cc = c[2 * i:2 * i + 2].decode("ascii", "replace")
        return cc if cc.isalpha() else "??"


class Store:
    def __init__(self, path):
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path or ":memory:", check_same_thread=False)
        # deleted rows (yesterday's secret and hashes) are overwritten with zeros, not left in free pages
        self.db.execute("PRAGMA secure_delete=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS daily (day TEXT NOT NULL, dim TEXT NOT NULL, val TEXT NOT NULL,
                views INTEGER NOT NULL DEFAULT 0, visitors INTEGER NOT NULL DEFAULT 0,
                downloads INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, dim, val));
            CREATE TABLE IF NOT EXISTS gh (day TEXT NOT NULL, tag TEXT NOT NULL, asset TEXT NOT NULL,
                count INTEGER NOT NULL, PRIMARY KEY (day, tag, asset));
            -- today only: the day secret, the keyed visitor hashes and the channel noted with each; wiped at midnight UTC
            CREATE TABLE IF NOT EXISTS secret (day TEXT PRIMARY KEY, value BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS visitor (h TEXT PRIMARY KEY, source TEXT NOT NULL, campaign TEXT NOT NULL,
                downloaded INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS seen (h TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS perip (h TEXT PRIMARY KEY, n INTEGER NOT NULL);
            -- launcher reports (anonymous; see LAUNCHER REPORTS above)
            CREATE TABLE IF NOT EXISTS lhw (month TEXT NOT NULL, dim TEXT NOT NULL, val TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (month, dim, val));
            CREATE TABLE IF NOT EXISTS luse (day TEXT NOT NULL, game TEXT NOT NULL, reports INTEGER NOT NULL DEFAULT 0,
                launches INTEGER NOT NULL DEFAULT 0, safe INTEGER NOT NULL DEFAULT 0, crashes INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (day, game));
            CREATE TABLE IF NOT EXISTS lcrash (sig TEXT PRIMARY KEY, program TEXT NOT NULL, code TEXT NOT NULL, kind TEXT NOT NULL,
                at TEXT NOT NULL, frames TEXT NOT NULL, first_day TEXT NOT NULL, last_day TEXT NOT NULL, first_game TEXT NOT NULL,
                last_game TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS lcrashday (day TEXT NOT NULL, sig TEXT NOT NULL, game TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0,
                up INTEGER NOT NULL DEFAULT 0, gpuvendor TEXT NOT NULL DEFAULT '', PRIMARY KEY (day, sig, game, gpuvendor));
        """)
        self.db.commit()
        self.day, self.key = None, None
        self.roll()

    def roll(self):
        """Start a new day: forget the old secret and every hash made with it."""
        d = today()
        if d == self.day:
            return
        row = self.db.execute("SELECT value FROM secret WHERE day=?", (d,)).fetchone()
        if not row:
            self.db.execute("DELETE FROM secret")
            self.db.execute("DELETE FROM visitor")
            self.db.execute("DELETE FROM seen")
            self.db.execute("DELETE FROM perip")
            row = (secrets.token_bytes(32),)
            self.db.execute("INSERT INTO secret VALUES (?,?)", (d, row[0]))
            self.prune_launcher(d)
            self.db.commit()
        self.day, self.key = d, row[0]

    def tag(self, *parts):
        return hmac.new(self.key, "|".join(parts).encode("utf-8", "replace"), hashlib.sha256).hexdigest()

    def _bump(self, dim, val, views=0, visitors=0, downloads=0):
        val = val[:80] or "(none)"
        have = self.db.execute("SELECT 1 FROM daily WHERE day=? AND dim=? AND val=?", (self.day, dim, val)).fetchone()
        if not have:
            n = self.db.execute("SELECT COUNT(*) FROM daily WHERE day=? AND dim=?", (self.day, dim)).fetchone()[0]
            if n >= MAX_VALUES:
                val = OTHER
            self.db.execute("INSERT OR IGNORE INTO daily (day, dim, val) VALUES (?,?,?)", (self.day, dim, val))
        self.db.execute("UPDATE daily SET views=views+?, visitors=visitors+?, downloads=downloads+? WHERE day=? AND dim=? AND val=?",
                        (views, visitors, downloads, self.day, dim, val))

    def hit(self, ip, ua, page, ref, utm, lang, device, country):
        """One page view. Returns True when it was this visitor's first page today."""
        with self.lock:
            self.roll()
            vid = self.tag("v", ip, ua)
            first = self.db.execute("SELECT 1 FROM visitor WHERE h=?", (vid,)).fetchone() is None
            if first:
                # one connection that keeps changing its browser string is one machine inflating the count:
                # past IP_VISITORS new visitors a day from one address, further ones are not counted
                ih = self.tag("i", ip)
                n = (self.db.execute("SELECT n FROM perip WHERE h=?", (ih,)).fetchone() or (0,))[0]
                if n >= IP_VISITORS:
                    return None
                self.db.execute("INSERT OR REPLACE INTO perip VALUES (?,?)", (ih, n + 1))
                host = ref_host(ref)
                source = utm.get("s") or (channel_of(host) if host else "direct")
                campaign = " / ".join(x for x in (source, utm.get("m", ""), utm.get("c", ""), utm.get("t", "")) if x) if utm.get("s") else ""
                self.db.execute("INSERT INTO visitor (h, source, campaign) VALUES (?,?,?)", (vid, source, campaign))
                self._bump("total", "", visitors=1)
                self._bump("source", source, views=1, visitors=1)
                if campaign:
                    self._bump("campaign", campaign, views=1, visitors=1)
                if host:
                    self._bump("referrer", host, visitors=1)
                self._bump("country", country, visitors=1)
                self._bump("device", device, visitors=1)
                self._bump("lang", lang, visitors=1)
            else:
                source, campaign = self.db.execute("SELECT source, campaign FROM visitor WHERE h=?", (vid,)).fetchone()
                self._bump("source", source, views=1)
                if campaign:
                    self._bump("campaign", campaign, views=1)
            new_page = self.db.execute("INSERT OR IGNORE INTO seen VALUES (?)", (self.tag("p", ip, ua, page),)).rowcount == 1
            self._bump("total", "", views=1)
            self._bump("page", page, views=1, visitors=int(new_page))
            self.db.commit()
            return first

    def download(self, ip, ua, kind, page):
        """A download click, credited to the channel that brought this visitor in today."""
        with self.lock:
            self.roll()
            vid = self.tag("v", ip, ua)
            row = self.db.execute("SELECT source, campaign, downloaded FROM visitor WHERE h=?", (vid,)).fetchone()
            source, campaign, done = row if row else ("unknown", "", 0)
            if done:
                return False
            if row:
                self.db.execute("UPDATE visitor SET downloaded=1 WHERE h=?", (vid,))
            else:
                self.db.execute("INSERT INTO visitor (h, source, campaign, downloaded) VALUES (?,?,?,1)", (vid, source, campaign))
            self._bump("total", "", downloads=1)
            self._bump("source", source, downloads=1)
            if campaign:
                self._bump("campaign", campaign, downloads=1)
            self._bump("download", kind, downloads=1)
            if page:
                self._bump("page", page, downloads=1)
            self.db.commit()
            return True

    # ---- launcher reports -------------------------------------------------------------------
    def prune_launcher(self, day):
        """Retention: daily launcher counts and crash signatures for CRASH_DAYS, hardware months for HW_MONTHS."""
        d = dt.date.fromisoformat(day)
        cut = (d - dt.timedelta(days=CRASH_DAYS)).isoformat()
        self.db.execute("DELETE FROM luse WHERE day<?", (cut,))
        self.db.execute("DELETE FROM lcrashday WHERE day<?", (cut,))
        self.db.execute("DELETE FROM lcrash WHERE last_day<?", (cut,))
        y, m = d.year, d.month - HW_MONTHS
        while m <= 0:
            y, m = y - 1, m + 12
        self.db.execute("DELETE FROM lhw WHERE month<?", ("%04d-%02d" % (y, m),))

    def _hw(self, month, dim, val):
        val = val[:80] or "(none)"
        have = self.db.execute("SELECT 1 FROM lhw WHERE month=? AND dim=? AND val=?", (month, dim, val)).fetchone()
        if not have and self.db.execute("SELECT COUNT(*) FROM lhw WHERE month=? AND dim=?", (month, dim)).fetchone()[0] >= MAX_VALUES:
            val = OTHER
        self.db.execute("INSERT OR IGNORE INTO lhw (month, dim, val) VALUES (?,?,?)", (month, dim, val))
        self.db.execute("UPDATE lhw SET n=n+1 WHERE month=? AND dim=? AND val=?", (month, dim, val))

    def launcher(self, ip, report):
        """One cleaned launcher report (see clean_launcher). Returns False when this address is over its daily cap."""
        with self.lock:
            self.roll()
            ih = self.tag("l", ip)
            n = (self.db.execute("SELECT n FROM perip WHERE h=?", (ih,)).fetchone() or (0,))[0]
            if n >= LAUNCHER_PER_IP:
                return False
            self.db.execute("INSERT OR REPLACE INTO perip VALUES (?,?)", (ih, n + 1))
            game = report["game"]
            if report.get("hw"):
                month = self.day[:7]
                for dim, val in report["hw"].items():
                    self._hw(month, dim, val)
            use = report.get("use")
            crashes = report.get("crashes") or []
            if use or crashes:
                self.db.execute("INSERT OR IGNORE INTO luse (day, game) VALUES (?,?)", (self.day, game))
                self.db.execute("UPDATE luse SET reports=reports+1, launches=launches+?, safe=safe+?, crashes=crashes+? WHERE day=? AND game=?",
                                (use["launches"] if use else 0, use["safe"] if use else 0, len(crashes), self.day, game))
            vendor = (report.get("hw") or {}).get("gpuvendor") or report.get("gpuvendor", "")
            for c in crashes:
                sig = hashlib.sha256("|".join((c["program"], c["code"], c["at"], " ".join(c["frames"][:3]))).encode()).hexdigest()[:16]
                v = c.get("game") or game
                if self.db.execute("SELECT 1 FROM lcrash WHERE sig=?", (sig,)).fetchone():
                    self.db.execute("UPDATE lcrash SET last_day=?, last_game=? WHERE sig=?", (self.day, v, sig))
                else:
                    self.db.execute("INSERT INTO lcrash VALUES (?,?,?,?,?,?,?,?,?,?)",
                                    (sig, c["program"], c["code"], c["kind"], c["at"], " ".join(c["frames"]), self.day, self.day, v, v))
                self.db.execute("INSERT OR IGNORE INTO lcrashday (day, sig, game, gpuvendor) VALUES (?,?,?,?)", (self.day, sig, v, vendor))
                self.db.execute("UPDATE lcrashday SET n=n+1, up=up+? WHERE day=? AND sig=? AND game=? AND gpuvendor=?",
                                (c["up"], self.day, sig, v, vendor))
            self.db.commit()
            return True

    def launcher_stats(self, dates):
        idx = {d: i for i, d in enumerate(dates)}
        days = len(dates)
        with self.lock:
            use = self.db.execute("SELECT day, game, reports, launches, safe, crashes FROM luse WHERE day>=?", (dates[0],)).fetchall()
            cd = self.db.execute("SELECT day, sig, game, n, up, gpuvendor FROM lcrashday WHERE day>=?", (dates[0],)).fetchall()
            sigs = {r[0]: r for r in self.db.execute("SELECT sig, program, code, kind, at, frames, first_day, last_day, first_game, last_game FROM lcrash")}
            months = [r[0] for r in self.db.execute("SELECT DISTINCT month FROM lhw ORDER BY month DESC LIMIT 2")]
            hw = self.db.execute("SELECT month, dim, val, n FROM lhw WHERE month IN (%s)" % ",".join("?" * len(months)), months).fetchall() if months else []
        series = {k: [0] * days for k in ("reports", "launches", "safe", "crashes")}
        versions = {}
        for day, game, reports, launches, safe, crashes in use:
            i = idx.get(day)
            if i is None:
                continue
            for k, v in (("reports", reports), ("launches", launches), ("safe", safe), ("crashes", crashes)):
                series[k][i] += v
            g = versions.setdefault(game, {"game": game, "launches": 0, "crashes": 0, "safe": 0})
            g["launches"] += launches
            g["crashes"] += crashes
            g["safe"] += safe
        for g in versions.values():
            g["crash_rate"] = round(g["crashes"] / g["launches"], 4) if g["launches"] else None
        top = {}
        for day, sig, game, n, up, vendor in cd:
            if day not in idx or sig not in sigs:
                continue
            t = top.get(sig)
            if not t:
                _, program, code, kind, at, frames, first_day, last_day, first_game, last_game = sigs[sig]
                t = top[sig] = {"sig": sig, "program": program, "code": code, "kind": kind, "at": at, "frames": frames.split(),
                                "first_seen": first_day, "last_seen": last_day, "first_game": first_game, "last_game": last_game,
                                "count": 0, "minutes": 0, "games": {}, "gpuvendors": {}}
            t["count"] += n
            t["minutes"] += up
            t["games"][game] = t["games"].get(game, 0) + n
            if vendor:
                t["gpuvendors"][vendor] = t["gpuvendors"].get(vendor, 0) + n
        crashes = sorted(top.values(), key=lambda r: (-r["count"], r["sig"]))[:40]
        for r in crashes:
            r["avg_minutes"] = round(r.pop("minutes") / r["count"], 1) if r["count"] else 0
        hardware = {}
        for month, dim, val, n in hw:
            if month != (months[0] if months else ""):
                continue
            hardware.setdefault(dim, []).append({"name": val, "count": n})
        for dim in hardware:
            hardware[dim].sort(key=lambda r: (-r["count"], r["name"]))
            hardware[dim] = hardware[dim][:25]
        reports_month = sum(r["count"] for r in hardware.get("launcher", []))
        return {"series": series, "totals": {k: sum(v) for k, v in series.items()},
                "versions": sorted(versions.values(), key=lambda g: g["game"], reverse=True),
                "crashes": crashes, "hardware_month": months[0] if months else "", "hardware_reports": reports_month,
                "hardware": hardware}

    def github(self, counts):
        """counts: {(tag, asset): download_count} as read from the GitHub API now."""
        with self.lock:
            d = today()
            for (tag, asset), n in counts.items():
                self.db.execute("INSERT OR REPLACE INTO gh VALUES (?,?,?,?)", (d, tag[:60], asset[:120], int(n)))
            self.db.commit()

    def stats(self, days=30):
        days = max(1, min(int(days), 400))
        now = dt.datetime.now(dt.timezone.utc)
        dates = [(now - dt.timedelta(days=days - 1 - i)).strftime("%Y-%m-%d") for i in range(days)]
        idx = {d: i for i, d in enumerate(dates)}
        with self.lock:
            rows = self.db.execute("SELECT day, dim, val, views, visitors, downloads FROM daily WHERE day>=?", (dates[0],)).fetchall()
            gh = self.db.execute("SELECT day, tag, asset, count FROM gh WHERE day>=? OR day=(SELECT MAX(day) FROM gh)", (dates[0],)).fetchall()
        series = {k: [0] * days for k in ("views", "visitors", "downloads")}
        tops = {d: {} for d in DIMS + ("download",)}
        per_source = {}
        for day, dim, val, views, visitors, downloads in rows:
            i = idx.get(day)
            if i is None:
                continue
            if dim == "total":
                series["views"][i] += views
                series["visitors"][i] += visitors
                series["downloads"][i] += downloads
                continue
            if dim not in tops:
                continue
            t = tops[dim].setdefault(val, {"views": 0, "visitors": 0, "downloads": 0})
            t["views"] += views
            t["visitors"] += visitors
            t["downloads"] += downloads
            if dim == "source":
                s = per_source.setdefault(val, {"visitors": [0] * days, "downloads": [0] * days})
                s["visitors"][i] += visitors
                s["downloads"][i] += downloads

        def ranked(d, key="visitors", n=50):
            out = [dict(v, name=k) for k, v in d.items()]
            out.sort(key=lambda r: (-r[key], -r["views"], r["name"]))
            return out[:n]

        top_sources = [r["name"] for r in ranked(tops["source"], n=8)]
        latest, first_seen = {}, {}
        for day, tag, asset, count in gh:
            key = (tag, asset)
            if key not in latest or day >= latest[key][0]:
                latest[key] = (day, count)
            if day in idx:
                first_seen.setdefault(key, {})[day] = count
        releases = {}
        for (tag, asset), (day, count) in latest.items():
            r = releases.setdefault(tag, {"tag": tag, "downloads": 0, "assets": {}})
            r["assets"][asset] = count
            r["downloads"] += count
        gh_daily = [0] * days
        for key, by_day in first_seen.items():
            prev = None
            for d in dates:
                if d in by_day:
                    if prev is not None:
                        gh_daily[idx[d]] += max(0, by_day[d] - prev)
                    prev = by_day[d]
        return {
            "schema": SCHEMA, "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "days": dates,
            "totals": {k: sum(v) for k, v in series.items()}, "series": series,
            "pages": ranked(tops["page"], "views"), "sources": ranked(tops["source"]), "campaigns": ranked(tops["campaign"]),
            "referrers": ranked(tops["referrer"]), "countries": ranked(tops["country"]), "devices": ranked(tops["device"]),
            "langs": ranked(tops["lang"]), "download_kinds": ranked(tops["download"], "downloads"),
            "source_series": {s: per_source[s] for s in top_sources if s in per_source},
            "github": {"releases": sorted(releases.values(), key=lambda r: r["tag"], reverse=True), "daily": gh_daily},
            "launcher": self.launcher_stats(dates),
        }


def _text(v, n=64):
    """Printable text from a launcher report, single spaces, at most n characters."""
    v = "".join(ch if ch.isprintable() and ch not in "\\:<>\"'`" else " " for ch in str(v or ""))
    return " ".join(v.split())[:n]


def _int(v, low, high):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    return v if low <= v <= high else None


def windows_name(build):
    """'10.0.22631' -> 'Windows 11 (22631)'; anything else -> 'other'."""
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{3,6})$", str(build or ""))
    if not m:
        return "other"
    major, minor, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if major == 10 and minor == 0:
        return "Windows %s (%d)" % ("11" if b >= 22000 else "10", b)
    return "Windows %d.%d (%d)" % (major, minor, b)


def gpu_vendor(name):
    n = name.lower()
    for key, vendor in (("nvidia", "NVIDIA"), ("geforce", "NVIDIA"), ("radeon", "AMD"), ("amd", "AMD"), ("intel", "Intel"),
                        ("arc ", "Intel"), ("qualcomm", "Qualcomm"), ("adreno", "Qualcomm"), ("microsoft basic", "Microsoft")):
        if key in n:
            return vendor
    return "other" if n else ""


def clean_cpu(name):
    name = re.sub(r"\((?:R|TM|tm|r)\)", "", _text(name, 96))
    name = re.sub(r"\s+(?:CPU|Processor)\b", "", name)
    name = re.sub(r"\s+@\s*[\d.]+\s*GHz$", "", name)
    name = re.sub(r"\s+\d+-Core$", "", name)
    return " ".join(name.split())[:64] or "unknown"


def _at(v):
    m = MODULE_AT.match(str(v or "").strip())
    return "%s+0x%s" % (m.group(1).lower(), m.group(2).lower()) if m else ""


def clean_launcher(data, country):
    """Validates a launcher report and keeps only the documented fields. Returns None when it is unusable."""
    if not isinstance(data, dict) or data.get("v") != 1:
        return None
    game = str(data.get("game") or "")
    launcher = str(data.get("launcher") or "")
    if not VERSION.match(game):
        game = "dev"
    if not VERSION.match(launcher):
        launcher = "other"
    out = {"game": game}
    hw = data.get("hw")
    if isinstance(hw, dict):
        gpu = _text(hw.get("gpu"), 64) or "unknown"
        threads, ram, vram, hz = _int(hw.get("threads"), 1, 1024), _int(hw.get("ram"), 1, 4096), _int(hw.get("vram"), 0, 512), _int(hw.get("hz"), 20, 1000)
        res = str(hw.get("display") or "")
        res = res if re.match(r"^\d{3,5}x\d{3,5}$", res) else "unknown"
        lang = str(hw.get("lang") or "")
        out["hw"] = {
            "os": windows_name(hw.get("os")), "cpu": clean_cpu(hw.get("cpu")),
            "threads": str(threads) if threads else "unknown",
            # memory in buckets so an unusual amount cannot single anyone out
            "ram": next(("%d GB or less" % b for b in (4, 8, 12, 16, 24, 32, 48, 64, 128) if ram and ram <= b), "more than 128 GB") if ram else "unknown",
            "gpu": gpu, "gpuvendor": gpu_vendor(gpu) or "unknown",
            "vram": next(("%d GB or less" % b for b in (1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32) if vram is not None and vram <= b), "more than 32 GB") if vram is not None else "unknown",
            "dx12": "yes" if hw.get("dx12") in (1, True, "1") else "no",
            "display": res, "refresh": str(hz) + " Hz" if hz else "unknown",
            "lang": lang if lang in LANGS else "other", "country": country,
            "launcher": launcher, "game": game,
        }
    use = data.get("use")
    if isinstance(use, dict):
        launches, safe = _int(use.get("launches"), 0, 500), _int(use.get("safe"), 0, 500)
        if launches is not None:
            out["use"] = {"launches": launches, "safe": min(safe or 0, launches)}
    vendor = gpu_vendor(_text(data.get("gpu"), 64))
    if vendor:
        out["gpuvendor"] = vendor
    crashes = []
    for c in (data.get("crashes") or [])[:5] if isinstance(data.get("crashes"), list) else []:
        if not isinstance(c, dict):
            continue
        at = _at(c.get("at"))
        code = str(c.get("code") or "").lower()
        if not at or not re.match(r"^0x[0-9a-f]{8}$", code):
            continue
        program = c.get("program") if c.get("program") in ("client", "server") else "other"
        kind = re.sub(r"[^a-z ()-]", "", str(c.get("kind") or "").lower())[:40] or "unhandled exception"
        frames = [f for f in (_at(x) for x in (c.get("frames") or [])[:5] if isinstance(c.get("frames"), list)) if f]
        up = _int(c.get("up"), 0, 100000)
        cg = str(c.get("game") or "")
        crashes.append({"program": program, "code": code, "kind": kind, "at": at, "frames": frames,
                        "up": up or 0, "game": cg if VERSION.match(cg) else ""})
    out["crashes"] = crashes
    if "hw" not in out and "use" not in out and not crashes:
        return None
    return out


class Limiter:
    """Per-IP request budget, in memory only."""

    def __init__(self, window=RATE_WINDOW, limit=RATE_MAX):
        self.window, self.limit, self.hits, self.lock = window, limit, {}, threading.Lock()

    def ok(self, ip, now=None):
        now = now if now is not None else time.monotonic()
        with self.lock:
            if len(self.hits) > 50000:
                self.hits = {k: v for k, v in self.hits.items() if v[0] > now - self.window}
            start, n = self.hits.get(ip, (now, 0))
            if now - start >= self.window:
                start, n = now, 0
            self.hits[ip] = (start, n + 1)
            return n < self.limit


def page_exists(site_root, page):
    if not site_root:
        return True
    root = pathlib.Path(site_root)
    rel = page.strip("/")
    if not rel:
        return (root / "index.html").is_file()
    return (root / (rel + ".html")).is_file() or (root / rel / "index.html").is_file()


def poll_github(store, repo, every=6 * 3600, once=False):
    url = "https://api.github.com/repos/%s/releases?per_page=30" % repo
    while True:
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "tcp-insights"})
            with urllib.request.urlopen(req, timeout=30) as r:
                rels = json.loads(r.read().decode("utf-8"))
            counts = {}
            for rel in rels:
                if rel.get("draft"):
                    continue
                for a in rel.get("assets") or []:
                    name = a.get("name", "")
                    if name.lower().endswith((".exe", ".zip")):
                        counts[(rel.get("tag_name", ""), name)] = int(a.get("download_count") or 0)
            store.github(counts)
        except Exception as e:  # keep running; the next poll tries again
            print("github poll failed: %s" % e, file=sys.stderr, flush=True)
        if once:
            return
        time.sleep(every)


def make_handler(store, key, cors, site_root, limiter, geoip):
    class Handler(BaseHTTPRequestHandler):
        server_version = "tcp-insights"
        timeout = 30                       # a client that stops sending frees its thread

        def log_message(self, fmt, *a):
            pass

        def client_ip(self):
            # Caddy sets X-Forwarded-For to the real client; the last entry is the one it added.
            fwd = self.headers.get("X-Forwarded-For", "")
            return fwd.split(",")[-1].strip() if fwd else self.client_address[0]

        def send_json(self, obj, code=200, cache="no-store"):
            body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            origin = self.headers.get("Origin", "")
            if "*" in cors:
                self.send_header("Access-Control-Allow-Origin", "*")
            elif origin in cors:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            origin = self.headers.get("Origin", "")
            if origin in cors or "*" in cors:
                self.send_header("Access-Control-Allow-Origin", origin or "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                self.send_header("Access-Control-Max-Age", "86400")
                self.send_header("Vary", "Origin")
            self.end_headers()

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/insights/stats.json":
                auth = self.headers.get("Authorization", "")
                given = auth[7:].strip() if auth.startswith("Bearer ") else ""
                if not key or not given or not hmac.compare_digest(given, key):
                    return self.send_json({"error": "unauthorized"}, 401)
                try:
                    days = int((parse_qs(u.query).get("days") or ["30"])[0])
                except ValueError:
                    days = 30
                return self.send_json(store.stats(days))
            if u.path == "/insights/health":
                return self.send_json({"ok": True, "geoip": bool(len(geoip.v4s))})
            self.send_json({"error": "not found"}, 404)

        do_HEAD = do_GET

        def launcher_report(self):
            ip = self.client_ip()
            if not limiter.ok(ip):
                return self.send_json({"error": "slow down"}, 429)
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if n <= 0 or n > MAX_LAUNCHER_BODY:
                return self.send_json({"error": "bad size"}, 413)
            try:
                data = json.loads(self.rfile.read(n).decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return self.send_json({"error": "bad json"}, 400)
            country = geoip.country(ip) if len(geoip.v4s) else "??"
            report = clean_launcher(data, country)
            if report is None:
                return self.send_json({"error": "bad report"}, 400)
            self.send_json({"ok": True, "counted": store.launcher(ip, report)})

        def do_POST(self):
            p = urlparse(self.path).path
            if p == "/insights/launcher":
                return self.launcher_report()
            if p not in ("/insights/hit", "/insights/event"):
                return self.send_json({"error": "not found"}, 404)
            ip = self.client_ip()
            if not limiter.ok(ip):
                return self.send_json({"error": "slow down"}, 429)
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if n <= 0 or n > MAX_BODY:
                return self.send_json({"error": "bad size"}, 413)
            try:
                data = json.loads(self.rfile.read(n).decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return self.send_json({"error": "bad json"}, 400)
            if not isinstance(data, dict):
                return self.send_json({"error": "bad json"}, 400)
            ua = self.headers.get("User-Agent", "") or ""
            # Global Privacy Control, Do Not Track and crawlers: answer politely, count nothing
            if self.headers.get("Sec-GPC", "").strip() == "1" or self.headers.get("DNT", "").strip() == "1" or not ua or BOTS.search(ua):
                return self.send_json({"ok": True, "counted": False})
            page = page_of(data.get("p"))
            if p == "/insights/event":
                if data.get("e") != "download":
                    return self.send_json({"error": "unknown event"}, 400)
                kind = str(data.get("k", ""))
                kind = kind if kind in DOWNLOAD_KINDS else "other"
                if page and not page_exists(site_root, page):
                    page = ""
                return self.send_json({"ok": True, "counted": store.download(ip, ua, kind, page)})
            if not page or not page_exists(site_root, page):
                return self.send_json({"error": "unknown page"}, 404)
            utm = {k: token(data.get(k)) for k in ("s", "m", "c", "t")}
            lang = str(data.get("l", ""))[:2]
            lang = lang if lang in LANGS else "other"
            country = geoip.country(ip) if len(geoip.v4s) else "??"
            device = data.get("d") if data.get("d") in ("phone", "tablet", "desktop") else device_of(data.get("w"))
            first = store.hit(ip, ua, page, data.get("r", ""), utm, lang, device, country)
            if first is None:
                return self.send_json({"ok": True, "counted": False})
            self.send_json({"ok": True, "counted": True, "first": first})

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="", help="SQLite file (empty = in memory)")
    ap.add_argument("--listen", default="127.0.0.1:8094")
    ap.add_argument("--key-file", default="", help="file holding the studio key for /insights/stats.json")
    ap.add_argument("--site-root", default="", help="folder with the site's .html pages; only those pages are counted")
    ap.add_argument("--geoip", default="", help="DB-IP Lite country CSV (.csv or .csv.gz); empty = no countries")
    ap.add_argument("--github-repo", default="", help="owner/repo whose release download counts are read every 6 hours")
    ap.add_argument("--cors", default="https://truecombat.eu,https://www.truecombat.eu")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("stats", help="print the figures")
    s.add_argument("--days", type=int, default=30)
    sub.add_parser("new-key", help="print a fresh random studio key")
    args = ap.parse_args(argv)

    if args.cmd == "new-key":
        print(secrets.token_urlsafe(24))
        return
    store = Store(args.db)
    if args.cmd == "stats":
        print(json.dumps(store.stats(args.days), indent=2))
        return

    key = pathlib.Path(args.key_file).read_text(encoding="utf-8").strip() if args.key_file else os.environ.get("TCP_INSIGHTS_KEY", "")
    if not key:
        sys.exit("no --key-file given (make one with: tcp_insights.py new-key)")
    geoip = GeoIP()
    if args.geoip and pathlib.Path(args.geoip).is_file():
        geoip.load(args.geoip)
    if args.github_repo:
        threading.Thread(target=poll_github, args=(store, args.github_repo), daemon=True).start()
    host, _, port = args.listen.rpartition(":")
    cors = [c.strip() for c in args.cors.split(",") if c.strip()]
    print("tcp-insights on http://%s:%s (countries %s)" % (host, port, "on" if len(geoip.v4s) else "off"), flush=True)
    ThreadingHTTPServer.request_queue_size = 128   # the default 5 overflows under a burst behind Caddy
    httpd = ThreadingHTTPServer((host, int(port)), make_handler(store, key, cors, args.site_root, Limiter(), geoip))
    httpd.daemon_threads = True
    httpd.serve_forever()


if __name__ == "__main__":
    main()
