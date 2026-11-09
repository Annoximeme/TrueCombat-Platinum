#!/usr/bin/env python3
"""TrueCombat: Platinum devlog reads and ratings, without visitor tracking.

Every devlog post page tells this service once that someone actually read it
(the page waits until the post has been open for about ten seconds), and
readers can give a post one to five stars.

  POST /devlog/read      {"slug": "..."}                 count a read
  POST /devlog/rate      {"slug": "...", "stars": 1..5}  rate a post
  GET  /devlog/public.json   public figures (schema tcp-devlog/1): rating
                         averages once a post has --min-ratings ratings, and
                         read counts only when --public-reads is on
  GET  /devlog/stats.json    full figures for the studio (Authorization:
                         Bearer <key from --key-file>)
  GET  /devlog/health

Privacy: nothing that identifies a reader is ever stored. No cookies, no IP
addresses, no user agents. To count a reader once per day, the service keeps
a keyed hash of (IP address, post) made with a random secret that only lives
for the current UTC day. At midnight the secret and every hash are deleted,
so yesterday's readers cannot be linked to today's, or to anything else.
What stays is per-post, per-day totals and per-post star counts.

Abuse protection: one rating per reader per post per day (a second vote that
day replaces the first), a per-IP rate limit kept only in memory, a body size
cap, slug validation against the posts actually on the site (--site-root),
and obvious crawlers are ignored.

Python 3.8+ standard library only. Run it behind the same HTTPS proxy as the
stats bridge, for example with Caddy on api.truecombat.eu:

  handle /devlog/* { reverse_proxy 127.0.0.1:8092 }

  python tcp_devlog.py --db /var/lib/tcp-devlog/devlog.db --key-file /etc/tcp-devlog/key \\
      --site-root /var/www/truecombat
"""
import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

SCHEMA = "tcp-devlog/1"
MAX_BODY = 512
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
BOTS = re.compile(r"bot|crawl|spider|slurp|preview|fetch|headless|lighthouse|python|curl|wget", re.I)
RATE_WINDOW = 60      # seconds
RATE_MAX = 20         # requests per IP per window
MAX_POSTS = 500       # hard cap on distinct slugs when --site-root is not given


def today():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


class Store:
    def __init__(self, path):
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path or ":memory:", check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS daily (day TEXT NOT NULL, slug TEXT NOT NULL, reads INTEGER NOT NULL DEFAULT 0,
                readers INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, slug));
            CREATE TABLE IF NOT EXISTS stars (slug TEXT NOT NULL, stars INTEGER NOT NULL, n INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (slug, stars));
            -- today only: the day secret and the keyed hashes made with it, wiped at midnight UTC
            CREATE TABLE IF NOT EXISTS secret (day TEXT PRIMARY KEY, value BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS seen (h TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS voted (h TEXT PRIMARY KEY, stars INTEGER NOT NULL);
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
            self.db.execute("DELETE FROM seen")
            self.db.execute("DELETE FROM voted")
            row = (secrets.token_bytes(32),)
            self.db.execute("INSERT INTO secret VALUES (?,?)", (d, row[0]))
            self.db.commit()
        self.day, self.key = d, row[0]

    def tag(self, ip, slug, kind):
        return hmac.new(self.key, ("%s|%s|%s" % (kind, ip, slug)).encode(), hashlib.sha256).hexdigest()

    def known(self, slug):
        return self.db.execute("SELECT 1 FROM daily WHERE slug=? LIMIT 1", (slug,)).fetchone() is not None

    def slugs(self):
        return self.db.execute("SELECT COUNT(DISTINCT slug) FROM daily").fetchone()[0]

    def read(self, ip, slug):
        with self.lock:
            self.roll()
            new = self.db.execute("INSERT OR IGNORE INTO seen VALUES (?)", (self.tag(ip, slug, "r"),)).rowcount == 1
            self.db.execute("INSERT OR IGNORE INTO daily (day, slug) VALUES (?,?)", (self.day, slug))
            self.db.execute("UPDATE daily SET reads=reads+1, readers=readers+? WHERE day=? AND slug=?", (int(new), self.day, slug))
            self.db.commit()
            return new

    def rate(self, ip, slug, stars):
        with self.lock:
            self.roll()
            h = self.tag(ip, slug, "v")
            old = self.db.execute("SELECT stars FROM voted WHERE h=?", (h,)).fetchone()
            if old:
                if old[0] == stars:
                    return False
                self.db.execute("UPDATE stars SET n=n-1 WHERE slug=? AND stars=? AND n>0", (slug, old[0]))
            self.db.execute("INSERT OR REPLACE INTO voted VALUES (?,?)", (h, stars))
            self.db.execute("INSERT OR IGNORE INTO stars VALUES (?,?,0)", (slug, stars))
            self.db.execute("UPDATE stars SET n=n+1 WHERE slug=? AND stars=?", (slug, stars))
            self.db.execute("INSERT OR IGNORE INTO daily (day, slug) VALUES (?,?)", (self.day, slug))
            self.db.commit()
            return True

    def _ratings(self):
        out = {}
        for slug, s, n in self.db.execute("SELECT slug, stars, n FROM stars WHERE n>0"):
            r = out.setdefault(slug, {"n": 0, "sum": 0, "split": [0, 0, 0, 0, 0]})
            r["n"] += n
            r["sum"] += s * n
            r["split"][s - 1] = n
        for r in out.values():
            r["avg"] = round(r.pop("sum") / r["n"], 2)
        return out

    def public(self, min_ratings, show_reads):
        with self.lock:
            ratings = self._ratings()
            reads = dict(self.db.execute("SELECT slug, SUM(readers) FROM daily GROUP BY slug").fetchall())
        posts = {}
        for slug in set(ratings) | set(reads):
            p = {}
            r = ratings.get(slug)
            if r and r["n"] >= min_ratings:
                p["rating"] = r["avg"]
                p["ratings"] = r["n"]
            if show_reads and reads.get(slug):
                p["reads"] = reads[slug]
            if p:
                posts[slug] = p
        return {"schema": SCHEMA, "posts": posts}

    def stats(self, days=30):
        start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days - 1)).strftime("%Y-%m-%d")
        with self.lock:
            ratings = self._ratings()
            totals = self.db.execute("SELECT slug, SUM(reads), SUM(readers) FROM daily GROUP BY slug").fetchall()
            recent = self.db.execute("SELECT day, slug, readers FROM daily WHERE day>=? ORDER BY day", (start,)).fetchall()
        dates = [(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days - 1 - i)).strftime("%Y-%m-%d") for i in range(days)]
        idx = {d: i for i, d in enumerate(dates)}
        posts = {}
        for slug, reads, readers in totals:
            posts[slug] = {"reads": reads or 0, "readers": readers or 0, "last30": [0] * days, "rating": None}
        for day, slug, readers in recent:
            if slug in posts and day in idx:
                posts[slug]["last30"][idx[day]] = readers
        for slug, r in ratings.items():
            posts.setdefault(slug, {"reads": 0, "readers": 0, "last30": [0] * days})["rating"] = r
        return {"schema": SCHEMA, "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "days": dates, "posts": posts}


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


def post_exists(site_root, slug):
    if slug == "stats":  # devlog-stats.html is the studio stats page, not a post
        return False
    if not site_root:
        return True
    return (pathlib.Path(site_root) / ("devlog-%s.html" % slug)).is_file()


def make_handler(store, key, cors, site_root, min_ratings, show_reads, limiter):
    class Handler(BaseHTTPRequestHandler):
        server_version = "tcp-devlog"

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
            p = urlparse(self.path).path
            if p == "/devlog/public.json":
                return self.send_json(store.public(min_ratings, show_reads), cache="public, max-age=60")
            if p == "/devlog/stats.json":
                auth = self.headers.get("Authorization", "")
                given = auth[7:].strip() if auth.startswith("Bearer ") else ""
                if not key or not given or not hmac.compare_digest(given, key):
                    return self.send_json({"error": "unauthorized"}, 401)
                return self.send_json(store.stats())
            if p == "/devlog/health":
                return self.send_json({"ok": True})
            self.send_json({"error": "not found"}, 404)

        do_HEAD = do_GET

        def do_POST(self):
            p = urlparse(self.path).path
            if p not in ("/devlog/read", "/devlog/rate"):
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
            slug = str(data.get("slug", ""))
            if not SLUG.match(slug) or not post_exists(site_root, slug):
                return self.send_json({"error": "unknown post"}, 404)
            if not site_root and not store.known(slug) and store.slugs() >= MAX_POSTS:
                return self.send_json({"error": "unknown post"}, 404)
            if BOTS.search(self.headers.get("User-Agent", "") or "bot"):
                return self.send_json({"ok": True, "counted": False})
            if p == "/devlog/read":
                return self.send_json({"ok": True, "counted": store.read(ip, slug)})
            stars = data.get("stars")
            if not isinstance(stars, int) or isinstance(stars, bool) or not 1 <= stars <= 5:
                return self.send_json({"error": "stars must be 1 to 5"}, 400)
            store.rate(ip, slug, stars)
            self.send_json({"ok": True})

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="", help="SQLite file (empty = in memory)")
    ap.add_argument("--listen", default="127.0.0.1:8092")
    ap.add_argument("--key-file", default="", help="file holding the studio key for /devlog/stats.json")
    ap.add_argument("--site-root", default="", help="folder with devlog-<slug>.html; only those posts are accepted")
    ap.add_argument("--min-ratings", type=int, default=5, help="ratings needed before a post's average is public")
    ap.add_argument("--public-reads", action="store_true", help="also publish read counts in public.json")
    ap.add_argument("--cors", default="https://truecombat.eu,https://www.truecombat.eu")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("stats", help="print the full stats")
    sub.add_parser("new-key", help="print a fresh random studio key")
    args = ap.parse_args(argv)

    if args.cmd == "new-key":
        print(secrets.token_urlsafe(24))
        return
    store = Store(args.db)
    if args.cmd == "stats":
        print(json.dumps(store.stats(), indent=2))
        return

    key = pathlib.Path(args.key_file).read_text(encoding="utf-8").strip() if args.key_file else os.environ.get("TCP_DEVLOG_KEY", "")
    if not key:
        sys.exit("no --key-file given (make one with: tcp_devlog.py new-key)")
    host, _, port = args.listen.rpartition(":")
    cors = [c.strip() for c in args.cors.split(",") if c.strip()]
    print("tcp-devlog on http://%s:%s (public reads %s)" % (host, port, "on" if args.public_reads else "off"), flush=True)
    handler = make_handler(store, key, cors, args.site_root, args.min_ratings, args.public_reads, Limiter())
    ThreadingHTTPServer((host, int(port)), handler).serve_forever()


if __name__ == "__main__":
    main()
