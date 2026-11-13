#!/usr/bin/env python3
"""Player accounts 1.1: QR pairing, passkeys, the lost-PC button, name history, looking for a squad, the weekly report
list, bans that follow the account, clean-record and trusted badges, and the stats service's service record, career,
rivals, weekly numbers and accounts-only ranked board.

  python3 test_accounts_more.py

Needs the 'cryptography' package to act as the launcher and as a passkey authenticator (test only)."""
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
import tcp_webauthn as W  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

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


def error_of(fn):
    try:
        fn()
    except A.ApiError as e:
        return e.message
    return ""


class PC:
    def __init__(self):
        self.sk = Ed25519PrivateKey.generate()
        self.pub = self.sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        self.kid = hashlib.sha256(bytes.fromhex(self.pub)).hexdigest()[:40]

    def pair_body(self, label="Desk PC", t=None):
        t = str(int(t if t is not None else time.time()))
        sig = self.sk.sign(A.PAIR_TAG + t.encode() + b"\n" + self.pub.encode()).hex()
        return {"public": self.pub, "t": t, "signature": sig, "label": label}


# ------------------------------------------------------------------ CBOR encoder for the fake authenticator
def cbor(v):
    def head(major, n):
        if n < 24:
            return bytes([major << 5 | n])
        for info, size in ((24, 1), (25, 2), (26, 4), (27, 8)):
            if n < 1 << (8 * size):
                return bytes([major << 5 | info]) + n.to_bytes(size, "big")
        raise ValueError
    if v is None:
        return b"\xf6"
    if isinstance(v, bool):
        return b"\xf5" if v else b"\xf4"
    if isinstance(v, int):
        return head(0, v) if v >= 0 else head(1, -1 - v)
    if isinstance(v, bytes):
        return head(2, len(v)) + v
    if isinstance(v, str):
        b = v.encode()
        return head(3, len(b)) + b
    if isinstance(v, list):
        return head(4, len(v)) + b"".join(cbor(x) for x in v)
    if isinstance(v, dict):
        return head(5, len(v)) + b"".join(cbor(k) + cbor(x) for k, x in v.items())
    raise TypeError(v)


class Authenticator:
    """A passkey: ES256 or Ed25519, discoverable, with a signature counter."""

    def __init__(self, kind="es256", counter=True):
        self.kind, self.count, self.counter = kind, 0, counter
        self.cred = hashlib.sha256(str(time.time_ns()).encode() + kind.encode()).digest()
        if kind == "es256":
            self.sk = ec.generate_private_key(ec.SECP256R1())
            n = self.sk.public_key().public_numbers()
            self.cose = {1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")}
        else:
            self.sk = Ed25519PrivateKey.generate()
            raw = self.sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            self.cose = {1: 1, 3: -8, -1: 6, -2: raw}
        self.user = b""

    def _sign(self, msg):
        if self.kind == "es256":
            return self.sk.sign(msg, ec.ECDSA(hashes.SHA256()))
        return self.sk.sign(msg)

    def create(self, options, origin, rp_id=None):
        rp_id = rp_id or options["rp"]["id"]
        self.user = W.unb64u(options["user"]["id"])
        cd = json.dumps({"type": "webauthn.create", "challenge": options["challenge"], "origin": origin}).encode()
        auth = (hashlib.sha256(rp_id.encode()).digest() + bytes([0x45]) + self.count.to_bytes(4, "big") + b"\0" * 16
                + len(self.cred).to_bytes(2, "big") + self.cred + cbor(self.cose))
        return {"id": W.b64u(self.cred), "clientDataJSON": W.b64u(cd),
                "attestationObject": W.b64u(cbor({"fmt": "none", "attStmt": {}, "authData": auth}))}

    def get(self, options, origin, challenge=None, rp_id=None):
        if self.counter:
            self.count += 1
        rp_id = rp_id or options["rpId"]
        cd = json.dumps({"type": "webauthn.get", "challenge": challenge or options["challenge"], "origin": origin}).encode()
        auth = hashlib.sha256(rp_id.encode()).digest() + bytes([0x05]) + self.count.to_bytes(4, "big")
        sig = self._sign(auth + hashlib.sha256(cd).digest())
        return {"id": W.b64u(self.cred), "clientDataJSON": W.b64u(cd), "authenticatorData": W.b64u(auth),
                "signature": W.b64u(sig), "userHandle": W.b64u(self.user)}


SITE = "https://truecombat.eu"
tmp = pathlib.Path(tempfile.mkdtemp())
acc = A.Accounts({"data_dir": str(tmp), "site_url": SITE, "public_url": SITE, "reserved_dirs": [str(tmp / "srv" / "accounts")]})


def session(did, name="Disc"):
    return acc.session(acc.new_session(did, name, "", "203.0.113.9"))


s1 = session("501", "Razic")
a1 = acc.signup(s1, "Razic", "public", True)
s1 = acc.session(acc.new_session("501", "Razic", "", "203.0.113.9"))

# ------------------------------------------------------------------ 1. QR pairing
pc = PC()
start = acc.pair_start(**dict(zip(("public_hex", "stamp", "signature_hex", "label"),
                                  (lambda b: (b["public"], b["t"], b["signature"], b["label"]))(pc.pair_body()))), ip="1.1.1.1")
check("pair: the launcher gets a QR address on the site", start["url"] == SITE + "/account?pair=" + start["pair"])
check("pair: the launcher waits", acc.pair_status(start["pair"])["state"] == "waiting")
info = acc.pair_info(s1["account"], start["pair"])
check("pair: the phone sees which PC asks", info["label"] == "Desk PC" and info["key"] == pc.kid[:8])
acc.pair_answer(s1["account"], start["pair"], True)
st = acc.pair_status(start["pair"])
check("pair: approved on the phone links the PC", st == {"state": "linked", "account": "Razic"}, st)
check("pair: the key is on the account", [k["kid"] for k in acc.keys_of(a1["id"], True)] == [pc.kid])
check("pair: a used code cannot be approved twice", raises(lambda: acc.pair_answer(s1["account"], start["pair"], True), 410))
old = pc.pair_body(t=time.time() - 3600)
check("pair: an old signed time is refused", raises(lambda: acc.pair_start(old["public"], old["t"], old["signature"], "", "1.1.1.1"), 400))
bad = pc.pair_body()
bad["label"] = "x"
other = PC().pair_body()
check("pair: a signature by another key is refused",
      raises(lambda: acc.pair_start(pc.pub, other["t"], other["signature"], "", "1.1.1.1"), 401))
pc2 = PC()
b2 = pc2.pair_body("Laptop")
st2 = acc.pair_start(b2["public"], b2["t"], b2["signature"], b2["label"], "1.1.1.1")
acc.pair_answer(s1["account"], st2["pair"], False)
check("pair: refusing on the phone links nothing", acc.pair_status(st2["pair"])["state"] == "refused"
      and pc2.kid not in [k["kid"] for k in acc.keys_of(a1["id"], True)])
check("pair: unknown code", acc.pair_status("0" * 32)["state"] == "unknown")

# ------------------------------------------------------------------ 2. passkeys
for kind in ("es256", "ed25519"):
    auth = Authenticator(kind)
    ticket, opts = acc.passkey_register_begin(acc.account(a1["id"]))
    check("passkey %s: options ask for a discoverable key on truecombat.eu" % kind,
          opts["rp"]["id"] == "truecombat.eu" and opts["authenticatorSelection"]["residentKey"] == "required")
    res = acc.passkey_register_finish(acc.account(a1["id"]), ticket, dict(auth.create(opts, SITE), label="Phone"))
    check("passkey %s: added" % kind, res["ok"] and res["label"] == "Phone")
    ticket, lo = acc.passkey_login_begin("9.9.9.9")
    sid = acc.passkey_login_finish(ticket, auth.get(lo, SITE), "9.9.9.9")
    s = acc.session(sid)
    check("passkey %s: signs in to the account" % kind, s and s["account"]["id"] == a1["id"])
    ticket, lo = acc.passkey_login_begin("9.9.9.9")
    check("passkey %s: a ticket works once" % kind,
          acc.passkey_login_finish(ticket, auth.get(lo, SITE), "9.9.9.9")
          and raises(lambda: acc.passkey_login_finish(ticket, auth.get(lo, SITE), "9.9.9.9"), 400))
    ticket, lo = acc.passkey_login_begin("9.9.9.9")
    check("passkey %s: another site's origin is refused" % kind,
          raises(lambda: acc.passkey_login_finish(ticket, auth.get(lo, "https://evil.example"), "9.9.9.9"), 401))
    ticket, lo = acc.passkey_login_begin("9.9.9.9")
    check("passkey %s: a signature over another challenge is refused" % kind,
          raises(lambda: acc.passkey_login_finish(ticket, auth.get(lo, SITE, challenge=W.b64u(b"x" * 32)), "9.9.9.9"), 401))
    ticket, lo = acc.passkey_login_begin("9.9.9.9")
    forged = auth.get(lo, SITE)
    forged["signature"] = W.b64u(Authenticator(kind)._sign(b"nope"))
    check("passkey %s: a forged signature is refused" % kind, raises(lambda: acc.passkey_login_finish(ticket, forged, "9.9.9.9"), 401))
    ticket, lo = acc.passkey_login_begin("9.9.9.9")
    replay = auth.get(lo, SITE)
    auth.count -= 5
    ticket2, lo2 = acc.passkey_login_begin("9.9.9.9")
    check("passkey %s: a counter that goes back (a copied key) is refused" % kind,
          acc.passkey_login_finish(ticket, replay, "9.9.9.9") and raises(lambda: acc.passkey_login_finish(ticket2, auth.get(lo2, SITE), "9.9.9.9"), 401))
ticket, opts = acc.passkey_register_begin(acc.account(a1["id"]))
dup = Authenticator("es256")
acc.passkey_register_finish(acc.account(a1["id"]), ticket, dup.create(opts, SITE))
ticket, opts = acc.passkey_register_begin(acc.account(a1["id"]))
check("passkey: the same credential cannot be added twice",
      raises(lambda: acc.passkey_register_finish(acc.account(a1["id"]), ticket, dup.create(opts, SITE)), 409))
ticket, opts = acc.passkey_register_begin(acc.account(a1["id"]))
check("passkey: registration for another site is refused",
      raises(lambda: acc.passkey_register_finish(acc.account(a1["id"]), ticket, Authenticator().create(opts, SITE, rp_id="evil.example")), 400))
me = acc.me(acc.session(acc.new_session("501", "Razic", "", "1.1.1.1")))
check("passkeys listed on the account page", len(me["account"]["passkeys"]) == 3)
acc.passkey_remove(acc.account(a1["id"]), me["account"]["passkeys"][0]["id"])
check("passkey removed", len(acc.me(acc.session(acc.new_session("501", "R", "", "1.1.1.1")))["account"]["passkeys"]) == 2)
check("passkey: an unknown credential cannot sign in",
      raises(lambda: acc.passkey_login_finish(acc.passkey_login_begin("8.8.8.8")[0], Authenticator().get(
          {"rpId": "truecombat.eu", "challenge": "x"}, SITE), "8.8.8.8"), 401))


def cbor_refuses(raw):
    try:
        W.cbor_decode(raw)
    except W.CborError:
        return True
    return False


check("CBOR: refuses truncated, indefinite and too-deep data",
      cbor_refuses(b"\x58\x10ab") and cbor_refuses(b"\x5f") and cbor_refuses(b"\x81" * 40 + b"\x00"))
check("CBOR: round trip of what WebAuthn sends", W.cbor_decode(cbor({1: 2, -1: b"xy", "fmt": "none", "a": [True, None]}))[0]
      == {1: 2, -1: b"xy", "fmt": "none", "a": [True, None]})

# ------------------------------------------------------------------ 9. name history
acc.store.x("UPDATE accounts SET name_changed=0 WHERE id=?", (a1["id"],))
acc.rename(acc.account(a1["id"]), "Razor")
p = acc.profile("Razor")
check("name history: the profile shows the old name for 30 days", p["formerly"] == ["Razic"], p)
acc.store.x("UPDATE name_history SET until=1")
acc.tidy()
check("name history: gone after 30 days", acc.profile("Razor")["formerly"] == [])

# ------------------------------------------------------------------ 12. looking for a squad
s1 = acc.session(acc.new_session("501", "Razic", "", "1.1.1.1"))
acc.lfs(s1["account"], True, "  EU evenings, ^1chill^7 obj  ", 3)
lst = acc.lfs_list()
check("squad: listed with a clean note", lst and lst[0]["name"] == "Razor" and lst[0]["note"] == "EU evenings, chill obj", lst)
check("squad: an abusive note is refused", raises(lambda: acc.lfs(s1["account"], True, "n1gger", 1), 400))
check("squad: hours capped", acc.lfs(s1["account"], True, "", 99)["until"] <= A.now() + A.LFS_HOURS * 3600)
acc.lfs(s1["account"], False, "", 0)
check("squad: off", acc.lfs_list() == [])

# ------------------------------------------------------------------ 11. weekly report opt-in
acc.settings(s1, None, None, True)
check("weekly: opted in", [w["discordId"] for w in acc.weekly_list()] == ["501"])

# ------------------------------------------------------------------ 15/16. badges
s3 = session("503", "Veteran")
a3 = acc.signup(s3, "Veteran", "public", True)
pc3 = PC()
b3 = pc3.pair_body("Rig")
acc.pair_answer(acc.account(a3["id"]), acc.pair_start(b3["public"], b3["t"], b3["signature"], "Rig", "2.2.2.2")["pair"], True)
check("badges: a new account has none", acc.badges(acc.account(a3["id"])) == [])
acc.store.x("UPDATE accounts SET created=? WHERE id=?", (A.now() - 40 * 86400, a3["id"]))
acc.played({}, {A.account_pid(a3["id"]): {"matches": 25, "lastSeen": "2026-01-01T00:00:00Z"}})
check("badges: a month and 20 matches give the clean record", acc.badges(acc.account(a3["id"])) == ["clean"])
acc.store.x("UPDATE accounts SET created=? WHERE id=?", (A.now() - 70 * 86400, a3["id"]))
acc.played({}, {A.account_pid(a3["id"]): {"matches": 60}})
check("badges: two months and 50 matches make a trusted player", acc.badges(acc.account(a3["id"])) == ["clean", "trusted"])
check("trusted list carries the key's tag", A.key_tag(pc3.kid) in acc.trusted_txt() and pc3.kid not in acc.trusted_txt())
check("badges.json for the site", acc.badges_json().get(A.account_pid(a3["id"])) == ["clean", "trusted"])
acc.sanction({"id": a3["id"]}, "warning", "spawn camping abuse", 0, "staff1")
check("badges: a warning clears them for 90 days", acc.badges(acc.account(a3["id"])) == [])

# ------------------------------------------------------------------ 13. bans follow the account
s4 = session("504", "Cheater")
a4 = acc.signup(s4, "Cheater", "public", True)
pc4 = PC()
b4 = pc4.pair_body()
acc.pair_answer(acc.account(a4["id"]), acc.pair_start(b4["public"], b4["t"], b4["signature"], "", "3.3.3.3")["pair"], True)
r = acc.sanction({"name": "Cheater"}, "ban", "aimbot", 0, "staff1")
check("ban: covers the account's PCs", r["keys"] == 1)
check("ban: the ban list has the PC's tag, permanent", "%s 0" % A.key_tag(pc4.kid) in acc.bans_txt())
check("ban: signed out everywhere", acc.store.one("SELECT COUNT(*) n FROM sessions WHERE discord_id='504'")["n"] == 0)
check("ban: profile hidden", acc.profile("Cheater") is None and A.account_pid(a4["id"]) not in acc.names_json())
pc5 = PC()
b5 = pc5.pair_body()
st5 = acc.pair_start(b5["public"], b5["t"], b5["signature"], "", "3.3.3.3")
check("ban: a new PC cannot join the banned account", raises(lambda: acc.pair_answer(acc.account(a4["id"]), st5["pair"], True), 403))
b4b = pc4.pair_body()
check("ban: the banned PC cannot pair at all", raises(lambda: acc.pair_start(b4b["public"], b4b["t"], b4b["signature"], "", "3.3.3.3"), 403))
s4b = acc.session(acc.new_session("504", "Cheater", "", "3.3.3.3"))
check("ban: the page says so", acc.me(s4b)["account"]["banned"]["reason"] == "aimbot")
acc.delete(acc.account(a4["id"]))
s4c = acc.session(acc.new_session("504", "Cheater", "", "3.3.3.3"))
check("ban: deleting the account does not lift it", raises(lambda: acc.signup(s4c, "Fresh", "public", True), 403))
check("ban: the PCs stay banned after the delete", "%s 0" % A.key_tag(pc4.kid) in acc.bans_txt())
bid = acc.bans_list()[0]["id"]
acc.lift(bid)
check("ban: lifted", A.key_tag(pc4.kid) not in acc.bans_txt() and acc.signup(s4c, "Fresh", "public", True)["name"] == "Fresh")
r = acc.sanction({"discord": "501"}, "ban", "test", 7, "staff1")
check("ban: a timed ban ends", acc.ban_of(account=a1["id"])["until"] > A.now() + 6 * 86400)
acc.lift(r["ban"])

# ------------------------------------------------------------------ 3. lost or stolen PC
s1 = acc.session(acc.new_session("501", "Razic", "", "1.1.1.1"))
other = acc.session(acc.new_session("501", "Razic", "", "1.1.1.2"))
acc.panic(s1["account"])
check("lost PC: every PC unlinked", acc.keys_of(a1["id"], True) == [] and len(acc.keys_of(a1["id"])) == 1)
check("lost PC: every session signed out", acc.store.one("SELECT COUNT(*) n FROM sessions WHERE discord_id='501'")["n"] == 0)

# ------------------------------------------------------------------ lists for the game servers
acc.push()
d = tmp / "srv" / "accounts"
check("game server lists written: names, bans, trusted", all((d / f).read_text().startswith(h) for f, h in
      (("names.txt", "TCPNAMES2"), ("bans.txt", "TCPBANS1"), ("trusted.txt", "TCPTRUST1"))))
check("game server lists are readable by the game", all((d / f).stat().st_mode & 0o044 == 0o044 for f in ("names.txt", "bans.txt", "trusted.txt")))
check("export carries the new data", set(("nameHistory", "passkeys", "lookingForSquad", "weeklyReport", "sanctions"))
      <= set(acc.export(acc.account(a1["id"]))))
roles = {r["discordId"]: r for r in acc.roles()}
check("bot roles: every account with its stats id and badges", roles["503"]["badges"] == [] and "statsId" in roles["501"])

# ------------------------------------------------------------------ HTTP
import os  # noqa: E402
os.environ["TCP_ACCOUNTS_DEV"] = "1"
hacc = A.Accounts({"data_dir": str(tmp / "http"), "public_url": "http://127.0.0.1", "site_url": "http://127.0.0.1",
                   "dev_login": True, "internal_token": "itok"})
srv = ThreadingHTTPServer(("127.0.0.1", 0), A.make_handler(hacc))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def req(method, path, body=None, cookie="", headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    h = dict(headers or {})
    if cookie:
        h["Cookie"] = cookie
    if body is not None:
        h["Content-Type"] = "application/json"
    c.request(method, path, json.dumps(body).encode() if body is not None else None, h)
    r = c.getresponse()
    raw = r.read()
    try:
        out = json.loads(raw)
    except ValueError:
        out = raw.decode()
    return r.status, out, r


st, _, r = req("GET", "/api/account/dev?id=777&name=Http")
cookie = r.getheader("Set-Cookie").split(";")[0]
st, me, _ = req("GET", "/api/account/me", cookie=cookie)
csrf = me["csrf"]
H = {"X-CSRF": csrf}
req("POST", "/api/account/signup", {"name": "Httper", "visibility": "public", "age13": True}, cookie, H)
hp = PC()
st, ps, _ = req("POST", "/api/account/pair/start", hp.pair_body("Box"))
check("http: launcher starts a pairing without a cookie", st == 200 and ps["url"].endswith("/account?pair=" + ps["pair"]), ps)
st, inf, _ = req("GET", "/api/account/pair/info?id=" + ps["pair"], cookie=cookie)
check("http: the phone reads what it approves", st == 200 and inf["label"] == "Box")
st, _, _ = req("POST", "/api/account/pair/approve", {"id": ps["pair"]}, cookie)
check("http: approving needs the CSRF header", st == 403)
st, _, _ = req("POST", "/api/account/pair/approve", {"id": ps["pair"]}, cookie, dict(H, Origin="https://evil.example"))
check("http: approving from another site is refused", st == 403)
st, out, _ = req("POST", "/api/account/pair/approve", {"id": ps["pair"]}, cookie, H)
check("http: approved", st == 200 and out["state"] == "linked")
st, out, _ = req("GET", "/api/account/pair/status?id=" + ps["pair"])
check("http: the launcher sees the account name", out == {"state": "linked", "account": "Httper"}, out)
auth = Authenticator("es256")
st, rb, _ = req("POST", "/api/account/passkey/register/begin", {}, cookie, H)
st, out, _ = req("POST", "/api/account/passkey/register/finish",
                 dict(auth.create(rb["options"], "http://127.0.0.1"), ticket=rb["ticket"], label="Hello"), cookie, H)
check("http: passkey added", st == 200 and out["account"]["passkeys"][0]["label"] == "Hello", out)
st, lb, _ = req("POST", "/api/account/passkey/login/begin", {})
st, out, r = req("POST", "/api/account/passkey/login/finish", dict(auth.get(lb["options"], "http://127.0.0.1"), ticket=lb["ticket"]))
check("http: passkey sign-in sets the session cookie", st == 200 and out["account"]["name"] == "Httper"
      and (r.getheader("Set-Cookie") or "").startswith("tcpacct="), out)
st, out, _ = req("POST", "/api/account/lfs", {"on": True, "note": "obj only", "hours": 2}, cookie, H)
st, lf, r = req("GET", "/api/account/lfs.json")
check("http: squad list is public and short-cached", st == 200 and lf["players"][0]["note"] == "obj only"
      and "max-age=30" in r.getheader("Cache-Control"))
st, out, _ = req("GET", "/api/account/internal/roles")
check("http: internal lists are not under the public prefix", st == 404)
st, out, _ = req("GET", "/internal/roles", headers={"X-Accounts-Token": "itok"})
check("http: bot reads the roles list", st == 200 and out["accounts"][0]["name"] == "Httper", out)
st, out, _ = req("POST", "/internal/ban", {"name": "Httper", "reason": "test", "days": 1, "by": "t"}, headers={"X-Accounts-Token": "itok"})
check("http: staff ban through the internal route", st == 200 and out["keys"] == 1, out)
st, out, _ = req("GET", "/api/account/bans.txt")
check("http: public ban list (tags only)", st == 200 and out.startswith("TCPBANS1") and A.key_tag(hp.kid) in out and hp.kid not in out)
st, out, _ = req("GET", "/api/account/me", cookie=cookie)
check("http: banned sessions are signed out", out == {"signedIn": False}, out)
st, out, _ = req("GET", "/internal/bans", headers={"X-Accounts-Token": "itok"})
req("POST", "/internal/unban", {"ban": out["bans"][0]["id"]}, headers={"X-Accounts-Token": "itok"})
st, _, r = req("GET", "/api/account/dev?id=777&name=Http")
cookie = r.getheader("Set-Cookie").split(";")[0]
st, me, _ = req("GET", "/api/account/me", cookie=cookie)
st, out, r = req("POST", "/api/account/panic", {"confirm": True}, cookie, {"X-CSRF": me["csrf"]})
check("http: lost-PC button signs out", st == 200 and "Max-Age=0" in r.getheader("Set-Cookie"))
srv.shutdown()

# ------------------------------------------------------------------ stats: service record, career, rivals, week
db = S.StatsStore(":memory:", min_matches=1, require_anticheat=True)
G = {"Raz": "A" * 32, "Bob": "B" * 32, "Cid": "C" * 32, "Dan": "D" * 32}


def report(n, raz_kills=12, hours_ago=10.0, raz_wins=True):
    ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - hours_ago * 3600 + n * 60))
    players = []
    for nm, team in (("Raz", "specops"), ("Bob", "specops"), ("Cid", "terrorists"), ("Dan", "terrorists")):
        won = (team == "specops") == raz_wins
        players.append({"guid": G[nm], "name": nm, "team": team, "kills": raz_kills if nm == "Raz" else 2, "deaths": 1,
                        "headshots": 0, "damage": 500, "damageTaken": 500, "roundsWon": 6 if won else 4, "objectives": 0,
                        "won": won, "timePlayed": 900, "idle": 0, "ip": "a" + nm, "hits": {"head": 1, "body": 5},
                        "weapons": {}})
    kills = [[10000 + i * 1000, 1, 0 if raz_wins else 2, (2 + (i % 2)) if raz_wins else (i % 2), "M4", 0, 500, []]
             for i in range(raz_kills)]
    return {"schema": "tcp-match/2", "id": "m-%03d" % n, "server": "Official", "map": "obj_village", "mode": "Team elimination",
            "started": ended, "ended": ended, "duration": 900, "rounds": 10, "winner": "specops" if raz_wins else "terrorists",
            "eac": {"start": 2, "end": 2, "min": 2}, "password": False, "ranked": True, "botSeconds": 0,
            "players": players, "kills": kills, "events": []}


for i in range(6):
    db.ingest(report(i, raz_kills=22 if i == 2 else 12, hours_ago=200 - i * 30), "official1")
raz = S.player_id(G["Raz"])
md = db.medals(raz)
keys = [m["key"] for m in md["medals"]]
check("service record: career medals", "first_match" in keys and "first_win" in keys and "streak_5" in keys, keys)
check("service record: a match medal remembers the match", any(m["key"] == "match_20" and m["match"] for m in md["medals"]), md)
check("service record: rarest first", md["medals"][0]["tier"] == 3)
check("service record: same names as the Discord bot", S.MEDALS["match_20"][0] == "Wrecking crew")
cr = db.career(raz)
check("career: month by month", cr["months"] and sum(m["matches"] for m in cr["months"]) == 6 and cr["bestMatches"][0]["kills"] >= 20, cr)
rv = db.rivals(raz)
check("rivals: the players met on the other side", {r["id"] for r in rv["rivals"]} == {S.player_id(G["Cid"]), S.player_id(G["Dan"])}
      and rv["rivals"][0]["matches"] == 6 and rv["rivals"][0]["wins"] == 6, rv)
wk = db.week(raz)
check("week: this week against last week", wk["week"]["matches"] + wk["before"]["matches"] <= 6 and "newMedals" in wk, wk)
db.set_aliases([{"pid": raz, "canonical": "f" * 16, "since": None, "until": None}])
lb_all = db.leaderboard(who="all")["players"]
lb_acc = db.leaderboard(who="accounts")["players"]
check("ranked board: accounts only on request", [p["id"] for p in lb_acc] == ["f" * 16] and len(lb_all) == 4, (lb_acc, len(lb_all)))
db.ranked_accounts_only = True
check("ranked board: the switch makes it the default", [p["id"] for p in db.leaderboard()["players"]] == ["f" * 16])
check("ranked board: ?who=all still shows everyone", len(db.leaderboard(who="all")["players"]) == 4)
code, body = S.handle_get(db, "/medals.json", {"id": ["f" * 16]})
check("routes: medals, career, rivals, week", code == 200 and all(S.handle_get(db, r, {"id": ["f" * 16]})[0] == 200
                                                                  for r in ("/career.json", "/rivals.json", "/week.json")))
os.environ["TCP_STATS_ACCOUNTS_TOKEN"] = "t"
code, body = S.handle_staff(db, "POST", "/staff/accounts/aliases", {"X-Accounts-Token": "t"}, "127.0.0.1",
                            json.dumps({"aliases": [{"pid": raz, "canonical": "f" * 16, "since": None, "until": None}]}).encode(), "")
check("alias answer carries matches per account", body["players"]["f" * 16]["matches"] == 6, body)

# ------------------------------------------------------------------ Team Terminus ribbon
acc.cfg["team"] = {"501": "Founder \u00b7 Lead Developer", "777": "Moderator"}
raz_name = acc.account(a1["id"])["name"]
pr = acc.profile(raz_name)
check("team: the ribbon follows the Discord sign-in", pr and pr.get("team") == {"name": "Team Terminus", "role": "Founder \u00b7 Lead Developer"}, pr)
check("team: own page shows it too", acc.me(acc.session(acc.new_session("501", "R", "", "1.1.1.1")))["account"].get("team", {}).get("role"))
sx = session("778", "Copycat")
ax = acc.signup(sx, "RazicFan", "public", True)
check("team: other players get no ribbon", "team" not in acc.profile("RazicFan"))
tj = acc.team_json()
check("team: team.json lists public members only", [m["name"] for m in tj] == [raz_name] and tj[0]["statsId"] == A.account_pid(a1["id"]), tj)
acc.cfg["team"] = {}
check("team: off when the list is empty", "team" not in acc.profile(raz_name) and acc.team_json() == [])

failed = [n for n, ok in checks if not ok]
print("%d/%d checks passed" % (len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
