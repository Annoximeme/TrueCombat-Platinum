#!/usr/bin/env python3
"""TrueCombat: Platinum player accounts: optional, Discord sign-in, progress that follows the player.

Nobody needs an account to play. Players who want one sign in with Discord on truecombat.eu (scope
"identify" only: no email, no password, no real name), reserve a name and link their PCs. A PC is
identified by the game's private Ed25519 key (profile/etmain/eacid.key, the same key the game uses for
the anti-cheat sign-in); the launcher proves it holds that key by signing a one-time link code. We only
ever see the public key, and store the key id: the first 40 hex digits of SHA-256 of the public key
(identical to the "sub" of the EOS sign-in service).

What it gives the player:
  * progress follows you: every linked key is one player in the stats service (rank, rating, totals);
    a lost key is replaced by linking the new one;
  * a public profile (truecombat.eu/u/<name>), with the Discord name only when the player turns it on;
  * a reserved name: game servers read a list of hashed name skeletons and the key ids allowed to use them.

Routes (all under /api/account, behind Caddy on the main site so the session cookie is first-party):
  GET  login, callback, me, check?name=, link/status?code=, export, profile?u=, names.json, reserved.txt
  POST logout, signup, name, settings, link/start, claim (from the launcher), unlink, delete
  GET  /internal/... loopback-only, shared token: account lookup for the Discord bot and the staff portal

Python 3.10+ standard library only. State in one SQLite file.

  python3 tcp_accounts.py --config /etc/tcp-accounts/config.json
"""
import argparse
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION = "1.0.0"
log = logging.getLogger("tcp-accounts")

LINK_TAG = b"TrueCombat account link v1\n"
LINK_TTL = 600                    # seconds a link code lives
SESSION_DAYS = 30
PENDING_SESSION = 3600            # a signed-in Discord user who has not made an account yet
NAME_CHANGE_DAYS = 30
NAME_HOLD_DAYS = 30
INACTIVE_DAYS = 365
SIGNIN_LOG_DAYS = 30
MAX_KEYS = 8                      # linked PCs per account
DISCORD_API = "https://discord.com/api/v10"


def now() -> int:
    return int(time.time())


# ----------------------------------------------------------------------------- names

COLOR = re.compile(r"\^[^\^\s]")
NAME_OK = re.compile(r"[A-Za-z0-9 \-_.\[\]*|]{3,20}")
SEPARATORS = set(" -_.[]*|")
LOOKALIKE = str.maketrans({"0": "o", "1": "i", "l": "i", "!": "i", "3": "e", "4": "a", "@": "a",
                           "5": "s", "$": "s", "7": "t", "8": "b", "9": "g", "2": "z", "6": "g"})
# Studio and staff words: a name may not contain these.
BLOCK_CONTAINS = ["admin", "staff", "moderator", "official", "truecombat", "terminus", "console", "server",
                  "support", "anticheat", "devteam"]
# Whole-name blocks. "player" as a prefix covers the Player#### names the game hands out.
BLOCK_EXACT = ["mod", "mods", "gm", "dev", "owner", "system", "root", "anonymous", "unnamedplayer", "nobody"]
BLOCK_PREFIX = ["player"]
# A short abuse list: long words match anywhere in the name, short ones only as the whole name.
ABUSE = ["nigger", "nigga", "faggot", "retard", "hitler", "tranny", "rapist", "whore", "chink"]
ABUSE_EXACT = ["fag", "nazi", "kike"]


def display_name(raw: str) -> str:
    text = COLOR.sub("", unicodedata.normalize("NFKC", str(raw or "")))
    text = "".join(ch for ch in text if ch.isprintable())
    return re.sub(r"\s+", " ", text).strip()


def skeleton(name: str) -> str:
    """What a name looks like, for collisions: RaziC*, r4z1c and 'R a z i c' all give 'razic'."""
    s = display_name(name).lower().translate(LOOKALIKE)
    s = "".join(ch for ch in s if ch not in SEPARATORS and ch.isalnum())
    out = []
    for ch in s:                                  # repeated letters count once: Raazic = Razic
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)


_SK = {}


def _sk_list(words):
    return [skeleton(w) for w in words]


def name_problem(raw: str) -> str | None:
    """None when the name may be reserved, else a reason the player can read."""
    name = display_name(raw)
    if not NAME_OK.fullmatch(name):
        return "Use 3 to 20 characters: letters, digits, spaces and - _ . [ ] * |"
    if name != raw.strip() and COLOR.search(str(raw)):
        return "Leave colour codes out: pick your colour in the launcher."
    sk = skeleton(name)
    if len(sk) < 3:
        return "The name needs at least 3 letters or digits."
    if not _SK:
        _SK.update(exact=set(_sk_list(BLOCK_EXACT)), prefix=_sk_list(BLOCK_PREFIX), contains=_sk_list(BLOCK_CONTAINS),
                   abuse=_sk_list(ABUSE), abuse_exact=set(_sk_list(ABUSE_EXACT)))
    if sk in _SK["exact"] or any(sk.startswith(p) for p in _SK["prefix"]):
        return "That name is reserved for the game."
    if any(w in sk for w in _SK["contains"]):
        return "Names may not contain studio or staff words."
    if any(w in sk for w in _SK["abuse"]) or sk in _SK["abuse_exact"]:
        return "That name is not allowed."
    return None


def name_hash(sk: str) -> str:
    """What game servers see: a hash of the skeleton, so hidden accounts' names are not listed in clear."""
    return hashlib.sha256(("tcp-name:" + sk).encode()).hexdigest()[:32]


# ----------------------------------------------------------------------------- ids

def key_id(public: bytes) -> str:
    return hashlib.sha256(public).hexdigest()[:40]


def stats_pid(raw: str) -> str:
    """The stats service's public player id (tcp_stats.player_id)."""
    return hashlib.sha256(("tcp-lb:" + str(raw)).encode()).hexdigest()[:16]


def key_pid(kid: str) -> str:
    return stats_pid("key:" + kid)


def account_pid(acct: str) -> str:
    return stats_pid("acct:" + acct)


# ----------------------------------------------------------------------------- Ed25519 verify (RFC 8032)

_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _padd(a, b):
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    A = (y1 - x1) * (y2 - x2) % _P
    B = (y1 + x1) * (y2 + x2) % _P
    C = 2 * t1 * t2 * _D % _P
    D = 2 * z1 * z2 % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _pmul(s, p):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _padd(q, p)
        p = _padd(p, p)
        s >>= 1
    return q


def _pequal(a, b):
    x1, y1, z1, _ = a
    x2, y2, z2, _ = b
    return (x1 * z2 - x2 * z1) % _P == 0 and (y1 * z2 - y2 * z1) % _P == 0


def _recover_x(y, sign):
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


def _pdecompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % _P)


_GY = 4 * pow(5, _P - 2, _P) % _P
_G = (_recover_x(_GY, 0), _GY, 1, _recover_x(_GY, 0) * _GY % _P)


def ed25519_verify(public: bytes, msg: bytes, sig: bytes) -> bool:
    if len(public) != 32 or len(sig) != 64:
        return False
    A = _pdecompress(public)
    R = _pdecompress(sig[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(sig[32:], "little")
    if s >= _L:
        return False
    h = int.from_bytes(hashlib.sha512(sig[:32] + public + msg).digest(), "little") % _L
    return _pequal(_pmul(s, _G), _padd(R, _pmul(h, A)))


def link_message(code: str, public_hex: str) -> bytes:
    return LINK_TAG + code.encode() + b"\n" + public_hex.encode()


# ----------------------------------------------------------------------------- store

DDL = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS accounts(
  id TEXT PRIMARY KEY, discord_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, skeleton TEXT NOT NULL,
  visibility TEXT NOT NULL DEFAULT 'public', show_discord INTEGER NOT NULL DEFAULT 0,
  discord_name TEXT, discord_avatar TEXT, created INTEGER NOT NULL, name_changed INTEGER NOT NULL,
  last_active INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS names(skeleton TEXT PRIMARY KEY, account TEXT NOT NULL, display TEXT NOT NULL,
  held_until INTEGER);
CREATE TABLE IF NOT EXISTS keys(id INTEGER PRIMARY KEY, kid TEXT NOT NULL, account TEXT NOT NULL, public TEXT NOT NULL,
  label TEXT, linked INTEGER NOT NULL, retired INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS keys_active ON keys(kid) WHERE retired IS NULL;
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, discord_id TEXT NOT NULL, discord_name TEXT,
  discord_avatar TEXT, csrf TEXT NOT NULL, created INTEGER NOT NULL, seen INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS links(code TEXT PRIMARY KEY, account TEXT NOT NULL, created INTEGER NOT NULL,
  used_by TEXT);
CREATE TABLE IF NOT EXISTS signins(at INTEGER NOT NULL, account TEXT, ip TEXT);
CREATE INDEX IF NOT EXISTS keys_account ON keys(account);
CREATE INDEX IF NOT EXISTS names_account ON names(account);
"""


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.executescript(DDL)
            if not self.one("SELECT v FROM meta WHERE k='ip_salt'"):
                self.x("INSERT INTO meta VALUES('ip_salt', ?)", (secrets.token_hex(16),))

    def x(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args)

    def one(self, sql, args=()):
        with self.lock:
            r = self.db.execute(sql, args).fetchone()
        return dict(r) if r else None

    def all(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args)]

    def tx(self):
        return _Tx(self)


class _Tx:
    def __init__(self, store):
        self.store = store

    def __enter__(self):
        self.store.lock.acquire()
        self.store.db.execute("BEGIN IMMEDIATE")
        return self.store

    def __exit__(self, kind, *_):
        try:
            self.store.db.execute("ROLLBACK" if kind else "COMMIT")
        finally:
            self.store.lock.release()
        return False


class Accounts:
    """Everything the routes do, without HTTP, so tests can drive it directly."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        data = Path(cfg.get("data_dir", "/var/lib/tcp-accounts"))
        data.mkdir(parents=True, exist_ok=True)
        self.store = Store(cfg.get("db") or str(data / "accounts.db"))
        self.rate = {}
        self.rate_lock = threading.Lock()
        self.dirty = threading.Event()        # the stats aliases or the reserved list need pushing
        self.stop = threading.Event()
        self.dirty.set()

    # -- small helpers
    def limited(self, key: str, count: int, window: int) -> bool:
        t = time.time()
        with self.rate_lock:
            hits = [h for h in self.rate.get(key, []) if t - h < window]
            if len(hits) >= count:
                self.rate[key] = hits
                return True
            hits.append(t)
            self.rate[key] = hits
            if len(self.rate) > 20000:
                self.rate = {k: v for k, v in self.rate.items() if v and t - v[-1] < 3600}
        return False

    def ip_hash(self, ip: str) -> str:
        salt = self.store.one("SELECT v FROM meta WHERE k='ip_salt'")["v"]
        return hashlib.sha256((salt + ip).encode()).hexdigest()[:16]

    def account(self, acct: str) -> dict | None:
        return self.store.one("SELECT * FROM accounts WHERE id=?", (acct,))

    def by_discord(self, discord_id: str) -> dict | None:
        return self.store.one("SELECT * FROM accounts WHERE discord_id=?", (discord_id,))

    def by_name(self, name: str) -> dict | None:
        sk = skeleton(name)
        row = self.store.one("SELECT account FROM names WHERE skeleton=? AND held_until IS NULL", (sk,))
        return self.account(row["account"]) if row else None

    def name_taken(self, sk: str, acct: str | None = None) -> bool:
        row = self.store.one("SELECT account, held_until FROM names WHERE skeleton=?", (sk,))
        if not row or row["account"] == acct:
            return False
        if row["held_until"] and row["held_until"] < now():
            self.store.x("DELETE FROM names WHERE skeleton=?", (sk,))
            return False
        return True

    def check_name(self, name: str, acct: str | None = None) -> str | None:
        why = name_problem(name)
        if why:
            return why
        if self.name_taken(skeleton(name), acct):
            return "That name, or one that looks like it, is taken."
        return None

    # -- sessions
    def new_session(self, discord_id: str, discord_name: str, avatar: str, ip: str) -> str:
        sid = secrets.token_urlsafe(32)
        t = now()
        self.store.x("INSERT INTO sessions VALUES(?,?,?,?,?,?,?)",
                     (hashlib.sha256(sid.encode()).hexdigest(), discord_id, discord_name[:64], avatar[:64],
                      secrets.token_urlsafe(24), t, t))
        acct = self.by_discord(discord_id)
        if acct:
            self.store.x("UPDATE accounts SET last_active=? WHERE id=?", (t, acct["id"]))
            if acct["show_discord"]:
                self.store.x("UPDATE accounts SET discord_name=?, discord_avatar=? WHERE id=?",
                             (discord_name[:64], avatar[:64], acct["id"]))
        self.store.x("INSERT INTO signins VALUES(?,?,?)", (t, acct["id"] if acct else None, self.ip_hash(ip)))
        return sid

    def session(self, sid: str) -> dict | None:
        if not sid or not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", sid):
            return None
        s = self.store.one("SELECT * FROM sessions WHERE id=?", (hashlib.sha256(sid.encode()).hexdigest(),))
        if not s:
            return None
        t = now()
        acct = self.by_discord(s["discord_id"])
        limit = SESSION_DAYS * 86400 if acct else PENDING_SESSION
        if t - s["created"] > limit:
            self.store.x("DELETE FROM sessions WHERE id=?", (s["id"],))
            return None
        if t - s["seen"] > 300:
            self.store.x("UPDATE sessions SET seen=? WHERE id=?", (t, s["id"]))
        s["account"] = acct
        return s

    def end_session(self, s: dict) -> None:
        self.store.x("DELETE FROM sessions WHERE id=?", (s["id"],))

    # -- account life
    def signup(self, s: dict, name: str, visibility: str, age_ok: bool) -> dict:
        if s["account"]:
            raise ApiError(409, "You already have an account.")
        if not age_ok:
            raise ApiError(400, "Accounts are for players aged 13 or older.")
        if visibility not in ("public", "hidden"):
            raise ApiError(400, "Pick public or hidden.")
        name = display_name(name)
        acct = secrets.token_hex(8)
        t = now()
        with self.store.tx() as db:
            why = self.check_name(name)
            if why:
                raise ApiError(409, why)
            sk = skeleton(name)
            db.db.execute("DELETE FROM names WHERE skeleton=?", (sk,))      # an expired hold
            db.db.execute("INSERT INTO accounts(id, discord_id, name, skeleton, visibility, show_discord, created, "
                          "name_changed, last_active) VALUES(?,?,?,?,?,0,?,?,?)",
                          (acct, s["discord_id"], name, sk, visibility, t, t, t))
            db.db.execute("INSERT INTO names VALUES(?,?,?,NULL)", (sk, acct, name))
        self.dirty.set()
        return self.account(acct)

    def rename(self, acct: dict, name: str) -> dict:
        name = display_name(name)
        t = now()
        sk = skeleton(name)
        if name == acct["name"]:
            return acct
        if sk != acct["skeleton"] and t - acct["name_changed"] < NAME_CHANGE_DAYS * 86400:
            days = NAME_CHANGE_DAYS - (t - acct["name_changed"]) // 86400
            raise ApiError(409, "You can change your name again in %d days." % max(1, days))
        with self.store.tx() as db:
            why = self.check_name(name, acct["id"])
            if why:
                raise ApiError(409, why)
            if sk == acct["skeleton"]:            # same skeleton: only the spelling changes, no wait, no hold
                db.db.execute("UPDATE names SET display=? WHERE skeleton=?", (name, sk))
                db.db.execute("UPDATE accounts SET name=? WHERE id=?", (name, acct["id"]))
            else:
                db.db.execute("UPDATE names SET held_until=? WHERE skeleton=? AND account=?",
                              (t + NAME_HOLD_DAYS * 86400, acct["skeleton"], acct["id"]))
                db.db.execute("DELETE FROM names WHERE skeleton=?", (sk,))
                db.db.execute("INSERT INTO names VALUES(?,?,?,NULL)", (sk, acct["id"], name))
                db.db.execute("UPDATE accounts SET name=?, skeleton=?, name_changed=? WHERE id=?",
                              (name, sk, t, acct["id"]))
        self.dirty.set()
        return self.account(acct["id"])

    def settings(self, s: dict, visibility: str | None, show_discord: bool | None) -> dict:
        acct = s["account"]
        if visibility is not None:
            if visibility not in ("public", "hidden"):
                raise ApiError(400, "Pick public or hidden.")
            self.store.x("UPDATE accounts SET visibility=? WHERE id=?", (visibility, acct["id"]))
        if show_discord is not None:
            if show_discord:
                self.store.x("UPDATE accounts SET show_discord=1, discord_name=?, discord_avatar=? WHERE id=?",
                             (s["discord_name"], s["discord_avatar"], acct["id"]))
            else:
                self.store.x("UPDATE accounts SET show_discord=0, discord_name=NULL, discord_avatar=NULL WHERE id=?",
                             (acct["id"],))
        return self.account(acct["id"])

    def delete(self, acct: dict) -> None:
        with self.store.tx() as db:
            for table, col in (("keys", "account"), ("names", "account"), ("links", "account")):
                db.db.execute("DELETE FROM %s WHERE %s=?" % (table, col), (acct["id"],))
            db.db.execute("DELETE FROM sessions WHERE discord_id=?", (acct["discord_id"],))
            db.db.execute("DELETE FROM signins WHERE account=?", (acct["id"],))
            db.db.execute("DELETE FROM accounts WHERE id=?", (acct["id"],))
        self.dirty.set()

    def export(self, acct: dict) -> dict:
        a = self.account(acct["id"])
        return {
            "schema": "tcp-account-export/1", "exported": now(),
            "account": {k: a[k] for k in ("id", "name", "visibility", "show_discord", "discord_id", "discord_name",
                                          "created", "name_changed", "last_active")},
            "statsId": account_pid(a["id"]),
            "names": self.store.all("SELECT display, held_until FROM names WHERE account=?", (a["id"],)),
            "keys": self.store.all("SELECT kid, public, label, linked, retired FROM keys WHERE account=?", (a["id"],)),
            "sessions": self.store.all("SELECT created, seen FROM sessions WHERE discord_id=?", (a["discord_id"],)),
            "signins": [r["at"] for r in self.store.all("SELECT at FROM signins WHERE account=? ORDER BY at", (a["id"],))],
            "note": "Match stats are public and anonymous; see your profile or the stats service for them.",
        }

    # -- linking a PC
    def link_start(self, acct: dict) -> dict:
        if self.limited("linkstart:" + acct["id"], 10, 3600):
            raise ApiError(429, "Too many link codes. Try again later.")
        code = secrets.token_hex(16)
        self.store.x("DELETE FROM links WHERE account=? AND used_by IS NULL", (acct["id"],))
        self.store.x("INSERT INTO links VALUES(?,?,?,NULL)", (hashlib.sha256(code.encode()).hexdigest(), acct["id"], now()))
        return {"code": code, "url": "truecombat://account/" + code, "expires_in": LINK_TTL}

    def link_status(self, acct: dict, code: str) -> dict:
        if not re.fullmatch(r"[0-9a-f]{32}", code or ""):
            raise ApiError(400, "Bad code.")
        row = self.store.one("SELECT * FROM links WHERE code=? AND account=?",
                             (hashlib.sha256(code.encode()).hexdigest(), acct["id"]))
        if not row:
            return {"state": "unknown"}
        if row["used_by"]:
            return {"state": "linked", "key": row["used_by"]}
        if now() - row["created"] > LINK_TTL:
            return {"state": "expired"}
        return {"state": "waiting"}

    def claim(self, code: str, public_hex: str, signature_hex: str, label: str, ip: str) -> dict:
        if self.limited("claim:" + ip, 20, 3600):
            raise ApiError(429, "Too many tries. Try again later.")
        code, public_hex, signature_hex = str(code).lower(), str(public_hex).lower(), str(signature_hex).lower()
        if (not re.fullmatch(r"[0-9a-f]{32}", code) or not re.fullmatch(r"[0-9a-f]{64}", public_hex)
                or not re.fullmatch(r"[0-9a-f]{128}", signature_hex)):
            raise ApiError(400, "Bad request.")
        public = bytes.fromhex(public_hex)
        if not ed25519_verify(public, link_message(code, public_hex), bytes.fromhex(signature_hex)):
            raise ApiError(401, "The signature does not match this key.")
        kid = key_id(public)
        label = display_name(label)[:32] or "PC"
        t = now()
        with self.store.tx() as db:
            h = hashlib.sha256(code.encode()).hexdigest()
            row = db.db.execute("SELECT * FROM links WHERE code=?", (h,)).fetchone()
            if not row or row["used_by"] or t - row["created"] > LINK_TTL:
                raise ApiError(410, "This link code has expired. Start again on truecombat.eu.")
            acct = row["account"]
            owner = db.db.execute("SELECT id, account FROM keys WHERE kid=? AND retired IS NULL", (kid,)).fetchone()
            if owner and owner["account"] != acct:
                raise ApiError(409, "This PC is linked to another account. Unlink it there first.")
            if owner:
                db.db.execute("UPDATE keys SET label=? WHERE id=?", (label, owner["id"]))
            else:
                active = db.db.execute("SELECT COUNT(*) FROM keys WHERE account=? AND retired IS NULL", (acct,)).fetchone()[0]
                if active >= MAX_KEYS:
                    raise ApiError(409, "An account can link %d PCs. Unlink an old one first." % MAX_KEYS)
                db.db.execute("INSERT INTO keys(kid, account, public, label, linked, retired) VALUES(?,?,?,?,?,NULL)",
                              (kid, acct, public_hex, label, t))
            db.db.execute("UPDATE links SET used_by=? WHERE code=?", (kid, h))
            db.db.execute("UPDATE accounts SET last_active=? WHERE id=?", (t, acct))
            name = db.db.execute("SELECT name FROM accounts WHERE id=?", (acct,)).fetchone()["name"]
        self.dirty.set()
        log.info("key %s linked to account %s", kid[:12], acct)
        return {"ok": True, "key": kid, "account": name}

    def unlink(self, acct: dict, kid: str) -> None:
        """The key stops counting for this account from now on; matches played with it before stay yours."""
        n = self.store.x("UPDATE keys SET retired=? WHERE kid=? AND account=? AND retired IS NULL",
                         (now(), str(kid), acct["id"])).rowcount
        if not n:
            raise ApiError(404, "No such linked PC.")
        self.dirty.set()

    def keys_of(self, acct_id: str, active_only=False) -> list:
        sql = "SELECT kid, label, linked, retired FROM keys WHERE account=?" + (" AND retired IS NULL" if active_only else "")
        return self.store.all(sql + " ORDER BY linked, id", (acct_id,))

    # -- what others read
    def me(self, s: dict | None) -> dict:
        if not s:
            return {"signedIn": False}
        out = {"signedIn": True, "csrf": s["csrf"], "discord": {"name": s["discord_name"], "avatar": s["discord_avatar"]}}
        a = s["account"]
        if not a:
            out["needsSignup"] = True
            return out
        t = now()
        out["account"] = {
            "name": a["name"], "visibility": a["visibility"], "showDiscord": bool(a["show_discord"]),
            "created": a["created"], "statsId": account_pid(a["id"]),
            "nameChangeIn": max(0, NAME_CHANGE_DAYS * 86400 - (t - a["name_changed"])),
            "keys": [{"id": k["kid"], "label": k["label"], "linked": k["linked"], "retired": k["retired"]}
                     for k in self.keys_of(a["id"])],
        }
        return out

    def profile(self, name: str) -> dict | None:
        a = self.by_name(name)
        if not a or a["visibility"] != "public":
            return None
        out = {"name": a["name"], "verified": True, "created": a["created"], "statsId": account_pid(a["id"]),
               "pcs": len(self.keys_of(a["id"], active_only=True))}
        if a["show_discord"] and a["discord_name"]:
            out["discord"] = {"name": a["discord_name"],
                              "avatar": ("https://cdn.discordapp.com/avatars/%s/%s.png?size=128" % (a["discord_id"], a["discord_avatar"]))
                              if a["discord_avatar"] else ""}
        return out

    def names_json(self) -> dict:
        """Stats id -> account name for public accounts (leaderboards, match pages, the bot)."""
        return {account_pid(r["id"]): r["name"] for r in
                self.store.all("SELECT id, name FROM accounts WHERE visibility='public'")}

    def reserved_txt(self) -> str:
        """For game servers: hashed name skeleton -> the key ids allowed to use it. Held names have no keys,
        so nobody may use them until the hold ends."""
        lines = ["TCPNAMES1 %d" % now()]
        rows = self.store.all("SELECT n.skeleton, n.account, n.held_until FROM names n")
        keys = {}
        for k in self.store.all("SELECT kid, account FROM keys WHERE retired IS NULL"):
            keys.setdefault(k["account"], []).append(k["kid"])
        t = now()
        for r in sorted(rows, key=lambda r: r["skeleton"]):
            if r["held_until"] and r["held_until"] < t:
                continue
            allowed = sorted(keys.get(r["account"], []))          # a held name still belongs to its owner
            lines.append("%s %s" % (name_hash(r["skeleton"]), ",".join(allowed) or "-"))
        return "\n".join(lines) + "\n"

    def aliases(self) -> list:
        """For the stats service: which key player ids are one account, and when. A key's whole history before
        it was linked counts for the account that links it, unless an earlier account had it then: each link
        runs from the end of the one before it (or the beginning) to its unlink (or for good)."""
        out, prev = [], {}
        for k in self.store.all("SELECT kid, account, linked, retired FROM keys ORDER BY kid, linked, id"):
            since = prev.get(k["kid"])
            out.append({"pid": key_pid(k["kid"]), "canonical": account_pid(k["account"]),
                        "since": since, "until": k["retired"]})
            prev[k["kid"]] = k["retired"] or k["linked"]
        return out

    def internal_lookup(self, discord_id: str = "", name: str = "", pid: str = "") -> dict | None:
        a = None
        if discord_id:
            a = self.by_discord(discord_id)
        elif name:
            a = self.by_name(name)
        elif pid:
            for r in self.store.all("SELECT id FROM accounts"):
                if account_pid(r["id"]) == pid:
                    a = self.account(r["id"])
                    break
        if not a:
            return None
        return {"id": a["id"], "name": a["name"], "discordId": a["discord_id"], "visibility": a["visibility"],
                "statsId": account_pid(a["id"]), "created": a["created"], "lastActive": a["last_active"],
                "keys": [{"id": k["kid"], "label": k["label"], "linked": k["linked"], "retired": k["retired"],
                          "statsId": key_pid(k["kid"])} for k in self.keys_of(a["id"])]}

    def staff_rename(self, acct_id: str, name: str) -> dict:
        """Staff force a new name (abuse). No wait, no hold on the old one."""
        a = self.account(acct_id)
        if not a:
            raise ApiError(404, "No such account.")
        name = display_name(name)
        with self.store.tx() as db:
            why = self.check_name(name, acct_id)
            if why:
                raise ApiError(409, why)
            sk = skeleton(name)
            db.db.execute("DELETE FROM names WHERE account=?", (acct_id,))
            db.db.execute("DELETE FROM names WHERE skeleton=?", (sk,))
            db.db.execute("INSERT INTO names VALUES(?,?,?,NULL)", (sk, acct_id, name))
            db.db.execute("UPDATE accounts SET name=?, skeleton=?, name_changed=? WHERE id=?", (name, sk, now(), acct_id))
        self.dirty.set()
        return self.account(acct_id)

    # -- housekeeping
    def tidy(self) -> dict:
        t = now()
        out = {}
        out["holds"] = self.store.x("DELETE FROM names WHERE held_until IS NOT NULL AND held_until<?", (t,)).rowcount
        out["links"] = self.store.x("DELETE FROM links WHERE created<?", (t - 86400,)).rowcount
        out["signins"] = self.store.x("DELETE FROM signins WHERE at<?", (t - SIGNIN_LOG_DAYS * 86400,)).rowcount
        out["sessions"] = self.store.x("DELETE FROM sessions WHERE created<?", (t - SESSION_DAYS * 86400,)).rowcount
        # names of accounts with no sign-in and no linked-PC use for a year are released; the account stays
        idle = self.store.all("SELECT id, skeleton FROM accounts WHERE last_active<?", (t - INACTIVE_DAYS * 86400,))
        released = 0
        for a in idle:
            released += self.store.x("DELETE FROM names WHERE account=?", (a["id"],)).rowcount
        out["released"] = released
        if out["holds"] or released:
            self.dirty.set()
        return out

    def touch_key(self, kid: str) -> None:
        """A game server saw this key (from its match reports): the account counts as active."""
        self.store.x("UPDATE accounts SET last_active=? WHERE id=(SELECT account FROM keys WHERE kid=? AND retired IS NULL)",
                     (now(), kid))

    # -- pushes
    def push(self) -> list:
        """Writes the reserved list for local game servers and sends the aliases to the stats service."""
        done = []
        text = self.reserved_txt()
        for folder in self.cfg.get("reserved_dirs", []):
            try:
                p = Path(folder)
                p.mkdir(parents=True, exist_ok=True)
                tmp = p / "names.txt.tmp"
                body = text
                old = (p / "names.txt").read_text(encoding="utf-8") if (p / "names.txt").exists() else ""
                if old.split("\n", 1)[-1] != body.split("\n", 1)[-1]:
                    tmp.write_text(body, encoding="utf-8")
                    os.replace(tmp, p / "names.txt")
                    done.append("names:" + folder)
            except OSError as e:
                log.warning("could not write %s: %s", folder, e)
        url = self.cfg.get("stats_url", "")
        token = credential("stats-token", self.cfg.get("stats_token", ""))
        if url and token:
            body = json.dumps({"aliases": self.aliases()}).encode()
            req = urllib.request.Request(url.rstrip("/") + "/accounts/aliases", data=body, method="POST",
                                         headers={"Content-Type": "application/json", "X-Accounts-Token": token})
            with urllib.request.urlopen(req, timeout=60) as r:
                done.append("stats:%s" % json.loads(r.read() or b"{}").get("rebuilt", "unchanged"))
        return done

    def background(self) -> None:
        last_tidy = 0
        while not self.stop.is_set():
            if time.time() - last_tidy > 3600:
                last_tidy = time.time()
                try:
                    self.tidy()
                except sqlite3.Error:
                    log.exception("tidy failed")
            self.dirty.wait(600)                # a change, or every 10 minutes in case the stats service missed one
            if self.stop.is_set():
                break
            self.dirty.clear()
            try:
                self.push()
            except (OSError, urllib.error.URLError, ValueError) as e:
                log.warning("push failed, retrying in a minute: %s", e)
                self.stop.wait(60)
                self.dirty.set()


def credential(name: str, fallback: str = "") -> str:
    cred = os.environ.get("CREDENTIALS_DIRECTORY")
    if cred and (Path(cred) / name).exists():
        return (Path(cred) / name).read_text(encoding="utf-8").strip()
    return str(fallback or "").strip()


# ----------------------------------------------------------------------------- HTTP

def http_json(url: str, data: dict | None = None, token: str | None = None, timeout: float = 8) -> dict:
    headers = {"User-Agent": "TrueCombatAccounts/%s" % VERSION, "Accept": "application/json"}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}
PREFIX = "/api/account"


def make_handler(acc: Accounts):
    cfg = acc.cfg
    public = cfg.get("public_url", "http://127.0.0.1:%d" % cfg.get("port", 8095)).rstrip("/")
    site = cfg.get("site_url", public).rstrip("/")
    secure_cookie = public.startswith("https://")
    cookie_name = ("__Host-" if secure_cookie else "") + "tcpacct"
    state_cookie = ("__Host-" if secure_cookie else "") + "tcpacct_state"
    dev_login = bool(cfg.get("dev_login")) and os.environ.get("TCP_ACCOUNTS_DEV") == "1"
    internal_token = credential("internal-token", cfg.get("internal_token", ""))
    oauth = cfg.get("discord", {})

    class Handler(BaseHTTPRequestHandler):
        server_version = "TCPAccounts"
        sys_version = ""
        timeout = 30
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            log.debug("%s", fmt % args)            # no IPs in the journal

        def client_ip(self) -> str:
            ip = self.client_address[0]
            if ip in ("127.0.0.1", "::1") and self.headers.get("X-Forwarded-For"):
                return self.headers["X-Forwarded-For"].split(",")[-1].strip()
            return ip

        def local(self) -> bool:
            return self.client_address[0] in ("127.0.0.1", "::1") and not self.headers.get("X-Forwarded-For")

        def send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
            try:
                unread = int(self.headers.get("Content-Length") or 0) != 0 and not getattr(self, "_body_read", False)
            except ValueError:
                unread = True
            self.send_response(status)
            if unread:
                self.close_connection = True
                self.send_header("Connection", "close")
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            if not (extra or {}).get("Cache-Control"):
                self.send_header("Cache-Control", "no-store")
            for k, v in SECURITY_HEADERS.items():
                self.send_header(k, v)
            for k, v in (extra or {}).items():
                for item in (v if isinstance(v, list) else [v]):
                    self.send_header(k, item)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def json(self, data, status: int = 200, extra: dict | None = None) -> None:
            self.send(status, json.dumps(data, separators=(",", ":")).encode(), "application/json; charset=utf-8", extra)

        def redirect(self, to: str, cookies: list | None = None) -> None:
            self.send(302, b"", "text/plain", {"Location": to, "Set-Cookie": cookies or []})

        def body_json(self, limit: int = 8192) -> dict:
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError as e:
                raise ApiError(400, "Bad request.") from e
            if n < 0 or n > limit:
                raise ApiError(413, "Too much data.")
            self._body_read = True
            raw = self.rfile.read(n) if n else b"{}"
            try:
                data = json.loads(raw or b"{}")
            except ValueError as e:
                raise ApiError(400, "Bad JSON.") from e
            if not isinstance(data, dict):
                raise ApiError(400, "Bad JSON.")
            return data

        def cookie(self, name: str) -> str:
            for part in (self.headers.get("Cookie") or "").split(";"):
                k, _, v = part.strip().partition("=")
                if k == name:
                    return v
            return ""

        def set_cookie(self, name: str, value: str, max_age: int) -> str:
            c = "%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d" % (name, value, max_age)
            return c + ("; Secure" if secure_cookie else "")

        def session(self) -> dict | None:
            return acc.session(self.cookie(cookie_name))

        def need_account(self, write: bool = True) -> dict:
            s = self.session()
            if not s:
                raise ApiError(401, "Please sign in.")
            if write and not hmac.compare_digest(self.headers.get("X-CSRF", ""), s["csrf"]):
                raise ApiError(403, "Please reload the page and try again.")
            if not s["account"]:
                raise ApiError(409, "Make your account first.")
            return s

        # -- dispatch
        def do_GET(self):
            self.route("GET")

        def do_HEAD(self):
            self.route("GET")

        def do_POST(self):
            self.route("POST")

        def route(self, method: str) -> None:
            u = urllib.parse.urlsplit(self.path)
            path = u.path
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
            try:
                if path.startswith("/internal/"):
                    return self.internal(method, path, qs)
                if not path.startswith(PREFIX + "/"):
                    raise ApiError(404, "Not found.")
                sub = path[len(PREFIX) + 1:]
                fn = getattr(self, "%s_%s" % (method.lower(), sub.replace("/", "_").replace(".", "_")), None)
                if not fn or not re.fullmatch(r"[a-z_/.]+", sub):
                    raise ApiError(404, "Not found.")
                if method == "POST" and sub != "claim":
                    origin = self.headers.get("Origin")
                    if origin and origin.rstrip("/") not in (site, public):
                        raise ApiError(403, "Cross-site request refused.")
                return fn(qs)
            except ApiError as e:
                self.json({"error": e.message}, e.status)
            except Exception:  # noqa: BLE001
                log.exception("request failed: %s %s", method, path)
                self.json({"error": "Something went wrong on our side."}, 500)

        # -- sign-in
        def get_login(self, qs):
            state = secrets.token_urlsafe(24)
            url = "https://discord.com/oauth2/authorize?" + urllib.parse.urlencode({
                "client_id": oauth.get("client_id", ""), "response_type": "code",
                "redirect_uri": public + PREFIX + "/callback", "scope": "identify", "state": state, "prompt": "none"})
            self.redirect(url, [self.set_cookie(state_cookie, state, 600)])

        def get_callback(self, qs):
            state = self.cookie(state_cookie)
            back = site + "/account.html"
            if not state or not hmac.compare_digest(state, qs.get("state", "")) or not qs.get("code"):
                return self.redirect(back + "?signin=failed")
            if acc.limited("login:" + self.client_ip(), 10, 600):
                return self.redirect(back + "?signin=slow")
            try:
                tok = http_json(DISCORD_API + "/oauth2/token", {
                    "client_id": oauth.get("client_id", ""), "client_secret": credential("client-secret", oauth.get("client_secret", "")),
                    "grant_type": "authorization_code", "code": qs["code"], "redirect_uri": public + PREFIX + "/callback"})
                me = http_json(DISCORD_API + "/users/@me", token=tok["access_token"])
            except (urllib.error.URLError, OSError, ValueError, KeyError):
                log.exception("Discord sign-in failed")
                return self.redirect(back + "?signin=discord")
            # the Discord access token is not kept: we only needed who you are
            sid = acc.new_session(str(me["id"]), str(me.get("global_name") or me.get("username") or ""),
                                  str(me.get("avatar") or ""), self.client_ip())
            self.redirect(back, [self.set_cookie(cookie_name, sid, SESSION_DAYS * 86400),
                                 self.set_cookie(state_cookie, "", 0)])

        def get_dev(self, qs):
            if not (dev_login and self.local()):
                raise ApiError(404, "Not found.")
            sid = acc.new_session(qs.get("id", "1000"), qs.get("name", "Dev"), "", "127.0.0.1")
            self.redirect(site + "/account.html", [self.set_cookie(cookie_name, sid, SESSION_DAYS * 86400)])

        def post_logout(self, qs):
            s = self.session()
            if s and hmac.compare_digest(self.headers.get("X-CSRF", ""), s["csrf"]):
                acc.end_session(s)
            self.json({"ok": True}, extra={"Set-Cookie": [self.set_cookie(cookie_name, "", 0)]})

        # -- the account page
        def get_me(self, qs):
            self.json(acc.me(self.session()))

        def get_check(self, qs):
            if acc.limited("check:" + self.client_ip(), 120, 600):
                raise ApiError(429, "Slow down a little.")
            s = self.session()
            why = acc.check_name(qs.get("name", ""), s["account"]["id"] if s and s["account"] else None)
            self.json({"ok": why is None, "reason": why or ""})

        def post_signup(self, qs):
            s = self.session()
            if not s:
                raise ApiError(401, "Please sign in.")
            if not hmac.compare_digest(self.headers.get("X-CSRF", ""), s["csrf"]):
                raise ApiError(403, "Please reload the page and try again.")
            d = self.body_json()
            acc.signup(s, str(d.get("name", "")), str(d.get("visibility", "public")), d.get("age13") is True)
            self.json(acc.me(self.session()))

        def post_name(self, qs):
            s = self.need_account()
            acc.rename(s["account"], str(self.body_json().get("name", "")))
            self.json(acc.me(self.session()))

        def post_settings(self, qs):
            s = self.need_account()
            d = self.body_json()
            acc.settings(s, d.get("visibility"), (d["showDiscord"] is True) if "showDiscord" in d else None)
            self.json(acc.me(self.session()))

        def post_link_start(self, qs):
            s = self.need_account()
            self.json(acc.link_start(s["account"]))

        def get_link_status(self, qs):
            s = self.need_account(write=False)
            self.json(acc.link_status(s["account"], qs.get("code", "")))

        def post_unlink(self, qs):
            s = self.need_account()
            acc.unlink(s["account"], str(self.body_json().get("key", "")))
            self.json(acc.me(self.session()))

        def get_export(self, qs):
            s = self.need_account(write=False)
            body = json.dumps(acc.export(s["account"]), indent=2).encode()
            self.send(200, body, "application/json; charset=utf-8",
                      {"Content-Disposition": 'attachment; filename="truecombat-account.json"'})

        def post_delete(self, qs):
            s = self.need_account()
            d = self.body_json()
            if skeleton(str(d.get("confirm", ""))) != s["account"]["skeleton"]:
                raise ApiError(400, "Type your account name to confirm.")
            acc.delete(s["account"])
            self.json({"ok": True}, extra={"Set-Cookie": [self.set_cookie(cookie_name, "", 0)]})

        # -- the launcher
        def post_claim(self, qs):
            d = self.body_json(2048)
            self.json(acc.claim(d.get("code", ""), d.get("public", ""), d.get("signature", ""),
                                str(d.get("label", "")), self.client_ip()))

        # -- public reads (cacheable)
        def get_profile(self, qs):
            p = acc.profile(qs.get("u", ""))
            if not p:
                raise ApiError(404, "No public profile with that name.")
            self.json(p, extra={"Cache-Control": "public, max-age=60", "Access-Control-Allow-Origin": "*"})

        def get_names_json(self, qs):
            self.json(acc.names_json(), extra={"Cache-Control": "public, max-age=120", "Access-Control-Allow-Origin": "*"})

        def get_reserved_txt(self, qs):
            self.send(200, acc.reserved_txt().encode(), "text/plain; charset=utf-8",
                      {"Cache-Control": "public, max-age=120"})

        def get_health(self, qs):
            self.json({"ok": True, "version": VERSION})

        # -- loopback only: the Discord bot and the staff portal
        def internal(self, method, path, qs):
            if (not internal_token or not self.local()
                    or not hmac.compare_digest(self.headers.get("X-Accounts-Token", ""), internal_token)):
                raise ApiError(404, "Not found.")
            if method == "GET" and path == "/internal/lookup":
                a = acc.internal_lookup(qs.get("discord", ""), qs.get("name", ""), qs.get("pid", ""))
                return self.json(a) if a else self.json({"error": "No such account."}, 404)
            if method == "POST" and path == "/internal/rename":
                d = self.body_json()
                a = acc.staff_rename(str(d.get("id", "")), str(d.get("name", "")))
                return self.json({"ok": True, "name": a["name"]})
            if method == "POST" and path == "/internal/seen":
                for kid in (self.body_json().get("keys") or [])[:256]:
                    if re.fullmatch(r"[0-9a-f]{40}", str(kid)):
                        acc.touch_key(str(kid))
                return self.json({"ok": True})
            raise ApiError(404, "Not found.")

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--listen", help="host:port (default from the config, 127.0.0.1:8095)")
    ap.add_argument("--push-once", action="store_true", help="write the reserved list and send the aliases, then exit")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    if cfg.get("dev_login") and str(cfg.get("public_url", "")).startswith("https://"):
        raise SystemExit("dev_login is for local tests only")
    acc = Accounts(cfg)
    if a.push_once:
        print("\n".join(acc.push()) or "nothing to push")
        return 0
    host, _, port = (a.listen or "%s:%s" % (cfg.get("host", "127.0.0.1"), cfg.get("port", 8095))).rpartition(":")
    threading.Thread(target=acc.background, daemon=True).start()
    httpd = ThreadingHTTPServer((host, int(port)), make_handler(acc))
    httpd.daemon_threads = True
    log.info("accounts %s on http://%s:%s", VERSION, host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        acc.stop.set()
    return 0


if __name__ == "__main__":
    sys.exit(main())
