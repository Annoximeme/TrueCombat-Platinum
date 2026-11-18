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
    # the scoreboard is drawn as an image; the embed keeps the headline, MVP and unlocks
    assert "Player of the match" in names and "Special Ops" not in names
    f = ch.sent[0].kwargs["file"]
    assert f.filename == "match.png" and e.image.url == "attachment://match.png"
    assert f.fp.getvalue()[:8] == b"\x89PNG\r\n\x1a\n"
    bot.cfg["cards"]["enabled"] = False             # text fallback keeps the team tables
    bot.store.set("matches_seen", bot.store.get("matches_seen")[1:])
    run(cog.check_matches())
    e2 = ch.sent[-1].kwargs["embed"]
    assert "Special Ops" in [f.name for f in e2.fields] and "file" not in ch.sent[-1].kwargs
    bot.cfg["cards"]["enabled"] = True
    del ch.sent[2:]
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


# ------------------------------------------------------------ Season 1 (stats service seasons, game 0.40.0)
SEASON = {"schema": "tcp-season/1", "state": "live",
          "season": {"id": "s1", "number": 1, "name": "Season 1", "start": "2027-02-05T17:00:00Z", "end": "2027-05-07T16:00:00Z"},
          "week": {"id": "2027-W06", "contracts": [{"id": "e-play3", "text": "Play 3 matches"}, {"id": "m-hs5", "text": "Get 5 headshot kills"},
                                                   {"id": "h-long40", "text": "Get a kill from 40 m or more"}]},
          "players": [{"id": "a" * 16, "name": "Ana", "position": 1, "tier": 5, "tierName": "Elite", "rating": 1180, "wins": 7},
                      {"id": "b" * 16, "name": "Ben", "position": 2, "tier": 3, "tierName": "Operator", "rating": 990, "wins": 2}]}


class SeasonStats(LocalStats):
    def __init__(self, store, data):
        super().__init__(store)
        self.data = data

    async def season(self, fresh=False, season=""):
        return self.data


def test_official_season_replaces_calendar_seasons(stats):
    cog, bot, ch = make(stats)
    feb = dt.datetime(2027, 2, 1, 12, 0, tzinfo=dt.timezone.utc)
    run(cog.check_season(feb))                                 # older service: calendar month
    assert bot.store.get("season")["key"] == "2027-02"
    bot.stats = SeasonStats(stats, dict(SEASON))
    run(cog.check_season(feb + dt.timedelta(days=5)))          # Season 1 goes live: February's board closes
    assert bot.store.get("season")["key"] == "s1" and bot.store.get("season")["official"]
    e = embeds.season_tiers(cog.cfg, SEASON, bot.store.get("season"))
    check_embed(e)
    assert "Elite" in e.description and "Ana" in e.description
    assert any(f.name == "This week's contracts" and "headshot" in f.value for f in e.fields)
    sent = len(bot.channels[20].sent)
    run(cog.check_season(feb + dt.timedelta(days=6)))          # same season: nothing new
    assert len(bot.channels[20].sent) == sent
    bot.stats.data = dict(SEASON, state="ended")
    run(cog.check_season(dt.datetime(2027, 5, 8, tzinfo=dt.timezone.utc)))
    assert bot.store.get("season")["key"] == "s1-ended"
    final = bot.channels[20].sent[-1].kwargs["embed"]
    check_embed(final)
    assert "Season 1 · final standings" == final.title
    assert A.SEASON_KEY in bot.store.achievements("a" * 16)
    closed = [d for d in bot.store.docs("season") if d["key"] == "s1"]
    assert closed and closed[0]["top"][0]["tier"] == "Elite"
    n = len(bot.channels[20].sent)
    run(cog.check_season(dt.datetime(2027, 5, 9, tzinfo=dt.timezone.utc)))
    assert len(bot.channels[20].sent) == n                     # closed once


def test_official_season_upcoming_keeps_calendar(stats):
    cog, bot, ch = make(stats)
    bot.stats = SeasonStats(stats, dict(SEASON, state="upcoming"))
    assert run(cog.current(dt.datetime(2026, 12, 3, tzinfo=dt.timezone.utc)))["key"] == "2026-12"
