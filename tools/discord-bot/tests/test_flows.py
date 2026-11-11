"""Behaviour of the background jobs, with Discord replaced by small fakes."""

import asyncio
import json
import pathlib
import tempfile
import time
import types

import discord
import pytest

from tcpbot import config
from tcpbot.cogs import community, linking, news, status
from tcpbot.store import Store

HERE = pathlib.Path(__file__).parent


class FakeMessage:
    def __init__(self, channel, mid, kwargs):
        self.channel, self.id, self.kwargs = channel, mid, kwargs
        self.jump_url = "https://discord.com/channels/1/%d/%d" % (channel.id, mid)

    async def edit(self, **kwargs):
        if self.id in self.channel.deleted:
            raise discord.NotFound(types.SimpleNamespace(status=404, reason="gone"), "Unknown Message")
        self.channel.edits.append((self.id, kwargs))

    async def publish(self):
        pass


class FakeChannel:
    def __init__(self, cid):
        self.id = cid
        self.mention = "<#%d>" % cid
        self.sent, self.edits, self.deleted = [], [], set()

    async def send(self, content=None, **kwargs):
        kwargs["content"] = content
        m = FakeMessage(self, 1000 + len(self.sent), kwargs)
        self.sent.append(m)
        return m

    def get_partial_message(self, mid):
        return FakeMessage(self, mid, {})


class FakeBot:
    def __init__(self, cfg, channels):
        self.cfg, self.store, self.channels = cfg, Store(), channels
        self.guild = None
        self.cogs = {}

    def text_channel(self, cid):
        return self.channels.get(int(cid or 0))

    def role(self, key):
        return None

    def role_id(self, key):
        return 0

    def get_cog(self, name):
        return self.cogs.get(name)

    def get_user(self, uid):
        return None

    def is_staff(self, member):
        return True

    async def set_presence(self, text):
        self.presence = text

    async def draw(self, name, fn, *args):
        from tcpbot.bot import TCPBot
        return await TCPBot.draw(self, name, fn, *args)


def make_cfg(**extra):
    raw = {"guild_id": 1, "channels": {"status": 10, "announcements": 20, "staff": 30, "events": 40}}
    raw.update(extra)
    p = pathlib.Path(tempfile.mkdtemp()) / "config.json"
    p.write_text(json.dumps(raw))
    return config.load(str(p))


def run(coro):
    return asyncio.run(coro)


STATUS = {"cvars": {"mapname": "obj_snow", "sv_maxclients": "16", "tcp_mode": "Team elimination"},
          "players": [{"name": "A", "score": 1, "ping": 30}]}


def test_status_card_posts_edits_and_reposts():
    cfg = make_cfg()
    ch = FakeChannel(10)
    bot = FakeBot(cfg, {10: ch})
    cog = status.Status.__new__(status.Status)
    cog.bot, cog.cfg = bot, cfg
    server = cfg["servers"][0]
    run(cog.update_card(server, STATUS, None, None, None))
    assert len(ch.sent) == 1 and ch.sent[0].kwargs["view"] is not None
    run(cog.update_card(server, STATUS, None, None, None))          # unchanged: nothing happens
    assert len(ch.edits) == 0
    changed = dict(STATUS, players=STATUS["players"] + [{"name": "B", "score": 0, "ping": 50}])
    run(cog.update_card(server, changed, None, None, None))
    assert len(ch.edits) == 1
    ch.deleted.add(ch.sent[0].id)                                   # someone deleted the card
    run(cog.update_card(server, STATUS, None, None, None))
    assert len(ch.sent) == 2


def test_offline_debounce():
    cfg = make_cfg()
    bot = FakeBot(cfg, {})
    cog = status.Status.__new__(status.Status)
    cog.bot, cog.cfg = bot, cfg
    server = cfg["servers"][0]
    assert cog.track(server, STATUS) == (STATUS, None)
    shown, since = cog.track(server, None)          # one miss: still shown as online
    assert shown == STATUS and since is None
    shown, since = cog.track(server, None)          # two misses: offline
    assert shown is None and since


def test_leader_needs_two_checks_and_match_alert_cooldown():
    cfg = make_cfg()
    ch = FakeChannel(10)
    bot = FakeBot(cfg, {10: ch})
    cog = status.Status.__new__(status.Status)
    cog.bot, cog.cfg = bot, cfg
    rank = {"title": "Corporal", "level": 5}
    a = {"id": "a" * 16, "name": "A", "rating": 1100, "rank": rank, "matches": 3, "kd": 1.2}
    b = {"id": "b" * 16, "name": "B", "rating": 1200, "rank": rank, "matches": 3, "kd": 1.5}
    run(cog.check_leader({"players": [a]}))          # first run: silent
    run(cog.check_leader({"players": [b, a]}))       # first sighting of a new leader
    assert ch.sent == []
    run(cog.check_leader({"players": [b, a]}))       # confirmed
    assert len(ch.sent) == 1 and "B" in ch.sent[0].kwargs["embed"].description
    four = dict(STATUS, players=[{"name": str(i), "score": 0, "ping": 40} for i in range(4)])
    server = cfg["servers"][0]
    run(cog.check_match(server, STATUS))
    run(cog.check_match(server, four))
    assert len(ch.sent) == 2 and ch.sent[1].kwargs["embed"].title == "Match on now"
    run(cog.check_match(server, STATUS))
    run(cog.check_match(server, four))               # within the cooldown
    assert len(ch.sent) == 2


def release(rid, tag):
    return {"id": rid, "tag_name": tag, "name": tag, "html_url": "https://x/%s" % tag, "draft": False,
            "published_at": "2026-11-0%dT10:00:00Z" % rid, "assets": [],
            "body": (HERE / "fixtures" / "release-body.md").read_text(encoding="utf-8")}


def test_release_draft_then_publish_with_notes():
    cfg = make_cfg()
    staff, ann = FakeChannel(30), FakeChannel(20)
    bot = FakeBot(cfg, {30: staff, 20: ann})
    rels = [release(1, "v0.32.0")]
    bot.releases = types.SimpleNamespace(published=lambda: _async(rels))
    cog = news.News.__new__(news.News)
    cog.bot, cog.cfg = bot, cfg
    run(cog.check_releases())                       # primes, posts nothing
    assert staff.sent == [] and ann.sent == []
    rels.insert(0, release(2, "v0.33.0-sandbox24"))
    run(cog.check_releases())
    assert len(staff.sent) == 1 and ann.sent == []   # waiting for approval
    assert "0.33.0" in staff.sent[0].kwargs["content"]
    notes = (HERE / "fixtures" / "discord-notes.txt").read_text(encoding="utf-8")
    cog.set_notes(2, notes)
    ok, where = run(cog.publish(2))
    assert ok and where == ann.mention
    assert ann.sent[0].kwargs["embed"].title == "TrueCombat: Platinum 0.33.0 is out"
    assert len(ann.sent) == 1 + notes.count("NEXT DISCORD MESSAGE") + 1
    assert all(len(m.kwargs["content"]) <= 2000 for m in ann.sent[1:])
    assert cog.draft(2)["state"] == "published"
    run(cog.check_releases())                       # never twice
    assert len(staff.sent) == 1


def test_release_auto_mode():
    cfg = make_cfg(releases={"mode": "auto"})
    ann = FakeChannel(20)
    bot = FakeBot(cfg, {20: ann})
    rels = []
    bot.releases = types.SimpleNamespace(published=lambda: _async(rels))
    cog = news.News.__new__(news.News)
    cog.bot, cog.cfg = bot, cfg
    bot.store.set("releases_seen", [])
    rels.append(release(3, "v0.34.0"))
    run(cog.check_releases())
    assert len(ann.sent) == 1


def test_link_watcher(tmp_path):
    cfg = make_cfg(linking={"dirs": [str(tmp_path)]})
    bot = FakeBot(cfg, {})
    cog = linking.Linking(bot)
    code = bot.store.new_link_code(77)
    (tmp_path / ("%s.json" % code)).write_text(json.dumps({"code": code, "guid": "B" * 32, "name": "^2Gianni"}))
    (tmp_path / "ZZZZZZ.json").write_text(json.dumps({"code": "ZZZZZZ", "guid": "C" * 32, "name": "x"}))
    for p in sorted(tmp_path.glob("*.json")):
        run(cog.handle(p))
    assert list(tmp_path.glob("*.json")) == []       # every request file is consumed
    link = bot.store.linked_player(77)
    assert link["pid"] == linking.player_id("B" * 32) and link["name"] == "Gianni"


def test_rsvp_capacity_and_waitlist_promotion():
    cfg = make_cfg()
    ch = FakeChannel(40)
    bot = FakeBot(cfg, {40: ch})
    cog = community.Community.__new__(community.Community)
    cog.bot, cog.cfg, cog.lock = bot, cfg, asyncio.Lock()
    eid = bot.store.add_event("event", "Scrims", "", int(time.time()) + 7200, 1, "", 1)
    bot.store.update_event(eid, channel_id=40, message_id=5)
    replies = []

    def inter(uid):
        async def send_message(**kw):
            replies.append((uid, kw["embed"].description))
        return types.SimpleNamespace(user=types.SimpleNamespace(id=uid),
                                     response=types.SimpleNamespace(send_message=send_message))

    run(cog.rsvp(inter(1), eid, "going"))
    run(cog.rsvp(inter(2), eid, "going"))
    assert bot.store.rsvps(eid) == {"going": [1], "maybe": [], "waitlist": [2]}
    assert "waitlist" in replies[-1][1]
    run(cog.rsvp(inter(1), eid, "leave"))
    assert bot.store.rsvps(eid)["going"] == [2]
    assert "<@2>" in ch.sent[-1].kwargs["content"]   # promoted member is told
    assert len(ch.edits) == 3                        # the card refreshed after each click


async def _async(v):
    return v


def test_reports_are_posted_and_filed(tmp_path):
    from tcpbot.cogs import reports
    cfg = make_cfg(reports={"dirs": [str(tmp_path)]})
    staff = FakeChannel(30)
    bot = FakeBot(cfg, {30: staff})
    cog = reports.Reports(bot)
    rep = {"schema": "tcp-report/1", "time": "2026-11-08T18:20:00Z", "server": "Official #1", "map": "obj_snow",
           "level_time_ms": 1, "reporter": {"slot": 2, "name": "Kestrel", "id": "a" * 16},
           "reported": {"slot": 5, "bot": False, "name": "^1Sus", "id": "b" * 16, "kills": 31, "deaths": 2,
                        "shots": 120, "hits": 96, "team_kills": 0}, "reason": "aimbot, snaps through smoke"}
    (tmp_path / "1-2-5.json").write_text(json.dumps(rep))
    (tmp_path / "2-3-5.json").write_text(json.dumps(rep))
    (tmp_path / "3-3-5.json").write_text("not json")
    for p in sorted(tmp_path.glob("*.json")):
        run(cog.handle(p, staff))
    assert len(staff.sent) == 2
    d = staff.sent[1].kwargs["embed"].to_dict()
    assert d["title"] == "Player report · Sus" and "2 reports" in d["description"]
    assert any(f["value"].startswith("80% (96/120)") for f in d["fields"])
    assert sorted(p.name for p in (tmp_path / "sent").iterdir()) == ["1-2-5.json", "2-3-5.json", "invalid-3-3-5.json"]
    assert list(tmp_path.glob("*.json")) == []
