"""Pickup queue: team balancing, rcon, and the whole flow from queue to result
against a fake match server (real UDP on 127.0.0.1) and fake Discord channels."""

import asyncio
import json
import random
import types

import pytest

from tcpbot import teams
from tcpbot.cogs import pickup
from tcpbot.rcon import RconError, rcon
from test_flows import FakeBot, FakeChannel, make_cfg


def test_balance_is_optimal_and_even():
    r = {1: 1400, 2: 1300, 3: 1000, 4: 1000, 5: 900, 6: 800}
    red, blue = teams.balance(r, random.Random(1))
    assert sorted(red + blue) == [1, 2, 3, 4, 5, 6] and len(red) == len(blue) == 3
    assert abs(sum(r[p] for p in red) - sum(r[p] for p in blue)) == 0
    with pytest.raises(ValueError):
        teams.balance({1: 1, 2: 2, 3: 3})


def test_balance_ten_players_and_unrated():
    rng = random.Random(3)
    raw = {i: (rng.randint(800, 1600) if i % 3 else None) for i in range(10)}
    r = teams.fill_unrated(raw)
    known = [v for v in raw.values() if v is not None]
    assert r[0] == pytest.approx(sum(known) / len(known))
    red, blue = teams.balance(r, rng)
    diff = abs(sum(r[p] for p in red) - sum(r[p] for p in blue))
    import itertools
    best = min(abs(2 * sum(r[p] for p in c) - sum(r.values())) for c in itertools.combinations(r, 5))
    assert diff == pytest.approx(best)
    assert teams.password().isalnum()


class FakeServer(asyncio.DatagramProtocol):
    """Answers getstatus and rcon like a TrueCombat server."""

    def __init__(self, rcon_password="s3cret"):
        self.players = []
        self.commands = []
        self.pw = rcon_password

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if data == b"\xff\xff\xff\xffgetstatus":
            body = b"\n".join(b'%d %d "%s"' % (s, p, n.encode()) for n, s, p in self.players)
            self.transport.sendto(b"\xff\xff\xff\xffstatusResponse\n\\mapname\\obj_snow\\sv_maxclients\\12\n" + body, addr)
        elif data.startswith(b"\xff\xff\xff\xffrcon "):
            _, pw, cmd = data[9:].decode().split(" ", 2) if data[9:].count(b" ") >= 1 else ("", "", "")
            pw, cmd = data[9:].decode().split(" ", 1)
            if pw != self.pw:
                self.transport.sendto(b"\xff\xff\xff\xffprint\nBad rconpassword.\n", addr)
                return
            self.commands.append(cmd)
            self.transport.sendto(b"\xff\xff\xff\xffprint\nok: " + cmd.encode() + b"\n", addr)


async def start_server():
    loop = asyncio.get_running_loop()
    transport, proto = await loop.create_datagram_endpoint(FakeServer, local_addr=("127.0.0.1", 0))
    return transport, proto, transport.get_extra_info("sockname")[1]


def test_rcon_roundtrip():
    async def go():
        t, srv, port = await start_server()
        try:
            out = await rcon("127.0.0.1", port, "s3cret", "match status")
            with pytest.raises(RconError):
                await rcon("127.0.0.1", port, "wrong", "match status")
        finally:
            t.close()
        return out, srv.commands

    out, cmds = asyncio.run(go())
    assert out == "ok: match status\n" and cmds == ["match status"]


class Member(types.SimpleNamespace):
    pass


def test_full_pickup_flow(tmp_path):
    async def go():
        t, srv, port = await start_server()
        rfile = tmp_path / "rcon-match1"
        rfile.write_text("s3cret\n")
        cfg = make_cfg(pickup={"enabled": True, "channel": 50, "team_size": 2, "map_load_seconds": 0,
                               "join_url": "https://truecombat.eu/join.html",
                               "servers": [{"key": "match1", "host": "127.0.0.1", "port": port,
                                            "public_address": "2.24.59.195:27963", "rcon_file": str(rfile)}]})
        ch = FakeChannel(50)
        bot = FakeBot(cfg, {50: ch})
        dms = {}

        class U:
            def __init__(self, uid):
                self.id = uid

            async def send(self, embed=None, **kw):
                dms.setdefault(self.id, []).append(embed)

        bot.get_user = lambda uid: U(uid)
        ratings = {1: 1500, 2: 1400, 3: 1000, 4: 900}

        async def player(pid, fresh=False):
            uid = int(pid[-1])
            return {"rating": ratings[uid], "matches": 5, "recent": [
                {"ended": "2099-01-01T00:00:00Z", "ratingChange": 12 if uid % 2 else -12}]}

        async def recent(fresh=False):
            return {"matches": [{"map": state["map"], "ended": "2099-01-01T00:00:00Z", "rounds": 9,
                                 "duration": 1500, "mvp": {"name": "Ace", "kills": 31}}]}

        bot.stats = types.SimpleNamespace(player=player, recent=recent)
        for uid in ratings:
            bot.store.link(uid, "%016d" % uid, "P%d" % uid)
        cog = pickup.Pickup(bot)
        cog.rng = random.Random(5)
        state = {}

        r = [await cog.on_join(Member(id=u)) for u in (1, 2, 3)]
        assert "(3/4)" in r[-1]
        assert "already" in await cog.on_join(Member(id=1))
        await cog.on_join(Member(id=4))                      # queue full -> ready check
        st = cog.state()
        assert st["check"] and st["queue"] == [] and set(st["check"]["players"]) == {1, 2, 3, 4}
        cid = st["check"]["id"]
        check_msg = [m for m in ch.sent if m.kwargs["embed"].title == "Match ready"][0]
        assert check_msg.kwargs["content"] == "<@1> <@2> <@3> <@4>"

        # one player declines: the others who accepted go back to the front of the queue
        await cog.on_accept(Member(id=1), cid)
        await cog.on_decline(Member(id=4), cid)
        st = cog.state()
        assert st["check"] is None and [q[0] for q in st["queue"]] == [1]

        for u in (2, 3, 5):
            await cog.on_join(Member(id=u))
        ratings[5] = 900
        bot.store.link(5, "%016d" % 5, "P5")
        cid = cog.state()["check"]["id"]
        for u in (1, 2, 3):
            await cog.on_accept(Member(id=u), cid)
        assert "Everyone" in await cog.on_accept(Member(id=5), cid)
        for _ in range(100):                                 # wait for the server setup to finish
            await asyncio.sleep(0.05)
            if dms:
                break
        m = list(cog.state()["matches"].values())[0]
        state["map"] = m["map"]
        # balanced: 1500+900 vs 1400+1000
        assert sorted([sorted(m["red"]), sorted(m["blue"])]) == [[1, 5], [2, 3]]
        assert srv.commands[:5] == ['set g_password "%s"' % m["password"], "set g_competitive 1",
                                    "set g_pugTeams 1", "set sv_mapRotationTime 0", "map %s" % m["map"]]
        assert any(c.startswith('match name r "Team ') for c in srv.commands)
        assert set(dms) == {1, 2, 3, 5} and m["password"] in dms[1][0].description
        team1 = "r" if 1 in m["red"] else "b"
        assert "join.html#2.24.59.195:27963?pw=%s&team=%s" % (m["password"], team1) in dms[1][0].description
        assert "/setu tcp_team %s; password %s; connect 2.24.59.195:27963" % (team1, m["password"]) in dms[1][0].description
        assert m["password"] not in json.dumps([x.kwargs["embed"].to_dict() for x in ch.sent if x.kwargs.get("embed")])
        details = await cog.on_details(Member(id=2), m["id"])
        assert m["address"] in details.description
        with pytest.raises(Exception):
            await cog.on_details(Member(id=9), m["id"])
        assert "in a match" in str(await _err(cog.on_join(Member(id=1))))

        # players connect, play, leave -> result posted, server locked again and freed
        srv.players = [("A", 10, 30), ("B", 5, 40)]
        cog.last_scan = 0
        await cog.housekeeping()
        srv.players = []
        for _ in range(2):
            cog.last_scan = 0
            await cog.housekeeping()
        assert cog.state()["matches"] == {}
        result = ch.sent[-1].kwargs["embed"].to_dict()
        assert result["title"].startswith("Pickup #%d finished" % m["id"])
        assert "MVP **Ace** with 31 kills" in result["description"]
        assert "+12" in result["fields"][0]["value"] and "-12" in result["fields"][0]["value"]
        assert srv.commands[-1].startswith("set g_password") and m["password"] not in srv.commands[-1]
        t.close()

    asyncio.run(go())


async def _err(coro):
    try:
        return await coro
    except Exception as e:  # noqa: BLE001
        return e


def test_ready_check_timeout(tmp_path):
    async def go():
        cfg = make_cfg(pickup={"enabled": True, "channel": 50, "team_size": 1,
                               "servers": [{"key": "m", "host": "127.0.0.1", "port": 1, "public_address": "x:1",
                                            "rcon_file": str(tmp_path / "none")}]})
        ch = FakeChannel(50)
        bot = FakeBot(cfg, {50: ch})
        cog = pickup.Pickup(bot)
        await cog.on_join(Member(id=1))
        await cog.on_join(Member(id=2))
        st = cog.state()
        await cog.on_accept(Member(id=2), st["check"]["id"])
        st = cog.state()
        st["check"]["deadline"] = 0
        cog.save(st)
        await cog.housekeeping()
        st = cog.state()
        assert st["check"] is None and [q[0] for q in st["queue"]] == [2]
        assert any(e[1].get("embed") and e[1]["embed"].title == "Match cancelled" for e in ch.edits)

    asyncio.run(go())


def test_pickup_config_validation():
    cfg = make_cfg(pickup={"enabled": True, "servers": [{"key": "m", "host": "10.0.0.5", "port": 27963,
                                                          "public_address": "x", "rcon_file": "/x"}]})
    assert any("pickup.channel" in p for p in cfg.problems)
    assert any("only allowed to servers on this machine" in p for p in cfg.problems)
