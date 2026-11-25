"""Friends and presence for the launcher (launcher 3.0.0). Part of the accounts service, same database.

Opt-in: nothing is stored about a PC until its player turns Friends on in the launcher. Turning it off sends
"leave", which deletes every row about that player.

Identity is the PC's key (profile\\etmain\\eacid.key), the same one the account links use. A PC linked to an
account is the account ("a:<id>"), so friends follow the player to every linked PC; any other PC is its key
("k:<kid>"). When a PC links an account later, its friends move over on the next sync.

One route, POST /api/account/friends, body:
  {public, t, action, arg, name, state, server, addr, map, show_online, show_server, requests, signature}
  t is milliseconds since 1970 and must grow from call to call (no replays); the clock may be off by 5 minutes.
  signature = Ed25519 over FRIENDS_TAG + "\\n".join(t, public, action, arg, name, state, server, addr, map,
              show_online, show_server, requests)
  action: sync | add (arg = friend code or exact name) | accept | decline | remove | invite (arg = friend id)
          | leave
          | party_invite (arg = friend id) | party_join (arg = leader id) | party_decline (arg = leader id)
          | party_leave | party_kick (arg = member id) | party_go (arg = "host:port", leader only)
Answer: {code, friends:[{id,name,state,server,map,addr,seen}], requests:[{id,name,at}],
         invites:[{id,name,server,addr}], party, party_invites:[{id,name,size}], note}
  party (0.41) is null or {tag, leader, me, members:[{id,name,state,server,addr}], target:{server,addr,at}}.
  A party is up to PARTY_MAX friends of its leader who play together: members see each other's server whatever
  show_server says (joining a party shares it), the leader's server is the target the members' launchers follow,
  and tag goes to the game as the tcp_party userinfo key so the server keeps the party on one team.
  state is "playing", "launcher" or "offline"; seen (offline only) is when they were last online, 0 if hidden.
"""
import re
import secrets
import time

FRIENDS_TAG = b"TrueCombat friends v1\n"
FRIENDS_SKEW = 300 * 1000          # ms the PC clock may be off
ONLINE_FOR = 150                   # seconds after the last sync a player still shows online (the launcher syncs every 60)
INVITE_TTL = 600
MAX_FRIENDS = 200
MAX_INCOMING = 50
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ACTIONS = ("sync", "add", "accept", "decline", "remove", "invite", "leave",
           "party_invite", "party_join", "party_decline", "party_leave", "party_kick", "party_go")
PARTY_MAX = 5
PARTY_IDLE = 600                   # a member who has not synced for 10 minutes drops out of the party
PARTY_TAG_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"

DDL = """
CREATE TABLE IF NOT EXISTS fr_people(id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  name_lower TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'launcher', server TEXT, addr TEXT, map TEXT,
  seen INTEGER NOT NULL, last_t INTEGER NOT NULL, show_online INTEGER NOT NULL DEFAULT 1,
  show_server INTEGER NOT NULL DEFAULT 1, requests INTEGER NOT NULL DEFAULT 1, created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS fr_links(a TEXT NOT NULL, b TEXT NOT NULL, created INTEGER NOT NULL, PRIMARY KEY(a, b));
CREATE TABLE IF NOT EXISTS fr_requests(src TEXT NOT NULL, dst TEXT NOT NULL, created INTEGER NOT NULL,
  declined INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(src, dst));
CREATE TABLE IF NOT EXISTS fr_invites(src TEXT NOT NULL, dst TEXT NOT NULL, server TEXT, addr TEXT,
  created INTEGER NOT NULL, PRIMARY KEY(src, dst));
CREATE TABLE IF NOT EXISTS fr_parties(id TEXT PRIMARY KEY, leader TEXT NOT NULL, target_server TEXT,
  target_addr TEXT, target_at INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS fr_party_members(person TEXT PRIMARY KEY, party TEXT NOT NULL, joined INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS fr_party_invites(party TEXT NOT NULL, src TEXT NOT NULL, dst TEXT NOT NULL,
  created INTEGER NOT NULL, PRIMARY KEY(party, dst));
CREATE INDEX IF NOT EXISTS fr_party_members_party ON fr_party_members(party);
CREATE INDEX IF NOT EXISTS fr_people_name ON fr_people(name_lower);
CREATE INDEX IF NOT EXISTS fr_requests_dst ON fr_requests(dst);
"""
TABLES = (("fr_links", ("a", "b")), ("fr_requests", ("src", "dst")), ("fr_invites", ("src", "dst")),
          ("fr_party_members", ("person",)), ("fr_party_invites", ("src", "dst")))


def message(body: dict) -> bytes:
    parts = [str(body.get(k, "")) for k in ("t", "public", "action", "arg", "name", "state", "server", "addr", "map",
                                            "show_online", "show_server", "requests")]
    return FRIENDS_TAG + "\n".join(parts).encode("utf-8")


def _flag(v) -> int:
    return 0 if str(v) in ("0", "false", "False", "") else 1


def _short(v, n: int, clean) -> str:
    return clean(str(v or ""))[:n]


def new_code(store) -> str:
    for _ in range(50):
        raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
        code = raw[:4] + "-" + raw[4:]
        if not store.one("SELECT 1 FROM fr_people WHERE code=?", (code,)):
            return code
    raise RuntimeError("no free friend code")


def norm_code(text: str) -> str:
    raw = re.sub(r"[^0-9A-Za-z]", "", text).upper()
    return raw[:4] + "-" + raw[4:] if len(raw) == 8 else ""


class Friends:
    def __init__(self, acc, error, verify, key_id, display_name, now):
        self.acc, self.Error, self.verify, self.key_id, self.clean, self.now = acc, error, verify, key_id, display_name, now
        self.store = acc.store
        self.store.db.executescript(DDL)

    # ------------------------------------------------------------ helpers
    def _person_id(self, kid: str) -> tuple[str, str | None]:
        row = self.store.one("SELECT account FROM keys WHERE kid=? AND retired IS NULL", (kid,))
        if row:
            acct = self.store.one("SELECT name FROM accounts WHERE id=?", (row["account"],))
            return "a:" + row["account"], acct["name"] if acct else None
        return "k:" + kid, None

    def _move(self, db, old: str, new: str) -> None:
        """A PC linked an account: its friends, requests and invites move to the account."""
        if not db.db.execute("SELECT 1 FROM fr_people WHERE id=?", (old,)).fetchone():
            return
        if db.db.execute("SELECT 1 FROM fr_people WHERE id=?", (new,)).fetchone():
            db.db.execute("DELETE FROM fr_people WHERE id=?", (old,))
        else:
            db.db.execute("UPDATE fr_people SET id=? WHERE id=?", (new, old))
        for table, cols in TABLES:
            for col in cols:
                db.db.execute("UPDATE OR IGNORE %s SET %s=? WHERE %s=?" % (table, col, col), (new, old))
                db.db.execute("DELETE FROM %s WHERE %s=?" % (table, col), (old,))
        db.db.execute("UPDATE fr_parties SET leader=? WHERE leader=?", (new, old))
        db.db.execute("DELETE FROM fr_links WHERE a=b")
        db.db.execute("DELETE FROM fr_requests WHERE src=dst")

    def _friends_of(self, me: str) -> set:
        return {r["b"] for r in self.store.all("SELECT b FROM fr_links WHERE a=?", (me,))}

    def _view(self, me: str, t: int) -> dict:
        out = []
        for p in self.store.all("SELECT p.* FROM fr_links l JOIN fr_people p ON p.id=l.b WHERE l.a=? ORDER BY p.name_lower",
                                (me,)):
            online = p["show_online"] and t - p["seen"] <= ONLINE_FOR and p["state"] != "offline"
            entry = {"id": p["id"][2:14], "name": p["name"], "state": p["state"] if online else "offline",
                     "server": "", "map": "", "addr": "", "seen": 0}
            if online and p["state"] == "playing" and p["show_server"]:
                entry.update(server=p["server"] or "", map=p["map"] or "", addr=p["addr"] or "")
            if not online and p["show_online"]:
                entry["seen"] = p["seen"]
            out.append(entry)
        reqs = [{"id": r["id"][2:14], "name": r["name"], "at": r["created"]} for r in self.store.all(
            "SELECT p.id, p.name, q.created FROM fr_requests q JOIN fr_people p ON p.id=q.src "
            "WHERE q.dst=? AND q.declined=0 ORDER BY q.created DESC LIMIT 20", (me,))]
        invites = [{"id": r["id"][2:14], "name": r["name"], "server": r["server"] or "", "addr": r["addr"] or ""}
                   for r in self.store.all("SELECT p.id, p.name, i.server, i.addr FROM fr_invites i JOIN fr_people p "
                                           "ON p.id=i.src WHERE i.dst=? AND i.created>=?", (me, t - INVITE_TTL))]
        self.store.x("DELETE FROM fr_invites WHERE dst=? OR created<?", (me, t - INVITE_TTL))
        code = self.store.one("SELECT code FROM fr_people WHERE id=?", (me,))
        party, party_invites = self._party_view(me, t)
        if party:      # party members see each other's server, whatever show_server says
            mates = {m["id"]: m for m in party["members"]}
            for entry in out:
                m = mates.get(entry["id"])
                if m and m["state"] == "playing" and entry["state"] == "playing" and not entry["addr"]:
                    entry.update(server=m["server"], addr=m["addr"])
        return {"code": code["code"] if code else "", "friends": out, "requests": reqs, "invites": invites,
                "party": party, "party_invites": party_invites}

    def _by_short(self, me: str, short: str, table_sql: str) -> str | None:
        if not re.fullmatch(r"[0-9a-z]{1,12}", short or ""):
            raise self.Error(400, "Bad request.")
        row = self.store.one(table_sql, (me, short + "%"))
        return row["id"] if row else None

    # ------------------------------------------------------------ parties (0.41)
    def _party_of(self, me: str) -> str | None:
        row = self.store.one("SELECT party FROM fr_party_members WHERE person=?", (me,))
        return row["party"] if row else None

    def _party_tidy(self, db, party: str) -> None:
        """After someone left: hand the lead to the longest member, or close a party nobody is left in."""
        members = [r["person"] for r in db.db.execute(
            "SELECT person FROM fr_party_members WHERE party=? ORDER BY joined, rowid", (party,)).fetchall()]
        invites = db.db.execute("SELECT COUNT(*) n FROM fr_party_invites WHERE party=?", (party,)).fetchone()["n"]
        if not members or (len(members) == 1 and not invites):
            db.db.execute("DELETE FROM fr_parties WHERE id=?", (party,))
            db.db.execute("DELETE FROM fr_party_members WHERE party=?", (party,))
            db.db.execute("DELETE FROM fr_party_invites WHERE party=?", (party,))
            return
        row = db.db.execute("SELECT leader FROM fr_parties WHERE id=?", (party,)).fetchone()
        if not row or row["leader"] not in members:
            db.db.execute("UPDATE fr_parties SET leader=? WHERE id=?", (members[0], party))

    def _party_drop(self, db, person: str) -> None:
        row = db.db.execute("SELECT party FROM fr_party_members WHERE person=?", (person,)).fetchone()
        db.db.execute("DELETE FROM fr_party_members WHERE person=?", (person,))
        db.db.execute("DELETE FROM fr_party_invites WHERE src=? OR dst=?", (person, person))
        if row:
            self._party_tidy(db, row["party"])

    def _party_expire(self, party: str, t: int) -> None:
        """Members who closed the launcher a while ago drop out, and stale invites go."""
        with self.store.tx() as db:
            for r in db.db.execute("SELECT m.person FROM fr_party_members m LEFT JOIN fr_people p ON p.id=m.person "
                                   "WHERE m.party=? AND (p.id IS NULL OR p.seen<? OR p.state='offline')",
                                   (party, t - PARTY_IDLE)).fetchall():
                db.db.execute("DELETE FROM fr_party_members WHERE person=?", (r["person"],))
            db.db.execute("DELETE FROM fr_party_invites WHERE party=? AND created<?", (party, t - INVITE_TTL))
            self._party_tidy(db, party)

    def _party_view(self, me: str, t: int) -> tuple[dict | None, list]:
        party = self._party_of(me)
        if party:
            self._party_expire(party, t)
            party = self._party_of(me)
        out = None
        if party:
            row = self.store.one("SELECT * FROM fr_parties WHERE id=?", (party,))
            members = []
            for p in self.store.all("SELECT p.id, p.name, p.state, p.server, p.addr, p.seen FROM fr_party_members m "
                                    "JOIN fr_people p ON p.id=m.person WHERE m.party=? ORDER BY m.joined, m.rowid", (party,)):
                playing = p["state"] == "playing" and t - p["seen"] <= ONLINE_FOR
                members.append({"id": p["id"][2:14], "name": p["name"], "state": "playing" if playing else "launcher",
                                "server": (p["server"] or "") if playing else "", "addr": (p["addr"] or "") if playing else ""})
            target = {"server": row["target_server"] or "", "addr": row["target_addr"] or "", "at": row["target_at"]}
            out = {"tag": party, "leader": row["leader"][2:14], "me": me[2:14], "members": members, "target": target,
                   "pending": [r["name"] for r in self.store.all(
                       "SELECT p.name FROM fr_party_invites i JOIN fr_people p ON p.id=i.dst WHERE i.party=? "
                       "AND i.created>=? ORDER BY i.created", (party, t - INVITE_TTL))]}
        invites = [{"id": r["id"][2:14], "name": r["name"], "size": r["size"]} for r in self.store.all(
            "SELECT p.id, p.name, (SELECT COUNT(*) FROM fr_party_members m WHERE m.party=i.party) size "
            "FROM fr_party_invites i JOIN fr_people p ON p.id=i.src WHERE i.dst=? AND i.created>=? "
            "ORDER BY i.created DESC LIMIT 5", (me, t - INVITE_TTL))]
        return out, invites

    def _party_action(self, me: str, action: str, arg: str, t: int, state: str, server: str, addr: str) -> str:
        Error = self.Error
        party = self._party_of(me)
        if action == "party_invite":
            other = self._by_short(me, arg, "SELECT b id FROM fr_links WHERE a=? AND substr(b,3) LIKE ?")
            if not other:
                raise Error(404, "You can only invite friends to your party.")
            if self.acc.limited("friends-party:" + me, 40, 3600):
                raise Error(429, "That is a lot of party invites. Try again later.")
            with self.store.tx() as db:
                if not party:
                    party = "".join(secrets.choice(PARTY_TAG_ALPHABET) for _ in range(8))
                    db.db.execute("INSERT INTO fr_parties(id, leader, target_server, target_addr, target_at, created) "
                                  "VALUES(?,?,?,?,?,?)", (party, me, server if state == "playing" else "",
                                                          addr if state == "playing" else "", t if addr else 0, t))
                    db.db.execute("INSERT INTO fr_party_members(person, party, joined) VALUES(?,?,?)", (me, party, t))
                if db.db.execute("SELECT 1 FROM fr_party_members WHERE party=? AND person=?", (party, other)).fetchone():
                    return "party_already"
                size = db.db.execute("SELECT COUNT(*) n FROM fr_party_members WHERE party=?", (party,)).fetchone()["n"]
                if size >= PARTY_MAX:
                    raise Error(409, "Your party is full.")
                db.db.execute("INSERT OR REPLACE INTO fr_party_invites(party, src, dst, created) VALUES(?,?,?,?)",
                              (party, me, other, t))
            return "party_invited"
        if action in ("party_join", "party_decline"):
            src = self._by_short(me, arg, "SELECT src id FROM fr_party_invites WHERE dst=? AND substr(src,3) LIKE ?")
            inv = self.store.one("SELECT party, created FROM fr_party_invites WHERE dst=? AND src=?", (me, src)) if src else None
            if not inv or inv["created"] < t - INVITE_TTL:
                raise Error(404, "This party invite is no longer open.")
            with self.store.tx() as db:
                db.db.execute("DELETE FROM fr_party_invites WHERE party=? AND dst=?", (inv["party"], me))
                if action == "party_decline":
                    self._party_tidy(db, inv["party"])
                    return "party_declined"
                if not db.db.execute("SELECT 1 FROM fr_parties WHERE id=?", (inv["party"],)).fetchone():
                    raise Error(404, "This party has closed.")
                size = db.db.execute("SELECT COUNT(*) n FROM fr_party_members WHERE party=?", (inv["party"],)).fetchone()["n"]
                if size >= PARTY_MAX:
                    raise Error(409, "This party is full.")
                if party and party != inv["party"]:
                    self._party_drop(db, me)                      # one party at a time: joining leaves the old one
                db.db.execute("INSERT OR REPLACE INTO fr_party_members(person, party, joined) VALUES(?,?,?)",
                              (me, inv["party"], t))
            return "party_joined"
        if not party:
            raise Error(409, "You are not in a party.")
        leader = self.store.one("SELECT leader FROM fr_parties WHERE id=?", (party,))["leader"]
        if action == "party_leave":
            with self.store.tx() as db:
                self._party_drop(db, me)
            return "party_left"
        if me != leader:
            raise Error(403, "Only the party leader can do that.")
        if action == "party_kick":
            other = self._by_short(party, arg, "SELECT person id FROM fr_party_members WHERE party=? AND substr(person,3) LIKE ?")
            if not other or other == me:
                raise Error(404, "That player is not in your party.")
            with self.store.tx() as db:
                self._party_drop(db, other)
            return "party_kicked"
        # party_go: the leader picked a server (Quick Play or the browser) before joining it
        if not re.fullmatch(r"[0-9A-Za-z.:\-\[\]]{3,64}", arg):
            raise Error(400, "Bad request.")
        self.store.x("UPDATE fr_parties SET target_addr=?, target_server=?, target_at=? WHERE id=?",
                     (arg, server if addr == arg else "", t, party))
        return "party_go"

    # ------------------------------------------------------------ the route
    def call(self, body: dict, ip: str) -> dict:
        Error = self.Error
        if self.acc.limited("friends-ip:" + ip, 240, 3600):
            raise Error(429, "Too many requests. Try again later.")
        public_hex = str(body.get("public", "")).lower()
        sig_hex = str(body.get("signature", "")).lower()
        action = str(body.get("action", ""))
        stamp = str(body.get("t", ""))
        if (not re.fullmatch(r"[0-9a-f]{64}", public_hex) or not re.fullmatch(r"[0-9a-f]{128}", sig_hex)
                or not re.fullmatch(r"[0-9]{12,14}", stamp) or action not in ACTIONS):
            raise Error(400, "Bad request.")
        for k in ("arg", "name", "server", "addr", "map"):
            if len(str(body.get(k, ""))) > 120:
                raise Error(400, "Bad request.")
        t_ms = int(stamp)
        if abs(time.time() * 1000 - t_ms) > FRIENDS_SKEW:
            raise Error(400, "Your PC's clock is off. Set it to the right time and try again.")
        public = bytes.fromhex(public_hex)
        if not self.verify(public, message(body), bytes.fromhex(sig_hex)):
            raise Error(401, "The signature does not match this key.")
        kid = self.key_id(public)
        if self.acc.ban_of(kid=kid):
            raise Error(403, "Friends are not available for this PC.")
        me, account_name = self._person_id(kid)
        if self.acc.limited("friends:" + me, 30, 60):
            raise Error(429, "Too many requests. Try again in a minute.")
        t = self.now()
        name = account_name or _short(body.get("name"), 24, self.clean) or "Player"
        state = str(body.get("state", ""))
        state = state if state in ("playing", "launcher") else "launcher"
        server = _short(body.get("server"), 64, self.clean)
        addr = str(body.get("addr", ""))[:64]
        if addr and not re.fullmatch(r"[0-9A-Za-z.:\-\[\]]{3,64}", addr):
            addr = ""
        mapname = _short(body.get("map"), 32, self.clean)
        flags = (_flag(body.get("show_online", 1)), _flag(body.get("show_server", 1)), _flag(body.get("requests", 1)))
        note = ""

        if action == "leave":
            with self.store.tx() as db:
                for old in {me, "k:" + kid}:
                    db.db.execute("DELETE FROM fr_people WHERE id=?", (old,))
                    self._party_drop(db, old)
                    for table, cols in TABLES:
                        for col in cols:
                            db.db.execute("DELETE FROM %s WHERE %s=?" % (table, col), (old,))
            return {"code": "", "friends": [], "requests": [], "invites": [], "party": None, "party_invites": [],
                    "note": "left"}

        with self.store.tx() as db:
            if me.startswith("a:"):
                self._move(db, "k:" + kid, me)
            row = db.db.execute("SELECT last_t FROM fr_people WHERE id=?", (me,)).fetchone()
            if row and t_ms <= row["last_t"]:
                raise Error(409, "This request was already used.")
            if row:
                db.db.execute("UPDATE fr_people SET name=?, name_lower=?, state=?, server=?, addr=?, map=?, seen=?, "
                              "last_t=?, show_online=?, show_server=?, requests=? WHERE id=?",
                              (name, name.lower(), state, server, addr, mapname, t, t_ms, *flags, me))
            else:
                db.db.execute("INSERT INTO fr_people(id, code, name, name_lower, state, server, addr, map, seen, last_t, "
                              "show_online, show_server, requests, created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (me, new_code(self.store), name, name.lower(), state, server, addr, mapname, t, t_ms,
                               *flags, t))

        arg = str(body.get("arg", "")).strip()
        party = self._party_of(me)
        if party and state == "playing" and addr:      # the leader's server is where the party goes
            self.store.x("UPDATE fr_parties SET target_addr=?, target_server=?, target_at=? WHERE id=? AND leader=? "
                         "AND (target_addr IS NULL OR target_addr<>?)", (addr, server, t, party, me, addr))
        if action.startswith("party_"):
            note = self._party_action(me, action, arg, t, state, server, addr)
        elif action == "add":
            if self.acc.limited("friends-add:" + me, 20, 3600):
                raise Error(429, "That is a lot of requests. Try again later.")
            code = norm_code(arg)
            target = self.store.one("SELECT id, requests FROM fr_people WHERE code=?", (code,)) if code else None
            if not target and arg and not code:
                hits = self.store.all("SELECT id, requests FROM fr_people WHERE name_lower=? LIMIT 2",
                                      (self.clean(arg).lower(),))
                if len(hits) > 1:
                    raise Error(409, "More than one player has that name. Ask for their friend code.")
                target = hits[0] if hits else None
            if not target or target["id"] == me:
                raise Error(404, "No player with that friend code or name has Friends turned on.")
            if target["id"] in self._friends_of(me):
                note = "already"
            elif not target["requests"]:
                raise Error(403, "This player is not taking friend requests.")
            elif self.store.one("SELECT 1 FROM fr_requests WHERE src=? AND dst=? AND declined=0", (target["id"], me)):
                self._link(me, target["id"], t)                      # they asked first: now friends
                note = "friends"
            else:
                if len(self._friends_of(me)) >= MAX_FRIENDS:
                    raise Error(409, "Your friends list is full.")
                if (self.store.one("SELECT COUNT(*) n FROM fr_requests WHERE dst=? AND declined=0", (target["id"],))["n"]
                        >= MAX_INCOMING):
                    raise Error(409, "This player has too many open requests.")
                self.store.x("INSERT OR IGNORE INTO fr_requests(src, dst, created) VALUES(?,?,?)", (me, target["id"], t))
                note = "sent"                                         # a declined request stays quietly declined
        elif action in ("accept", "decline"):
            src = self._by_short(me, arg, "SELECT src id FROM fr_requests WHERE dst=? AND substr(src,3) LIKE ? AND declined=0")
            if not src:
                raise Error(404, "This request is no longer open.")
            if action == "accept":
                if len(self._friends_of(me)) >= MAX_FRIENDS:
                    raise Error(409, "Your friends list is full.")
                self._link(me, src, t)
                note = "friends"
            else:
                self.store.x("UPDATE fr_requests SET declined=1 WHERE src=? AND dst=?", (src, me))
                note = "declined"
        elif action == "remove":
            other = self._by_short(me, arg, "SELECT b id FROM fr_links WHERE a=? AND substr(b,3) LIKE ?")
            if other:
                with self.store.tx() as db:
                    db.db.execute("DELETE FROM fr_links WHERE (a=? AND b=?) OR (a=? AND b=?)", (me, other, other, me))
                    db.db.execute("DELETE FROM fr_invites WHERE (src=? AND dst=?) OR (src=? AND dst=?)",
                                  (me, other, other, me))
            note = "removed"
        elif action == "invite":
            other = self._by_short(me, arg, "SELECT b id FROM fr_links WHERE a=? AND substr(b,3) LIKE ?")
            if not other:
                raise Error(404, "You can only invite friends.")
            if state != "playing" or not addr:
                raise Error(409, "Join a server first, then invite.")
            if self.acc.limited("friends-invite:" + me, 30, 3600):
                raise Error(429, "That is a lot of invites. Try again later.")
            self.store.x("INSERT OR REPLACE INTO fr_invites(src, dst, server, addr, created) VALUES(?,?,?,?,?)",
                         (me, other, server, addr, t))
            note = "invited"
        out = self._view(me, t)
        out["note"] = note
        return out

    def _link(self, a: str, b: str, t: int) -> None:
        with self.store.tx() as db:
            db.db.execute("INSERT OR IGNORE INTO fr_links(a, b, created) VALUES(?,?,?)", (a, b, t))
            db.db.execute("INSERT OR IGNORE INTO fr_links(a, b, created) VALUES(?,?,?)", (b, a, t))
            db.db.execute("DELETE FROM fr_requests WHERE (src=? AND dst=?) OR (src=? AND dst=?)", (a, b, b, a))

    def purge(self, days: int = 365) -> None:
        """People who have not opened the launcher for a year leave on their own."""
        old = self.now() - days * 86400
        for r in self.store.all("SELECT id FROM fr_people WHERE seen<?", (old,)):
            self.forget(r["id"])

    def forget(self, person: str) -> None:
        """Every row about one person ("a:<account id>" or "k:<key id>"): an idle purge, or a deleted account."""
        with self.store.tx() as db:
            self._party_drop(db, person)
            db.db.execute("DELETE FROM fr_people WHERE id=?", (person,))
            for table, cols in TABLES:
                for col in cols:
                    db.db.execute("DELETE FROM %s WHERE %s=?" % (table, col), (person,))
