#!/usr/bin/env python3
"""TrueCombat: Platinum stats service: persistent player stats and ranks.

Game servers write one tcp-match/1 report per finished match (see README.md).
This module stores them in SQLite, keeps per-player totals, an XP rank and a
skill rating, and answers the website's JSON requests. It runs on its own or
inside tcp_bridge.py (--stats-db). Python 3.8+ standard library only, so it can
be hosted on any VPS, home server or container.

A player is identified by the game's cl_guid (derived from the local etkey file) or, from game 0.37.0, by the
identity key the server checked (eacid.key; the report carries its key id). Only one-way hashes (the
16-character player ids) are stored or published. Optional player accounts (tools/accounts) tell this service
which ids belong to one player (POST /staff/accounts/aliases, loopback only); those ids are then merged into one.

Only real players count (tcp-match/2, game 0.35.0 and later): kills, deaths, hits, damage and
assists between two humans, from verified servers with Easy Anti-Cheat on for the whole match.
Ranked and unranked servers both feed the stats; only ranked matches move the skill rating.
See the integrity rules in README.md ("Detailed stats").

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
import os
import pathlib
import re
import secrets
import sqlite3
import threading
import time

# Any ET colour code: ^ and one printable character other than ^ (ColorIndex = (c - 48) & 31,
# so ^: ^< ^= ^> ^? ^@ are colours too, not only digits and letters).
COLOR = re.compile(r"\^[^\^\s]")
SCHEMA_VERSION = 1
MAX_BODY = 256 * 1024
CLOCK_SKEW = 300            # seconds a signed upload may be off
RATING_START = 1000.0
UPLOADS_PER_HOUR = 120      # per server
UNIT_M = 0.0254             # one map unit in metres
PAIR_KILL_CAP = 10          # counted kills on the same opponent per match
MIN_PRESENT = 120           # seconds a real player must be active for the match to count
TRADE_MS = 3000             # a kill this soon after the victim killed a teammate is a trade
MULTI_MS = 3000             # kills this close together form a multi-kill

# Every stat a match adds per player (stored in match_stats). "max" stats keep the best value,
# all others are summed. Ratios (K/D, accuracy, headshot rate...) are worked out from these.
STATS = {
    "kills": "sum", "deaths": "sum", "assists": "sum", "headshots": "sum", "damage": "sum", "damageTaken": "sum",
    "teamKills": "sum", "suicides": "sum", "hitsHead": "sum", "hitsBody": "sum", "hitsLegs": "sum",
    "shots": "sum", "hits": "sum",                       # bot-free matches only (accuracy)
    "objectives": "sum", "captures": "sum", "plants": "sum", "defuses": "sum", "returns": "sum",
    "roundsWon": "sum", "roundsPlayed": "sum", "roundMvps": "sum", "wins": "sum", "matches": "sum", "timePlayed": "sum",
    "longestKill": "max", "killDistance": "sum", "bestStreak": "max", "doubleKills": "sum", "tripleKills": "sum",
    "quadKills": "sum", "openingKills": "sum", "openingDeaths": "sum", "clutches": "sum", "bestClutch": "max",
    "trades": "sum", "revenges": "sum", "knifeKills": "sum", "grenadeKills": "sum", "aimedKills": "sum",
    "hipKills": "sum", "standKills": "sum", "crouchKills": "sum", "proneKills": "sum", "leanKills": "sum", "airKills": "sum",
    "xp": "sum",
}
# Ratios: name -> (numerator stat, denominator stat, scale)
DERIVED = {"kd": ("kills", "deaths", 1), "headshotRate": ("headshots", "kills", 100), "accuracy": ("hits", "shots", 100),
           "headHitRate": ("hitsHead", "hitsAll", 100), "adr": ("damage", "roundsPlayed", 1), "winRate": ("wins", "matches", 100),
           "kpm": ("kills", "minutes", 1), "avgKillDistance": ("killDistance", "kills", 1)}
KILL_FLAGS = {"head": 1, "aimed": 2, "crouch": 4, "prone": 8, "lean": 16, "air": 32}

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


def match_pub(server, mid):
    """The public id of a match: stable, and it gives away neither the server id nor the server's own match id."""
    return hashlib.sha256(("%s\n%s" % (server, mid)).encode("utf-8")).hexdigest()[:16]


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
    if not isinstance(report, dict) or report.get("schema") not in ("tcp-match/1", "tcp-match/2"):
        raise Rejected("not a tcp-match report")
    v2 = report.get("schema") == "tcp-match/2"
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
    out, seen, index = [], {}, []
    for p in players:
        if not isinstance(p, dict):
            raise Rejected("bad player")
        guid = str(p.get("guid") or p.get("id") or "")
        if not trusted and not re.fullmatch(r"[0-9A-Fa-f]{32}", guid):
            raise Rejected("bad player guid")
        if not guid:
            guid = "name:" + clean(p.get("name"))
        pid = player_id(guid.upper() if re.fullmatch(r"[0-9A-Fa-f]{32}", guid) else guid)
        # Game 0.37.0 and later: the server checked that the client holds its identity key (eacid.key) and reports
        # the key id. The key, not the guid, is then the player: a guid can be copied, a signature cannot.
        key = str(p.get("key") or "").lower() if v2 else ""
        guid_pid = ""
        if re.fullmatch(r"[0-9a-f]{40}", key):
            guid_pid, pid = pid, player_id("key:" + key)
        else:
            key = ""
        if pid in seen:
            index.append(seen[pid])
            continue
        seen[pid] = len(out)
        index.append(len(out))
        q = {"id": pid, "name": clean(p.get("name")) or "Player",
             "team": clean(p.get("team"), 16).lower(),
             "kills": _int(p.get("kills"), 0, cap * 4), "deaths": _int(p.get("deaths"), 0, cap * 4),
             "teamKills": _int(p.get("teamKills"), 0, cap), "suicides": _int(p.get("suicides"), 0, cap),
             "headshots": _int(p.get("headshots"), 0, cap * 4), "damage": _int(p.get("damage"), 0, cap * 2000),
             "roundsWon": _int(p.get("roundsWon"), 0, 1000), "objectives": _int(p.get("objectives"), 0, 1000),
             "won": bool(p.get("won")), "filler": p.get("filler") is True,
             "timePlayed": _int(p.get("timePlayed", duration), 0, cap + 120), "weapons": {},
             # Left before the end (the game sets connected=false); abandoning a losing match costs full rating
             "left": p.get("connected") is False, "leaves": _int(p.get("leaves"), 0, 100)}
        if key:
            q["key"], q["guidId"] = key, guid_pid
        net = p.get("net")
        if isinstance(net, dict):
            def f(v, hi):
                try:
                    return max(0.0, min(float(v), hi))
                except (TypeError, ValueError):
                    return 0.0
            q["net"] = {"ping": _int(net.get("ping"), 0, 999), "pingMax": _int(net.get("pingMax"), 0, 999),
                        "jitter": round(f(net.get("jitter"), 999), 1), "loss": round(f(net.get("loss"), 100), 2),
                        "rewind": _int(net.get("rewind"), 0, 1000), "rewindCapped": _int(net.get("rewindCapped"), 0, 1 << 24),
                        "shotsRewound": _int(net.get("shotsRewound"), 0, 1 << 24)}
        q["headshots"] = min(q["headshots"], q["kills"])
        for w, ws in list((p.get("weapons") or {}).items())[:32]:
            if not isinstance(ws, dict):
                continue
            name = clean(w, 24)
            if not name:
                continue
            q["weapons"][name] = {k: _int(ws.get(k), 0, 1 << 24) for k in ("kills", "headshots", "shots", "hits", "time", "longest")}
        if v2:
            hits = p.get("hits") if isinstance(p.get("hits"), dict) else {}
            q.update({"assists": 0, "idle": _int(p.get("idle"), 0, cap + 120),
                      "ip": str(p.get("ip") or "")[:16] if re.fullmatch(r"[0-9a-f]{1,16}", str(p.get("ip") or "")) else "",
                      "hitsHead": _int(hits.get("head"), 0, 1 << 24), "hitsBody": _int(hits.get("body"), 0, 1 << 24),
                      "hitsLegs": _int(hits.get("legs"), 0, 1 << 24), "damageTaken": _int(p.get("damageTaken"), 0, cap * 2000)})
        out.append(q)
    winner = report.get("winner")
    extra = {"ranked": True, "verified": False, "eac": None, "bots": 0, "kills": [], "events": []}
    if v2:
        eac = report.get("eac") if isinstance(report.get("eac"), dict) else {}
        extra.update({"ranked": report.get("ranked") is True,
                      "eac": {k: _int(eac.get(k), 0, 9) for k in ("start", "end", "min")},
                      "password": report.get("password") is True, "bots": _int(report.get("botSeconds"), 0, cap + 120),
                      "kills": _kill_events(report.get("kills"), index, cap), "events": _round_events(report.get("events"), index, cap)})
        extra["verified"] = min(extra["eac"].values()) >= 1 and not extra["password"]
    return dict(extra, **{"schema": "tcp-match/2" if v2 else "tcp-match/1", "id": clean(report.get("id") or "", 40),
            "server": clean(report.get("server"), 64), "map": clean(report.get("map"), 40),
            "mode": clean(report.get("mode"), 32), "version": clean(report.get("version"), 48),
            "started": started.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "ended": ended.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "duration": duration, "rounds": _int(report.get("rounds"), 0, 1000),
            "winner": clean(winner, 16).lower() if winner else None,
            "team": bool(winner) or any(p["team"] for p in out),
            "players": out})


def _kill_events(raw, index, cap):
    """[t, round, killer, victim, weapon, flags, distance, [assists]] with indices into "players"."""
    out = []
    n = len(index)
    for e in (raw if isinstance(raw, list) else [])[:4096]:
        if not isinstance(e, list) or len(e) < 7:
            continue
        k, v = _int(e[2], -1, n - 1), _int(e[3], -1, n - 1)
        if k < 0 or v < 0 or index[k] == index[v]:
            continue
        assists = [index[a] for a in (e[7] if len(e) > 7 and isinstance(e[7], list) else [])[:3]
                   if isinstance(a, int) and 0 <= a < n and index[a] not in (index[k], index[v])]
        out.append({"t": _int(e[0], 0, (cap + 120) * 1000), "round": _int(e[1], 0, 1000), "killer": index[k], "victim": index[v],
                    "weapon": clean(e[4], 24) or "Unknown", "flags": _int(e[5], 0, 255), "dist": _int(e[6], 0, 65536),
                    "assists": sorted(set(assists))})
    out.sort(key=lambda x: x["t"])
    return out


def _round_events(raw, index, cap):
    """["o", t, round, player, capture|plant|defuse|return] and ["r", t, round, winner, clutch, enemies, humans]."""
    out = []
    n = len(index)
    for e in (raw if isinstance(raw, list) else [])[:1024]:
        if not isinstance(e, list) or len(e) < 5:
            continue
        t, rnd = _int(e[1], 0, (cap + 120) * 1000), _int(e[2], 0, 1000)
        if e[0] == "o" and e[4] in ("capture", "plant", "defuse", "return"):
            who = _int(e[3], -1, n - 1)
            if who >= 0:
                out.append({"kind": "o", "t": t, "round": rnd, "player": index[who], "what": e[4]})
        elif e[0] == "r" and len(e) >= 7:
            c = _int(e[4], -1, n - 1)
            out.append({"kind": "r", "t": t, "round": rnd, "winner": clean(e[3], 16).lower() if isinstance(e[3], str) else None,
                        "clutch": index[c] if c >= 0 else None, "enemies": _int(e[5], 0, 64), "humans": _int(e[6], 0, 64)})
    out.sort(key=lambda x: x["t"])
    return out


def _original(m):
    """The report as stored: every player under the id it arrived with (accounts are applied again on a rebuild)."""
    out = dict(m)
    out["players"] = [dict(p, id=p.get("pid0", p["id"])) for p in m["players"]]
    return out


def integrity(m, min_present=MIN_PRESENT):
    """The rules a tcp-match/2 report must pass to count. Returns None or the reason it doesn't."""
    if not m["verified"]:
        if m["eac"] is None:
            return "no anti-cheat record"
        return "join password set" if m.get("password") else "anti-cheat was off during the match"
    present = [p for p in m["players"] if p["timePlayed"] >= min(min_present, max(60, m["duration"] * 0.5))]
    def people(ps):
        # two clients behind one address count as one person
        return len({p["ip"] or p["id"] for p in ps})
    if m["team"]:
        sides = {}
        for p in present:
            if p["team"]:
                sides.setdefault(p["team"], []).append(p)
        if len(sides) < 2 or any(people(ps) < 1 for ps in sides.values()) or people(present) < 2:
            return "needs real players on both teams"
    elif people(present) < 2:
        return "needs two real players"
    return None


def derive(m):
    """Per-player stats for one match (dict of STATS keys), per-weapon lines and kills per opponent.
    Same-address opponents never count against each other, and at most PAIR_KILL_CAP kills on one opponent count."""
    players = m["players"]
    team = [p["team"] for p in players]
    ip = [p.get("ip") or "" for p in players]
    st = [{k: 0 for k in STATS} for _ in players]
    vs = [dict() for _ in players]
    weapons = [dict() for _ in players]
    dur = max(m["duration"], 1)
    botfree = m["schema"] == "tcp-match/1" or not m["bots"]
    for i, p in enumerate(players):
        s = st[i]
        share = min(1.0, p["timePlayed"] / dur)
        s.update({"teamKills": p["teamKills"], "suicides": p["suicides"], "damage": p["damage"], "roundsWon": p["roundsWon"],
                  "objectives": p["objectives"], "wins": int(p["won"]), "matches": 1, "timePlayed": p["timePlayed"],
                  "roundsPlayed": max(1, int(round(m["rounds"] * share))) if m["rounds"] else 0,
                  "damageTaken": p.get("damageTaken", 0), "hitsHead": p.get("hitsHead", 0), "hitsBody": p.get("hitsBody", 0),
                  "hitsLegs": p.get("hitsLegs", 0)})
        for w, ws in p["weapons"].items():
            weapons[i][w] = {"kills": 0 if m["kills"] else ws["kills"], "headshots": 0 if m["kills"] else ws["headshots"],
                             "shots": ws["shots"] if botfree else 0, "hits": ws["hits"] if botfree else 0,
                             "time": ws.get("time", 0), "longest": 0}
            if botfree:
                s["shots"] += ws["shots"]
                s["hits"] += ws["hits"]
    if m["schema"] == "tcp-match/1":
        for i, p in enumerate(players):
            st[i].update({"kills": p["kills"], "deaths": p["deaths"], "headshots": p["headshots"]})
        return st, weapons, vs
    # --- kills, from the event log
    pair = {}
    streak = [0] * len(players)
    last_kill = [None] * len(players)      # (t, chain length)
    killed_by = [None] * len(players)      # who killed this player last (for revenge)
    recent_deaths = []                     # (t, victim, killer) for trades
    opened = set()
    round_kills = {}
    for e in m["kills"]:
        k, v = e["killer"], e["victim"]
        if ip[k] and ip[k] == ip[v]:
            continue
        if m["team"] and team[k] and team[k] == team[v]:
            continue
        pair[(k, v)] = pair.get((k, v), 0) + 1
        if pair[(k, v)] > PAIR_KILL_CAP:
            continue
        sk, sv, f = st[k], st[v], e["flags"]
        sk["kills"] += 1
        sv["deaths"] += 1
        vs[k][v] = vs[k].get(v, 0) + 1
        head = bool(f & KILL_FLAGS["head"])
        sk["headshots"] += head
        dist = e["dist"]
        sk["killDistance"] += int(round(dist * UNIT_M))
        sk["longestKill"] = max(sk["longestKill"], int(round(dist * UNIT_M)))
        w = weapons[k].setdefault(e["weapon"], {"kills": 0, "headshots": 0, "shots": 0, "hits": 0, "time": 0, "longest": 0})
        w["kills"] += 1
        w["headshots"] += head
        w["longest"] = max(w["longest"], int(round(dist * UNIT_M)))
        lw = e["weapon"].lower()
        sk["knifeKills"] += lw == "knife"
        sk["grenadeKills"] += "grenade" in lw
        sk["aimedKills" if f & KILL_FLAGS["aimed"] else "hipKills"] += 1
        sk["proneKills" if f & KILL_FLAGS["prone"] else "crouchKills" if f & KILL_FLAGS["crouch"] else "standKills"] += 1
        sk["leanKills"] += bool(f & KILL_FLAGS["lean"])
        sk["airKills"] += bool(f & KILL_FLAGS["air"])
        for a in e["assists"]:
            if not (ip[a] and ip[a] == ip[v]) and not (m["team"] and team[a] and team[a] == team[v]):
                st[a]["assists"] += 1
        # streaks and multi-kills
        streak[k] += 1
        streak[v] = 0
        sk["bestStreak"] = max(sk["bestStreak"], streak[k])
        lk = last_kill[k]
        chain = lk[1] + 1 if lk and e["t"] - lk[0] <= MULTI_MS else 1
        last_kill[k] = (e["t"], chain)
        if chain == 2:
            sk["doubleKills"] += 1
        elif chain == 3:
            sk["doubleKills"] -= 1
            sk["tripleKills"] += 1
        elif chain == 4:
            sk["tripleKills"] -= 1
            sk["quadKills"] += 1
        # opening kill of the round
        if e["round"] and e["round"] not in opened:
            opened.add(e["round"])
            sk["openingKills"] += 1
            sv["openingDeaths"] += 1
        # trade: the victim had just killed one of the killer's teammates
        if m["team"] and any(t0 >= e["t"] - TRADE_MS and kk == v and team[vv] == team[k] and vv != k
                             for t0, vv, kk in recent_deaths):
            sk["trades"] += 1
        recent_deaths = [x for x in recent_deaths if x[0] >= e["t"] - TRADE_MS] + [(e["t"], v, k)]
        if killed_by[k] == v:
            sk["revenges"] += 1
            killed_by[k] = None
        killed_by[v] = k
        rk = round_kills.setdefault(e["round"], {})
        rk[k] = rk.get(k, 0) + 1
    for rk in round_kills.values():
        top = max(rk.values())
        if top >= 2:
            for k, n in rk.items():
                if n == top:
                    st[k]["roundMvps"] += 1
                    break
    for e in m["events"]:
        if e["kind"] == "o":
            key = {"capture": "captures", "plant": "plants", "defuse": "defuses", "return": "returns"}[e["what"]]
            st[e["player"]][key] += 1
        elif e["kind"] == "r" and e["clutch"] is not None and e["humans"] >= 1:
            st[e["clutch"]]["clutches"] += 1
            st[e["clutch"]]["bestClutch"] = max(st[e["clutch"]]["bestClutch"], e["humans"])
    return st, weapons, vs


def suspicious(d, m):
    """Numbers no fair player reaches. They are kept, but listed for staff (tcp_stats.py review)."""
    out = []
    minutes = max(1.0, d["timePlayed"] / 60.0)
    if d["shots"] >= 50 and d["hits"] > 0.9 * d["shots"]:
        out.append("accuracy %d%% over %d shots" % (100 * d["hits"] // d["shots"], d["shots"]))
    if d["kills"] >= 20 and d["headshots"] > 0.85 * d["kills"]:
        out.append("headshot kills %d of %d" % (d["headshots"], d["kills"]))
    if d["kills"] >= 15 and d["kills"] / minutes > 4:
        out.append("%.1f kills per minute" % (d["kills"] / minutes))
    if d["longestKill"] > 400:
        out.append("kill at %d m" % d["longestKill"])
    return out


def ratios(t):
    """Adds K/D, accuracy, headshot rate and the other ratios to a dict of summed stats."""
    t = dict(t)
    t["hitsAll"] = t.get("hitsHead", 0) + t.get("hitsBody", 0) + t.get("hitsLegs", 0)
    t["minutes"] = t.get("timePlayed", 0) / 60.0
    for name, (num, den, scale) in DERIVED.items():
        a, b = t.get(num, 0), t.get(den, 0)
        if name == "kd":
            t[name] = round(a / b, 2) if b else float(a)
        else:
            t[name] = round(scale * a / b, 1) if b else None
    t.pop("minutes")
    return t


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
                if p.get("left") and s - e < 0:
                    share = 1.0      # quitting a match you are losing doesn't soften the loss
                d = k(p["id"]) * share * (s - e)
                if p.get("filler") and d < 0:
                    d = 0.0  # joined a short team to replace a leaver: no rating loss
                deltas[p["id"]] = d
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
CREATE TABLE IF NOT EXISTS match_stats(server TEXT, match TEXT, pid TEXT, ended TEXT, ranked INTEGER, stat TEXT, value INTEGER,
  PRIMARY KEY(server, match, pid, stat));
CREATE INDEX IF NOT EXISTS match_stats_stat ON match_stats(stat, ended);
CREATE INDEX IF NOT EXISTS match_stats_pid ON match_stats(pid, stat);
CREATE TABLE IF NOT EXISTS match_weapons(server TEXT, match TEXT, pid TEXT, ended TEXT, ranked INTEGER, weapon TEXT,
  kills INTEGER, headshots INTEGER, shots INTEGER, hits INTEGER, time INTEGER, longest INTEGER, PRIMARY KEY(server, match, pid, weapon));
CREATE INDEX IF NOT EXISTS match_weapons_pid ON match_weapons(pid);
CREATE TABLE IF NOT EXISTS match_vs(server TEXT, match TEXT, pid TEXT, opp TEXT, ended TEXT, ranked INTEGER, kills INTEGER,
  PRIMARY KEY(server, match, pid, opp));
CREATE INDEX IF NOT EXISTS match_vs_pid ON match_vs(pid);
CREATE INDEX IF NOT EXISTS match_vs_opp ON match_vs(opp);
CREATE TABLE IF NOT EXISTS review(server TEXT, match TEXT, pid TEXT, reason TEXT, created TEXT, PRIMARY KEY(server, match, pid, reason));
CREATE TABLE IF NOT EXISTS learned(old TEXT PRIMARY KEY, new TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS guid_keys(old TEXT NOT NULL, new TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY(old, new));
CREATE TABLE IF NOT EXISTS aliases(pid TEXT NOT NULL, canonical TEXT NOT NULL, since TEXT, until TEXT);
CREATE INDEX IF NOT EXISTS aliases_pid ON aliases(pid);
CREATE TABLE IF NOT EXISTS voided(kind TEXT, id TEXT, reason TEXT, created TEXT, PRIMARY KEY(kind, id));
"""


class StatsStore:
    def __init__(self, path=":memory:", allow_cheats=False, min_matches=3, require_anticheat=False):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.allow_cheats = allow_cheats
        self.min_matches = min_matches
        self.require_anticheat = require_anticheat   # refuse reports without Easy Anti-Cheat on (live service)
        self.rate_window = {}
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript(DDL)
            # accounts 1.0.2: a guid may be seen with several keys (guid_keys); the old one-key table moves over
            self.db.execute("INSERT OR IGNORE INTO guid_keys SELECT old, new, at FROM learned")
            self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema', ?)", (str(SCHEMA_VERSION),))
            # the public id of a match (match pages on the website); older databases get the column here
            if "pub" not in [c[1] for c in self.db.execute("PRAGMA table_info(matches)")]:
                self.db.execute("ALTER TABLE matches ADD COLUMN pub TEXT")
            for r in self.db.execute("SELECT server, id FROM matches WHERE pub IS NULL").fetchall():
                self.db.execute("UPDATE matches SET pub=? WHERE server=? AND id=?", (match_pub(r[0], r[1]), r[0], r[1]))
            self.db.execute("CREATE INDEX IF NOT EXISTS matches_pub ON matches(pub)")
            self._migrate()

    # ------------------------------------------------------------ servers
    def add_server(self, name):
        sid = secrets.token_hex(6)
        key = secrets.token_hex(32)
        with self.lock:
            self.db.execute("INSERT INTO servers(id, name, key, active, created) VALUES(?,?,?,1,?)",
                            (sid, clean(name, 64), key, now_iso()))
        return sid, key

    def _migrate(self):
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(players)")}
        if "abandons" not in cols:
            self.db.execute("ALTER TABLE players ADD COLUMN abandons INTEGER DEFAULT 0")
        mcols = {r["name"] for r in self.db.execute("PRAGMA table_info(matches)")}
        for col in ("ranked", "verified", "bots"):
            if col not in mcols:
                self.db.execute("ALTER TABLE matches ADD COLUMN %s INTEGER DEFAULT %d" % (col, 1 if col == "ranked" else 0))

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
        if m["schema"] == "tcp-match/2":
            why = integrity(m)
            if why and (self.require_anticheat or m["verified"]):
                raise Rejected(why)
        elif self.require_anticheat:
            raise Rejected("no anti-cheat record (update the server to 0.35.0)")
        if not m["id"]:
            m["id"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()[:16]
        with self.lock:
            if self.db.execute("SELECT 1 FROM matches WHERE server=? AND id=?", (server, m["id"])).fetchone():
                return "duplicate", {"id": m["id"]}
            self.db.execute("BEGIN")
            try:
                learned = self.learn_keys(m, server)
                self._apply(m, server)
                self.db.execute("UPDATE servers SET last_seen=?, uploads=uploads+1 WHERE id=?", (now_iso(), server))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            if learned:
                self.recompute()          # older guid matches now count for the key
        return "stored", {"id": m["id"], "players": len(m["players"])}

    def _resolve(self, m, server):
        """Player accounts: maps each player's own id to the id the stats are kept under. A guid id first seen
        with a verified key becomes that key (its history moves with it), and a key linked to an account becomes
        the account for the time it was linked. The report keeps the original id (pid0), so a rebuild can redo this."""
        db = self.db
        when = m["ended"]
        out = []
        for p in m["players"]:
            base = p.setdefault("pid0", p["id"])
            pid = base
            target, why = self._guid_target(pid)
            if target:
                pid = target
            elif why:
                db.execute("INSERT OR IGNORE INTO review VALUES(?,?,?,?,?)", (server, m["id"], pid, why, now_iso()))
            for a in db.execute("SELECT canonical, since, until FROM aliases WHERE pid=?", (pid,)):
                if (not a["since"] or when >= a["since"]) and (not a["until"] or when < a["until"]):
                    pid = a["canonical"]
                    break
            out.append(pid)
        # two ids of one player in the same match: every one of them keeps its own id for this match (the ids a
        # report arrives with are unique, so this never collides) and staff get a look
        for pid in {x for x in out if out.count(x) > 1}:
            db.execute("INSERT OR IGNORE INTO review VALUES(?,?,?,?,?)",
                       (server, m["id"], pid, "two ids of one account in the same match", now_iso()))
            out = [p["pid0"] if x == pid else x for p, x in zip(m["players"], out)]
        for p, pid in zip(m["players"], out):
            p["id"] = pid

    def _guid_target(self, gid):
        """The key a guid id's history belongs to, or (None, reason). A guid seen with one verified key belongs to
        that key. Seen with several keys, it belongs to them only when they are one player (all linked to the same
        account at some time): a copied guid with someone else's key moves nothing, and staff see it in the review queue."""
        keys = [r["new"] for r in self.db.execute("SELECT new FROM guid_keys WHERE old=? ORDER BY at, new", (gid,))]
        if not keys:
            return None, None
        if len(keys) == 1:
            return keys[0], None
        shared = None
        for k in keys:
            mine = {r["canonical"] for r in self.db.execute("SELECT canonical FROM aliases WHERE pid=?", (k,))}
            shared = mine if shared is None else shared & mine
        if shared:
            return keys[0], None
        return None, "guid seen with the keys of different players"

    def learn_keys(self, m, server):
        """A verified match that shows a guid together with a key: remember the pair. Returns True when the pair is
        new (the caller rebuilds, so the guid's older matches follow the key)."""
        if not m.get("verified"):
            return False
        new = False
        for p in m["players"]:
            if not p.get("key") or not p.get("guidId"):
                continue
            cur = self.db.execute("INSERT OR IGNORE INTO guid_keys VALUES(?,?,?)",
                                  (p["guidId"], p.get("pid0", p["id"]), m["ended"]))
            new = new or cur.rowcount > 0
        return new

    def set_aliases(self, aliases):
        """From the account service: [{pid, canonical, since, until}] (since/until: unix seconds or null).
        Replaces the table; rebuilds the stats when it changed. Returns the number of matches rebuilt, or None."""
        def iso(v):
            if v in (None, "", 0):
                return None
            return dt.datetime.fromtimestamp(int(v), dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        rows = []
        for a in aliases or []:
            pid, can = str(a.get("pid", "")), str(a.get("canonical", ""))
            if not (re.fullmatch(r"[0-9a-f]{16}", pid) and re.fullmatch(r"[0-9a-f]{16}", can)):
                raise ValueError("bad alias")
            rows.append((pid, can, iso(a.get("since")), iso(a.get("until"))))
        rows.sort(key=lambda r: tuple(x or "" for x in r))
        with self.lock:
            old = sorted((tuple(r) for r in self.db.execute("SELECT pid, canonical, since, until FROM aliases")),
                         key=lambda r: tuple(x or "" for x in r))
            if old == rows:
                return None
            self.db.execute("BEGIN")
            try:
                self.db.execute("DELETE FROM aliases")
                self.db.executemany("INSERT INTO aliases VALUES(?,?,?,?)", rows)
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            return self.recompute()

    def last_seen_of(self, aliases):
        """When each account last played (its canonical id's last match), so the account service can tell an active
        player from one who left; a name is released only after a year without either."""
        ids = sorted({str(a.get("canonical", "")) for a in aliases or [] if isinstance(a, dict)})[:5000]
        with self.lock:
            return {r["pid"]: r["last_seen"] for r in self.db.execute(
                "SELECT pid, last_seen FROM players WHERE pid IN (%s)" % ",".join("?" * len(ids)), ids)} if ids else {}

    def _apply(self, m, server, received=None):
        db = self.db
        self._resolve(m, server)
        pids = [p["id"] for p in m["players"]]
        rows = {r["pid"]: r for r in db.execute(
            "SELECT pid, rating, rated, last_seen FROM players WHERE pid IN (%s)" % ",".join("?" * len(pids)), pids)}
        ratings = {pid: r["rating"] for pid, r in rows.items()}
        counts = {pid: r["rated"] for pid, r in rows.items()}
        m.setdefault("ranked", True)
        m.setdefault("kills", [])
        m.setdefault("events", [])
        m.setdefault("bots", 0)
        detail, weapons, vs = derive(m)
        if m["schema"] == "tcp-match/2":
            # the counted kills (real opponents, farming rules applied) replace the game's totals
            for p, d in zip(m["players"], detail):
                p.update({"kills": d["kills"], "deaths": d["deaths"], "headshots": d["headshots"]})
        deltas = rate(m, ratings, counts) if m["ranked"] else {}
        ranked = int(bool(m["ranked"]))
        db.execute("INSERT INTO matches(server, id, ended, map, mode, duration, rounds, winner, players, received, report, pub, "
                   "ranked, verified, bots) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (server, m["id"], m["ended"], m["map"], m["mode"], m["duration"], m["rounds"], m["winner"],
                    len(m["players"]), received or now_iso(), json.dumps(_original(m), separators=(",", ":")), match_pub(server, m["id"]),
                    ranked, int(bool(m.get("verified"))), int(m.get("bots") or 0)))
        for i, p in enumerate(m["players"]):
            pid = p["id"]
            xp = match_xp(p, m["duration"])
            detail[i]["xp"] = xp
            db.executemany("INSERT INTO match_stats VALUES(?,?,?,?,?,?,?)",
                           [(server, m["id"], pid, m["ended"], ranked, k, v) for k, v in detail[i].items() if v])
            db.executemany("INSERT INTO match_weapons VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                           [(server, m["id"], pid, m["ended"], ranked, w, ws["kills"], ws["headshots"], ws["shots"], ws["hits"],
                             ws["time"], ws["longest"]) for w, ws in weapons[i].items()])
            db.executemany("INSERT INTO match_vs VALUES(?,?,?,?,?,?,?)",
                           [(server, m["id"], pid, m["players"][j]["id"], m["ended"], ranked, n) for j, n in vs[i].items()])
            for reason in suspicious(detail[i], m):
                db.execute("INSERT OR IGNORE INTO review VALUES(?,?,?,?,?)", (server, m["id"], pid, reason, now_iso()))
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
                db.execute("INSERT INTO players(pid, name, first_seen, last_seen, matches, kills, deaths, team_kills, "
                           "suicides, headshots, damage, rounds_won, wins, objectives, time_played, xp, rating, rated, "
                           "peak_rating, abandons) VALUES(?,?,?,?,0,0,0,0,0,0,0,0,0,0,0,0,?,0,?,0)",
                           (pid, p["name"], m["ended"], m["ended"], RATING_START, RATING_START))
            newer = r is None or m["ended"] >= (r["last_seen"] or "")
            db.execute("""UPDATE players SET name=CASE WHEN ? THEN ? ELSE name END,
                last_seen=MAX(last_seen, ?), first_seen=MIN(first_seen, ?), matches=matches+1, kills=kills+?, deaths=deaths+?,
                team_kills=team_kills+?, suicides=suicides+?, headshots=headshots+?, damage=damage+?,
                rounds_won=rounds_won+?, wins=wins+?, objectives=objectives+?, time_played=time_played+?, xp=xp+?,
                rating=?, rated=rated+?, peak_rating=MAX(peak_rating, ?), abandons=COALESCE(abandons, 0)+? WHERE pid=?""",
                       (int(newer), p["name"], m["ended"], m["ended"], p["kills"], p["deaths"], p["teamKills"],
                        p["suicides"], p["headshots"], p["damage"], p["roundsWon"], int(p["won"]), p["objectives"],
                        p["timePlayed"], xp, after, int(pid in deltas), after,
                        int(bool(p.get("left")) and m["team"] and not p["won"]), pid))
            for w, ws in weapons[i].items():
                db.execute("""INSERT INTO player_weapons VALUES(?,?,?,?,?,?) ON CONFLICT(pid, weapon) DO UPDATE SET
                    kills=kills+excluded.kills, headshots=headshots+excluded.headshots,
                    shots=shots+excluded.shots, hits=hits+excluded.hits""",
                           (pid, w, ws["kills"], ws["headshots"], ws["shots"], ws["hits"]))
        if len(m["players"]) == 2:
            # two players who keep meeting alone: worth a look (stat padding between friends)
            a, b = m["players"][0]["id"], m["players"][1]["id"]
            since = (parse_time(m["ended"]) - dt.timedelta(days=14)).isoformat().replace("+00:00", "Z")
            n = db.execute("SELECT COUNT(*) FROM matches x JOIN match_players pa ON pa.server=x.server AND pa.match=x.id AND pa.pid=? "
                           "JOIN match_players pb ON pb.server=x.server AND pb.match=x.id AND pb.pid=? "
                           "WHERE x.players=2 AND x.ended >= ?", (a, b, since)).fetchone()[0]
            if n >= 5:
                for pid in (a, b):
                    db.execute("INSERT OR IGNORE INTO review VALUES(?,?,?,?,?)",
                               (server, m["id"], pid, "%d two-player matches with the same opponent in 14 days" % n, now_iso()))

    def recompute(self):
        """Rebuilds every total, XP and rating from the stored reports, oldest first."""
        with self.lock:
            stored = [(r["server"], r["received"], json.loads(r["report"])) for r in
                      self.db.execute("SELECT server, received, report FROM matches ORDER BY ended, received")]
            self.db.execute("BEGIN")
            try:
                for t in ("matches", "match_players", "players", "player_weapons", "match_stats", "match_weapons", "match_vs", "review"):
                    self.db.execute("DELETE FROM " + t)
                void = {r[0] for r in self.db.execute("SELECT id FROM voided WHERE kind='match'")}
                for server, received, m in stored:
                    if match_pub(server, m["id"]) in void:
                        continue
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

    @staticmethod
    def _stamp(text):
        """A since/until query value as the stored ISO form, or None when it is missing or not a time."""
        try:
            return parse_time(text).replace(microsecond=0).isoformat().replace("+00:00", "Z") if text else None
        except (ValueError, TypeError):
            return None

    def leaderboard(self, period="all", sort="rating", mode="", limit=100, since="", until="", scope="all"):
        """period is all, 30d or 7d; since/until (ISO times) select any other window, e.g. a season.
        sort "season" ranks by XP earned inside the window and "gain" by rating won inside it."""
        sort = sort if sort in ("rating", "xp", "kills", "kd", "headshots", "wins", "season", "gain") else "rating"
        limit = max(1, min(500, _int(limit, 1, 500)))
        args, where = [], []
        since, until = self._stamp(since), self._stamp(until)
        period = period if period in ("30d", "7d") and not (since or until) else "all"
        if period != "all":
            since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(period[:-1]))).replace(
                microsecond=0).isoformat().replace("+00:00", "Z")
        if since:
            where.append("mp.ended >= ?")
            args.append(since)
        if until:
            where.append("mp.ended < ?")
            args.append(until)
        if mode:
            where.append("m.mode = ?")
            args.append(clean(mode, 32))
        if sort in ("rating", "gain"):
            scope = "ranked"      # the skill rating only moves on ranked servers
        if scope == "ranked":
            where.append("m.ranked = 1")
        where.append("mp.pid NOT IN (SELECT id FROM voided WHERE kind='player')")
        cond = ("WHERE " + " AND ".join(where)) if where else ""
        with self.lock:
            nmatches = self.db.execute("SELECT COUNT(DISTINCT m.server || '/' || m.id) FROM match_players mp JOIN matches m "
                                       "ON m.server=mp.server AND m.id=mp.match " + cond, args).fetchone()[0]
            rows = self.db.execute(
                """SELECT mp.pid, p.name, COUNT(*) matches, SUM(mp.kills) kills, SUM(mp.deaths) deaths,
                   SUM(mp.headshots) headshots, SUM(mp.won) wins, SUM(mp.rounds_won) rounds_won,
                   SUM(mp.objectives) objectives, SUM(mp.time_played) time_played, p.xp xp, p.rating rating,
                   SUM(mp.xp) period_xp, SUM(mp.rating_after - mp.rating_before) rating_gain,
                   (SELECT weapon FROM player_weapons w WHERE w.pid=mp.pid AND w.kills>0 ORDER BY w.kills DESC LIMIT 1) top_weapon
                   FROM match_players mp JOIN matches m ON m.server=mp.server AND m.id=mp.match
                   JOIN players p ON p.pid=mp.pid """ + cond + " GROUP BY mp.pid HAVING COUNT(*) >= ?",
                args + [self.min_matches]).fetchall()
        players = [self._player_json(r) for r in rows]
        for p, r in zip(players, rows):
            p["periodXp"] = r["period_xp"] or 0
            p["ratingGain"] = int(round(r["rating_gain"] or 0))
        key = {"rating": lambda p: (p["rating"], p["kills"]), "xp": lambda p: (p["rank"]["xp"], p["kills"]),
               "season": lambda p: (p["periodXp"], p["kills"]), "gain": lambda p: (p["ratingGain"], p["kills"]),
               "kills": lambda p: (p["kills"], p["kd"]), "kd": lambda p: (p["kd"], p["kills"]),
               "headshots": lambda p: (p["headshots"], p["kills"]), "wins": lambda p: (p["wins"], p["kills"])}[sort]
        players.sort(key=key, reverse=True)
        for i, p in enumerate(players):
            p["position"] = i + 1
        return {"schema": "tcp-leaderboard/1", "updated": now_iso(), "period": period,
                "since": since if period == "all" else None, "until": until, "sort": sort, "mode": mode, "scope": scope, "minMatches": self.min_matches, "matches": nmatches,
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
                """SELECT m.pub, m.ended, m.map, m.mode, m.duration, mp.team, mp.won, mp.kills, mp.deaths, mp.headshots,
                   mp.xp, mp.rating_before, mp.rating_after FROM match_players mp JOIN matches m
                   ON m.server=mp.server AND m.id=mp.match WHERE mp.pid=? ORDER BY mp.ended DESC LIMIT 20""", (pid,))]
            better = self.db.execute("SELECT COUNT(*) FROM players WHERE matches>=? AND rating>?",
                                     (self.min_matches, r["rating"])).fetchone()[0]
        out = self._player_json(r, extra=False)
        out.update({"schema": "tcp-player/1", "updated": now_iso(), "firstSeen": r["first_seen"], "lastSeen": r["last_seen"],
                    "teamKills": r["team_kills"], "suicides": r["suicides"], "damage": r["damage"],
                    "abandons": r["abandons"] or 0,
                    "peakRating": int(round(r["peak_rating"])), "ranked": r["matches"] >= self.min_matches,
                    "position": better + 1 if r["matches"] >= self.min_matches else None,
                    "weapons": [{"name": w["weapon"], "kills": w["kills"], "headshots": w["headshots"],
                                 "shots": w["shots"], "hits": w["hits"],
                                 "accuracy": round(w["hits"] / w["shots"], 3) if w["shots"] else None} for w in weapons],
                    "recent": [{"id": x["pub"], "ended": x["ended"], "map": x["map"], "mode": x["mode"], "duration": x["duration"],
                                "team": x["team"], "won": bool(x["won"]), "kills": x["kills"], "deaths": x["deaths"],
                                "headshots": x["headshots"], "xp": x["xp"],
                                "ratingChange": int(round(x["rating_after"] - x["rating_before"]))} for x in recent]})
        out["topWeapon"] = weapons[0]["weapon"] if weapons and weapons[0]["kills"] else ""
        return out

    def _window(self, period, scope, map_="", mode="", alias="x"):
        where, args = ["%s.pid NOT IN (SELECT id FROM voided WHERE kind='player')" % alias], []
        if period in ("7d", "30d", "90d", "365d"):
            where.append("%s.ended >= ?" % alias)
            args.append((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(period[:-1]))).replace(
                microsecond=0).isoformat().replace("+00:00", "Z"))
        if scope == "ranked":
            where.append("%s.ranked = 1" % alias)
        if map_ or mode:
            sub, sargs = [], []
            if map_:
                sub.append("map = ?")
                sargs.append(clean(map_, 40))
            if mode:
                sub.append("mode = ?")
                sargs.append(clean(mode, 32))
            where.append("(%s.server || '/' || %s.match) IN (SELECT server || '/' || id FROM matches WHERE %s)"
                         % (alias, alias, " AND ".join(sub)))
            args += sargs
        return " AND ".join(where), args

    def totals(self, pid, scope="all", period="all"):
        """Every stat of one player, summed (or best, for "max" stats), with the ratios."""
        cond, args = self._window(period, scope)
        with self.lock:
            rows = self.db.execute("SELECT stat, SUM(value) s, MAX(value) mx FROM match_stats x WHERE x.pid=? AND " + cond +
                                   " GROUP BY stat", [pid] + args).fetchall()
        t = {k: 0 for k in STATS}
        for r in rows:
            if r["stat"] in STATS:
                t[r["stat"]] = r["mx"] if STATS[r["stat"]] == "max" else r["s"]
        return ratios(t)

    def detail(self, pid, scope="all", period="all"):
        """The full stats page of one player (tcp-player-stats/1)."""
        pid = str(pid or "").lower()
        if not re.fullmatch(r"[0-9a-f]{16}", pid):
            return None
        with self.lock:
            r = self.db.execute("SELECT name FROM players WHERE pid=?", (pid,)).fetchone()
            if not r:
                return None
            if self.db.execute("SELECT 1 FROM voided WHERE kind='player' AND id=?", (pid,)).fetchone():
                return {"schema": "tcp-player-stats/1", "id": pid, "name": r["name"], "removed": True}
        cond, args = self._window(period, scope)
        out = {"schema": "tcp-player-stats/1", "updated": now_iso(), "id": pid, "name": r["name"], "scope": scope,
               "period": period, "totals": self.totals(pid, scope, period)}
        with self.lock:
            out["weapons"] = [{"name": w["weapon"], "kills": w["k"], "headshots": w["hs"], "shots": w["sh"], "hits": w["hi"],
                               "accuracy": round(100.0 * w["hi"] / w["sh"], 1) if w["sh"] else None,
                               "headshotRate": round(100.0 * w["hs"] / w["k"], 1) if w["k"] else None,
                               "time": w["t"], "longest": w["lg"]} for w in self.db.execute(
                "SELECT weapon, SUM(kills) k, SUM(headshots) hs, SUM(shots) sh, SUM(hits) hi, SUM(time) t, MAX(longest) lg "
                "FROM match_weapons x WHERE x.pid=? AND " + cond + " GROUP BY weapon ORDER BY k DESC, t DESC", [pid] + args)]
            per = lambda col: [dict(x) for x in self.db.execute(
                "SELECT m.%s name, COUNT(*) matches, SUM(mp.won) wins, SUM(mp.kills) kills, SUM(mp.deaths) deaths, "
                "SUM(mp.time_played) timePlayed FROM match_players mp JOIN matches m ON m.server=mp.server AND m.id=mp.match "
                "JOIN (SELECT DISTINCT server, match FROM match_stats x WHERE x.pid=? AND %s) w ON w.server=mp.server AND w.match=mp.match "
                "WHERE mp.pid=? GROUP BY m.%s ORDER BY matches DESC" % (col, cond, col), [pid] + args + [pid])]
            out["maps"], out["modes"] = per("map"), per("mode")
            for x in out["maps"] + out["modes"]:
                x["winRate"] = round(100.0 * x["wins"] / x["matches"], 1) if x["matches"] else None
                x["kd"] = round(x["kills"] / x["deaths"], 2) if x["deaths"] else float(x["kills"])
            def rival(sql):
                row = self.db.execute(sql + " AND " + cond + " GROUP BY 1 ORDER BY n DESC LIMIT 1", [pid] + args).fetchone()
                if not row or not row["n"]:
                    return None
                name = self.db.execute("SELECT name FROM players WHERE pid=?", (row["o"],)).fetchone()
                return {"id": row["o"], "name": name["name"] if name else "Player", "kills": row["n"]}
            out["nemesis"] = rival("SELECT x.pid o, SUM(x.kills) n FROM match_vs x WHERE x.opp=?")
            out["favouriteVictim"] = rival("SELECT x.opp o, SUM(x.kills) n FROM match_vs x WHERE x.pid=?")
            out["activity"] = [{"day": a["d"], "matches": a["n"]} for a in self.db.execute(
                "SELECT substr(ended, 1, 10) d, COUNT(*) n FROM match_players WHERE pid=? AND ended >= ? GROUP BY d ORDER BY d",
                (pid, (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=371)).strftime("%Y-%m-%d")))]
            out["ratingHistory"] = [{"ended": h["ended"], "rating": int(round(h["rating_after"]))} for h in self.db.execute(
                "SELECT mp.ended, mp.rating_after FROM match_players mp JOIN matches m ON m.server=mp.server AND m.id=mp.match "
                "WHERE mp.pid=? AND m.ranked=1 ORDER BY mp.ended DESC LIMIT 100", (pid,))][::-1]
        return out

    def statboard(self, stat="kills", period="all", scope="all", map_="", mode="", weapon="", limit=100):
        """A leaderboard for any stat or ratio (tcp-statboard/1). Ratios need a fair sample."""
        stat = stat if stat in STATS or stat in DERIVED else "kills"
        limit = max(1, min(500, _int(limit, 1, 500)))
        cond, args = self._window(period, scope, map_, mode)
        minimum = {"kd": ("kills", 25), "headshotRate": ("kills", 25), "accuracy": ("shots", 500), "headHitRate": ("hitsAll", 50),
                   "adr": ("roundsPlayed", 20), "winRate": ("matches", 10), "kpm": ("timePlayed", 3600),
                   "avgKillDistance": ("kills", 25)}
        if weapon and stat not in ("kills", "headshots", "longestKill", "accuracy", "timePlayed"):
            stat = "kills"        # per weapon, only these exist
        with self.lock:
            if weapon:
                col = {"kills": "SUM(kills)", "headshots": "SUM(headshots)", "longestKill": "MAX(longest)",
                       "accuracy": "100.0 * SUM(hits) / MAX(1, SUM(shots))", "timePlayed": "SUM(time)"}.get(stat, "SUM(kills)")
                having = "SUM(shots) >= 200" if stat == "accuracy" else "1"
                minimum["accuracy"] = ("shots", 200)
                rows = self.db.execute("SELECT x.pid, %s v, COUNT(DISTINCT x.match) n FROM match_weapons x WHERE x.weapon=? AND %s "
                                       "GROUP BY x.pid HAVING %s AND v > 0 ORDER BY v DESC LIMIT ?" % (col, cond, having),
                                       [clean(weapon, 24)] + args + [limit]).fetchall()
            elif stat in STATS:
                agg = "MAX" if STATS[stat] == "max" else "SUM"
                rows = self.db.execute("SELECT x.pid, %s(x.value) v, COUNT(DISTINCT x.match) n FROM match_stats x WHERE x.stat=? AND %s "
                                       "GROUP BY x.pid HAVING v > 0 ORDER BY v DESC LIMIT ?" % (agg, cond),
                                       [stat] + args + [limit]).fetchall()
            else:
                num, den, scale = DERIVED[stat]
                floor_stat, floor = minimum[stat]
                parts = {num, den, floor_stat} - {"hitsAll", "minutes"}
                need = sorted(parts | ({"hitsHead", "hitsBody", "hitsLegs"} if "hitsAll" in (num, den, floor_stat) else set())
                              | ({"timePlayed"} if "minutes" in (num, den) else set()))
                q = "SELECT x.pid, x.stat, SUM(x.value) v FROM match_stats x WHERE x.stat IN (%s) AND %s GROUP BY x.pid, x.stat" % (
                    ",".join("?" * len(need)), cond)
                acc = {}
                for r in self.db.execute(q, need + args):
                    acc.setdefault(r["pid"], {})[r["stat"]] = r["v"]
                ranked_rows = []
                for pid_, t in acc.items():
                    full = ratios({k: t.get(k, 0) for k in STATS})
                    if full.get(floor_stat, 0) < floor or full.get(stat) is None:
                        continue
                    ranked_rows.append({"pid": pid_, "v": full[stat], "n": None})
                ranked_rows.sort(key=lambda r: r["v"], reverse=True)
                rows = ranked_rows[:limit]
            names = {r["pid"]: r["name"] for r in self.db.execute(
                "SELECT pid, name FROM players WHERE pid IN (%s)" % ",".join("?" * len(rows)), [r["pid"] for r in rows])} if rows else {}
        return {"schema": "tcp-statboard/1", "updated": now_iso(), "stat": stat, "period": period, "scope": scope, "map": map_,
                "mode": mode, "weapon": weapon, "minimum": dict(zip(("stat", "value"), minimum[stat])) if stat in minimum else None,
                "players": [{"position": i + 1, "id": r["pid"], "name": names.get(r["pid"], "Player"),
                             "value": round(r["v"], 1) if isinstance(r["v"], float) else r["v"]} for i, r in enumerate(rows)]}

    def h2h(self, a, b, scope="all"):
        """Head-to-head between two players (tcp-h2h/1)."""
        a, b = str(a or "").lower(), str(b or "").lower()
        if not (re.fullmatch(r"[0-9a-f]{16}", a) and re.fullmatch(r"[0-9a-f]{16}", b)) or a == b:
            return None
        cond, args = self._window("all", scope)
        with self.lock:
            names = {r["pid"]: r["name"] for r in self.db.execute("SELECT pid, name FROM players WHERE pid IN (?, ?)", (a, b))}
            if len(names) < 2:
                return None
            def kills(x, y):
                return self.db.execute("SELECT COALESCE(SUM(kills), 0) FROM match_vs x WHERE x.pid=? AND x.opp=? AND " + cond,
                                       [x, y] + args).fetchone()[0]
            shared = self.db.execute(
                "SELECT m.pub, m.ended, m.map, m.mode, pa.team ta, pb.team tb, pa.won wa, pb.won wb FROM match_players pa "
                "JOIN match_players pb ON pb.server=pa.server AND pb.match=pa.match AND pb.pid=? "
                "JOIN matches m ON m.server=pa.server AND m.id=pa.match WHERE pa.pid=? %s ORDER BY m.ended DESC"
                % ("AND m.ranked=1" if scope == "ranked" else ""), (b, a)).fetchall()
        against = [x for x in shared if x["ta"] != x["tb"] or not x["ta"]]
        return {"schema": "tcp-h2h/1", "updated": now_iso(), "scope": scope,
                "a": {"id": a, "name": names[a], "kills": kills(a, b), "wins": sum(1 for x in against if x["wa"])},
                "b": {"id": b, "name": names[b], "kills": kills(b, a), "wins": sum(1 for x in against if x["wb"])},
                "matchesAgainst": len(against), "matchesTogether": len(shared) - len(against),
                "recent": [{"id": x["pub"], "ended": x["ended"], "map": x["map"], "mode": x["mode"],
                            "together": bool(x["ta"]) and x["ta"] == x["tb"], "aWon": bool(x["wa"]), "bWon": bool(x["wb"])}
                           for x in shared[:10]]}

    def meta(self):
        """What the stat boards can filter on: the maps, modes and weapons that have verified matches (tcp-statmeta/1)."""
        with self.lock:
            maps = [r[0] for r in self.db.execute("SELECT map FROM matches GROUP BY map ORDER BY COUNT(*) DESC") if r[0]]
            modes = [r[0] for r in self.db.execute("SELECT mode FROM matches GROUP BY mode ORDER BY COUNT(*) DESC") if r[0]]
            weapons = [r[0] for r in self.db.execute("SELECT weapon FROM match_weapons WHERE kills > 0 GROUP BY weapon "
                                                     "ORDER BY SUM(kills) DESC") if r[0]]
        return {"schema": "tcp-statmeta/1", "updated": now_iso(), "stats": list(STATS), "ratios": list(DERIVED),
                "maps": maps, "modes": modes, "weapons": weapons}

    # ------------------------------------------------------------ staff
    def review_list(self, limit=100):
        with self.lock:
            return [dict(r) for r in self.db.execute(
                "SELECT r.pid, p.name, m.pub AS match_id, r.reason, r.created FROM review r LEFT JOIN players p ON p.pid=r.pid "
                "LEFT JOIN matches m ON m.server=r.server AND m.id=r.match "
                "WHERE r.pid NOT IN (SELECT id FROM voided WHERE kind='player') ORDER BY r.created DESC LIMIT ?", (limit,))]

    def void(self, kind, ident, reason=""):
        """Staff: remove a match (by its public id) or every stat of a player. Rebuilds the totals."""
        if kind not in ("match", "player") or not re.fullmatch(r"[0-9a-f]{16}", str(ident or "")):
            raise ValueError("void match|player <16-character id>")
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO voided VALUES(?,?,?,?)", (kind, ident, clean(reason, 200), now_iso()))
        return self.recompute()

    def unvoid(self, kind, ident):
        with self.lock:
            self.db.execute("DELETE FROM voided WHERE kind=? AND id=?", (kind, ident))
        return self.recompute()

    def export_ratings(self, path):
        """Writes '<pid> <rating>' lines for the game servers' skill-based team
        balance (g_balanceSkill reads ratings.txt from the server's home folder).
        Atomic, so a server never reads a half-written file. Returns the count."""
        with self.lock:
            rows = [(r["pid"], r["rating"]) for r in
                    self.db.execute("SELECT pid, rating FROM players WHERE rated > 0 ORDER BY pid")]
            rating = dict(rows)
            # accounts: the game looks a player up by its own id, so every id of a merged player carries its rating
            extra = {}
            current = {r["pid"]: r["canonical"] for r in self.db.execute("SELECT pid, canonical FROM aliases WHERE until IS NULL")}
            links = dict(current)
            for (gid,) in self.db.execute("SELECT DISTINCT old FROM guid_keys").fetchall():
                key, _ = self._guid_target(gid)
                if key:
                    links[gid] = current.get(key, key)
            for pid, to_pid in links.items():
                if to_pid in rating:            # a linked id plays at its account's rating, even with a few matches of its own
                    extra[pid] = rating[to_pid]
            rows = sorted(dict(rows, **extra).items())
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="ascii") as fh:
            for pid, value in rows:
                fh.write("%s %d\n" % (pid, int(round(value))))
        os.replace(tmp, path)
        return len(rows)

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
            rows = self.db.execute("SELECT m.server sid, m.id mid, m.pub id, m.ended, m.map, m.mode, m.duration, m.rounds, m.winner, "
                                   "m.players, m.ranked, COALESCE(NULLIF(json_extract(m.report, '$.server'), ''), s.name) server "
                                   "FROM matches m LEFT JOIN servers s ON s.id=m.server "
                                   "ORDER BY m.ended DESC LIMIT ?", (max(1, min(100, limit)),)).fetchall()
            matches = []
            for r in rows:
                m = {k: r[k] for k in ("id", "ended", "map", "mode", "duration", "rounds", "winner", "players", "server")}
                m["ranked"] = bool(r["ranked"])
                # the match MVP: most kills, then most XP
                top = self.db.execute("SELECT pid, name, kills FROM match_players WHERE server=? AND match=? "
                                      "ORDER BY kills DESC, xp DESC LIMIT 1", (r["sid"], r["mid"])).fetchone()
                m["mvp"] = {"id": top["pid"], "name": top["name"], "kills": top["kills"]} if top and top["kills"] else None
                matches.append(m)
        return {"schema": "tcp-recent/1", "updated": now_iso(), "matches": matches}

    def netstats(self, days=30):
        """Connection quality per server from the match reports (tcp-match/1 "net"): what players
        actually experience, so tick rate, lag compensation and caps are tuned on data."""
        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max(1, min(365, _int(days, 1, 365))))
                 ).isoformat().replace("+00:00", "Z")
        agg = {}
        with self.lock:
            rows = self.db.execute("SELECT m.server sid, s.name, m.report FROM matches m LEFT JOIN servers s "
                                   "ON s.id=m.server WHERE m.ended >= ?", (since,)).fetchall()
        for r in rows:
            try:
                rep = json.loads(r["report"])
            except ValueError:
                continue
            a = agg.setdefault(r["sid"], {"server": r["name"] or r["sid"], "matches": 0, "samples": 0, "ping": 0.0,
                                          "jitter": 0.0, "loss": 0.0, "rewind": 0.0, "shots": 0, "capped": 0,
                                          "pingOver150": 0, "lossOver2": 0, "leaves": 0})
            a["matches"] += 1
            for p in rep.get("players", []):
                n = p.get("net")
                a["leaves"] += int(bool(p.get("left")))
                if not n or not n.get("ping"):
                    continue
                a["samples"] += 1
                a["ping"] += n["ping"]
                a["jitter"] += n["jitter"]
                a["loss"] += n["loss"]
                a["rewind"] += n["rewind"] * n["shotsRewound"]
                a["shots"] += n["shotsRewound"]
                a["capped"] += n["rewindCapped"]
                a["pingOver150"] += int(n["ping"] > 150)
                a["lossOver2"] += int(n["loss"] > 2)
        out = []
        for a in agg.values():
            s = max(1, a["samples"])
            out.append({"server": a["server"], "matches": a["matches"], "players": a["samples"],
                        "avgPing": round(a["ping"] / s), "avgJitter": round(a["jitter"] / s, 1),
                        "avgLoss": round(a["loss"] / s, 2), "avgRewind": round(a["rewind"] / max(1, a["shots"])),
                        "rewindCappedPct": round(100.0 * a["capped"] / max(1, a["shots"]), 2),
                        "highPingPct": round(100.0 * a["pingOver150"] / s, 1),
                        "highLossPct": round(100.0 * a["lossOver2"] / s, 1), "leaves": a["leaves"]})
        out.sort(key=lambda x: -x["matches"])
        return {"schema": "tcp-netstats/1", "updated": now_iso(), "days": days, "servers": out}

    def match(self, pub):
        """One finished match for its page on the website: the result and both teams' scoreboards."""
        pub = str(pub or "").lower()
        if not re.fullmatch(r"[0-9a-f]{16}", pub):
            return None
        with self.lock:
            r = self.db.execute("SELECT m.*, s.name server_name FROM matches m LEFT JOIN servers s ON s.id=m.server "
                                "WHERE m.pub=?", (pub,)).fetchone()
            if not r:
                return None
            rows = self.db.execute("SELECT * FROM match_players WHERE server=? AND match=? ORDER BY kills DESC, xp DESC",
                                   (r["server"], r["id"])).fetchall()
        try:
            rep = json.loads(r["report"] or "{}")
            version, host = clean(rep.get("version"), 48), clean(rep.get("server"), 64)
        except ValueError:
            version, host = "", ""
        players = [{"id": p["pid"], "name": p["name"], "team": p["team"], "won": bool(p["won"]), "kills": p["kills"],
                    "deaths": p["deaths"], "headshots": p["headshots"], "damage": p["damage"], "teamKills": p["team_kills"],
                    "objectives": p["objectives"], "roundsWon": p["rounds_won"], "timePlayed": p["time_played"], "xp": p["xp"],
                    "ratingChange": int(round(p["rating_after"] - p["rating_before"])), "topWeapon": p["top_weapon"] or ""}
                   for p in rows]
        # a team's score is the most rounds any of its players was present to win
        score = {}
        for p in players:
            if p["team"]:
                score[p["team"]] = max(score.get(p["team"], 0), p["roundsWon"])
        top = players[0] if players and players[0]["kills"] else None
        return {"schema": "tcp-match-page/1", "updated": now_iso(), "id": pub, "ended": r["ended"], "map": r["map"],
                "mode": r["mode"], "duration": r["duration"], "rounds": r["rounds"], "winner": r["winner"],
                "server": host or r["server_name"], "version": version, "score": score, "ranked": bool(r["ranked"]),
                "antiCheat": bool(r["verified"]),
                "mvp": {"id": top["id"], "name": top["name"], "kills": top["kills"]} if top else None, "players": players}

    def recap(self, days=7):
        """What happened in the last N days (tcp-recap/1): totals, the busiest map and the standout players."""
        days = max(1, min(92, _int(days, 1, 92)))
        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).replace(
            microsecond=0).isoformat().replace("+00:00", "Z")

        def best(expr, having="1"):
            r = self.db.execute(
                "SELECT mp.pid, p.name, %s v, COUNT(*) n FROM match_players mp JOIN players p ON p.pid=mp.pid "
                "WHERE mp.ended >= ? GROUP BY mp.pid HAVING %s ORDER BY v DESC, n DESC LIMIT 1" % (expr, having),
                (since,)).fetchone()
            return {"id": r["pid"], "name": r["name"], "value": round(r["v"], 2), "matches": r["n"]} if r and r["v"] else None

        with self.lock:
            tot = self.db.execute("SELECT COUNT(*) n, COALESCE(SUM(duration), 0) secs FROM matches WHERE ended >= ?",
                                  (since,)).fetchone()
            ppl = self.db.execute("SELECT COUNT(DISTINCT pid) n, COALESCE(SUM(kills), 0) kills, "
                                  "COALESCE(SUM(headshots), 0) hs FROM match_players WHERE ended >= ?", (since,)).fetchone()
            new = self.db.execute("SELECT COUNT(*) FROM players WHERE first_seen >= ?", (since,)).fetchone()[0]
            maps = [{"map": r["map"], "matches": r["n"]} for r in self.db.execute(
                "SELECT map, COUNT(*) n FROM matches WHERE ended >= ? GROUP BY map ORDER BY n DESC, map LIMIT 3", (since,))]
            out = {"schema": "tcp-recap/1", "updated": now_iso(), "days": days, "since": since,
                   "matches": tot["n"], "timePlayed": tot["secs"], "players": ppl["n"], "newPlayers": new,
                   "kills": ppl["kills"], "headshots": ppl["hs"], "maps": maps,
                   "mostKills": best("SUM(mp.kills)"), "mostWins": best("SUM(mp.won)"),
                   "mostXp": best("SUM(mp.xp)"), "mostObjectives": best("SUM(mp.objectives)"),
                   "biggestClimb": best("SUM(mp.rating_after - mp.rating_before)"),
                   "bestKd": best("CAST(SUM(mp.kills) AS REAL) / MAX(1, SUM(mp.deaths))", "COUNT(*) >= 3"),
                   "mostActive": best("COUNT(*)")}
        return out

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
        return 200, store.leaderboard(q.get("period", "all"), q.get("sort", "rating"), q.get("mode", ""),
                                      q.get("limit", 100), q.get("since", ""), q.get("until", ""),
                                      "ranked" if q.get("scope") == "ranked" else "all")
    scope = "ranked" if q.get("scope") == "ranked" else "all"
    if path == "/stats.json":
        p = store.detail(q.get("id"), scope, q.get("period", "all"))
        return (200, p) if p else (404, {"error": "unknown player"})
    if path == "/statboard.json":
        return 200, store.statboard(q.get("stat", "kills"), q.get("period", "all"), scope, q.get("map", ""), q.get("mode", ""),
                                    q.get("weapon", ""), q.get("limit", 100))
    if path == "/statmeta.json":
        return 200, store.meta()
    if path == "/h2h.json":
        h = store.h2h(q.get("a"), q.get("b"), scope)
        return (200, h) if h else (404, {"error": "unknown players"})
    if path == "/player.json":
        p = store.player(q.get("id"))
        return (200, p) if p else (404, {"error": "unknown player"})
    if path == "/search.json":
        return 200, store.search(q.get("q", ""))
    if path == "/recent.json":
        return 200, store.recent()
    if path == "/match.json":
        m = store.match(q.get("id"))
        return (200, m) if m else (404, {"error": "unknown match"})
    if path == "/recap.json":
        return 200, store.recap(q.get("days", 7))
    if path == "/ranks.json":
        return 200, store.ranks()
    if path == "/netstats.json":
        return 200, store.netstats(q.get("days", 30))
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


def staff_token(path=""):
    """The shared secret of the staff portal's routes: --staff-token-file, else the systemd credential 'staff-token'
    (a LoadCredential= drop-in, so the service's command line stays as it is), else TCP_STATS_STAFF_TOKEN.
    Empty = the routes are off."""
    cred = os.environ.get("CREDENTIALS_DIRECTORY", "")
    if not path and cred and (pathlib.Path(cred) / "staff-token").exists():
        path = str(pathlib.Path(cred) / "staff-token")
    if path:
        try:
            return pathlib.Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return os.environ.get("TCP_STATS_STAFF_TOKEN", "").strip()


def accounts_token():
    """The account service's secret: the systemd credential 'accounts-token' (a LoadCredential= drop-in), else
    TCP_STATS_ACCOUNTS_TOKEN. Empty = the route is off."""
    cred = os.environ.get("CREDENTIALS_DIRECTORY", "")
    if cred and (pathlib.Path(cred) / "accounts-token").exists():
        try:
            return (pathlib.Path(cred) / "accounts-token").read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return os.environ.get("TCP_STATS_ACCOUNTS_TOKEN", "").strip()


def handle_staff(store, method, path, headers, client, body, token):
    """Staff portal routes: the review queue and voiding stats. Only from this machine, never through the
    reverse proxy (which adds X-Forwarded-For), and only with the shared token. Anything else looks like 404."""
    if not path.startswith("/staff/"):
        return None
    if path == "/staff/accounts/aliases":
        # the account service (its own token, never the staff portal's): which player ids are one account
        acct = accounts_token()
        if (method != "POST" or not acct or client not in ("127.0.0.1", "::1") or headers.get("X-Forwarded-For")
                or not hmac.compare_digest(str(headers.get("X-Accounts-Token", "")), acct)):
            return 404, {"error": "not found"}
        try:
            d = json.loads(body or b"{}")
            n = store.set_aliases(d.get("aliases"))
        except (ValueError, TypeError, AttributeError) as exc:
            return 400, {"error": str(exc)}
        return 200, {"ok": True, "rebuilt": "unchanged" if n is None else n, "seen": store.last_seen_of(d.get("aliases"))}
    if (not token or client not in ("127.0.0.1", "::1") or headers.get("X-Forwarded-For")
            or not hmac.compare_digest(str(headers.get("X-Staff-Token", "")), token)):
        return 404, {"error": "not found"}
    if method == "GET" and path == "/staff/review.json":
        return 200, {"review": store.review_list(200)}
    if method == "POST" and path in ("/staff/void", "/staff/unvoid"):
        try:
            d = json.loads(body or b"{}")
            kind, ident = d.get("kind"), str(d.get("id", ""))
            if kind not in ("match", "player") or not re.fullmatch(r"[0-9a-f]{16}", ident):
                raise ValueError("void match|player <16-character id>")
            n = store.void(kind, ident, str(d.get("reason", ""))) if path == "/staff/void" else store.unvoid(kind, ident)
        except (ValueError, AttributeError) as exc:
            return 400, {"error": str(exc)}
        return 200, {"ok": True, "rebuilt": n}
    return 404, {"error": "not found"}


def sign(key_hex, body, stamp=None):
    stamp = str(int(stamp if stamp is not None else time.time()))
    return stamp, hmac.new(bytes.fromhex(key_hex), stamp.encode() + b"\n" + body, hashlib.sha256).hexdigest()


def serve(store, listen, cors, token=""):
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
            private = self.path.startswith("/staff/")
            self.send_header("Cache-Control", "public, max-age=30" if self.command == "GET" and not private else "no-store")
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
            r = handle_staff(store, "GET", u.path, self.headers, self.client_address[0], b"", token) or \
                handle_get(store, u.path, parse_qs(u.query))
            self.reply(*(r or (404, {"error": "not found"})))

        def do_POST(self):
            n = _int(self.headers.get("Content-Length"), 0, MAX_BODY + 1)
            body = self.rfile.read(n)
            path = urlparse(self.path).path
            r = handle_staff(store, "POST", path, self.headers, self.client_address[0], body, token) or \
                handle_post(store, path, self.headers, body)
            self.reply(*(r or (404, {"error": "not found"})))

    host, _, port = listen.rpartition(":")
    print("tcp-stats on http://%s:%s" % (host, port), flush=True)
    ThreadingHTTPServer((host, int(port)), Handler).serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="stats.db")
    ap.add_argument("--allow-cheats", action="store_true", help="accept matches played with sv_cheats 1 (testing)")
    ap.add_argument("--min-matches", type=int, default=3)
    ap.add_argument("--require-anticheat", action="store_true",
                    help="only accept tcp-match/2 reports from matches with Easy Anti-Cheat on (live service)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--listen", default="127.0.0.1:8091")
    s.add_argument("--cors", default="https://truecombat.eu,https://www.truecombat.eu")
    s.add_argument("--staff-token-file", default="", help="shared secret for the staff portal's /staff/ routes (loopback only)")
    s.add_argument("--import-dir", default="", help="also import this folder every minute (trusted)")
    s.add_argument("--ratings-file", action="append", default=[],
                   help="keep this ratings.txt current for skill-based team balance (repeatable)")
    a = sub.add_parser("add-server")
    a.add_argument("name")
    sub.add_parser("list-servers")
    for name in ("disable-server", "enable-server"):
        sub.add_parser(name).add_argument("id")
    i = sub.add_parser("import")
    i.add_argument("--server", default="local")
    i.add_argument("folder")
    sub.add_parser("recompute")
    sub.add_parser("export-ratings").add_argument("file")
    sub.add_parser("review")
    for name in ("void", "unvoid"):
        v = sub.add_parser(name)
        v.add_argument("kind", choices=("match", "player"))
        v.add_argument("id")
        if name == "void":
            v.add_argument("--reason", default="")
    args = ap.parse_args(argv)
    store = StatsStore(args.db, allow_cheats=args.allow_cheats, min_matches=args.min_matches,
                       require_anticheat=args.require_anticheat)
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
    elif args.cmd == "review":
        print(json.dumps(store.review_list(), indent=2))
    elif args.cmd == "void":
        print("voided; rebuilt", store.void(args.kind, args.id, args.reason), "matches")
    elif args.cmd == "unvoid":
        print("restored; rebuilt", store.unvoid(args.kind, args.id), "matches")
    elif args.cmd == "export-ratings":
        print("exported", store.export_ratings(args.file), "ratings")
    elif args.cmd == "serve":
        if args.import_dir or args.ratings_file:
            def loop():
                while True:
                    try:
                        if args.import_dir:
                            store.import_dir(args.import_dir)
                        for f in args.ratings_file:
                            store.export_ratings(f)
                    except Exception as exc:
                        print("import failed:", exc, flush=True)
                    time.sleep(60)
            threading.Thread(target=loop, daemon=True).start()
        serve(store, args.listen, args.cors, staff_token(args.staff_token_file))


if __name__ == "__main__":
    main()
