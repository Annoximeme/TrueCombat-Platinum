"""rcon client, admin helpers and the report demo lookup."""

import asyncio
import os
import pathlib
import tempfile
import time

from tcpbot.cogs import admin, reports
from tcpbot.rcon import parse_banlist, parse_status, password_for, rcon, safe_arg

STATUS = ("map                   : obj_village\n\n"
          "num score ping name                                lastmsg address               qport rate  lastConnectTime\n"
          "--- ----- ---- ----------------------------------- ------- --------------------- ----- ----- ---------------\n"
          "  0     5   48 Gianni                                    0 203.0.113.7:27960     1234 25000 1000\n"
          "  1     0    0 [BOT] Raven                               0 bot                       0 16384 25625\n")
BANLIST = ("2 ban(s) in tcetest/banlist.txt\n"
           "#1   ip 203.0.113.*        guid -                                name '' added 2026-11-09 00:17:47 (30 min left) reason: range\n"
           "#2   ip 203.0.113.7        guid FEDCBA9876543210FEDCBA9876543210 name 'Cheater' added 2026-11-09 00:17:47 reason: aimbot\n")


class FakeServer(asyncio.DatagramProtocol):
    def __init__(self, password, answers):
        self.password, self.answers, self.seen = password, answers, []

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        _, pw, cmd = data[4:].decode().split(" ", 2)
        self.seen.append(cmd)
        text = "Bad rconpassword.\n" if pw != self.password else self.answers.get(cmd.split()[0], "")
        for i in range(0, len(text), 40):        # several packets, like long answers
            self.transport.sendto(b"\xff\xff\xff\xffprint\n" + text[i:i + 40].encode(), addr)


def test_rcon_round_trip_and_parsers():
    async def go():
        loop = asyncio.get_running_loop()
        tr, srv = await loop.create_datagram_endpoint(lambda: FakeServer("pw", {"status": STATUS, "banlist": BANLIST}),
                                                      local_addr=("127.0.0.1", 0))
        port = tr.get_extra_info("sockname")[1]
        try:
            st = parse_status(await rcon("127.0.0.1", port, "pw", "status"))
            bl = parse_banlist(await rcon("127.0.0.1", port, "pw", "banlist"))
            try:
                await rcon("127.0.0.1", port, "nope", "status")
                refused = False
            except Exception:  # noqa: BLE001
                refused = True
            return st, bl, refused
        finally:
            tr.close()
    st, bl, refused = asyncio.run(go())
    assert st["map"] == "obj_village"
    assert [(p["slot"], p["name"], p["bot"], p["ping"]) for p in st["players"]] == [(0, "Gianni", False, 48),
                                                                                   (1, "[BOT] Raven", True, 0)]
    assert bl[0]["ip"] == "203.0.113.*" and bl[0]["minutes_left"] == 30 and bl[0]["guid"] == ""
    assert bl[1]["guid"] == "FEDCBA9876543210FEDCBA9876543210" and bl[1]["name"] == "Cheater" and bl[1]["reason"] == "aimbot"
    assert refused


def test_safe_arg_and_password_file():
    assert safe_arg('hi"; quit\\n^1red') == "hi quit nred"
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "rcon-official1").write_text('set rconpassword "s3cret"\n')
    os.environ["CREDENTIALS_DIRECTORY"] = str(d)
    try:
        assert password_for({"key": "official1", "rcon_credential": "rcon-official1"}) == "s3cret"
    finally:
        del os.environ["CREDENTIALS_DIRECTORY"]
    (d / "plain").write_text("plainpw\n")
    assert password_for({"rcon_password_file": str(d / "plain")}) == "plainpw"


def test_length_label():
    assert admin.length_label("30m") == "for 30 minutes"
    assert admin.length_label("1d") == "for 1 day"
    assert admin.length_label("perm") == "permanently"


def test_find_demo_picks_covering_demo():
    d = pathlib.Path(tempfile.mkdtemp())
    a = d / "Official_1_2026-11-09-20-00-00_obj_village.sv_84"
    b = d / "Official_1_2026-11-09-20-20-00_obj_snow.sv_84"
    for f in (a, b):
        f.write_bytes(b"x")
    import datetime as dt
    t0 = int(dt.datetime(2026, 11, 9, 20, 20, 0, tzinfo=dt.timezone.utc).timestamp())
    os.utime(a, (t0 - 1, t0 - 1))
    os.utime(b, (t0 + 1200, t0 + 1200))
    assert reports.find_demo(d, t0 - 600) == (a.name, 600)
    assert reports.find_demo(d, t0 + 75) == (b.name, 75)
    assert reports.find_demo(d, t0 + 5000) is None
