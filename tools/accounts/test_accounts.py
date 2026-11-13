#!/usr/bin/env python3
"""Player accounts: names, linking PCs with a signed code, the HTTP routes, GDPR export/delete, the reserved
list for game servers, and the stats service merging linked ids (progress follows you).

  python3 test_accounts.py

Needs the 'cryptography' package to sign like the launcher will (test only; the service itself is stdlib)."""
import hashlib
import http.client
import json
import pathlib
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "server-bridge"))
import tcp_accounts as A  # noqa: E402
import tcp_stats as S  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402

checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)))


def raises(fn, status=None):
    try:
        fn()
    except A.ApiError as e:
        return status is None or e.status == status
    return False


class PC:
    """A player's PC: the eacid.key the game keeps, and what the launcher sends when it claims a link code."""

    def __init__(self):
        self.sk = Ed25519PrivateKey.generate()
        self.pub = self.sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        self.kid = hashlib.sha256(bytes.fromhex(self.pub)).hexdigest()[:40]

    def claim_body(self, code, label="Desk PC"):
        sig = self.sk.sign(A.link_message(code, self.pub)).hex()
        return {"code": code, "public": self.pub, "signature": sig, "label": label}


# ------------------------------------------------------------------ names
check("skeleton folds look-alikes", A.skeleton("RaziC*") == A.skeleton("r4z1c") == A.skeleton("R a z i c")
      == A.skeleton("^1Ra^7zic") == A.skeleton("RAAZIC"), [A.skeleton(x) for x in ("RaziC*", "r4z1c", "R a z i c")])
check("plain name accepted", A.name_problem("Ghost-7") is None)
for bad, why in (("ab", "3 to 20"), ("x" * 21, "3 to 20"), ("Adm1n", "studio"), ("TheStaffGuy", "studio"),
                 ("0fficial", "studio"), ("Player1234", "reserved"), ("mod", "reserved"), ("n4zi", "not allowed"),
                 ("^1Red", "colour"), ("bad/name", "3 to 20"), ("a.-.b", "at least 3")):
    got = A.name_problem(bad) or ""
    check("name refused: %s" % bad, why in got, got)
check("common word with a short abuse word inside is fine", A.name_problem("Nazir") is None)
check("unicode width tricks are normalised", A.skeleton("Ｒａｚｉｃ") == "razic")

# ------------------------------------------------------------------ service logic
tmp = pathlib.Path(tempfile.mkdtemp())
acc = A.Accounts({"data_dir": str(tmp), "reserved_dirs": [str(tmp / "srv1" / "accounts")]})


def session(did, name="Disc"):
    return acc.session(acc.new_session(did, name, "abc123", "203.0.113.5"))


s1 = session("111", "Gianni")
check("new Discord user has no account yet", s1["account"] is None and acc.me(s1)["needsSignup"])
check("signup needs the age confirmation", raises(lambda: acc.signup(s1, "RaziC", "public", False), 400))
a1 = acc.signup(s1, "RaziC", "public", True)
check("signup reserves the name", a1["name"] == "RaziC" and acc.by_name("razic")["id"] == a1["id"])
s2 = session("222", "Other")
check("look-alike of a taken name refused", raises(lambda: acc.signup(s2, "R4z1c", "public", True), 409))
a2 = acc.signup(s2, "Ghost", "hidden", True)
check("second account", a2["visibility"] == "hidden")
s1 = acc.session(acc.new_session("111", "Gianni", "abc123", "203.0.113.5"))
check("returning user finds the account", s1["account"]["id"] == a1["id"])
check("double signup refused", raises(lambda: acc.signup(s1, "Other", "public", True), 409))

# link a PC
pc1, pc2, pc3 = PC(), PC(), PC()
code = acc.link_start(s1["account"])["code"]
check("link status waits", acc.link_status(s1["account"], code)["state"] == "waiting")
body = pc1.claim_body(code)
tampered = dict(body, signature=("0" if body["signature"][0] != "0" else "1") + body["signature"][1:])
check("bad signature refused", raises(lambda: acc.claim(tampered["code"], tampered["public"], tampered["signature"], "", "1.2.3.4"), 401))
other_key = PC().claim_body(code)
check("signature by another key refused", raises(lambda: acc.claim(code, pc1.pub, other_key["signature"], "", "1.2.3.4"), 401))
r = acc.claim(body["code"], body["public"], body["signature"], body["label"], "1.2.3.4")
check("claim links the key", r["key"] == pc1.kid and r["account"] == "RaziC")
check("link status says linked", acc.link_status(s1["account"], code)["state"] == "linked")
check("a code works once", raises(lambda: acc.claim(body["code"], body["public"], body["signature"], "", "1.2.3.4"), 410))
code2 = acc.link_start(a2)["code"]
b2 = pc1.claim_body(code2)
check("a linked PC cannot join a second account", raises(lambda: acc.claim(b2["code"], b2["public"], b2["signature"], "", "1.2.3.5"), 409))
c = acc.link_start(s1["account"])["code"]
b = pc2.claim_body(c, "Laptop")
acc.claim(b["code"], b["public"], b["signature"], b["label"], "1.2.3.4")
check("two PCs on one account", [k["kid"] for k in acc.keys_of(a1["id"], True)] == [pc1.kid, pc2.kid])
old = acc.link_start(s1["account"])["code"]
acc.store.x("UPDATE links SET created=created-700 WHERE code=?", (hashlib.sha256(old.encode()).hexdigest(),))
ob = pc3.claim_body(old)
check("expired code refused", raises(lambda: acc.claim(ob["code"], ob["public"], ob["signature"], "", "1.2.3.4"), 410))

# reserved list
txt = acc.reserved_txt()
lines = dict(l.split(" ", 1) for l in txt.strip().split("\n")[1:])
h1 = A.name_hash(A.skeleton("RaziC"))
check("reserved list: hashed name -> both keys", lines.get(h1) == ",".join(sorted([pc1.kid, pc2.kid])), lines)
check("reserved list holds no names in clear", "razic" not in txt.lower() and "ghost" not in txt.lower())
check("hidden account's name still reserved", A.name_hash(A.skeleton("Ghost")) in lines and lines[A.name_hash("ghost")] == "-")
acc.push()
check("reserved list written for the local game server", (tmp / "srv1" / "accounts" / "names.txt").read_text() == txt)

# rename rules
check("rename blocked for 30 days", raises(lambda: acc.rename(acc.account(a1["id"]), "Razor"), 409))
a1b = acc.rename(acc.account(a1["id"]), "RAZIC")
check("respelling the same name is free", a1b["name"] == "RAZIC")
acc.store.x("UPDATE accounts SET name_changed=name_changed-31*86400 WHERE id=?", (a1["id"],))
a1c = acc.rename(acc.account(a1["id"]), "Razor")
check("rename after 30 days", a1c["name"] == "Razor")
s3 = session("333")
check("old name held for 30 days", raises(lambda: acc.signup(s3, "Razic", "public", True), 409))
lines = dict(l.split(" ", 1) for l in acc.reserved_txt().strip().split("\n")[1:])
check("held name still allowed for its owner in game", lines.get(h1) == ",".join(sorted([pc1.kid, pc2.kid])))
acc.store.x("UPDATE names SET held_until=1 WHERE skeleton='razic'")
a3 = acc.signup(s3, "Razic", "public", True)
check("hold over: name free again", a3["name"] == "Razic")

# profile + names
s1 = acc.session(acc.new_session("111", "Gianni", "abc123", "203.0.113.5"))
p = acc.profile("razor")
check("public profile", p and p["name"] == "Razor" and p["pcs"] == 2 and "discord" not in p, p)
acc.settings(s1, None, True)
check("Discord shows only when turned on", acc.profile("Razor")["discord"]["name"] == "Gianni")
acc.settings(s1, None, False)
check("Discord name cleared when turned off", acc.account(a1["id"])["discord_name"] is None)
check("hidden account has no profile", acc.profile("Ghost") is None)
check("names.json has public accounts only", set(acc.names_json().values()) == {"Razor", "Razic"})

# ------------------------------------------------------------------ stats: progress follows you
db = S.StatsStore(str(tmp / "stats.db"), min_matches=1, require_anticheat=True)
GUID = {"Raz": "A" * 32, "Bob": "B" * 32, "Cid": "C" * 32, "Dan": "D" * 32}


def report(n, keys=None, hours_ago=10.0):
    ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - hours_ago * 3600 + n * 60))
    names, teams = ["Raz", "Bob", "Cid", "Dan"], ["specops", "specops", "terrorists", "terrorists"]
    players = []
    for i, (nm, t) in enumerate(zip(names, teams)):
        p = {"guid": GUID[nm], "name": nm, "team": t, "kills": 0, "deaths": 0, "headshots": 0, "damage": 500,
             "damageTaken": 500, "roundsWon": 6 if t == "specops" else 4, "objectives": 0, "won": t == "specops",
             "timePlayed": 900, "idle": 0, "ip": "a%d" % i, "hits": {"head": 1, "body": 5, "legs": 1}, "weapons": {}}
        if keys and nm in keys:
            p["key"] = keys[nm]
        players.append(p)
    kills = [[10000 + i * 1000, 1, 0, 2 + (i % 2), "M4", 0, 500, []] for i in range(3)]
    return {"schema": "tcp-match/2", "id": "acct-%03d" % n, "server": "Official", "map": "obj_village",
            "mode": "Team elimination", "started": ended, "ended": ended, "duration": 900, "rounds": 10,
            "winner": "specops", "eac": {"start": 2, "end": 2, "min": 2}, "password": False, "ranked": True,
            "botSeconds": 0, "players": players, "kills": kills, "events": []}


guid_pid = S.player_id(GUID["Raz"])
db.ingest(report(1), "official1")                       # before 0.37.0: guid only
db.ingest(report(2), "official1")
check("old matches under the guid id", db.player(guid_pid)["matches"] == 2)
db.ingest(report(3, {"Raz": pc1.kid}), "official1")    # 0.37.0: the server checked Raz's key
kp1 = A.key_pid(pc1.kid)
check("stats and accounts agree on key ids", kp1 == S.player_id("key:" + pc1.kid))
check("first verified key takes over the guid's history", db.player(kp1)["matches"] == 3 and not db.player(guid_pid))
db.ingest(report(4, {"Raz": pc2.kid}, hours_ago=9), "official1")      # the laptop (same etkey copied, new eacid)
kp2 = A.key_pid(pc2.kid)
check("second PC is its own player before the merge", db.player(kp2)["matches"] == 1)
check("review notes a guid seen with a second key", any("another key" in r["reason"] for r in db.review_list()))
n = db.set_aliases(acc.aliases())
canon = A.account_pid(a1["id"])
pl = db.player(canon)
check("account merge: one player with every match", pl and pl["matches"] == 4 and not db.player(kp1) and not db.player(kp2), pl)
check("merge rebuilt the stats", n == 4, n)
check("same aliases again: no rebuild", db.set_aliases(acc.aliases()) is None)
detail = db.detail(canon)
check("profile stats come from one id", detail and detail["totals"].get("matches") == 4, str(detail and detail.get("totals"))[:300])
lb = db.leaderboard()
ids = [r["id"] for r in lb["players"]] if isinstance(lb, dict) else []
check("leaderboard lists the account once", ids.count(canon) == 1 and kp1 not in ids and kp2 not in ids, ids)

# both of one account's PCs in the same match: kept apart for that match, flagged
db.ingest(report(5, {"Raz": pc1.kid, "Bob": pc2.kid}, hours_ago=8), "official1")
check("two linked PCs in one match stay apart", db.player(canon)["matches"] == 5 and db.player(kp2)["matches"] == 1)
check("and go to the review queue", any("same match" in r["reason"] for r in db.review_list()))

# unlink: earlier matches stay with the account, later ones go to the key
acc.unlink(acc.account(a1["id"]), pc2.kid)
time.sleep(1.1)
db.set_aliases(acc.aliases())
db.ingest(report(6, {"Raz": pc2.kid}, hours_ago=-0.01), "official1")
check("after unlink the PC plays as itself", db.player(kp2) and db.player(kp2)["matches"] >= 1)
check("matches before the unlink stay with the account", db.player(canon)["matches"] == 5)
ratings = tmp / "ratings.txt"
db.export_ratings(ratings)
rt = dict(l.split() for l in ratings.read_text().split("\n") if l)
check("team balance finds the account by the key id", rt.get(kp1) == rt.get(canon) and rt.get(guid_pid) == rt.get(canon))

# GDPR: export + delete
s1 = acc.session(acc.new_session("111", "Gianni", "abc123", "203.0.113.5"))
ex = acc.export(s1["account"])
check("export has the account, keys and sign-ins", ex["account"]["name"] == "Razor" and len(ex["keys"]) == 2 and ex["signins"])
check("export never holds a raw IP", "203.0.113.5" not in json.dumps(ex))
acc.delete(s1["account"])
check("delete removes account, keys, names, sessions", acc.by_discord("111") is None and acc.by_name("Razor") is None
      and not acc.store.all("SELECT * FROM keys WHERE account=?", (a1["id"],))
      and not acc.store.all("SELECT * FROM sessions WHERE discord_id='111'"))
db.set_aliases(acc.aliases())
check("after delete the stats split back to the keys", not db.player(canon) and db.player(kp1)["matches"] >= 4)
check("signin log keeps no raw IPs", all("203.0.113" not in str(r) for r in acc.store.all("SELECT * FROM signins")))

# tidy: inactive names released
acc.store.x("UPDATE accounts SET last_active=1 WHERE id=?", (a2["id"],))
acc.tidy()
check("a year without activity frees the name", acc.by_name("Ghost") is None and acc.account(a2["id"]))

# ------------------------------------------------------------------ HTTP
cfg = {"data_dir": str(tmp / "http"), "dev_login": True, "internal_token": "tok-internal", "public_url": "http://127.0.0.1:0"}
import os  # noqa: E402
os.environ["TCP_ACCOUNTS_DEV"] = "1"
hacc = A.Accounts(cfg)
srv = ThreadingHTTPServer(("127.0.0.1", 0), A.make_handler(hacc))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def req(method, path, body=None, cookie="", headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    h = dict(headers or {})
    if cookie:
        h["Cookie"] = cookie
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        h["Content-Type"] = "application/json"
    c.request(method, path, data, h)
    r = c.getresponse()
    raw = r.read()
    try:
        out = json.loads(raw) if raw and "json" in (r.getheader("Content-Type") or "") else raw.decode()
    except ValueError:
        out = raw
    return r.status, out, r


st, out, _ = req("GET", "/api/account/me")
check("http: signed out", st == 200 and out == {"signedIn": False})
st, out, r = req("GET", "/api/account/dev?id=999&name=Tester")
cookie = (r.getheader("Set-Cookie") or "").split(";")[0]
check("http: dev sign-in sets a cookie (loopback, dev only)", st == 302 and cookie.startswith("tcpacct="))
st, me, _ = req("GET", "/api/account/me", cookie=cookie)
csrf = me.get("csrf", "")
check("http: needs signup", me.get("needsSignup") is True)
st, out, _ = req("POST", "/api/account/signup", {"name": "Tester", "age13": True}, cookie)
check("http: write without CSRF refused", st == 403)
st, out, _ = req("POST", "/api/account/signup", {"name": "Tester", "age13": True}, cookie,
                 {"X-CSRF": csrf, "Origin": "https://evil.example"})
check("http: cross-site POST refused", st == 403)
st, out, _ = req("POST", "/api/account/signup", {"name": "Tester", "age13": True, "visibility": "public"}, cookie, {"X-CSRF": csrf})
check("http: signup", st == 200 and out["account"]["name"] == "Tester", out)
st, out, _ = req("GET", "/api/account/check?name=T3ster")
check("http: name check finds the look-alike", st == 200 and out["ok"] is False)
st, link, _ = req("POST", "/api/account/link/start", {}, cookie, {"X-CSRF": csrf})
check("http: link code + launcher URL", st == 200 and link["url"] == "truecombat://account/" + link["code"])
pc = PC()
st, out, _ = req("POST", "/api/account/claim", pc.claim_body(link["code"], "Gaming PC"), headers={"Origin": "null"})
check("http: launcher claim (no cookie needed)", st == 200 and out["account"] == "Tester", out)
st, out, _ = req("GET", "/api/account/link/status?code=" + link["code"], cookie=cookie)
check("http: page sees the link", out.get("state") == "linked")
st, prof, r = req("GET", "/api/account/profile?u=tester")
check("http: public profile", st == 200 and prof["name"] == "Tester" and r.getheader("Access-Control-Allow-Origin") == "*")
st, out, _ = req("GET", "/api/account/reserved.txt")
check("http: reserved list", st == 200 and out.startswith("TCPNAMES1") and pc.kid in out)
st, out, _ = req("GET", "/internal/lookup?name=tester")
check("http: internal route needs the token", st == 404)
st, out, _ = req("GET", "/internal/lookup?name=tester", headers={"X-Accounts-Token": "tok-internal"})
check("http: internal lookup for the bot", st == 200 and out["keys"][0]["id"] == pc.kid)
st, out, _ = req("GET", "/internal/lookup?name=tester", headers={"X-Accounts-Token": "tok-internal", "X-Forwarded-For": "1.1.1.1"})
check("http: internal route never through the proxy", st == 404)
st, out, r = req("GET", "/api/account/export", cookie=cookie)
check("http: export download", st == 200 and "attachment" in (r.getheader("Content-Disposition") or ""))
st, out, _ = req("POST", "/api/account/delete", {"confirm": "nope"}, cookie, {"X-CSRF": csrf})
check("http: delete needs the name typed", st == 400)
st, out, _ = req("POST", "/api/account/delete", {"confirm": "tester"}, cookie, {"X-CSRF": csrf})
check("http: delete", st == 200 and req("GET", "/api/account/me", cookie=cookie)[1] == {"signedIn": False})
st, out, _ = req("GET", "/api/account/../internal/lookup")
check("http: odd paths are 404", st == 404)
st, out, _ = req("POST", "/api/account/claim", {"code": "x"})
check("http: malformed claim is 400", st == 400)
srv.shutdown()

# stats route token
os.environ["TCP_STATS_ACCOUNTS_TOKEN"] = "acct-tok"
body = json.dumps({"aliases": []}).encode()
r = S.handle_staff(db, "POST", "/staff/accounts/aliases", {"X-Accounts-Token": "acct-tok"}, "127.0.0.1", body, "staff-tok")
check("stats: alias route with the account token", r[0] == 200, r)
r = S.handle_staff(db, "POST", "/staff/accounts/aliases", {"X-Staff-Token": "staff-tok"}, "127.0.0.1", body, "staff-tok")
check("stats: the staff portal's token cannot set aliases", r[0] == 404)
r = S.handle_staff(db, "POST", "/staff/accounts/aliases", {"X-Accounts-Token": "acct-tok"}, "8.8.8.8", body, "staff-tok")
check("stats: alias route loopback only", r[0] == 404)

failed = [n for n, ok in checks if not ok]
print("%d/%d checks passed" % (len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
