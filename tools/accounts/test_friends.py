#!/usr/bin/env python3
"""Friends and presence (accounts 1.2.0, launcher 3.0.0).  python3 test_friends.py
Needs the 'cryptography' package to sign as the launcher (test only)."""
import json
import pathlib
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tcp_accounts as A  # noqa: E402
import tcp_friends as F  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

checks = []


def check(name, ok):
    checks.append((name, bool(ok)))
    print(("ok   " if ok else "FAIL ") + name)


class PC:
    clock = int(time.time() * 1000)

    def __init__(self, acc, name):
        self.acc, self.name = acc, name
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        self.state, self.server, self.addr, self.map = "launcher", "", "", ""
        self.flags = {"show_online": 1, "show_server": 1, "requests": 1}

    def call(self, action="sync", arg="", t=None, tamper=None):
        PC.clock += 7
        body = {"public": self.public, "t": t if t is not None else PC.clock, "action": action, "arg": arg,
                "name": self.name, "state": self.state, "server": self.server, "addr": self.addr, "map": self.map,
                **self.flags}
        body["signature"] = self.key.sign(F.message(body)).hex()
        if tamper:
            body.update(tamper)
        try:
            return self.acc.friends.call(body, "1.2.3.4")
        except A.ApiError as e:
            return {"error": e.message, "status": e.status}


def main():
    tmp = tempfile.mkdtemp()
    acc = A.Accounts({"data_dir": tmp})
    viper, kestrel, hollow = PC(acc, "Viper"), PC(acc, "Kestrel"), PC(acc, "Hollow")
    a = viper.call()
    check("first sync gives a friend code", len(a.get("code", "")) == 9 and a["code"][4] == "-")
    check("no friends at first", a["friends"] == [] and a["requests"] == [])
    k = kestrel.call()
    hollow.call()
    r = kestrel.call("add", a["code"].lower().replace("-", ""))
    check("add by code (any case, no dash) sends a request", r.get("note") == "sent")
    a = viper.call()
    check("request arrives", len(a["requests"]) == 1 and a["requests"][0]["name"] == "Kestrel")
    rid = a["requests"][0]["id"]
    a = viper.call("accept", rid)
    check("accept makes friends", a.get("note") == "friends" and [f["name"] for f in a["friends"]] == ["Kestrel"])
    k = kestrel.call()
    check("both sides see it", [f["name"] for f in k["friends"]] == ["Viper"] and k["friends"][0]["state"] == "launcher")
    viper.state, viper.server, viper.addr, viper.map = "playing", "Official #1", "2.24.59.195:27960", "obj_railhouse"
    viper.call()
    k = kestrel.call()
    f = k["friends"][0]
    check("playing shows server and address", f["state"] == "playing" and f["addr"] == "2.24.59.195:27960" and f["map"] == "obj_railhouse")
    viper.flags["show_server"] = 0
    viper.call()
    f = kestrel.call()["friends"][0]
    check("hidden server: playing without address", f["state"] == "playing" and f["addr"] == "" and f["server"] == "")
    viper.flags["show_online"] = 0
    viper.call()
    f = kestrel.call()["friends"][0]
    check("hidden online: offline, no last seen", f["state"] == "offline" and f["seen"] == 0)
    viper.flags.update(show_online=1, show_server=1)
    viper.call()
    vid = kestrel.call()["friends"][0]["id"]
    r = kestrel.call("invite", vid)
    check("invite needs a server", r.get("status") == 409)
    kestrel.state, kestrel.addr, kestrel.server = "playing", "2.24.59.195:27961", "Official #2"
    r = kestrel.call("invite", vid)
    check("invite sent", r.get("note") == "invited")
    a = viper.call()
    check("invite arrives once", len(a["invites"]) == 1 and a["invites"][0]["addr"] == "2.24.59.195:27961")
    check("invite gone after delivery", viper.call()["invites"] == [])
    # replays, tampering, clock
    t = PC.clock + 1
    viper.call(t=t)
    check("replayed stamp refused", viper.call(t=t).get("status") == 409)
    check("tampered body refused", viper.call(tamper={"name": "Admin"}).get("status") == 401)
    check("clock far off refused", viper.call(t=int(time.time() * 1000) - 3600 * 1000).get("status") == 400)
    check("unknown action refused", viper.call("drop").get("status") == 400)
    # names
    hollow.flags["requests"] = 0
    hollow.call()
    check("add by exact name respects 'accept requests'", viper.call("add", "hollow").get("status") == 403)
    hollow.flags["requests"] = 1
    hollow.call()
    check("add by name", viper.call("add", "Hollow").get("note") == "sent")
    h = hollow.call()
    r = hollow.call("decline", h["requests"][0]["id"])
    check("decline", r.get("note") == "declined" and r["requests"] == [])
    check("declined stays quiet for the sender", viper.call("add", "Hollow").get("note") == "sent" and hollow.call()["requests"] == [])
    check("unknown code", viper.call("add", "ZZZZ-ZZZZ").get("status") == 404)
    check("cannot add yourself", viper.call("add", a["code"]).get("status") == 404)
    other = PC(acc, "Hollow")
    other.call()
    check("ambiguous name asks for the code", kestrel.call("add", "Hollow").get("status") == 409)
    # both ask: instant friends
    kestrel.call("add", hollow.call()["code"])
    r = hollow.call("add", kestrel.call()["code"])
    check("mutual requests become friends", r.get("note") == "friends")
    # remove
    kid_short = [f for f in viper.call()["friends"] if f["name"] == "Kestrel"][0]["id"]
    r = viper.call("remove", kid_short)
    check("remove", r.get("note") == "removed" and all(f["name"] != "Kestrel" for f in r["friends"]))
    check("removed on both sides", all(f["name"] != "Viper" for f in kestrel.call()["friends"]))
    # account link moves friends
    acc.store.x("INSERT INTO accounts(id, discord_id, name, skeleton, created, name_changed, last_active) VALUES(?,?,?,?,?,?,?)",
                ("acct1", "d1", "KestrelPro", "kestrelpro", 1, 1, 1))
    kkid = A.key_id(bytes.fromhex(kestrel.public))
    acc.store.x("INSERT INTO keys(kid, account, public, label, linked) VALUES(?,?,?,?,?)", (kkid, "acct1", kestrel.public, "PC", 1))
    k = kestrel.call()
    check("linking an account keeps friends and takes the account name",
          [f["name"] for f in k["friends"]] == ["Hollow"] and [f["name"] for f in hollow.call()["friends"]] == ["KestrelPro"])
    # leave
    r = hollow.call("leave")
    check("leave answers empty", r.get("note") == "left")
    check("leave deletes everything", acc.store.one("SELECT COUNT(*) n FROM fr_people WHERE name='Hollow' AND id IN "
                                                    "(SELECT b FROM fr_links)")["n"] == 0 and kestrel.call()["friends"] == [])
    # HTTP route
    import http.client
    import threading
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), A.make_handler(acc))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    PC.clock += 7
    body = {"public": viper.public, "t": PC.clock, "action": "sync", "arg": "", "name": "Viper", "state": "launcher",
            "server": "", "addr": "", "map": "", **viper.flags}
    body["signature"] = viper.key.sign(F.message(body)).hex()
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1])
    c.request("POST", "/api/account/friends", json.dumps(body), {"Content-Type": "application/json"})
    res = c.getresponse()
    data = json.loads(res.read())
    check("HTTP route answers", res.status == 200 and data.get("code") == a["code"])
    srv.shutdown()
    acc.tidy()
    check("tidy runs with friends", True)
    bad = [n for n, ok in checks if not ok]
    print("%d checks, %d failed" % (len(checks), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
