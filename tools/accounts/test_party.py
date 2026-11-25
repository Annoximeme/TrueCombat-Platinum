#!/usr/bin/env python3
"""Parties (accounts 1.3.0, launcher 3.3.0, game 0.41).  python3 test_party.py
Needs the 'cryptography' package to sign as the launcher (test only)."""
import sqlite3
import sys
import tempfile

import test_friends as T
from test_friends import A, F, PC, check, checks


def befriend(a, b):
    code = a.call()["code"]
    b.call("add", code)
    rid = [r["id"] for r in a.call()["requests"] if r["name"] == b.name][0]
    a.call("accept", rid)


_call = PC.call


def _fresh_call(self, *a, **k):
    self.acc.rate.clear()          # these tests make far more calls a minute than a launcher would
    return _call(self, *a, **k)


PC.call = _fresh_call


def fid(pc, name):
    return [f["id"] for f in pc.call()["friends"] if f["name"] == name][0]


def main():
    acc = A.Accounts({"data_dir": tempfile.mkdtemp()})
    lead, m1, m2, m3, m4, m5, stranger = (PC(acc, n) for n in ("Lead", "Ash", "Birch", "Cedar", "Dune", "Elm", "Stray"))
    for pc in (m1, m2, m3, m4, m5, stranger):
        pc.call()
    for pc in (m1, m2, m3, m4, m5):
        befriend(lead, pc)
    r = lead.call()
    check("no party at first", r["party"] is None and r["party_invites"] == [])
    r = lead.call("party_invite", "zzzz")
    check("only friends can be invited", r.get("status") == 404)
    r = lead.call("party_invite", fid(lead, "Ash"))
    check("first invite opens a party", r.get("note") == "party_invited" and r["party"]["leader"] == r["party"]["me"]
          and len(r["party"]["members"]) == 1 and r["party"]["pending"] == ["Ash"] and len(r["party"]["tag"]) == 8)
    tag = r["party"]["tag"]
    a = m1.call()
    check("invite arrives", len(a["party_invites"]) == 1 and a["party_invites"][0]["name"] == "Lead"
          and a["party_invites"][0]["size"] == 1)
    a = m1.call("party_join", a["party_invites"][0]["id"])
    check("join puts both in one party", a.get("note") == "party_joined" and a["party"]["tag"] == tag
          and [m["name"] for m in a["party"]["members"]] == ["Lead", "Ash"])
    r = m1.call("party_go", "1.2.3.4:27960")
    check("only the leader sends the party somewhere", r.get("status") == 403)
    r = m1.call("party_kick", fid(m1, "Lead"))
    check("only the leader kicks", r.get("status") == 403)
    # leader joins a server: the party follows
    lead.state, lead.server, lead.addr, lead.map = "playing", "Official #2", "2.24.59.195:27961", "obj_village"
    lead.flags["show_server"] = 0
    lead.call()
    a = m1.call()
    check("leader's server becomes the target", a["party"]["target"]["addr"] == "2.24.59.195:27961"
          and a["party"]["target"]["server"] == "Official #2" and a["party"]["target"]["at"] > 0)
    f = [f for f in a["friends"] if f["name"] == "Lead"][0]
    check("party members see the server even when it is hidden from friends", f["addr"] == "2.24.59.195:27961")
    s = stranger.call()
    check("strangers see nothing", s["party"] is None)
    r = lead.call("party_go", "9.9.9.9:27960")
    check("party_go sets the target", r.get("note") == "party_go" and r["party"]["target"]["addr"] == "9.9.9.9:27960")
    r = lead.call("party_go", "bad addr;rm")
    check("party_go checks the address", r.get("status") == 400)
    # fill up to five
    for pc in (m2, m3, m4):
        lead.call("party_invite", fid(lead, pc.name))
        inv = pc.call()["party_invites"]
        pc.call("party_join", inv[0]["id"])
    r = lead.call()
    check("party of five", len(r["party"]["members"]) == 5)
    r = lead.call("party_invite", fid(lead, "Elm"))
    check("a sixth cannot be invited", r.get("status") == 409)
    r = lead.call("party_kick", fid(lead, "Dune"))
    check("leader kicks", r.get("note") == "party_kicked" and len(r["party"]["members"]) == 4)
    check("kicked player is out", m4.call()["party"] is None)
    # decline
    lead.call("party_invite", fid(lead, "Elm"))
    e = m5.call()
    r = m5.call("party_decline", e["party_invites"][0]["id"])
    check("decline", r.get("note") == "party_declined" and r["party"] is None and m5.call()["party_invites"] == [])
    r = m5.call("party_join", e["party_invites"][0]["id"])
    check("a declined invite cannot be used", r.get("status") == 404)
    # leader leaves: the lead moves on
    r = lead.call("party_leave")
    check("leader leaves", r.get("note") == "party_left" and r["party"] is None)
    a = m1.call()
    check("longest member leads now", a["party"]["leader"] == a["party"]["me"] and len(a["party"]["members"]) == 3)
    # one party at a time
    lead.state = "launcher"
    lead.call("party_invite", fid(lead, "Birch"))
    b = m2.call()
    b = m2.call("party_join", [i for i in b["party_invites"] if i["name"] == "Lead"][0]["id"])
    check("joining another party leaves the old one", b["party"]["leader"] != b["party"]["me"]
          and [m["name"] for m in b["party"]["members"]] == ["Lead", "Birch"])
    check("old party shrank", len(m1.call()["party"]["members"]) == 2)
    # idle members drop out
    db = acc.store.db
    db.execute("UPDATE fr_people SET seen=seen-3600 WHERE name='Cedar'")
    db.commit()
    a = m1.call()
    check("idle member drops out; a party of one closes", a["party"] is None)
    # turning Friends off removes party rows
    m2.call("leave")
    r = lead.call()
    check("Friends off leaves the party (and it closes)", r["party"] is None)
    left = db.execute("SELECT COUNT(*) FROM fr_party_members WHERE person LIKE 'k:%'").fetchone()[0]
    check("no orphan party rows", db.execute("SELECT COUNT(*) FROM fr_parties").fetchone()[0] == 0 and left == 0)
    failed = [n for n, ok in checks if not ok]
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
