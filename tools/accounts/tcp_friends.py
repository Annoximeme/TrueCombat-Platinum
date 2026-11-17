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
Answer: {code, friends:[{id,name,state,server,map,addr,seen}], requests:[{id,name,at}],
         invites:[{id,name,server,addr}], note}
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
ACTIONS = ("sync", "add", "accept", "decline", "remove", "invite", "leave")

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
CREATE INDEX IF NOT EXISTS fr_people_name ON fr_people(name_lower);
CREATE INDEX IF NOT EXISTS fr_requests_dst ON fr_requests(dst);
"""


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
        for table, cols in (("fr_links", ("a", "b")), ("fr_requests", ("src", "dst")), ("fr_invites", ("src", "dst"))):
            for col in cols:
                db.db.execute("UPDATE OR IGNORE %s SET %s=? WHERE %s=?" % (table, col, col), (new, old))
                db.db.execute("DELETE FROM %s WHERE %s=?" % (table, col), (old,))
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
        return {"code": code["code"] if code else "", "friends": out, "requests": reqs, "invites": invites}

    def _by_short(self, me: str, short: str, table_sql: str) -> str | None:
        if not re.fullmatch(r"[0-9a-z]{1,12}", short or ""):
            raise self.Error(400, "Bad request.")
        row = self.store.one(table_sql, (me, short + "%"))
        return row["id"] if row else None

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
                    for table, cols in (("fr_links", ("a", "b")), ("fr_requests", ("src", "dst")),
                                        ("fr_invites", ("src", "dst"))):
                        for col in cols:
                            db.db.execute("DELETE FROM %s WHERE %s=?" % (table, col), (old,))
            return {"code": "", "friends": [], "requests": [], "invites": [], "note": "left"}

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
        if action == "add":
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
            db.db.execute("DELETE FROM fr_people WHERE id=?", (person,))
            for table, cols in (("fr_links", ("a", "b")), ("fr_requests", ("src", "dst")), ("fr_invites", ("src", "dst"))):
                for col in cols:
                    db.db.execute("DELETE FROM %s WHERE %s=?" % (table, col), (person,))
