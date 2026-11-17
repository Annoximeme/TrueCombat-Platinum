"""Devlog comments: players with an account comment under devlog posts on truecombat.eu. Part of the accounts
service, same database, same sign-in cookie, CSRF token and bans.

Reading is open to everyone. Posting needs an account. One conversation per post (the slug), shared by every
language of the site. Plain text only: the page escapes it and never turns a link into a link.

Public routes (under /api/account/):
  GET  comments?post=<slug>&sort=new|old|top    the post's comments, plus what the viewer may do ("viewer")
  GET  comments/counts.json                     slug -> number of visible comments (devlog cards)
  POST comments/post   {post, text, parent?}    new comment or reply (replies are one level deep)
  POST comments/edit   {id, text}               own comment, within EDIT_MINUTES
  POST comments/delete {id}                     own comment, any time
  POST comments/like   {id, on}
  POST comments/report {id, reason, note?}      reason: spam | abuse | cheats | other

Loopback routes for the staff portal (X-Accounts-Token: the internal token or the comments token):
  GET  /internal/comments/stats
  GET  /internal/comments/queue?tab=needs|recent|hidden|paused&post=&q=
  POST /internal/comments/act     {id, action: publish|hide|restore|remove|pin|unpin|dismiss, by}
  POST /internal/comments/pause   {account|name, days (0 = for good), reason, by}
  POST /internal/comments/unpause {account, by}
  POST /internal/comments/close   {post, closed, by}
  POST /internal/comments/reply   {parent, text, discord, by}   a staff member answers as themselves (team tag)

States: live; held (waits for staff: first comment of an account with no linked PC, a word-filter hit, a link from
an account with no linked PC); hidden (3 reports from different players, or staff; can be restored); removed (staff
took it down: text kept REMOVED_KEEP_DAYS as evidence, staff only); deleted (the author or their account went: no
text, no author, kept only while it has replies to hold together).
"""
import re
import time
import unicodedata
from pathlib import Path

MIN_LEN, MAX_LEN = 2, 1000
EDIT_MINUTES = 15
REPORTS_TO_HIDE = 3
REMOVED_KEEP_DAYS = 90            # staff-removed comments: evidence for appeals, then gone
REPORT_KEEP_DAYS = 90             # closed reports
HELD_KEEP_DAYS = 30               # a held comment nobody looked at for a month is dropped
MAX_TOP_LEVEL = 400               # per post, newest first: far more than any devlog post will see
REASONS = ("spam", "abuse", "cheats", "other")
SORTS = ("new", "old", "top")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
# A link: a scheme, www., or a dotted name ending in a known top-level domain shape.
LINK = re.compile(r"(?i)(?:[a-z][a-z0-9+.-]*://|www\.|\b[a-z0-9-]{2,}\.(?:com|net|org|eu|io|gg|ru|cn|xyz|ly|me|co|be|nl|de|"
                  r"fr|pl|uk|info|biz|shop|store|link|click|top|site|online|tk|to|cc)\b|discord\.gg/|t\.me/)")

DDL = """
CREATE TABLE IF NOT EXISTS cm_comments(id INTEGER PRIMARY KEY, post TEXT NOT NULL, parent INTEGER, account TEXT,
  text TEXT NOT NULL, created INTEGER NOT NULL, edited INTEGER, state TEXT NOT NULL DEFAULT 'live', reason TEXT,
  moderated INTEGER, moderated_by TEXT, pinned INTEGER NOT NULL DEFAULT 0, likes INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS cm_likes(comment INTEGER NOT NULL, account TEXT NOT NULL, created INTEGER NOT NULL,
  PRIMARY KEY(comment, account));
CREATE TABLE IF NOT EXISTS cm_reports(id INTEGER PRIMARY KEY, comment INTEGER NOT NULL, account TEXT NOT NULL,
  reason TEXT NOT NULL, note TEXT, created INTEGER NOT NULL, closed INTEGER, outcome TEXT, UNIQUE(comment, account));
CREATE TABLE IF NOT EXISTS cm_pauses(account TEXT PRIMARY KEY, until INTEGER, reason TEXT, by_whom TEXT,
  created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cm_trust(account TEXT PRIMARY KEY, since INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cm_posts(post TEXT PRIMARY KEY, closed INTEGER, by_whom TEXT);
CREATE INDEX IF NOT EXISTS cm_comments_post ON cm_comments(post, state);
CREATE INDEX IF NOT EXISTS cm_comments_account ON cm_comments(account);
CREATE INDEX IF NOT EXISTS cm_comments_parent ON cm_comments(parent);
CREATE INDEX IF NOT EXISTS cm_reports_comment ON cm_reports(comment);
"""


def clean_text(raw) -> str:
    """Printable text with line breaks kept: no control characters, no runs of blank lines, trimmed."""
    text = unicodedata.normalize("NFC", str(raw or "")).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch for ch in text if ch == "\n" or (ch.isprintable() and unicodedata.category(ch) not in ("Cf", "Co", "Cs")))
    text = "\n".join(re.sub(r"[ \t ]+", " ", line).strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def has_link(text: str) -> bool:
    return bool(LINK.search(text))


class Comments:
    def __init__(self, acc, error, note_problem, account_pid, now):
        self.acc, self.Error, self.note_problem, self.account_pid, self.now = acc, error, note_problem, account_pid, now
        self.store = acc.store
        self.store.db.executescript(DDL)
        self._pages = {}              # slug -> (checked at, open?) when the site's files are on this machine

    # ------------------------------------------------------------ settings and small helpers
    @property
    def cfg(self) -> dict:
        c = self.acc.cfg.get("comments")
        return c if isinstance(c, dict) else {}

    def words(self) -> list:
        """Extra filter words (config comments.words; the portal's chat filter list can be copied here)."""
        return [str(w).lower() for w in (self.cfg.get("words") or []) if str(w).strip()][:2000]

    def filtered(self, text: str) -> bool:
        if self.note_problem(text):
            return True
        low = text.lower()
        for w in self.words():
            if (len(w) >= 5 and w in low) or re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", low):
                return True
        return False

    def post_state(self, slug: str) -> str:
        """'open', 'closed' or 'missing'. With comments.site_root set, a post exists only when its page does and the
        page says comments are on (build.py writes data-comments="on"; front matter `comments: off` turns it off)."""
        if not SLUG.fullmatch(slug or ""):
            return "missing"
        row = self.store.one("SELECT closed FROM cm_posts WHERE post=?", (slug,))
        root = self.cfg.get("site_root")
        if root:
            t = time.time()
            hit = self._pages.get(slug)
            if not hit or t - hit[0] > 300:
                page = Path(root) / ("devlog-%s.html" % slug)
                try:
                    html = page.read_text(encoding="utf-8", errors="replace") if page.is_file() else None
                except OSError:
                    html = None
                hit = (t, None if html is None else ('data-comments="on"' in html))
                self._pages[slug] = hit
                if len(self._pages) > 2000:
                    self._pages = {k: v for k, v in self._pages.items() if t - v[0] < 300}
            if hit[1] is None:
                return "missing"
            if not hit[1]:
                return "closed"
        return "closed" if row and row["closed"] else "open"

    def paused(self, acct_id: str):
        """None, or the pause row (until NULL = for good)."""
        row = self.store.one("SELECT * FROM cm_pauses WHERE account=?", (acct_id,))
        if row and row["until"] is not None and row["until"] <= self.now():
            self.store.x("DELETE FROM cm_pauses WHERE account=?", (acct_id,))
            return None
        return row

    def has_pc(self, acct_id: str) -> bool:
        return bool(self.store.one("SELECT 1 AS x FROM keys WHERE account=? AND retired IS NULL", (acct_id,)))

    def trusted(self, acct_id: str) -> bool:
        return bool(self.store.one("SELECT 1 AS x FROM cm_trust WHERE account=?", (acct_id,)))

    def _comment(self, cid) -> dict:
        try:
            cid = int(cid)
        except (TypeError, ValueError):
            raise self.Error(400, "Which comment?") from None
        row = self.store.one("SELECT * FROM cm_comments WHERE id=?", (cid,))
        if not row:
            raise self.Error(404, "That comment is gone.")
        return row

    def _can_write(self, acct: dict) -> None:
        if self.acc.ban_of(account=acct["id"]):
            raise self.Error(403, "Your account is suspended.")
        p = self.paused(acct["id"])
        if p:
            raise self.Error(403, "Your comments are paused %s." % (
                "until further notice" if p["until"] is None else time.strftime("until %d %b %Y", time.gmtime(p["until"]))))

    def _text(self, raw) -> str:
        text = clean_text(raw)
        if len(text) < MIN_LEN:
            raise self.Error(400, "Write a little more.")
        if len(text) > MAX_LEN:
            raise self.Error(400, "Keep it under %d characters." % MAX_LEN)
        return text

    def _hold_reason(self, acct: dict, text: str):
        """None to publish straight away, else why it waits for staff."""
        if self.acc.team_role(acct):
            return None
        if self.filtered(text):
            return "filter"
        pc = self.has_pc(acct["id"])
        if has_link(text) and not pc:
            return "link"
        if not pc and not self.trusted(acct["id"]):
            return "new"
        return None

    # ------------------------------------------------------------ what everyone reads
    def _author(self, cache: dict, acct_id) -> dict | None:
        if acct_id in cache:
            return cache[acct_id]
        a = self.acc.account(acct_id) if acct_id else None
        out = None
        if a and not self.acc.ban_of(account=a["id"]):
            out = {"name": a["name"], "profile": a["visibility"] == "public", "team": bool(self.acc.team_role(a)),
                   "clean": "clean" in self.acc.badges(a)}
        cache[acct_id] = out
        return out

    def _item(self, c: dict, cache: dict, me: str | None, liked: set) -> dict | None:
        """One comment as the page shows it, or None when the viewer should not see it at all."""
        author = self._author(cache, c["account"])
        mine = bool(me and c["account"] == me)
        state = c["state"]
        if state == "live" and author:
            item = {"id": c["id"], "name": author["name"], "profile": author["profile"], "team": author["team"],
                    "clean": author["clean"], "text": c["text"], "at": c["created"], "edited": c["edited"],
                    "likes": c["likes"], "pinned": bool(c["pinned"])}
        elif state == "held" and mine and author:
            item = {"id": c["id"], "name": author["name"], "profile": author["profile"], "team": author["team"],
                    "clean": author["clean"], "text": c["text"], "at": c["created"], "edited": c["edited"],
                    "likes": 0, "pinned": False, "held": True}
        else:
            # gone for the viewer: a placeholder only where replies hang under it (decided by the caller)
            gone = "removed" if state in ("removed",) else "hidden" if state in ("hidden", "held") else "deleted"
            if state == "live" and not author:            # the author is banned: hidden like their profile
                gone = "hidden"
            return {"id": c["id"], "gone": gone, "at": c["created"]}
        if mine:
            item["mine"] = True
            item["editable"] = self.now() - c["created"] <= EDIT_MINUTES * 60 and state in ("live", "held")
        if c["id"] in liked:
            item["liked"] = True
        return item

    def listing(self, slug: str, sort: str, viewer: dict | None) -> dict:
        state = self.post_state(slug)
        if state == "missing":
            raise self.Error(404, "No such post.")
        sort = sort if sort in SORTS else "new"
        me = viewer["account"]["id"] if viewer and viewer.get("account") else None
        rows = self.store.all("SELECT * FROM cm_comments WHERE post=? ORDER BY created DESC, id DESC", (slug,))
        liked = set()
        if me and rows:
            liked = {r["comment"] for r in self.store.all(
                "SELECT l.comment FROM cm_likes l JOIN cm_comments c ON c.id=l.comment WHERE l.account=? AND c.post=?", (me, slug))}
        cache = {}
        replies = {}
        for r in rows:
            if r["parent"]:
                item = self._item(r, cache, me, liked)
                if item and "gone" not in item:
                    replies.setdefault(r["parent"], []).append(item)
        top = []
        for r in rows:
            if r["parent"]:
                continue
            item = self._item(r, cache, me, liked)
            kids = sorted(replies.get(r["id"], []), key=lambda x: (x["at"], x["id"]))
            if "gone" in item and not kids:
                continue
            item["replies"] = kids
            top.append(item)
        if sort == "old":
            top.sort(key=lambda x: (x["at"], x["id"]))
        elif sort == "top":
            top.sort(key=lambda x: (-(x.get("likes") or 0), -x["at"]))
        top.sort(key=lambda x: not x.get("pinned"))          # the pinned comment leads, the rest keep their order
        top = top[:MAX_TOP_LEVEL]
        count = sum(1 for x in top if "gone" not in x and not x.get("held")) + sum(
            1 for x in top for k in x["replies"] if not k.get("held"))
        return {"schema": "tcp-comments/1", "post": slug, "open": state == "open", "count": count, "sort": sort,
                "comments": top, "viewer": self.viewer(viewer, state == "open")}

    def viewer(self, s: dict | None, open_: bool) -> dict:
        if not s:
            return {"signedIn": False}
        out = {"signedIn": True, "csrf": s["csrf"]}
        a = s.get("account")
        if not a:
            out["needsSignup"] = True
            return out
        out["name"] = a["name"]
        out["team"] = bool(self.acc.team_role(a))
        if self.acc.ban_of(account=a["id"]):
            out["banned"] = True
        p = self.paused(a["id"])
        if p:
            out["pausedUntil"] = p["until"] if p["until"] is not None else -1
        out["firstHeld"] = bool(not out["team"] and not self.has_pc(a["id"]) and not self.trusted(a["id"]))
        out["canPost"] = open_ and not out.get("banned") and not p
        return out

    def counts(self) -> dict:
        out = {}
        for r in self.store.all("SELECT post, COUNT(*) AS n FROM cm_comments WHERE state='live' GROUP BY post"):
            out[r["post"]] = r["n"]
        return out

    # ------------------------------------------------------------ what players do
    def post(self, s: dict, d: dict, ip: str) -> dict:
        acct = s["account"]
        self._can_write(acct)
        slug = str(d.get("post", ""))
        st = self.post_state(slug)
        if st == "missing":
            raise self.Error(404, "No such post.")
        if st == "closed":
            raise self.Error(409, "Comments on this post are closed.")
        text = self._text(d.get("text"))
        parent = d.get("parent")
        if parent not in (None, "", 0):
            p = self._comment(parent)
            if p["post"] != slug:
                raise self.Error(400, "That reply belongs to another post.")
            if p["parent"]:
                p = self._comment(p["parent"])               # replies stay one level deep: answer the thread
            if p["state"] != "live":
                raise self.Error(409, "That comment can't take replies any more.")
            parent = p["id"]
        else:
            parent = None
        team = bool(self.acc.team_role(acct))
        if not team:
            if (self.acc.limited("cm-20s:" + acct["id"], 1, 20) or self.acc.limited("cm-ip:" + ip, 20, 3600)):
                raise self.Error(429, "One moment: you just posted.")
            if self.acc.limited("cm-hour:" + acct["id"], 8, 3600):
                raise self.Error(429, "That is a lot of comments for one hour. Try again later.")
            if self.acc.limited("cm-day:" + acct["id"], 30, 86400):
                raise self.Error(429, "You reached today's comment limit.")
        t = self.now()
        if self.store.one("SELECT 1 AS x FROM cm_comments WHERE account=? AND text=? AND created>?", (acct["id"], text, t - 86400)):
            raise self.Error(409, "You already posted that.")
        why = self._hold_reason(acct, text)
        cur = self.store.x("INSERT INTO cm_comments(post, parent, account, text, created, state, reason) VALUES(?,?,?,?,?,?,?)",
                           (slug, parent, acct["id"], text, t, "held" if why else "live", why))
        return {"ok": True, "id": cur.lastrowid, "held": bool(why)}

    def _own(self, s: dict, cid) -> dict:
        c = self._comment(cid)
        if c["account"] != s["account"]["id"]:
            raise self.Error(403, "That is not your comment.")
        return c

    def edit(self, s: dict, d: dict) -> dict:
        acct = s["account"]
        self._can_write(acct)
        c = self._own(s, d.get("id"))
        if c["state"] not in ("live", "held"):
            raise self.Error(409, "That comment can't be edited.")
        if self.now() - c["created"] > EDIT_MINUTES * 60:
            raise self.Error(409, "Comments can be edited for %d minutes." % EDIT_MINUTES)
        text = self._text(d.get("text"))
        if text == c["text"]:
            return {"ok": True, "id": c["id"], "held": c["state"] == "held"}
        state, reason = c["state"], c["reason"]
        if state == "live" and self.filtered(text) and not self.acc.team_role(acct):
            state, reason = "held", "filter"
        elif state == "live" and has_link(text) and not self.has_pc(acct["id"]) and not self.acc.team_role(acct):
            state, reason = "held", "link"
        self.store.x("UPDATE cm_comments SET text=?, edited=?, state=?, reason=? WHERE id=?",
                     (text, self.now(), state, reason, c["id"]))
        return {"ok": True, "id": c["id"], "held": state == "held"}

    def delete(self, s: dict, d: dict) -> dict:
        c = self._own(s, d.get("id"))
        with self.store.tx() as db:
            self._drop(db, c)
        return {"ok": True}

    def _drop(self, db, c: dict) -> None:
        """The author's comment goes: whole, or as an empty 'deleted' line while replies hang under it."""
        kids = db.db.execute("SELECT 1 FROM cm_comments WHERE parent=? LIMIT 1", (c["id"],)).fetchone()
        db.db.execute("DELETE FROM cm_likes WHERE comment=?", (c["id"],))
        db.db.execute("DELETE FROM cm_reports WHERE comment=?", (c["id"],))
        if kids:
            db.db.execute("UPDATE cm_comments SET state='deleted', text='', account=NULL, reason=NULL, likes=0, pinned=0 "
                          "WHERE id=?", (c["id"],))
        else:
            db.db.execute("DELETE FROM cm_comments WHERE id=?", (c["id"],))
            if c["parent"]:
                self._prune(db, c["parent"])

    def _prune(self, db, parent: int) -> None:
        """A deleted placeholder whose last reply went is not needed any more."""
        row = db.db.execute("SELECT state FROM cm_comments WHERE id=?", (parent,)).fetchone()
        if row and row[0] == "deleted" and not db.db.execute("SELECT 1 FROM cm_comments WHERE parent=? LIMIT 1", (parent,)).fetchone():
            db.db.execute("DELETE FROM cm_comments WHERE id=?", (parent,))

    def like(self, s: dict, d: dict) -> dict:
        acct = s["account"]
        if self.acc.ban_of(account=acct["id"]):
            raise self.Error(403, "Your account is suspended.")
        c = self._comment(d.get("id"))
        if c["state"] != "live":
            raise self.Error(409, "That comment can't be liked.")
        if c["account"] == acct["id"]:
            raise self.Error(409, "You can't like your own comment.")
        on = d.get("on") is not False
        if self.acc.limited("cm-like:" + acct["id"], 60, 3600):
            raise self.Error(429, "Easy on the hearts. Try again later.")
        with self.store.tx() as db:
            if on:
                db.db.execute("INSERT OR IGNORE INTO cm_likes VALUES(?,?,?)", (c["id"], acct["id"], self.now()))
            else:
                db.db.execute("DELETE FROM cm_likes WHERE comment=? AND account=?", (c["id"], acct["id"]))
            n = db.db.execute("SELECT COUNT(*) FROM cm_likes WHERE comment=?", (c["id"],)).fetchone()[0]
            db.db.execute("UPDATE cm_comments SET likes=? WHERE id=?", (n, c["id"]))
        return {"ok": True, "id": c["id"], "likes": n, "liked": on}

    def report(self, s: dict, d: dict) -> dict:
        acct = s["account"]
        if self.acc.ban_of(account=acct["id"]):
            raise self.Error(403, "Your account is suspended.")
        c = self._comment(d.get("id"))
        if c["account"] == acct["id"]:
            raise self.Error(409, "That is your own comment.")
        reason = str(d.get("reason", ""))
        if reason not in REASONS:
            raise self.Error(400, "Pick a reason.")
        note = clean_text(d.get("note", ""))[:200]
        if self.acc.limited("cm-report:" + acct["id"], 10, 86400):
            raise self.Error(429, "You sent a lot of reports today. Our team is on it.")
        t = self.now()
        with self.store.tx() as db:
            db.db.execute("INSERT OR IGNORE INTO cm_reports(comment, account, reason, note, created) VALUES(?,?,?,?,?)",
                          (c["id"], acct["id"], reason, note, t))
            n = db.db.execute("SELECT COUNT(DISTINCT account) FROM cm_reports WHERE comment=? AND closed IS NULL",
                              (c["id"],)).fetchone()[0]
            author = self.acc.account(c["account"]) if c["account"] else None
            if (n >= REPORTS_TO_HIDE and c["state"] == "live" and not (author and self.acc.team_role(author))):
                db.db.execute("UPDATE cm_comments SET state='hidden', reason='reports', moderated=? WHERE id=?", (t, c["id"]))
        return {"ok": True}

    # ------------------------------------------------------------ account life
    def forget(self, acct_id: str) -> None:
        """The account is deleted: its comments, likes, reports, pause and trust go with it."""
        for c in self.store.all("SELECT * FROM cm_comments WHERE account=?", (acct_id,)):
            with self.store.tx() as db:
                self._drop(db, c)
        with self.store.tx() as db:
            liked = [r[0] for r in db.db.execute("SELECT comment FROM cm_likes WHERE account=?", (acct_id,))]
            db.db.execute("DELETE FROM cm_likes WHERE account=?", (acct_id,))
            for cid in liked:
                db.db.execute("UPDATE cm_comments SET likes=(SELECT COUNT(*) FROM cm_likes WHERE comment=?) WHERE id=?", (cid, cid))
            db.db.execute("DELETE FROM cm_reports WHERE account=?", (acct_id,))
            db.db.execute("DELETE FROM cm_pauses WHERE account=?", (acct_id,))
            db.db.execute("DELETE FROM cm_trust WHERE account=?", (acct_id,))

    def export(self, acct_id: str) -> dict:
        return {
            "comments": self.store.all("SELECT id, post, parent, text, created, edited, state FROM cm_comments WHERE account=? "
                                       "ORDER BY created", (acct_id,)),
            "likes": self.store.all("SELECT comment, created FROM cm_likes WHERE account=?", (acct_id,)),
            "reportsSent": self.store.all("SELECT comment, reason, note, created, closed FROM cm_reports WHERE account=?", (acct_id,)),
            "pause": self.store.one("SELECT until, reason, created FROM cm_pauses WHERE account=?", (acct_id,)),
        }

    def tidy(self) -> dict:
        t = self.now()
        out = {}
        gone = self.store.all("SELECT * FROM cm_comments WHERE (state='removed' AND moderated<?) OR (state='held' AND created<?)",
                              (t - REMOVED_KEEP_DAYS * 86400, t - HELD_KEEP_DAYS * 86400))
        for c in gone:
            with self.store.tx() as db:
                self._drop(db, c)
        out["comments"] = len(gone)
        out["reports"] = self.store.x("DELETE FROM cm_reports WHERE closed IS NOT NULL AND closed<?",
                                      (t - REPORT_KEEP_DAYS * 86400,)).rowcount
        self.store.x("DELETE FROM cm_pauses WHERE until IS NOT NULL AND until<=?", (t,))
        return out

    # ------------------------------------------------------------ staff (loopback, the portal)
    def _staff_row(self, c: dict, with_text=True) -> dict:
        a = self.acc.account(c["account"]) if c["account"] else None
        reports = self.store.all("SELECT r.reason, r.note, r.created, a.name FROM cm_reports r LEFT JOIN accounts a "
                                 "ON a.id=r.account WHERE r.comment=? AND r.closed IS NULL ORDER BY r.created", (c["id"],))
        out = {"id": c["id"], "post": c["post"], "parent": c["parent"], "state": c["state"], "reason": c["reason"],
               "at": c["created"], "edited": c["edited"], "likes": c["likes"], "pinned": bool(c["pinned"]),
               "moderated": c["moderated"], "moderatedBy": c["moderated_by"], "reports": reports}
        if with_text:
            out["text"] = c["text"]
        if a:
            p = self.paused(a["id"])
            out["author"] = {"account": a["id"], "name": a["name"], "statsId": self.account_pid(a["id"]),
                             "created": a["created"], "matches": a["matches"] or 0, "badges": self.acc.badges(a),
                             "team": bool(self.acc.team_role(a)), "pc": self.has_pc(a["id"]),
                             "paused": (p["until"] if p["until"] is not None else -1) if p else None,
                             "today": self.store.one("SELECT COUNT(*) AS n FROM cm_comments WHERE account=? AND created>?",
                                                     (a["id"], self.now() - 86400))["n"]}
        return out

    def stats(self) -> dict:
        t = self.now()
        one = lambda sql, args=(): self.store.one(sql, args)["n"]  # noqa: E731
        return {
            "reported": one("SELECT COUNT(DISTINCT comment) AS n FROM cm_reports r JOIN cm_comments c ON c.id=r.comment "
                            "WHERE r.closed IS NULL AND c.state='live'"),
            "hidden": one("SELECT COUNT(*) AS n FROM cm_comments c WHERE state='hidden' AND EXISTS(SELECT 1 FROM cm_reports r "
                          "WHERE r.comment=c.id AND r.closed IS NULL)"),
            "held": one("SELECT COUNT(*) AS n FROM cm_comments WHERE state='held'"),
            "today": one("SELECT COUNT(*) AS n FROM cm_comments WHERE created>? AND state!='deleted'", (t - 86400,)),
            "todayPosts": one("SELECT COUNT(DISTINCT post) AS n FROM cm_comments WHERE created>?", (t - 86400,)),
            "paused": one("SELECT COUNT(*) AS n FROM cm_pauses WHERE until IS NULL OR until>?", (t,)),
            "closedPosts": [r["post"] for r in self.store.all("SELECT post FROM cm_posts WHERE closed IS NOT NULL ORDER BY post")],
            "needs": one("SELECT COUNT(*) AS n FROM cm_comments c WHERE c.state='held' OR (c.state IN ('live','hidden') AND "
                         "EXISTS(SELECT 1 FROM cm_reports r WHERE r.comment=c.id AND r.closed IS NULL))"),
        }

    def queue(self, tab: str, post: str = "", q: str = "") -> dict:
        where, args = [], []
        if tab == "needs":
            where.append("(c.state='held' OR (c.state IN ('live','hidden') AND EXISTS(SELECT 1 FROM cm_reports r WHERE "
                         "r.comment=c.id AND r.closed IS NULL)))")
        elif tab == "hidden":
            where.append("c.state IN ('hidden','removed')")
        elif tab == "paused":
            rows = []
            for p in self.store.all("SELECT * FROM cm_pauses WHERE until IS NULL OR until>? ORDER BY created DESC", (self.now(),)):
                a = self.acc.account(p["account"])
                rows.append({"account": p["account"], "name": a["name"] if a else "?", "until": p["until"] if p["until"] is not None else -1,
                             "reason": p["reason"] or "", "by": p["by_whom"] or "", "at": p["created"]})
            return {"paused": rows}
        else:
            where.append("c.state!='deleted'")
        if post:
            where.append("c.post=?")
            args.append(post)
        if q:
            where.append("c.account IN (SELECT id FROM accounts WHERE name LIKE ? ESCAPE '\\')")
            args.append("%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        rows = self.store.all("SELECT c.* FROM cm_comments c WHERE " + " AND ".join(where) + " ORDER BY c.created DESC LIMIT 200", tuple(args))
        return {"comments": [self._staff_row(c) for c in rows]}

    def act(self, d: dict) -> dict:
        c = self._comment(d.get("id"))
        action = str(d.get("action", ""))
        by = str(d.get("by", ""))[:64]
        t = self.now()
        with self.store.tx() as db:
            if action == "publish":                      # a held comment is fine: the author is trusted from now on
                if c["state"] not in ("held", "hidden"):
                    raise self.Error(409, "Only held or hidden comments can be published.")
                db.db.execute("UPDATE cm_comments SET state='live', reason=NULL, moderated=?, moderated_by=? WHERE id=?", (t, by, c["id"]))
                db.db.execute("UPDATE cm_reports SET closed=?, outcome='kept' WHERE comment=? AND closed IS NULL", (t, c["id"]))
                if c["account"]:
                    db.db.execute("INSERT OR IGNORE INTO cm_trust VALUES(?,?)", (c["account"], t))
            elif action == "restore":
                if c["state"] not in ("hidden", "removed"):
                    raise self.Error(409, "That comment is not hidden.")
                db.db.execute("UPDATE cm_comments SET state='live', reason=NULL, moderated=?, moderated_by=? WHERE id=?", (t, by, c["id"]))
                db.db.execute("UPDATE cm_reports SET closed=?, outcome='kept' WHERE comment=? AND closed IS NULL", (t, c["id"]))
            elif action == "dismiss":                    # reports were wrong: close them, the comment stays as it is
                db.db.execute("UPDATE cm_reports SET closed=?, outcome='no action' WHERE comment=? AND closed IS NULL", (t, c["id"]))
            elif action == "hide":
                if c["state"] not in ("live", "held", "hidden"):        # hidden by reports: staff keep it hidden
                    raise self.Error(409, "That comment is already gone.")
                db.db.execute("UPDATE cm_comments SET state='hidden', reason='staff', pinned=0, moderated=?, moderated_by=? WHERE id=?",
                              (t, by, c["id"]))
                db.db.execute("UPDATE cm_reports SET closed=?, outcome='hidden' WHERE comment=? AND closed IS NULL", (t, c["id"]))
            elif action == "remove":
                if c["state"] == "deleted":
                    raise self.Error(409, "The author already deleted it.")
                db.db.execute("UPDATE cm_comments SET state='removed', reason='staff', pinned=0, moderated=?, moderated_by=? WHERE id=?",
                              (t, by, c["id"]))
                db.db.execute("UPDATE cm_reports SET closed=?, outcome='removed' WHERE comment=? AND closed IS NULL", (t, c["id"]))
            elif action in ("pin", "unpin"):
                if action == "pin":
                    if c["parent"] or c["state"] != "live":
                        raise self.Error(409, "Only a visible top-level comment can be pinned.")
                    db.db.execute("UPDATE cm_comments SET pinned=0 WHERE post=?", (c["post"],))
                db.db.execute("UPDATE cm_comments SET pinned=? WHERE id=?", (1 if action == "pin" else 0, c["id"]))
            else:
                raise self.Error(400, "Unknown action.")
        return {"ok": True, "comment": self._staff_row(self._comment(c["id"]))}

    def _target(self, d: dict) -> dict:
        a = None
        if d.get("account"):
            a = self.acc.account(str(d["account"]))
        elif d.get("name"):
            a = self.acc.by_name(str(d["name"]))
        if not a:
            raise self.Error(404, "No such account.")
        return a

    def pause(self, d: dict) -> dict:
        a = self._target(d)
        try:
            days = int(d.get("days", 0) or 0)
        except (TypeError, ValueError):
            raise self.Error(400, "Days must be a number.") from None
        if days < 0 or days > 3650:
            raise self.Error(400, "Days must be 0 (for good) to 3650.")
        until = None if days == 0 else self.now() + days * 86400
        self.store.x("INSERT OR REPLACE INTO cm_pauses VALUES(?,?,?,?,?)",
                     (a["id"], until, clean_text(d.get("reason", ""))[:200], str(d.get("by", ""))[:64], self.now()))
        return {"ok": True, "account": a["id"], "name": a["name"], "until": until if until is not None else -1}

    def unpause(self, d: dict) -> dict:
        a = self._target(d)
        self.store.x("DELETE FROM cm_pauses WHERE account=?", (a["id"],))
        return {"ok": True}

    def close(self, d: dict) -> dict:
        slug = str(d.get("post", ""))
        if not SLUG.fullmatch(slug):
            raise self.Error(400, "Which post?")
        if d.get("closed") is False:
            self.store.x("DELETE FROM cm_posts WHERE post=?", (slug,))
        else:
            self.store.x("INSERT OR REPLACE INTO cm_posts VALUES(?,?,?)", (slug, self.now(), str(d.get("by", ""))[:64]))
        return {"ok": True, "post": slug, "closed": d.get("closed") is not False}

    def staff_reply(self, d: dict) -> dict:
        a = self.acc.by_discord(str(d.get("discord", "")))
        if not a:
            raise self.Error(409, "Make a TrueCombat account with your Discord first (truecombat.eu/account), then reply.")
        if self.acc.ban_of(account=a["id"]):
            raise self.Error(403, "That account is suspended.")
        p = self._comment(d.get("parent"))
        if p["parent"]:
            p = self._comment(p["parent"])
        if p["state"] == "deleted":
            raise self.Error(409, "That thread is gone.")
        text = self._text(d.get("text"))
        cur = self.store.x("INSERT INTO cm_comments(post, parent, account, text, created, state) VALUES(?,?,?,?,?,'live')",
                           (p["post"], p["id"], a["id"], text, self.now()))
        return {"ok": True, "id": cur.lastrowid}
