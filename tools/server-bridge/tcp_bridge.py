#!/usr/bin/env python3
"""TrueCombat: Platinum web bridge.

Browsers can't speak the UDP master/server protocol, so this small service
does it for the website and serves the result as JSON over HTTP:

  GET /servers.json                 live public servers (schema tcp-servers/1)
  GET /leaderboard.json?period=all  player rankings from match reports (tcp-leaderboard/1)
  GET /leaderboard.json?period=30d
  GET /health

Every <interval> seconds it asks the master server for the list
("getservers <protocol> empty full"), then asks each game server for its
status ("getstatus"). Match reports (schema tcp-match/1, see README.md) are
JSON files that game servers drop into --stats-dir.

Python 3.8+ standard library only. Put it behind an HTTPS reverse proxy
(Caddy, nginx, Cloudflare Tunnel) and set TCP_API in docs/js/site.js to its
public URL.

  python tcp_bridge.py --master 127.0.0.1:27950 --listen 127.0.0.1:8090 --stats-dir ./matches
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import pathlib
import re
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

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


def server_entry(addr, status, modes):
    c = status["cvars"]
    humans = status["players"]
    gt = c.get("g_gametype", "")
    mode = c.get("tcp_mode") or modes.get(gt, "")
    try:
        maxp = int(c.get("sv_maxclients", "0")) - int(c.get("sv_privateclients", "0") or 0)
    except ValueError:
        maxp = 0
    return {
        "address": "%s:%d" % addr,
        "name": clean(c.get("sv_hostname", "TrueCombat: Platinum server")),
        "map": clean(c.get("mapname", ""), 40),
        "mode": clean(mode, 32),
        "players": len(humans),
        "maxPlayers": maxp,
        "password": c.get("g_needpass", "0") not in ("", "0"),
        "version": clean(c.get("tcp_version") or c.get("version", ""), 48),
        "playerList": sorted(humans, key=lambda p: -p["score"]),
    }


# ------------------------------------------------------------------ stats
def player_id(raw):
    """Never publish GUIDs or IPs: a short one-way hash is enough to tell players apart."""
    return hashlib.sha256(("tcp-lb:" + str(raw)).encode()).hexdigest()[:16]


def load_matches(stats_dir):
    out = []
    if not stats_dir:
        return out
    for path in sorted(pathlib.Path(stats_dir).glob("*.json")):
        try:
            m = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if m.get("schema") != "tcp-match/1" or m.get("practice"):
            continue
        try:
            m["_ended"] = dt.datetime.fromisoformat(m["ended"].replace("Z", "+00:00"))
        except (KeyError, ValueError, AttributeError):
            continue
        out.append(m)
    return out


def leaderboard(matches, period, min_matches=3):
    since = None
    if period == "30d":
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
    agg, count = {}, 0
    for m in matches:
        if since and m["_ended"] < since:
            continue
        count += 1
        for p in m.get("players", []):
            pid = player_id(p.get("guid") or p.get("id") or p.get("name"))
            a = agg.setdefault(pid, {"id": pid, "name": "", "matches": 0, "kills": 0, "deaths": 0,
                                     "headshots": 0, "wins": 0, "timePlayed": 0, "_w": {}, "_last": None})
            if a["_last"] is None or m["_ended"] >= a["_last"]:
                a["name"], a["_last"] = clean(p.get("name", ""), 36), m["_ended"]
            a["matches"] += 1
            for k, src in (("kills", "kills"), ("deaths", "deaths"), ("headshots", "headshots"),
                           ("wins", "roundsWon"), ("timePlayed", "timePlayed")):
                try:
                    a[k] += max(0, int(p.get(src, 0)))
                except (TypeError, ValueError):
                    pass
            for w, ws in (p.get("weapons") or {}).items():
                try:
                    a["_w"][w] = a["_w"].get(w, 0) + int(ws.get("kills", 0))
                except (TypeError, ValueError, AttributeError):
                    pass
    players = []
    for a in agg.values():
        if a["matches"] < min_matches:
            continue
        top = max(a["_w"].items(), key=lambda kv: kv[1])[0] if a["_w"] else ""
        a = {k: v for k, v in a.items() if not k.startswith("_")}
        a["topWeapon"] = clean(top, 24)
        players.append(a)
    players.sort(key=lambda a: -a["kills"])
    return {"schema": "tcp-leaderboard/1", "updated": now_iso(), "period": period,
            "minMatches": min_matches, "matches": count, "players": players[:500]}


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
        self.boards = {}

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
        matches = load_matches(self.args.stats_dir)
        boards = {p: leaderboard(matches, p, self.args.min_matches) for p in ("all", "30d")}
        with self.lock:
            self.servers = {"schema": "tcp-servers/1", "updated": now_iso(),
                            "master": {"online": online, "listed": len(addrs)}, "servers": servers}
            self.boards = boards

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
            self.send_header("Cache-Control", "public, max-age=30")
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
                if u.path == "/leaderboard.json":
                    period = parse_qs(u.query).get("period", ["all"])[0]
                    return self.send_json(bridge.boards.get(period) or bridge.boards.get("all") or leaderboard([], "all"))
                if u.path == "/health":
                    return self.send_json({"ok": True, "updated": bridge.servers["updated"]})
            self.send_json({"error": "not found"}, 404)

        do_HEAD = do_GET

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--master", default="127.0.0.1:27950", help="master server host:port")
    ap.add_argument("--protocol", type=int, default=84)
    ap.add_argument("--listen", default="127.0.0.1:8090", help="HTTP host:port")
    ap.add_argument("--interval", type=int, default=60, help="seconds between refreshes")
    ap.add_argument("--max-servers", type=int, default=256)
    ap.add_argument("--stats-dir", default="", help="folder with tcp-match/1 JSON reports")
    ap.add_argument("--min-matches", type=int, default=3)
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
