#!/usr/bin/env python3
"""TrueCombat: Platinum web bridge.

Browsers can't speak the UDP master/server protocol, so this small service
does it for the website and serves the result as JSON over HTTP:

  GET /servers.json                 live public servers (schema tcp-servers/1)
  GET /leaderboard.json?period=all|30d&sort=rating|xp|kills|kd|headshots|wins
                                    player rankings and ranks (tcp-leaderboard/1)
  GET /player.json?id=<player id>   one player's profile (tcp-player/1)
  GET /search.json?q=<name>         find players by name
  GET /recent.json, /ranks.json     latest matches, the rank table
  POST /api/v1/match                signed match report from a ranked server
  GET /health

Every <interval> seconds it asks the master server for the list
("getservers <protocol> empty full"), then asks each game server for its
status ("getstatus"). Player stats and ranks live in tcp_stats.py (SQLite,
--stats-db): ranked servers upload signed reports, and a server on the same
machine can also drop tcp-match/1 files into --stats-dir.

Python 3.8+ standard library only. Put it behind an HTTPS reverse proxy
(Caddy, nginx, Cloudflare Tunnel) and set TCP_API in docs/js/site.js to its
public URL.

  python tcp_bridge.py --master 127.0.0.1:27950 --listen 127.0.0.1:8090 --stats-dir ./matches
"""
import argparse
import concurrent.futures
import datetime as dt
import json
import pathlib
import re
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import tcp_stats

OOB = b"\xff\xff\xff\xff"
COLOR = re.compile(r"\^[0-9A-Za-z]")
# Labels for g_gametype numbers. Empty on purpose: a server that sets the
# serverinfo cvar tcp_mode (e.g. "Team elimination") is shown with that name,
# otherwise pass --modes "2=Elimination,3=Team elimination" once the numbers are fixed.
DEFAULT_MODES = {}


def clean(text, limit=64):
    text = COLOR.sub("", text or "")
    text = "".join(ch for ch in text if ch.isprintable())
    return text.strip()[:limit]


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_addr(text, default_port):
    host, _, port = text.rpartition(":")
    if not host:
        host, port = text, default_port
    return host, int(port)


# ------------------------------------------------------------------ UDP
def query_master(master, protocol, timeout=2.0):
    """Returns a list of (ip, port) from one or more getserversResponse packets."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(OOB + ("getservers %d empty full" % protocol).encode(), master)
        found, deadline = [], time.time() + timeout
        while time.time() < deadline:
            try:
                data, _ = sock.recvfrom(8192)
            except socket.timeout:
                break
            head = OOB + b"getserversResponse"
            if not data.startswith(head):
                continue
            body, done = data[len(head):], False
            i = 0
            while i < len(body):
                if body[i:i + 4] == b"\\EOT":
                    done = True
                    break
                if body[i:i + 1] == b"\\" and i + 7 <= len(body):
                    ip = socket.inet_ntoa(body[i + 1:i + 5])
                    port = struct.unpack(">H", body[i + 5:i + 7])[0]
                    if port and ip != "0.0.0.0":
                        found.append((ip, port))
                    i += 7
                else:
                    i += 1
            if done:
                break
        return list(dict.fromkeys(found))
    finally:
        sock.close()


def query_status(addr, timeout=1.5):
    """getstatus -> dict with cvars and players, or None when the server doesn't answer."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        t0 = time.time()
        sock.sendto(OOB + b"getstatus", addr)
        data, _ = sock.recvfrom(16384)
        ping = int((time.time() - t0) * 1000)
    except (socket.timeout, OSError):
        return None
    finally:
        sock.close()
    head = OOB + b"statusResponse"
    if not data.startswith(head):
        return None
    lines = data[len(head):].decode("latin-1").split("\n")
    lines = [l for l in lines if l != ""]
    if not lines:
        return None
    parts = lines[0].split("\\")[1:]
    cvars = {parts[i].lower(): parts[i + 1] for i in range(0, len(parts) - 1, 2)}
    players = []
    for line in lines[1:]:
        m = re.match(r'^(-?\d+)\s+(\d+)\s+"(.*)"', line)
        if m:
            players.append({"name": clean(m.group(3), 36), "score": int(m.group(1)), "ping": int(m.group(2))})
    return {"cvars": cvars, "players": players, "ping": ping}


def load_verified(path):
    """Staff-checked community servers: one "host:port [label]" per line, # comments.
    Hostnames are resolved, so a server keeps its tag when it changes IP behind the same name."""
    out = set()
    if not path:
        return out
    try:
        lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            host, port = parse_addr(line.split()[0], 27960)
            out.add("%s:%d" % (socket.gethostbyname(host), port))
        except (OSError, ValueError):
            continue
    return out


def server_entry(addr, status, modes):
    c = status["cvars"]
    # engine bots answer with ping 0; they fill the server but are not players
    humans = [p for p in status["players"] if p["ping"] > 0]
    bots = len(status["players"]) - len(humans)
    ranked = c.get("tcp_ranked", "")
    gt = c.get("g_gametype", "")
    mode = c.get("tcp_mode") or modes.get(gt, "")
    try:
        maxp = int(c.get("sv_maxclients", "0")) - int(c.get("sv_privateclients", "0") or 0)
    except ValueError:
        maxp = 0
    try:
        need = max(0, min(int(c.get("tcp_need", "0") or 0), 8))
    except ValueError:
        need = 0
    if c.get("g_needpass", "0") not in ("", "0"):
        need = 0  # never advertise a private server
    try:
        eac = max(0, min(int(c.get("sv_eac", "0") or 0), 2))  # 0 off, 1 on, 2 required to join
    except ValueError:
        eac = 0
    return {
        "address": "%s:%d" % addr,
        "name": clean(c.get("sv_hostname", "TrueCombat: Platinum server")),
        "map": clean(c.get("mapname", ""), 40),
        "mode": clean(mode, 32),
        "players": len(humans),
        "bots": bots,
        "ranked": None if ranked == "" else ranked not in ("0", "false", "no"),
        "maxPlayers": maxp,
        "password": c.get("g_needpass", "0") not in ("", "0"),
        "version": clean(c.get("tcp_version") or c.get("version", ""), 48),
        "eac": eac,  # Easy Anti-Cheat: 0 off, 1 on, 2 required
        "need": need,  # open places on the short team after someone left mid-match
        "playerList": sorted(humans, key=lambda p: -p["score"]),
    }


# ------------------------------------------------------------------ service
class Bridge:
    def __init__(self, args):
        self.args = args
        self.master = parse_addr(args.master, 27950)
        self.modes = dict(DEFAULT_MODES)
        if args.modes:
            for pair in args.modes.split(","):
                k, _, v = pair.partition("=")
                self.modes[k.strip()] = v.strip()
        self.lock = threading.Lock()
        self.servers = {"schema": "tcp-servers/1", "updated": None, "master": {"online": False}, "servers": []}
        self.stats = tcp_stats.StatsStore(args.stats_db or ":memory:", allow_cheats=args.allow_cheats,
                                          min_matches=args.min_matches)

    def refresh(self):
        try:
            addrs = query_master(self.master, self.args.protocol)
            online = True
        except OSError:
            addrs, online = [], False
        servers = []
        if addrs:
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
                for addr, st in zip(addrs, pool.map(query_status, addrs[: self.args.max_servers])):
                    if st:
                        servers.append(server_entry(addr, st, self.modes))
        verified = load_verified(getattr(self.args, "verified", ""))
        for s in servers:
            s["verified"] = s["address"] in verified
        if self.args.stats_dir:
            self.stats.import_dir(self.args.stats_dir)
        with self.lock:
            self.servers = {"schema": "tcp-servers/1", "updated": now_iso(),
                            "master": {"online": online, "listed": len(addrs)}, "servers": servers}

    def loop(self):
        while True:
            try:
                self.refresh()
            except Exception as exc:  # keep serving the last good answer
                print("refresh failed:", exc, flush=True)
            time.sleep(self.args.interval)


def make_handler(bridge):
    class Handler(BaseHTTPRequestHandler):
        server_version = "tcp-bridge/1"

        def log_message(self, fmt, *a):
            if bridge.args.verbose:
                super().log_message(fmt, *a)

        def send_json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=30" if self.command != "POST" else "no-store")
            origin = self.headers.get("Origin", "")
            allowed = [o.strip() for o in bridge.args.cors.split(",")]
            if "*" in allowed:
                self.send_header("Access-Control-Allow-Origin", "*")
            elif origin in allowed:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):
            u = urlparse(self.path)
            with bridge.lock:
                if u.path == "/servers.json":
                    return self.send_json(bridge.servers)
                if u.path == "/health":
                    return self.send_json({"ok": True, "updated": bridge.servers["updated"]})
            r = tcp_stats.handle_get(bridge.stats, u.path, parse_qs(u.query))
            if r:
                return self.send_json(r[1], r[0])
            self.send_json({"error": "not found"}, 404)

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if n > tcp_stats.MAX_BODY:
                return self.send_json({"error": "report too large"}, 413)
            r = tcp_stats.handle_post(bridge.stats, urlparse(self.path).path, self.headers, self.rfile.read(n))
            self.send_json(*((r[1], r[0]) if r else ({"error": "not found"}, 404)))

        do_HEAD = do_GET

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--master", default="127.0.0.1:27950", help="master server host:port")
    ap.add_argument("--protocol", type=int, default=84)
    ap.add_argument("--listen", default="127.0.0.1:8090", help="HTTP host:port")
    ap.add_argument("--interval", type=int, default=60, help="seconds between refreshes")
    ap.add_argument("--max-servers", type=int, default=256)
    ap.add_argument("--stats-db", default="", help="SQLite file for player stats (empty = in memory)")
    ap.add_argument("--stats-dir", default="", help="also import tcp-match/1 files from this local folder")
    ap.add_argument("--allow-cheats", action="store_true", help="accept matches played with cheats on (tests)")
    ap.add_argument("--min-matches", type=int, default=3)
    ap.add_argument("--verified", default="", help="file of staff-checked community servers (host:port per line)")
    ap.add_argument("--cors", default="https://truecombat.eu,https://www.truecombat.eu",
                    help="comma-separated allowed origins, or *")
    ap.add_argument("--modes", default="", help="override g_gametype labels, e.g. 2=Elimination,3=Team elimination")
    ap.add_argument("--once", action="store_true", help="refresh once, print servers.json and exit")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    bridge = Bridge(args)
    if args.once:
        bridge.refresh()
        print(json.dumps(bridge.servers, indent=2, ensure_ascii=False))
        return
    threading.Thread(target=bridge.loop, daemon=True).start()
    host, port = parse_addr(args.listen, 8090)
    print("tcp-bridge on http://%s:%d (master %s:%d)" % (host, port, *bridge.master), flush=True)
    ThreadingHTTPServer((host, port), make_handler(bridge)).serve_forever()


if __name__ == "__main__":
    main()
