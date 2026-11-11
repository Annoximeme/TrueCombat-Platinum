"""The bot's own state in SQLite: account links, events, sign-ups and small
bits of memory (message ids, last announced release, ...).

Calls are synchronous: every query is tiny and local, so running them on the
event loop is simpler and faster than a thread pool.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS links(
  discord_id INTEGER PRIMARY KEY, pid TEXT NOT NULL UNIQUE, name TEXT NOT NULL, linked_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS link_codes(
  code TEXT PRIMARY KEY, discord_id INTEGER NOT NULL, expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
  starts INTEGER NOT NULL, capacity INTEGER NOT NULL DEFAULT 0, server TEXT NOT NULL DEFAULT '',
  channel_id INTEGER NOT NULL DEFAULT 0, message_id INTEGER NOT NULL DEFAULT 0,
  scheduled_id INTEGER NOT NULL DEFAULT 0, created_by INTEGER NOT NULL, created_at INTEGER NOT NULL,
  reminded INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'open');
CREATE TABLE IF NOT EXISTS rsvps(
  event_id INTEGER NOT NULL, user_id INTEGER NOT NULL, status TEXT NOT NULL, at INTEGER NOT NULL,
  PRIMARY KEY(event_id, user_id));
CREATE TABLE IF NOT EXISTS docs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'open',
  owner INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL, data TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS docs_kind ON docs(kind, state);
CREATE TABLE IF NOT EXISTS achievements(
  pid TEXT NOT NULL, key TEXT NOT NULL, at INTEGER NOT NULL, PRIMARY KEY(pid, key));
CREATE TABLE IF NOT EXISTS alerts(
  discord_id INTEGER NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL, label TEXT NOT NULL DEFAULT '',
  last_sent INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(discord_id, kind, target));
CREATE TABLE IF NOT EXISTS teams(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE, tag TEXT NOT NULL UNIQUE COLLATE NOCASE,
  captain INTEGER NOT NULL, rating REAL NOT NULL DEFAULT 1000, wins INTEGER NOT NULL DEFAULT 0,
  losses INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS team_members(
  discord_id INTEGER PRIMARY KEY, team_id INTEGER NOT NULL, joined INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS team_invites(
  team_id INTEGER NOT NULL, discord_id INTEGER NOT NULL, at INTEGER NOT NULL, PRIMARY KEY(team_id, discord_id));
"""

# Unambiguous characters only: no 0/O, 1/I/L
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class Store:
    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        self.db.close()

    # ------------------------------------------------------------ key/value
    def get(self, key: str, default=None):
        r = self.db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(r["value"]) if r else default

    def set(self, key: str, value) -> None:
        self.db.execute("INSERT INTO kv VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, json.dumps(value)))
        self.db.commit()

    def delete(self, key: str) -> None:
        self.db.execute("DELETE FROM kv WHERE key=?", (key,))
        self.db.commit()

    # ------------------------------------------------------------ links
    def new_link_code(self, discord_id: int, minutes: int = 15) -> str:
        now = int(time.time())
        self.db.execute("DELETE FROM link_codes WHERE expires < ? OR discord_id = ?", (now, discord_id))
        while True:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            try:
                self.db.execute("INSERT INTO link_codes VALUES(?, ?, ?)", (code, discord_id, now + minutes * 60))
                break
            except sqlite3.IntegrityError:
                continue
        self.db.commit()
        return code

    def redeem_link_code(self, code: str) -> int | None:
        """Returns the Discord user the code belongs to, and burns the code."""
        code = (code or "").upper().replace("-", "").strip()
        r = self.db.execute("SELECT discord_id FROM link_codes WHERE code=? AND expires >= ?",
                            (code, int(time.time()))).fetchone()
        self.db.execute("DELETE FROM link_codes WHERE code=?", (code,))
        self.db.commit()
        return r["discord_id"] if r else None

    def link(self, discord_id: int, pid: str, name: str) -> int | None:
        """Links a Discord user to a player. Returns the Discord user who had this player before, if any."""
        prev = self.db.execute("SELECT discord_id FROM links WHERE pid=?", (pid,)).fetchone()
        self.db.execute("DELETE FROM links WHERE pid=? OR discord_id=?", (pid, discord_id))
        self.db.execute("INSERT INTO links VALUES(?, ?, ?, ?)", (discord_id, pid, name, int(time.time())))
        self.db.commit()
        if prev and prev["discord_id"] != discord_id:
            return prev["discord_id"]
        return None

    def unlink(self, discord_id: int) -> bool:
        cur = self.db.execute("DELETE FROM links WHERE discord_id=?", (discord_id,))
        self.db.commit()
        return cur.rowcount > 0

    def linked_player(self, discord_id: int):
        return self.db.execute("SELECT * FROM links WHERE discord_id=?", (discord_id,)).fetchone()

    def linked_member(self, pid: str):
        return self.db.execute("SELECT * FROM links WHERE pid=?", (pid,)).fetchone()

    def all_links(self):
        return self.db.execute("SELECT * FROM links").fetchall()

    def rename_link(self, pid: str, name: str) -> None:
        self.db.execute("UPDATE links SET name=? WHERE pid=? AND name<>?", (name, pid, name))
        self.db.commit()

    # ------------------------------------------------------------ events
    def add_event(self, kind: str, title: str, description: str, starts: int, capacity: int,
                  server: str, created_by: int) -> int:
        cur = self.db.execute(
            "INSERT INTO events(kind, title, description, starts, capacity, server, created_by, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (kind, title, description, starts, capacity, server, created_by, int(time.time())))
        self.db.commit()
        return cur.lastrowid

    def event(self, event_id: int):
        return self.db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()

    def update_event(self, event_id: int, **fields) -> None:
        if not fields:
            return
        cols = ", ".join("%s=?" % k for k in fields)
        self.db.execute("UPDATE events SET %s WHERE id=?" % cols, (*fields.values(), event_id))
        self.db.commit()

    def open_events(self):
        return self.db.execute("SELECT * FROM events WHERE state='open' ORDER BY starts").fetchall()

    def rsvp(self, event_id: int, user_id: int, status: str | None) -> None:
        if status is None:
            self.db.execute("DELETE FROM rsvps WHERE event_id=? AND user_id=?", (event_id, user_id))
        else:
            self.db.execute("INSERT INTO rsvps VALUES(?, ?, ?, ?) ON CONFLICT(event_id, user_id) "
                            "DO UPDATE SET status=excluded.status, at=excluded.at",
                            (event_id, user_id, status, int(time.time())))
        self.db.commit()

    def rsvps(self, event_id: int) -> dict[str, list[int]]:
        out: dict[str, list[int]] = {"going": [], "maybe": [], "waitlist": []}
        for r in self.db.execute("SELECT user_id, status FROM rsvps WHERE event_id=? ORDER BY at", (event_id,)):
            out.setdefault(r["status"], []).append(r["user_id"])
        return out

    def rsvp_status(self, event_id: int, user_id: int) -> str | None:
        r = self.db.execute("SELECT status FROM rsvps WHERE event_id=? AND user_id=?", (event_id, user_id)).fetchone()
        return r["status"] if r else None

    # ------------------------------------------------------------ documents
    # Small records with their own life cycle (bug reports, suggestions, appeals, map votes,
    # scrims, tournaments, finished seasons). The body is JSON; kind, state and owner are columns
    # so they can be listed without reading every body.
    def doc_add(self, kind: str, data: dict, owner: int = 0, state: str = "open") -> int:
        cur = self.db.execute("INSERT INTO docs(kind, state, owner, created, data) VALUES(?, ?, ?, ?, ?)",
                              (kind, state, owner, int(time.time()), json.dumps(data)))
        self.db.commit()
        return cur.lastrowid

    @staticmethod
    def _doc(r) -> dict | None:
        if r is None:
            return None
        d = json.loads(r["data"])
        d.update(id=r["id"], kind=r["kind"], state=r["state"], owner=r["owner"], created=r["created"])
        return d

    def doc(self, kind: str, doc_id: int) -> dict | None:
        return self._doc(self.db.execute("SELECT * FROM docs WHERE kind=? AND id=?", (kind, int(doc_id))).fetchone())

    def doc_save(self, d: dict) -> None:
        body = {k: v for k, v in d.items() if k not in ("id", "kind", "state", "owner", "created")}
        self.db.execute("UPDATE docs SET state=?, data=? WHERE id=?", (d["state"], json.dumps(body), d["id"]))
        self.db.commit()

    def docs(self, kind: str, state: str | None = None, owner: int | None = None, limit: int = 100) -> list[dict]:
        q, args = "SELECT * FROM docs WHERE kind=?", [kind]
        if state is not None:
            q += " AND state=?"
            args.append(state)
        if owner is not None:
            q += " AND owner=?"
            args.append(owner)
        return [self._doc(r) for r in self.db.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit))]

    # ------------------------------------------------------------ achievements
    def achievements(self, pid: str) -> dict[str, int]:
        return {r["key"]: r["at"] for r in self.db.execute("SELECT key, at FROM achievements WHERE pid=?", (pid,))}

    def unlock(self, pid: str, keys: list[str], at: int | None = None) -> None:
        at = int(time.time()) if at is None else at
        self.db.executemany("INSERT OR IGNORE INTO achievements VALUES(?, ?, ?)", [(pid, k, at) for k in keys])
        self.db.commit()

    # ------------------------------------------------------------ personal alerts
    def alert_add(self, discord_id: int, kind: str, target: str, label: str = "") -> bool:
        cur = self.db.execute("INSERT OR IGNORE INTO alerts(discord_id, kind, target, label) VALUES(?, ?, ?, ?)",
                              (discord_id, kind, target, label))
        self.db.commit()
        return cur.rowcount > 0

    def alert_remove(self, discord_id: int, kind: str | None = None, target: str | None = None) -> int:
        q, args = "DELETE FROM alerts WHERE discord_id=?", [discord_id]
        if kind is not None:
            q += " AND kind=?"
            args.append(kind)
        if target is not None:
            q += " AND target=?"
            args.append(target)
        cur = self.db.execute(q, args)
        self.db.commit()
        return cur.rowcount

    def alerts_of(self, discord_id: int):
        return self.db.execute("SELECT * FROM alerts WHERE discord_id=? ORDER BY kind, label", (discord_id,)).fetchall()

    def alerts_for(self, kind: str, target: str | None = None):
        if target is None:
            return self.db.execute("SELECT * FROM alerts WHERE kind=?", (kind,)).fetchall()
        return self.db.execute("SELECT * FROM alerts WHERE kind=? AND target=?", (kind, target)).fetchall()

    def alert_sent(self, discord_id: int, kind: str, target: str) -> None:
        self.db.execute("UPDATE alerts SET last_sent=? WHERE discord_id=? AND kind=? AND target=?",
                        (int(time.time()), discord_id, kind, target))
        self.db.commit()

    # ------------------------------------------------------------ teams
    def team(self, team_id: int):
        return self.db.execute("SELECT * FROM teams WHERE id=?", (int(team_id),)).fetchone()

    def team_named(self, name: str):
        return self.db.execute("SELECT * FROM teams WHERE name=? OR tag=?", (name, name)).fetchone()

    def team_of(self, discord_id: int):
        return self.db.execute("SELECT t.* FROM teams t JOIN team_members m ON m.team_id=t.id WHERE m.discord_id=?",
                               (discord_id,)).fetchone()

    def teams(self, search: str = "", limit: int = 25):
        like = "%" + search.replace("%", "").replace("_", "") + "%"
        return self.db.execute("SELECT t.*, (SELECT COUNT(*) FROM team_members m WHERE m.team_id=t.id) members "
                               "FROM teams t WHERE name LIKE ? OR tag LIKE ? ORDER BY rating DESC, wins DESC, name "
                               "LIMIT ?", (like, like, limit)).fetchall()

    def team_create(self, name: str, tag: str, captain: int) -> int | None:
        try:
            cur = self.db.execute("INSERT INTO teams(name, tag, captain, created) VALUES(?, ?, ?, ?)",
                                  (name, tag, captain, int(time.time())))
        except sqlite3.IntegrityError:
            return None
        self.db.execute("INSERT INTO team_members VALUES(?, ?, ?)", (captain, cur.lastrowid, int(time.time())))
        self.db.commit()
        return cur.lastrowid

    def team_members(self, team_id: int) -> list[int]:
        return [r["discord_id"] for r in self.db.execute(
            "SELECT discord_id FROM team_members WHERE team_id=? ORDER BY joined", (team_id,))]

    def team_join(self, team_id: int, discord_id: int) -> None:
        self.db.execute("INSERT OR REPLACE INTO team_members VALUES(?, ?, ?)", (discord_id, team_id, int(time.time())))
        self.db.execute("DELETE FROM team_invites WHERE discord_id=?", (discord_id,))
        self.db.commit()

    def team_leave(self, discord_id: int) -> None:
        self.db.execute("DELETE FROM team_members WHERE discord_id=?", (discord_id,))
        self.db.commit()

    def team_delete(self, team_id: int) -> None:
        for table in ("team_members", "team_invites"):
            self.db.execute("DELETE FROM %s WHERE team_id=?" % table, (team_id,))
        self.db.execute("DELETE FROM teams WHERE id=?", (team_id,))
        self.db.commit()

    def team_update(self, team_id: int, **fields) -> None:
        cols = ", ".join("%s=?" % k for k in fields)
        self.db.execute("UPDATE teams SET %s WHERE id=?" % cols, (*fields.values(), team_id))
        self.db.commit()

    def team_invite(self, team_id: int, discord_id: int) -> None:
        self.db.execute("INSERT OR REPLACE INTO team_invites VALUES(?, ?, ?)", (team_id, discord_id, int(time.time())))
        self.db.commit()

    def team_invited(self, team_id: int, discord_id: int, days: int = 7) -> bool:
        r = self.db.execute("SELECT at FROM team_invites WHERE team_id=? AND discord_id=?", (team_id, discord_id)).fetchone()
        return bool(r and r["at"] > time.time() - days * 86400)
