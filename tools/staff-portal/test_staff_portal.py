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


def wait_for(check, timeout=8.0):
    """Polls until check() is true (background loops run on their own clock), then gives up quietly."""
    end = time.time() + timeout
    while time.time() < end:
        if check():
            return True
        time.sleep(0.1)
    return False
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
        self.players = {0: {"name": "Viper^7", "guid": GUID, "ip": "203.0.113.9", "team": 1, "muted": 0, "tk": 0,
                            "xyz": (100.0, 200.0, 50.0)},
                        1: {"name": "[BOT] Rook^7", "guid": "", "ip": "bot", "team": 2, "muted": 0, "tk": 0,
                            "xyz": (-500.0, -900.0, 60.0)}}
        self.cvars = {"g_friendlyFire": "1", "g_password": "", "bot_minplayers": "4", "g_autoBalance": "1",
                      "g_allowVote": "1", "sv_autoDemo": "0", "g_warmup": "20"}

    def answer(self, cmd: str) -> str:
        word, _, rest = cmd.partition(" ")
        if word in self.cvars and not rest:
            return '"%s" is: "%s^7", the default\n' % (word, self.cvars[word])
        if word == "set":
            name, _, value = rest.partition(" ")
            self.cvars[name] = value.strip('"')
            return ""
        if word == "tcp_status":
            out = "TCP_NATIVE_STATUS bits=64 frames=10\n"
            for slot, p in self.players.items():
                out += ("TCP_NATIVE_PLAYER slot=%d begun=1 moves=10 time=1 xyz=%.3f,%.3f,%.3f hp=100 weapon=41 mode=0 clip=30 "
                        "reserve=90 shots=100 hits=80 kills=20 deaths=2 targets=0 team=%d stance=0 stamina=1 head=0 body=0 legs=0\n") % (
                    slot, *p["xyz"], p["team"])
            return out
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
                out += "TCP_STAFF_PLAYER slot=%d begun=1 team=%d spec=0 bot=%d alive=1 muted=%d kills=3 deaths=1 team_kills=%d damage=300 pid=%s name=%s\n" % (
                    slot, p["team"], p["ip"] == "bot", p["muted"], p["tk"], tsp.player_pid(p["guid"]) or "-", p["name"])
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


HOOKS, VOIDED, PUSHES = [], [], []


def totp_now(secret):
    return tsp.totp_code(secret, int(time.time() // 30))


def fake_stats():
    """Stands in for the stats service (tcp_stats.py routes player.json and search.json)."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/webhook":
                HOOKS.append(body)
                out = {}
            elif self.path.startswith("/push/"):
                PUSHES.append((self.path, dict(self.headers)))
                if self.path == "/push/gone":
                    self.send_response(410)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                out = {}
            elif self.path in ("/staff/void", "/staff/unvoid") and self.headers.get("X-Staff-Token") == "tok":
                VOIDED.append((self.path, body))
                out = {"ok": True, "rebuilt": 1}
            else:
                self.send_response(403)
                self.end_headers()
                return
            data = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/staff/review.json" and self.headers.get("X-Staff-Token") == "tok":
                body = {"review": [{"pid": PID, "name": "Viper", "match_id": "00112233aabbccdd", "reason": "accuracy 92%",
                                    "created": "2026-11-12T10:00:00Z"}]}
            elif self.path.startswith("/player.json?id=" + PID):
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


class ShortIpTest(unittest.TestCase):
    def test_request_log_address_is_shortened(self):
        self.assertEqual(tsp.short_ip("203.0.113.77"), "203.0.113.0/24")
        self.assertEqual(tsp.short_ip("2001:db8:1234:5678::1"), "2001:db8:1234::/48")
        self.assertEqual(tsp.short_ip("::ffff:198.51.100.9"), "198.51.100.0/24")
        self.assertEqual(tsp.short_ip("not an address"), "-")


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
               "ban_sync_seconds": 3600, "stats_api": fake_stats(), "owners": ["100000000000000001"], "require_2fa": False, "stats_token": "tok",
               "suspicion_seconds": 3600, "enforce_seconds": 3600, "afk_spectate_seconds": 0,
               "discord_bot_db": str(Path(cls.tmp.name) / "bot.db"),
               "servers": [
                   {"key": "one", "name": "Official #1", "host": "127.0.0.1", "port": cls.game.port, "rcon_password": "pw",
                    "reports_dir": str(reports), "log_file": str(cls.chatlog)},
                   {"key": "two", "name": "Official #2", "host": "127.0.0.1", "port": cls.old.port, "rcon_password": "pw"}]}
        cfg["alerts"] = {"webhook_url": cfg["stats_api"] + "/webhook", "gap_seconds": 0.05}
        import sqlite3
        con = sqlite3.connect(cfg["discord_bot_db"])
        con.execute("CREATE TABLE links(discord_id INTEGER PRIMARY KEY, pid TEXT UNIQUE, name TEXT, linked_at TEXT)")
        con.execute("INSERT INTO links VALUES(?,?,?,?)", (184000000000000001, PID, "viper#0", "2026-11-10T12:00:00Z"))
        con.commit()
        con.close()
        cls.portal = tsp.Portal(cfg)
        cls.portal.start()
        from http.server import ThreadingHTTPServer
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), tsp.make_handler(cls.portal))
        cls.port = cls.httpd.server_address[1]
        cfg["public_url"] = "http://127.0.0.1:%d" % cls.port
        cls.httpd.RequestHandlerClass = tsp.make_handler(cls.portal)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        time.sleep(3.5)
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
        wait_for(lambda: any(l["text"] == "enemy at the gate" for l in self.call("moderator", "GET", "/api/chat?server=one")[1]["lines"]))
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
        self.assertEqual(tsp.resolve_role(self.portal, "700000000000000073", []), None)

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


    # ---------------------------------------------------------------- round two
    def viper_back(self):
        if 0 not in self.game.players:
            self.game.players[0] = {"name": "Viper^7", "guid": GUID, "ip": "203.0.113.9", "team": 1, "muted": 0, "tk": 0,
                                    "xyz": (100.0, 200.0, 50.0)}
        self.game.bans = []
        self.portal.store.x("UPDATE bans SET active=0")
        time.sleep(2.5)

    def test_16_ladder(self):
        self.viper_back()
        st, d = self.call("moderator", "GET", "/api/punish/next?pid=" + PID)
        tk = [x for x in d["steps"] if x["offence"] == "teamkill"][0]
        self.assertEqual((tk["index"], tk["action"]), (0, "Warn"))
        body = {"server": "one", "slot": 0, "name": "Viper", "offence": "teamkill", "note": "spawn"}
        st, d = self.call("moderator", "POST", "/api/punish", body)
        self.assertEqual((st, d.get("action")), (200, "Warn"), d)
        self.assertIn("warn 0 Team killing: spawn", self.game.commands)
        st, d = self.call("moderator", "POST", "/api/punish", body)
        self.assertEqual(d["action"], "Kick", d)
        st, d = self.call("moderator", "POST", "/api/punish", body)
        self.assertEqual((st, d["action"]), (200, "Ban, 1 day"), d)
        self.viper_back()
        st, d = self.call("moderator", "POST", "/api/punish", body)
        self.assertEqual(st, 403, d)                     # step 4 is 7 days: past the moderator limit
        self.assertIn("Ask an admin", d["error"])
        st, d = self.call("admin", "POST", "/api/punish", {"pid": PID, "offence": "teamkill"})
        self.assertEqual((st, d["action"]), (200, "Ban, 7 days"), d)
        self.viper_back()
        # on a 0.35.0 server the warning goes to public chat
        st, d = self.call("moderator", "POST", "/api/punish", {"server": "two", "slot": 0, "offence": "spam"})
        self.assertEqual(d["result"], "warned in public chat", d)
        self.assertTrue(any(c.startswith("say ^8[STAFF]^7 Viper: Spam") for c in self.old.commands))

    def test_17_undo(self):
        self.viper_back()
        st, d = self.call("moderator", "POST", "/api/action", {"action": "mute", "server": "one", "slot": 0, "length": "1h", "reason": "x"})
        self.assertTrue(d["undo"])
        self.assertEqual(self.call("admin", "POST", "/api/undo", {"id": 999999})[0], 404)
        st, r = self.call("moderator", "POST", "/api/undo", {"id": d["undo"]})
        self.assertEqual(st, 200, r)
        self.assertIn("voiceunmute 0", self.game.commands)
        self.assertFalse(self.portal.store.one("SELECT id FROM mutes WHERE active=1"))
        st, d = self.call("moderator", "POST", "/api/bans", {"pid": PID, "length": "2h", "reason": "rage"})
        self.assertEqual(st, 200, d)
        self.assertEqual(self.call("moderator", "POST", "/api/undo", {"id": d["undo"]})[0], 200)
        self.assertFalse(self.portal.store.one("SELECT active FROM bans WHERE id=?", (d["id"],))["active"])
        self.assertEqual(self.call("moderator", "POST", "/api/undo", {"id": d["undo"]})[0], 404)   # once only
        # past the window
        st, d = self.call("moderator", "POST", "/api/bans", {"pid": PID, "length": "2h", "reason": "rage"})
        self.portal.store.x("UPDATE undo SET expires=1 WHERE audit_id=?", (d["undo"],))
        self.assertEqual(self.call("moderator", "POST", "/api/undo", {"id": d["undo"]})[0], 409)
        self.viper_back()

    def test_18_chat_filter(self):
        self.viper_back()
        self.assertEqual(self.call("moderator", "POST", "/api/filters", {"pattern": "noob*", "kind": "word", "action": "mute"})[0], 403)
        self.assertEqual(self.call("admin", "POST", "/api/filters", {"pattern": "(", "kind": "regex", "action": "flag"})[0], 400)
        st, d = self.call("admin", "POST", "/api/filters", {"pattern": "noob*", "kind": "word", "action": "mute", "length": "15m", "note": "Insult"})
        self.assertEqual(st, 200, d)
        st, d = self.call("moderator", "POST", "/api/filters/test", {"text": "you are all N00BS"})
        self.assertEqual(len(d["matches"]), 1)
        self.assertFalse(self.call("moderator", "POST", "/api/filters/test", {"text": "snoobly"})[1]["matches"])
        with self.chatlog.open("a") as f:
            f.write("  1001 TCP_NATIVE_SAY slot=0 team=0 you are all N00BS\n")
        wait_for(lambda: "mute 0 15 Insult" in self.game.commands and
                 self.portal.store.one("SELECT id FROM audit WHERE staff='Chat filter'"))
        self.assertIn("mute 0 15 Insult", self.game.commands)
        st, d = self.call("moderator", "GET", "/api/filters")
        self.assertEqual(d["flagged"][0]["flag"], "Insult")
        self.assertEqual(d["filters"][0]["hits"], 1)
        a = self.portal.store.one("SELECT * FROM audit WHERE staff='Chat filter' ORDER BY id DESC")
        self.assertEqual(a["action"], "mute")

    def test_19_watchlist_and_dodgers(self):
        self.viper_back()
        self.assertEqual(self.call("moderator", "POST", "/api/watchlist", {"pid": PID, "reason": "aim looks odd"})[0], 200)
        self.portal.watch_cache.clear()
        self.portal.online.clear()
        wait_for(lambda: self.portal.store.one("SELECT id FROM alerts WHERE kind='watch' AND pid=?", (PID,)))
        self.assertTrue(self.portal.store.one("SELECT id FROM alerts WHERE kind='watch' AND pid=?", (PID,)))
        st, d = self.call("moderator", "GET", "/api/servers")
        viper = [p for p in d["servers"][0]["players"] if p.get("pid") == PID][0]
        self.assertTrue(viper["watched"])
        # a banned identity on the same anti-cheat account
        self.portal.store.x("INSERT INTO bans(pid,guid,ip,puid,name,reason,created,expires,by_id,by_name,active) VALUES(?,?,?,?,?,?,?,?,?,?,1)",
                            ("aaaaaaaaaaaaaaaa", "G2", "198.51.100.1", "0002aabbccddeeff00112233445566778", "OldViper", "aimbot", 1, 0, "1", "t"))
        self.portal.watch_cache.clear()
        wait_for(lambda: self.portal.store.one("SELECT 1 x FROM flags WHERE pid=? AND kind='ban dodger'", (PID,)))
        f = self.portal.store.one("SELECT * FROM flags WHERE pid=? AND kind='ban dodger'", (PID,))
        self.assertIn("OldViper", f["detail"])
        st, p = self.call("moderator", "GET", "/api/player/" + PID)
        self.assertEqual(p["watch"]["reason"], "aim looks odd")
        self.assertEqual(p["discord"][0]["discord_id"], "184000000000000001")
        score = p["suspicion"]["score"]
        self.assertGreaterEqual(score, 50, p["suspicion"])        # shared account with a banned player + 80% accuracy
        self.assertTrue(any("anti-cheat account" in r for r in p["suspicion"]["reasons"]))
        st, d = self.call("moderator", "GET", "/api/lookup?q=184000000000000001")
        self.assertIn(PID, [x["pid"] for x in d["players"]])
        self.call("moderator", "POST", "/api/watchlist", {"pid": PID, "remove": True})
        self.portal.store.x("UPDATE bans SET active=0")

    def test_20_appeals(self):
        self.viper_back()
        st, d = self.call("admin", "POST", "/api/bans", {"pid": PID, "length": "7d", "reason": "wallhack"})
        code = d["appeal_code"]
        self.assertRegex(code, r"^[A-Z2-9]{6}$")
        self.assertTrue(any(("appeal at 127.0.0.1:%d/appeal code %s" % (self.port, code)) in c for c in self.game.commands))
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/appeal")
        self.assertEqual(c.getresponse().status, 200)
        c.close()

        def public(method, path, body=None):
            c = http.client.HTTPConnection("127.0.0.1", self.port)
            c.request(method, path, body=json.dumps(body) if body else None, headers={"Content-Type": "application/json"})
            r = c.getresponse()
            out = (r.status, json.loads(r.read() or b"{}"))
            c.close()
            return out
        self.assertEqual(public("POST", "/appeal/submit", {"code": "ZZZZZZ", "text": "x" * 30})[0], 404)
        self.assertEqual(public("POST", "/appeal/submit", {"code": code, "text": "short"})[0], 400)
        st, r = public("POST", "/appeal/submit", {"code": code.lower(), "text": "I was not cheating, check the demo please.", "contact": "viper#0"})
        self.assertEqual(st, 201, r)
        self.assertEqual(public("POST", "/appeal/submit", {"code": code, "text": "Again, I was not cheating at all."})[0], 409)
        st, r = public("GET", "/appeal/status?code=" + code)
        self.assertEqual(r["appeal"]["status"], "open")
        st, d = self.call("moderator", "GET", "/api/reports?status=open&source=appeal")
        rep = d["reports"][0]
        self.assertEqual(rep["data"]["contact"], "viper#0")
        body = {"id": rep["data"]["appeal_id"], "decision": "accept", "answer": "Demo checked, you are clean."}
        self.assertEqual(self.call("moderator", "POST", "/api/appeals/answer", body)[0], 403)
        st, r = self.call("admin", "POST", "/api/appeals/answer", body)      # the admin made this ban: someone else answers
        self.assertEqual(st, 403, r)
        self.assertIn("You made this ban", r["error"])
        self.assertEqual(self.call("owner", "POST", "/api/appeals/answer", body)[0], 200)
        st, r = public("GET", "/appeal/status?code=" + code)
        self.assertEqual((r["appeal"]["status"], r["ban"]["active"]), ("accepted", False))
        self.assertEqual(r["appeal"]["answer"], "Demo checked, you are clean.")
        self.assertTrue(self.portal.store.one("SELECT id FROM alerts WHERE kind='appeal'"))

    def test_21_schedule(self):
        self.viper_back()
        self.assertEqual(self.call("moderator", "POST", "/api/schedule", {"server": "one", "action": "map", "map": "obj_snow", "at": int(time.time())})[0], 403)
        st, d = self.call("moderator", "POST", "/api/schedule", {"server": "*", "action": "say", "text": "Tournament at 20:00",
                                                                 "at": int(time.time()), "every_min": 30})
        self.assertEqual(st, 200, d)
        self.assertEqual(self.portal.run_schedule(), 1)
        self.assertTrue(any(c.startswith("staffsay Moderator Tournament at 20:00") for c in self.game.commands))
        job = self.portal.store.one("SELECT * FROM schedule WHERE id=?", (d["id"],))
        self.assertTrue(job["active"])
        self.assertGreater(job["next_at"], time.time() + 25 * 60)
        self.assertEqual(self.call("moderator", "POST", "/api/schedule/cancel", {"id": d["id"]})[0], 200)
        st, d = self.call("admin", "POST", "/api/schedule", {"server": "one", "action": "nextmap", "at": int(time.time())})
        self.portal.run_schedule()
        self.assertFalse(self.portal.store.one("SELECT active FROM schedule WHERE id=?", (d["id"],))["active"])

    def test_22_event_and_settings(self):
        st, d = self.call("admin", "POST", "/api/event", {"server": "one", "action": "start", "note": "Clan cup"})
        self.assertEqual(st, 200, d)
        self.assertEqual(self.game.cvars["g_password"], d["password"])
        self.assertEqual(self.game.cvars["bot_minplayers"], "0")
        self.assertEqual(self.call("admin", "POST", "/api/cvars", {"server": "one", "cvar": "bot_minplayers", "value": "2"})[0], 409)
        self.game.cvars["g_password"] = ""                 # the server restarted mid-event
        self.portal.enforce()
        self.assertEqual(self.game.cvars["g_password"], d["password"])
        st, _ = self.call("admin", "POST", "/api/event", {"server": "one", "action": "stop"})
        self.assertEqual((self.game.cvars["g_password"], self.game.cvars["bot_minplayers"]), ("", "4"))
        # config editor
        self.assertEqual(self.call("moderator", "GET", "/api/cvars?server=one")[0], 403)
        self.assertEqual(self.call("admin", "POST", "/api/cvars", {"server": "one", "cvar": "rconpassword", "value": "x"})[0], 400)
        self.assertEqual(self.call("admin", "POST", "/api/cvars", {"server": "one", "cvar": "g_warmup", "value": "1;quit"})[0], 400)
        st, d = self.call("admin", "POST", "/api/cvars", {"server": "one", "cvar": "g_friendlyFire", "value": "0", "keep": True})
        self.assertEqual((st, d["old"], self.game.cvars["g_friendlyFire"]), (200, "1", "0"), d)
        self.game.cvars["g_friendlyFire"] = "1"
        self.portal.enforce()
        self.assertEqual(self.game.cvars["g_friendlyFire"], "0")
        st, v = self.call("admin", "GET", "/api/cvars?server=one")
        ff = [c for c in v["cvars"] if c["name"] == "g_friendlyFire"][0]
        self.assertEqual((ff["value"], ff["kept"]), ("0", "0"))
        st, d = self.call("admin", "POST", "/api/cvars/rollback", {"id": [h for h in v["history"] if h["kind"] == "set"][0]["id"]})
        self.assertEqual((st, self.game.cvars["g_friendlyFire"]), (200, "1"))
        self.game.cvars["g_friendlyFire"] = "1"
        self.portal.enforce()
        self.assertEqual(self.game.cvars["g_friendlyFire"], "1")           # a rollback releases the kept value

    def test_23_live_map(self):
        self.viper_back()
        self.assertEqual(self.call("moderator", "GET", "/api/positions?server=one")[0], 403)
        st, d = self.call("admin", "GET", "/api/positions?server=one")
        self.assertEqual(st, 200, d)
        self.assertEqual(d["layout"]["image"], "/static/maps/layout-village.webp")
        viper = [p for p in d["players"] if p["slot"] == 0][0]
        self.assertTrue(0 <= viper["u"] <= 1 and 0 <= viper["v"] <= 1, viper)
        self.call("admin", "GET", "/api/positions?server=one")
        n = self.portal.store.one("SELECT COUNT(*) n FROM audit WHERE action='live map' AND staff='Admin'")["n"]
        self.assertEqual(n, 1)                                              # once per session and server
        st, d = self.call("moderator", "GET", "/api/servers")
        self.assertNotIn("x", d["servers"][0]["players"][0])               # positions never reach the normal view

    def test_24_two_step_sign_in(self):
        self.portal.cfg["require_2fa"] = True
        try:
            st, d = self.call("admin", "GET", "/api/audit")
            self.assertEqual(st, 403)
            st, d = self.call("admin", "POST", "/api/2fa/setup", {})
            secret = d["secret"]
            self.assertTrue(d["uri"].startswith("otpauth://totp/"))
            self.assertTrue(d["qr"].startswith("data:image/svg+xml;base64,"))   # drawn here: the CSP allows data: images only
            self.assertEqual(self.call("admin", "POST", "/api/2fa/enable", {"code": "000000"})[0], 400)
            code = totp_now(secret)
            self.assertEqual(self.call("admin", "POST", "/api/2fa/enable", {"code": code})[0], 200)
            self.assertEqual(self.call("admin", "GET", "/api/audit")[0], 200)
            # a new session must give a code first, and a code is never accepted twice
            fresh = self.login("admin")
            saved = self.sessions["admin"]
            self.sessions["admin"] = fresh
            st, me = self.call("admin", "GET", "/api/me")
            self.assertTrue(me["mfa_pending"])
            self.assertEqual(self.call("admin", "GET", "/api/servers")[0], 401)
            self.assertEqual(self.call("admin", "POST", "/api/2fa/verify", {"code": code})[0], 400)
            later = tsp.totp_code(secret, int(time.time() // 30) + 1)
            self.assertEqual(self.call("admin", "POST", "/api/2fa/verify", {"code": later})[0], 200)
            self.assertEqual(self.call("admin", "GET", "/api/servers")[0], 200)
            self.assertEqual(self.call("admin", "POST", "/api/2fa/disable", {"code": tsp.totp_code(secret, int(time.time() // 30) + 2)})[0], 409)
            self.sessions["admin"] = saved
            # the owner resets a lost phone
            self.assertEqual(self.call("admin", "POST", "/api/2fa/reset", {"discord_id": "dev-admin"})[0], 403)
            self.portal.cfg["require_2fa"] = False
            self.assertEqual(self.call("owner", "POST", "/api/2fa/reset", {"discord_id": "dev-admin"})[0], 200)
            self.sessions["admin"] = self.login("admin")
        finally:
            self.portal.cfg["require_2fa"] = False

    def test_25_weekly_alerts_review_demo(self):
        st, w = self.call("admin", "GET", "/api/weekly")
        self.assertEqual(st, 200, w)
        self.assertGreaterEqual(w["actions"]["ban"], 1)
        self.assertIn("**Actions**", w["text"])
        self.portal.alert("weekly", "Staff report", w["text"])
        for _ in range(60):
            if any(h["embeds"][0]["title"] == "Staff report" for h in HOOKS):
                break
            time.sleep(0.25)
        self.assertTrue(any(h["embeds"][0]["title"] == "Staff report" for h in HOOKS), HOOKS)
        self.assertEqual(HOOKS[0]["allowed_mentions"]["parse"], [])
        st, d = self.call("moderator", "GET", "/api/alerts")
        self.assertTrue(d["webhook"] and d["alerts"])
        # stats review queue through the stats service's staff routes
        self.assertEqual(self.call("moderator", "GET", "/api/review")[0], 403)
        st, d = self.call("admin", "GET", "/api/review")
        self.assertEqual(d["review"][0]["reason"], "accuracy 92%")
        st, d = self.call("admin", "POST", "/api/review", {"action": "void", "kind": "match", "id": "00112233aabbccdd", "reason": "aimbot"})
        self.assertEqual((st, VOIDED[-1][0]), (200, "/staff/void"))
        # the server demo that covers a report
        demos = Path(self.tmp.name) / "svdemos"
        demos.mkdir(exist_ok=True)
        f = demos / "Test_2026-11-12-09-50-00_obj_village.sv_84"
        f.write_bytes(b"demo" * 100)
        os.utime(f, (1794477600 + 3600, 1794477600 + 3600))
        rid = self.portal.store.one("SELECT id FROM reports WHERE source='player'")["id"]
        st, d = self.call("moderator", "GET", "/api/demo?report=%d" % rid)
        self.assertEqual((st, d["offset_s"]), (200, 600), d)
        st, raw = self.call("moderator", "GET", "/api/demo/file?report=%d" % rid)
        self.assertEqual(raw, b"demo" * 100)


    def test_26_audit_fixes(self):
        # owner rights come from the config only, never from a leftover staff row
        self.portal.store.x("INSERT INTO staff(discord_id,name,role,note,added_by,created) VALUES('710000000000000072','Old','owner','','x',0)")
        self.assertIsNone(tsp.resolve_role(self.portal, "710000000000000072", []))
        self.assertEqual(tsp.resolve_role(self.portal, "100000000000000001", []), "owner")
        # an admin cannot revoke another admin, also when that admin's rights come from a Discord role
        self.portal.store.x("INSERT INTO sessions(id,discord_id,name,avatar,role,csrf,created,seen,checked,token,ip) "
                            "VALUES('x1','700000000000000073','Disco','','admin','c',?,?,?,'dev','')", (int(time.time()),) * 3)
        st, r = self.call("admin", "POST", "/api/staff", {"discord_id": "700000000000000073", "role": "revoked"})
        self.assertEqual(st, 403, r)
        # a staff member who plays on a server cannot open its live map (Discord account linked to Viper, who is on "one")
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/auth/dev?role=admin&name=Player&id=184000000000000001")
        cookie = c.getresponse().getheader("Set-Cookie").split(";")[0]
        c.close()
        self.viper_back()
        st, r = self.call(None, "GET", "/api/positions?server=one", cookie=cookie)
        self.assertEqual(st, 403, r)
        self.assertIn("playing on this server", r["error"])
        # scheduled jobs of revoked staff stop
        self.portal.store.x("INSERT INTO staff(discord_id,name,role,note,added_by,created) VALUES('700000000000000074','Gone','revoked','','x',0)")
        jid = self.portal.store.x("INSERT INTO schedule(server,action,arg,next_at,every_min,until,created,by_name,by_id) "
                                  "VALUES('one','say','hello',?,0,0,?,'Gone','700000000000000074')", (int(time.time()) - 5, int(time.time())))
        before = len(self.game.commands)
        self.portal.run_schedule()
        job = self.portal.store.one("SELECT * FROM schedule WHERE id=?", (jid,))
        self.assertEqual(job["active"], 0)
        self.assertIn("no longer has staff access", job["last_result"])
        self.assertFalse(any("hello" in c for c in self.game.commands[before:]))
        # event mode stays on when the server does not take the old values back
        who = {"discord_id": "1", "name": "Admin", "role": "admin"}
        srv = self.portal.server("one")
        self.portal.event_start(who, srv)
        real = srv.set_cvar

        def down(name, value):
            raise tsp.RconError("no answer")
        srv.set_cvar = down
        with self.assertRaises(tsp.ApiError):
            self.portal.event_stop(who, srv)
        self.assertTrue(self.portal.store.one("SELECT server FROM events WHERE server='one'"))
        srv.set_cvar = real
        self.assertTrue(self.portal.event_stop(who, srv)["ok"])
        self.assertEqual(self.game.cvars["g_password"], "")
        # filters that could stall the chat feed are refused
        st, r = self.call("admin", "POST", "/api/filters", {"pattern": "(a+)+", "kind": "regex", "action": "flag"})
        self.assertEqual(st, 400, r)
        self.assertIn("Simplify", r["error"])
        # bug report senders are tagged with a keyed hash, not a plain hash of the address
        tag = self.portal.ip_tag("127.0.0.1")
        self.assertNotEqual(tag, __import__("hashlib").sha256(b"127.0.0.1").hexdigest()[:12])
        self.assertEqual(tag, self.portal.ip_tag("127.0.0.1"))

    def test_27_second_audit(self):
        # a player name that carries the chat marker inside another log line is not chat
        before = self.portal.store.one("SELECT COUNT(*) n FROM chat")["n"]
        for line in ('    3450 broadcast: print "TCP_NATIVE_SAY slot=0 team=0 n00b^7 connected\\n"',
                     "   73451 ClientUserinfoChanged: 2 n\\TCP_NATIVE_SAY slot=0 team=0 n00b"):
            self.portal._chat_line(self.portal.server("one"), line)
        self.assertEqual(self.portal.store.one("SELECT COUNT(*) n FROM chat")["n"], before)
        self.portal._chat_line(self.portal.server("one"), "\x1b[0m   73452 TCP_NATIVE_SAY slot=0 team=0 real line\x1b[0m")
        self.assertEqual(self.portal.store.one("SELECT text FROM chat ORDER BY id DESC LIMIT 1")["text"], "real line")
        # the event password is for admins only
        self.portal.event_start({"discord_id": "1", "name": "Admin", "role": "admin"}, self.portal.server("one"), password="cup2026")
        try:
            ev = self.call("moderator", "GET", "/api/event")[1]["events"][0]
            self.assertEqual(ev["password"], "")
            self.assertNotIn("g_password", ev["preset"])
            self.assertEqual(self.call("admin", "GET", "/api/event")[1]["events"][0]["password"], "cup2026")
        finally:
            self.portal.event_stop({"discord_id": "1", "name": "Admin", "role": "admin"}, self.portal.server("one"))
        # 20 wrong two-step codes in a day end every session of that account
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/auth/dev?role=moderator&name=Lock&id=lockme")
        cookie = c.getresponse().getheader("Set-Cookie").split(";")[0]
        c.close()
        csrf = self.call(None, "GET", "/api/me", cookie=cookie)[1]["csrf"]

        def post(path, body):
            c = http.client.HTTPConnection("127.0.0.1", self.port)
            c.request("POST", path, body=json.dumps(body), headers={"Cookie": cookie, "X-CSRF": csrf, "Content-Type": "application/json"})
            r = c.getresponse()
            out = r.status, json.loads(r.read() or b"{}")
            c.close()
            return out
        secret = post("/api/2fa/setup", {})[1]["secret"]
        self.assertEqual(post("/api/2fa/enable", {"code": totp_now(secret)})[0], 200)
        self.portal.rate["2fa-day:lockme"] = [time.time()] * 20
        st, r = post("/api/2fa/verify", {"code": "000000"})
        self.assertEqual(st, 401, r)
        self.assertFalse(self.portal.store.one("SELECT id FROM sessions WHERE discord_id='lockme'"))
        self.assertTrue(self.portal.store.one("SELECT id FROM alerts WHERE key='2fa-lock:lockme'"))
        # an offline server answers the settings page quickly
        st, v = self.call("admin", "GET", "/api/cvars?server=two")
        self.assertEqual(st, 200)

    def test_28_third_audit(self):
        who = {"discord_id": "1", "name": "Admin", "role": "admin"}
        # two players behind one address: lifting one ban keeps the other on the servers
        a = self.portal.ban_player(who, {"pid": "aaaaaaaaaaaaaaaa", "guid": "A" * 32, "ip": "198.51.100.7", "name": "Twin A"}, 0, "cheating")
        b = self.portal.ban_player(who, {"pid": "bbbbbbbbbbbbbbbb", "guid": "B" * 32, "ip": "198.51.100.7", "name": "Twin B"}, 0, "cheating")
        before = len(self.game.commands)
        self.portal.lift_ban(who, self.portal.store.one("SELECT * FROM bans WHERE id=?", (a["id"],)), "appeal")
        after = self.game.commands[before:]
        self.assertTrue(any(c.startswith("unban 198.51.100.7") for c in after))
        self.assertTrue(any(c.startswith("banip 198.51.100.7") for c in after), after)
        self.assertTrue(any(c.startswith("banguid " + "B" * 32) for c in after))
        self.portal.lift_ban(who, self.portal.store.one("SELECT * FROM bans WHERE id=?", (b["id"],)), "test over")
        # an appeal is closed by answering it, never by the plain Close button
        rep = self.portal.store.one("SELECT id FROM reports WHERE source='appeal' ORDER BY id DESC LIMIT 1")
        if rep:
            st, r = self.call("admin", "POST", "/api/reports/update", {"id": rep["id"], "status": "closed"})
            self.assertEqual(st, 409, r)
        # event mode never stays half switched on
        srv = self.portal.server("one")
        real, calls = srv.set_cvar, []

        def flaky(name, value):
            calls.append(name)
            if len(calls) == 2:
                raise tsp.RconError("no answer")
            return real(name, value)
        old_pw = self.game.cvars.get("g_password", "")
        srv.set_cvar = flaky
        try:
            with self.assertRaises(tsp.ApiError):
                self.portal.event_start(who, srv, password="half2026")
        finally:
            srv.set_cvar = real
        self.assertFalse(self.portal.store.one("SELECT server FROM events WHERE server='one'"))
        self.assertEqual(self.game.cvars.get("g_password", ""), old_pw)
        # settings the server does not have are skipped, not created
        self.portal.cfg["event_preset"] = dict(tsp.EVENT_PRESET, g_madeUpSetting="1")
        try:
            r = self.portal.event_start(who, srv)
            self.assertNotIn("g_madeUpSetting", r["preset"])
            self.assertNotIn("g_madeUpSetting", self.game.cvars)
            self.portal.event_stop(who, srv)
        finally:
            self.portal.cfg.pop("event_preset")

    def test_29_webhook_url_checked(self):
        alerts = self.portal.cfg["alerts"]
        saved = alerts["webhook_url"]
        try:
            for bad in ("file:///etc/passwd", "http://example.com/hook", "https://evil.example/api/webhooks/1/x"):
                alerts["webhook_url"] = bad
                self.assertEqual(self.portal.webhook_url(), "")
            alerts["webhook_url"] = "https://discord.com/api/webhooks/123456/abc-DEF_9"
            self.assertTrue(self.portal.webhook_url())
        finally:
            alerts["webhook_url"] = saved

    def test_30_qr_code(self):
        uri = "otpauth://totp/TrueCombat%20Staff%3AViper?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP&issuer=TrueCombat%20Staff&digits=6&period=30"
        for text, size in (("A", 21), (uri, 4 * 8 + 17), ("x" * 200, 4 * 10 + 17)):
            m = tsp.qr_matrix(text)
            self.assertEqual(len(m), size)
            self.assertEqual(tsp.qr_matrix(text), m)                           # the same text always gives the same symbol
            for cx, cy in ((0, 0), (size - 7, 0), (0, size - 7)):              # three finder patterns
                ring = [m[cy + i][cx] for i in range(7)]
                self.assertEqual(ring, [True] * 7)
                self.assertTrue(m[cy + 3][cx + 3] and not m[cy + 1][cx + 1])
            self.assertEqual([m[6][x] for x in range(8, size - 8)], [x % 2 == 0 for x in range(8, size - 8)])   # timing
            # format bits: undo the mask, check the BCH code and that the level is M (00)
            bits = [m[i][8] for i in (0, 1, 2, 3, 4, 5, 7, 8)] + [m[8][7]] + [m[8][14 - i] for i in range(9, 15)]
            word = sum(1 << i for i, b in enumerate(bits) if b) ^ 0x5412
            data = word >> 10
            rem = data
            for _ in range(10):
                rem = (rem << 1) ^ ((rem >> 9) * 0x537)
            self.assertEqual(word, (data << 10) | rem)
            self.assertEqual(data >> 3, 0)
        svg = tsp.qr_svg_data_uri(uri)
        import base64
        body = base64.b64decode(svg.split(",", 1)[1]).decode()
        self.assertIn('viewBox="0 0 57 57"', body)                              # 49 modules plus the quiet zone
        with self.assertRaises(ValueError):
            tsp.qr_matrix("x" * 3000)

    def test_31_f12_bug_report(self):
        import base64
        jpg = b"\xff\xd8\xff\xe0" + b"\0" * 2000 + b"\xff\xd9"
        self.portal.servers["one"].cfg["public_address"] = "127.0.0.1:27960"
        sample = {"format": "tcp-bugreport/1", "category": "bug", "text": "Grenade went through the wall\nat the bomb site.",
                  "map": "obj_snow", "pos": [120.5, -64, 32], "server": "127.0.0.1:27960", "build": "0.36.0-sandbox28",
                  "renderer": "DX12 RTX 4080 SUPER", "time": 1789000000, "ping": 38, "fps": 240,
                  "hw": {"cpu": "Ryzen 7 7800X3D", "ram": "32 GB"}, "console": "line\x07 one\nline two\n" * 50,
                  "screenshot_jpg": base64.b64encode(jpg).decode(), "name": "Viper", "guid": GUID, "puid": "0002abc", "match": "m-77"}
        def post(body, ctype="application/json"):
            self.portal.rate.pop("bug:127.0.0.1", None)
            c = http.client.HTTPConnection("127.0.0.1", self.port)
            c.request("POST", "/api/bugreport", body=body, headers={"Content-Type": ctype})
            r = c.getresponse()
            out = r.status, json.loads(r.read() or b"{}")
            c.close()
            return out
        st, d = post(json.dumps(sample))
        self.assertEqual(st, 201)
        st, lst = self.call("moderator", "GET", "/api/reports?status=open&source=bug")
        r = [x for x in lst["reports"] if x["file"] == d["id"]][0]
        self.assertEqual(r["target_pid"], PID)                              # linked to the player's profile
        self.assertEqual(r["data"]["server_name"], "Official #1")
        self.assertEqual(r["data"]["category"], "Bug")
        self.assertEqual(r["data"]["pos"], [120, -64, 32])
        self.assertTrue(r["data"]["shot"] and r["data"]["has_console"])
        self.assertNotIn("console", r["data"])                              # the list stays light
        self.assertNotIn("guid", r["data"])                                 # the raw guid is never stored
        st, full = self.call("moderator", "GET", "/api/reports/bug?id=%d" % r["id"])
        self.assertIn("line one", full["report"]["data"]["console"])        # control characters removed
        self.assertEqual(full["report"]["data"]["hw"]["cpu"], "Ryzen 7 7800X3D")
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/api/reports/bugshot?id=%d" % r["id"], headers={"Cookie": self.sessions["moderator"]["cookie"]})
        resp = c.getresponse()
        self.assertEqual((resp.status, resp.getheader("Content-Type"), resp.read()), (200, "image/jpeg", jpg))
        self.assertIn("max-age", resp.getheader("Cache-Control"))          # the inbox refresh doesn't fetch it again
        c.close()
        self.assertEqual(self.call(None, "GET", "/api/reports/bugshot?id=%d" % r["id"])[0], 401)
        self.assertTrue(self.portal.store.one("SELECT id FROM alerts WHERE kind='bugreport' AND key=?", ("bugreport:" + PID,)))
        n = self.portal.store.one("SELECT COUNT(*) n FROM alerts WHERE kind='bugreport'")["n"]
        self.assertEqual(post(json.dumps(sample))[0], 201)                      # same player again: no second alert yet
        self.assertEqual(self.portal.store.one("SELECT COUNT(*) n FROM alerts WHERE kind='bugreport'")["n"], n)
        # player text can't smuggle links or mentions into the staff Discord
        st, d4 = post(json.dumps(dict(sample, text="[free skins](https://evil.example) @everyone", screenshot_jpg="", guid="")))
        a = self.portal.store.one("SELECT title, text FROM alerts WHERE key=?", (d4["id"],))
        self.assertNotIn("](", a["text"])
        self.assertNotIn("https://", a["text"])
        self.assertIn("\\@everyone", a["text"])
        # screenshot storage has a ceiling; past it the report still arrives without its picture
        self.portal.cfg["bugshot_max_mb"] = 0
        try:
            st, d5 = post(json.dumps(sample))
            self.assertEqual(st, 201)
            r5 = json.loads(self.portal.store.one("SELECT data FROM reports WHERE file=?", (d5["id"],))["data"])
            self.assertTrue(r5.get("shot_dropped") and not r5.get("shot"))
        finally:
            self.portal.cfg.pop("bugshot_max_mb", None)
        # a non-JPEG screenshot is dropped, the report still arrives; junk is refused
        st, d2 = post(json.dumps(dict(sample, screenshot_jpg=base64.b64encode(b"<svg/>").decode(), server="evil host")))
        self.assertEqual(st, 201)
        r2 = self.portal.store.one("SELECT data FROM reports WHERE file=?", (d2["id"],))
        self.assertNotIn("shot", json.loads(r2["data"]))
        self.assertNotIn("server", json.loads(r2["data"]))
        self.assertEqual(post(json.dumps({"format": "other", "text": "x" * 20}))[0], 400)
        self.assertEqual(post("{not json")[0], 400)
        self.assertEqual(post(json.dumps(dict(sample, text="hi")))[0], 400)
        self.assertEqual(post(json.dumps(dict(sample, console="x" * 1700 * 1024)))[0], 413)
        st, d3 = post("Old style plain text report about the menu.", "text/plain")
        self.assertEqual(st, 201)
        # closed and pruned reports take their screenshot with them
        self.portal.store.x("DELETE FROM reports WHERE file=?", (d["id"],))
        shot = self.portal.bugshot_path(d["id"])
        os.utime(shot, (time.time() - 7200, time.time() - 7200))
        self.portal.prune_bugshots()
        self.assertFalse(shot.exists())

    def test_32_staff_keys(self):
        keyfile = Path(self.tmp.name) / "staffkeys.txt"
        self.portal.servers["one"].cfg["staff_keys_file"] = str(keyfile)
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/auth/dev?role=moderator&name=Keyholder&id=555000000000000001")
        r = c.getresponse(); r.read(); c.close()
        cookie = r.getheader("Set-Cookie").split(";")[0]
        me = self.call(None, "GET", "/api/me", cookie=cookie)[1]
        self.sessions["keyholder"] = {"cookie": cookie, "csrf": me["csrf"]}
        def as_mod(method, path, body=None):
            return self.call("keyholder", method, path, body)
        self.assertIsNone(as_mod("GET", "/api/staffkey")[1]["key"])
        self.assertEqual(as_mod("POST", "/api/staffkey", {"public": "zz"})[0], 400)
        self.assertEqual(as_mod("POST", "/api/staffkey", {"public": "0" * 64})[0], 400)
        st, k1 = as_mod("POST", "/api/staffkey", {"public": "ab" * 32})
        self.assertEqual(st, 201)
        self.assertRegex(k1["id"], r"^k[0-9a-f]{10}$")
        text = keyfile.read_text()
        self.assertIn("TCPSTAFFKEY1 %s 1 %s Keyholder" % (k1["id"], "ab" * 32), text)
        self.assertIn("staffkeys_reload", self.game.commands)                     # the server reloads at once
        st, k = as_mod("GET", "/api/staffkey")
        self.assertTrue(k["active"] and k["key"]["id"] == k1["id"] and k["servers"] == 1)
        # a new key replaces the old one
        st, k2 = as_mod("POST", "/api/staffkey", {"public": "cd" * 32})
        text = keyfile.read_text()
        self.assertNotIn(k1["id"], text)
        self.assertIn(k2["id"], text)
        # one moderator can't revoke another's key; an admin can, and so can the owner of the key
        st, other = self.call("moderator", "POST", "/api/staffkey", {"public": "ef" * 32})
        self.assertEqual(as_mod("POST", "/api/staffkey/revoke", {"id": other["id"]})[0], 403)
        st, lst = self.call("admin", "GET", "/api/staffkeys")
        self.assertEqual({x["id"] for x in lst["keys"]}, {k2["id"], other["id"]})
        self.assertEqual(self.call("admin", "POST", "/api/staffkey/revoke", {"id": other["id"]})[0], 200)
        self.assertNotIn(other["id"], keyfile.read_text())
        # not signing in for a long time makes a key inactive
        self.portal.store.x("UPDATE staff SET last_login=? WHERE discord_id='555000000000000001'", (int(time.time()) - 90 * 86400,))
        self.portal.publish_staff_keys()
        self.assertNotIn(k2["id"], keyfile.read_text())
        self.portal.store.x("UPDATE staff SET last_login=? WHERE discord_id='555000000000000001'", (int(time.time()),))
        self.portal.publish_staff_keys()
        self.assertIn(k2["id"], keyfile.read_text())
        # removing someone's access revokes their key
        self.assertEqual(self.call("admin", "POST", "/api/staff", {"discord_id": "555000000000000001", "role": "revoked", "name": "Keyholder"})[0], 200)
        self.assertNotIn(k2["id"], keyfile.read_text())
        self.assertFalse(self.portal.store.one("SELECT 1 x FROM staff_keys WHERE revoked=0 AND discord_id='555000000000000001'"))
        self.call("admin", "POST", "/api/staff", {"discord_id": "555000000000000001", "role": "discord"})

    def test_33_launcher_installs_staff_key(self):
        keyfile = Path(self.tmp.name) / "staffkeys.txt"
        self.portal.servers["one"].cfg["staff_keys_file"] = str(keyfile)
        self.portal.rate.pop("staffkey:dev-admin", None)
        st, r = self.call("admin", "POST", "/api/staffkey/link", {})
        self.assertEqual(st, 200)
        self.assertRegex(r["link"], r"^truecombat://staffkey/[0-9a-f]{32}$")
        code = r["link"].rsplit("/", 1)[1]
        def claim(body):
            self.portal.rate.pop("keyclaim:127.0.0.1", None)
            c = http.client.HTTPConnection("127.0.0.1", self.port)
            c.request("POST", "/api/staffkey/claim", body=json.dumps(body), headers={"Content-Type": "application/json"})
            resp = c.getresponse()
            out = resp.status, json.loads(resp.read() or b"{}")
            c.close()
            return out
        self.assertEqual(claim({"code": code, "public": "nope"})[0], 400)          # malformed: the code survives
        st, k = claim({"code": code, "public": "12" * 32})
        self.assertEqual(st, 201)
        self.assertIn("TCPSTAFFKEY1 %s 1 %s" % (k["id"], "12" * 32), keyfile.read_text())
        self.assertEqual(claim({"code": code, "public": "34" * 32})[0], 410)        # single use
        self.assertEqual(self.call("admin", "GET", "/api/staffkey")[1]["key"]["id"], k["id"])
        # an expired link does nothing
        st, r = self.call("admin", "POST", "/api/staffkey/link", {})
        self.portal.store.x("UPDATE staff_key_codes SET expires=?", (int(time.time()) - 1,))
        self.assertEqual(claim({"code": r["link"].rsplit("/", 1)[1], "public": "56" * 32})[0], 410)
        # a link made before someone lost access does nothing either
        st, r = self.call("admin", "POST", "/api/staffkey/link", {})
        saved = self.portal.store.q("SELECT * FROM sessions WHERE discord_id='dev-admin'")
        self.portal.store.x("DELETE FROM sessions WHERE discord_id='dev-admin'")
        try:
            self.assertEqual(claim({"code": r["link"].rsplit("/", 1)[1], "public": "78" * 32})[0], 403)
        finally:
            for row in saved:
                self.portal.store.x("INSERT INTO sessions(%s) VALUES(%s)" % (",".join(row.keys()), ",".join("?" * len(row))), tuple(row))

    def test_34_game_sample_report(self):
        """The exact sample the 0.36.0 game sends (tools/bugreport/sample.json on the game branch)."""
        body = (Path(__file__).resolve().parent / "test_bugreport_sample.json").read_bytes()
        self.portal.rate.pop("bug:127.0.0.1", None)
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("POST", "/api/bugreport", body=body, headers={"Content-Type": "application/json; charset=utf-8",
                                                               "User-Agent": "TrueCombat-Platinum-BugReport/1"})
        r = c.getresponse()
        out = json.loads(r.read())
        c.close()
        self.assertEqual(r.status, 201)
        d = json.loads(self.portal.store.one("SELECT data FROM reports WHERE file=?", (out["id"],))["data"])
        self.assertEqual(d["name"], "Example")                                   # colour codes gone
        self.assertEqual(d["server_label"], "TrueCombat Platinum | Example")    # not ours: kept as reported
        self.assertTrue(d["shot"] and d["console"] and d["hw"] and d["match"] and d["puid"])
        self.assertNotIn("^3", d["console"])
    def test_40_dashboard_and_search(self):
        wait_for(lambda: self.portal.servers["one"].view().get("online"))
        self.portal.record_samples(force=True)
        self.assertGreaterEqual(self.portal.store.one("SELECT COUNT(*) n FROM samples")["n"], 2)
        code, d = self.call("moderator", "GET", "/api/dashboard")
        self.assertEqual(code, 200)
        self.assertEqual(len(d["servers"]), 2)
        self.assertIn("reports", d)
        self.assertNotIn("backup", d)                       # admin only
        self.assertTrue(d["spark"])
        self.assertGreaterEqual(d["players_online"], 1)
        self.assertIn("backup", self.call("owner", "GET", "/api/dashboard")[1])
        self.assertEqual(self.call(None, "GET", "/api/dashboard")[0], 401)
        # search: online player, a ban by its appeal code and by number, a report by number
        code, r = self.call("moderator", "GET", "/api/search?q=vip")
        self.assertEqual(code, 200)
        self.assertTrue(any(o["name"] == "Viper" for o in r["online"]))
        bid = self.portal.store.x("INSERT INTO bans(pid,guid,ip,puid,name,reason,created,expires,by_name,appeal_code,active) "
                                  "VALUES('aaaaaaaaaaaaaaaa','','','','Searchable','spam',1,0,'t','QWERTZ',0)")
        self.assertEqual(self.call("moderator", "GET", "/api/search?q=qwertz")[1]["bans"][0]["id"], bid)
        self.assertEqual(self.call("moderator", "GET", "/api/search?q=%23" + str(bid))[1]["bans"][0]["name"], "Searchable")
        rid = self.portal.store.one("SELECT MIN(id) i FROM reports")["i"]
        self.assertEqual(self.call("moderator", "GET", "/api/search?q=%d" % rid)[1]["reports"][0]["id"], rid)
        self.assertEqual(self.call("moderator", "GET", "/api/search?q=searchable")[1]["staff"], [])   # staff list: admins only
        self.assertEqual(self.call("moderator", "GET", "/api/search?q=")[1]["players"], [])

    def test_41_addresses_only_for_admins(self):
        wait_for(lambda: self.portal.servers["one"].view().get("players"))
        mod = [p for s in self.call("moderator", "GET", "/api/servers")[1]["servers"] for p in s["players"] if not p["bot"]]
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/auth/dev?role=admin&id=dev-admin-ip&name=IpAdmin")
        cookie = c.getresponse().getheader("Set-Cookie").split(";")[0]
        c.close()
        adm = [p for s in self.call(None, "GET", "/api/servers", cookie=cookie)[1]["servers"] for p in s["players"] if not p["bot"]]
        self.assertTrue(mod and adm)
        self.assertTrue(all("ip" not in p and "guid" not in p for p in mod))
        self.assertTrue(any(p.get("ip") for p in adm))
        self.assertTrue(self.portal.servers["one"].view()["players"][0].get("ip") is not None)   # the snapshot itself is untouched

    def test_42_database_snapshot(self):
        import sqlite3
        self.assertEqual(self.call("moderator", "GET", "/api/backup")[0], 403)
        code, st = self.call("owner", "POST", "/api/backup", {})
        self.assertEqual(code, 200)
        self.assertTrue(st["ok"], st)
        con = sqlite3.connect(st["file"])
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)     # no sign-in tokens leave
            self.assertGreater(con.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 0)
        finally:
            con.close()
        self.assertGreater(self.portal.store.one("SELECT COUNT(*) n FROM sessions")["n"], 0)   # the live database keeps them
        self.assertEqual(oct(os.stat(st["file"]).st_mode & 0o777), "0o640")
        got = self.call("owner", "GET", "/api/backup")[1]
        self.assertTrue(got["ok"] and not got["stale"])
        self.assertTrue(self.call("owner", "GET", "/api/dashboard")[1]["backup"]["ok"])

    def test_43_portal_watch(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent / "deploy"))
        import tcp_staff_watch as watch
        state = tempfile.mkdtemp()
        hook = Path(state) / "hook"
        hook.write_text(self.portal.cfg["stats_api"] + "/webhook")
        snap = Path(state) / "snap.db"
        snap.write_text("x")
        before = len(HOOKS)
        dead = "http://127.0.0.1:9/healthz"
        args = ["--state", state, "--webhook", str(hook), "--snapshot", str(snap)]
        watch.main(["--url", dead] + args)
        self.assertEqual(len(HOOKS), before)                                   # one miss is not an alert
        watch.main(["--url", dead] + args)
        self.assertTrue(wait_for(lambda: len(HOOKS) == before + 1, 3))
        self.assertIn("down", HOOKS[-1]["embeds"][0]["title"])
        watch.main(["--url", dead] + args)
        self.assertEqual(len(HOOKS), before + 1)                               # no repeat while it stays down
        watch.main(["--url", "http://127.0.0.1:%d/healthz" % self.port] + args)
        self.assertIn("back", HOOKS[-1]["embeds"][0]["title"])
        snap.unlink()
        watch.main(["--url", "http://127.0.0.1:%d/healthz" % self.port] + args)
        self.assertIn("snapshot", HOOKS[-1]["embeds"][0]["title"])

    def test_44_live_stream(self):
        self.assertEqual(self.call(None, "GET", "/api/stream")[0], 401)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", "/api/stream", headers={"Cookie": self.sessions["moderator"]["cookie"]})
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        self.assertTrue(r.getheader("Content-Type").startswith("text/event-stream"))
        self.assertIn(b"retry:", r.fp.readline())
        self.portal.alert("test", "Stream check", "hello", key="stream-check-%d" % time.time())
        got = b""
        deadline = time.time() + 8
        while b"event: alert" not in got and time.time() < deadline:
            got += r.fp.readline()
        self.assertIn(b"event: alert", got)
        self.assertNotIn(b"hello", got)                         # events carry ids, never the content
        c.close()
        # five streams for one person: the fifth is refused
        conns = []
        for _ in range(4):
            x = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
            x.request("GET", "/api/stream", headers={"Cookie": self.sessions["owner"]["cookie"]})
            conns.append((x, x.getresponse()))
        self.assertEqual([resp.status for _, resp in conns], [200] * 4)
        self.assertEqual(self.call("owner", "GET", "/api/stream")[0], 429)
        for x, _ in conns:
            x.close()

    def test_45_cases(self):
        wait_for(lambda: self.portal.servers["one"].view().get("online"))
        rid = self.portal.store.one("SELECT MIN(id) i FROM reports WHERE source IN ('player','auto')")["i"]
        self.assertEqual(self.call("moderator", "POST", "/api/cases", {"title": "x", "pid": "nope"})[0], 400)
        code, r = self.call("moderator", "POST", "/api/cases", {"title": "Suspected wallhack", "report": rid})
        self.assertEqual(code, 201, r)
        cid = r["id"]
        code, c = self.call("moderator", "GET", "/api/case/%d" % cid)
        self.assertEqual(code, 200)
        self.assertEqual(c["items"][0]["kind"], "report")
        self.assertEqual(c["assignee"], self.portal.store.one("SELECT name FROM sessions WHERE role='moderator' LIMIT 1")["name"])
        self.assertEqual(self.call("moderator", "POST", "/api/case/link", {"id": cid, "kind": "report", "ref": rid})[0], 409)
        self.assertEqual(self.call("moderator", "POST", "/api/case/link", {"id": cid, "kind": "ban", "ref": 999999})[0], 404)
        self.assertEqual(self.call("moderator", "POST", "/api/case/note", {"id": cid, "text": "Watched the demo"})[0], 200)
        self.assertEqual(self.call("moderator", "POST", "/api/case/update", {"id": cid, "status": "closed"})[0], 400)  # outcome needed
        code, u = self.call("owner", "POST", "/api/case/update", {"id": cid, "status": "closed", "outcome": "Banned 30 days", "assignee": "me"})
        self.assertEqual(code, 200, u)
        self.assertEqual(u["case"]["status"], "closed")
        c = self.call("moderator", "GET", "/api/case/%d" % cid)[1]
        kinds = [i["kind"] for i in c["items"]]
        self.assertIn("note", kinds)
        self.assertIn("status", kinds)
        note = next(i for i in c["items"] if i["kind"] == "note")
        status = next(i for i in c["items"] if i["kind"] == "status")
        self.assertEqual(self.call("moderator", "POST", "/api/case/unlink", {"id": cid, "item": status["id"]})[0], 409)
        self.assertEqual(self.call("moderator", "POST", "/api/case/unlink", {"id": cid, "item": note["id"]})[0], 200)
        self.assertTrue(any(x["id"] == cid for x in self.call("moderator", "GET", "/api/cases?status=closed")[1]["cases"]))
        self.assertEqual(self.call("moderator", "GET", "/api/search?q=case%%20%d" % cid)[1]["cases"][0]["id"], cid)
        self.assertIn("cases", self.call("moderator", "GET", "/api/dashboard")[1])
        self.assertEqual(self.call("moderator", "GET", "/api/case/999999")[0], 404)
        self.assertTrue(self.portal.store.one("SELECT id FROM audit WHERE action='case closed'"))

    def test_46_player_timeline(self):
        wait_for(lambda: self.portal.servers["one"].view().get("online"))
        wait_for(lambda: self.portal.store.one("SELECT id FROM player_sessions WHERE pid=?", (PID,)))
        self.portal.store.x("INSERT INTO notes(pid,text,created,by_name) VALUES(?,?,?,?)", (PID, "timeline note", int(time.time()), "t"))
        code, t = self.call("moderator", "GET", "/api/timeline/" + PID)
        self.assertEqual(code, 200)
        kinds = {e["kind"] for e in t["events"]}
        self.assertIn("session", kinds)
        self.assertIn("note", kinds)
        self.assertIn("name", kinds)
        ats = [e["at"] for e in t["events"]]
        self.assertEqual(ats, sorted(ats, reverse=True))
        self.assertEqual(self.call("moderator", "GET", "/api/timeline/zzz")[0], 400)
        # a player who leaves gets the session closed
        srv = self.portal.servers["one"]
        self.portal.track_sessions(srv, {}, {}, True)
        self.assertIsNotNone(self.portal.store.one("SELECT left_at FROM player_sessions WHERE pid=? ORDER BY id DESC LIMIT 1", (PID,))["left_at"])

    def test_47_evidence(self):
        import base64 as b64
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        code, r = self.call("moderator", "POST", "/api/evidence", {"kind": "image", "pid": PID, "title": "shot", "data": b64.b64encode(png).decode()})
        self.assertEqual(code, 201, r)
        eid = r["id"]
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", "/api/evidence/file?id=%d" % eid, headers={"Cookie": self.sessions["moderator"]["cookie"]})
        resp = c.getresponse()
        self.assertEqual((resp.status, resp.getheader("Content-Type")), (200, "image/png"))
        self.assertEqual(resp.read(), png)
        c.close()
        # a script dressed up as a picture is refused
        bad = b64.b64encode(b"<svg onload=alert(1)>").decode()
        self.assertEqual(self.call("moderator", "POST", "/api/evidence", {"kind": "image", "pid": PID, "data": bad})[0], 415)
        self.assertEqual(self.call("moderator", "POST", "/api/evidence", {"kind": "link", "pid": PID, "url": "javascript:alert(1)"})[0], 400)
        self.assertEqual(self.call("moderator", "POST", "/api/evidence", {"kind": "text", "text": "x"})[0], 400)   # no case, no player
        self.portal.store.x("INSERT INTO chat(server,at,slot,team,pid,name,text,kind) VALUES('one',?,0,0,?,?,?,'all')",
                            (int(time.time()), PID, "Viper", "evidence line"))
        code, r = self.call("moderator", "POST", "/api/evidence", {"kind": "chat", "pid": PID, "minutes": 5})
        self.assertEqual(code, 201, r)
        cid = self.call("moderator", "POST", "/api/cases", {"title": "Evidence case", "pid": PID})[1]["id"]
        code, r2 = self.call("moderator", "POST", "/api/evidence", {"kind": "link", "case": cid, "url": "https://example.com/clip"})
        self.assertEqual(code, 201, r2)
        case = self.call("moderator", "GET", "/api/case/%d" % cid)[1]
        self.assertEqual(len(case["evidence"]), 1)
        self.assertTrue(any(x["kind"] == "evidence" and x["ref"] == eid for x in case["suggest"]))
        ev = self.call("moderator", "GET", "/api/evidence?pid=" + PID)[1]["evidence"]
        self.assertTrue(any(x["kind"] == "chat" and any(l["text"] == "evidence line" for l in x["text"]) for x in ev))
        self.assertEqual(self.call("moderator", "POST", "/api/evidence/delete", {"id": eid})[0], 403)
        self.assertEqual(self.call("owner", "POST", "/api/evidence/delete", {"id": eid, "reason": "test"})[0], 200)
        self.assertEqual(self.call("moderator", "GET", "/api/evidence/file?id=%d" % eid)[0], 404)
        self.assertFalse(list((Path(self.portal.cfg["data_dir"]) / "evidence").glob("*.png")))

    def test_48_vapid_signature(self):
        d, pub = tsp.p256_keypair()
        self.assertEqual(tsp.p256_public(d), pub)
        sig = tsp.es256_sign(d, b"hello")
        self.assertEqual(len(sig), 64)
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
        except ImportError:
            self.skipTest("cryptography not installed")
        key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), pub)
        der = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
        key.verify(der, b"hello", ec.ECDSA(hashes.SHA256()))           # raises when wrong
        h = tsp.vapid_header(d, pub, "https://fcm.googleapis.com/fcm/send/abc", "https://staff.example")
        tok = h.split("t=")[1].split(",")[0]
        head, body, s64 = tok.split(".")
        import base64
        raw = base64.urlsafe_b64decode(s64 + "==")
        der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
        key.verify(der, ("%s.%s" % (head, body)).encode(), ec.ECDSA(hashes.SHA256()))
        self.assertEqual(json.loads(base64.urlsafe_b64decode(body + "==="))["aud"], "https://fcm.googleapis.com")

    def test_49_push_and_duty(self):
        self.assertEqual(self.call("moderator", "POST", "/api/push/subscribe", {"endpoint": "https://evil.example/x"})[0], 400)
        self.assertEqual(self.call("moderator", "GET", "/api/push/key")[0], 200)
        hook = self.portal.cfg["stats_api"] + "/push/mod"
        self.assertEqual(self.call("moderator", "POST", "/api/push/subscribe", {"endpoint": hook})[0], 200)
        self.assertEqual(self.call("owner", "POST", "/api/push/subscribe", {"endpoint": self.portal.cfg["stats_api"] + "/push/gone"})[0], 200)
        before = len(PUSHES)
        self.portal.alert("reports", "not urgent", "x", key="push-a-%d" % time.time())
        time.sleep(1)
        self.assertEqual(len(PUSHES), before)                                  # nobody on duty, not urgent: no push
        code, d = self.call("moderator", "POST", "/api/duty", {"on": True, "hours": 2})
        self.assertEqual((code, d["on"]), (200, True))
        self.portal.alert("reports", "now on duty", "x", key="push-b-%d" % time.time())
        wait_for(lambda: len(PUSHES) > before)
        path, headers = PUSHES[-1]
        self.assertEqual(path, "/push/mod")
        self.assertTrue(headers.get("Authorization", "").startswith("vapid t="))
        self.portal.alert("server_down", "urgent", "x", key="push-c-%d" % time.time(), urgent=True)
        wait_for(lambda: not self.portal.store.one("SELECT 1 x FROM push_subs WHERE endpoint LIKE '%/push/gone'"))   # 410: dropped
        latest = self.call("moderator", "GET", "/api/push/latest")[1]["alert"]
        self.assertEqual(latest["title"], "urgent")
        self.assertTrue(self.call("moderator", "GET", "/api/duty")[1]["me"]["on"])
        self.assertTrue(self.call("moderator", "GET", "/api/dashboard")[1]["on_duty"])
        self.assertFalse(self.call("moderator", "POST", "/api/duty", {"on": False})[1]["on"])
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/sw.js")
        r = c.getresponse()
        self.assertEqual((r.status, "javascript" in r.getheader("Content-Type")), (200, True))
        c.close()

    def test_50_history_quality_anticheat(self):
        self.portal.record_samples(force=True)
        code, h = self.call("moderator", "GET", "/api/history?days=7")
        self.assertEqual(code, 200)
        self.assertTrue(h["points"])
        self.assertEqual(len(h["heatmap"]), 7)
        self.assertEqual(self.call("moderator", "GET", "/api/history?server=nope")[0], 404)
        self.assertEqual(self.call("moderator", "GET", "/api/quality")[0], 403)
        code, q = self.call("owner", "GET", "/api/quality?days=30")
        self.assertEqual(code, 200)
        self.assertTrue(any(x["bans"] for x in q["staff"]))
        # anti-cheat queue: a suspicion alert and a detection rise both land there, once
        self.portal.alert("suspicion", "Suspicion 88: Viper on Official #1", "- aim", key="sus-q-%d" % time.time(), pid=PID, server="one")
        srv = self.portal.servers["one"]
        self.portal.ac_watch(srv, [{"pid": PID, "name": "Viper", "detections": 2}])
        self.portal.ac_watch(srv, [{"pid": PID, "name": "Viper", "detections": 2}])
        self.assertEqual(self.call("moderator", "GET", "/api/anticheat")[0], 403)
        items = self.call("owner", "GET", "/api/anticheat")[1]["items"]
        kinds = sorted(x["kind"] for x in items if x["pid"] == PID)
        self.assertEqual(kinds.count("detection"), 1)
        self.assertEqual(kinds.count("suspicion"), 1)
        sid = next(x["id"] for x in items if x["kind"] == "suspicion")
        self.assertEqual(self.call("owner", "POST", "/api/anticheat", {"id": sid, "outcome": "cleared", "note": "clean demo"})[0], 200)
        self.assertEqual(self.call("owner", "POST", "/api/anticheat", {"id": sid, "outcome": "bogus"})[0], 400)
        self.assertFalse(any(x["id"] == sid for x in self.call("owner", "GET", "/api/anticheat")[1]["items"]))

    def test_51_trial_role_and_rights(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/auth/dev?role=trial&id=200000000000000002&name=Trial")
        cookie = c.getresponse().getheader("Set-Cookie").split(";")[0]
        c.close()
        me = self.call(None, "GET", "/api/me", cookie=cookie)[1]
        self.assertIn("player.warn", me["perms"])
        self.assertNotIn("player.kick", me["perms"])
        self.assertNotIn("ban.temp", me["perms"])
        self.assertEqual(self.call(None, "GET", "/api/servers", cookie=cookie)[0], 200)
        did = "200000000000000002"
        self.assertEqual(self.call("owner", "POST", "/api/staff", {"discord_id": did, "role": "trial", "name": "Trial"})[0], 200)
        # moderator cannot hand out rights; an admin cannot hand out admin tools; the owner can
        self.assertEqual(self.call("moderator", "POST", "/api/staff/rights", {"discord_id": did, "add": ["player.kick"]})[0], 403)
        self.assertEqual(self.call("owner", "POST", "/api/staff/rights", {"discord_id": did, "add": ["staff.manage"]})[0], 403)
        code, r = self.call("owner", "POST", "/api/staff/rights", {"discord_id": did, "add": ["player.kick", "event"], "remove": ["player.warn"]})
        self.assertEqual(code, 200, r)
        me = self.call(None, "GET", "/api/me", cookie=cookie)[1]
        self.assertIn("player.kick", me["perms"])
        self.assertNotIn("player.warn", me["perms"])
        self.assertIn("event", me["perms"])
        got = self.call("owner", "GET", "/api/staff/rights?id=" + did)[1]
        self.assertEqual(got["add"], ["event", "player.kick"])
        self.call("owner", "POST", "/api/staff/rights", {"discord_id": did, "add": [], "remove": []})
        self.assertNotIn("player.kick", self.call(None, "GET", "/api/me", cookie=cookie)[1]["perms"])

    def test_52_install_keeps_staff_root(self):
        text = (Path(__file__).resolve().parent / "deploy" / "install.sh").read_text()
        self.assertIn("s|^#LoadCredential=staff-root:|LoadCredential=staff-root:|", text)
        unit = (Path(__file__).resolve().parent / "deploy" / "tcp-staff-portal.service").read_text()
        self.assertIn("#LoadCredential=staff-root:/etc/tcp-staff-portal/staff-root", unit)

    def bot(self, method, path, body=None, did="300000000000000003", roles="555", token="bt", xff=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"X-Bot-Token": token, "X-Discord-Id": did, "X-Discord-Roles": roles, "X-Discord-Name": "Disc%20Mod"}
        if xff:
            h["X-Forwarded-For"] = xff
        data = None
        if body is not None:
            data = json.dumps(body)
            h["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = json.loads(r.read() or b"{}")
        c.close()
        return r.status, out

    def test_53_discord_bot_commands(self):
        self.assertEqual(self.bot("GET", "/bot/me")[0], 404)                  # no token set up: the route does not exist
        self.portal.cfg.setdefault("discord", {})
        self.portal.cfg["discord"]["bot_api_token"] = "bt"
        self.portal.cfg["discord"]["moderator_role_ids"] = ["555"]
        try:
            self.assertEqual(self.bot("GET", "/bot/me", token="wrong")[0], 401)
            self.assertEqual(self.bot("GET", "/bot/me", xff="203.0.113.5")[0], 404)       # never through the reverse proxy
            self.assertEqual(self.bot("GET", "/bot/me", roles="")[0], 403)                # not staff
            code, me = self.bot("GET", "/bot/me")
            self.assertEqual((code, me["role"]), (200, "moderator"))
            self.assertNotIn("ban.perm", me["perms"])
            self.assertEqual(self.bot("GET", "/bot/summary")[0], 200)
            wait_for(lambda: self.portal.servers["one"].view().get("online"))
            online = self.bot("GET", "/bot/online")[1]["servers"]
            viper = next(p for x in online if x["key"] == "one" for p in x["players"] if p["name"] == "Viper")
            self.assertNotIn("ip", viper)
            code, r = self.bot("POST", "/bot/action", {"server": "one", "slot": viper["slot"], "action": "warn", "reason": "from Discord"})
            self.assertEqual(code, 200, r)
            self.assertIn("warn %d from Discord" % viper["slot"], self.game.commands)
            self.assertEqual(self.bot("POST", "/bot/action", {"server": "one", "slot": viper["slot"], "action": "ban", "length": "0",
                                                              "reason": "x"})[0], 403)                      # permanent: admins in the portal
            rid = self.portal.store.one("SELECT MIN(id) i FROM reports WHERE source IN ('player','auto')")["i"]
            self.assertEqual(self.bot("POST", "/bot/report", {"id": rid, "action": "close"})[0], 400)
            self.assertEqual(self.bot("POST", "/bot/report", {"id": rid, "action": "take"})[0], 200)
            self.assertEqual(self.portal.store.one("SELECT claimed_by FROM reports WHERE id=?", (rid,))["claimed_by"], "Disc Mod")
            self.assertTrue(self.bot("GET", "/bot/reports")[1]["reports"])
            self.assertTrue(self.bot("GET", "/bot/lookup?q=vip")[1]["players"])
            self.assertTrue(self.bot("POST", "/bot/duty", {"on": True, "hours": 1})[1]["on"])
            self.assertTrue(self.portal.store.one("SELECT id FROM audit WHERE staff='Disc Mod' AND action='warn'"))
        finally:
            self.portal.cfg["discord"].pop("bot_api_token", None)
            self.portal.cfg["discord"].pop("moderator_role_ids", None)

    def test_insights_page_reads_the_insights_service(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server-bridge"))
        try:
            import tcp_insights
        except ImportError:
            self.skipTest("tools/server-bridge/tcp_insights.py not in this checkout")
        from http.server import ThreadingHTTPServer
        store = tcp_insights.Store("")
        store.github({("v0.35.0", "TrueCombat-Platinum-Setup.exe"): 42})
        srv = ThreadingHTTPServer(("127.0.0.1", 0), tcp_insights.make_handler(store, "ikey", [], "", tcp_insights.Limiter(), tcp_insights.GeoIP()))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            self.portal.cfg["insights_api"] = "http://127.0.0.1:%d" % srv.server_address[1]
            self.portal.cfg.pop("insights_key", None)
            self.assertEqual(self.call("owner", "GET", "/api/insights?days=7")[0], 409)   # not linked yet
            self.portal.cfg["insights_key"] = "wrong"
            self.assertEqual(self.call("owner", "GET", "/api/insights?days=7")[0], 409)
            self.portal.cfg["insights_key"] = "ikey"
            self.assertEqual(self.call("moderator", "GET", "/api/insights")[0], 403)
            code, body = self.call("owner", "GET", "/api/insights?days=7")
            self.assertEqual(code, 200)
            self.assertEqual((body["schema"], len(body["days"])), ("tcp-insights/1", 7))
            self.assertEqual(body["github"]["releases"][0]["downloads"], 42)
            self.assertIn("launcher", body)                                           # launcher 2.6.0 crash/hardware section
            self.assertEqual(body["launcher"]["totals"]["crashes"], 0)
            self.assertEqual(len(self.call("owner", "GET", "/api/insights?days=12345")[1]["days"]), 30)
        finally:
            self.portal.cfg.pop("insights_key", None)
            srv.shutdown()
            srv.server_close()


    def test_comments_page_drives_the_accounts_service(self):
        """1.5.0: the Devlog comments page reads and moderates through the accounts service's /internal/comments/*."""
        import sys as _sys
        import tempfile as _tf
        _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "accounts"))
        try:
            import tcp_accounts
        except ImportError:
            self.skipTest("tools/accounts/tcp_accounts.py not in this checkout")
        from http.server import ThreadingHTTPServer
        acc = tcp_accounts.Accounts({"data_dir": _tf.mkdtemp(), "comments_token": "ctok", "internal_token": "itok",
                                     "team": {"dev-moderator": "Moderator"}})
        srv = ThreadingHTTPServer(("127.0.0.1", 0), tcp_accounts.make_handler(acc))
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        def account(discord, name):
            s = acc.session(acc.new_session(discord, name, "", "127.0.0.9"))
            acc.signup(s, name, "public", True)
            return acc.session(acc.new_session(discord, name, "", "127.0.0.9"))

        self.sessions["admin"] = self.login("admin")      # earlier tests may have signed the shared admin out
        try:
            self.portal.cfg["accounts_api"] = "http://127.0.0.1:%d" % srv.server_address[1]
            self.portal.cfg.pop("accounts_token", None)
            code, body = self.call("moderator", "GET", "/api/comments")
            self.assertEqual(code, 409)                                               # not linked yet
            self.assertIn("accounts-link", body["error"])
            self.portal.cfg["accounts_token"] = "wrong"
            self.assertEqual(self.call("moderator", "GET", "/api/comments")[0], 404)
            self.portal.cfg["accounts_token"] = "ctok"
            web = account("300000000000000001", "Webonly")
            held = acc.comments.post(web, {"post": "inside-0372", "text": "First comment from the web"}, "127.0.0.9")
            self.assertTrue(held["held"])
            self.assertEqual(self.call(None, "GET", "/api/comments")[0], 401)
            code, body = self.call("moderator", "GET", "/api/comments?tab=needs")
            self.assertEqual(code, 200)
            self.assertEqual(body["comments"][0]["author"]["name"], "Webonly")
            self.assertEqual(body["comments"][0]["reason"], "new")
            self.assertEqual(self.call("moderator", "GET", "/api/comments/stats")[1]["held"], 1)
            self.assertEqual(self.call("moderator", "POST", "/api/comments/act", {"id": held["id"], "action": "nuke"})[0], 400)
            code, body = self.call("moderator", "POST", "/api/comments/act", {"id": held["id"], "action": "publish"})
            self.assertEqual((code, body["comment"]["state"]), (200, "live"))
            audit = self.portal.store.one("SELECT * FROM audit WHERE action='comment.publish' ORDER BY id DESC LIMIT 1")
            self.assertEqual(audit["target"], "Webonly")
            self.assertIn("First comment", audit["detail"])
            code, body = self.call("moderator", "POST", "/api/comments/reply", {"parent": held["id"], "text": "Welcome aboard."})
            self.assertEqual(code, 409)                                               # the moderator has no player account yet
            account("dev-moderator", "ModMan")
            code, body = self.call("moderator", "POST", "/api/comments/reply", {"parent": held["id"], "text": "Welcome aboard."})
            self.assertEqual(code, 200)
            listing = acc.comments.listing("inside-0372", "new", None)
            self.assertTrue(listing["comments"][0]["replies"][0]["team"])
            code, body = self.call("moderator", "POST", "/api/comments/pause", {"name": "Webonly", "days": 7, "reason": "spam"})
            self.assertEqual((code, body["name"]), (200, "Webonly"))
            self.assertEqual(self.call("moderator", "GET", "/api/comments?tab=paused")[1]["paused"][0]["name"], "Webonly")
            self.assertEqual(self.call("moderator", "POST", "/api/comments/unpause", {"account": body["account"]})[0], 200)
            self.assertEqual(self.call("moderator", "POST", "/api/comments/close", {"post": "inside-0372"})[0], 403)   # admins only
            code, body = self.call("admin", "POST", "/api/comments/close", {"post": "inside-0372"})
            self.assertEqual((code, body.get("closed")), (200, True), body)
            self.assertEqual(acc.comments.post_state("inside-0372"), "closed")
            self.assertEqual(self.call("admin", "POST", "/api/comments/close", {"post": "inside-0372", "closed": False})[1]["closed"], False)
            # the loop's alert: more waiting than last time -> one alert, no comment text in it
            acc.comments.post(account("300000000000000002", "Webtwo"), {"post": "inside-0372", "text": "Secret words here"}, "127.0.0.9")
            self.portal.meta("comments_needs", "0")
            self.portal.stop.clear()
            st = self.portal.comments_api("GET", "stats")
            self.assertEqual(st["needs"], 1)
            t = threading.Thread(target=self.portal.comments_loop, daemon=True)
            t.start()
            deadline = time.time() + 5
            alert = None
            while time.time() < deadline and not alert:
                alert = self.portal.store.one("SELECT * FROM alerts WHERE kind='comments' ORDER BY id DESC LIMIT 1")
                time.sleep(0.1)
            self.assertIsNotNone(alert)
            self.assertNotIn("Secret", alert["text"] + alert["title"])
        finally:
            self.portal.cfg.pop("accounts_token", None)
            srv.shutdown()
            srv.server_close()

    def test_35_staff_certificates(self):
        """0.38.0: the portal signs active staff keys into certificates every game server checks offline."""
        root_seed, staff_seed = bytes([0x11]) * 32, bytes([0x22]) * 32
        staff_pub = tsp.ed25519_public(staff_seed).hex()
        rootfile = Path(self.tmp.name) / "staff-root"
        for attr in ("_staff_root", "_staff_certs"):
            if hasattr(self.portal, attr):
                delattr(self.portal, attr)
        self.portal.cfg.pop("staff_root_file", None)
        st, k = self.call("moderator", "POST", "/api/staffkey", {"public": staff_pub})
        self.assertEqual(st, 201)
        self.assertEqual(self.call(None, "GET", "/api/staffcert?id=" + k["id"])[0], 404)      # no root set up yet
        rootfile.write_text("TCPSTAFFROOT1 p1 %s\n" % root_seed.hex())
        self.portal.cfg["staff_root_file"] = str(rootfile)
        del self.portal._staff_root
        st, c = self.call(None, "GET", "/api/staffcert?id=" + k["id"])                       # public: no session
        self.assertEqual(st, 200)
        f = c["cert"].split()
        self.assertEqual((f[0], f[1], f[2], f[3], f[6]), ("TCPSTAFFCERT1", "p1", k["id"], "1", staff_pub))
        issued, expires = int(f[4]), int(f[5])
        self.assertEqual(expires - issued, 30 * 86400)
        self.assertEqual(bytes.fromhex(f[7]).decode(), "Moderator")
        msg = tsp.staff_cert_message("p1", k["id"], 1, issued, expires, staff_pub, f[7])
        root_pub = tsp.ed25519_public(root_seed)
        self.assertTrue(tsp.ed25519_verify(root_pub, msg, bytes.fromhex(f[8])))
        self.assertFalse(tsp.ed25519_verify(root_pub, msg + b"x", bytes.fromhex(f[8])))
        self.assertEqual(root_pub.hex(), "d04ab232742bb4ab3a1368bd4615e4e6d0224ab71a016baf8520a332c9778737")  # = game probe root p1
        self.assertEqual(self.call(None, "GET", "/api/staffcert?id=" + k["id"])[1]["cert"], c["cert"])   # cached
        self.assertEqual(self.call(None, "GET", "/api/staffcert?id=kzzzz")[0], 404)
        self.assertEqual(self.call(None, "GET", "/api/staffcert?id=k0000000000")[0], 404)
        self.assertEqual(self.call("moderator", "POST", "/api/staffkey/revoke", {"id": k["id"]})[0], 200)
        self.assertEqual(self.call(None, "GET", "/api/staffcert?id=" + k["id"])[0], 404)      # revoked: no new certificate
        self.portal.cfg.pop("staff_root_file", None)
        del self.portal._staff_root


class Ed25519Test(unittest.TestCase):
    def test_rfc8032_vectors(self):
        for sk, pk, msg, sig in (
            ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
             "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
             "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
            ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
             "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
             "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")):
            s, p, m = bytes.fromhex(sk), bytes.fromhex(pk), bytes.fromhex(msg)
            self.assertEqual(tsp.ed25519_public(s), p)
            self.assertEqual(tsp.ed25519_sign(s, m).hex(), sig)
            self.assertTrue(tsp.ed25519_verify(p, m, bytes.fromhex(sig)))

    def test_make_staff_root(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "staff-root"
            cfgfile = Path(d) / "c.json"
            cfgfile.write_text("{}")
            self.assertEqual(tsp.main(["--config", str(cfgfile), "--make-staff-root", "r1", "--root-out", str(out)]), 0)
            parts = out.read_text().split()
            self.assertEqual((parts[0], parts[1], len(parts[2])), ("TCPSTAFFROOT1", "r1", 64))
            if os.name == "posix":
                self.assertEqual(out.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):                                     # never overwrites a root
                tsp.main(["--config", str(cfgfile), "--make-staff-root", "r1", "--root-out", str(out)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
