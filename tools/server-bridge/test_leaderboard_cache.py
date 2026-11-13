"""Leaderboard cache: a repeated board comes from the cache, any write starts a fresh one, the TTL expires it."""
import sys
import tcp_stats

checks = 0


def check(cond, what):
    global checks
    checks += 1
    print(("PASS " if cond else "FAIL ") + what)
    if not cond:
        sys.exit(1)


s = tcp_stats.StatsStore(":memory:", min_matches=1)
calls = []
real = s._leaderboard
s._leaderboard = lambda *a, **k: (calls.append(a), real(*a, **k))[1]
a = s.leaderboard(period="all", sort="kills")
b = s.leaderboard(period="all", sort="kills")
check(len(calls) == 1, "second identical board served from the cache")
check(a == b and a is not b, "cached board is an equal copy, not a shared object")
b["players"].append({"x": 1})
check(s.leaderboard(period="all", sort="kills")["players"] == a["players"], "caller changes do not leak into the cache")
s.leaderboard(period="7d", sort="kills")
check(len(calls) == 2, "different query builds its own board")
s.db.execute("INSERT INTO voided(kind, id, reason, created) VALUES('player', 'x', 'test', '2026-11-13')")
s.leaderboard(period="all", sort="kills")
check(len(calls) == 3, "a write through the store invalidates the cache")
s.LEADERBOARD_TTL = 0.0
s.leaderboard(period="all", sort="kills")
check(len(calls) == 4, "an expired entry is rebuilt")
print(f"{checks}/{checks} checks passed")
