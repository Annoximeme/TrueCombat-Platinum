#!/usr/bin/env python3
"""TrueCombat: Platinum staff portal (staff.truecombat.eu).

A private web console for the people who run the official and pickup servers:
live servers and players, kick / mute / warn / team moves, bans that hold on
every server, map control, live chat with staff replies, player lookup,
player reports and bug reports, an audit log, staff roles and server health.

Standard library only (Python 3.10+). It runs on the VPS next to the game
servers, listens on 127.0.0.1 and sits behind Caddy. Game servers are driven
over rcon on 127.0.0.1; rcon passwords arrive as systemd credentials and never
reach the browser.

    python3 tcp_staff_portal.py --config /etc/tcp-staff-portal/config.json
    python3 test_staff_portal.py          # loopback tests with a fake game server

See README.md for the configuration, roles and deployment.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import ipaddress
import json
import logging
import mimetypes
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION = "1.0.0"
HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
log = logging.getLogger("tcp-staff")

# ----------------------------------------------------------------------------- roles

ROLES = ["moderator", "admin", "owner"]          # lowest to highest
RANK = {r: i + 1 for i, r in enumerate(ROLES)}

# Lowest role that may do each thing.
PERMS = {
    "view": "moderator",
    "chat.reply": "moderator",
    "player.kick": "moderator",
    "player.warn": "moderator",
    "player.mute": "moderator",
    "player.move": "moderator",
    "ban.temp": "moderator",          # up to MOD_BAN_LIMIT minutes
    "ban.perm": "admin",
    "ban.remove": "admin",
    "server.say": "moderator",
    "server.map": "admin",
    "server.restart": "admin",
    "reports": "moderator",
    "lookup": "moderator",
    "lookup.ip": "admin",
    "audit": "admin",
    "staff.manage": "admin",
    "health": "moderator",
    "health.restart": "admin",
}
MOD_BAN_LIMIT = 24 * 60


def allowed(role: str | None, perm: str) -> bool:
    return bool(role) and RANK.get(role, 0) >= RANK[PERMS[perm]]


# ----------------------------------------------------------------------------- small helpers

COLOUR = re.compile(r"\^.")
PID = re.compile(r"^[0-9a-f]{16}$")
MAP_NAME = re.compile(r"^[A-Za-z0-9_-]{1,48}$")


def now() -> int:
    return int(time.time())


def iso(t: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now() if t is None else t))


def plain(text: str) -> str:
    return COLOUR.sub("", str(text or ""))


def safe_arg(text, limit: int = 120) -> str:
    """Free text that is safe inside one rcon command: no quotes, separators, colour codes or control bytes."""
    text = plain(text)
    text = re.sub(r'[";\\\r\n\x00-\x1f\x7f]', " ", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def player_pid(guid: str) -> str:
    """Leaderboard id, the same as the game and stats service: sha256('tcp-lb:' + GUID)[:16]."""
    g = (guid or "").strip()
    if not g:
        return ""
    if len(g) == 32 and all(c in "0123456789abcdefABCDEF" for c in g):
        g = g.upper()
    return hashlib.sha256(("tcp-lb:" + g).encode()).hexdigest()[:16]


def host_of(address: str) -> str:
    a = (address or "").strip()
    if a.startswith("["):
        return a[1:a.find("]")] if "]" in a else a
    if a.count(":") == 1:
        return a.rsplit(":", 1)[0]
    return a


def duration_minutes(text) -> int:
    """'30m', '12h', '7d', '2w', '0' / 'perm' -> minutes (0 = permanent)."""
    t = str(text or "").strip().lower()
    if t in ("", "0", "perm", "permanent"):
        return 0
    m = re.fullmatch(r"(\d{1,5})\s*([mhdw]?)", t)
    if not m:
        raise ValueError("Use a length such as 30m, 12h, 7d or 2w.")
    n = int(m.group(1))
    return n * {"": 1, "m": 1, "h": 60, "d": 1440, "w": 10080}[m.group(2)]


def engine_length(minutes: int) -> str:
    if minutes <= 0:
        return ""
    for unit, size in (("w", 10080), ("d", 1440), ("h", 60)):
        if minutes % size == 0:
            return "%d%s" % (minutes // size, unit)
    return "%dm" % minutes


# ----------------------------------------------------------------------------- rcon

PREFIX = b"\xff\xff\xff\xff"


class RconError(Exception):
    pass


def read_password(server: dict) -> str:
    names = []
    cred = os.environ.get("CREDENTIALS_DIRECTORY")
    if cred and server.get("rcon_credential"):
        names.append(Path(cred) / server["rcon_credential"])
    if server.get("rcon_password_file"):
        names.append(Path(server["rcon_password_file"]))
    for p in names:
        try:
            text = p.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        m = re.search(r'rconpassword\s+"?([^"\s]+)"?', text)
        pw = m.group(1) if m else (text.splitlines()[0].strip() if text else "")
        if pw:
            return pw
    if server.get("rcon_password"):          # tests and local runs only
        return str(server["rcon_password"])
    raise RconError("no rcon password configured for %s" % server.get("key"))


def rcon(host: str, port: int, password: str, command: str, timeout: float = 1.5, settle: float = 0.2) -> str:
    """Sends one console command and returns what the server printed, colour codes removed."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    s = socket.socket(family, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)
        s.sendto(PREFIX + ("rcon %s %s" % (password, command)).encode("latin-1", "replace"), (host, int(port)))
        chunks = []
        try:
            while True:
                data, _ = s.recvfrom(65536)
                chunks.append(data)
                s.settimeout(settle)
        except socket.timeout:
            pass
    finally:
        s.close()
    if not chunks:
        raise RconError("no answer from %s:%s" % (host, port))
    out = []
    for data in chunks:
        if data.startswith(PREFIX + b"print\n"):
            out.append(data[len(PREFIX) + 6:].decode("latin-1"))
    text = "".join(out)
    low = text.lower()
    if "bad rconpassword" in low or "rcon is locked" in low or "no rconpassword set" in low:
        raise RconError("the server refused the rcon password")
    return text


STATUS_LINE = re.compile(r"^\s*(\d+)\s+(-?\d+)\s+(\d+|CNCT|ZMBI|DEMO)\s+(.*?)\s+(\d+)\s+(\S+)\s+(\d+)\s+(\d+)(?:\s+(-?\d+))?\s*$")


def parse_status(text: str) -> dict:
    out = {"map": "", "players": {}}
    for line in text.splitlines():
        if re.match(r"^map\s*:", line, re.I):
            out["map"] = line.split(":", 1)[1].strip()
            continue
        m = STATUS_LINE.match(line)
        if m:
            addr = m.group(6)
            slot = int(m.group(1))
            ping = m.group(3)
            out["players"][slot] = {
                "slot": slot, "score": int(m.group(2)),
                "ping": int(ping) if ping.isdigit() else -1,
                "state": "active" if ping.isdigit() else ping.lower(),
                "name": plain(m.group(4)).strip(), "address": addr,
                "bot": addr.lower() == "bot",
                "connected_s": int(m.group(9)) // 1000 if m.group(9) else 0,
            }
    return out


def parse_acstatus(text: str) -> dict:
    """acstatus: EAC mode in the header, then per slot the EAC state, file check and account id."""
    out = {"eac_mode": "", "players": {}}
    last = None
    for line in text.splitlines():
        m = re.search(r"EAC (required|on|off)", line)
        if line.startswith("anti-cheat") and m:
            out["eac_mode"] = m.group(1)
            continue
        m = re.match(r"^\s*(\d+) (.{16}) (.*)$", line)
        if m and not line.strip().startswith("slot"):
            slot = int(m.group(1))
            rest = m.group(3)
            if "(bot or host" in rest:
                out["players"][slot] = {"eac": "exempt"}
            else:
                state = rest[:12].strip()
                files = rest[13:37].strip()
                det = re.search(r"(\d+)\s*/\s*(\d+)\s+(\d+)\s*(.*)$", rest[37:])
                out["players"][slot] = {"eac": state, "files": files,
                                        "detections": int(det.group(3)) if det else 0,
                                        "last_detection": det.group(4).strip() if det else ""}
            last = slot
            continue
        m = re.match(r"^\s+account id (\S+)", line)
        if m and last is not None and last in out["players"]:
            out["players"][last]["puid"] = m.group(1)
    return out


def parse_info(text: str) -> dict:
    """serverinfo / dumpuser: 'key<spaces>value' lines."""
    info = {}
    for line in text.splitlines():
        m = re.match(r"^(\S+)\s+(.*?)\s*$", line)
        if m and not line.startswith(("Server info", "userinfo", "--")):
            info[m.group(1)] = m.group(2)
    return info


STAFF_PLAYER = re.compile(r"^TCP_STAFF_PLAYER (.*?) name=(.*)$")


def parse_staff_players(text: str) -> dict:
    out = {"match": {}, "players": {}}
    for line in text.splitlines():
        if line.startswith("TCP_STAFF_MATCH "):
            out["match"] = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)}
            continue
        m = STAFF_PLAYER.match(line.strip())
        if m:
            fields = dict(re.findall(r"(\w+)=(\S+)", m.group(1)))
            row = {k: (int(v) if re.fullmatch(r"-?\d+", v) else v) for k, v in fields.items()}
            row["name"] = plain(m.group(2)).strip()
            out["players"][int(row["slot"])] = row
    return out


BAN_LINE = re.compile(r"^#(\d+)\s+ip\s+(\S+)\s+guid\s+(\S+)\s+name\s+'(.*?)'\s+added\s+(\S+(?: \S+)?)(.*)$")


def parse_banlist(text: str) -> list:
    bans = []
    for line in text.splitlines():
        m = BAN_LINE.match(line.strip())
        if not m:
            continue
        rest = m.group(6)
        left = re.search(r"\((\d+) min left\)", rest)
        reason = re.search(r"reason:\s*(.*)$", rest)
        puid = re.search(r"\bpuid (\S+)", rest)
        bans.append({"number": int(m.group(1)), "ip": "" if m.group(2) == "-" else m.group(2),
                     "guid": "" if m.group(3) == "-" else m.group(3), "name": m.group(4),
                     "added": m.group(5).strip(), "minutes_left": int(left.group(1)) if left else 0,
                     "reason": reason.group(1).strip() if reason else "", "puid": puid.group(1) if puid else ""})
    return bans


# ----------------------------------------------------------------------------- storage

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, discord_id TEXT, name TEXT, avatar TEXT, role TEXT,
  csrf TEXT, created INTEGER, seen INTEGER, checked INTEGER, token TEXT, ip TEXT);
CREATE TABLE IF NOT EXISTS staff(discord_id TEXT PRIMARY KEY, name TEXT, role TEXT, note TEXT, added_by TEXT,
  created INTEGER, last_login INTEGER);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER, discord_id TEXT, staff TEXT,
  role TEXT, action TEXT, server TEXT, target TEXT, target_pid TEXT, detail TEXT, ok INTEGER, result TEXT);
CREATE INDEX IF NOT EXISTS audit_at ON audit(at);
CREATE INDEX IF NOT EXISTS audit_pid ON audit(target_pid);
CREATE TABLE IF NOT EXISTS sightings(pid TEXT, guid TEXT, name TEXT, ip TEXT, puid TEXT, server TEXT,
  first_seen INTEGER, last_seen INTEGER, PRIMARY KEY(pid, name, ip, server));
CREATE INDEX IF NOT EXISTS sightings_name ON sightings(name);
CREATE INDEX IF NOT EXISTS sightings_ip ON sightings(ip);
CREATE INDEX IF NOT EXISTS sightings_seen ON sightings(last_seen);
CREATE TABLE IF NOT EXISTS bans(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, guid TEXT, ip TEXT, puid TEXT,
  name TEXT, reason TEXT, created INTEGER, expires INTEGER, by_id TEXT, by_name TEXT, active INTEGER DEFAULT 1,
  lifted INTEGER, lifted_by TEXT, lift_reason TEXT);
CREATE INDEX IF NOT EXISTS bans_active ON bans(active);
CREATE TABLE IF NOT EXISTS mutes(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, guid TEXT, name TEXT, reason TEXT,
  created INTEGER, expires INTEGER, by_name TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS warnings(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, name TEXT, text TEXT,
  created INTEGER, by_name TEXT, server TEXT);
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, text TEXT, created INTEGER, by_name TEXT);
CREATE TABLE IF NOT EXISTS chat(id INTEGER PRIMARY KEY AUTOINCREMENT, server TEXT, at INTEGER, slot INTEGER,
  team INTEGER, pid TEXT, name TEXT, text TEXT, kind TEXT);
CREATE INDEX IF NOT EXISTS chat_server ON chat(server, id);
CREATE INDEX IF NOT EXISTS chat_pid ON chat(pid);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, file TEXT UNIQUE,
  server TEXT, received INTEGER, data TEXT, target_pid TEXT, target_name TEXT, status TEXT DEFAULT 'open',
  claimed_by TEXT, resolution TEXT, updated INTEGER);
CREATE INDEX IF NOT EXISTS reports_status ON reports(status);
"""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript(SCHEMA)

    def q(self, sql: str, args=()) -> list:
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def one(self, sql: str, args=()):
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def x(self, sql: str, args=()) -> int:
        with self.lock:
            cur = self.db.execute(sql, args)
            return cur.lastrowid

    def audit(self, who: dict, action: str, server: str = "", target: str = "", pid: str = "",
              detail: str = "", ok: bool = True, result: str = "") -> None:
        self.x("INSERT INTO audit(at,discord_id,staff,role,action,server,target,target_pid,detail,ok,result) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
               (now(), who.get("discord_id", ""), who.get("name", "system"), who.get("role", ""), action, server,
                target, pid, detail[:500], 1 if ok else 0, (result or "")[:500]))


# ----------------------------------------------------------------------------- live servers

class GameServer:
    """One game server: rcon, the latest snapshot and what the portal knows about its players."""

    def __init__(self, cfg: dict, store: Store):
        self.cfg = cfg
        self.key = cfg["key"]
        self.name = cfg.get("name", self.key)
        self.host = cfg.get("host", "127.0.0.1")
        self.port = int(cfg["port"])
        self.store = store
        self.lock = threading.RLock()
        self.cmd_lock = threading.Lock()
        self.snapshot = {"key": self.key, "name": self.name, "online": False, "players": [], "updated": 0}
        self.guids = {}          # slot -> (connect marker, guid, ip, userinfo name)
        self.names = {}          # slot -> last known name (chat lines arrive after a player leaves too)
        self.caps = None         # TCP_STAFF_CAPS features, or [] on a server without the staff commands
        self.caps_at = 0
        self.info = {}
        self.info_at = 0
        self.error = ""

    # -- rcon
    def run(self, command: str, timeout: float = 1.5) -> str:
        with self.cmd_lock:                      # one command at a time per server: replies never mix
            return rcon(self.host, self.port, read_password(self.cfg), command, timeout=timeout)

    def has(self, feature: str) -> bool:
        return bool(self.caps) and feature in self.caps

    # -- polling
    def poll(self) -> None:
        t = now()
        try:
            if self.caps is None or t - self.caps_at > 300:
                text = self.run("tcp_staffcaps")
                m = re.search(r"TCP_STAFF_CAPS (\d+) (.*)", text)
                self.caps = m.group(2).split() if m else []
                self.caps_at = t
            if t - self.info_at > 30 or not self.info:
                self.info = parse_info(self.run("serverinfo"))
                self.info_at = t
            status = parse_status(self.run("status"))
            ac = parse_acstatus(self.run("acstatus"))
            staff = parse_staff_players(self.run("tcp_players")) if self.has("players") else {"match": {}, "players": {}}
        except (RconError, OSError) as e:
            with self.lock:
                self.error = str(e)
                self.snapshot = dict(self.snapshot, online=False, error=self.error, updated=t)
            return
        players = []
        for slot, p in sorted(status["players"].items()):
            extra = staff["players"].get(slot, {})
            acp = ac["players"].get(slot, {})
            bot = p["bot"] or bool(extra.get("bot"))
            row = {
                "slot": slot, "name": extra.get("name") or p["name"], "score": p["score"], "ping": p["ping"],
                "state": p["state"], "bot": bot, "connected_s": p["connected_s"],
                "team": extra.get("team"), "spectator": bool(extra.get("spec")), "alive": bool(extra.get("alive")),
                "muted_s": extra.get("muted", 0), "kills": extra.get("kills"), "deaths": extra.get("deaths"),
                "team_kills": extra.get("team_kills"), "damage": extra.get("damage"),
                "eac": acp.get("eac", ""), "files": acp.get("files", ""), "detections": acp.get("detections", 0),
                "puid": acp.get("puid", ""), "ip": "" if bot else host_of(p["address"]),
            }
            if not bot:
                self._identify(slot, row)
            self.names[slot] = row["name"]
            players.append(row)
        live = {p["slot"] for p in players}
        for slot in list(self.guids):
            if slot not in live:
                del self.guids[slot]
        snap = {
            "key": self.key, "name": self.name, "online": True, "updated": t, "error": "",
            "address": self.cfg.get("public_address", "%s:%d" % (self.host, self.port)),
            "kind": self.cfg.get("kind", "official"), "unit": self.cfg.get("unit", ""),
            "hostname": plain(self.info.get("sv_hostname", self.name)),
            "map": status["map"] or self.info.get("mapname", ""),
            "mode": self.info.get("tcp_mode", ""), "max_players": int(self.info.get("sv_maxclients", "0") or 0),
            "ranked": self.info.get("tcp_ranked", "") == "1" or "Ranked" in self.name and "Unranked" not in self.name,
            "eac": ac.get("eac_mode") or {"2": "required", "1": "on"}.get(self.info.get("sv_eac", "0"), "off"),
            "needpass": self.info.get("g_needpass", "0") == "1",
            "rotation": self.info.get("sv_mapRotation", ""),
            "match": staff.get("match", {}), "staff_commands": self.caps or [],
            "humans": sum(1 for p in players if not p["bot"]), "bots": sum(1 for p in players if p["bot"]),
            "players": players,
        }
        with self.lock:
            self.error = ""
            self.snapshot = snap
        self._reapply_mutes(players)

    def _identify(self, slot: int, row: dict) -> None:
        marker = (row["ip"], row["name"]) if not row["connected_s"] else (row["ip"],)
        known = self.guids.get(slot)
        if not known or known[0] != marker:
            try:
                info = parse_info(self.run("dumpuser %d" % slot))
            except RconError:
                info = {}
            guid = info.get("cl_guid", "")
            ip = host_of(info.get("ip", "")) or row["ip"]
            self.guids[slot] = known = (marker, guid, ip)
        _, guid, ip = known
        row["guid"] = guid
        row["pid"] = player_pid(guid)
        row["ip"] = ip or row["ip"]
        if row["pid"]:
            t = now()
            self.store.x("INSERT INTO sightings(pid,guid,name,ip,puid,server,first_seen,last_seen) VALUES(?,?,?,?,?,?,?,?) "
                         "ON CONFLICT(pid,name,ip,server) DO UPDATE SET last_seen=excluded.last_seen, "
                         "puid=CASE WHEN excluded.puid<>'' THEN excluded.puid ELSE sightings.puid END, guid=excluded.guid",
                         (row["pid"], guid, row["name"], row["ip"], row.get("puid", ""), self.key, t, t))

    def _reapply_mutes(self, players: list) -> None:
        """Mutes live in the game only until the map changes; the portal puts them back."""
        if not self.has("mute"):
            return
        t = now()
        for p in players:
            if p["bot"] or not p.get("pid") or p.get("muted_s"):
                continue
            m = self.store.one("SELECT * FROM mutes WHERE pid=? AND active=1 AND (expires=0 OR expires>?) "
                               "ORDER BY id DESC LIMIT 1", (p["pid"], t))
            if m:
                left = 0 if not m["expires"] else max(1, (m["expires"] - t + 59) // 60)
                try:
                    self.run("mute %d %d %s" % (p["slot"], left, safe_arg(m["reason"], 80)))
                    self.run("voicemute %d" % p["slot"])
                except RconError:
                    pass

    def slot_player(self, slot: int) -> dict | None:
        with self.lock:
            for p in self.snapshot.get("players", []):
                if p["slot"] == slot:
                    return dict(p)
        return None

    def view(self) -> dict:
        with self.lock:
            return json.loads(json.dumps(self.snapshot))


# ----------------------------------------------------------------------------- the portal

class Portal:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        data = Path(cfg.get("data_dir", "/var/lib/tcp-staff-portal"))
        data.mkdir(parents=True, exist_ok=True)
        self.store = Store(str(data / "portal.db"))
        self.servers = {s["key"]: GameServer(s, self.store) for s in cfg.get("servers", [])}
        self.order = [s["key"] for s in cfg.get("servers", [])]
        self.stop = threading.Event()
        self.chat_offsets = {}
        self.rate = {}
        self.rate_lock = threading.Lock()
        self.health_cache = (0, None)
        for d in cfg.get("owners", []):
            self.store.x("INSERT INTO staff(discord_id,name,role,note,added_by,created) VALUES(?,?,?,?,?,?) "
                         "ON CONFLICT(discord_id) DO UPDATE SET role='owner'",
                         (str(d), "", "owner", "from config", "config", now()))

    # ------------------------------------------------------------------ background work
    def start(self) -> None:
        loops = [(self.poll_loop, "poll"), (self.report_loop, "reports"), (self.ban_loop, "bans"),
                 (self.prune_loop, "prune")]
        for s in self.servers.values():
            loops.append((lambda s=s: self.chat_loop(s), "chat-" + s.key))
        for fn, name in loops:
            threading.Thread(target=self._guard, args=(fn, name), name=name, daemon=True).start()

    def _guard(self, fn, name) -> None:
        while not self.stop.is_set():
            try:
                fn()
            except Exception:  # noqa: BLE001
                log.exception("%s loop failed; restarting in 5 s", name)
            self.stop.wait(5)

    def poll_loop(self) -> None:
        every = float(self.cfg.get("poll_seconds", 3))
        while not self.stop.is_set():
            started = time.time()
            threads = [threading.Thread(target=s.poll, daemon=True) for s in self.servers.values()]
            for th in threads:
                th.start()
            for th in threads:
                th.join(10)
            self.stop.wait(max(0.5, every - (time.time() - started)))

    # chat comes from the game's own log line: TCP_NATIVE_SAY slot=N team=T text
    SAY = re.compile(r"TCP_NATIVE_SAY slot=(\d+) team=(\d+) (.*)$")

    def chat_loop(self, server: GameServer) -> None:
        src = server.cfg.get("log_file")
        if src:
            self._tail_file(server, Path(src))
        elif server.cfg.get("unit") and shutil.which("journalctl"):
            self._tail_journal(server)
        else:
            self.stop.wait(3600)

    def _chat_line(self, server: GameServer, line: str) -> None:
        line = plain(line).rstrip()
        m = self.SAY.search(line)
        if m:
            slot, team, text = int(m.group(1)), int(m.group(2)), m.group(3)
            p = server.slot_player(slot) or {}
            name = p.get("name") or server.names.get(slot) or "slot %d" % slot
            self.store.x("INSERT INTO chat(server,at,slot,team,pid,name,text,kind) VALUES(?,?,?,?,?,?,?,?)",
                         (server.key, now(), slot, p.get("team") if team else None, p.get("pid", ""), name, text[:300],
                          "team" if team else "all"))
            return

    def _tail_journal(self, server: GameServer) -> None:
        cmd = ["journalctl", "-u", server.cfg["unit"], "-f", "-n", "0", "-o", "cat", "--no-pager"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace")
        try:
            for line in p.stdout:
                if self.stop.is_set():
                    break
                if "TCP_NATIVE_SAY" in line:
                    self._chat_line(server, line)
        finally:
            p.kill()

    def _tail_file(self, server: GameServer, path: Path) -> None:
        pos = path.stat().st_size if path.exists() else 0
        while not self.stop.is_set():
            try:
                size = path.stat().st_size
                if size < pos:
                    pos = 0
                if size > pos:
                    with path.open("r", encoding="latin-1", errors="replace") as f:
                        f.seek(pos)
                        for line in f:
                            if line.endswith("\n"):
                                self._chat_line(server, line)
                                pos += len(line.encode("latin-1", "replace"))
                            else:
                                break
            except OSError:
                pass
            self.stop.wait(0.5)

    # player reports written by the game (tcp-report/1); the Discord bot moves them to reports/sent/
    def report_loop(self) -> None:
        while not self.stop.is_set():
            self.scan_reports()
            self.stop.wait(15)

    def scan_reports(self) -> int:
        added = 0
        for s in self.servers.values():
            folder = s.cfg.get("reports_dir")
            if not folder:
                continue
            for d in (Path(folder), Path(folder) / "sent"):
                try:
                    files = sorted(d.glob("*.json"))[-500:]
                except OSError:
                    continue
                for f in files:
                    key = "%s/%s" % (s.key, f.name)
                    if self.store.one("SELECT id FROM reports WHERE file=?", (key,)):
                        continue
                    try:
                        r = json.loads(f.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        continue
                    if not isinstance(r, dict) or not isinstance(r.get("reported"), dict):
                        continue
                    who = r["reported"]
                    self.store.x("INSERT OR IGNORE INTO reports(source,file,server,received,data,target_pid,target_name,status,updated) "
                                 "VALUES(?,?,?,?,?,?,?,?,?)",
                                 ("auto" if r.get("auto") else "player", key, s.key, now(), json.dumps(r),
                                  str(who.get("id") or ""), plain(who.get("name"))[:64], "open", now()))
                    added += 1
        return added

    # bans: expiry and making sure every server still has every ban
    def ban_loop(self) -> None:
        while not self.stop.is_set():
            self.expire_bans()
            self.reconcile_bans()
            self.stop.wait(float(self.cfg.get("ban_sync_seconds", 300)))

    def expire_bans(self) -> None:
        t = now()
        for b in self.store.q("SELECT * FROM bans WHERE active=1 AND expires>0 AND expires<=?", (t,)):
            self._lift_everywhere(b)
            self.store.x("UPDATE bans SET active=0, lifted=?, lifted_by='expired' WHERE id=?", (t, b["id"]))
        self.store.x("UPDATE mutes SET active=0 WHERE active=1 AND expires>0 AND expires<=?", (t,))

    def reconcile_bans(self) -> dict:
        report = {}
        active = self.store.q("SELECT * FROM bans WHERE active=1")
        for s in self.servers.values():
            try:
                listed = parse_banlist(s.run("banlist", timeout=2))
            except RconError as e:
                report[s.key] = "offline: %s" % e
                continue
            have_guid = {b["guid"].upper() for b in listed if b["guid"]}
            have_puid = {b["puid"].lower() for b in listed if b["puid"]}
            fixed = 0
            for b in active:
                if (b["guid"] and b["guid"].upper() not in have_guid) or (b["puid"] and b["puid"].lower() not in have_puid):
                    self._apply_ban(s, b, slot=None)
                    fixed += 1
            report[s.key] = "ok, %d re-applied" % fixed
        return report

    def _apply_ban(self, s: GameServer, b: dict, slot: int | None) -> list:
        left = 0 if not b["expires"] else max(1, (b["expires"] - now() + 59) // 60)
        length = engine_length(left)
        reason = safe_arg(b["reason"], 100)
        done = []
        if slot is not None:
            done.append(s.run(("ban %d %s %s" % (slot, length, reason)).strip()))
        else:
            if b["guid"]:
                done.append(s.run(("banguid %s %s %s" % (safe_arg(b["guid"], 40), length, reason)).strip()))
            if b["ip"] and self.cfg.get("ban_ip", True):
                done.append(s.run(("banip %s %s %s" % (safe_arg(b["ip"], 60), length, reason)).strip()))
        if b["puid"]:
            done.append(s.run(("banpuid %s %s" % (safe_arg(b["puid"], 64), reason)).strip()))
        return done

    def _lift_everywhere(self, b: dict) -> dict:
        out = {}
        for s in self.servers.values():
            res = []
            for v in (b.get("guid"), b.get("ip"), b.get("puid")):
                if v:
                    try:
                        res.append(s.run("unban %s" % safe_arg(v, 64)).strip())
                    except RconError as e:
                        res.append("offline: %s" % e)
            out[s.key] = "; ".join(x for x in res if x) or "nothing to lift"
        return out

    def prune_loop(self) -> None:
        while not self.stop.is_set():
            days = int(self.cfg.get("retention_days", 90))
            cut = now() - days * 86400
            self.store.x("DELETE FROM chat WHERE at<?", (now() - int(self.cfg.get("chat_days", 30)) * 86400,))
            self.store.x("DELETE FROM sightings WHERE last_seen<?", (cut,))
            self.store.x("DELETE FROM sessions WHERE seen<?", (now() - 86400,))
            self.stop.wait(3600)

    # ------------------------------------------------------------------ queries used by the API
    def server(self, key: str) -> GameServer:
        s = self.servers.get(str(key or ""))
        if not s:
            raise ApiError(404, "Unknown server.")
        return s

    def servers_view(self) -> list:
        out = []
        for key in self.order:
            v = self.servers[key].view()
            pids = [p.get("pid") for p in v.get("players", []) if p.get("pid")]
            flags = self._flags(pids)
            for p in v.get("players", []):
                p.update(flags.get(p.get("pid"), {}))
            out.append(v)
        return out

    def _flags(self, pids: list) -> dict:
        out = {}
        if not pids:
            return out
        marks = ",".join("?" * len(pids))
        t = now()
        for r in self.store.q("SELECT target_pid pid, COUNT(*) n FROM reports WHERE status<>'closed' AND target_pid IN (%s) "
                              "GROUP BY target_pid" % marks, pids):
            out.setdefault(r["pid"], {})["open_reports"] = r["n"]
        for r in self.store.q("SELECT pid, COUNT(*) n FROM warnings WHERE pid IN (%s) GROUP BY pid" % marks, pids):
            out.setdefault(r["pid"], {})["warnings"] = r["n"]
        for r in self.store.q("SELECT pid, COUNT(*) n FROM bans WHERE pid IN (%s) GROUP BY pid" % marks, pids):
            out.setdefault(r["pid"], {})["past_bans"] = r["n"]
        for r in self.store.q("SELECT pid, expires FROM mutes WHERE active=1 AND (expires=0 OR expires>?) AND pid IN (%s)" % marks,
                              [t] + pids):
            out.setdefault(r["pid"], {})["mute_until"] = r["expires"]
        return out

    def stats(self, route: str, **params):
        """The stats service's own JSON API (the bridge on 127.0.0.1:8090): no access to its database file needed."""
        base = self.cfg.get("stats_api")
        if not base:
            return None
        url = "%s/%s?%s" % (base.rstrip("/"), route, urllib.parse.urlencode(params))
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "TCPStaff"}), timeout=4) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def lookup(self, query: str, show_ip: bool) -> list:
        q = query.strip()
        if len(q) < 2:
            return []
        rows = {}
        like = "%" + q.replace("%", "").replace("_", "") + "%"
        params = [like, q.lower(), q]
        sql = ("SELECT pid, MAX(last_seen) last_seen, MIN(first_seen) first_seen FROM sightings "
               "WHERE name LIKE ? OR pid=? OR guid=?")
        try:
            ipaddress.ip_address(q)
            if show_ip:
                sql += " OR ip=?"
                params.append(q)
        except ValueError:
            pass
        sql += " GROUP BY pid ORDER BY last_seen DESC LIMIT 50"
        for r in self.store.q(sql, params):
            rows[r["pid"]] = {"pid": r["pid"], "last_seen": r["last_seen"], "first_seen": r["first_seen"]}
        found = self.stats("search.json", q=q) or {}
        for r in found.get("players", []):
            if PID.match(str(r.get("id", ""))):
                rows.setdefault(r["id"], {"pid": r["id"], "stats_name": r.get("name", "")})
        out = []
        for pid, r in list(rows.items())[:50]:
            names = self.store.q("SELECT name, MAX(last_seen) at FROM sightings WHERE pid=? GROUP BY name ORDER BY at DESC LIMIT 5", (pid,))
            r["names"] = [n["name"] for n in names] or ([r["stats_name"]] if r.get("stats_name") else [])
            r["banned"] = bool(self.store.one("SELECT id FROM bans WHERE pid=? AND active=1", (pid,)))
            out.append(r)
        return out

    def player(self, pid: str, show_ip: bool) -> dict:
        if not PID.match(pid):
            raise ApiError(400, "That is not a player id.")
        out = {"pid": pid}
        seen = self.store.q("SELECT name, ip, puid, guid, server, first_seen, last_seen FROM sightings WHERE pid=? "
                            "ORDER BY last_seen DESC LIMIT 200", (pid,))
        names = {}
        for s in seen:
            n = names.setdefault(s["name"], {"name": s["name"], "first_seen": s["first_seen"], "last_seen": s["last_seen"]})
            n["first_seen"] = min(n["first_seen"], s["first_seen"])
            n["last_seen"] = max(n["last_seen"], s["last_seen"])
        out["names"] = sorted(names.values(), key=lambda n: -n["last_seen"])
        out["servers"] = sorted({s["server"] for s in seen})
        out["puids"] = sorted({s["puid"] for s in seen if s["puid"]})
        out["first_seen"] = min((s["first_seen"] for s in seen), default=None)
        out["last_seen"] = max((s["last_seen"] for s in seen), default=None)
        if show_ip:
            ips = {}
            for s in seen:
                if s["ip"]:
                    ips[s["ip"]] = max(ips.get(s["ip"], 0), s["last_seen"])
            out["ips"] = [{"ip": k, "last_seen": v} for k, v in sorted(ips.items(), key=lambda kv: -kv[1])]
            alts = set()
            for ip in ips:
                for r in self.store.q("SELECT DISTINCT pid FROM sightings WHERE ip=? AND pid<>?", (ip, pid)):
                    alts.add(r["pid"])
            out["shared_ip"] = sorted(alts)[:20]
        out["bans"] = self.store.q("SELECT id,name,reason,created,expires,by_name,active,lifted,lifted_by,lift_reason "
                                   "FROM bans WHERE pid=? ORDER BY id DESC", (pid,))
        out["mutes"] = self.store.q("SELECT id,name,reason,created,expires,by_name,active FROM mutes WHERE pid=? ORDER BY id DESC", (pid,))
        out["warnings"] = self.store.q("SELECT id,name,text,created,by_name,server FROM warnings WHERE pid=? ORDER BY id DESC", (pid,))
        out["notes"] = self.store.q("SELECT id,text,created,by_name FROM notes WHERE pid=? ORDER BY id DESC", (pid,))
        out["reports"] = [self._report_row(r) for r in self.store.q(
            "SELECT * FROM reports WHERE target_pid=? ORDER BY id DESC LIMIT 50", (pid,))]
        out["actions"] = self.store.q("SELECT at, staff, action, server, detail, ok FROM audit WHERE target_pid=? "
                                      "ORDER BY id DESC LIMIT 100", (pid,))
        out["chat"] = self.store.q("SELECT server, at, kind, name, text FROM chat WHERE pid=? ORDER BY id DESC LIMIT 100", (pid,))
        out["online"] = [{"server": s.key, "slot": p["slot"], "name": p["name"]}
                         for s in self.servers.values() for p in s.view().get("players", []) if p.get("pid") == pid]
        st = self.stats("player.json", id=pid)
        out["stats"] = st
        out["matches"] = (st or {}).get("recent", [])
        out["profile_url"] = "%s/player.html?id=%s" % (self.cfg.get("site", "https://truecombat.eu").rstrip("/"), pid)
        return out

    def _report_row(self, r: dict) -> dict:
        r = dict(r)
        try:
            r["data"] = json.loads(r["data"])
        except (TypeError, ValueError):
            r["data"] = {}
        return r

    def health(self) -> dict:
        t, cached = self.health_cache
        if cached and time.time() - t < 5:
            return cached
        h = {"time": now(), "portal_version": VERSION}
        try:
            h["load"] = [float(x) for x in Path("/proc/loadavg").read_text().split()[:3]]
            h["cpus"] = os.cpu_count()
            mem = dict(re.findall(r"^(\w+):\s+(\d+)", Path("/proc/meminfo").read_text(), re.M))
            h["mem_total_mb"] = int(mem.get("MemTotal", 0)) // 1024
            h["mem_available_mb"] = int(mem.get("MemAvailable", 0)) // 1024
            h["uptime_s"] = int(float(Path("/proc/uptime").read_text().split()[0]))
        except (OSError, ValueError):
            pass
        try:
            st = os.statvfs(self.cfg.get("disk_path", "/"))
            h["disk_total_gb"] = round(st.f_blocks * st.f_frsize / 1e9, 1)
            h["disk_free_gb"] = round(st.f_bavail * st.f_frsize / 1e9, 1)
        except OSError:
            pass
        units = []
        for s in self.servers.values():
            units.append(self._unit(s.cfg.get("unit"), s.key, s.name))
        for extra in self.cfg.get("services", []):
            units.append(self._unit(extra.get("unit"), extra.get("key", extra.get("unit")), extra.get("name", extra.get("unit"))))
        h["services"] = units
        self.health_cache = (time.time(), h)
        return h

    def _unit(self, unit: str | None, key: str, name: str) -> dict:
        row = {"key": key, "name": name, "unit": unit or "", "state": "unknown"}
        if not unit or not shutil.which("systemctl"):
            return row
        try:
            out = subprocess.run(["systemctl", "show", unit, "--no-pager", "-p",
                                  "ActiveState,SubState,ActiveEnterTimestamp,NRestarts,MemoryCurrent,CPUUsageNSec,MainPID"],
                                 capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.SubprocessError):
            return row
        p = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
        row["state"] = p.get("ActiveState", "unknown")
        row["sub"] = p.get("SubState", "")
        row["since"] = p.get("ActiveEnterTimestamp", "")
        row["restarts"] = int(p["NRestarts"]) if p.get("NRestarts", "").isdigit() else None
        row["memory_mb"] = int(p["MemoryCurrent"]) // 1048576 if p.get("MemoryCurrent", "").isdigit() else None
        row["cpu_s"] = int(p["CPUUsageNSec"]) // 10**9 if p.get("CPUUsageNSec", "").isdigit() else None
        try:
            j = subprocess.run(["journalctl", "-u", unit, "--since", "-24h", "--no-pager", "-o", "cat",
                                "--grep", r"segfault|core dumped|Main process exited|Failed with result"],
                               capture_output=True, text=True, timeout=5).stdout
            lines = [x for x in j.splitlines() if x.strip() and not x.startswith("-- ")]
            row["problems_24h"] = len(lines)
            row["last_problem"] = lines[-1][:200] if lines else ""
        except (OSError, subprocess.SubprocessError):
            pass
        return row

    # ------------------------------------------------------------------ rate limit (per key, per window)
    def limited(self, key: str, limit: int, window: int) -> bool:
        t = time.time()
        with self.rate_lock:
            hits = [x for x in self.rate.get(key, []) if t - x < window]
            if len(hits) >= limit:
                self.rate[key] = hits
                return True
            hits.append(t)
            self.rate[key] = hits
            if len(self.rate) > 5000:
                self.rate = {k: v for k, v in self.rate.items() if v and t - v[-1] < 3600}
            return False


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ----------------------------------------------------------------------------- Discord sign-in

DISCORD_API = "https://discord.com/api/v10"


def http_json(url: str, data: dict | None = None, token: str | None = None, timeout: float = 8) -> dict:
    headers = {"User-Agent": "TrueCombatStaffPortal/%s" % VERSION, "Accept": "application/json"}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def secret(cfg: dict, name: str) -> str:
    cred = os.environ.get("CREDENTIALS_DIRECTORY")
    if cred and (Path(cred) / name).exists():
        return (Path(cred) / name).read_text(encoding="utf-8").strip()
    return str(cfg.get("discord", {}).get(name.replace("-", "_"), "") or "")


def resolve_role(portal: Portal, discord_id: str, member_roles: list) -> str | None:
    """Highest role from: the manual staff list (which can also revoke), owners, Discord roles."""
    d = portal.cfg.get("discord", {})
    row = portal.store.one("SELECT role FROM staff WHERE discord_id=?", (discord_id,))
    if row and row["role"] == "revoked":
        return None
    best = row["role"] if row and row["role"] in RANK else None
    if str(discord_id) in {str(x) for x in portal.cfg.get("owners", [])}:
        best = "owner"
    roles = {str(r) for r in member_roles or []}
    for role, ids in (("admin", d.get("admin_role_ids", [])), ("moderator", d.get("moderator_role_ids", []))):
        if roles & {str(x) for x in ids} and RANK[role] > RANK.get(best, 0):
            best = role
    return best


# ----------------------------------------------------------------------------- HTTP

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": ("default-src 'self'; img-src 'self' data: https://cdn.discordapp.com; "
                                "style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                                "base-uri 'none'; form-action 'self' https://discord.com"),
}
SESSION_HOURS = 12
RECHECK_SECONDS = 600


def make_handler(portal: Portal):
    cfg = portal.cfg
    public = cfg.get("public_url", "http://127.0.0.1:%d" % cfg.get("port", 8097)).rstrip("/")
    secure_cookie = public.startswith("https://")
    cookie_name = ("__Host-" if secure_cookie else "") + "tcpstaff"
    dev_login = bool(cfg.get("dev_login")) and os.environ.get("TCP_STAFF_DEV") == "1"

    class Handler(BaseHTTPRequestHandler):
        server_version = "TCPStaff"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # noqa: D401
            log.info("%s %s", self.client_ip(), fmt % args)

        # -- plumbing
        def client_ip(self) -> str:
            ip = self.client_address[0]
            if ip in ("127.0.0.1", "::1") and self.headers.get("X-Forwarded-For"):
                return self.headers["X-Forwarded-For"].split(",")[-1].strip()
            return ip

        def send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
            unread = int(self.headers.get("Content-Length") or 0) and not getattr(self, "_body_read", False)
            self.send_response(status)
            if unread:                       # an early refusal left the body in the stream: never reuse it
                self.close_connection = True
                self.send_header("Connection", "close")
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in SECURITY_HEADERS.items():
                self.send_header(k, v)
            if secure_cookie:
                self.send_header("Strict-Transport-Security", "max-age=31536000")
            for k, v in (extra or {}).items():
                if isinstance(v, list):
                    for item in v:
                        self.send_header(k, item)
                else:
                    self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def json(self, data, status: int = 200, extra: dict | None = None) -> None:
            self.send(status, json.dumps(data, separators=(",", ":")).encode(), "application/json; charset=utf-8", extra)

        def redirect(self, to: str, cookies: list | None = None) -> None:
            self.send(302, b"", "text/plain", {"Location": to, "Set-Cookie": cookies or []})

        def body(self, limit: int = 65536) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            if n > limit:
                raise ApiError(413, "Too much data.")
            self._body_read = True
            return self.rfile.read(n) if n else b""

        def body_json(self) -> dict:
            try:
                data = json.loads(self.body() or b"{}")
            except ValueError as e:
                raise ApiError(400, "Bad JSON.") from e
            if not isinstance(data, dict):
                raise ApiError(400, "Bad JSON.")
            return data

        def cookie(self, name: str) -> str:
            for part in (self.headers.get("Cookie") or "").split(";"):
                k, _, v = part.strip().partition("=")
                if k == name:
                    return v
            return ""

        def set_cookie(self, name: str, value: str, max_age: int) -> str:
            c = "%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d" % (name, value, max_age)
            return c + ("; Secure" if secure_cookie else "")

        # -- sessions
        def session(self) -> dict | None:
            sid = self.cookie(cookie_name)
            if not sid or not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", sid):
                return None
            s = portal.store.one("SELECT * FROM sessions WHERE id=?", (hashlib.sha256(sid.encode()).hexdigest(),))
            if not s:
                return None
            t = now()
            if t - s["created"] > SESSION_HOURS * 3600:
                portal.store.x("DELETE FROM sessions WHERE id=?", (s["id"],))
                return None
            if t - (s["checked"] or 0) > RECHECK_SECONDS:
                role = self.recheck(s)
                if not role:
                    portal.store.x("DELETE FROM sessions WHERE id=?", (s["id"],))
                    return None
                s["role"] = role
                portal.store.x("UPDATE sessions SET role=?, checked=? WHERE id=?", (role, t, s["id"]))
            if t - s["seen"] > 60:
                portal.store.x("UPDATE sessions SET seen=? WHERE id=?", (t, s["id"]))
            return s

        def recheck(self, s: dict) -> str | None:
            """Staff rights follow Discord: a removed role or a revoked entry ends the session within minutes."""
            if s["token"] == "dev":
                return resolve_role(portal, s["discord_id"], []) or s["role"]
            guild = cfg.get("discord", {}).get("guild_id")
            try:
                member = http_json("%s/users/@me/guilds/%s/member" % (DISCORD_API, guild), token=s["token"])
                roles = member.get("roles", [])
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404):
                    roles = []
                else:
                    return s["role"]          # Discord trouble: keep the session for now
            except (urllib.error.URLError, OSError, ValueError):
                return s["role"]
            return resolve_role(portal, s["discord_id"], roles)

        def new_session(self, discord_id: str, name: str, avatar: str, role: str, token: str) -> str:
            sid = secrets.token_urlsafe(32)
            t = now()
            portal.store.x("INSERT INTO sessions(id,discord_id,name,avatar,role,csrf,created,seen,checked,token,ip) "
                           "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (hashlib.sha256(sid.encode()).hexdigest(), discord_id, name, avatar, role,
                            secrets.token_urlsafe(24), t, t, t, token, self.client_ip()))
            portal.store.x("INSERT INTO staff(discord_id,name,role,note,added_by,created,last_login) VALUES(?,?,NULL,'',"
                           "'discord',?,?) ON CONFLICT(discord_id) DO UPDATE SET name=excluded.name, last_login=excluded.last_login",
                           (discord_id, name, t, t))
            portal.store.audit({"discord_id": discord_id, "name": name, "role": role}, "sign-in", detail=self.client_ip())
            return sid

        def need(self, s: dict | None, perm: str) -> dict:
            if not s:
                raise ApiError(401, "Please sign in.")
            if not allowed(s["role"], perm):
                raise ApiError(403, "Your role cannot do that.")
            return s

        # -- routing
        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            self.dispatch("GET")

        def do_POST(self):
            self.dispatch("POST")

        def dispatch(self, method: str) -> None:
            url = urllib.parse.urlsplit(self.path)
            path = url.path
            qs = dict(urllib.parse.parse_qsl(url.query))
            try:
                if method == "GET" and (path == "/" or path == "/index.html"):
                    return self.static("index.html")
                if method == "GET" and path.startswith("/static/"):
                    return self.static(path[len("/static/"):])
                if path == "/healthz":
                    return self.json({"ok": True, "version": VERSION})
                if path.startswith("/auth/"):
                    return self.auth(method, path, qs)
                if path == "/api/bugreport" and method == "POST":
                    return self.bugreport()
                if path.startswith("/api/"):
                    s = self.session()
                    if method == "POST":
                        if not s:
                            raise ApiError(401, "Please sign in.")
                        if not hmac.compare_digest(self.headers.get("X-CSRF", ""), s["csrf"]):
                            raise ApiError(403, "Your session expired. Reload the page.")
                        origin = self.headers.get("Origin")
                        if origin and origin.rstrip("/") != public:
                            raise ApiError(403, "Wrong origin.")
                    return self.api(method, path[len("/api/"):], qs, s)
                raise ApiError(404, "Not found.")
            except (BrokenPipeError, ConnectionResetError):
                return
            except ApiError as e:
                self.json({"error": e.message}, e.status)
            except RconError as e:
                self.json({"error": "The game server did not take the command: %s" % e}, 502)
            except Exception:  # noqa: BLE001
                log.exception("request failed: %s %s", method, path)
                self.json({"error": "Something went wrong on the portal. It has been logged."}, 500)

        def static(self, name: str) -> None:
            target = (STATIC / name).resolve()
            if STATIC.resolve() not in target.parents or not target.is_file():
                raise ApiError(404, "Not found.")
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript",):
                ctype += "; charset=utf-8"
            self.send(200, target.read_bytes(), ctype)

        # -- sign-in
        def auth(self, method: str, path: str, qs: dict) -> None:
            d = cfg.get("discord", {})
            if path == "/auth/login":
                state = secrets.token_urlsafe(24)
                url = "https://discord.com/oauth2/authorize?" + urllib.parse.urlencode({
                    "client_id": d.get("client_id", ""), "response_type": "code",
                    "redirect_uri": public + "/auth/callback", "scope": "identify guilds.members.read",
                    "state": state, "prompt": "none"})
                return self.redirect(url, [self.set_cookie("tcpstaff_state", state, 600)])
            if path == "/auth/callback":
                state = self.cookie("tcpstaff_state")
                if not state or not hmac.compare_digest(state, qs.get("state", "")) or not qs.get("code"):
                    return self.redirect("/?signin=failed")
                if portal.limited("login:" + self.client_ip(), 10, 600):
                    return self.redirect("/?signin=slow")
                try:
                    tok = http_json(DISCORD_API + "/oauth2/token", {
                        "client_id": d.get("client_id", ""), "client_secret": secret(cfg, "client-secret"),
                        "grant_type": "authorization_code", "code": qs["code"],
                        "redirect_uri": public + "/auth/callback"})
                    token = tok["access_token"]
                    me = http_json(DISCORD_API + "/users/@me", token=token)
                    try:
                        member = http_json("%s/users/@me/guilds/%s/member" % (DISCORD_API, d.get("guild_id")), token=token)
                    except urllib.error.HTTPError:
                        member = {}
                except (urllib.error.URLError, OSError, ValueError, KeyError):
                    log.exception("Discord sign-in failed")
                    return self.redirect("/?signin=discord")
                discord_id = str(me.get("id"))
                role = resolve_role(portal, discord_id, member.get("roles", []))
                name = member.get("nick") or me.get("global_name") or me.get("username") or "Staff"
                if not role:
                    portal.store.audit({"discord_id": discord_id, "name": name}, "sign-in refused", detail=self.client_ip(), ok=False)
                    return self.redirect("/?signin=denied", [self.set_cookie("tcpstaff_state", "", 0)])
                avatar = ("https://cdn.discordapp.com/avatars/%s/%s.png?size=64" % (discord_id, me["avatar"])) if me.get("avatar") else ""
                sid = self.new_session(discord_id, name, avatar, role, token)
                return self.redirect("/", [self.set_cookie(cookie_name, sid, SESSION_HOURS * 3600),
                                           self.set_cookie("tcpstaff_state", "", 0)])
            if (path == "/auth/dev" and dev_login and self.client_address[0] in ("127.0.0.1", "::1")
                    and not self.headers.get("X-Forwarded-For")):          # never through the reverse proxy
                role = qs.get("role", "owner")
                if role not in RANK:
                    raise ApiError(400, "Unknown role.")
                did = qs.get("id", "dev-" + role)
                sid = self.new_session(did, qs.get("name", "Dev " + role.title()), "", role, "dev")
                return self.redirect("/", [self.set_cookie(cookie_name, sid, SESSION_HOURS * 3600)])
            if path == "/auth/logout" and method == "POST":
                s = self.session()
                if s and hmac.compare_digest(self.headers.get("X-CSRF", ""), s["csrf"]):
                    portal.store.x("DELETE FROM sessions WHERE id=?", (s["id"],))
                return self.json({"ok": True}, extra={"Set-Cookie": [self.set_cookie(cookie_name, "", 0)]})
            raise ApiError(404, "Not found.")

        # -- public bug report intake (the launcher uploads F12 reports here when cl_bugReportUrl points at it)
        def bugreport(self) -> None:
            ip = self.client_ip()
            if portal.limited("bug:" + ip, int(cfg.get("bugreport_per_hour", 6)), 3600) or portal.limited("bug:*", 300, 86400):
                raise ApiError(429, "Too many reports from this address. Try again later.")
            raw = self.body(limit=int(cfg.get("bugreport_max_bytes", 96 * 1024)))
            text = raw.decode("utf-8", "replace").replace("\x00", "")
            if len(text.strip()) < 10:
                raise ApiError(400, "The report is empty.")
            category = safe_arg(self.headers.get("X-Report-Category", ""), 20) or "Bug"
            first = next((ln for ln in text.splitlines() if ln.strip()), "")[:120]
            key = "bug/%d-%s" % (now(), secrets.token_hex(4))
            portal.store.x("INSERT INTO reports(source,file,server,received,data,target_pid,target_name,status,updated) "
                           "VALUES('bug',?,?,?,?,?,?,'open',?)",
                           (key, "", now(), json.dumps({"category": category, "text": text, "summary": first,
                                                        "from": hashlib.sha256(ip.encode()).hexdigest()[:12]}),
                            "", "", now()))
            self.json({"ok": True, "id": key}, 201)

        # -- API
        def api(self, method: str, route: str, qs: dict, s: dict | None) -> None:
            if route == "me" and method == "GET":
                if not s:
                    return self.json({"signed_in": False, "dev_login": dev_login})
                perms = sorted(p for p in PERMS if allowed(s["role"], p))
                return self.json({"signed_in": True, "name": s["name"], "avatar": s["avatar"], "role": s["role"],
                                  "discord_id": s["discord_id"], "csrf": s["csrf"], "perms": perms,
                                  "mod_ban_limit": MOD_BAN_LIMIT, "version": VERSION,
                                  "maps": cfg.get("maps", []), "site": cfg.get("site", "https://truecombat.eu")})
            if route == "servers" and method == "GET":
                self.need(s, "view")
                return self.json({"servers": portal.servers_view(), "time": now()})
            if route == "chat" and method == "GET":
                self.need(s, "view")
                after = int(qs.get("after") or 0)
                server = qs.get("server", "")
                args, sql = [after], "SELECT * FROM chat WHERE id>?"
                if server:
                    sql += " AND server=?"
                    args.append(server)
                if after:
                    sql += " ORDER BY id ASC LIMIT 200"
                    rows = portal.store.q(sql, args)
                else:
                    rows = list(reversed(portal.store.q(sql + " ORDER BY id DESC LIMIT 150", args)))
                return self.json({"lines": rows})
            if route == "action" and method == "POST":
                return self.player_action(s, self.body_json())
            if route == "server" and method == "POST":
                return self.server_action(s, self.body_json())
            if route == "bans" and method == "GET":
                self.need(s, "view")
                show = qs.get("show", "active")
                where = "active=1" if show == "active" else "1=1"
                bans = portal.store.q("SELECT id,pid,name,reason,created,expires,by_name,active,lifted,lifted_by,lift_reason,"
                                      "guid<>'' has_guid, ip<>'' has_ip, puid<>'' has_puid FROM bans WHERE %s "
                                      "ORDER BY id DESC LIMIT 500" % where)
                return self.json({"bans": bans})
            if route == "bans" and method == "POST":
                return self.ban(s, self.body_json())
            if route == "bans/lift" and method == "POST":
                return self.unban(s, self.body_json())
            if route == "bans/server" and method == "GET":
                self.need(s, "ban.remove")
                out = {}
                for key in portal.order:
                    try:
                        out[key] = parse_banlist(portal.servers[key].run("banlist", timeout=2))
                    except RconError as e:
                        out[key] = {"error": str(e)}
                return self.json({"servers": out})
            if route == "bans/sync" and method == "POST":
                who = self.need(s, "ban.remove")
                rep = portal.reconcile_bans()
                portal.store.audit(who, "ban sync", detail=json.dumps(rep))
                return self.json({"result": rep})
            if route == "lookup" and method == "GET":
                who = self.need(s, "lookup")
                return self.json({"players": portal.lookup(qs.get("q", ""), allowed(who["role"], "lookup.ip"))})
            if route.startswith("player/") and method == "GET":
                who = self.need(s, "lookup")
                return self.json(portal.player(route[len("player/"):], allowed(who["role"], "lookup.ip")))
            if route == "notes" and method == "POST":
                who = self.need(s, "lookup")
                d = self.body_json()
                pid, text = str(d.get("pid", "")), str(d.get("text", "")).strip()[:1000]
                if not PID.match(pid) or not text:
                    raise ApiError(400, "Write a note first.")
                portal.store.x("INSERT INTO notes(pid,text,created,by_name) VALUES(?,?,?,?)", (pid, text, now(), who["name"]))
                portal.store.audit(who, "note", target=pid, pid=pid, detail=text[:200])
                return self.json({"ok": True})
            if route == "reports" and method == "GET":
                self.need(s, "reports")
                portal.scan_reports()
                status = qs.get("status", "open")
                where, args = ("status=?", [status]) if status in ("open", "claimed", "closed") else ("1=1", [])
                if qs.get("source") in ("player", "auto", "bug"):
                    where += " AND source=?"
                    args.append(qs["source"])
                rows = [portal._report_row(r) for r in portal.store.q(
                    "SELECT * FROM reports WHERE %s ORDER BY id DESC LIMIT 300" % where, args)]
                counts = {r["status"]: r["n"] for r in portal.store.q("SELECT status, COUNT(*) n FROM reports GROUP BY status")}
                return self.json({"reports": rows, "counts": counts})
            if route == "reports/update" and method == "POST":
                who = self.need(s, "reports")
                d = self.body_json()
                r = portal.store.one("SELECT * FROM reports WHERE id=?", (int(d.get("id") or 0),))
                if not r:
                    raise ApiError(404, "No such report.")
                status = d.get("status")
                if status not in ("open", "claimed", "closed"):
                    raise ApiError(400, "Unknown status.")
                resolution = str(d.get("resolution") or "").strip()[:500]
                portal.store.x("UPDATE reports SET status=?, claimed_by=?, resolution=?, updated=? WHERE id=?",
                               (status, who["name"] if status != "open" else None, resolution or r["resolution"], now(), r["id"]))
                portal.store.audit(who, "report " + status, server=r["server"], target=r["target_name"],
                                   pid=r["target_pid"], detail=resolution or ("#%d" % r["id"]))
                return self.json({"ok": True})
            if route == "audit" and method == "GET":
                self.need(s, "audit")
                args, where = [], "1=1"
                if qs.get("q"):
                    where = "(staff LIKE ? OR action LIKE ? OR target LIKE ? OR detail LIKE ? OR target_pid=?)"
                    like = "%" + qs["q"] + "%"
                    args = [like, like, like, like, qs["q"]]
                before = int(qs.get("before") or 0)
                if before:
                    where += " AND id<?"
                    args.append(before)
                return self.json({"entries": portal.store.q("SELECT * FROM audit WHERE %s ORDER BY id DESC LIMIT 200" % where, args)})
            if route == "staff" and method == "GET":
                self.need(s, "staff.manage")
                return self.json({"staff": portal.store.q("SELECT * FROM staff ORDER BY last_login DESC")})
            if route == "staff" and method == "POST":
                return self.staff_change(s, self.body_json())
            if route == "health" and method == "GET":
                self.need(s, "health")
                return self.json(portal.health())
            if route == "health/restart" and method == "POST":
                return self.restart(s, self.body_json())
            raise ApiError(404, "Not found.")

        # -- player actions
        def target(self, d: dict) -> tuple:
            srv = portal.server(d.get("server"))
            try:
                slot = int(d.get("slot"))
            except (TypeError, ValueError) as e:
                raise ApiError(400, "Pick a player.") from e
            p = srv.slot_player(slot)
            if not p:
                raise ApiError(409, "That player is no longer on the server.")
            if d.get("name") and plain(d["name"]) != p["name"]:
                raise ApiError(409, "That slot now belongs to someone else. Refresh and try again.")
            return srv, slot, p

        def player_action(self, s: dict | None, d: dict) -> None:
            act = d.get("action")
            perm = {"kick": "player.kick", "warn": "player.warn", "mute": "player.mute", "unmute": "player.mute",
                    "move": "player.move"}.get(act)
            if not perm:
                raise ApiError(400, "Unknown action.")
            who = self.need(s, perm)
            if portal.limited("act:" + who["discord_id"], 40, 60):
                raise ApiError(429, "Slow down a little.")
            srv, slot, p = self.target(d)
            reason = safe_arg(d.get("reason", ""), 100)
            detail, result = reason, ""
            if act == "kick":
                if not reason:
                    raise ApiError(400, "Give a reason. The player sees it.")
                result = srv.run("clientkick %d %s" % (slot, reason))
            elif act == "warn":
                if not reason:
                    raise ApiError(400, "Write the warning.")
                if not srv.has("warn"):
                    raise ApiError(409, "This server needs the 0.36.0 server update for private warnings.")
                result = srv.run("warn %d %s" % (slot, reason))
                portal.store.x("INSERT INTO warnings(pid,name,text,created,by_name,server) VALUES(?,?,?,?,?,?)",
                               (p.get("pid", ""), p["name"], reason, now(), who["name"], srv.key))
            elif act in ("mute", "unmute"):
                if not srv.has("mute"):
                    raise ApiError(409, "This server needs the 0.36.0 server update for mutes.")
                if act == "mute":
                    minutes = duration_minutes(d.get("length") or "30m")
                    detail = "%s, %s" % (engine_length(minutes) or "until lifted", reason)
                    result = srv.run("mute %d %d %s" % (slot, min(minutes, 10080) if minutes else 0, reason))
                    srv.run("voicemute %d" % slot)        # 0.36.0 voice chat; an unknown command on older servers
                    if p.get("pid"):
                        portal.store.x("UPDATE mutes SET active=0 WHERE pid=? AND active=1", (p["pid"],))
                        portal.store.x("INSERT INTO mutes(pid,guid,name,reason,created,expires,by_name) VALUES(?,?,?,?,?,?,?)",
                                       (p["pid"], p.get("guid", ""), p["name"], reason, now(),
                                        now() + minutes * 60 if minutes else 0, who["name"]))
                else:
                    result = srv.run("unmute %d" % slot)
                    srv.run("voiceunmute %d" % slot)
                    if p.get("pid"):
                        portal.store.x("UPDATE mutes SET active=0 WHERE pid=? AND active=1", (p["pid"],))
            elif act == "move":
                team = d.get("team")
                if team not in ("r", "b", "s"):
                    raise ApiError(400, "Pick a team.")
                detail = {"r": "to Terrorists", "b": "to Specops", "s": "to spectators"}[team]
                if srv.has("putteam"):
                    result = srv.run("putteam %d %s" % (slot, team))
                elif team == "s":
                    result = srv.run("spectate %d" % slot)
                else:
                    raise ApiError(409, "This server needs the 0.36.0 server update to move players between teams.")
            ok = "usage:" not in result.lower() and "refused" not in result.lower()
            portal.store.audit(who, act, server=srv.key, target=p["name"], pid=p.get("pid", ""), detail=detail,
                               ok=ok, result=plain(result).strip())
            if not ok:
                raise ApiError(409, "The server refused: %s" % plain(result).strip()[:200])
            self.json({"ok": True, "result": plain(result).strip()})

        def ban(self, s: dict | None, d: dict) -> None:
            minutes = duration_minutes(d.get("length", ""))
            who = self.need(s, "ban.temp" if minutes else "ban.perm")
            if minutes > MOD_BAN_LIMIT and not allowed(who["role"], "ban.perm"):
                raise ApiError(403, "Moderators can ban for up to 24 hours. Ask an admin for longer bans.")
            reason = safe_arg(d.get("reason", ""), 100)
            if not reason:
                raise ApiError(400, "Give a reason. The player sees it.")
            slot, srv = None, None
            if d.get("server") is not None and d.get("slot") is not None:
                srv, slot, p = self.target(d)
                if p["bot"]:
                    raise ApiError(400, "That is a bot.")
                b = {"pid": p.get("pid", ""), "guid": p.get("guid", ""), "ip": p.get("ip", ""), "puid": p.get("puid", ""),
                     "name": p["name"]}
            else:
                pid = str(d.get("pid", ""))
                if not PID.match(pid):
                    raise ApiError(400, "Pick a player.")
                last = portal.store.one("SELECT * FROM sightings WHERE pid=? ORDER BY last_seen DESC LIMIT 1", (pid,))
                if not last:
                    raise ApiError(404, "The portal has never seen this player on a server, so it has nothing to ban.")
                puid = portal.store.one("SELECT puid FROM sightings WHERE pid=? AND puid<>'' ORDER BY last_seen DESC LIMIT 1", (pid,))
                b = {"pid": pid, "guid": last["guid"], "ip": last["ip"], "puid": puid["puid"] if puid else "", "name": last["name"]}
            if not d.get("ip_ban", True):
                b["ip"] = ""
            b.update({"reason": reason, "expires": now() + minutes * 60 if minutes else 0})
            bid = portal.store.x("INSERT INTO bans(pid,guid,ip,puid,name,reason,created,expires,by_id,by_name) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                 (b["pid"], b["guid"], b["ip"], b["puid"], b["name"], reason, now(), b["expires"],
                                  who["discord_id"], who["name"]))
            results = {}
            for key in portal.order:
                server = portal.servers[key]
                try:
                    out = portal._apply_ban(server, b, slot if server is srv else None)
                    results[key] = plain(" ".join(out)).strip()[:200] or "ok"
                except RconError as e:
                    results[key] = "offline, applied at the next sync: %s" % e
            portal.store.audit(who, "ban", server=srv.key if srv else "", target=b["name"], pid=b["pid"],
                               detail="%s, %s" % (engine_length(minutes) or "permanent", reason), result=json.dumps(results))
            self.json({"ok": True, "id": bid, "servers": results})

        def unban(self, s: dict | None, d: dict) -> None:
            who = self.need(s, "ban.remove")
            b = portal.store.one("SELECT * FROM bans WHERE id=? AND active=1", (int(d.get("id") or 0),))
            if not b:
                raise ApiError(404, "No active ban with that number.")
            reason = safe_arg(d.get("reason", ""), 200)
            res = portal._lift_everywhere(b)
            portal.store.x("UPDATE bans SET active=0, lifted=?, lifted_by=?, lift_reason=? WHERE id=?",
                           (now(), who["name"], reason, b["id"]))
            portal.store.audit(who, "unban", target=b["name"], pid=b["pid"], detail=reason or "#%d" % b["id"], result=json.dumps(res))
            self.json({"ok": True, "servers": res})

        def server_action(self, s: dict | None, d: dict) -> None:
            act = d.get("action")
            perm = {"say": "server.say", "chat": "chat.reply", "map": "server.map", "nextmap": "server.map",
                    "restart": "server.restart", "rotation": "server.map"}.get(act)
            if not perm:
                raise ApiError(400, "Unknown action.")
            who = self.need(s, perm)
            if portal.limited("srv:" + who["discord_id"], 30, 60):
                raise ApiError(429, "Slow down a little.")
            keys = portal.order if d.get("server") == "*" and act in ("say", "chat") else [portal.server(d.get("server")).key]
            text = safe_arg(d.get("text", ""), 200)
            results = {}
            for key in keys:
                srv = portal.servers[key]
                if act in ("say", "chat"):
                    if not text:
                        raise ApiError(400, "Write a message.")
                    staff_name = safe_arg(who["name"], 24) or "Staff"
                    if srv.has("staffsay"):
                        cmd = "staffsay %s %s" % (staff_name.replace(" ", "_"), text)
                    else:
                        cmd = "say ^8[STAFF] %s^7: %s" % (staff_name, text)
                    try:
                        results[key] = srv.run(cmd)
                    except RconError as e:
                        results[key] = "offline: %s" % e
                        continue
                    # rcon output never reaches the server log, so the portal records staff lines itself
                    portal.store.x("INSERT INTO chat(server,at,slot,team,pid,name,text,kind) VALUES(?,?,?,?,?,?,?,?)",
                                   (srv.key, now(), -1, None, "", staff_name, text, "staff"))
                elif act == "map":
                    m = str(d.get("map", ""))
                    if not MAP_NAME.match(m):
                        raise ApiError(400, "Pick a map.")
                    results[key] = srv.run("map %s" % m, timeout=4)
                    text = m
                elif act == "nextmap":
                    m = str(d.get("map", "") or "")
                    if m and not MAP_NAME.match(m):
                        raise ApiError(400, "Pick a map.")
                    results[key] = srv.run(("nextmap %s" % m).strip(), timeout=4)
                    text = m or "next in rotation"
                elif act == "restart":
                    results[key] = srv.run("map_restart 0", timeout=4)
                    text = "match restart"
                elif act == "rotation":
                    maps = [x for x in str(d.get("maps", "")).split() if MAP_NAME.match(x)]
                    if not maps:
                        raise ApiError(400, "List at least one map.")
                    results[key] = srv.run("maprotation %s" % " ".join(maps[:20]), timeout=3)
                    text = " ".join(maps[:20])
            portal.store.audit(who, "server " + act, server=",".join(keys), detail=text, result=json.dumps(
                {k: plain(v).strip()[:200] for k, v in results.items()}))
            self.json({"ok": True, "servers": {k: plain(v).strip()[:300] for k, v in results.items()}})

        def staff_change(self, s: dict | None, d: dict) -> None:
            who = self.need(s, "staff.manage")
            did = str(d.get("discord_id", "")).strip()
            role = d.get("role")
            if not re.fullmatch(r"\d{15,21}", did):
                raise ApiError(400, "Use the Discord user id (Developer Mode, right-click the user, Copy User ID).")
            if role not in ("moderator", "admin", "revoked", "discord"):
                raise ApiError(400, "Unknown role.")
            if did in {str(x) for x in cfg.get("owners", [])}:
                raise ApiError(403, "Owners are set in the portal configuration.")
            if role == "admin" and who["role"] != "owner":
                raise ApiError(403, "Only the owner can make admins.")
            current = portal.store.one("SELECT role FROM staff WHERE discord_id=?", (did,))
            if current and current["role"] == "admin" and who["role"] != "owner":
                raise ApiError(403, "Only the owner can change an admin.")
            stored = None if role == "discord" else role
            portal.store.x("INSERT INTO staff(discord_id,name,role,note,added_by,created) VALUES(?,?,?,?,?,?) "
                           "ON CONFLICT(discord_id) DO UPDATE SET role=excluded.role, note=excluded.note, added_by=excluded.added_by",
                           (did, safe_arg(d.get("name", ""), 40), stored, safe_arg(d.get("note", ""), 120), who["name"], now()))
            if role == "revoked":
                portal.store.x("DELETE FROM sessions WHERE discord_id=?", (did,))
            else:
                portal.store.x("UPDATE sessions SET checked=0 WHERE discord_id=?", (did,))
            portal.store.audit(who, "staff " + role, target=did, detail=safe_arg(d.get("note", ""), 120))
            self.json({"ok": True})

        def restart(self, s: dict | None, d: dict) -> None:
            who = self.need(s, "health.restart")
            srv = portal.server(d.get("server"))
            unit = srv.cfg.get("unit")
            if not unit or not re.fullmatch(r"[A-Za-z0-9@_.-]+\.service|[A-Za-z0-9@_.-]+", unit):
                raise ApiError(409, "This server has no service to restart.")
            humans = srv.view().get("humans", 0)
            if humans and not d.get("confirm_players"):
                raise ApiError(409, "%d players are on this server. Confirm to restart anyway." % humans)
            if portal.limited("restart:" + srv.key, 2, 600):
                raise ApiError(429, "This server was restarted twice in the last 10 minutes. Check the logs first.")
            steps = []
            for cmd in cfg.get("restart_prefix", []):
                steps.append(subprocess.run(cmd, capture_output=True, text=True, timeout=30))
            # allowed for this service's user by a polkit rule that names exactly these units (deploy/install.sh)
            p = subprocess.run(["systemctl", "restart", "--no-ask-password", unit], capture_output=True, text=True, timeout=90)
            for cmd in cfg.get("restart_suffix", []):
                steps.append(subprocess.run(cmd, capture_output=True, text=True, timeout=30))
            ok = p.returncode == 0
            portal.store.audit(who, "service restart", server=srv.key, target=unit, detail="%d players on" % humans,
                               ok=ok, result=(p.stderr or p.stdout).strip()[:300])
            portal.health_cache = (0, None)
            if not ok:
                raise ApiError(500, "The restart failed: %s" % (p.stderr or p.stdout).strip()[:200])
            self.json({"ok": True})

    return Handler


# ----------------------------------------------------------------------------- main

def load_config(path: str) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    keys = [s.get("key") for s in cfg.get("servers", [])]
    if len(keys) != len(set(keys)) or not all(keys):
        raise SystemExit("every server needs a unique key")
    return cfg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--listen", help="host:port (default from the config, 127.0.0.1:8097)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config(a.config)
    if cfg.get("dev_login") and str(cfg.get("public_url", "")).startswith("https://"):
        raise SystemExit("dev_login is for local tests only; remove it from a public portal's config")
    host, _, port = (a.listen or "%s:%s" % (cfg.get("host", "127.0.0.1"), cfg.get("port", 8097))).rpartition(":")
    portal = Portal(cfg)
    portal.start()
    httpd = ThreadingHTTPServer((host, int(port)), make_handler(portal))
    httpd.daemon_threads = True
    log.info("staff portal %s on http://%s:%s (%d servers)", VERSION, host, port, len(portal.servers))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        portal.stop.set()
    return 0


if __name__ == "__main__":
    sys.exit(main())
