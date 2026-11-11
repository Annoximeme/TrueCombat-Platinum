"""Match reports, achievements, recap and seasons, fed by the real stats service code."""

import datetime as dt
import types

import pytest

from tcpbot import achievements as A
from tcpbot import embeds
from tcpbot.cogs import highlights
from tcpbot.sources import StatsUnavailable
from test_embeds import check as check_embed, cfg, stats  # noqa: F401  (fixtures)
from test_flows import FakeBot, FakeChannel, make_cfg, run


class LocalStats:
    """The bot's StatsAPI, answered straight from a StatsStore."""

    def __init__(self, store, old=False):
        self.s, self.old = store, old

    async def recent(self, fresh=False):
        r = self.s.recent()
        if self.old:
            for m in r["matches"]:
                m.pop("id")
        return r

    async def match(self, mid):
        return None if self.old else self.s.match(mid)

    async def player(self, pid, fresh=False):
        return self.s.player(pid)

    async def recap(self, days=7):
        return None if self.old else self.s.recap(days)

    async def leaderboard(self, sort="rating", period="all", limit=10, fresh=False, since="", until=""):
        b = self.s.leaderboard(period, sort, "", limit, since, until)
        if self.old:
            b.pop("since", None)
        return b


def make(stats, old=False, **extra):
    c = make_cfg(**extra)
    ch = FakeChannel(10)
    bot = FakeBot(c, {10: ch, 20: FakeChannel(20)})
    bot.stats = LocalStats(stats, old)
    cog = highlights.Highlights.__new__(highlights.Highlights)
    cog.bot, cog.cfg = bot, c
    return cog, bot, ch


def test_season_windows():
    now = dt.datetime(2026, 11, 11, 6, 0, tzinfo=dt.timezone.utc)
    m = highlights.season_window(now, "month")
    assert m["key"] == "2026-11" and m["name"] == "November 2026 season"
    assert m["since"] == "2026-10-31T23:00:00Z" and m["until"] == "2026-11-30T23:00:00Z"
    q = highlights.season_window(now, "quarter")
    assert q["key"] == "2026Q4" and q["until"] == "2026-12-31T23:00:00Z"
    edge = highlights.season_window(dt.datetime(2026, 12, 31, 23, 30, tzinfo=dt.timezone.utc), "month")
    assert edge["key"] == "2027-01"


def test_first_run_is_silent_then_new_matches_are_reported(stats):
    cog, bot, ch = make(stats)
    run(cog.check_matches())
    assert ch.sent == [] and len(bot.store.get("matches_seen")) == 12
    seen = bot.store.get("matches_seen")
    bot.store.set("matches_seen", seen[2:])          # pretend the two newest just finished
    run(cog.check_matches())
    assert len(ch.sent) == 2
    e = ch.sent[0].kwargs["embed"]
    check_embed(e)
    assert e.title.startswith("Match report") and "win" in e.description
    names = [f.name for f in e.fields]
    assert "Player of the match" in names and "Special Ops" in names and "Terrorists" in names
    run(cog.check_matches())
    assert len(ch.sent) == 2                          # nothing twice


def test_old_stats_service_gets_the_short_report(stats):
    cog, bot, ch = make(stats, old=True, match_reports={"min_players": 2})
    run(cog.check_matches())
    bot.store.set("matches_seen", bot.store.get("matches_seen")[1:])
    run(cog.check_matches())
    assert len(ch.sent) == 1
    check_embed(ch.sent[0].kwargs["embed"])


def test_achievements_backfill_quietly_and_announce_new(stats):
    cog, bot, ch = make(stats)
    newest = stats.recent()["matches"][0]
    detail = stats.match(newest["id"])
    first = run(cog.award(detail))
    assert all(k in A.MATCH for _n, k in first)       # 12 matches of history: career is recorded, not announced
    pid = detail["players"][0]["id"]
    have = bot.store.achievements(pid)
    assert "first_match" in have and "matches_10" in have
    assert run(cog.award(detail)) == []               # nothing is unlocked twice
    p = stats.player(pid)
    card = embeds.achievements_card(cog.cfg, p, have)
    check_embed(card)
    check_embed(embeds.profile(cog.cfg, p, None, have))


def test_achievement_rules():
    p = {"matches": 12, "wins": 10, "kills": 600, "headshots": 120, "rating": 1090, "peakRating": 1260,
         "timePlayed": 11 * 3600, "recent": [{"won": True}] * 3 + [{"won": False}]}
    got = set(A.career(p))
    assert got == {"first_match", "first_win", "matches_10", "wins_10", "kills_100", "kills_500", "headshots_100",
                   "rating_1100", "rating_1250", "hours_10", "streak_3"}
    board = [{"id": "a", "kills": 31, "deaths": 2, "headshots": 10, "objectives": 3, "won": True, "xp": 900},
             {"id": "b", "kills": 5, "deaths": 9, "won": True, "xp": 100},
             {"id": "c", "kills": 9, "deaths": 9, "won": False, "xp": 950},
             {"id": "d", "kills": 2, "deaths": 9, "won": False, "xp": 50}]
    assert set(A.in_match(board[0], board)) == {"match_20", "match_30", "match_hs10", "match_survivor", "match_objective"}
    assert A.in_match(board[2], board) == []          # top of the board, but lost
    assert all(len(v) == 3 for v in A.ALL.values())


def test_weekly_recap_once_a_week(stats, monkeypatch):
    cog, bot, ch = make(stats)
    monday = dt.datetime(2026, 11, 9, 18, 5, tzinfo=dt.timezone.utc)      # 19:05 in Brussels
    real = stats.recap

    def recap(days=7):                                # the fixture matches are from the 7th; keep them in range
        return real(92)
    monkeypatch.setattr(stats, "recap", recap)
    run(cog.check_recap(monday - dt.timedelta(days=1)))
    assert ch.sent == []
    run(cog.check_recap(monday))
    run(cog.check_recap(monday + dt.timedelta(hours=1)))
    assert len(ch.sent) == 1
    e = ch.sent[0].kwargs["embed"]
    check_embed(e)
    assert "12" in e.description and any(f.name == "Most kills" for f in e.fields)
    check_embed(embeds.weekly_recap(cog.cfg, {"days": 7, "matches": 0}))


def test_season_rolls_over_and_crowns(stats):
    cog, bot, ch = make(stats)
    nov = dt.datetime(2026, 11, 20, 12, 0, tzinfo=dt.timezone.utc)
    run(cog.check_season(nov))
    assert bot.store.get("season")["key"] == "2026-11" and ch.sent == []
    board = run(cog.season_standings(cog.season(nov)))
    e = embeds.season_board(cog.cfg, board, cog.season(nov))
    check_embed(e)
    assert "XP" in e.description
    run(cog.check_season(nov + dt.timedelta(days=15)))
    assert bot.store.get("season")["key"] == "2026-12"
    final = bot.channels[20].sent[0].kwargs["embed"]
    check_embed(final)
    assert "final standings" in final.title
    closed = bot.store.docs("season")
    assert closed[0]["key"] == "2026-11" and closed[0]["top"]
    assert A.SEASON_KEY in bot.store.achievements(closed[0]["top"][0]["id"])


def test_season_on_old_service(stats):
    cog, bot, ch = make(stats, old=True)
    with pytest.raises(Exception) as e:
        run(cog.season_standings(cog.season()))
    assert "next update" in str(e.value)
