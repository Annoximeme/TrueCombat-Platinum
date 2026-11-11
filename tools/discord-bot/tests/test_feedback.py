"""Bug tracker cards and suggestion votes."""

import types

import pytest

from tcpbot.bot import UserFacingError
from tcpbot.cogs import feedback
from test_embeds import check as check_embed
from test_flows import FakeBot, FakeChannel, make_cfg, run


class Resp:
    def __init__(self):
        self.sent, self.edited = [], []

    def is_done(self):
        return bool(self.sent or self.edited)

    async def send_message(self, **kw):
        self.sent.append(kw)

    async def edit_message(self, **kw):
        self.edited.append(kw)


def inter(uid):
    return types.SimpleNamespace(user=types.SimpleNamespace(id=uid), response=Resp())


class DMUser:
    def __init__(self):
        self.dms = []

    async def send(self, **kw):
        self.dms.append(kw["embed"])


def make(**channels):
    cfg = make_cfg(channels=dict({"status": 10, "staff": 30}, **channels))
    chans = {30: FakeChannel(30), 50: FakeChannel(50)}
    bot = FakeBot(cfg, chans)
    users = {7: DMUser()}
    bot.get_user = users.get
    cog = feedback.Feedback.__new__(feedback.Feedback)
    cog.bot, cog.cfg, cog.fc = bot, cfg, cfg["feedback"]
    return cog, bot, chans, users


def test_bug_goes_to_the_tracker_and_reporter_hears_back():
    cog, bot, chans, users = make()
    i = inter(7)
    run(cog.new_bug(i, "Grenade fires the gun", "Throwing a grenade also fires my rifle. @everyone", "1. throw", "0.34.1"))
    card = chans[30].sent[0]
    check_embed(card.kwargs["embed"])
    assert card.kwargs["embed"].title.startswith("Bug #1") and len(card.kwargs["view"].children) == 5
    assert "bug #1" in i.response.sent[0]["embed"].title
    with pytest.raises(UserFacingError):
        cog.throttle("bug", 7)                         # one report per few minutes
    cog.throttle("bug", 8)
    staff = inter(1)
    run(cog.set_bug_state(staff, 1, "fixed"))
    d = bot.store.doc("bug", 1)
    assert d["state"] == "fixed" and d["by"] == 1
    assert "Fixed" in staff.response.edited[0]["embed"].fields[-1].value
    assert "next update" in users[7].dms[0].description
    bot.is_staff = lambda m: False
    with pytest.raises(UserFacingError):
        run(cog.set_bug_state(inter(9), 1, "notabug"))


def test_suggestion_votes_are_one_per_member():
    cog, bot, chans, users = make(suggestions=50)
    run(cog.new_idea(inter(7), "Night version of Snow", "Flares and muzzle flashes would look incredible."))
    card = chans[50].sent[0].kwargs["embed"]
    check_embed(card)
    assert "👍 1 · 👎 0" in card.fields[0].value
    for uid, v in ((8, 1), (9, -1), (9, 1), (8, 1)):   # 9 changes their mind, 8 takes theirs back
        run(cog.vote(inter(uid), 1, v))
    d = bot.store.doc("suggestion", 1)
    assert d["votes"] == {"7": 1, "9": 1}
    d["state"] = "shipped"
    bot.store.doc_save(d)
    assert feedback.idea_view(d) is None
    with pytest.raises(UserFacingError):
        run(cog.vote(inter(8), 1, 1))


def test_no_channel_no_form():
    cog, bot, chans, users = make()
    assert cog.idea_channel() is None and cog.bug_channel() is chans[30] and not cog.github()
