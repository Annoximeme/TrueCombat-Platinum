"""Raid watch, appeals and /ask."""

import datetime as dt
import types

import pytest

from tcpbot import faq
from tcpbot.bot import UserFacingError
from tcpbot.cogs import support
from test_embeds import check as check_embed
from test_feedback import DMUser, inter
from test_flows import FakeBot, FakeChannel, make_cfg, run


def make():
    cfg = make_cfg()
    staff = FakeChannel(30)
    bot = FakeBot(cfg, {30: staff})
    users = {7: DMUser()}
    bot.get_user = users.get
    cog = support.Support(bot)
    return cog, bot, staff, users


def member(i, age_days):
    return types.SimpleNamespace(id=i, bot=False, created_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=age_days))


def test_join_wave_alerts_once():
    cog, bot, staff, _ = make()
    wave = None
    for i in range(7):
        assert cog.note_join(member(i, 0 if i < 5 else 400), 1000.0 + i) is None
    wave = cog.note_join(member(7, 0), 1008.0)
    assert wave and len(wave) == 8
    e = cog.raid_embed(wave)
    check_embed(e)
    assert "6 of the last 8" in e.fields[0].value
    assert cog.note_join(member(8, 0), 1009.0) is None          # already alerted
    cog2, *_ = make()
    for i in range(12):                                         # a slow trickle is not a wave
        assert cog2.note_join(member(i, 100), 1000.0 + i * 30) is None


def test_appeal_flow():
    cog, bot, staff, users = make()
    bot.store.link(7, "c" * 16, "Fox")
    run(cog.new_appeal(inter(7), "Fox", "Banned on Official #1 last night after a heated round.",
                       "I lost my temper, it won't happen again. @everyone"))
    card = staff.sent[0]
    check_embed(card.kwargs["embed"])
    assert "player.html?id=cccc" in card.kwargs["embed"].url and len(card.kwargs["view"].children) == 2
    i = inter(1)
    run(cog.decide(i, 1, "denied"))
    assert "Denied" in i.response.edited[0]["embed"].fields[-1].value and i.response.edited[0]["view"] is None
    assert "stays in place" in users[7].dms[0].description
    with pytest.raises(UserFacingError):
        run(cog.decide(inter(1), 1, "accepted"))                # decided once


def test_ask_finds_the_right_answers():
    cog, bot, staff, _ = make()
    cases = {
        "how do i install the game": "How do I install it?",
        "is this free to play?": "Is it free?",
        "game crashes when starting with directx": "DirectX 12 won't start",
        "why am i not showing on the leaderboard": "Why am I not on the leaderboard?",
        "how can i link my discord": "How do I link my Discord account",
        "can I donate": "How can I support the project?",
        "there is a cheater on the server": "How do I report a cheater",
        "does it run on linux": "Is there a Linux or Mac version?",
        "how do I host a server for my friends": "Can I host my own server?",
        "what are the system requirements": "What do I need to run it?",
        "how does xp work": "How is XP calculated?",
        "I got banned": "I was banned. Can I appeal?",
        "pug queue": "How does the pickup queue work?",
        "when is the next update": "How do I follow development?",
    }
    for q, want in cases.items():
        e = cog.answer(q)
        assert e is not None and e.title.startswith(want), (q, e and e.title)
        check_embed(e)
    assert cog.answer("what is the airspeed of an unladen swallow") is None
    assert cog.answer("???") is None
    assert all(len(q) <= 100 and len(a) < 900 for q, a, _x, _u in faq.ENTRIES)


def test_ask_staff_passes_the_question_on_once():
    cog, bot, staff, _ = make()
    ref = bot.store.doc_add("question", {"q": "Will there be a night map?", "answered": False}, owner=7)
    i = inter(7)
    i.user.mention = "<@7>"
    run(cog.on_staff(i, ref))
    assert "night map" in staff.sent[0].kwargs["embed"].description
    with pytest.raises(UserFacingError):
        run(cog.on_staff(i, ref))
    other = inter(8)
    with pytest.raises(UserFacingError):
        run(cog.on_staff(other, ref))
