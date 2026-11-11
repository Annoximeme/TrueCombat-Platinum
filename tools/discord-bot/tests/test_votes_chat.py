"""Map votes and the chat bridge."""

import datetime as dt
import re
import types

import pytest

from tcpbot.bot import UserFacingError
from tcpbot.cogs import chatbridge, mapvote
from test_embeds import check as check_embed
from test_flows import FakeBot, FakeChannel, make_cfg, run


def make_vote(**mv):
    cfg = make_cfg(map_votes=mv)
    chans = {20: FakeChannel(20), 30: FakeChannel(30)}
    bot = FakeBot(cfg, chans)
    cog = mapvote.MapVote.__new__(mapvote.MapVote)
    cog.bot, cog.cfg, cog.mc = bot, cfg, cfg["map_votes"]
    return cog, bot, chans


def test_map_vote_limits_and_result():
    cog, bot, chans = make_vote(votes_per_member=2, winners=2)
    d = run(cog.start(48))
    card = chans[20].sent[0]
    check_embed(card.kwargs["embed"])
    assert len(card.kwargs["view"].children) == 6
    with pytest.raises(UserFacingError):
        run(cog.start(48))                                     # one vote at a time
    snow, village, delta = (d["maps"].index(m) for m in ("obj_snow", "obj_village", "obj_delta"))
    cog.cast(1, d["id"], snow)
    cog.cast(1, d["id"], village)
    with pytest.raises(UserFacingError):
        cog.cast(1, d["id"], delta)                            # out of votes
    _, text = cog.cast(1, d["id"], village)                    # take one back
    assert "taken back" in text
    cog.cast(1, d["id"], delta)
    cog.cast(2, d["id"], snow)
    cog.cast(3, d["id"], delta)
    cog.cast(3, d["id"], snow)
    d = bot.store.doc("mapvote", d["id"])
    assert mapvote.tally(d)[:2] == [("obj_snow", 3), ("obj_delta", 2)]
    run(cog.housekeeping(dt.datetime.fromtimestamp(d["closes"] + 1, dt.timezone.utc)))
    d = bot.store.doc("mapvote", d["id"])
    assert d["state"] == "closed" and d["winners"] == ["obj_snow", "obj_delta"]
    assert "Snow" in chans[20].edits[-1][1]["embed"].description and chans[20].edits[-1][1]["view"] is None
    note = chans[30].sent[0].kwargs["embed"].description
    assert "obj_snow obj_delta" in note and "not changed automatically" in note
    with pytest.raises(UserFacingError):
        cog.cast(4, d["id"], snow)


def test_map_vote_opens_on_schedule_once():
    cog, bot, chans = make_vote(enabled=True, weekday=4, hour=18)
    friday = dt.datetime(2026, 11, 13, 17, 30, tzinfo=dt.timezone.utc)     # 18:30 in Brussels
    run(cog.housekeeping(friday - dt.timedelta(hours=2)))
    assert chans[20].sent == []
    run(cog.housekeeping(friday))
    run(cog.housekeeping(friday + dt.timedelta(minutes=2)))
    assert len(chans[20].sent) == 1


PATTERNS = None


def pats():
    return [re.compile(p) for p in make_cfg()["chat_bridge"]["patterns"]]


def test_chat_lines():
    p = pats()
    assert chatbridge.parse_line("say: ^1Red^7Fox: gg wp\n", p) == {"name": "RedFox", "text": "gg wp"}
    assert chatbridge.parse_line("sayteam: Fox: push B", p) is None
    assert chatbridge.parse_line("say: Fox: !link ABC123", p) is None
    assert chatbridge.parse_line("say: Fox: /link ABC123", p) is None
    assert chatbridge.parse_line("TCP_NATIVE_SAY slot=3 team=0 nice shot", p) == {"slot": 3, "text": "nice shot"}
    assert chatbridge.parse_line("TCP_NATIVE_SAY slot=3 team=1 flank left", p) is None
    assert chatbridge.parse_line("Kill: 1 2 3: A killed B", p) is None


def test_follower_and_batching(tmp_path):
    log = tmp_path / "console.log"
    log.write_text("say: Old: before the bot started\n")
    cfg = make_cfg(chat_bridge={"enabled": True, "servers": [{"key": "official1", "channel": 60, "log": str(log)}]})
    assert cfg.problems == []
    ch = FakeChannel(60)
    bot = FakeBot(cfg, {60: ch})
    cog = chatbridge.ChatBridge(bot)
    entry = cog.servers()[0]
    f = chatbridge.Follower(str(log))
    assert f.read() == []
    with open(log, "a") as fh:
        fh.write("say: A: hello @everyone\nsay: B: *hi*\nsay: C: half a li")
    for line in f.read():
        run(cog.take(entry, line))
    with open(log, "a") as fh:
        fh.write("ne\n")
    for line in f.read():
        run(cog.take(entry, line))
    run(cog.flush(entry))
    text = ch.sent[0].kwargs["content"]
    assert text.count("\n") == 2 and "**C**: half a line" in text and "@everyone" not in text and "\\*hi\\*" in text
    log.write_text("say: D: after rotation\n")                 # rotated: smaller file
    assert f.read() == ["say: D: after rotation"]
    member = types.SimpleNamespace(id=5, display_name='Evil"; quit')
    assert cog.relay_line(member, 'hi"; rcon map x') == 'say "[Discord] Evil quit: hi rcon map x"'
