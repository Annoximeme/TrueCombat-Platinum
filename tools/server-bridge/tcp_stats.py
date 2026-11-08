#!/usr/bin/env python3
"""TrueCombat: Platinum stats service: persistent player stats and ranks.

Game servers write one tcp-match/1 report per finished match (see README.md).
This module stores them in SQLite, keeps per-player totals, an XP rank and a
skill rating, and answers the website's JSON requests. It runs on its own or
inside tcp_bridge.py (--stats-db). Python 3.8+ standard library only, so it can
be hosted on any VPS, home server or container.

No player accounts: a player is identified by the game's cl_guid, which the
client derives from its own locally generated etkey file. Only a one-way hash
of it (the 16-character player id) is stored or published.

Servers are trusted per key. An operator registers each ranked server once:

  python tcp_stats.py --db stats.db add-server "Red Server"     -> server id + secret key

and the server's upload agent (tcp_stats_agent.py) signs every report with that
key (HMAC-SHA256). Reports from unknown or removed servers are refused.

  python tcp_stats.py --db stats.db serve --listen 127.0.0.1:8091
  python tcp_stats.py --db stats.db import --server local ./matches   (trusted folder import)
  python tcp_stats.py --db stats.db recompute                          (rebuild ranks after a rule change)
"""
import argparse
import datetime as dt
import hashlib
import hmac
import json
import math
import pathlib
import re
import secrets
import sqlite3
import threading
import time

COLOR = re.compile(r"\^[0-9A-Za-z]")
SCHEMA_VERSION = 1
MAX_BODY = 256 * 1024
CLOCK_SKEW = 300            # seconds a signed upload may be off
RATING_START = 1000.0
UPLOADS_PER_HOUR = 120      # per server

# XP ranks. Thresholds grow so the top ranks take real time to reach.
RANKS = [
    ("Recruit", "RCT"), ("Private", "PVT"), ("Private First Class", "PFC"), ("Specialist", "SPC"),
    ("Corporal", "CPL"), ("Sergeant", "SGT"), ("Staff Sergeant", "SSG"), ("Sergeant First Class", "SFC"),
    ("Master Sergeant", "MSG"), ("First Sergeant", "1SG"), ("Sergeant Major", "SGM"),
    ("Second Lieutenant", "2LT"), ("First Lieutenant", "1LT"), ("Captain", "CPT"), ("Major", "MAJ"),
    ("Lieutenant Colonel", "LTC"), ("Colonel", "COL"), ("Brigadier General", "BG"), ("Major General", "MG"),
    ("Lieutenant General", "LTG"), ("General", "GEN"),
]
RANK_XP = [0] + [250 * i * (i + 1) for i in range(1, len(RANKS))]   # 500, 1500, 3000 ... 105000


def clean(text, limit=36):
    text = COLOR.sub("", str(text or ""))
    text = "".join(ch for ch in text if ch.isprintable())
    return text.strip()[:limit]


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(text):
    return dt.datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def player_id(raw):
    """Public player id: never publish guids. Same hash as the first bridge version."""
    return hashlib.sha256(("tcp-lb:" + str(raw)).encode()).hexdigest()[:16]


def rank_for(xp):
    level = 0
    for i, need in enumerate(RANK_XP):
        if xp >= need:
            level = i
    title, short = RANKS[level]
    nxt = RANK_XP[level + 1] if level + 1 < len(RANK_XP) else None
    return {"level": level + 1, "title": title, "short": short, "xp": int(xp),
            "xpThis": RANK_XP[level], "xpNext": nxt}


def match_xp(p, duration):
    minutes = min(p["timePlayed"], duration) / 60.0
    xp = (p["kills"] * 10 + p["headshots"] * 5 + p["roundsWon"] * 20 + p["objectives"] * 30
          + (100 if p["won"] else 25) + minutes * 2 - p["teamKills"] * 25)
    return max(0, int(round(xp)))


def _int(v, lo=0, hi=1 << 30):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


class Rejected(Exception):
    pass


def sanitize(report, trusted=False, allow_cheats=False):
    """Validates a tcp-match/1 report. Returns a normalized copy with player ids
    in place of guids, or raises Rejected."""
    if not isinstance(report, dict) or report.get("schema") != "tcp-match/1":
        raise Rejected("not a tcp-match/1 report")
    if report.get("practice"):
        raise Rejected("practice match")
    if report.get("cheats") and not allow_cheats:
        raise Rejected("cheats were enabled")
    try:
        ended = parse_time(report["ended"])
    except (KeyError, ValueError, TypeError):
        raise Rejected("bad end time")
    try:
        started = parse_time(report.get("started") or report["ended"])
    except (ValueError, TypeError):
        started = ended
    if ended > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10):
        raise Rejected("end time is in the future")
    duration = _int(report.get("duration", (ended - started).total_seconds()), 0, 86400)
    if not trusted and not 60 <= duration <= 6 * 3600:
        raise Rejected("match length out of range")
    players = report.get("players")
    if not isinstance(players, list) or not 1 <= len(players) <= 64:
        raise Rejected("bad player list")
    cap = max(duration, 60)
    out, seen = [], set()
    for p in players:
        if not isinstance(p, dict):
            raise Rejected("bad player")
        guid = str(p.get("guid") or p.get("id") or "")
        if not trusted and not re.fullmatch(r"[0-9A-Fa-f]{32}", guid):
            raise Rejected("bad player guid")
        if not guid:
            guid = "name:" + clean(p.get("name"))
        pid = player_id(guid.upper() if re.fullmatch(r"[0-9A-Fa-f]{32}", guid) else guid)
        if pid in seen:
            continue
        seen.add(pid)
        q = {"id": pid, "name": clean(p.get("name")) or "Player",
             "team": clean(p.get("team"), 16).lower(),
             "kills": _int(p.get("kills"), 0, cap * 4), "deaths": _int(p.get("deaths"), 0, cap * 4),
             "teamKills": _int(p.get("teamKills"), 0, cap), "suicides": _int(p.get("suicides"), 0, cap),
             "headshots": _int(p.get("headshots"), 0, cap * 4), "damage": _int(p.get("damage"), 0, cap * 2000),
             "roundsWon": _int(p.get("roundsWon"), 0, 1000), "objectives": _int(p.get("objectives"), 0, 1000),
             "won": bool(p.get("won")),
             "timePlayed": _int(p.get("timePlayed", duration), 0, cap + 120), "weapons": {}}
        q["headshots"] = min(q["headshots"], q["kills"])
        for w, ws in list((p.get("weapons") or {}).items())[:32]:
            if not isinstance(ws, dict):
                continue
            name = clean(w, 24)
            if not name:
                continue
            q["weapons"][name] = {k: _int(ws.get(k), 0, 1 << 24) for k in ("kills", "headshots", "shots", "hits")}
        out.append(q)
    winner = report.get("winner")
    return {"schema": "tcp-match/1", "id": clean(report.get("id") or "", 40),
            "server": clean(report.get("server"), 64), "map": clean(report.get("map"), 40),
            "mode": clean(report.get("mode"), 32), "version": clean(report.get("version"), 48),
            "started": started.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "ended": ended.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "duration": duration, "rounds": _int(report.get("rounds"), 0, 1000),
            "winner": clean(winner, 16).lower() if winner else None,
            "team": bool(winner) or any(p["team"] for p in out),
            "players": out}


def rate(match, ratings, counts):
    """Elo-style update. Team modes: each team's mean rating against the other.
    Free-for-all: every pair of players compared by score. Returns {pid: delta}."""
    dur = max(match["duration"], 1)
    ranked = [p for p in match["players"] if p["timePlayed"] >= min(60, dur * 0.3)]
    deltas = {}

    def k(pid):
        return 40.0 if counts.get(pid, 0) < 10 else 24.0

    if match["team"]:
        teams = {}
        for p in ranked:
            if p["team"]:
                teams.setdefault(p["team"], []).append(p)
        if len(teams) != 2:
            return deltas
        (ta, pa), (tb, pb) = teams.items()
        ra = sum(ratings.get(p["id"], RATING_START) for p in pa) / len(pa)
        rb = sum(ratings.get(p["id"], RATING_START) for p in pb) / len(pb)
        ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
        sa = 0.5 if not match["winner"] else (1.0 if match["winner"] == ta else 0.0)
        for team, ps, e, s in ((ta, pa, ea, sa), (tb, pb, 1 - ea, 1 - sa)):
            for p in ps:
                share = min(1.0, p["timePlayed"] / dur)
                deltas[p["id"]] = k(p["id"]) * share * (s - e)
        return deltas
    if len(ranked) < 2:
        return deltas
    score = {p["id"]: p["roundsWon"] * 3 + p["kills"] - p["suicides"] for p in ranked}
    n = len(ranked)
    for p in ranked:
        rp, total = ratings.get(p["id"], RATING_START), 0.0
        for o in ranked:
            if o is p:
                continue
            ro = ratings.get(o["id"], RATING_START)
            e = 1.0 / (1.0 + 10 ** ((ro - rp) / 400.0))
            s = 1.0 if score[p["id"]] > score[o["id"]] else 0.0 if score[p["id"]] < score[o["id"]] else 0.5
            total += s - e
        deltas[p["id"]] = k(p["id"]) * total / (n - 1)
    return deltas


DDL = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS servers(id TEXT PRIMARY KEY, name TEXT, key TEXT, active INTEGER DEFAULT 1,
  created TEXT, last_seen TEXT, uploads INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS matches(server TEXT, id TEXT, ended TEXT, map TEXT, mode TEXT, duration INTEGER,
  rounds INTEGER, winner TEXT, players INTEGER, received TEXT, report TEXT, PRIMARY KEY(server, id));
CREATE INDEX IF NOT EXISTS matches_ended ON matches(ended);
CREATE TABLE IF NOT EXISTS match_players(server TEXT, match TEXT, pid TEXT, ended TEXT, name TEXT, team TEXT,
  kills INTEGER, deaths INTEGER, team_kills INTEGER, suicides INTEGER, headshots INTEGER, damage INTEGER,
  rounds_won INTEGER, objectives INTEGER, won INTEGER, time_played INTEGER, xp INTEGER,
  rating_before REAL, rating_after REAL, top_weapon TEXT, PRIMARY KEY(server, match, pid));
CREATE INDEX IF NOT EXISTS match_players_pid ON match_players(pid, ended);
CREATE INDEX IF NOT EXISTS match_players_ended ON match_players(ended);
CREATE TABLE IF NOT EXISTS players(pid TEXT PRIMARY KEY, name TEXT, first_seen TEXT, last_seen TEXT,
  matches INTEGER, kills INTEGER, deaths INTEGER, team_kills INTEGER, suicides INTEGER, headshots INTEGER,
  damage INTEGER, rounds_won INTEGER, wins INTEGER, objectives INTEGER, time_played INTEGER, xp INTEGER,
  rating REAL, rated INTEGER, peak_rating REAL);
CREATE TABLE IF NOT EXISTS player_weapons(pid TEXT, weapon TEXT, kills INTEGER, headshots INTEGER,
  shots INTEGER, hits INTEGER, PRIMARY KEY(pid, weapon));
"""


class StatsStore:
    def __init__(self, path=":memory:", allow_cheats=False, min_matches=3):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.allow_cheats = allow_cheats
        self.min_matches = min_matches
        self.rate_window = {}
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript(DDL)
            self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema', ?)", (str(SCHEMA_VERSION),))

    # ------------------------------------------------------------ servers
    def add_server(self, name):
        sid = secrets.token_hex(6)
        key = secrets.token_hex(32)
        with self.lock:
            self.db.execute("INSERT INTO servers(id, name, key, active, created) VALUES(?,?,?,1,?)",
                            (sid, clean(name, 64), key, now_iso()))
        return sid, key

    def ensure_server(self, sid, name=""):
        with self.lock:
            self.db.execute("INSERT OR IGNORE INTO servers(id, name, key, active, created) VALUES(?,?,'',1,?)",
                            (sid, clean(name or sid, 64), now_iso()))

    def set_server_active(self, sid, active):
        with self.lock:
            return self.db.execute("UPDATE servers SET active=? WHERE id=?", (1 if active else 0, sid)).rowcount

    def servers(self):
        with self.lock:
            return [dict(r) for r in self.db.execute(
                "SELECT id, name, active, created, last_seen, uploads FROM servers ORDER BY created")]

    def verify(self, sid, stamp, signature, body):
        """HMAC check for an upload. Returns None when valid, else a reason."""
        with self.lock:
            row = self.db.execute("SELECT key, active FROM servers WHERE id=?", (sid or "",)).fetchone()
        if not row or not row["key"] or not row["active"]:
            return "unknown server"
        try:
            if abs(time.time() - int(stamp)) > CLOCK_SKEW:
                return "clock skew"
        except (TypeError, ValueError):
            return "bad timestamp"
        want = hmac.new(bytes.fromhex(row["key"]), str(stamp).encode() + b"\n" + body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, str(signature or "").lower()):
            return "bad signature"
        window = [t for t in self.rate_window.get(sid, []) if t > time.time() - 3600]
        if len(window) >= UPLOADS_PER_HOUR:
            return "rate limited"
        window.append(time.time())
        self.rate_window[sid] = window
        return None

    # ------------------------------------------------------------ ingest
    def ingest(self, report, server, trusted=False):
        """Stores one report. Returns (status, info): status is 'stored' or 'duplicate'."""
        m = sanitize(report, trusted=trusted, allow_cheats=self.allow_cheats)
        if not m["id"]:
            m["id"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()[:16]
        with self.lock:
            if self.db.execute("SELECT 1 FROM matches WHERE server=? AND id=?", (server, m["id"])).fetchone():
                return "duplicate", {"id": m["id"]}
            self.db.execute("BEGIN")
            try:
                self._apply(m, server)
                self.db.execute("UPDATE servers SET last_seen=?, uploads=uploads+1 WHERE id=?", (now_iso(), server))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return "stored", {"id": m["id"], "players": len(m["players"])}

    def _apply(self, m, server, received=None):
        db = self.db
        pids = [p["id"] for p in m["players"]]
        rows = {r["pid"]: r for r in db.execute(
            "SELECT pid, rating, rated, last_seen FROM players WHERE pid IN (%s)" % ",".join("?" * len(pids)), pids)}
        ratings = {pid: r["rating"] for pid, r in rows.items()}
        counts = {pid: r["rated"] for pid, r in rows.items()}
        deltas = rate(m, ratings, counts)
        db.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (server, m["id"], m["ended"], m["map"], m["mode"], m["duration"], m["rounds"], m["winner"],
                    len(m["players"]), received or now_iso(), json.dumps(m, separators=(",", ":"))))
        for p in m["players"]:
            pid = p["id"]
            xp = match_xp(p, m["duration"])
            before = ratings.get(pid, RATING_START)
            after = before + deltas.get(pid, 0.0)
            top = max(p["weapons"].items(), key=lambda kv: kv[1]["kills"])[0] if p["weapons"] else ""
            if top and not p["weapons"][top]["kills"]:
                top = ""
            db.execute("INSERT INTO match_players VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (server, m["id"], pid, m["ended"], p["name"], p["team"], p["kills"], p["deaths"],
                        p["teamKills"], p["suicides"], p["headshots"], p["damage"], p["roundsWon"], p["objectives"],
                        int(p["won"]), p["timePlayed"], xp, before, after, top))
            r = rows.get(pid)
            if r is None:
                db.execute("INSERT INTO players VALUES(?,?,?,?,0,0,0,0,0,0,0,0,0,0,0,0,?,0,?)",
                           (pid, p["name"], m["ended"], m["ended"], RATING_START, RATING_START))
            newer = r is None or m["ended"] >= (r["last_seen"] or "")
            db.execute("""UPDATE players SET name=CASE WHEN ? THEN ? ELSE name END,
                last_seen=MAX(last_seen, ?), first_seen=MIN(first_seen, ?), matches=matches+1, kills=kills+?, deaths=deaths+?,
                team_kills=team_kills+?, suicides=suicides+?, headshots=headshots+?, damage=damage+?,
                rounds_won=rounds_won+?, wins=wins+?, objectives=objectives+?, time_played=time_played+?, xp=xp+?,
                rating=?, rated=rated+?, peak_rating=MAX(peak_rating, ?) WHERE pid=?""",
                       (int(newer), p["name"], m["ended"], m["ended"], p["kills"], p["deaths"], p["teamKills"],
                        p["suicides"], p["headshots"], p["damage"], p["roundsWon"], int(p["won"]), p["objectives"],
                        p["timePlayed"], xp, after, int(pid in deltas), after, pid))
            for w, ws in p["weapons"].items():
                db.execute("""INSERT INTO player_weapons VALUES(?,?,?,?,?,?) ON CONFLICT(pid, weapon) DO UPDATE SET
                    kills=kills+excluded.kills, headshots=headshots+excluded.headshots,
                    shots=shots+excluded.shots, hits=hits+excluded.hits""",
                           (pid, w, ws["kills"], ws["headshots"], ws["shots"], ws["hits"]))

    def recompute(self):
        """Rebuilds every total, XP and rating from the stored reports, oldest first."""
        with self.lock:
            stored = [(r["server"], r["received"], json.loads(r["report"])) for r in
                      self.db.execute("SELECT server, received, report FROM matches ORDER BY ended, received")]
            self.db.execute("BEGIN")
            try:
                for t in ("matches", "match_players", "players", "player_weapons"):
                    self.db.execute("DELETE FROM " + t)
                for server, received, m in stored:
                    self._apply(m, server, received)
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return len(stored)

    def import_dir(self, folder, server="local"):
        """Trusted import of report files from a local folder (same machine as the game server)."""
        self.ensure_server(server, "Local reports")
        stored = 0
        for path in sorted(pathlib.Path(folder).glob("*.json")):
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(report, dict) and not report.get("id"):
                report["id"] = path.stem[:40]
            try:
                if self.ingest(report, server, trusted=True)[0] == "stored":
                    stored += 1
            except Rejected:
                pass
        return stored

    # ------------------------------------------------------------ queries
    def _player_json(self, r, extra=True):
        kills, deaths = r["kills"] or 0, r["deaths"] or 0
        out = {"id": r["pid"], "name": r["name"], "matches": r["matches"], "kills": kills, "deaths": deaths,
               "kd": round(kills / deaths, 2) if deaths else float(kills),
               "headshots": r["headshots"], "wins": r["wins"], "roundsWon": r["rounds_won"],
               "objectives": r["objectives"], "timePlayed": r["time_played"],
               "rating": int(round(r["rating"])), "rank": rank_for(r["xp"] or 0)}
        if extra:
            out["topWeapon"] = r["top_weapon"] or ""
        return out

    def leaderboard(self, period="all", sort="rating", mode="", limit=100):
        sort = sort if sort in ("rating", "xp", "kills", "kd", "headshots", "wins") else "rating"
        limit = max(1, min(500, _int(limit, 1, 500)))
        args, where = [], []
        if period == "30d":
            where.append("mp.ended >= ?")
            args.append((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat().replace("+00:00", "Z"))
        if mode:
            where.append("m.mode = ?")
            args.append(clean(mode, 32))
        cond = ("WHERE " + " AND ".join(where)) if where else ""
        with self.lock:
            nmatches = self.db.execute("SELECT COUNT(DISTINCT m.server || '/' || m.id) FROM match_players mp JOIN matches m "
                                       "ON m.server=mp.server AND m.id=mp.match " + cond, args).fetchone()[0]
            rows = self.db.execute(
                """SELECT mp.pid, p.name, COUNT(*) matches, SUM(mp.kills) kills, SUM(mp.deaths) deaths,
                   SUM(mp.headshots) headshots, SUM(mp.won) wins, SUM(mp.rounds_won) rounds_won,
                   SUM(mp.objectives) objectives, SUM(mp.time_played) time_played, p.xp xp, p.rating rating,
                   SUM(mp.xp) period_xp,
                   (SELECT weapon FROM player_weapons w WHERE w.pid=mp.pid AND w.kills>0 ORDER BY w.kills DESC LIMIT 1) top_weapon
                   FROM match_players mp JOIN matches m ON m.server=mp.server AND m.id=mp.match
                   JOIN players p ON p.pid=mp.pid """ + cond + " GROUP BY mp.pid HAVING COUNT(*) >= ?",
                args + [self.min_matches]).fetchall()
        players = [self._player_json(r) for r in rows]
        for p, r in zip(players, rows):
            p["periodXp"] = r["period_xp"] or 0
        key = {"rating": lambda p: (p["rating"], p["kills"]), "xp": lambda p: (p["rank"]["xp"], p["kills"]),
               "kills": lambda p: (p["kills"], p["kd"]), "kd": lambda p: (p["kd"], p["kills"]),
               "headshots": lambda p: (p["headshots"], p["kills"]), "wins": lambda p: (p["wins"], p["kills"])}[sort]
        players.sort(key=key, reverse=True)
        for i, p in enumerate(players):
            p["position"] = i + 1
        return {"schema": "tcp-leaderboard/1", "updated": now_iso(), "period": period if period == "30d" else "all",
                "sort": sort, "mode": mode, "minMatches": self.min_matches, "matches": nmatches,
                "players": players[:limit]}

    def player(self, pid):
        pid = str(pid or "").lower()
        if not re.fullmatch(r"[0-9a-f]{16}", pid):
            return None
        with self.lock:
            r = self.db.execute("SELECT * FROM players WHERE pid=?", (pid,)).fetchone()
            if not r:
                return None
            weapons = [dict(w) for w in self.db.execute(
                "SELECT weapon, kills, headshots, shots, hits FROM player_weapons WHERE pid=? ORDER BY kills DESC, shots DESC",
                (pid,))]
            recent = [dict(x) for x in self.db.execute(
                """SELECT m.ended, m.map, m.mode, m.duration, mp.team, mp.won, mp.kills, mp.deaths, mp.headshots,
                   mp.xp, mp.rating_before, mp.rating_after FROM match_players mp JOIN matches m
                   ON m.server=mp.server AND m.id=mp.match WHERE mp.pid=? ORDER BY mp.ended DESC LIMIT 20""", (pid,))]
            better = self.db.execute("SELECT COUNT(*) FROM players WHERE matches>=? AND rating>?",
                                     (self.min_matches, r["rating"])).fetchone()[0]
        out = self._player_json(r, extra=False)
        out.update({"schema": "tcp-player/1", "updated": now_iso(), "firstSeen": r["first_seen"], "lastSeen": r["last_seen"],
                    "teamKills": r["team_kills"], "suicides": r["suicides"], "damage": r["damage"],
                    "peakRating": int(round(r["peak_rating"])), "ranked": r["matches"] >= self.min_matches,
                    "position": better + 1 if r["matches"] >= self.min_matches else None,
                    "weapons": [{"name": w["weapon"], "kills": w["kills"], "headshots": w["headshots"],
                                 "shots": w["shots"], "hits": w["hits"],
                                 "accuracy": round(w["hits"] / w["shots"], 3) if w["shots"] else None} for w in weapons],
                    "recent": [{"ended": x["ended"], "map": x["map"], "mode": x["mode"], "duration": x["duration"],
                                "team": x["team"], "won": bool(x["won"]), "kills": x["kills"], "deaths": x["deaths"],
                                "headshots": x["headshots"], "xp": x["xp"],
                                "ratingChange": int(round(x["rating_after"] - x["rating_before"]))} for x in recent]})
        out["topWeapon"] = weapons[0]["weapon"] if weapons and weapons[0]["kills"] else ""
        return out

    def search(self, q, limit=20):
        q = clean(q, 36)
        if len(q) < 2:
            return {"schema": "tcp-search/1", "query": q, "players": []}
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        with self.lock:
            rows = self.db.execute("""SELECT *, '' top_weapon FROM players WHERE name LIKE ? ESCAPE '\\'
                                      ORDER BY matches DESC LIMIT ?""", (like, limit)).fetchall()
        return {"schema": "tcp-search/1", "query": q, "players": [self._player_json(r) for r in rows]}

    def recent(self, limit=20):
        with self.lock:
            rows = self.db.execute("SELECT m.server sid, m.id mid, m.ended, m.map, m.mode, m.duration, m.rounds, m.winner, "
                                   "m.players, s.name server FROM matches m LEFT JOIN servers s ON s.id=m.server "
                                   "ORDER BY m.ended DESC LIMIT ?", (max(1, min(100, limit)),)).fetchall()
            matches = []
            for r in rows:
                m = {k: r[k] for k in ("ended", "map", "mode", "duration", "rounds", "winner", "players", "server")}
                # the match MVP: most kills, then most XP
                top = self.db.execute("SELECT pid, name, kills FROM match_players WHERE server=? AND match=? "
                                      "ORDER BY kills DESC, xp DESC LIMIT 1", (r["sid"], r["mid"])).fetchone()
                m["mvp"] = {"id": top["pid"], "name": top["name"], "kills": top["kills"]} if top and top["kills"] else None
                matches.append(m)
        return {"schema": "tcp-recent/1", "updated": now_iso(), "matches": matches}

    @staticmethod
    def ranks():
        return {"schema": "tcp-ranks/1", "ranks": [{"level": i + 1, "title": t, "short": s, "xp": RANK_XP[i]}
                                                  for i, (t, s) in enumerate(RANKS)],
                "xp": "10 per kill, 5 per headshot kill, 20 per round won, 30 per objective, 100 for a match win "
                      "(25 otherwise), 2 per minute played, minus 25 per team kill"}


# ------------------------------------------------------------------ HTTP
def handle_get(store, path, query):
    """Returns (code, json) for GET routes, or None when the path is not a stats route."""
    q = {k: v[0] for k, v in query.items()}
    if path == "/leaderboard.json":
        return 200, store.leaderboard(q.get("period", "all"), q.get("sort", "rating"), q.get("mode", ""), q.get("limit", 100))
    if path == "/player.json":
        p = store.player(q.get("id"))
        return (200, p) if p else (404, {"error": "unknown player"})
    if path == "/search.json":
        return 200, store.search(q.get("q", ""))
    if path == "/recent.json":
        return 200, store.recent()
    if path == "/ranks.json":
        return 200, store.ranks()
    return None


def handle_post(store, path, headers, body):
    if path != "/api/v1/match":
        return None
    if len(body) > MAX_BODY:
        return 413, {"error": "report too large"}
    sid = headers.get("X-TCP-Server", "")
    why = store.verify(sid, headers.get("X-TCP-Time"), headers.get("X-TCP-Signature"), body)
    if why:
        return (429 if why == "rate limited" else 401), {"error": why}
    try:
        report = json.loads(body.decode("utf-8"))
        status, info = store.ingest(report, sid)
    except (ValueError, UnicodeDecodeError):
        return 400, {"error": "not JSON"}
    except Rejected as exc:
        return 422, {"error": str(exc)}
    return (200 if status == "stored" else 409), dict(info, status=status)


def sign(key_hex, body, stamp=None):
    stamp = str(int(stamp if stamp is not None else time.time()))
    return stamp, hmac.new(bytes.fromhex(key_hex), stamp.encode() + b"\n" + body, hashlib.sha256).hexdigest()


def serve(store, listen, cors):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse

    class Handler(BaseHTTPRequestHandler):
        server_version = "tcp-stats/1"

        def log_message(self, fmt, *a):
            pass

        def reply(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=30" if self.command == "GET" else "no-store")
            allowed = [o.strip() for o in cors.split(",")]
            origin = self.headers.get("Origin", "")
            if "*" in allowed:
                self.send_header("Access-Control-Allow-Origin", "*")
            elif origin in allowed:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/health":
                return self.reply(200, {"ok": True})
            r = handle_get(store, u.path, parse_qs(u.query))
            self.reply(*(r or (404, {"error": "not found"})))

        def do_POST(self):
            n = _int(self.headers.get("Content-Length"), 0, MAX_BODY + 1)
            body = self.rfile.read(n)
            r = handle_post(store, urlparse(self.path).path, self.headers, body)
            self.reply(*(r or (404, {"error": "not found"})))

    host, _, port = listen.rpartition(":")
    print("tcp-stats on http://%s:%s" % (host, port), flush=True)
    ThreadingHTTPServer((host, int(port)), Handler).serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="stats.db")
    ap.add_argument("--allow-cheats", action="store_true", help="accept matches played with sv_cheats 1 (testing)")
    ap.add_argument("--min-matches", type=int, default=3)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--listen", default="127.0.0.1:8091")
    s.add_argument("--cors", default="https://truecombat.eu,https://www.truecombat.eu")
    s.add_argument("--import-dir", default="", help="also import this folder every minute (trusted)")
    a = sub.add_parser("add-server")
    a.add_argument("name")
    sub.add_parser("list-servers")
    for name in ("disable-server", "enable-server"):
        sub.add_parser(name).add_argument("id")
    i = sub.add_parser("import")
    i.add_argument("--server", default="local")
    i.add_argument("folder")
    sub.add_parser("recompute")
    args = ap.parse_args(argv)
    store = StatsStore(args.db, allow_cheats=args.allow_cheats, min_matches=args.min_matches)
    if args.cmd == "add-server":
        sid, key = store.add_server(args.name)
        print(json.dumps({"server": sid, "key": key}, indent=2))
        print("Give the key to the server operator. It is not shown again.")
    elif args.cmd == "list-servers":
        print(json.dumps(store.servers(), indent=2))
    elif args.cmd in ("disable-server", "enable-server"):
        print("updated" if store.set_server_active(args.id, args.cmd == "enable-server") else "no such server")
    elif args.cmd == "import":
        print("stored", store.import_dir(args.folder, args.server))
    elif args.cmd == "recompute":
        print("recomputed", store.recompute(), "matches")
    elif args.cmd == "serve":
        if args.import_dir:
            def loop():
                while True:
                    try:
                        store.import_dir(args.import_dir)
                    except Exception as exc:
                        print("import failed:", exc, flush=True)
                    time.sleep(60)
            threading.Thread(target=loop, daemon=True).start()
        serve(store, args.listen, args.cors)


if __name__ == "__main__":
    main()
