"""Teams, the ladder, scrims and tournament brackets."""

import types

import pytest

from tcpbot import bracket as B
from tcpbot.bot import UserFacingError
from tcpbot.cogs import clans
from test_flows import FakeBot, FakeChannel, make_cfg, run


def test_elo_and_seeding():
    w, l = B.elo(1000, 1000)
    assert (round(w), round(l)) == (1016, 984)
    up_w, _ = B.elo(900, 1100)
    assert up_w - 900 > 16                                 # an upset is worth more
    assert B.seed_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]
    with pytest.raises(ValueError):
        B.build([1])


def test_bracket_byes_and_progress():
    rounds = B.build([10, 20, 30, 40, 50])                 # five teams: seeds 1-3 get a bye
    assert len(rounds) == 3 and len(rounds[0]) == 4
    assert [m["w"] for m in rounds[0]] == [10, None, 20, 30]
    assert [(r, i) for r, i, _ in B.pending(rounds)] == [(0, 1), (1, 1)]
    assert B.report(rounds, 0, 1, 50) is None
    assert rounds[1][0] == {"a": 10, "b": 50, "w": None, "live": False}
    B.report(rounds, 1, 0, 10)
    B.report(rounds, 1, 1, 30)
    assert B.round_name(rounds, 2) == "Final" and B.round_name(rounds, 1) == "Semi-finals"
    with pytest.raises(ValueError):
        B.report(rounds, 2, 0, 20)
    assert B.report(rounds, 2, 0, 30) == 30


class FakePickup:
    def __init__(self):
        self.started, self.matches, self.free = [], {}, True

    def servers(self):
        return [{"key": "match1"}]

    def state(self):
        return {"matches": self.matches}

    async def start_custom(self, owner, label, red, blue, names, channel_id=0, mapname=None, meta=None):
        if not self.free:
            return None
        m = {"id": len(self.started) + 1, "red": red, "blue": blue, "meta": meta, "label": label, "map": mapname or "obj_snow"}
        self.started.append(m)
        self.matches[str(m["id"])] = m
        return m


def user(uid):
    return types.SimpleNamespace(id=uid, mention="<@%d>" % uid, display_name="U%d" % uid, bot=False)


def make():
    cfg = make_cfg()
    ch, staff = FakeChannel(40), FakeChannel(30)
    bot = FakeBot(cfg, {40: ch, 30: staff})
    bot.cogs["Pickup"] = FakePickup()
    cog = clans.Clans.__new__(clans.Clans)
    cog.bot, cog.cfg, cog.tc = bot, cfg, cfg["teams"]
    return cog, bot, ch, staff


def team(cog, name, tag, captain, *members):
    tid = cog.store.team_create(name, tag, captain)
    for m in members:
        cog.store.team_invite(tid, m)
        run(cog.on_join(user(m), tid))
    return tid


def test_team_rules():
    cog, bot, ch, _ = make()
    a = team(cog, "Team Terminus", "TT", 1, 2)
    assert cog.store.team_create("team terminus", "XX", 9) is None        # names are unique, case-insensitive
    assert cog.store.team_members(a) == [1, 2]
    with pytest.raises(UserFacingError):
        run(cog.on_join(user(3), a))                                     # no invite
    cog.store.team_invite(a, 2)
    with pytest.raises(UserFacingError):
        run(cog.on_join(user(2), a))                                     # already in a team
    with pytest.raises(UserFacingError):
        cog.my_captaincy(2)
    assert cog.find("tt")["id"] == a and cog.find(str(a))["id"] == a
    card = cog.team_card(cog.store.team(a))
    assert "<@1>" in card.fields[0].value and "2/8" in card.fields[2].name
    assert "Terminus" in cog.ladder().description


def scoreboard(cog, winners, losers):
    rows = []
    for i, u in enumerate(winners + losers):
        pid = "%016x" % u
        cog.store.link(u, pid, "P%d" % u)
        rows.append({"id": pid, "won": u in winners})
    return {"players": rows}


def test_scrim_from_challenge_to_ladder():
    cog, bot, ch, _ = make()
    a, b = team(cog, "Alpha", "ALP", 1, 2), team(cog, "Bravo", "BRV", 3, 4)
    d = cog.store.doc("scrim", cog.store.doc_add("scrim", {"a": a, "b": b, "map": "obj_snow", "message": 0, "channel": 0,
                                                           "expires": 2 ** 40}))
    run(cog.refresh_scrim(d))
    assert ch.sent[0].kwargs["content"] == "<@3>" and ch.sent[0].kwargs["view"] is not None
    with pytest.raises(UserFacingError):
        run(cog.on_yes(user(1), d["id"]))                                # only the challenged captain
    pk = bot.cogs["Pickup"]
    pk.free = False
    with pytest.raises(UserFacingError):
        run(cog.on_yes(user(3), d["id"]))
    pk.free = True
    run(cog.on_yes(user(3), d["id"]))
    m = pk.started[0]
    assert m["red"] == [1, 2] and m["blue"] == [3, 4] and m["meta"]["teams"] == [a, b]
    assert cog.busy(a) and cog.store.doc("scrim", d["id"])["state"] == "live"
    pk.matches.clear()
    run(cog.on_team_match(m, {}, scoreboard(cog, [3, 4], [1, 2]), None))
    done = cog.store.doc("scrim", d["id"])
    assert done["state"] == "done" and done["winner"] == b and done["delta"] == [16, -16]
    assert round(cog.store.team(b)["rating"]) == 1016 and cog.store.team(a)["losses"] == 1
    assert "beat" in ch.edits[-1][1]["embed"].description


def test_scrim_without_a_readable_result_goes_to_staff():
    cog, bot, ch, _ = make()
    a, b = team(cog, "Alpha", "ALP", 1), team(cog, "Bravo", "BRV", 3)
    d = cog.store.doc("scrim", cog.store.doc_add("scrim", {"a": a, "b": b, "map": "", "message": 0, "channel": 0,
                                                           "expires": 2 ** 40}))
    run(cog.on_yes(user(3), d["id"]))
    m = bot.cogs["Pickup"].started[0]
    run(cog.on_team_match(m, None, None, None))
    d = cog.store.doc("scrim", d["id"])
    assert d["state"] == "review"
    cog.close_scrim(d, a)
    assert d["state"] == "done" and d["winner"] == a


def test_tournament_runs_to_a_champion():
    cog, bot, ch, staff = make()
    ids = [team(cog, n, t, c) for n, t, c in (("Alpha", "ALP", 1), ("Bravo", "BRV", 2), ("Charlie", "CHA", 3))]
    cog.store.team_update(ids[0], rating=1200)
    d = cog.store.doc("tournament", cog.store.doc_add("tournament", {
        "name": "Winter Cup", "about": "", "starts": 1800000000, "size": 4, "teams": [], "rounds": [], "message": 0,
        "channel": 0}))
    run(cog.refresh_tour(d))
    for c in (1, 2, 3):
        run(cog.on_in(user(c), d["id"]))
    assert "3/4" in ch.edits[-1][1]["embed"].fields[0].name
    d = cog.store.doc("tournament", d["id"])
    teams = sorted((cog.store.team(i) for i in d["teams"]), key=lambda t: -t["rating"])
    d["teams"] = [t["id"] for t in teams]
    d["rounds"], d["state"] = B.build(d["teams"]), "live"
    cog.store.doc_save(d)
    e = cog.tour_embed(d)
    assert e.fields[0].name == "Semi-finals" and "bye" in e.fields[0].value and "» [ALP] Alpha" in e.fields[0].value
    # the semi-final between Bravo and Charlie: scoreboard unreadable, staff are asked
    run(cog.tournament_match_over({"tournament": d["id"], "round": 0, "slot": 1}, None, None))
    assert "result needed" in staff.sent[0].kwargs["embed"].title.lower()
    d = cog.store.doc("tournament", d["id"])
    run(cog.advance(d, 0, 1, ids[2]))
    d = cog.store.doc("tournament", d["id"])
    assert d["rounds"][1][0]["a"] == ids[0] and d["rounds"][1][0]["b"] == ids[2]
    run(cog.tournament_match_over({"tournament": d["id"], "round": 1, "slot": 0}, ids[2], None))
    d = cog.store.doc("tournament", d["id"])
    assert d["state"] == "done" and d["champion"] == ids[2]
    assert "champion" in ch.sent[-1].kwargs["embed"].title.lower()
    assert "won the tournament" in cog.tour_embed(d).description


def test_scrim_on_a_real_match_server(tmp_path):
    """The whole path through the pickup module's match servers, against a fake game server on UDP."""
    import asyncio

    from tcpbot.cogs import pickup
    from test_pickup import start_server

    async def go():
        t, srv, port = await start_server()
        rfile = tmp_path / "rcon-match1"
        rfile.write_text("s3cret\n")
        cfg = make_cfg(pickup={"map_load_seconds": 0, "servers": [
            {"key": "match1", "host": "127.0.0.1", "port": port, "public_address": "2.24.59.195:27963",
             "rcon_file": str(rfile), "stats_name": "Pickup #1"}]})
        ch = FakeChannel(40)
        bot = FakeBot(cfg, {40: ch, 30: FakeChannel(30)})
        dms = {}

        class U:
            def __init__(self, uid):
                self.id = uid

            async def send(self, embed=None, **kw):
                dms.setdefault(self.id, []).append(embed)
        bot.get_user = lambda uid: U(uid)
        pk = pickup.Pickup(bot)
        cog = clans.Clans.__new__(clans.Clans)
        cog.bot, cog.cfg, cog.tc = bot, cfg, cfg["teams"]
        bot.cogs.update(Pickup=pk, Clans=cog)
        a = cog.store.team_create("Alpha Squad", "ALP", 1)
        b = cog.store.team_create("Bravo", "BRV", 3)
        cog.store.team_invite(a, 2)
        await cog.on_join(user(2), a)
        board = scoreboard(cog, [1, 2], [3])

        async def recent(fresh=False):
            return {"matches": [{"id": "m1", "map": "obj_snow", "ended": "2099-01-01T00:00:00Z",
                                 "server": "Pickup #1"}]}

        async def match(mid):
            return board
        bot.stats = types.SimpleNamespace(recent=recent, match=match)
        d = cog.store.doc("scrim", cog.store.doc_add("scrim", {"a": a, "b": b, "map": "obj_snow", "message": 0,
                                                               "channel": 0, "expires": 2 ** 40}))
        await cog.refresh_scrim(d)
        await cog.on_yes(user(3), d["id"])
        m = list(pk.state()["matches"].values())[0]
        assert 'match name r "Alpha Squad"' in srv.commands and "map obj_snow" in srv.commands
        assert set(dms) == {1, 2, 3} and "tcp_team b" in dms[3][0].description
        card = [x for x in ch.sent if x.kwargs.get("embed") and x.kwargs["embed"].title.startswith("Scrim #1 · ALP vs BRV")]
        assert card and m["password"] not in str(card[0].kwargs["embed"].to_dict())
        assert cog.busy(a) and cog.busy(b)
        srv.players = [("A", 1, 30)]
        pk.last_scan = 0
        await pk.housekeeping()
        srv.players = []
        for _ in range(2):
            pk.last_scan = 0
            await pk.housekeeping()
        assert pk.state()["matches"] == {} and not cog.busy(a)
        done = cog.store.doc("scrim", d["id"])
        assert done["state"] == "done" and done["winner"] == a
        assert cog.store.team(a)["wins"] == 1 and cog.store.team(b)["losses"] == 1
        t.close()

    asyncio.run(go())
