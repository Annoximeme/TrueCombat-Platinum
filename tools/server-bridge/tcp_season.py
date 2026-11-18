#!/usr/bin/env python3
"""TrueCombat: Platinum seasons: season rating tiers, weekly contracts and solo (practice) boards.

Pure rules, no storage: tcp_stats.py keeps the tables and calls these. Python 3.8+ standard library only.

Seasons
  A season is a dated window (UTC). Ranked matches inside it move a season rating next to the all-time one.
  A player's first season rating is a soft reset of the all-time rating: 1000 + half the distance from 1000.
  The tier (1-8, the K25 emblems) comes from the season rating; a player drops a tier only DEMOTE_MARGIN points
  below its cut-off, and Platinum also needs PLATINUM_MATCHES ranked matches in the season.

Contracts
  Every Monday 00:00 Europe/Brussels three contracts open (easy, medium, hard), the same for everyone, picked from
  a fixed pool in a fixed order. They count the stats tcp_stats.py already trusts (real players only, verified
  servers). Each pays CONTRACT_XP, all three a further CONTRACT_BONUS_XP.

Solo boards
  Local practice runs (firing-range time trial, accuracy drill, weekly bot challenge), signed by the player's
  identity key and checked for what no human can do. They never touch rating, tiers or XP.
"""
import datetime as dt
import hashlib
import json
import re

try:
    from zoneinfo import ZoneInfo
    BRUSSELS = ZoneInfo("Europe/Brussels")
except Exception:  # pragma: no cover - Python without tz data: CET without summer time is close enough for weeks
    BRUSSELS = dt.timezone(dt.timedelta(hours=1))

RATING_START = 1000.0
DEMOTE_MARGIN = 25
PLATINUM_MATCHES = 10

# tier, name, short, season rating from (tier 1 has no floor)
TIERS = [
    (1, "Rookie", "RKE", None),
    (2, "Contender", "CTD", 850),
    (3, "Operator", "OPR", 950),
    (4, "Veteran", "VET", 1050),
    (5, "Elite", "ELT", 1150),
    (6, "Vanguard", "VGD", 1250),
    (7, "Spearhead", "SPH", 1350),
    (8, "Platinum", "PLT", 1450),
]

# Season 1 opens with the 0.40.0 launch: Fri 5 Feb 2027 18:00 CET, ends Fri 7 May 2027 18:00 CEST.
DEFAULT_SEASONS = [
    {"id": "s1", "number": 1, "name": "Season 1", "start": "2027-02-05T17:00:00Z", "end": "2027-05-07T16:00:00Z",
     # launch week: double XP and the Frontline badge (one match on an official server)
     "xpMultiplier": [{"start": "2027-02-05T17:00:00Z", "end": "2027-02-14T23:00:00Z", "factor": 2}],
     "badges": [{"id": "frontline", "name": "Frontline", "start": "2027-02-05T17:00:00Z", "end": "2027-02-14T23:00:00Z",
                 "rule": "one finished match on an official server"}]},
]

CONTRACT_XP = 150
CONTRACT_BONUS_XP = 250

# A contract counts one thing over the week:
#   sum:   these match stats added up (tcp_stats.STATS keys)
#   count: matches where stat >= atLeast
#   mode:  only matches whose mode contains one of these words (case-insensitive)
#   ranked: only ranked matches
# Order inside each list is the rotation order. "group" keeps two contracts of one kind out of the same week.
CONTRACTS = {
    "easy": [
        {"id": "e-play3", "text": "Play 3 matches", "sum": ["matches"], "target": 3, "group": "play"},
        {"id": "e-rounds5", "text": "Win 5 rounds", "sum": ["roundsWon"], "target": 5, "group": "rounds"},
        {"id": "e-kills10", "text": "Get 10 kills", "sum": ["kills"], "target": 10, "group": "kills"},
        {"id": "e-obj1", "text": "Plant or defuse a bomb", "sum": ["plants", "defuses"], "target": 1, "group": "bomb"},
        {"id": "e-assists5", "text": "Get 5 assists", "sum": ["assists"], "target": 5, "group": "assists"},
        {"id": "e-play2r", "text": "Play 2 Ranked matches", "sum": ["matches"], "target": 2, "ranked": True, "group": "play"},
        {"id": "e-aimed8", "text": "Get 8 kills while aiming down sights", "sum": ["aimedKills"], "target": 8, "group": "kills"},
        {"id": "e-damage1500", "text": "Deal 1,500 damage", "sum": ["damage"], "target": 1500, "group": "damage"},
    ],
    "medium": [
        {"id": "m-bombrounds3", "text": "Win 3 Bomb rounds", "sum": ["roundsWon"], "target": 3, "mode": ["bomb", "objective"],
         "group": "bomb"},
        {"id": "m-hs5", "text": "Get 5 headshot kills", "sum": ["headshots"], "target": 5, "group": "kills"},
        {"id": "m-trades3", "text": "Make 3 trades", "sum": ["trades"], "target": 3, "group": "trades"},
        {"id": "m-open3", "text": "Get 3 opening kills", "sum": ["openingKills"], "target": 3, "group": "open"},
        {"id": "m-wins2", "text": "Win 2 matches", "sum": ["wins"], "target": 2, "group": "play"},
        {"id": "m-low10", "text": "Get 10 kills while crouched or prone", "sum": ["crouchKills", "proneKills"], "target": 10,
         "group": "kills"},
        {"id": "m-double3", "text": "Get 3 double kills", "sum": ["doubleKills", "tripleKills", "quadKills"], "target": 3,
         "group": "multi"},
        {"id": "m-mvp3", "text": "Be round MVP 3 times", "sum": ["roundMvps"], "target": 3, "group": "rounds"},
    ],
    "hard": [
        {"id": "h-long40", "text": "Get a kill from 40 m or more", "count": "longestKill", "atLeast": 40, "target": 1,
         "group": "long"},
        {"id": "h-clutch2", "text": "Win a 1-vs-2 clutch", "count": "bestClutch", "atLeast": 2, "target": 1, "group": "clutch"},
        {"id": "h-knife2", "text": "Get 2 knife kills", "sum": ["knifeKills"], "target": 2, "group": "knife"},
        {"id": "h-triple1", "text": "Get a triple kill", "sum": ["tripleKills", "quadKills"], "target": 1, "group": "multi"},
        {"id": "h-obj3", "text": "Plant or defuse 3 bombs", "sum": ["plants", "defuses"], "target": 3, "group": "bomb"},
        {"id": "h-rwins3", "text": "Win 3 Ranked matches", "sum": ["wins"], "target": 3, "ranked": True, "group": "play"},
        {"id": "h-streak5", "text": "Get 5 kills without dying", "count": "bestStreak", "atLeast": 5, "target": 1,
         "group": "streak"},
        {"id": "h-revenge3", "text": "Take revenge 3 times", "sum": ["revenges"], "target": 3, "group": "trades"},
    ],
}

# ---------------------------------------------------------------------------- time helpers


def parse(text):
    return dt.datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def iso(t):
    return t.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def week_start(t):
    """Monday 00:00 Brussels time of the week t falls in (UTC datetime)."""
    local = parse(t).astimezone(BRUSSELS) if isinstance(t, str) else t.astimezone(BRUSSELS)
    monday = (local - dt.timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    # rebuild through the zone so a DST change inside the week does not shift Monday's midnight
    return dt.datetime(monday.year, monday.month, monday.day, tzinfo=BRUSSELS).astimezone(dt.timezone.utc)


def week_key(t):
    ws = week_start(t).astimezone(BRUSSELS)
    y, w, _ = ws.isocalendar()
    return "%d-W%02d" % (y, w)


def week_bounds(key):
    m = re.fullmatch(r"(\d{4})-W(\d{2})", str(key or ""))
    if not m:
        return None
    d = dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    start = dt.datetime(d.year, d.month, d.day, tzinfo=BRUSSELS)
    end = start + dt.timedelta(days=7)
    end = dt.datetime(end.year, end.month, end.day, tzinfo=BRUSSELS)
    return start.astimezone(dt.timezone.utc), end.astimezone(dt.timezone.utc)


# ---------------------------------------------------------------------------- seasons


def load_seasons(path=""):
    """The season list from a JSON file (a list, or {"seasons": [...]}) or the built-in one."""
    if not path:
        return [dict(s) for s in DEFAULT_SEASONS]
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    seasons = data.get("seasons") if isinstance(data, dict) else data
    out = []
    for s in seasons or []:
        if not re.fullmatch(r"[a-z0-9-]{1,16}", str(s.get("id", ""))):
            raise ValueError("season id: 1-16 of a-z 0-9 -")
        if parse(s["end"]) <= parse(s["start"]):
            raise ValueError("season %s ends before it starts" % s["id"])
        out.append(dict(s))
    out.sort(key=lambda s: s["start"])
    for a, b in zip(out, out[1:]):
        if parse(b["start"]) < parse(a["end"]):
            raise ValueError("seasons %s and %s overlap" % (a["id"], b["id"]))
    return out


def season_at(seasons, t):
    t = parse(t) if isinstance(t, str) else t
    for s in seasons:
        if parse(s["start"]) <= t < parse(s["end"]):
            return s
    return None


def current_or_next(seasons, t):
    """(season, state): the running season ("live"), else the next one ("upcoming"), else the last ("ended")."""
    t = parse(t) if isinstance(t, str) else t
    live = season_at(seasons, t)
    if live:
        return live, "live"
    nxt = [s for s in seasons if parse(s["start"]) > t]
    if nxt:
        return nxt[0], "upcoming"
    return (seasons[-1], "ended") if seasons else (None, "none")


def xp_factor(season, t):
    if not season:
        return 1
    t = parse(t) if isinstance(t, str) else t
    for w in season.get("xpMultiplier") or []:
        if parse(w["start"]) <= t < parse(w["end"]):
            return max(1, int(w.get("factor", 1)))
    return 1


def soft_reset(career_rating):
    return RATING_START + 0.5 * ((career_rating if career_rating is not None else RATING_START) - RATING_START)


def tier_for(rating, matches, prev=None):
    """Tier 1-8 for a season rating. A drop needs DEMOTE_MARGIN points under the old tier's cut-off; Platinum
    needs PLATINUM_MATCHES season matches (until then the player stays at most Spearhead)."""
    t = 1
    for tier, _, _, floor in TIERS:
        if floor is None or rating >= floor:
            t = tier
    if t == 8 and matches < PLATINUM_MATCHES:
        t = 7
    if prev and t < prev:
        floor = TIERS[prev - 1][3]
        if floor is not None and rating >= floor - DEMOTE_MARGIN and not (prev == 8 and matches < PLATINUM_MATCHES):
            t = prev
    return t


def tier_progress(rating, tier):
    """0-99: how far into the band towards the next tier (99 at the top tier)."""
    if tier >= 8:
        return 99
    lo = TIERS[tier - 1][3]
    hi = TIERS[tier][3]
    if lo is None:
        lo = hi - 100
    return max(0, min(99, int((rating - lo) * 100 // (hi - lo))))


def tier_json(tier):
    _, name, short, floor = TIERS[tier - 1]
    return {"tier": tier, "name": name, "short": short, "from": floor, "emblem": "rank%d" % tier}


def tiers_json():
    return [dict(tier_json(t), next=TIERS[t][3] if t < 8 else None) for t, _, _, _ in TIERS]


# ---------------------------------------------------------------------------- contracts


def _week_index(key):
    b = week_bounds(key)
    epoch = dt.datetime(2027, 2, 1, tzinfo=dt.timezone.utc)      # week of the Season 1 launch = index 0
    return int(round((b[0] - epoch).total_seconds() / (7 * 86400))) if b else 0


def contracts_for_week(key):
    """The three contracts of a week: one per difficulty, rotating, never two of one group."""
    i = _week_index(key)
    out, groups = [], set()
    for diff in ("easy", "medium", "hard"):
        pool = CONTRACTS[diff]
        for step in range(len(pool)):
            c = pool[(i + step) % len(pool)]
            if c["group"] not in groups:
                break
        groups.add(c["group"])
        out.append(dict(c, difficulty=diff, xp=CONTRACT_XP))
    return out


def mode_matches(c, mode):
    words = c.get("mode")
    if not words:
        return True
    mode = str(mode or "").lower()
    return any(w in mode for w in words)


def contract_amount(c, stats, mode, ranked):
    """What one match adds to contract c (stats: the match's per-player STATS dict)."""
    if c.get("ranked") and not ranked:
        return 0
    if not mode_matches(c, mode):
        return 0
    if "count" in c:
        return 1 if (stats.get(c["count"]) or 0) >= c["atLeast"] else 0
    return sum(int(stats.get(k) or 0) for k in c["sum"])


# Same verifier as tools/accounts/tcp_accounts.py (copied: the VPS stats code is deployed on its own).
# ----------------------------------------------------------------------------- Ed25519 verify (RFC 8032)

_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _padd(a, b):
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    A = (y1 - x1) * (y2 - x2) % _P
    B = (y1 + x1) * (y2 + x2) % _P
    C = 2 * t1 * t2 * _D % _P
    D = 2 * z1 * z2 % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _pmul(s, p):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _padd(q, p)
        p = _padd(p, p)
        s >>= 1
    return q


def _pequal(a, b):
    x1, y1, z1, _ = a
    x2, y2, z2, _ = b
    return (x1 * z2 - x2 * z1) % _P == 0 and (y1 * z2 - y2 * z1) % _P == 0


def _recover_x(y, sign):
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


def _pdecompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % _P)


_GY = 4 * pow(5, _P - 2, _P) % _P
_G = (_recover_x(_GY, 0), _GY, 1, _recover_x(_GY, 0) * _GY % _P)


def ed25519_verify(public: bytes, msg: bytes, sig: bytes) -> bool:
    if len(public) != 32 or len(sig) != 64:
        return False
    A = _pdecompress(public)
    R = _pdecompress(sig[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(sig[32:], "little")
    if s >= _L:
        return False
    h = int.from_bytes(hashlib.sha512(sig[:32] + public + msg).digest(), "little") % _L
    return _pequal(_pmul(s, _G), _padd(R, _pmul(h, A)))


# ---------------------------------------------------------------------------- solo boards

SOLO_BOARDS = {
    "range": {"name": "Range Run", "unit": "ms", "better": "low", "targets": 20, "missPenaltyMs": 500},
    "drill": {"name": "Accuracy Drill", "unit": "points", "better": "high", "seconds": 60},
    "bots": {"name": "Weekly Bot Challenge", "unit": "ms", "better": "low"},
}
RANGE_WEAPONS = ["M4", "AK-47", "MP5/10", "SG 552", "Glock 19", "Desert Eagle"]   # game display names
# bots = bot clients in the match (5 v 5 with one human = 9); rounds = tcp_native_rounds the launcher starts the
# match with (2 Team Elimination, 6 Bomb); the game records map, mode (tcp_mode), bots and bot_skill
BOT_CHALLENGES = [
    {"map": "obj_village", "mode": "bomb", "rounds": 6, "bots": 9, "minSkill": 4, "rule": "any", "text": "Village Bomb, 5 v 5 against hard bots"},
    {"map": "obj_railhouse", "mode": "team elimination", "rounds": 2, "bots": 9, "minSkill": 4, "rule": "any", "text": "Railhouse Team Elimination, 5 v 5 against hard bots"},
    {"map": "obj_snow", "mode": "bomb", "rounds": 6, "bots": 7, "minSkill": 5, "rule": "any", "text": "Snow Bomb, 4 v 4 against the hardest bots"},
    {"map": "obj_village", "mode": "team elimination", "rounds": 2, "bots": 5, "minSkill": 5, "rule": "any", "text": "Village Team Elimination, 3 v 3 against the hardest bots"},
]
MIN_HIT_GAP_MS = 120          # no human hits two separate pop-up targets faster than this, run after run
MAX_RUN_BYTES = 64 * 1024


def solo_week(key):
    """What this week's solo boards use: the Range Run weapon, the drill seed and the bot challenge."""
    i = _week_index(key)
    seed = int(hashlib.sha256(("tcp-solo:" + key).encode()).hexdigest()[:8], 16)
    return {"week": key, "rangeWeapon": RANGE_WEAPONS[i % len(RANGE_WEAPONS)], "seed": seed,
            "botChallenge": dict(BOT_CHALLENGES[i % len(BOT_CHALLENGES)])}


def run_message(raw):
    """The bytes a run is signed over: the run's own JSON text exactly as uploaded, after a fixed prefix."""
    return b"tcp-solo/1\n" + (raw.encode("utf-8") if isinstance(raw, str) else raw)


def check_run(run, week):
    """(score, None) for a believable run of this week, else (None, reason). Signature is checked by the caller."""
    if not isinstance(run, dict) or run.get("schema") != "tcp-solo/1":
        return None, "not a tcp-solo/1 run"
    board = run.get("board")
    if board not in SOLO_BOARDS:
        return None, "unknown board"
    if run.get("week") != week["week"]:
        return None, "not this week's run"
    if run.get("seed") != week["seed"]:
        return None, "wrong seed"
    shots = run.get("shots")
    if not isinstance(shots, list) or len(shots) > 2000:
        return None, "no shot log"
    times = []
    for s in shots:
        if not (isinstance(s, list) and len(s) == 3 and all(isinstance(x, int) for x in s)):
            return None, "bad shot entry"
        times.append(s)              # [t ms, target index or -1 for a miss, ring 0 body / 1 head]
    if any(b[0] < a[0] for a, b in zip(times, times[1:])):
        return None, "shots out of order"
    hits = [s for s in times if s[1] >= 0]
    if board == "range":
        if run.get("weapon") != week["rangeWeapon"]:
            return None, "wrong weapon for this week"
        need = SOLO_BOARDS["range"]["targets"]
        if sorted({h[1] for h in hits}) != list(range(need)):
            return None, "not every target was hit"
        first = {}
        for h in hits:
            first.setdefault(h[1], h[0])
        order = sorted(first.values())
        if any(b - a < MIN_HIT_GAP_MS for a, b in zip(order, order[1:])) or (order and order[0] < MIN_HIT_GAP_MS):
            return None, "target hits closer together than a human can manage"
        misses = sum(1 for s in times if s[1] < 0)
        return order[-1] + misses * SOLO_BOARDS["range"]["missPenaltyMs"], None
    if board == "drill":
        if times and times[-1][0] > SOLO_BOARDS["drill"]["seconds"] * 1000 + 500:
            return None, "longer than the drill"
        if len(hits) >= 2 and any(b[0] - a[0] < MIN_HIT_GAP_MS // 2 for a, b in zip(hits, hits[1:]) if a[1] != b[1]):
            return None, "target switches faster than a human can manage"
        if len(times) >= 40 and len(hits) == len(times):
            return None, "every shot hit"
        return sum(2 if h[2] == 1 else 1 for h in hits), None
    # bots
    ch = week["botChallenge"]
    if run.get("map") != ch["map"] or run.get("bots") != ch["bots"] or ch["mode"] not in str(run.get("mode", "")).lower():
        return None, "not this week's challenge"
    if not isinstance(run.get("skill"), int) or run["skill"] < ch["minSkill"]:
        return None, "bots too easy for this week's challenge"
    if not run.get("won"):
        return None, "challenge not won"
    ms = run.get("timeMs")
    if not isinstance(ms, int) or ms < 60000:
        return None, "impossible time"
    return ms, None
