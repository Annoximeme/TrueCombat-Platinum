#!/usr/bin/env python3
"""Loopback tests for the staff portal: a fake game server answers rcon like the 0.35/0.36 server does,
and the tests drive the HTTP API with sessions for each role. Standard library only.

    python3 test_staff_portal.py
"""
from __future__ import annotations

import http.client
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["TCP_STAFF_DEV"] = "1"
import tcp_staff_portal as tsp  # noqa: E402

GUID = "0123456789ABCDEF0123456789ABCDEF"
PID = tsp.player_pid(GUID)


class FakeGame(threading.Thread):
    """Enough of the dedicated server's rcon to exercise the portal. staff=False acts like a 0.35.0 server."""

    def __init__(self, staff=True, password="pw"):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.staff = staff
        self.password = password
        self.commands = []
        self.bans = []
        self.players = {0: {"name": "Viper^7", "guid": GUID, "ip": "203.0.113.9", "team": 1, "muted": 0},
                        1: {"name": "[BOT] Rook^7", "guid": "", "ip": "bot", "team": 2, "muted": 0}}

    def answer(self, cmd: str) -> str:
        word, _, rest = cmd.partition(" ")
        if word == "status":
            lines = ["map                   : obj_village", "", "num score ping name lastmsg address qport rate lastConnectTime"]
            for slot, p in self.players.items():
                addr = "bot" if p["ip"] == "bot" else p["ip"] + ":27960"
                lines.append("%3d %5d %4d %-36s %7d %-21s %5d %5d %d" % (slot, 5, 0 if p["ip"] == "bot" else 48, p["name"], 0, addr, 1234, 25000, 61000))
            return "\n".join(lines) + "\n"
        if word == "acstatus":
            out = "anti-cheat on; speed log, aim log, files log; EAC required (eos)\nslot name             eac          files                    snaps/kills detections last\n"
            for slot, p in self.players.items():
                if p["ip"] == "bot":
                    out += "%4d %-16.16s (bot or host, not checked)\n" % (slot, p["name"])
                else:
                    out += "%4d %-16.16s %-12s %-24.24s %5d/%-5d %10d %s\n" % (slot, p["name"], "protected", "ok", 10, 2, 0, "")
                    out += "     account id 0002aabbccddeeff00112233445566778\n"
            return out
        if word == "serverinfo":
            return "Server info settings:\nsv_hostname   Test^1 Server\nmapname   obj_village\ntcp_mode   Team Elimination\nsv_maxclients   16\nsv_eac   2\nsv_mapRotation   obj_village obj_snow\n"
        if word == "dumpuser":
            p = self.players.get(int(rest))
            return "userinfo\n--------\nname   %s\ncl_guid   %s\nip   %s:27960\n" % (p["name"], p["guid"], p["ip"]) if p else "No player found.\n"
        if word == "tcp_staffcaps":
            return "TCP_STAFF_CAPS 1 players mute warn putteam staffsay\n" if self.staff else ""
        if word == "tcp_players" and self.staff:
            out = "TCP_STAFF_MATCH map_time=1000 round_phase=2 team_mode=1\n"
            for slot, p in self.players.items():
                out += "TCP_STAFF_PLAYER slot=%d begun=1 team=%d spec=0 bot=%d alive=1 muted=%d kills=3 deaths=1 team_kills=0 damage=300 pid=%s name=%s\n" % (
                    slot, p["team"], p["ip"] == "bot", p["muted"], tsp.player_pid(p["guid"]) or "-", p["name"])
            return out + "TCP_STAFF_END\n"
        if word == "banlist":
            return "%d ban(s)\n" % len(self.bans) + "".join(
                "#%d ip %s guid %s name '%s' added 2026-11-12 10:00 reason: x%s\n" % (i + 1, b.get("ip") or "-", b.get("guid") or "-", "n", " puid " + b["puid"] if b.get("puid") else "")
                for i, b in enumerate(self.bans))
        if word == "banguid":
            self.bans.append({"guid": rest.split()[0]})
            return "ban added\n"
        if word == "banip":
            self.bans.append({"ip": rest.split()[0]})
            return "ban added\n"
        if word == "banpuid":
            self.bans.append({"puid": rest.split()[0]})
            return "ban added\n"
        if word == "ban":
            p = self.players.pop(int(rest.split()[0]))
            self.bans.append({"guid": p["guid"], "ip": p["ip"]})
            return "ban added, kicked\n"
        if word == "unban":
            before = len(self.bans)
            self.bans = [b for b in self.bans if rest not in (b.get("guid"), b.get("ip"), b.get("puid"))]
            return "removed %d\n" % (before - len(self.bans))
        if word == "mute" and self.staff:
            self.players[int(rest.split()[0])]["muted"] = 60
            return "TCP_STAFF_MUTE slot=%s\n" % rest.split()[0]
        if word in ("warn", "putteam", "staffsay", "unmute") and self.staff:
            return "TCP_STAFF_%s ok\n" % word.upper()
        if word in ("clientkick", "spectate", "say", "map", "nextmap", "map_restart", "maprotation", "voicemute", "voiceunmute"):
            return "ok %s\n" % word
        return ""

    def run(self):
        while True:
            data, addr = self.sock.recvfrom(65536)
            text = data[4:].decode("latin-1")
            if not text.startswith("rcon "):
                continue
            _, pw, cmd = text.split(" ", 2)
            if pw != self.password:
                self.sock.sendto(b"\xff\xff\xff\xffprint\nBad rconpassword.\n", addr)
                continue
            self.commands.append(cmd)
            self.sock.sendto(b"\xff\xff\xff\xffprint\n" + self.answer(cmd).encode("latin-1"), addr)


def fake_stats():
    """Stands in for the stats service (tcp_stats.py routes player.json and search.json)."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.startswith("/player.json?id=" + PID):
                body = {"id": PID, "name": "Viper", "rating": 1234, "ranked": True, "position": 3, "matches": 12, "kills": 90,
                        "deaths": 40, "teamKills": 1, "recent": [{"ended": "2026-11-12T09:00:00Z", "map": "obj_snow", "won": True,
                                                                  "kills": 9, "deaths": 2, "headshots": 4}]}
            elif self.path.startswith("/search.json"):
                body = {"players": [{"id": "fedcba9876543210", "name": "OnlyInStats"}]}
            else:
                self.send_response(404)
                self.end_headers()
                return
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return "http://127.0.0.1:%d" % srv.server_address[1]


class PortalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.game = FakeGame(staff=True)
        cls.old = FakeGame(staff=False)
        cls.game.start()
        cls.old.start()
        reports = Path(cls.tmp.name) / "reports"
        (reports / "sent").mkdir(parents=True)
        (reports / "sent" / "1-0-0.json").write_text(json.dumps({
            "schema": "tcp-report/1", "time": "2026-11-12T10:00:00Z", "server": "Test", "map": "obj_village",
            "reporter": {"slot": 1, "name": "Someone", "id": ""}, "reported": {"slot": 0, "name": "Viper", "id": PID, "kills": 30},
            "reason": "wallhack"}))
        cls.chatlog = Path(cls.tmp.name) / "game.log"
        cls.chatlog.write_text("")
        cfg = {"public_url": "http://127.0.0.1:0", "data_dir": cls.tmp.name, "dev_login": True, "poll_seconds": 0.5,
               "ban_sync_seconds": 3600, "stats_api": fake_stats(), "owners": ["100000000000000001"],
               "servers": [
                   {"key": "one", "name": "Official #1", "host": "127.0.0.1", "port": cls.game.port, "rcon_password": "pw",
                    "reports_dir": str(reports), "log_file": str(cls.chatlog)},
                   {"key": "two", "name": "Official #2", "host": "127.0.0.1", "port": cls.old.port, "rcon_password": "pw"}]}
        cls.portal = tsp.Portal(cfg)
        cls.portal.start()
        from http.server import ThreadingHTTPServer
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), tsp.make_handler(cls.portal))
        cls.port = cls.httpd.server_address[1]
        cfg["public_url"] = "http://127.0.0.1:%d" % cls.port
        cls.httpd.RequestHandlerClass = tsp.make_handler(cls.portal)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        time.sleep(1.5)
        cls.sessions = {r: cls.login(r) for r in ("moderator", "admin", "owner")}

    @classmethod
    def tearDownClass(cls):
        cls.portal.stop.set()
        cls.httpd.shutdown()

    @classmethod
    def login(cls, role):
        c = http.client.HTTPConnection("127.0.0.1", cls.port)
        c.request("GET", "/auth/dev?role=%s&name=%s" % (role, role.title()))
        r = c.getresponse()
        r.read()
        c.close()
        cookie = r.getheader("Set-Cookie").split(";")[0]
        me = cls.call(None, "GET", "/api/me", cookie=cookie)[1]
        return {"cookie": cookie, "csrf": me["csrf"]}

    @classmethod
    def call(cls, role, method, path, body=None, cookie=None, csrf=None):
        c = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        headers = {}
        if role:
            headers["Cookie"] = cls.sessions[role]["cookie"]
            headers["X-CSRF"] = cls.sessions[role]["csrf"] if csrf is None else csrf
        if cookie:
            headers["Cookie"] = cookie
        data = None
        if body is not None:
            data = json.dumps(body)
            headers["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=headers)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            return r.status, json.loads(raw or b"{}")
        except ValueError:
            return r.status, raw

    # ---------------------------------------------------------------- tests
    def test_01_unauthenticated(self):
        self.assertEqual(self.call(None, "GET", "/api/servers")[0], 401)
        self.assertEqual(self.call(None, "POST", "/api/action", {})[0], 401)
        st, body = self.call(None, "GET", "/")
        self.assertEqual(st, 200)

    def test_02_servers_snapshot(self):
        st, data = self.call("moderator", "GET", "/api/servers")
        self.assertEqual(st, 200)
        one, two = data["servers"]
        self.assertTrue(one["online"])
        self.assertEqual(one["eac"], "required")
        self.assertEqual(one["humans"], 1)
        viper = [p for p in one["players"] if not p["bot"]][0]
        self.assertEqual(viper["name"], "Viper")
        self.assertEqual(viper["pid"], PID)
        self.assertEqual(viper["eac"], "protected")
        self.assertEqual(viper["puid"], "0002aabbccddeeff00112233445566778")
        self.assertEqual(viper["kills"], 3)
        self.assertEqual(two["staff_commands"], [])
        self.assertTrue(one["staff_commands"])

    def test_03_csrf_required(self):
        st, _ = self.call("moderator", "POST", "/api/action", {"action": "kick", "server": "one", "slot": 0, "reason": "x"}, csrf="wrong")
        self.assertEqual(st, 403)

    def test_04_warn_mute_move(self):
        st, d = self.call("moderator", "POST", "/api/action", {"action": "warn", "server": "one", "slot": 0, "name": "Viper", "reason": "Stop it"})
        self.assertEqual(st, 200, d)
        self.assertIn("warn 0 Stop it", self.game.commands)
        st, d = self.call("moderator", "POST", "/api/action", {"action": "mute", "server": "one", "slot": 0, "length": "30m", "reason": "spam"})
        self.assertEqual(st, 200, d)
        self.assertIn("mute 0 30 spam", self.game.commands)
        self.assertIn("voicemute 0", self.game.commands)
        st, d = self.call("moderator", "POST", "/api/action", {"action": "move", "server": "one", "slot": 0, "team": "b"})
        self.assertEqual(st, 200, d)
        # an old server has no warn / team move, but spectate works
        st, d = self.call("moderator", "POST", "/api/action", {"action": "warn", "server": "two", "slot": 0, "reason": "x"})
        self.assertEqual(st, 409)
        st, d = self.call("moderator", "POST", "/api/action", {"action": "move", "server": "two", "slot": 0, "team": "s"})
        self.assertEqual(st, 200, d)
        self.assertIn("spectate 0", self.old.commands)

    def test_05_wrong_name_is_refused(self):
        st, d = self.call("moderator", "POST", "/api/action", {"action": "kick", "server": "one", "slot": 0, "name": "SomeoneElse", "reason": "x"})
        self.assertEqual(st, 409)

    def test_06_kick_needs_reason(self):
        st, _ = self.call("moderator", "POST", "/api/action", {"action": "kick", "server": "one", "slot": 0, "reason": ""})
        self.assertEqual(st, 400)

    def test_07_bans(self):
        # moderators are capped at 24 hours
        st, d = self.call("moderator", "POST", "/api/bans", {"pid": PID, "length": "7d", "reason": "cheating"})
        self.assertEqual(st, 403)
        st, d = self.call("moderator", "POST", "/api/bans", {"pid": PID, "length": "0", "reason": "cheating"})
        self.assertEqual(st, 403)
        st, d = self.call("admin", "POST", "/api/bans", {"pid": PID, "length": "7d", "reason": "cheating; rm -rf \"x\""})
        self.assertEqual(st, 200, d)
        for g in (self.game, self.old):
            self.assertTrue(any(c.startswith("banguid %s 1w cheating rm -rf x" % GUID) for c in g.commands), g.commands)
            self.assertTrue(any(c.startswith("banpuid 0002aabbccddeeff00112233445566778") for c in g.commands))
        st, bans = self.call("moderator", "GET", "/api/bans")
        ban = bans["bans"][0]
        self.assertTrue(ban["active"])
        # the reconcile puts a ban back on a server that lost it
        self.old.bans = []
        rep = self.portal.reconcile_bans()
        self.assertIn("1 re-applied", rep["two"])
        self.assertTrue(any(b.get("guid") == GUID for b in self.old.bans))
        # moderators cannot lift; admins can, on every server
        self.assertEqual(self.call("moderator", "POST", "/api/bans/lift", {"id": ban["id"]})[0], 403)
        st, d = self.call("admin", "POST", "/api/bans/lift", {"id": ban["id"], "reason": "appeal"})
        self.assertEqual(st, 200, d)
        self.assertFalse([b for b in self.old.bans if b.get("guid") == GUID])

    def test_08_expiry(self):
        bid = self.portal.store.x("INSERT INTO bans(pid,guid,ip,puid,name,reason,created,expires,by_id,by_name) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                  (PID, GUID, "", "", "Viper", "x", 1, 2, "1", "t"))
        self.game.bans.append({"guid": GUID})
        self.portal.expire_bans()
        self.assertEqual(self.portal.store.one("SELECT active FROM bans WHERE id=?", (bid,))["active"], 0)
        self.assertFalse([b for b in self.game.bans if b.get("guid") == GUID])

    def test_09_server_control_permissions(self):
        self.assertEqual(self.call("moderator", "POST", "/api/server", {"server": "one", "action": "map", "map": "obj_snow"})[0], 403)
        st, d = self.call("admin", "POST", "/api/server", {"server": "one", "action": "map", "map": "obj_snow"})
        self.assertEqual(st, 200, d)
        self.assertEqual(self.call("admin", "POST", "/api/server", {"server": "one", "action": "map", "map": "x; quit"})[0], 400)
        st, d = self.call("moderator", "POST", "/api/server", {"server": "*", "action": "chat", "text": "hello all"})
        self.assertEqual(st, 200, d)
        self.assertTrue(any(c.startswith("staffsay Moderator hello all") for c in self.game.commands))
        self.assertTrue(any(c.startswith("say ^8[STAFF] Moderator^7: hello all") for c in self.old.commands))

    def test_10_chat_feed(self):
        with self.chatlog.open("a") as f:
            f.write("  1000 TCP_NATIVE_SAY slot=0 team=1 enemy at the gate\n")
        time.sleep(1.2)
        st, d = self.call("moderator", "GET", "/api/chat?server=one")
        texts = [(l["name"], l["text"], l["kind"]) for l in d["lines"]]
        self.assertIn(("Viper", "enemy at the gate", "team"), texts)

    def test_11_reports_and_bugs(self):
        st, d = self.call("moderator", "GET", "/api/reports?status=open")
        self.assertEqual(st, 200)
        self.assertEqual(d["reports"][0]["target_pid"], PID)
        rid = d["reports"][0]["id"]
        self.assertEqual(self.call("moderator", "POST", "/api/reports/update", {"id": rid, "status": "closed", "resolution": "banned"})[0], 200)
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("POST", "/api/bugreport", body="Category: Bug\nThe door on Snow does not open.\n", headers={"X-Report-Category": "Bug"})
        self.assertEqual(c.getresponse().status, 201)
        c.close()
        st, d = self.call("moderator", "GET", "/api/reports?status=open&source=bug")
        self.assertIn("door", d["reports"][0]["data"]["text"])

    def test_12_lookup_and_profile(self):
        st, d = self.call("moderator", "GET", "/api/lookup?q=vip")
        self.assertEqual(d["players"][0]["pid"], PID)
        self.assertIn("fedcba9876543210", [x["pid"] for x in d["players"]])
        st, p = self.call("moderator", "GET", "/api/player/" + PID)
        self.assertNotIn("ips", p)
        self.assertEqual(p["stats"]["rating"], 1234)
        self.assertEqual(p["matches"][0]["map"], "obj_snow")
        st, p = self.call("admin", "GET", "/api/player/" + PID)
        self.assertEqual(p["ips"][0]["ip"], "203.0.113.9")
        self.assertEqual(self.call("moderator", "POST", "/api/notes", {"pid": PID, "text": "Watch this one"})[0], 200)

    def test_13_staff_management(self):
        self.assertEqual(self.call("moderator", "GET", "/api/staff")[0], 403)
        self.assertEqual(self.call("admin", "POST", "/api/staff", {"discord_id": "200000000000000002", "role": "admin"})[0], 403)
        self.assertEqual(self.call("admin", "POST", "/api/staff", {"discord_id": "200000000000000002", "role": "moderator"})[0], 200)
        self.assertEqual(self.call("owner", "POST", "/api/staff", {"discord_id": "200000000000000002", "role": "admin"})[0], 200)
        self.assertEqual(self.call("owner", "POST", "/api/staff", {"discord_id": "100000000000000001", "role": "revoked"})[0], 403)
        self.assertEqual(tsp.resolve_role(self.portal, "200000000000000002", []), "admin")
        self.assertEqual(tsp.resolve_role(self.portal, "300000000000000003", []), None)

    def test_14_audit(self):
        self.assertEqual(self.call("moderator", "GET", "/api/audit")[0], 403)
        st, d = self.call("admin", "GET", "/api/audit")
        actions = {a["action"] for a in d["entries"]}
        self.assertTrue({"warn", "mute", "ban", "unban", "server map", "sign-in"} <= actions, actions)

    def test_15_parsers(self):
        self.assertEqual(tsp.duration_minutes("2w"), 20160)
        self.assertEqual(tsp.engine_length(1440 * 7), "1w")
        self.assertEqual(tsp.engine_length(90), "90m")
        self.assertEqual(tsp.safe_arg('a"b;c\\d^1e\n'), "a b c de")
        self.assertEqual(tsp.host_of("[2a02::1]:27960"), "2a02::1")
        st = tsp.parse_status("  3     7   55 Some Name With Spaces^7          0 1.2.3.4:27960   111 25000 5000\n")
        self.assertEqual(st["players"][3]["name"], "Some Name With Spaces")


if __name__ == "__main__":
    unittest.main(verbosity=2)
