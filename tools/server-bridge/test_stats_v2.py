#!/usr/bin/env python3
"""Detailed stats (tcp-match/2): integrity rules, real-player-only counting and the new stats routes."""
import json
import pathlib
import sys
import tempfile
import time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tcp_stats

checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)))


G = {n: c * 32 for n, c in (("Ana", "A"), ("Ben", "B"), ("Cas", "C"), ("Dio", "D"))}
H, B, HEAD, AIM, CROUCH = 0, 0, 1, 2, 4


def report(n, ranked=False, eac=(2, 2, 2), password=False, bots=300, kills=None, events=None, ips=None, **extra):
    ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 7200 + n * 60))
    ips = ips or ["a1", "b2", "c3", "d4"]
    names = ["Ana", "Ben", "Cas", "Dio"]
    teams = ["specops", "specops", "terrorists", "terrorists"]
    players = [{"guid": G[nm], "name": nm, "team": t, "kills": 99, "deaths": 0, "headshots": 0, "damage": 900, "damageTaken": 500,
                "roundsWon": 6 if t == "specops" else 4, "objectives": 0, "won": t == "specops", "timePlayed": 900,
                "idle": 0, "ip": ip, "hits": {"head": 10, "body": 30, "legs": 5},
                "weapons": {"M4": {"kills": 99, "headshots": 0, "shots": 400, "hits": 45, "time": 800, "longest": 0}}}
               for nm, t, ip in zip(names, teams, ips)]
    r = {"schema": "tcp-match/2", "id": "v2-%03d" % n, "server": "TrueCombat: Platinum | Official #2 Unranked (EU)",
         "map": "obj_village", "mode": "Team elimination", "practice": False, "cheats": False, "started": ended, "ended": ended,
         "duration": 900, "rounds": 10, "winner": "specops", "eac": dict(zip(("start", "end", "min"), eac)),
         "password": password, "ranked": ranked, "botSeconds": bots, "maxBots": 4 if bots else 0, "players": players,
         "kills": kills if kills is not None else [], "events": events if events is not None else []}
    r.update(extra)
    return r


# Round 1: Ana opens on Cas (headshot, aimed), Dio kills Ana, Ben trades Dio 1 s later; Ana's revenge comes in round 2.
KILLS = [
    [10000, 1, 0, 2, "M4", HEAD | AIM, 1200, [1]],
    [12000, 1, 3, 0, "AK-47", 0, 800, []],
    [13000, 1, 1, 3, "M4", CROUCH, 400, []],
    [40000, 2, 0, 3, "Knife", 0, 40, []],          # revenge? no: Dio killed Ana, so this IS revenge
    [41000, 2, 0, 2, "M4", AIM, 2000, []],         # double kill
    [42500, 2, 0, 1, "M4", 0, 500, []],            # team kill: never counted as a kill
]
EVENTS = [["o", 9000, 1, 2, "plant"], ["o", 20000, 1, 0, "defuse"], ["r", 21000, 1, "specops", 1, 1, 1],
          ["r", 50000, 2, "specops", -1, 0, 0]]

tmp = pathlib.Path(tempfile.mkdtemp())
store = tcp_stats.StatsStore(str(tmp / "s.db"), min_matches=1, require_anticheat=True)

st, info = store.ingest(report(1, kills=KILLS, events=EVENTS), "official2")
check("verified unranked match stored", st == "stored", info)
for name, rep, why in (("anti-cheat off at the start", report(2, eac=(0, 2, 0)), "anti-cheat"),
                       ("anti-cheat switched off mid-match", report(3, eac=(2, 2, 0)), "anti-cheat"),
                       ("join password", report(4, password=True), "password"),
                       ("one person on two clients is not two players", report(5, ips=["a1", "a1", "a1", "a1"]), "real players"),
                       ("old report without anti-cheat record", dict(report(6), schema="tcp-match/1"), "anti-cheat")):
    try:
        store.ingest(rep, "official2")
        check(name + " refused", False, "stored")
    except tcp_stats.Rejected as exc:
        check(name + " refused", why in str(exc), exc)

lone = report(7)
for p in lone["players"][1:]:
    p["timePlayed"] = 30
try:
    store.ingest(lone, "official2")
    check("one real player plus bots refused", False)
except tcp_stats.Rejected:
    check("one real player plus bots refused", True)

pid = {n: tcp_stats.player_id(G[n]) for n in G}
ana = store.totals(pid["Ana"])
check("kills come from human events, not the game's 99", ana["kills"] == 3, ana["kills"])
check("team kill kept out of kills", ana["teamKills"] == 0 or ana["kills"] == 3)
check("headshot and aimed kills", ana["headshots"] == 1 and ana["aimedKills"] == 2, ana)
check("opening kill", ana["openingKills"] == 2, ana["openingKills"])
check("double kill", ana["doubleKills"] == 1, ana)
check("revenge on Dio", ana["revenges"] == 1, ana["revenges"])
check("knife kill", ana["knifeKills"] == 1)
check("longest kill in metres", ana["longestKill"] == round(2000 * tcp_stats.UNIT_M), ana["longestKill"])
check("defuse counted", ana["defuses"] == 1)
ben = store.totals(pid["Ben"])
check("trade kill", ben["trades"] == 1, ben)
check("assist", ben["assists"] == 1, ben)
check("clutch 1v1", ben["clutches"] == 1 and ben["bestClutch"] == 1, ben)
check("crouch kill", ben["crouchKills"] == 1)
check("accuracy left out when bots played", ana["shots"] == 0 and ana["accuracy"] is None, ana["accuracy"])
check("hit locations kept with bots on", ana["hitsHead"] == 10 and ana["headHitRate"] == round(100 * 10 / 45, 1), ana)
cas = store.totals(pid["Cas"])
check("plant counted", cas["plants"] == 1)
check("deaths only from real players", cas["deaths"] == 2, cas["deaths"])
check("unranked match does not move rating", store.player(pid["Ana"])["rating"] == 1000)
check("unranked match earns XP", store.player(pid["Ana"])["rank"]["xp"] > 0)

# Ranked + bot-free match: rating moves and accuracy counts
st, _ = store.ingest(report(8, ranked=True, bots=0, kills=KILLS[:2]), "local")
check("ranked match moves rating", store.player(pid["Ana"])["rating"] > 1000)
ana = store.totals(pid["Ana"])
check("accuracy from the bot-free match", ana["shots"] == 400 and ana["accuracy"] == round(100 * 45 / 400, 1), ana)
check("ranked scope", store.totals(pid["Ana"], "ranked")["kills"] == 1, store.totals(pid["Ana"], "ranked")["kills"])
# report(1) was unranked=True default... make sure scope filtered
st, _ = store.ingest(report(9, ranked=False, kills=KILLS[:1]), "official2")
check("all scope sums both", store.totals(pid["Ana"])["kills"] == 5, store.totals(pid["Ana"])["kills"])

# farming: same address never counts, and only 10 kills on one opponent per match
farm = [[1000 * i, 1, 0, 2, "M4", 0, 300, []] for i in range(1, 16)]
store.ingest(report(10, ranked=False, kills=farm), "official2")
check("pair kill cap of 10", store.totals(pid["Ana"])["kills"] == 15, store.totals(pid["Ana"])["kills"])
same = report(11, ranked=False, kills=[[1000, 1, 0, 2, "M4", 0, 300, []]], ips=["a1", "b2", "a1", "d4"])
store.ingest(same, "official2")
check("same address kills ignored", store.totals(pid["Ana"])["kills"] == 15)

# routes
code, d = tcp_stats.handle_get(store, "/stats.json", {"id": [pid["Ana"]]})
check("stats.json", code == 200 and d["totals"]["kills"] == 15 and d["weapons"][0]["name"] == "M4" and d["maps"], d.get("maps"))
check("nemesis and favourite victim", d["nemesis"]["name"] == "Dio" and d["favouriteVictim"]["name"] == "Cas", (d["nemesis"], d["favouriteVictim"]))
check("activity and rating history", d["activity"] and len(d["ratingHistory"]) == 1)
code, b = tcp_stats.handle_get(store, "/statboard.json", {"stat": ["kills"]})
check("statboard kills", code == 200 and b["players"][0]["name"] == "Ana", b)
code, b = tcp_stats.handle_get(store, "/statboard.json", {"stat": ["kd"]})
check("ratio board needs a fair sample", code == 200 and b["players"] == [] and b["minimum"]["value"] == 25, b)
code, b = tcp_stats.handle_get(store, "/statboard.json", {"stat": ["kills"], "weapon": ["Knife"]})
check("weapon board", b["players"] and b["players"][0]["value"] == 1, b)
code, b = tcp_stats.handle_get(store, "/statboard.json", {"stat": ["kills"], "scope": ["ranked"]})
check("ranked board", b["players"][0]["value"] == 1, b)
code, b = tcp_stats.handle_get(store, "/statboard.json", {"stat": ["kills"], "map": ["obj_nowhere"]})
check("map filter", b["players"] == [], b)
code, h = tcp_stats.handle_get(store, "/h2h.json", {"a": [pid["Ana"]], "b": [pid["Cas"]]})
check("head to head", code == 200 and h["a"]["kills"] >= 12 and h["matchesAgainst"] >= 4, h)
check("no guids or addresses published", not any(G[n] in json.dumps(d) for n in G) and "a1" not in json.dumps(h))
code, rec = tcp_stats.handle_get(store, "/recent.json", {})
check("recent shows the server name and ranked flag", rec["matches"][0]["server"].startswith("TrueCombat") and "ranked" in rec["matches"][0])

# staff review and voids
flag = report(12, ranked=False, bots=0, kills=[[1000 * i, 1, 0, 3, "M4", HEAD, 300, []] for i in range(1, 11)] +
              [[20000 + 1000 * i, 1, 0, 2, "M4", HEAD, 300, []] for i in range(1, 11)])
flag["players"][0]["weapons"]["M4"].update(shots=60, hits=58)
store.ingest(flag, "official2")
rv = store.review_list()
check("impossible numbers go to review", any("accuracy" in r["reason"] for r in rv) and any("headshot" in r["reason"] for r in rv), rv)
pub = tcp_stats.match_pub("official2", "v2-012")
before = store.totals(pid["Ana"])["kills"]
store.void("match", pub, "test")
check("voided match removed from totals", store.totals(pid["Ana"])["kills"] == before - 20, store.totals(pid["Ana"])["kills"])
store.void("player", pid["Dio"])
check("voided player hidden", store.detail(pid["Dio"])["removed"] and all(p["id"] != pid["Dio"] for p in store.statboard("deaths")["players"]))
store.unvoid("player", pid["Dio"])
check("unvoid restores", any(p["id"] == pid["Dio"] for p in store.statboard("deaths")["players"]))

# the same two players alone, again and again
duo = tcp_stats.StatsStore(":memory:", min_matches=1, require_anticheat=True)
for n in range(6):
    r = report(100 + n, kills=[[1000, 1, 0, 2, "M4", 0, 300, []]])
    r["players"] = [r["players"][0], r["players"][2]]
    r["kills"] = [[1000, 1, 0, 1, "M4", 0, 300, []]]
    duo.ingest(r, "official2")
check("pair that keeps meeting alone is flagged", any("two-player" in x["reason"] for x in duo.review_list()), duo.review_list())

# a test store without the strict flag still takes old reports (development servers)
loose = tcp_stats.StatsStore(":memory:", min_matches=1)
st, _ = loose.ingest(dict(report(1), schema="tcp-match/1"), "local")
check("development store accepts tcp-match/1", st == "stored")

# staff portal routes: loopback, no proxy header, and the token; everything else looks like 404
SH = {"X-Staff-Token": "s3cret"}
code, r = tcp_stats.handle_staff(store, "GET", "/staff/review.json", SH, "127.0.0.1", b"", "s3cret")
check("staff route: code == 200 and isinstance(r['review'], list)", code == 200 and isinstance(r["review"], list))
check("staff route: tcp_stats.handle_staff(store, 'GET', '/staff/review.json', H", tcp_stats.handle_staff(store, "GET", "/staff/review.json", SH, "203.0.113.5", b"", "s3cret")[0] == 404)
check("staff route: tcp_stats.handle_staff(store, 'GET', '/staff/review.json', d", tcp_stats.handle_staff(store, "GET", "/staff/review.json", dict(SH, **{"X-Forwarded-For": "1.2.3.4"}), "127.0.0.1", b"", "s3cret")[0] == 404)
check("staff route: tcp_stats.handle_staff(store, 'GET', '/staff/review.json', {", tcp_stats.handle_staff(store, "GET", "/staff/review.json", {"X-Staff-Token": "nope"}, "127.0.0.1", b"", "s3cret")[0] == 404)
check("staff route: tcp_stats.handle_staff(store, 'GET', '/staff/review.json', H", tcp_stats.handle_staff(store, "GET", "/staff/review.json", SH, "127.0.0.1", b"", "")[0] == 404)
check("staff route: tcp_stats.handle_staff(store, 'GET', '/leaderboard.json', H,", tcp_stats.handle_staff(store, "GET", "/leaderboard.json", SH, "127.0.0.1", b"", "s3cret") is None)
code, r = tcp_stats.handle_staff(store, "POST", "/staff/void", SH, "127.0.0.1", json.dumps({"kind": "player", "id": pid["Ana"], "reason": "test"}).encode(), "s3cret")
check("staff route: code == 200 and r['ok']", code == 200 and r["ok"])
code, r = tcp_stats.handle_staff(store, "POST", "/staff/unvoid", SH, "127.0.0.1", json.dumps({"kind": "player", "id": pid["Ana"]}).encode(), "s3cret")
check("staff route: code == 200", code == 200)
check("staff route: tcp_stats.handle_staff(store, 'POST', '/staff/void', SH, '127", tcp_stats.handle_staff(store, "POST", "/staff/void", SH, "127.0.0.1", b'{"kind":"x","id":"1"}', "s3cret")[0] == 400)

# the match page's team score counts the reported round results, bots' rounds included
page = store.match(tcp_stats.match_pub("official2", "v2-001"))
check("team score from round results", page["score"] == {"specops": 2, "terrorists": 0}, page["score"])
page = store.match(tcp_stats.match_pub("official2", "v2-012"))
check("team score without round results falls back", page is None or page["score"] == {"specops": 6, "terrorists": 4},
      page and page["score"])
check("rivals of an unknown player is not found", store.rivals("f" * 16) is None)

ok = sum(1 for _, c in checks if c)

print("%d/%d checks passed" % (ok, len(checks)))
sys.exit(0 if ok == len(checks) else 1)
