#!/usr/bin/env python3
"""tcp_strip_ips.py: connection hashes leave reports after the retention time, and the stats stay identical."""
import json
import pathlib
import sqlite3
import sys
import tempfile
import time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tcp_stats
import tcp_strip_ips

# the report builder from test_stats_v2.py (that module runs its checks on import)
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


checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)))


def at(days_ago):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - days_ago * 86400))


tmp = pathlib.Path(tempfile.mkdtemp())
folder = tmp / "stats"
folder.mkdir()
old_shared = report(1, ips=["aaaaaaaaaaaa", "aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc"])   # Ana and Ben share an address
old_plain = report(2, ips=["dddddddddddd", "eeeeeeeeeeee", "ffffffffffff", "111111111111"])
new = report(3, ips=["dddddddddddd", "eeeeeeeeeeee", "ffffffffffff", "111111111111"])
for r, days in ((old_shared, 120), (old_plain, 95), (new, 10)):
    r["ended"] = r["started"] = at(days)
    (folder / (r["id"] + ".json")).write_text(json.dumps(r))

db_path = str(tmp / "stats.db")
st = tcp_stats.StatsStore(db_path)
st.import_dir(str(folder))
snap_before = sqlite3.connect(db_path).execute("SELECT pid, stat, SUM(value) FROM match_stats GROUP BY pid, stat ORDER BY 1, 2").fetchall()
check("stats were recorded", len(snap_before) > 0)

check("dry run changes nothing", tcp_strip_ips.main(["--db", db_path, "--dir", str(folder), "--dry-run"]) == 0
      and json.loads((folder / "v2-001.json").read_text())["players"][0]["ip"] == "aaaaaaaaaaaa")
tcp_strip_ips.main(["--db", db_path, "--dir", str(folder)])

f1 = [p["ip"] for p in json.loads((folder / "v2-001.json").read_text())["players"]]
f3 = [p["ip"] for p in json.loads((folder / "v2-003.json").read_text())["players"]]
check("old file: hashes replaced by per-match labels, shared address kept shared", f1 == ["1", "1", "2", "3"], f1)
check("recent file untouched", f3 == ["dddddddddddd", "eeeeeeeeeeee", "ffffffffffff", "111111111111"], f3)
con = sqlite3.connect(db_path)
stored = {mid: [p.get("ip") for p in json.loads(rep)["players"]] for mid, rep in con.execute("SELECT id, report FROM matches")}
check("old stored reports stripped in the database", stored["v2-001"] == ["1", "1", "2", "3"] and stored["v2-002"] == ["1", "2", "3", "4"], stored)
check("recent stored report untouched", stored["v2-003"][0] == "dddddddddddd", stored)
check("no old hash left anywhere", "aaaaaaaaaaaa" not in (folder / "v2-001.json").read_text()
      and not con.execute("SELECT 1 FROM matches WHERE id IN ('v2-001','v2-002') AND report LIKE '%dddddddddddd%'").fetchone())
con.close()

st.recompute()
snap_after = sqlite3.connect(db_path).execute("SELECT pid, stat, SUM(value) FROM match_stats GROUP BY pid, stat ORDER BY 1, 2").fetchall()
check("a full rebuild gives exactly the same stats", snap_before == snap_after)
st.import_dir(str(folder))
check("re-importing the rewritten files adds nothing", sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 3)
mt = (folder / "v2-002.json").stat().st_mtime
tcp_strip_ips.main(["--db", db_path, "--dir", str(folder)])
check("second run is a no-op", (folder / "v2-002.json").stat().st_mtime == mt
      and tcp_strip_ips.strip_db(db_path, time.time() - 90 * 86400, True) == 0
      and tcp_strip_ips.strip_dir(str(folder), time.time() - 90 * 86400, True) == 0)

failed = [n for n, ok in checks if not ok]
print("%d checks, %d failed" % (len(checks), len(failed)))
sys.exit(1 if failed else 0)
