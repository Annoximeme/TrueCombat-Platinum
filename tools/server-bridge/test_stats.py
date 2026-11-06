#!/usr/bin/env python3
"""Loopback test of the stats service: signed uploads, refusals, ranks, rating, profiles and the upload agent."""
import json, pathlib, sys, tempfile, threading, time, urllib.error, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tcp_stats, tcp_stats_agent

tmp = pathlib.Path(tempfile.mkdtemp())
store = tcp_stats.StatsStore(str(tmp / "stats.db"), min_matches=2)
sid, key = store.add_server("Red Server")
port = 18091
threading.Thread(target=tcp_stats.serve, args=(store, "127.0.0.1:%d" % port, "*"), daemon=True).start()
time.sleep(0.5)
URL = "http://127.0.0.1:%d" % port
G = {n: (c * 32) for n, c in (("Gianni", "A"), ("Bob", "B"), ("Cleo", "C"), ("Dax", "D"))}


def report(n, winner="specops", **extra):
    ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600 + n * 60))
    r = {"schema": "tcp-match/1", "id": "m%03d" % n, "server": "Red Server", "map": "obj_village", "mode": "Team Deathmatch",
         "practice": False, "cheats": False, "started": ended, "ended": ended, "duration": 600, "rounds": 1, "winner": winner,
         "players": [
             {"guid": G["Gianni"], "name": "^1Gianni", "team": "specops", "kills": 12, "deaths": 4, "headshots": 5, "roundsWon": 1,
              "won": winner == "specops", "timePlayed": 600, "weapons": {"M4": {"kills": 12, "headshots": 5, "shots": 300, "hits": 80}}},
             {"guid": G["Bob"], "name": "Bob", "team": "specops", "kills": 3, "deaths": 6, "won": winner == "specops", "timePlayed": 590},
             {"guid": G["Cleo"], "name": "Cleo", "team": "terrorists", "kills": 6, "deaths": 8, "won": winner == "terrorists", "timePlayed": 600,
              "weapons": {"AK-47": {"kills": 6, "shots": 200, "hits": 40}}},
             {"guid": G["Dax"], "name": "Dax", "team": "terrorists", "kills": 4, "deaths": 7, "teamKills": 1, "won": winner == "terrorists",
              "timePlayed": 300}]}
    r.update(extra)
    return r


def send(obj, server=sid, k=key, stamp=None, raw=None):
    body = raw if raw is not None else json.dumps(obj).encode()
    st, sig = tcp_stats.sign(k, body, stamp)
    req = urllib.request.Request(URL + "/api/v1/match", data=body, method="POST",
                                 headers={"X-TCP-Server": server, "X-TCP-Time": st, "X-TCP-Signature": sig})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get(path):
    with urllib.request.urlopen(URL + path) as r:
        return json.loads(r.read())


checks = []
def check(name, cond, detail=""):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)))

code, body = send(report(1)); check("signed upload stored", code == 200 and body["status"] == "stored", (code, body))
code, body = send(report(1)); check("same match again is a duplicate", code == 409, (code, body))
code, _ = send(report(2), k="00" * 32); check("wrong key refused", code == 401)
code, _ = send(report(2), server="nosuchserver"); check("unknown server refused", code == 401)
code, _ = send(report(2), stamp=time.time() - 3600); check("old timestamp refused", code == 401)
code, _ = send(report(2, cheats=True)); check("cheat match refused", code == 422)
code, _ = send(report(2, practice=True)); check("practice match refused", code == 422)
bad = report(2); bad["players"][0]["guid"] = "not-a-guid"
code, _ = send(bad); check("invalid guid refused", code == 422)
code, _ = send(report(2, duration=20)); check("too-short match refused", code == 422)
code, _ = send(None, raw=b"{nope"); check("garbage refused", code == 400)
for n in range(2, 6):
    send(report(n))
code, _ = send(report(6, winner="terrorists")); check("sixth match stored", code == 200)

lb = get("/leaderboard.json")
names = [p["name"] for p in lb["players"]]
check("leaderboard has 4 players, colours stripped", sorted(names) == ["Bob", "Cleo", "Dax", "Gianni"], names)
check("no guids published", all(G[n] not in json.dumps(lb) for n in G))
gianni = [p for p in lb["players"] if p["name"] == "Gianni"][0]
cleo = [p for p in lb["players"] if p["name"] == "Cleo"][0]
check("winning side rated above losing side", gianni["rating"] > 1000 > cleo["rating"], (gianni["rating"], cleo["rating"]))
check("totals add up", gianni["matches"] == 6 and gianni["kills"] == 72 and gianni["wins"] == 5, gianni)
check("XP rank assigned", gianni["rank"]["level"] >= 2 and gianni["rank"]["title"] == tcp_stats.RANKS[gianni["rank"]["level"] - 1][0], gianni["rank"])
check("sorted by rating", lb["players"][0]["rating"] == max(p["rating"] for p in lb["players"]))
check("top weapon", gianni["topWeapon"] == "M4", gianni)
k = get("/leaderboard.json?sort=kills")["players"]; check("sort by kills", k[0]["name"] == "Gianni")
check("30 day period", get("/leaderboard.json?period=30d")["matches"] == 6)
check("mode filter", get("/leaderboard.json?mode=Elimination")["players"] == [])

prof = get("/player.json?id=" + gianni["id"])
check("profile weapons and accuracy", prof["weapons"][0]["name"] == "M4" and abs(prof["weapons"][0]["accuracy"] - 80 * 6 / (300 * 6)) < 1e-3, prof["weapons"])
check("profile recent matches with rating change", len(prof["recent"]) == 6 and prof["recent"][0]["ratingChange"] < 0, prof["recent"][:1])
check("profile position", prof["position"] == [p["name"] for p in lb["players"]].index("Gianni") + 1)
try:
    get("/player.json?id=0000000000000000"); check("unknown player 404", False)
except urllib.error.HTTPError as e:
    check("unknown player 404", e.code == 404)
check("search", [p["name"] for p in get("/search.json?q=gia")["players"]] == ["Gianni"])
check("rank table", len(get("/ranks.json")["ranks"]) == 21)
check("recent matches", len(get("/recent.json")["matches"]) == 6)
dax = [p for p in lb["players"] if p["name"] == "Dax"][0]
before = {p["id"]: (p["rating"], p["rank"]["xp"]) for p in lb["players"]}
check("recompute gives the same result", store.recompute() == 6 and
      {p["id"]: (p["rating"], p["rank"]["xp"]) for p in get("/leaderboard.json")["players"]} == before)

store.set_server_active(sid, False)
code, _ = send(report(7)); check("disabled server refused", code == 401)
store.set_server_active(sid, True)

q = tmp / "queue"; q.mkdir()
(q / "a.json").write_text(json.dumps(report(8)))
(q / "b.json").write_text(json.dumps(report(9, cheats=True)))
old = time.time() - 10
import os
for f in q.iterdir():
    os.utime(f, (old, old))
res = tcp_stats_agent.run_once(q, URL, sid, key, log=lambda m: None)
check("agent sends and sorts reports", res == (1, 1, 0) and (q / "sent/a.json").exists() and (q / "rejected/b.json").exists(), res)
res = tcp_stats_agent.run_once(q, "http://127.0.0.1:9", sid, key, log=lambda m: None)
check("agent with nothing queued", res == (0, 0, 0))

failed = [n for n, ok in checks if not ok]
print("%d/%d checks passed" % (len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
