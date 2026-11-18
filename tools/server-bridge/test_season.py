#!/usr/bin/env python3
"""Seasons (0.40.0): season rating with soft reset, tiers with hysteresis, weekly contracts, double XP, the launch-week
badge, ranks.txt for game servers, the new routes and signed solo (practice) runs."""
import datetime as dt
import hashlib
import json
import pathlib
import sys
import tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tcp_season as S
import tcp_stats

checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)))


# ------------------------------------------------------------------ pure rules
check("new player lands at Operator", S.tier_for(1000, 1) == 3)
check("cut-offs", [S.tier_for(r, 20) for r in (700, 850, 949, 950, 1050, 1150, 1250, 1350, 1450)] == [1, 2, 2, 3, 4, 5, 6, 7, 8])
check("Platinum needs 10 matches", S.tier_for(1500, 9) == 7 and S.tier_for(1500, 10) == 8)
check("no drop within 25 points", S.tier_for(1030, 20, prev=4) == 4 and S.tier_for(1024, 20, prev=4) == 3)
check("climbing ignores the margin", S.tier_for(1150, 20, prev=4) == 5)
check("soft reset halves the distance", S.soft_reset(1300) == 1150 and S.soft_reset(800) == 900)
check("progress in the band", S.tier_progress(1000, 3) == 50 and S.tier_progress(1600, 8) == 99 and S.tier_progress(800, 1) == 50)
check("tier names", [t["name"] for t in S.tiers_json()] == ["Rookie", "Contender", "Operator", "Veteran", "Elite", "Vanguard",
                                                               "Spearhead", "Platinum"])
check("default Season 1 dates", S.DEFAULT_SEASONS[0]["start"] == "2027-02-05T17:00:00Z" and S.DEFAULT_SEASONS[0]["end"] == "2027-05-07T16:00:00Z")
check("launch Friday is in week 2027-W05", S.week_key("2027-02-05T17:00:00Z") == "2027-W05")
check("week opens Monday 00:00 Brussels", S.iso(S.week_bounds("2027-W05")[0]) == "2027-01-31T23:00:00Z")
check("summer-time week", S.iso(S.week_bounds("2027-W14")[0]) == "2027-04-04T22:00:00Z")
weeks = [S.contracts_for_week("2027-W%02d" % w) for w in range(5, 30)]
check("three contracts a week, one per difficulty", all([c["difficulty"] for c in w] == ["easy", "medium", "hard"] for w in weeks))
check("never two of one kind in a week", all(len({c["group"] for c in w}) == 3 for w in weeks))
check("the set changes every week", len({tuple(c["id"] for c in w) for w in weeks}) >= 8)
c = {"sum": ["roundsWon"], "mode": ["bomb", "objective"]}
check("mode filter", S.contract_amount(c, {"roundsWon": 4}, "Bomb", True) == 4 and S.contract_amount(c, {"roundsWon": 4}, "Team elimination", True) == 0)
check("ranked-only contract", S.contract_amount({"sum": ["wins"], "ranked": True}, {"wins": 1}, "x", False) == 0)
check("count contract", S.contract_amount({"count": "longestKill", "atLeast": 40}, {"longestKill": 41}, "x", True) == 1)

# ------------------------------------------------------------------ store
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
START = NOW - dt.timedelta(days=3)
SEASON = {"id": "s1", "number": 1, "name": "Season 1", "start": S.iso(START), "end": S.iso(NOW + dt.timedelta(days=80)),
          "xpMultiplier": [{"start": S.iso(START), "end": S.iso(START + dt.timedelta(days=1)), "factor": 2}],
          "badges": [{"id": "frontline", "name": "Frontline", "start": S.iso(START), "end": S.iso(START + dt.timedelta(days=2))}]}
G = {n: c * 32 for n, c in (("Ana", "A"), ("Ben", "B"), ("Cas", "C"), ("Dio", "D"))}
pid = {n: tcp_stats.player_id(G[n]) for n in G}


def report(n, when, ranked=True, win="specops", kills=None, mode="Bomb"):
    ended = S.iso(when)
    players = [{"guid": G[nm], "name": nm, "team": t, "kills": 0, "deaths": 0, "headshots": 0, "damage": 900, "damageTaken": 500,
                "roundsWon": 6 if t == win else 4, "objectives": 0, "won": t == win, "timePlayed": 900, "idle": 0, "ip": ip,
                "hits": {"head": 1, "body": 3, "legs": 1},
                "weapons": {"M4": {"kills": 0, "headshots": 0, "shots": 40, "hits": 5, "time": 800, "longest": 0}}}
               for nm, t, ip in zip(G, ["specops", "specops", "terrorists", "terrorists"], ["a1", "b2", "c3", "d4"])]
    return {"schema": "tcp-match/2", "id": "s-%03d" % n, "server": "Official #1 Ranked", "map": "obj_village", "mode": mode,
            "practice": False, "cheats": False, "started": ended, "ended": ended, "duration": 900, "rounds": 10, "winner": win,
            "eac": {"start": 2, "end": 2, "min": 2}, "password": False, "ranked": ranked, "botSeconds": 0, "maxBots": 0,
            "players": players, "kills": kills or [], "events": []}


tmp = pathlib.Path(tempfile.mkdtemp())
store = tcp_stats.StatsStore(str(tmp / "s.db"), min_matches=1, require_anticheat=True, seasons=[SEASON])
store.clock = lambda: NOW

# before the season: Ana climbs to 1100+ all-time
for i in range(6):
    store.ingest(report(i, START - dt.timedelta(days=5, minutes=-i)), "official1")
career = store.player(pid["Ana"])["rating"]
check("career rating moved before the season", career > 1050, career)
check("no season data before the season", "season" not in store.player(pid["Ana"]))
week0_xp = store.player(pid["Ana"])["rank"]["xp"]

# first season match (double XP window)
store.ingest(report(10, START + dt.timedelta(hours=1)), "official1")
sp = store.player(pid["Ana"])["season"]
reset = S.soft_reset(store.db.execute("SELECT rating_before FROM match_players WHERE match='s-010' AND pid=?", (pid["Ana"],)).fetchone()[0])
row = store.db.execute("SELECT rating FROM season_players WHERE pid=?", (pid["Ana"],)).fetchone()[0]
check("season rating starts from the soft reset", reset < row < reset + 41, (reset, row))
check("tier after one ranked match", sp["tier"] == S.tier_for(row, 1) and sp["tierName"] and sp["emblem"].startswith("rank") and sp["season"] == "s1", sp)
mp = store.db.execute("SELECT xp FROM match_players WHERE match='s-010' AND pid=?", (pid["Ana"],)).fetchone()[0]
base = tcp_stats.match_xp({"kills": 0, "headshots": 0, "roundsWon": 6, "objectives": 0, "won": True, "timePlayed": 900, "teamKills": 0}, 900)
check("double XP in launch week", mp >= 2 * base, (mp, base))

# losers: Cas lost everything before, so the reset lifts them
cas = store.player(pid["Cas"])["season"]
check("loser's season rating is above the career rating (reset towards 1000)",
      store.db.execute("SELECT rating FROM season_players WHERE pid=?", (pid["Cas"],)).fetchone()[0] > store.player(pid["Cas"])["rating"])

# unranked match: season XP but no rating move
before = store.db.execute("SELECT rating, xp FROM season_players WHERE pid=?", (pid["Dio"],)).fetchone()
store.ingest(report(11, START + dt.timedelta(days=1, hours=2), ranked=False, mode="Team elimination"), "official2")
after = store.db.execute("SELECT rating, xp, matches FROM season_players WHERE pid=?", (pid["Dio"],)).fetchone()
check("unranked: season XP, same season rating", after[0] == before[0] and after[1] > before[1], (tuple(before), tuple(after)))

# contracts: this week's set and progress
week = S.week_key(NOW)
cs = store.contracts(pid["Ana"])
check("contracts route", cs and cs["week"] == week and len(cs["contracts"]) == 3, cs)
easy = cs["contracts"][0]
check("easy contract has progress", easy["progress"] >= 0)

# drive enough matches to finish every contract that matches can finish
for i in range(20, 32):
    store.ingest(report(i, NOW - dt.timedelta(hours=1, minutes=-i)), "official1")
done = [c for c in store.contracts(pid["Ana"])["contracts"] if c["done"]]
print("  this week:", [(c["id"], c["progress"], c["target"], bool(c["done"])) for c in store.contracts(pid["Ana"])["contracts"]])
check("contract finished by play", any(c["id"].startswith(("e-play", "e-rounds", "m-wins", "m-bomb", "e-dam", "h-rwins")) for c in done)
      or not any(c["id"].startswith(("e-play", "e-rounds", "m-wins", "m-bomb", "e-dam", "h-rwins"))
                 for c in store.contracts(pid["Ana"])["contracts"]), store.contracts(pid["Ana"]))
xp_rows = store.db.execute("SELECT SUM(xp) FROM match_players WHERE pid=? AND ended >= ?", (pid["Ana"], S.iso(START))).fetchone()[0]
plain = sum(tcp_stats.match_xp({"kills": 0, "headshots": 0, "roundsWon": r[0], "objectives": 0, "won": bool(r[1]), "timePlayed": 900,
                                "teamKills": 0}, 900) * S.xp_factor(SEASON, r[2])
            for r in store.db.execute("SELECT rounds_won, won, ended FROM match_players WHERE pid=? AND ended >= ?", (pid["Ana"], S.iso(START))))
check("contract XP added on top of match XP", xp_rows == plain + S.CONTRACT_XP * len(done) * 1
      + (S.CONTRACT_BONUS_XP if len(done) == 3 else 0), (xp_rows, plain, len(done)))

# Ana keeps winning: tier climbs; peak kept
sp = store.player(pid["Ana"])["season"]
check("winner climbed", sp["tier"] >= 4 and sp["peakTier"] >= sp["tier"], sp)
check("loser dropped", store.player(pid["Cas"])["season"]["tier"] <= 2, store.player(pid["Cas"])["season"])

# recompute gives the same season state
snap = [tuple(r) for r in store.db.execute("SELECT * FROM season_players ORDER BY pid")]
csnap = [tuple(r) for r in store.db.execute("SELECT * FROM contract_progress ORDER BY pid, cid")]
store.recompute()
check("recompute rebuilds seasons identically", snap == [tuple(r) for r in store.db.execute("SELECT * FROM season_players ORDER BY pid")])
check("recompute rebuilds contracts identically", csnap == [tuple(r) for r in store.db.execute("SELECT * FROM contract_progress ORDER BY pid, cid")])

# season route
ss = store.season()
check("season route", ss["state"] == "live" and ss["season"]["id"] == "s1" and pid["Ana"] in [p["id"] for p in ss["players"][:2]]
      and ss["players"][0]["tierName"] and ss["players"][0]["name"] in G and len(ss["tiers"]) == 8 and len(ss["week"]["contracts"]) == 3, json.dumps(ss)[:300])
code, body = tcp_stats.handle_get(store, "/season.json", {})
check("GET /season.json", code == 200 and body["schema"] == "tcp-season/1")
code, body = tcp_stats.handle_get(store, "/contracts.json", {"id": [pid["Ben"]]})
check("GET /contracts.json", code == 200 and body["player"] == pid["Ben"])

# Frontline badge and ranks.txt
fl = store.frontline()
check("profile lists the badge", store.player(pid["Ana"])["seasonBadges"] == ["frontline"])
check("Frontline for everyone in the badge window", all("frontline" in fl.get(pid[n], []) for n in G), fl)
rk = tmp / "ranks.txt"
n = store.export_ranks(rk)
lines = rk.read_text().splitlines()
check("ranks.txt header", lines[0].startswith("TCPRANKS1 ") and lines[0].endswith(" s1"), lines[0])
ana_line = next(x for x in lines if x.startswith(pid["Ana"]))
f = ana_line.split()
check("ranks.txt line: pid tier progress badges", int(f[1]) == store.player(pid["Ana"])["season"]["tier"] and 0 <= int(f[2]) <= 99
      and f[3] == "frontline", ana_line)

# ------------------------------------------------------------------ solo runs (signed with an identity key)
L, P = S._L, S._P


def keypair(seed):
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little") & ((1 << 254) - 8) | (1 << 254)
    A = S._pmul(a, S._G)
    return a, h[32:], _compress(A)


def _compress(Pt):
    x, y, z, _ = Pt
    zi = pow(z, P - 2, P)
    x, y = x * zi % P, y * zi % P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def sign(a, prefix, pub, msg):
    r = int.from_bytes(hashlib.sha512(prefix + msg).digest(), "little") % L
    R = _compress(S._pmul(r, S._G))
    h = int.from_bytes(hashlib.sha512(R + pub + msg).digest(), "little") % L
    return R + int.to_bytes((r + h * a) % L, 32, "little")


a, prefix, pub = keypair(b"ana-test-key")
setup = S.solo_week(S.week_key(NOW))


def run(board="range", gap=300, misses=1, **kw):
    shots = []
    t = 0
    for i in range(20):
        t += gap
        if i < misses:
            shots.append([t - 50, -1, 0])
        shots.append([t, i, 0])
    r = {"schema": "tcp-solo/1", "board": board, "week": setup["week"], "seed": setup["seed"], "weapon": setup["rangeWeapon"],
         "version": "0.40.0", "name": "Ana", "shots": shots}
    r.update(kw)
    raw = json.dumps(r)
    return {"run": raw, "key": pub.hex(), "sig": sign(a, prefix, pub, S.run_message(raw)).hex()}


good = run()
status, info = store.solo_submit(good)
check("signed range run stored", status == "stored" and info["score"] == 20 * 300 + 500, info)
for name, bad, why in (("forged signature", dict(run(gap=310), sig="00" * 64), "signature"),
                       ("tampered run after signing", dict(good, run=good["run"].replace("300", "100", 1)), "signature"),
                       ("inhuman target gaps", run(gap=60), "human"),
                       ("wrong weapon", run(gap=320, weapon="Knife"), "weapon"),
                       ("old week's seed", run(gap=330, seed=setup["seed"] + 1), "seed")):
    try:
        store.solo_submit(bad)
        check(name + " refused", False)
    except tcp_stats.Rejected as exc:
        check(name + " refused", why in str(exc), exc)
try:
    store.solo_submit(run(gap=350))
    check("one run a minute", False)
except tcp_stats.Rejected as exc:
    check("one run a minute", "minute" in str(exc), exc)
board = store.solo("range")
kid = hashlib.sha256(pub).hexdigest()[:40]
check("range board", board["practice"] and board["players"][0]["id"] == tcp_stats.player_id("key:" + kid)
      and board["players"][0]["score"] == 6500, board)
store.void_run(info["id"])
check("voided run leaves the board", store.solo("range")["players"] == [])
ch = setup["botChallenge"]
store.clock = lambda: NOW + dt.timedelta(minutes=5)
bot_run = run(board="bots", map=ch["map"], mode=ch["mode"].title(), bots=ch["bots"], skill=ch["minSkill"], won=True, timeMs=600000)
status, info = store.solo_submit(bot_run)
check("bot challenge win stored", status == "stored" and info["score"] == 600000, info)
store.clock = lambda: NOW + dt.timedelta(minutes=7)
try:
    store.solo_submit(run(board="bots", map=ch["map"], mode=ch["mode"], bots=ch["bots"], skill=1, won=True, timeMs=500000))
    check("easy bots refused", False)
except tcp_stats.Rejected as exc:
    check("easy bots refused", "too easy" in str(exc), exc)
code, body = tcp_stats.handle_post(store, "/api/v1/solo", {}, b"{}")
check("POST /api/v1/solo refuses an unsigned run", code == 422, body)

failed = [n for n, ok in checks if not ok]
print("%d checks, %d failed" % (len(checks), len(failed)))
sys.exit(1 if failed else 0)
