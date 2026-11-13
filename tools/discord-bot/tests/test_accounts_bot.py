"""Bot 1.3.0: player accounts (role sync with badges, weekly report, looking for a squad, staff bans)."""

import asyncio
import datetime as dt
import types

import aiohttp
from aiohttp import web

from tcpbot.cogs import accounts, community
from tcpbot.sources import AccountsAPI, AccountsUnavailable
from test_flows import FakeBot, FakeChannel, make_cfg, run

TOKEN = "t" * 32
PID = "0123456789abcdef"


# ---------------------------------------------------------------- the HTTP client against a small fake service
def fake_service(seen):
    async def handle(request):
        seen.append((request.method, request.path_qs, request.headers.get("X-Accounts-Token")))
        if request.headers.get("X-Accounts-Token") != TOKEN and request.path.startswith("/internal/"):
            return web.json_response({"error": "Not found."}, status=404)
        if request.path == "/internal/roles":
            return web.json_response({"accounts": [{"discordId": "42", "name": "Gianni", "statsId": PID, "badges": ["clean"]}]})
        if request.path == "/internal/lookup":
            if request.query.get("discord") == "42":
                return web.json_response({"name": "Gianni", "statsId": PID})
            return web.json_response({"error": "No such account."}, status=404)
        if request.path == "/internal/ban":
            body = await request.json()
            return web.json_response({"ok": True, "ban": 7, "account": "Gianni", "keys": 2, "got": body})
        if request.path == "/api/account/lfs.json":
            return web.json_response({"players": [{"name": "Gianni", "note": "EU", "until": 2000000000}]})
        return web.json_response({"error": "Not found."}, status=404)
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handle)
    return app


def test_accounts_client_sends_token_and_reads_answers():
    async def go():
        seen = []
        runner = web.AppRunner(fake_service(seen))
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        async with aiohttp.ClientSession() as s:
            api = AccountsAPI(s, "http://127.0.0.1:%d" % port, TOKEN)
            roles = await api.roles()
            lfs = await api.lfs()
            found = await api.lookup(42)
            missing = await api.lookup(43)
            ban = await api.ban(discord_id=42, reason="aimbot", days=0, by="staff")
            bad = AccountsAPI(s, "http://127.0.0.1:%d" % port, "wrong")
            try:
                await bad.roles()
                refused = False
            except AccountsUnavailable:
                refused = True
            off = AccountsAPI(s, "http://127.0.0.1:%d" % port, "")
            try:
                await off.roles()
                off_refused = False
            except AccountsUnavailable:
                off_refused = True
        await runner.cleanup()
        return seen, roles, lfs, found, missing, ban, refused, off_refused
    seen, roles, lfs, found, missing, ban, refused, off_refused = run(go())
    assert roles[0]["statsId"] == PID and lfs[0]["name"] == "Gianni"
    assert found["name"] == "Gianni" and missing is None
    assert ban["got"] == {"discord": "42", "name": "", "kind": "ban", "reason": "aimbot", "days": 0, "by": "staff"}
    assert refused and off_refused
    assert all(tok == TOKEN for m, path, tok in seen if path.startswith("/internal/") and tok != "wrong")
    assert len([1 for s in seen if s[2] == ""]) == 0          # no token: nothing is sent at all


# ---------------------------------------------------------------- weekly report
class FakeUser:
    def __init__(self, uid, closed=False):
        self.id, self.closed, self.got = uid, closed, []

    async def send(self, **kwargs):
        if self.closed:
            raise _forbidden()
        self.got.append(kwargs)


def _forbidden():
    import discord
    return discord.Forbidden(types.SimpleNamespace(status=403, reason="closed"), "Cannot send messages to this user")


class FakeAccounts:
    ready = True

    def __init__(self, weekly=None, lfs=None, roles=None):
        self._weekly, self._lfs, self._roles = weekly or [], lfs or [], roles or []
        self.calls = 0

    async def weekly(self):
        return self._weekly

    async def lfs(self):
        self.calls += 1
        return self._lfs

    async def roles(self):
        return self._roles


class FakeStats:
    def __init__(self, weeks):
        self.weeks = weeks

    async def week(self, pid):
        return self.weeks.get(pid)


def _week(matches):
    return {"week": {"matches": matches, "wins": 2, "kills": 30, "deaths": 20, "kd": 1.5, "headshots": 9, "xp": 900,
                     "timePlayed": 3600, "rating": 14},
            "before": {"matches": 1, "kills": 10, "kd": 1.0},
            "best": {"id": "fedcba9876543210", "kills": 12, "deaths": 3, "won": True},
            "newMedals": [{"key": "kills_100", "name": "Rifleman"}]}


def test_weekly_report_once_a_week_only_to_players_who_played(monkeypatch):
    cfg = make_cfg()
    bot = FakeBot(cfg, {})
    users = {1: FakeUser(1), 2: FakeUser(2), 3: FakeUser(3, closed=True)}
    bot.get_user = users.get
    bot.accounts = FakeAccounts(weekly=[{"discordId": "1", "name": "A", "statsId": "a" * 16},
                                        {"discordId": "2", "name": "B", "statsId": "b" * 16},
                                        {"discordId": "3", "name": "C", "statsId": "c" * 16}])
    bot.stats = FakeStats({"a" * 16: _week(5), "b" * 16: _week(0), "c" * 16: _week(3)})
    cog = accounts.Accounts.__new__(accounts.Accounts)
    cog.bot, cog.cfg = bot, cfg
    monkeypatch.setattr(accounts.asyncio, "sleep", _no_sleep)
    sunday = dt.datetime(2026, 11, 15, 20, 0, tzinfo=dt.timezone.utc)
    assert run(cog.check_weekly(sunday)) == 0                      # not Monday yet
    monday_early = dt.datetime(2026, 11, 16, 10, 0, tzinfo=dt.timezone.utc)
    assert run(cog.check_weekly(monday_early)) == 0                # Monday before 19:00 Belgian time
    monday = dt.datetime(2026, 11, 16, 18, 30, tzinfo=dt.timezone.utc)   # 19:30 in Brussels
    assert run(cog.check_weekly(monday)) == 1
    assert len(users[1].got) == 1 and not users[2].got and not users[3].got
    e = users[1].got[0]["embed"]
    assert "A" in e.title and any(f.name == "New medals" and "Rifleman" in f.value for f in e.fields)
    assert e.url.endswith("/player?id=" + "a" * 16)
    assert run(cog.check_weekly(monday)) == 0                      # once per week
    assert len(users[1].got) == 1


async def _no_sleep(_s):
    return None


# ---------------------------------------------------------------- looking for a squad board
def test_lfs_board_posts_once_then_edits_only_on_change():
    cfg = make_cfg(channels={"status": 10, "lfs": 50})
    ch = FakeChannel(50)
    bot = FakeBot(cfg, {50: ch})
    bot.accounts = FakeAccounts(lfs=[])
    cog = accounts.Accounts.__new__(accounts.Accounts)
    cog.bot, cog.cfg = bot, cfg
    run(cog.refresh_lfs())
    assert len(ch.sent) == 1 and "Nobody right now" in ch.sent[0].kwargs["embed"].description
    run(cog.refresh_lfs())                                         # unchanged
    assert len(ch.edits) == 0
    bot.accounts._lfs = [{"name": "Gi anni", "note": "@everyone EU nights [free](https://evil.example)", "until": 2000000000}]
    run(cog.refresh_lfs())
    assert len(ch.edits) == 1
    desc = ch.edits[0][1]["embed"].description
    assert "Gi anni" in desc and "@\u200beveryone" in desc and "<t:2000000000:t>" in desc
    assert "/u/Gi%20anni)" in desc                                 # the profile link survives a space
    assert "[free](" not in desc and "\\[free\\]" in desc            # a note cannot post a link
    ch.deleted.add(ch.sent[0].id)
    bot.accounts._lfs = []
    run(cog.refresh_lfs())                                         # board deleted: posted again
    assert len(ch.sent) == 2


# ---------------------------------------------------------------- role sync with badges
class FakeRole:
    def __init__(self, rid):
        self.id, self.members = rid, []


class FakeMember:
    def __init__(self, uid, roles=()):
        self.id, self.roles = uid, list(roles)

    async def add_roles(self, *roles, reason=""):
        self.roles += list(roles)

    async def remove_roles(self, *roles, reason=""):
        self.roles = [r for r in self.roles if r not in roles]


class FakeGuild:
    def __init__(self, roles, members):
        self.roles, self.members = roles, members

    def get_role(self, rid):
        return self.roles.get(rid)

    def get_member(self, uid):
        return self.members.get(uid)


ROLE_IDS = {"verified": 101, "top10": 102, "clean": 103, "trusted": 104, "tier_recruit": 105}


def _role_bot(accounts_api):
    cfg = make_cfg()
    bot = FakeBot(cfg, {})
    roles = {rid: FakeRole(rid) for rid in ROLE_IDS.values()}
    bot.store.set("roles", ROLE_IDS)
    bot.role_id = lambda key: ROLE_IDS.get(key, 0)
    bot.accounts = accounts_api

    class Stats:
        async def player(self, pid, fresh=False):
            return {"name": "Gianni", "rank": {"level": 1}}

        async def leaderboard(self, *a, **k):
            return {"players": []}
    bot.stats = Stats()
    return bot, roles


def test_account_badges_become_roles_and_go_away_with_the_badge(monkeypatch):
    api = FakeAccounts(roles=[{"discordId": "42", "name": "Gianni", "statsId": PID, "badges": ["clean", "trusted"]}])
    bot, roles = _role_bot(api)
    m = FakeMember(42)
    bot.guild = FakeGuild(roles, {42: m})
    cog = community.Community.__new__(community.Community)
    cog.bot, cog.cfg, cog.account_links = bot, bot.cfg, {}
    monkeypatch.setattr(community.asyncio, "sleep", _no_sleep)
    run(cog.sync_all_roles())
    have = {r.id for r in m.roles}
    assert {101, 103, 104} <= have                     # verified through the account, both badges
    api._roles = [{"discordId": "42", "name": "Gianni", "statsId": PID, "badges": []}]
    for r in m.roles:
        roles[r.id].members.append(m)
    run(cog.sync_all_roles())
    have = {r.id for r in m.roles}
    assert 103 not in have and 104 not in have and 101 in have


def test_badge_roles_stay_while_the_account_service_is_down(monkeypatch):
    class Down(FakeAccounts):
        async def roles(self):
            raise AccountsUnavailable("down")
    bot, roles = _role_bot(Down())
    m = FakeMember(42, [roles[103]])                   # has the Clean record role, not linked in the bot itself
    roles[103].members.append(m)
    bot.guild = FakeGuild(roles, {42: m})
    cog = community.Community.__new__(community.Community)
    cog.bot, cog.cfg, cog.account_links = bot, bot.cfg, {}
    monkeypatch.setattr(community.asyncio, "sleep", _no_sleep)
    run(cog.sync_all_roles())
    assert roles[103] in m.roles


def test_weekly_embed_reads_well_without_extras():
    cfg = make_cfg()
    w = {"week": {"matches": 1, "wins": 0, "kills": 0, "deaths": 1, "kd": 0.0, "headshots": 0, "xp": 25, "timePlayed": 600,
                  "rating": 0}, "before": {}, "best": None, "newMedals": []}
    e = accounts.weekly_embed(cfg, "^1Red^7Name", PID, w)
    assert "^" not in e.title and "1** match," in e.description
    assert [f.name for f in e.fields][:3] == ["Kills", "K/D", "Rating"]
