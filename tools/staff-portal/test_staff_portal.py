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


HOOKS, VOIDED = [], []


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
            self.assertEqual(len(self.call("owner", "GET", "/api/insights?days=12345")[1]["days"]), 30)
        finally:
            self.portal.cfg.pop("insights_key", None)
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
