#!/usr/bin/env python3
"""Devlog comments (accounts 1.3.0): posting, holds, limits, replies, likes, reports, staff moderation, deleting with
the account, export, retention, the HTTP routes and the sign-in return to the post.

  python3 test_comments.py
"""
import hashlib
import http.client
import json
import os
import pathlib
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tcp_accounts as A  # noqa: E402
import tcp_comments as C  # noqa: E402

checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)))


def status_of(fn):
    try:
        fn()
    except A.ApiError as e:
        return e.status, e.message
    return 200, ""


class Clock:
    t = 1_800_000_000

    def __call__(self):
        return self.t


tmp = pathlib.Path(tempfile.mkdtemp())
site = tmp / "site"
site.mkdir()
for slug, on in (("inside-0372", "on"), ("quiet-post", "off")):
    (site / ("devlog-%s.html" % slug)).write_text('<section class="cmt" data-comments="%s"></section>' % on, encoding="utf-8")

clock = Clock()
A.now = clock                                   # the service and the module read the same clock
acc = A.Accounts({"data_dir": str(tmp / "a"), "team": {"900": "Founder"}, "comments": {"site_root": str(site), "words": ["badword"]}})
acc.comments.now = clock


def _limited(key, count, window):          # the service's in-memory limiter, on the test clock
    t = clock()
    hits = [h for h in acc.rate.get(key, []) if t - h < window]
    if len(hits) >= count:
        acc.rate[key] = hits
        return True
    acc.rate[key] = hits + [t]
    return False


acc.limited = _limited


def player(discord, name, pc=True, team=False):
    sid = acc.new_session(discord, name, "", "10.0.0.%d" % (int(discord) % 250))
    s = acc.session(sid)
    acc.signup(s, name, "public", True)
    s = acc.session(sid)
    if pc:
        kid = hashlib.sha256(name.encode()).hexdigest()[:40]
        acc.store.x("INSERT INTO keys(kid, account, public, label, linked, retired) VALUES(?,?,?,?,?,NULL)",
                    (kid, s["account"]["id"], "00" * 32, "PC", clock()))
    return s


def step(seconds=21):
    clock.t += seconds


viper = player("101", "Viper")
hexa = player("102", "Hexa")
kron = player("103", "kRonos")
moon = player("104", "Moonshot", pc=False)                 # web-only account: no linked PC
razic = player("900", "RaziC", team=True)
cm = acc.comments
P = "inside-0372"

# ------------------------------------------------------------------ text and posts
check("clean_text keeps line breaks, drops control chars and blank runs",
      C.clean_text("  hi​ there\r\n\r\n\r\n\r\nnext\x07 line  ") == "hi there\n\nnext line")
check("links are recognised", C.has_link("visit www.cheap.shop") and C.has_link("http://x.y") and C.has_link("discord.gg/abc")
      and C.has_link("buy at keys.ru now") and not C.has_link("version 0.37.2 is out") and not C.has_link("e.g. this"))
check("post exists and is open", cm.post_state(P) == "open")
check("front matter comments: off closes a post", cm.post_state("quiet-post") == "closed")
check("unknown post is missing", cm.post_state("nope") == "missing" and cm.post_state("../etc/passwd") == "missing")
check("posting on a missing post: 404", status_of(lambda: cm.post(viper, {"post": "nope", "text": "hello"}, "1.1.1.1"))[0] == 404)
check("posting on a closed post: 409", status_of(lambda: cm.post(viper, {"post": "quiet-post", "text": "hello"}, "1.1.1.1"))[0] == 409)
check("too short: 400", status_of(lambda: cm.post(viper, {"post": P, "text": " a "}, "1.1.1.1"))[0] == 400)
check("too long: 400", status_of(lambda: cm.post(viper, {"post": P, "text": "x" * 1001}, "1.1.1.1"))[0] == 400)

# ------------------------------------------------------------------ posting, holds
r1 = cm.post(viper, {"post": P, "text": "Grenade throws finally land where the arc says."}, "1.1.1.1")
check("player with a linked PC posts straight away", r1["ok"] and not r1["held"])
check("20 s between comments", status_of(lambda: cm.post(viper, {"post": P, "text": "Second one"}, "1.1.1.1"))[0] == 429)
step()
check("the same text twice in a day is refused",
      status_of(lambda: cm.post(viper, {"post": P, "text": "Grenade throws finally land where the arc says."}, "1.1.1.1"))[0] == 409)
step()
rm = cm.post(moon, {"post": P, "text": "Names over teammates are so much easier to read."}, "2.2.2.2")
check("first comment of an account with no linked PC is held", rm["held"])
lst = cm.listing(P, "new", None)
check("held comment is invisible to others", all(c["id"] != rm["id"] for c in lst["comments"]) and lst["count"] == 1)
lst_m = cm.listing(P, "new", moon)
mine = [c for c in lst_m["comments"] if c["id"] == rm["id"]]
check("held comment is shown to its author, marked held and mine", mine and mine[0].get("held") and mine[0].get("mine"))
check("viewer says the first comment will be checked", lst_m["viewer"]["firstHeld"] is True and lst_m["viewer"]["canPost"])
step()
rf = cm.post(hexa, {"post": P, "text": "This patch is badword great"}, "3.3.3.3")
check("config filter word holds a comment", rf["held"])
step()
rf2 = cm.post(hexa, {"post": P, "text": "what a retard update"}, "3.3.3.3")
check("abuse list holds a comment", rf2["held"])
step()
rl = cm.post(kron, {"post": P, "text": "Lineups video: youtube.com/watch?v=abc"}, "4.4.4.4")
check("a link from an account with a linked PC posts", not rl["held"])
step()
rt = cm.post(razic, {"post": P, "text": "Thanks for the reports. Press F12 in game so we get the demo."}, "5.5.5.5")
check("team members are never held", not rt["held"])
check("team member is not rate limited", not cm.post(razic, {"post": P, "text": "And one more thing."}, "5.5.5.5")["held"])

# ------------------------------------------------------------------ replies
step()
rr = cm.post(kron, {"post": P, "text": "Same on Railhouse.", "parent": r1["id"]}, "4.4.4.4")
step()
rr2 = cm.post(hexa, {"post": P, "text": "Reply to a reply", "parent": rr["id"]}, "3.3.3.3")
row = acc.store.one("SELECT parent FROM cm_comments WHERE id=?", (rr2["id"],))
check("replies stay one level deep (a reply to a reply joins the thread)", row["parent"] == r1["id"])
check("reply to another post's comment refused",
      status_of(lambda: cm.post(hexa, {"post": "quiet-post", "text": "x y", "parent": r1["id"]}, "3.3.3.3"))[0] in (400, 409))

# ------------------------------------------------------------------ listing
lst = cm.listing(P, "new", viper)
top = {c["id"]: c for c in lst["comments"]}
check("thread holds its replies, oldest first", [k["id"] for k in top[r1["id"]]["replies"]] == [rr["id"], rr2["id"]])
check("team flag and profile link", top[rt["id"]]["team"] is True and top[rt["id"]]["profile"] is True)
check("own comment marked mine and editable", top[r1["id"]].get("mine") and top[r1["id"]].get("editable"))
check("count = visible comments incl. replies", lst["count"] == 6, lst["count"])
check("no Discord data in the listing", "discord" not in json.dumps(lst).lower().replace('"discord":', ""))
check("newest first", lst["comments"][0]["at"] >= lst["comments"][-1]["at"])
check("oldest first", cm.listing(P, "old", None)["comments"][0]["id"] == r1["id"])

# ------------------------------------------------------------------ likes
check("can't like your own comment", status_of(lambda: cm.like(viper, {"id": r1["id"]}))[0] == 409)
cm.like(hexa, {"id": r1["id"]})
cm.like(kron, {"id": r1["id"]})
out = cm.like(kron, {"id": r1["id"]})
check("likes count each player once", out["likes"] == 2)
check("top sort puts the most liked first", cm.listing(P, "top", None)["comments"][0]["id"] == r1["id"])
check("viewer sees what they liked", [c for c in cm.listing(P, "new", hexa)["comments"] if c["id"] == r1["id"]][0].get("liked"))
cm.like(kron, {"id": r1["id"], "on": False})
check("unlike", acc.store.one("SELECT likes FROM cm_comments WHERE id=?", (r1["id"],))["likes"] == 1)
check("can't like a held comment", status_of(lambda: cm.like(viper, {"id": rm["id"]}))[0] == 409)

# ------------------------------------------------------------------ edit and delete
check("someone else's comment can't be edited", status_of(lambda: cm.edit(hexa, {"id": r1["id"], "text": "hacked"}))[0] == 403)
cm.edit(viper, {"id": r1["id"], "text": "Grenade throws land where the arc says. Village B feels new."})
r = acc.store.one("SELECT * FROM cm_comments WHERE id=?", (r1["id"],))
check("edit within 15 minutes, marked edited", r["edited"] and "Village" in r["text"])
cm.edit(kron, {"id": rl["id"], "text": "Lineups video badword"})
check("an edit that hits the filter puts the comment on hold",
      acc.store.one("SELECT state FROM cm_comments WHERE id=?", (rl["id"],))["state"] == "held")
step(16 * 60)
check("no edits after 15 minutes", status_of(lambda: cm.edit(viper, {"id": r1["id"], "text": "late edit"}))[0] == 409)
check("someone else's comment can't be deleted", status_of(lambda: cm.delete(hexa, {"id": r1["id"]}))[0] == 403)

# ------------------------------------------------------------------ reports
check("can't report your own", status_of(lambda: cm.report(viper, {"id": r1["id"], "reason": "spam"}))[0] == 409)
check("report needs a reason", status_of(lambda: cm.report(hexa, {"id": r1["id"], "reason": "meh"}))[0] == 400)
step()
spam = cm.post(kron, {"post": P, "text": "Cheap boosts, ask me"}, "4.4.4.4")
for s in (viper, hexa, hexa):                                   # hexa twice counts once
    cm.report(s, {"id": spam["id"], "reason": "spam"})
check("two different reporters: still visible", acc.store.one("SELECT state FROM cm_comments WHERE id=?", (spam["id"],))["state"] == "live")
cm.report(razic, {"id": spam["id"], "reason": "spam", "note": "obvious"})
check("three different reporters hide it", acc.store.one("SELECT state, reason FROM cm_comments WHERE id=?", (spam["id"],))
      == {"state": "hidden", "reason": "reports"})
for s in (viper, hexa, kron):
    cm.report(s, {"id": rt["id"], "reason": "abuse"})
check("team comments are not auto-hidden by reports", acc.store.one("SELECT state FROM cm_comments WHERE id=?", (rt["id"],))["state"] == "live")

# ------------------------------------------------------------------ staff
st = cm.stats()
check("stats: held, hidden by reports, reported", st["held"] >= 3 and st["hidden"] == 1 and st["reported"] >= 1, st)
q = cm.queue("needs")["comments"]
ids = {c["id"] for c in q}
check("needs-a-look queue has held, hidden and reported", {rm["id"], rf["id"], spam["id"], rt["id"]} <= ids)
qm = [c for c in q if c["id"] == rm["id"]][0]
check("queue row carries author facts", qm["author"]["name"] == "Moonshot" and qm["author"]["pc"] is False and qm["reason"] == "new")
check("queue row lists the reports", len([c for c in q if c["id"] == spam["id"]][0]["reports"]) == 3)
cm.act({"id": rm["id"], "action": "publish", "by": "Mod"})
check("publish makes it live and trusts the author", acc.store.one("SELECT state FROM cm_comments WHERE id=?", (rm["id"],))["state"] == "live"
      and cm.trusted(moon["account"]["id"]))
step()
check("a trusted web-only account posts straight away",
      not cm.post(moon, {"post": P, "text": "Thanks for approving, great update."}, "2.2.2.2")["held"])
step()
check("but its links still wait for a check", cm.post(moon, {"post": P, "text": "See www.example.com"}, "2.2.2.2")["held"])
cm.act({"id": spam["id"], "action": "hide", "by": "Mod"})
check("keep it hidden: reports closed, leaves the queue", spam["id"] not in {c["id"] for c in cm.queue("needs")["comments"]}
      and acc.store.one("SELECT reason FROM cm_comments WHERE id=?", (spam["id"],))["reason"] == "staff")
cm.act({"id": spam["id"], "action": "remove", "by": "Mod"})
check("remove: state removed, reports closed", acc.store.one("SELECT state FROM cm_comments WHERE id=?", (spam["id"],))["state"] == "removed"
      and not acc.store.one("SELECT 1 AS x FROM cm_reports WHERE comment=? AND closed IS NULL", (spam["id"],)))
check("removed comment without replies is gone from the page", all(c["id"] != spam["id"] for c in cm.listing(P, "new", None)["comments"]))
cm.act({"id": rt["id"], "action": "dismiss", "by": "Mod"})
check("dismiss closes the reports, comment stays", acc.store.one("SELECT state FROM cm_comments WHERE id=?", (rt["id"],))["state"] == "live"
      and rt["id"] not in {c["id"] for c in cm.queue("needs")["comments"]})
cm.act({"id": rt["id"], "action": "pin", "by": "Mod"})
check("pinned comment leads every sort", all(cm.listing(P, s, None)["comments"][0]["id"] == rt["id"] for s in ("new", "old", "top")))
check("replies can't be pinned", status_of(lambda: cm.act({"id": rr["id"], "action": "pin"}))[0] == 409)
cm.act({"id": r1["id"], "action": "hide", "by": "Mod"})
lst = cm.listing(P, "new", None)
ph = [c for c in lst["comments"] if c["id"] == r1["id"]]
check("hidden comment with replies leaves a placeholder without text or name",
      ph and ph[0].get("gone") == "hidden" and "text" not in ph[0] and "name" not in ph[0] and len(ph[0]["replies"]) == 2)
cm.act({"id": r1["id"], "action": "restore", "by": "Mod"})
check("restore", acc.store.one("SELECT state FROM cm_comments WHERE id=?", (r1["id"],))["state"] == "live")
check("unknown action refused", status_of(lambda: cm.act({"id": r1["id"], "action": "explode"}))[0] == 400)

cm.pause({"name": "Hexa", "days": 7, "reason": "spam", "by": "Mod"})
step()
code, msg = status_of(lambda: cm.post(hexa, {"post": P, "text": "am I paused?"}, "3.3.3.3"))
check("paused player can't post, message says until when", code == 403 and "until" in msg)
check("viewer shows the pause", cm.listing(P, "new", hexa)["viewer"].get("pausedUntil", 0) > clock())
check("paused tab lists the pause", cm.queue("paused")["paused"][0]["name"] == "Hexa")
step(8 * 86400)
check("pause ends by itself", status_of(lambda: cm.post(hexa, {"post": P, "text": "back again, hello"}, "3.3.3.3"))[0] == 200)
cm.pause({"account": hexa["account"]["id"], "days": 0, "by": "Mod"})
check("pause for good", cm.listing(P, "new", hexa)["viewer"].get("pausedUntil") == -1)
cm.unpause({"account": hexa["account"]["id"]})
check("unpause", "pausedUntil" not in cm.listing(P, "new", hexa)["viewer"])

cm.close({"post": P, "closed": True, "by": "Mod"})
check("staff can close a post", cm.post_state(P) == "closed" and cm.listing(P, "new", viper)["viewer"]["canPost"] is False)
check("closed post keeps its comments readable", cm.listing(P, "new", None)["count"] > 0)
cm.close({"post": P, "closed": False})
check("and open it again", cm.post_state(P) == "open")

rep = cm.staff_reply({"parent": rr["id"], "text": "That was the idea.", "discord": "900", "by": "RaziC"})
check("staff reply joins the thread as the staff member's account",
      acc.store.one("SELECT parent, account FROM cm_comments WHERE id=?", (rep["id"],)) == {"parent": r1["id"], "account": razic["account"]["id"]})
check("staff reply needs an account", status_of(lambda: cm.staff_reply({"parent": r1["id"], "text": "hi there", "discord": "555"}))[0] == 409)

# ------------------------------------------------------------------ bans
acc.sanction({"id": kron["account"]["id"]}, "ban", "cheating", 0, "Mod")
lst = cm.listing(P, "new", None)
check("a banned player's comments disappear from the page",
      all(k.get("name") != "kRonos" for c in lst["comments"] for k in [c] + c["replies"]))
check("a banned player can't post", status_of(lambda: cm.post(kron, {"post": P, "text": "let me in"}, "4.4.4.4"))[0] in (401, 403))

# ------------------------------------------------------------------ counts, export, deletion, retention
check("counts.json counts live comments per post", cm.counts().get(P, 0) >= 5)
exp = acc.export(viper["account"])
check("Download my data includes comments and likes", exp["devlogComments"]["comments"] and "likes" in exp["devlogComments"])
vid = viper["account"]["id"]
acc.delete(viper["account"])
row = acc.store.one("SELECT * FROM cm_comments WHERE id=?", (r1["id"],))
check("deleted account: its comment with replies stays as an empty, nameless line",
      row["state"] == "deleted" and row["text"] == "" and row["account"] is None)
check("deleted account: likes, reports, pause, trust gone",
      not acc.store.one("SELECT 1 AS x FROM cm_likes WHERE account=?", (vid,))
      and not acc.store.one("SELECT 1 AS x FROM cm_reports WHERE account=?", (vid,)))
lst = cm.listing(P, "new", None)
check("the page shows it as deleted", [c for c in lst["comments"] if c["id"] == r1["id"]][0]["gone"] == "deleted")
hid = hexa["account"]["id"]
acc.delete(hexa["account"])
check("deleted account: comments without replies are gone",
      not acc.store.one("SELECT 1 AS x FROM cm_comments WHERE account=?", (hid,)))
# the last reply under a deleted placeholder goes: the placeholder goes too
for k in acc.store.all("SELECT * FROM cm_comments WHERE parent=?", (r1["id"],)):
    with acc.store.tx() as db:
        cm._drop(db, k)
check("a deleted line with no replies left is pruned", not acc.store.one("SELECT 1 AS x FROM cm_comments WHERE id=?", (r1["id"],)))

# friends: deleting the account removes its Friends rows (they used to wait a year)
t = clock()
acc.store.x("INSERT INTO fr_people(id, code, name, name_lower, seen, last_t, created) VALUES(?,?,?,?,?,?,?)",
            ("a:" + moon["account"]["id"], "ABCD-EFGH", "Moonshot", "moonshot", t, t, t))
acc.store.x("INSERT INTO fr_links VALUES(?,?,?)", ("a:" + moon["account"]["id"], "k:" + "1" * 40, t))
acc.delete(moon["account"])
check("deleting an account removes its Friends data",
      not acc.store.one("SELECT 1 AS x FROM fr_people WHERE id=?", ("a:" + moon["account"]["id"],))
      and not acc.store.one("SELECT 1 AS x FROM fr_links WHERE a=?", ("a:" + moon["account"]["id"],)))

step(91 * 86400)
r = acc.tidy()
check("tidy: removed comments go after 90 days", not acc.store.one("SELECT 1 AS x FROM cm_comments WHERE id=?", (spam["id"],))
      and r["comments"]["comments"] >= 1, r)
check("tidy: held comments nobody reviewed go after 30 days", not acc.store.one("SELECT 1 AS x FROM cm_comments WHERE state='held'"))

# ------------------------------------------------------------------ HTTP
os.environ["TCP_ACCOUNTS_DEV"] = "1"
A.now = __import__("time").time
cfg = {"data_dir": str(tmp / "http"), "dev_login": True, "internal_token": "tok-internal", "comments_token": "tok-comments",
       "public_url": "http://127.0.0.1:0", "comments": {"site_root": str(site)}}
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


st, out, _ = req("GET", "/api/account/comments?post=" + P)
check("http: anyone can read", st == 200 and out["viewer"] == {"signedIn": False} and out["open"] is True)
check("http: unknown post 404", req("GET", "/api/account/comments?post=nope")[0] == 404)
st, out, r = req("GET", "/api/account/dev?id=77&name=Web")
ck = (r.getheader("Set-Cookie") or "").split(";")[0]
st, me, _ = req("GET", "/api/account/me", cookie=ck)
csrf = me["csrf"]
req("POST", "/api/account/signup", {"name": "Webby", "age13": True, "visibility": "hidden"}, ck, {"X-CSRF": csrf})
st, out, _ = req("POST", "/api/account/comments/post", {"post": P, "text": "hello from http"}, ck)
check("http: post without CSRF refused", st == 403)
st, out, _ = req("POST", "/api/account/comments/post", {"post": P, "text": "hello from http"}, ck,
                 {"X-CSRF": csrf, "Origin": "https://evil.example"})
check("http: cross-site post refused", st == 403)
st, out, _ = req("POST", "/api/account/comments/post", {"post": P, "text": "hello from http"}, ck, {"X-CSRF": csrf})
check("http: post works (held: web-only account)", st == 200 and out["held"] is True, out)
st, lst, _ = req("GET", "/api/account/comments?post=" + P, cookie=ck)
check("http: author sees the held comment, viewer block has csrf", lst["comments"][0].get("held") and lst["viewer"]["csrf"] == csrf)
check("http: hidden-profile account shows no profile link", lst["comments"][0]["profile"] is False)
st, out, _ = req("GET", "/api/account/comments/counts.json")
check("http: counts.json is public and cacheable", st == 200 and out == {})
st, out, _ = req("GET", "/internal/comments/stats", headers={"X-Accounts-Token": "tok-comments"})
check("http: the portal's comments token reaches /internal/comments", st == 200 and out["held"] == 1)
st, out, _ = req("GET", "/internal/lookup?name=Webby", headers={"X-Accounts-Token": "tok-comments"})
check("http: but nothing else under /internal", st == 404)
st, out, _ = req("GET", "/internal/comments/stats", headers={"X-Accounts-Token": "tok-internal"})
check("http: the internal token works too", st == 200)
st, out, _ = req("GET", "/internal/comments/stats", headers={"X-Accounts-Token": "nope"})
check("http: wrong token 404", st == 404)
st, out, _ = req("GET", "/internal/comments/stats", headers={"X-Accounts-Token": "tok-comments", "X-Forwarded-For": "8.8.8.8"})
check("http: internal routes are loopback-only (proxied requests refused)", st == 404)
cid = lst["comments"][0]["id"]
st, out, _ = req("POST", "/internal/comments/act", {"id": cid, "action": "publish", "by": "Mod"}, headers={"X-Accounts-Token": "tok-comments"})
check("http: staff publish", st == 200 and out["comment"]["state"] == "live")
st, out, _ = req("POST", "/api/account/comments/delete", {"id": cid}, ck, {"X-CSRF": csrf})
check("http: delete own", st == 200 and req("GET", "/api/account/comments?post=" + P)[1]["count"] == 0)
st, out, r = req("GET", "/api/account/login?next=/devlog-inside-0372.html")
cookies = r.getheaders()
check("http: login remembers a devlog post to return to",
      any(k == "Set-Cookie" and v.startswith("tcpacct_next=/devlog-inside-0372.html") for k, v in cookies))
st, out, r = req("GET", "/api/account/login?next=https://evil.example/")
check("http: login ignores any other return address",
      not any(k == "Set-Cookie" and v.startswith("tcpacct_next=") for k, v in r.getheaders()))
check("return address pattern", A.RETURN_TO.fullmatch("/nl/devlog-inside-0372") and A.RETURN_TO.fullmatch("/devlog-a-b.html")
      and not A.RETURN_TO.fullmatch("//evil.example/devlog-x") and not A.RETURN_TO.fullmatch("/devlog-x/../account.html"))
srv.shutdown()

failed = [n for n, ok in checks if not ok]
print("\n%d/%d checks passed" % (len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
