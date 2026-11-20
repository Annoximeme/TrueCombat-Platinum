#!/usr/bin/env python3
"""TrueCombat: Platinum staff portal (staff.truecombat.eu).

A private web console for the people who run the official and pickup servers:
live servers and players, kick / mute / warn / team moves, bans that hold on
every server, map control, live chat with staff replies, player lookup,
player reports and bug reports, an audit log, staff roles and server health.

Standard library only (Python 3.10+). It runs on the VPS next to the game
servers, listens on 127.0.0.1 and sits behind Caddy. Game servers are driven
over rcon on 127.0.0.1; rcon passwords arrive as systemd credentials and never
reach the browser.

    python3 tcp_staff_portal.py --config /etc/tcp-staff-portal/config.json
    python3 test_staff_portal.py          # loopback tests with a fake game server

See README.md for the configuration, roles and deployment.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import collections
import hashlib
import hmac
import ipaddress
import json
import logging
import mimetypes
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION = "1.7.0"
STAFF_KEY_LINK_SECONDS = 600
HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
log = logging.getLogger("tcp-staff")
mimetypes.add_type("application/manifest+json", ".webmanifest")

# ----------------------------------------------------------------------------- roles

ROLES = ["trial", "moderator", "admin", "owner"] # lowest to highest; trial: new staff who watch, warn and write up
RANK = {r: i + 1 for i, r in enumerate(ROLES)}

# Lowest role that may do each thing.
PERMS = {
    "view": "trial",
    "chat.reply": "moderator",
    "player.kick": "moderator",
    "player.warn": "trial",
    "player.mute": "moderator",
    "player.move": "moderator",
    "ban.temp": "moderator",          # up to MOD_BAN_LIMIT minutes
    "ban.perm": "admin",
    "ban.remove": "admin",
    "server.say": "moderator",
    "server.map": "admin",
    "server.restart": "admin",
    "reports": "trial",
    "lookup": "trial",
    "lookup.ip": "admin",
    "audit": "admin",
    "staff.manage": "admin",
    "health": "trial",
    "health.restart": "admin",
    "punish": "moderator",            # punishment ladder; steps past MOD_BAN_LIMIT need an admin
    "watch": "moderator",
    "filters.manage": "admin",
    "templates.manage": "admin",
    "appeals.answer": "admin",
    "schedule": "admin",
    "event": "admin",
    "livemap": "admin",               # positions are wallhack information: admins only, and not while playing there
    "cvars": "admin",
    "review": "admin",
    "weekly": "admin",
    "insights": "admin",              # website visits, channels and downloads (tools/server-bridge/tcp_insights.py)
    "backup": "admin",                # database snapshot status, run one now
    "cases": "trial",             # cases: open, take, link, note, close
    "evidence": "trial",          # add screenshots, demos, chat excerpts and links; download them
    "evidence.delete": "admin",
    "history": "trial",               # player counts over time, uptime, busiest hours
    "quality": "admin",               # what each staff member did and how it held up
    "anticheat": "admin",             # anti-cheat review queue
    "comments": "moderator",          # devlog comments on truecombat.eu: review, hide, remove, pause, pin, reply
    "comments.close": "admin",        # close or reopen comments on a whole devlog post
    "duty": "trial",                  # go on duty: phone alerts for everything, not only urgent ones
    "2fa.reset": "owner",
}
MOD_BAN_LIMIT = 24 * 60
UNDO_SECONDS = 300
SYSTEM = {"discord_id": "", "name": "Portal", "role": "system"}

# Default punishment ladder. Each offence climbs one step per earlier punishment for it in the last 90 days.
# Steps: warn, kick, mute:<length>, ban:<length> (ban:0 is permanent). Override with "ladder" in the config.
DEFAULT_LADDER = {
    "teamkill": {"label": "Team killing", "steps": ["warn", "kick", "ban:1d", "ban:7d", "ban:0"]},
    "toxic": {"label": "Toxic chat", "steps": ["warn", "mute:1h", "mute:1d", "ban:1d", "ban:7d"]},
    "cheat": {"label": "Cheating", "steps": ["ban:0"]},
    "grief": {"label": "Griefing or AFK", "steps": ["warn", "kick", "ban:1d", "ban:7d"]},
    "spam": {"label": "Spam or advertising", "steps": ["warn", "mute:1h", "mute:1d", "ban:1d", "ban:7d"]},
}

# Saved replies seeded on the first start. Admins edit them in the portal.
DEFAULT_TEMPLATES = [
    ("warn", "Team killing", "Watch your fire. Team kills lead to a kick, then a ban."),
    ("warn", "Language", "Keep the chat clean. The next step is a mute."),
    ("warn", "Spawn camping", "Stop camping the enemy spawn. Next time it is a kick."),
    ("kick", "Team killing", "Team killing"),
    ("kick", "AFK", "Away from keyboard"),
    ("kick", "Name", "Offensive name. Change it before you rejoin."),
    ("mute", "Spam", "Chat spam"),
    ("mute", "Toxic", "Toxic behaviour in chat"),
    ("ban", "Cheating", "Cheating"),
    ("ban", "Team killing", "Repeated team killing"),
    ("ban", "Ban evasion", "Ban evasion"),
    ("chat", "Behave", "Staff is watching this server. Play fair and keep it friendly."),
    ("chat", "Restart soon", "The server restarts for an update in 5 minutes."),
    ("appeal", "Accepted", "We looked at your case again and lifted the ban. Welcome back, play fair."),
    ("appeal", "Denied", "We checked the evidence again and the ban stays."),
    ("appeal", "Denied, cheating", "The anti-cheat evidence is clear. Cheating bans are not lifted."),
    ("close", "Banned", "Watched the demo, player banned."),
    ("close", "No action", "Checked the demo and the stats. Nothing wrong found."),
]

# Server settings shown in the portal's config editor, grouped as on the Settings page. Override with "cvars" in the
# config (a {name: label} map; settings without an entry here then show in "Other" as free text).
# Fields: label, help, type (bool | int | choice | words | weather | text), min/max, choices [(value, label)],
# words (the words a "words" setting accepts), next_map (the server only reads it at the next map), view (shown, never
# changed from the portal).
WX_KINDS = ["clear", "overcast", "rain", "storm", "afterrain", "snow", "fog", "wind", "golden"]   # tcp_weather.h order
WX_OFF_WORDS = ["clear", "overcast", "rain", "storm", "afterrain", "snow", "wind", "lightning", "flash", "thunder",
                "splashes", "wetground", "sky", "colour", "sounds", "gusts", "precipitation"]
VOTE_WORDS = ["kick", "map", "restart", "shuffle"]
OFF_ON = [("0", "Off"), ("1", "On")]

CVAR_GROUPS = ["Match", "Weather", "Weapons and CQB", "Movement and combat", "Map vote", "Player votes",
               "Teams and balance", "Bots", "Voice and chat", "Ping and connections", "Server and anti-cheat",
               "Competitive matches", "Other"]

CVAR_META = {
    # -- match
    "tcp_roundtime": {"group": "Match", "label": "Round time (seconds)", "type": "int", "min": 30, "max": 3600},
    "g_roundlimit": {"group": "Match", "label": "Rounds per map", "type": "int", "min": 0, "max": 100, "help": "0 = no round limit (the map timer ends the map)."},
    "sv_mapRotationTime": {"group": "Match", "label": "Minutes per map", "type": "int", "min": 0, "max": 240},
    "g_warmup": {"group": "Match", "label": "Warm-up seconds", "type": "int", "min": 0, "max": 600},
    "g_friendlyFire": {"group": "Match", "label": "Friendly fire", "type": "bool"},
    "g_fallDamage": {"group": "Match", "label": "Fall damage", "type": "bool"},
    # -- weather (0.39.4 random weather, 0.39.5 g_weatherOff)
    "g_weather": {"group": "Weather", "label": "Weather", "type": "weather",
                  "help": "random rolls a new weather every map. clear turns it off. A kind (rain, storm, afterrain, snow, "
                          "wind, overcast) forces it, optionally with a strength: storm:80. Applies from the next map. "
                          "Ranked servers cap rain and storm strength so nothing hides players.", "next_map": True},
    "g_weatherOff": {"group": "Weather", "label": "Turned-off weather kinds and effects", "type": "words", "words": WX_OFF_WORDS,
                     "help": "Kinds left out of the random roll (clear overcast rain storm afterrain snow wind) and effects "
                             "turned off for every player (lightning flash thunder splashes wetground sky colour sounds gusts "
                             "precipitation). Empty = everything on. A forced weather kind still wins. Needs 0.39.5 servers; "
                             "applies from the next map.", "next_map": True},
    "tcp_wx": {"group": "Weather", "label": "Weather on this map", "type": "text", "view": True,
               "help": "What the server rolled for the current map (kind, strength, seed)."},
    # -- weapons and CQB
    "g_weaponPickup": {"group": "Weapons and CQB", "label": "Weapon pickup", "type": "choice",
                       "choices": [("0", "Off"), ("1", "Enemy weapons only"), ("2", "Any dropped weapon")]},
    "g_weaponPickupTime": {"group": "Weapons and CQB", "label": "Seconds a dropped weapon stays", "type": "int", "min": 5, "max": 120},
    "g_experimental": {"group": "Weapons and CQB", "label": "Experimental CQB weapons and rules", "type": "bool",
                       "help": "Unranked servers only: a Ranked server switches it straight back to 0.", "next_map": True},
    # -- movement and combat
    "g_antilag": {"group": "Movement and combat", "label": "Lag compensation", "type": "bool"},
    "g_vault": {"group": "Movement and combat", "label": "Vaulting", "type": "bool", "next_map": True},
    "g_sprintNeedsStamina": {"group": "Movement and combat", "label": "Sprint uses stamina", "type": "bool", "next_map": True},
    "g_staminaRunRecover": {"group": "Movement and combat", "label": "Stamina recovers while running", "type": "bool", "next_map": True},
    "g_adsBlocksSprint": {"group": "Movement and combat", "label": "Aiming down sights stops sprint", "type": "bool", "next_map": True},
    "g_adsFocus": {"group": "Movement and combat", "label": "Aim focus (hold breath)", "type": "bool", "next_map": True},
    "g_hitFeedback": {"group": "Movement and combat", "label": "Hit markers", "type": "bool", "help": "Never shown on Ranked or competitive matches."},
    "g_damageReport": {"group": "Movement and combat", "label": "Damage report after death", "type": "bool"},
    "sv_hudHealthNumbers": {"group": "Movement and combat", "label": "Health numbers on the HUD", "type": "bool"},
    "g_tacticalMap": {"group": "Movement and combat", "label": "Tactical map (+tacmap)", "type": "bool"},
    # -- map vote
    "g_mapvote": {"group": "Map vote", "label": "Map vote at the end of a map", "type": "bool"},
    "g_mapvoteTime": {"group": "Map vote", "label": "Map vote seconds", "type": "int", "min": 5, "max": 120},
    "g_mapvoteChoices": {"group": "Map vote", "label": "Maps to choose from", "type": "int", "min": 2, "max": 5},
    "g_mapvoteReplay": {"group": "Map vote", "label": "Current map can win the vote", "type": "bool"},
    # -- player votes
    "g_allowVote": {"group": "Player votes", "label": "Player votes", "type": "bool"},
    "g_voteTypes": {"group": "Player votes", "label": "Votes players may call", "type": "words", "words": VOTE_WORDS},
    "g_votePercent": {"group": "Player votes", "label": "Yes votes needed (%)", "type": "int", "min": 1, "max": 100},
    "g_voteMinPlayers": {"group": "Player votes", "label": "Players needed to call a vote", "type": "int", "min": 1, "max": 64},
    "g_voteLimit": {"group": "Player votes", "label": "Votes per player per map", "type": "int", "min": 0, "max": 20},
    "g_voteTime": {"group": "Player votes", "label": "Vote seconds", "type": "int", "min": 10, "max": 120},
    "g_reports": {"group": "Player votes", "label": "In-game /report", "type": "bool"},
    # -- teams and balance
    "g_autoBalance": {"group": "Teams and balance", "label": "Automatic team balance", "type": "bool"},
    "g_autoBalanceDelay": {"group": "Teams and balance", "label": "Seconds before auto-balance moves someone", "type": "int", "min": 0, "max": 300},
    "g_balanceGap": {"group": "Teams and balance", "label": "Rating gap that triggers a skill swap", "type": "int", "min": 0, "max": 2000, "help": "Average rating difference between the teams before the server swaps two players at round start."},
    "g_balanceSkill": {"group": "Teams and balance", "label": "Balance teams by rating", "type": "bool"},
    # -- bots
    "bot_minplayers": {"group": "Bots", "label": "Fill with bots up to", "type": "int", "min": 0, "max": 32},
    "bot_skill": {"group": "Bots", "label": "Bot skill", "type": "int", "min": 1, "max": 5},
    "bot_adaptive": {"group": "Bots", "label": "Bots adapt to the players' level", "type": "bool"},
    "bot_standin": {"group": "Bots", "label": "Bot stands in for a player who drops", "type": "bool"},
    "bot_standinTime": {"group": "Bots", "label": "Seconds a stand-in bot keeps the slot", "type": "int", "min": 30, "max": 1800},
    "bot_chat": {"group": "Bots", "label": "Bot chat", "type": "bool"},
    # -- voice and chat
    "g_voice": {"group": "Voice and chat", "label": "Voice chat", "type": "bool"},
    "g_voiceLocal": {"group": "Voice and chat", "label": "Proximity voice", "type": "bool"},
    "g_voiceLocalRange": {"group": "Voice and chat", "label": "Proximity voice range (units)", "type": "int", "min": 200, "max": 6000},
    "g_voiceSprites": {"group": "Voice and chat", "label": "Voice icons over heads", "type": "bool"},
    "g_combatVoice": {"group": "Voice and chat", "label": "Automatic combat callouts", "type": "bool"},
    "g_voiceChatsAllowed": {"group": "Voice and chat", "label": "Quick voice messages before the spam limit", "type": "int", "min": 0, "max": 20},
    # -- ping and connections
    "sv_maxPing": {"group": "Ping and connections", "label": "Highest ping allowed to join", "type": "int", "min": 0, "max": 999, "help": "0 = no limit."},
    "g_maxPing": {"group": "Ping and connections", "label": "Highest ping while playing", "type": "int", "min": 0, "max": 999, "help": "0 = no limit."},
    "g_maxPingTime": {"group": "Ping and connections", "label": "Seconds above the ping limit before action", "type": "int", "min": 5, "max": 300},
    "g_maxPingAction": {"group": "Ping and connections", "label": "Above the ping limit", "type": "choice", "choices": [("0", "Warn only"), ("1", "Kick")]},
    "g_reconnectKeep": {"group": "Ping and connections", "label": "Seconds a dropped player keeps team and score", "type": "int", "min": 0, "max": 1800},
    "g_trustedSlots": {"group": "Ping and connections", "label": "Slots kept for players with an account", "type": "int", "min": 0, "max": 16},
    # -- server and anti-cheat
    "sv_autoDemo": {"group": "Server and anti-cheat", "label": "Record a server demo of every map", "type": "bool"},
    "sv_eac": {"group": "Server and anti-cheat", "label": "Anti-cheat", "type": "choice", "view": True,
               "choices": [("0", "Off"), ("1", "On, unprotected players allowed"), ("2", "Required")],
               "help": "Shown for reference. Anti-cheat is changed only with a server deploy, never from the portal."},
    "sv_official": {"group": "Server and anti-cheat", "label": "Official server", "type": "bool", "view": True,
                    "help": "Shown for reference (from 0.40.0). Changed only with a server deploy."},
    # -- competitive matches
    "g_competitive": {"group": "Competitive matches", "label": "Competitive match mode", "type": "bool"},
    "g_matchRounds": {"group": "Competitive matches", "label": "Match rounds", "type": "int", "min": 0, "max": 60, "help": "0 = the normal round limit."},
    "g_matchKnifeRound": {"group": "Competitive matches", "label": "Knife round for sides", "type": "bool"},
    "g_matchHalftime": {"group": "Competitive matches", "label": "Half-time seconds", "type": "int", "min": 5, "max": 300},
    "g_matchTimeouts": {"group": "Competitive matches", "label": "Time-outs per team", "type": "int", "min": 0, "max": 10},
    "g_matchTimeoutTime": {"group": "Competitive matches", "label": "Time-out seconds", "type": "int", "min": 10, "max": 300},
    "g_matchMinPlayers": {"group": "Competitive matches", "label": "Players needed to start", "type": "int", "min": 1, "max": 32},
    "g_matchEndTime": {"group": "Competitive matches", "label": "Seconds on the result screen", "type": "int", "min": 5, "max": 300},
}
CVARS = {name: m["label"] for name, m in CVAR_META.items()}
CVAR_VALUE = re.compile(r"^[A-Za-z0-9 ._:,-]{0,64}$")


def cvar_check(name: str, value: str, meta: dict | None) -> str:
    """The value as it goes to the server, or ValueError with a message for staff."""
    if not CVAR_VALUE.match(value):
        raise ValueError("Use letters, digits, spaces, dots, commas, colons, - or _ only (64 at most).")
    if not meta:
        return value
    kind = meta.get("type", "text")
    if kind == "bool":
        if value not in ("0", "1"):
            raise ValueError("Use 0 (off) or 1 (on).")
    elif kind == "choice":
        if value not in [c for c, _ in meta["choices"]]:
            raise ValueError("Use one of: " + ", ".join("%s (%s)" % c for c in meta["choices"]) + ".")
    elif kind == "int":
        if not re.fullmatch(r"-?\d{1,6}", value):
            raise ValueError("Use a whole number.")
        lo, hi = meta.get("min"), meta.get("max")
        if (lo is not None and int(value) < lo) or (hi is not None and int(value) > hi):
            raise ValueError("Use a number from %s to %s." % (lo, hi))
        value = str(int(value))
    elif kind == "words":
        words = [w for w in re.split(r"[\s,]+", value.lower()) if w]
        bad = [w for w in words if w not in meta["words"]]
        if bad:
            raise ValueError("Unknown: %s. Use any of: %s." % (", ".join(bad), " ".join(meta["words"])))
        value = " ".join(dict.fromkeys(words))
    elif kind == "weather":
        v = value.lower().strip()
        if v in ("", "off"):
            v = "clear"
        m = re.fullmatch(r"([a-z]+)(?::(\d{1,3}))?", v)
        if not m or (m.group(1) != "random" and m.group(1) not in WX_KINDS) or (m.group(1) == "random" and m.group(2)):
            raise ValueError("Use random, clear, or a kind (%s), optionally with a strength such as storm:80." % ", ".join(WX_KINDS[1:]))
        if m.group(2) and not 0 <= int(m.group(2)) <= 100:
            raise ValueError("Strength is 0 to 100.")
        value = v
    return value


# Event mode: what the server switches to, and back again afterwards. "*random*" makes a fresh password.
EVENT_PRESET = {"g_password": "*random*", "bot_minplayers": "0", "g_autoBalance": "0", "g_allowVote": "0"}


def weather_text(wx: str) -> str:
    """serverinfo tcp_wx "kind,strength,seed[,off]" in words: "storm, strength 60"."""
    parts = (wx or "").split(",")
    try:
        kind = WX_KINDS[int(parts[0])]
        strength = int(parts[1])
    except (ValueError, IndexError):
        return wx
    text = kind if kind == "clear" else "%s, strength %d" % (kind, strength)
    return text + (", some effects off" if len(parts) > 3 and parts[3] not in ("", "0") else "")


def allowed(who, perm: str) -> bool:
    """who: a role name, or a session / actor dict. A dict with "perms" (the person's own grants, 1.4) uses those."""
    if isinstance(who, dict):
        if who.get("perms") is not None:
            return perm in who["perms"]
        who = who.get("role")
    return bool(who) and RANK.get(who, 0) >= RANK[PERMS[perm]]


# ----------------------------------------------------------------------------- small helpers

COLOUR = re.compile(r"\^.")
PID = re.compile(r"^[0-9a-f]{16}$")
MAP_NAME = re.compile(r"^[A-Za-z0-9_-]{1,48}$")


def short_ip(ip: str) -> str:
    """An address cut to its network part for the request log (IPv4 /24, IPv6 /48)."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return "-"
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    bits = 24 if addr.version == 4 else 48
    return str(ipaddress.ip_network(f"{addr}/{bits}", strict=False))


def now() -> int:
    return int(time.time())


def iso(t: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now() if t is None else t))


def plain(text: str) -> str:
    return COLOUR.sub("", str(text or ""))


def safe_arg(text, limit: int = 120) -> str:
    """Free text that is safe inside one rcon command: no quotes, separators, colour codes or control bytes."""
    text = plain(text)
    text = re.sub(r'[";\\\r\n\x00-\x1f\x7f]', " ", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def player_pid(guid: str) -> str:
    """Leaderboard id, the same as the game and stats service: sha256('tcp-lb:' + GUID)[:16]."""
    g = (guid or "").strip()
    if not g:
        return ""
    if len(g) == 32 and all(c in "0123456789abcdefABCDEF" for c in g):
        g = g.upper()
    return hashlib.sha256(("tcp-lb:" + g).encode()).hexdigest()[:16]


def host_of(address: str) -> str:
    a = (address or "").strip()
    if a.startswith("["):
        return a[1:a.find("]")] if "]" in a else a
    if a.count(":") == 1:
        return a.rsplit(":", 1)[0]
    return a


def duration_minutes(text) -> int:
    """'30m', '12h', '7d', '2w', '0' / 'perm' -> minutes (0 = permanent)."""
    t = str(text or "").strip().lower()
    if t in ("", "0", "perm", "permanent"):
        return 0
    m = re.fullmatch(r"(\d{1,5})\s*([mhdw]?)", t)
    if not m:
        raise ValueError("Use a length such as 30m, 12h, 7d or 2w.")
    n = int(m.group(1))
    return n * {"": 1, "m": 1, "h": 60, "d": 1440, "w": 10080}[m.group(2)]


def engine_length(minutes: int) -> str:
    if minutes <= 0:
        return ""
    for unit, size in (("w", 10080), ("d", 1440), ("h", 60)):
        if minutes % size == 0:
            return "%d%s" % (minutes // size, unit)
    return "%dm" % minutes


def human_length(minutes: int) -> str:
    if not minutes:
        return "permanent"
    for unit, size in (("day", 1440), ("hour", 60)):
        if minutes % size == 0:
            n = minutes // size
            return "%d %s%s" % (n, unit, "" if n == 1 else "s")
    return "%d minutes" % minutes


def parse_step(step: str) -> tuple:
    """Ladder step 'warn' | 'kick' | 'mute:1h' | 'ban:7d' -> (action, minutes)."""
    action, _, length = str(step).partition(":")
    if action not in ("warn", "kick", "mute", "ban"):
        raise ValueError("Unknown ladder step %r." % step)
    return action, duration_minutes(length) if action in ("mute", "ban") else 0


def step_label(step: str) -> str:
    action, minutes = parse_step(step)
    if action in ("warn", "kick"):
        return action.title()
    return "%s, %s" % (action.title(), human_length(minutes))


APPEAL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # no 0/O or 1/I


def appeal_code() -> str:
    return "".join(secrets.choice(APPEAL_ALPHABET) for _ in range(6))


def normalise_chat(text: str) -> str:
    """Lower case, common letter swaps undone, everything that is not a letter or digit turned into one space."""
    t = plain(text).lower().translate(str.maketrans("013457@$!|", "oieastasil"))
    return " " + re.sub(r"[^a-z0-9]+", " ", t).strip() + " "


# ----------------------------------------------------------------------------- two-step sign-in (RFC 6238 TOTP)

# --- F12 bug reports ---------------------------------------------------------------------------------
BUG_CATEGORIES = ("Bug", "Suggestion", "Feature")


def bug_category(v) -> str:
    v = str(v or "").strip().capitalize()
    return v if v in BUG_CATEGORIES else "Bug"


def clean_text(v, limit: int) -> str:
    """Report text as sent, minus NULs and other control characters (tabs and line breaks kept), cut to limit."""
    v = v if isinstance(v, str) else ""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]", "", v)[:limit]


def discord_plain(v: str) -> str:
    """Player-written text for a Discord embed: no markdown, masked links, auto-links or mentions; reads as typed."""
    v = re.sub(r"(?i)\b(https?|discord)(?=:)", lambda m: m.group(1) + "\u200b", str(v or ""))   # breaks auto-links
    return re.sub(r"([\\*_~`|>\[\]()#<@-])", r"\\\1", v)


def bug_fields(j: dict) -> tuple:
    """The stored fields of a tcp-bugreport/1 report and its screenshot bytes (empty if none or not a JPEG)."""
    def num(v, lo, hi):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f if lo <= f <= hi and f == f else None
    d = {"format": "tcp-bugreport/1", "category": bug_category(j.get("category")), "text": clean_text(j.get("text"), 16 * 1024)}
    for k, n in (("map", 64), ("build", 64), ("renderer", 120), ("name", 64), ("match", 64), ("puid", 64),
                 ("server_name", 64), ("protocol", 64)):
        v = clean_text(j.get(k), n).strip()
        if k in ("name", "server_name"):
            v = re.sub(r"\^[^^]", "", v).strip()          # game colour codes
        if v:
            d[k if k != "server_name" else "server_label"] = v
    server = str(j.get("server") or "").strip()
    if re.fullmatch(r"[0-9A-Za-z.:\[\]-]{1,64}", server):
        d["server"] = server
    pos = j.get("pos")
    if isinstance(pos, list) and len(pos) == 3 and all(num(c, -1e6, 1e6) is not None for c in pos):
        d["pos"] = [round(float(c)) for c in pos]
    for k, lo, hi in (("time", 0, 2 ** 40), ("ping", 0, 100000), ("fps", 0, 100000)):
        v = num(j.get(k), lo, hi)
        if v is not None:
            d[k] = int(v)
    hw = j.get("hw")
    if isinstance(hw, dict):
        d["hw"] = {clean_text(str(k), 40): clean_text(str(v), 200) for k, v in list(hw.items())[:24]}
    console = re.sub(r"\^[^^\n]", "", clean_text(j.get("console"), 64 * 1024))
    if console:
        d["console"] = console
    guid = clean_text(j.get("guid"), 64).strip()
    if guid:
        d["pid"] = player_pid(guid)          # the same id the servers and the stats service use; the raw guid is not kept
    shot = b""
    b64 = j.get("screenshot_jpg")
    if isinstance(b64, str) and b64:
        try:
            shot = base64.b64decode(b64, validate=True)
        except ValueError:
            shot = b""
        if len(shot) > 1024 * 1024 or not shot.startswith(b"\xff\xd8\xff"):
            shot = b""
    for k, pat in (("kid", r"[0-9a-f]{40}"), ("hwid", None)):
        v = j.get(k)
        if k == "kid" and isinstance(v, str) and re.fullmatch(pat, v.strip().lower()):
            d["kid"] = v.strip().lower()
        if k == "hwid":
            hw = hw_ids(v)
            if hw:
                d["hwid"] = hw
    return d, shot


# --- whole-game bans ------------------------------------------------------------------------
# A whole-game ban holds on every identity the portal has for the player: the stats id (from the game's
# cl_guid), the anti-cheat account (EOS PUID), the PC's account key id (eacid.key), hardware hashes (made
# on the PC, salted, never the raw serials) and, when staff tick it, a keyed tag of the IP address. The
# game asks /api/gamecheck at start; any match keeps it from starting, and the new identities that came
# with a strong match are added to the ban, so a fresh install or a new name on the same PC stays banned.
GAMEBAN_KINDS = {"pid": r"[0-9a-f]{16}", "puid": r"[0-9a-f]{32}", "kid": r"[0-9a-f]{40}", "hw": r"[0-9a-f]{32,64}",
                 "ip": r"[0-9a-f]{12}"}
STRONG_KINDS = ("pid", "puid", "kid", "hw")     # an IP match alone blocks, but never spreads the ban


def hw_ids(v) -> list:
    """Up to 6 hardware hashes as sent by the game or launcher (lower-case hex), invalid ones dropped."""
    if not isinstance(v, list):
        return []
    out = []
    for x in v[:6]:
        x = str(x or "").strip().lower()
        if re.fullmatch(GAMEBAN_KINDS["hw"], x) and x not in out and x.strip("0"):
            out.append(x)
    return out


def id_pairs(pid: str = "", puid: str = "", kid: str = "", hw=(), iptag: str = "") -> list:
    """Valid (kind, value) pairs from whatever identities are known."""
    out = []
    for kind, v in (("pid", pid), ("puid", puid), ("kid", kid), ("ip", iptag)):
        v = str(v or "").strip().lower()
        if v and re.fullmatch(GAMEBAN_KINDS[kind], v):
            out.append((kind, v))
    for h in hw or ():
        if re.fullmatch(GAMEBAN_KINDS["hw"], str(h)):
            out.append(("hw", str(h)))
    return out


# --- QR code (for the authenticator setup) -----------------------------------------------------
# A small byte-mode QR encoder, error correction level M, after Project Nayuki's reference
# implementation (MIT). Made here so the setup screen needs no outside service and the key never
# leaves the portal; the page shows it as an inline SVG image.
_QR_ECC_PER_BLOCK = (0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26,
                     26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28)
_QR_BLOCKS = (0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16,
              17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49)


def _qr_raw_modules(ver: int) -> int:
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        a = ver // 7 + 2
        n -= (25 * a - 10) * a - 55
        if ver >= 7:
            n -= 36
    return n


def _qr_data_codewords(ver: int) -> int:
    return _qr_raw_modules(ver) // 8 - _QR_ECC_PER_BLOCK[ver] * _QR_BLOCKS[ver]


def _qr_gf_mul(x: int, y: int) -> int:
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _qr_rs_divisor(degree: int) -> list:
    res = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            res[j] = _qr_gf_mul(res[j], root)
            if j + 1 < degree:
                res[j] ^= res[j + 1]
        root = _qr_gf_mul(root, 0x02)
    return res


def _qr_rs_remainder(data, divisor) -> list:
    res = [0] * len(divisor)
    for b in data:
        factor = b ^ res.pop(0)
        res.append(0)
        for i, coef in enumerate(divisor):
            res[i] ^= _qr_gf_mul(coef, factor)
    return res


def qr_matrix(text: str) -> list:
    """The QR symbol for text as rows of booleans (True = dark), without the quiet zone."""
    data = text.encode("utf-8")
    for ver in range(1, 41):
        cap = _qr_data_codewords(ver) * 8
        used = 4 + (8 if ver <= 9 else 16) + 8 * len(data)
        if used <= cap:
            break
    else:
        raise ValueError("text too long for a QR code")
    bits = []
    def put(val, n):
        bits.extend((val >> i) & 1 for i in reversed(range(n)))
    put(0x4, 4)
    put(len(data), 8 if ver <= 9 else 16)
    for b in data:
        put(b, 8)
    put(0, min(4, cap - len(bits)))
    put(0, -len(bits) % 8)
    pad = 0xEC
    while len(bits) < cap:
        put(pad, 8)
        pad ^= 0xEC ^ 0x11
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    # split into blocks, add error correction, interleave
    nblocks, eccn = _QR_BLOCKS[ver], _QR_ECC_PER_BLOCK[ver]
    raw = _qr_raw_modules(ver) // 8
    nshort = nblocks - raw % nblocks
    short_len = raw // nblocks
    div = _qr_rs_divisor(eccn)
    blocks, k = [], 0
    for i in range(nblocks):
        dlen = short_len - eccn + (0 if i < nshort else 1)
        dat = words[k:k + dlen]
        k += dlen
        ecc = _qr_rs_remainder(dat, div)
        if i < nshort:
            dat = dat + [0]
        blocks.append(dat + ecc)
    final = []
    for i in range(len(blocks[0])):
        for j, blk in enumerate(blocks):
            if i != short_len - eccn or j >= nshort:
                final.append(blk[i])
    size = ver * 4 + 17
    mod = [[False] * size for _ in range(size)]
    fn = [[False] * size for _ in range(size)]
    def setf(x, y, dark):
        mod[y][x] = dark
        fn[y][x] = True
    for i in range(size):  # timing
        setf(6, i, i % 2 == 0)
        setf(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):  # finders
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < size and 0 <= y < size:
                    setf(x, y, max(abs(dx), abs(dy)) not in (2, 4))
    if ver > 1:  # alignment patterns
        n = ver // 7 + 2
        step = (ver * 8 + n * 3 + 5) // (n * 4 - 4) * 2
        pos = [6] + [size - 7 - i * step for i in reversed(range(n - 1))]
        for i, a in enumerate(pos):
            for j, b in enumerate(pos):
                if (i, j) in ((0, 0), (0, n - 1), (n - 1, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        setf(a + dx, b + dy, max(abs(dx), abs(dy)) != 1)
    def draw_format(mask):
        d = (0 << 3) | mask  # level M = 00
        rem = d
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        b = ((d << 10) | rem) ^ 0x5412
        g = lambda i: ((b >> i) & 1) != 0
        for i in range(6):
            setf(8, i, g(i))
        setf(8, 7, g(6)); setf(8, 8, g(7)); setf(7, 8, g(8))
        for i in range(9, 15):
            setf(14 - i, 8, g(i))
        for i in range(8):
            setf(size - 1 - i, 8, g(i))
        for i in range(8, 15):
            setf(8, size - 15 + i, g(i))
        setf(8, size - 8, True)
    draw_format(0)  # reserve the format areas
    if ver >= 7:
        rem = ver
        for _ in range(12):
            rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
        b = (ver << 12) | rem
        for i in range(18):
            bit = ((b >> i) & 1) != 0
            a, c = size - 11 + i % 3, i // 3
            setf(a, c, bit)
            setf(c, a, bit)
    # data, in the zigzag order
    i = 0
    right = size - 1
    while right >= 1:
        if right == 6:
            right = 5
        for vert in range(size):
            for j in range(2):
                x = right - j
                upward = ((right + 1) & 2) == 0
                y = size - 1 - vert if upward else vert
                if not fn[y][x] and i < len(final) * 8:
                    mod[y][x] = ((final[i >> 3] >> (7 - (i & 7))) & 1) != 0
                    i += 1
        right -= 2
    masks = (lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
             lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
             lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
             lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0)
    def apply(m):
        f = masks[m]
        for y in range(size):
            for x in range(size):
                if not fn[y][x] and f(x, y):
                    mod[y][x] = not mod[y][x]
    def penalty():
        p = 0
        lines = mod + [list(c) for c in zip(*mod)]
        for line in lines:  # runs of five or more, and finder-like patterns
            run, prev = 0, None
            for v in line:
                if v == prev:
                    run += 1
                    if run == 5:
                        p += 3
                    elif run > 5:
                        p += 1
                else:
                    run, prev = 1, v
            s = "".join("1" if v else "0" for v in line)
            for pat in ("10111010000", "00001011101"):
                p += 40 * sum(1 for k in range(len(s) - 10) if s[k:k + 11] == pat)
        for y in range(size - 1):  # 2x2 blocks
            for x in range(size - 1):
                if mod[y][x] == mod[y][x + 1] == mod[y + 1][x] == mod[y + 1][x + 1]:
                    p += 3
        dark = sum(map(sum, mod))
        total = size * size
        p += 10 * ((abs(dark * 20 - total * 10) + total - 1) // total - 1)
        return p
    best, best_p = 0, None
    for m in range(8):
        apply(m)
        draw_format(m)
        p = penalty()
        if best_p is None or p < best_p:
            best, best_p = m, p
        apply(m)
    apply(best)
    draw_format(best)
    return mod


def qr_svg_data_uri(text: str) -> str:
    """The QR code for text as a data: URI holding an SVG image, with a four-module quiet zone."""
    m = qr_matrix(text)
    n = len(m) + 8
    path = "".join("M%d %dh1v1h-1z" % (x + 4, y + 4) for y, row in enumerate(m) for x, v in enumerate(row) if v)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" shape-rendering="crispEdges">'
           '<rect width="%d" height="%d" fill="#fff"/><path fill="#000" d="%s"/></svg>') % (n, n, n, n, path)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("ascii")).decode("ascii")


def totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def totp_code(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, step.to_bytes(8, "big"), hashlib.sha1).digest()
    off = digest[-1] & 15
    return "%06d" % ((int.from_bytes(digest[off:off + 4], "big") & 0x7FFFFFFF) % 1000000)


def totp_match(secret: str, code: str, last_step: int, t: float | None = None) -> int:
    """The time step the code belongs to (one step of clock drift either way), or 0. A step is never accepted twice."""
    code = re.sub(r"\s", "", str(code or ""))
    if not re.fullmatch(r"\d{6}", code):
        return 0
    step = int((time.time() if t is None else t) // 30)
    for s in (step - 1, step, step + 1):
        if s > (last_step or 0) and hmac.compare_digest(totp_code(secret, s), code):
            return s
    return 0


# ----------------------------------------------------------------------------- rcon

PREFIX = b"\xff\xff\xff\xff"


# ---------------------------------------------------------------- staff certificates (0.38.0+)
# The portal signs each active staff key with a root Ed25519 key into a certificate the game sends with its staff
# answer; every server checks it offline against the root public keys built into the game (tcp_staff_cert.h).
# Pure-Python Ed25519 (RFC 8032 5.1 reference algorithm): a few signatures a day, so speed does not matter.
_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _sha512(b: bytes) -> bytes:
    return hashlib.sha512(b).digest()


def _add(a, b):
    A = (a[1] - a[0]) * (b[1] - b[0]) % _P
    B = (a[1] + a[0]) * (b[1] + b[0]) % _P
    C = 2 * a[3] * b[3] * _D % _P
    Dd = 2 * a[2] * b[2] % _P
    E, F, G, H = B - A, Dd - C, Dd + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _mul(s: int, pt):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _add(q, pt)
        pt = _add(pt, pt)
        s >>= 1
    return q


def _recover_x(y: int, sign: int):
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _I % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


_GY = 4 * pow(5, _P - 2, _P) % _P
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _compress(pt) -> bytes:
    zinv = pow(pt[2], _P - 2, _P)
    x, y = pt[0] * zinv % _P, pt[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, 'little')


def _decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, 'little')
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _expand(seed: bytes):
    if len(seed) != 32:
        raise ValueError('Ed25519 seed must be 32 bytes')
    h = _sha512(seed)
    a = int.from_bytes(h[:32], 'little')
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def ed25519_public(seed: bytes) -> bytes:
    a, _ = _expand(seed)
    return _compress(_mul(a, _G))


def ed25519_sign(seed: bytes, msg: bytes) -> bytes:
    a, prefix = _expand(seed)
    A = _compress(_mul(a, _G))
    r = int.from_bytes(_sha512(prefix + msg), 'little') % _L
    R = _compress(_mul(r, _G))
    h = int.from_bytes(_sha512(R + A + msg), 'little') % _L
    s = (r + h * a) % _L
    return R + int.to_bytes(s, 32, 'little')


def ed25519_verify(public: bytes, msg: bytes, sig: bytes) -> bool:
    if len(public) != 32 or len(sig) != 64:
        return False
    A = _decompress(public)
    R = _decompress(sig[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(sig[32:], 'little')
    if s >= _L:
        return False
    h = int.from_bytes(_sha512(sig[:32] + public + msg), 'little') % _L
    sB = _mul(s, _G)
    hA = _mul(h, A)
    lhs, rhs = sB, _add(R, hA)
    return (lhs[0] * rhs[2] - rhs[0] * lhs[2]) % _P == 0 and (lhs[1] * rhs[2] - rhs[1] * lhs[2]) % _P == 0


STAFF_CERT_TAG = "TCPSTAFFCERT1"


def gamecheck_message(nonce: str, play: bool, t: int) -> bytes:
    """What a start-check answer signs: the game's own random nonce, so an old or forged answer never passes."""
    return ("TCP-GAMECHECK-1\n%s\n%s\n%d" % (nonce, "play" if play else "banned", t)).encode()


def staff_cert_message(root_id: str, kid: str, role: int, issued: int, expires: int, pub_hex: str, name_hex: str) -> bytes:
    return ("TCP-STAFF-CERT-1\n%s\n%s\n%d\n%d\n%d\n%s\n%s" % (root_id, kid, role, issued, expires, pub_hex, name_hex)).encode()


def load_staff_root(cfg: dict):
    """(root id, seed, public) from the systemd credential 'staff-root' or cfg staff_root_file: one line
    "TCPSTAFFROOT1 <id> <64 hex seed>". None when not set up: the portal then issues no certificates."""
    names = []
    cred = os.environ.get("CREDENTIALS_DIRECTORY")
    if cred:
        names.append(Path(cred) / "staff-root")
    if cfg.get("staff_root_file"):
        names.append(Path(cfg["staff_root_file"]))
    for p in names:
        try:
            parts = p.read_text(encoding="ascii").split()
        except OSError:
            continue
        if len(parts) == 3 and parts[0] == "TCPSTAFFROOT1" and re.fullmatch(r"[A-Za-z0-9_-]{1,15}", parts[1]) \
                and re.fullmatch(r"[0-9a-f]{64}", parts[2]):
            seed = bytes.fromhex(parts[2])
            return parts[1], seed, ed25519_public(seed)
        log.warning("staff root in %s is not a TCPSTAFFROOT1 line; no certificates", p)
    return None


class RconError(Exception):
    pass


def read_password(server: dict) -> str:
    names = []
    cred = os.environ.get("CREDENTIALS_DIRECTORY")
    if cred and server.get("rcon_credential"):
        names.append(Path(cred) / server["rcon_credential"])
    if server.get("rcon_password_file"):
        names.append(Path(server["rcon_password_file"]))
    for p in names:
        try:
            text = p.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        m = re.search(r'rconpassword\s+"?([^"\s]+)"?', text)
        pw = m.group(1) if m else (text.splitlines()[0].strip() if text else "")
        if pw:
            return pw
    if server.get("rcon_password"):          # tests and local runs only
        return str(server["rcon_password"])
    raise RconError("no rcon password configured for %s" % server.get("key"))


def rcon(host: str, port: int, password: str, command: str, timeout: float = 1.5, settle: float = 0.2) -> str:
    """Sends one console command and returns what the server printed, colour codes removed."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    s = socket.socket(family, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)
        s.sendto(PREFIX + ("rcon %s %s" % (password, command)).encode("latin-1", "replace"), (host, int(port)))
        chunks = []
        try:
            while True:
                data, _ = s.recvfrom(65536)
                chunks.append(data)
                s.settimeout(settle)
        except socket.timeout:
            pass
    finally:
        s.close()
    if not chunks:
        raise RconError("no answer from %s:%s" % (host, port))
    out = []
    for data in chunks:
        if data.startswith(PREFIX + b"print\n"):
            out.append(data[len(PREFIX) + 6:].decode("latin-1"))
    text = "".join(out)
    low = text.lower()
    if "bad rconpassword" in low or "rcon is locked" in low or "no rconpassword set" in low:
        raise RconError("the server refused the rcon password")
    return text


STATUS_LINE = re.compile(r"^\s*(\d+)\s+(-?\d+)\s+(\d+|CNCT|ZMBI|DEMO)\s+(.*?)\s+(\d+)\s+(\S+)\s+(\d+)\s+(\d+)(?:\s+(-?\d+))?\s*$")


def parse_status(text: str) -> dict:
    out = {"map": "", "players": {}}
    for line in text.splitlines():
        if re.match(r"^map\s*:", line, re.I):
            out["map"] = line.split(":", 1)[1].strip()
            continue
        m = STATUS_LINE.match(line)
        if m:
            addr = m.group(6)
            slot = int(m.group(1))
            ping = m.group(3)
            out["players"][slot] = {
                "slot": slot, "score": int(m.group(2)),
                "ping": int(ping) if ping.isdigit() else -1,
                "state": "active" if ping.isdigit() else ping.lower(),
                "name": plain(m.group(4)).strip(), "address": addr,
                "bot": addr.lower() == "bot",
                "connected_s": int(m.group(9)) // 1000 if m.group(9) else 0,
            }
    return out


def parse_acstatus(text: str) -> dict:
    """acstatus: EAC mode in the header, then per slot the EAC state, file check and account id."""
    out = {"eac_mode": "", "players": {}}
    last = None
    for line in text.splitlines():
        m = re.search(r"EAC (required|on|off)", line)
        if line.startswith("anti-cheat") and m:
            out["eac_mode"] = m.group(1)
            continue
        m = re.match(r"^\s*(\d+) (.{16}) (.*)$", line)
        if m and not line.strip().startswith("slot"):
            slot = int(m.group(1))
            rest = m.group(3)
            if "(bot or host" in rest:
                out["players"][slot] = {"eac": "exempt"}
            else:
                state = rest[:12].strip()
                files = rest[13:37].strip()
                det = re.search(r"(\d+)\s*/\s*(\d+)\s+(\d+)\s*(.*)$", rest[37:])
                out["players"][slot] = {"eac": state, "files": files,
                                        "detections": int(det.group(3)) if det else 0,
                                        "last_detection": det.group(4).strip() if det else ""}
            last = slot
            continue
        m = re.match(r"^\s+account id (\S+)", line)
        if m and last is not None and last in out["players"]:
            out["players"][last]["puid"] = m.group(1)
    return out


def parse_info(text: str) -> dict:
    """serverinfo / dumpuser: 'key<spaces>value' lines."""
    info = {}
    for line in text.splitlines():
        m = re.match(r"^(\S+)\s+(.*?)\s*$", line)
        if m and not line.startswith(("Server info", "userinfo", "--")):
            info[m.group(1)] = m.group(2)
    return info


STAFF_PLAYER = re.compile(r"^TCP_STAFF_PLAYER (.*?) name=(.*)$")


def parse_staff_players(text: str) -> dict:
    out = {"match": {}, "players": {}}
    for line in text.splitlines():
        if line.startswith("TCP_STAFF_MATCH "):
            out["match"] = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)}
            continue
        m = STAFF_PLAYER.match(line.strip())
        if m:
            fields = dict(re.findall(r"(\w+)=(\S+)", m.group(1)))
            row = {k: (int(v) if re.fullmatch(r"-?\d+", v) else v) for k, v in fields.items()}
            row["name"] = plain(m.group(2)).strip()
            out["players"][int(row["slot"])] = row
    return out


NATIVE_PLAYER = re.compile(r"^TCP_NATIVE_PLAYER (.*)$")


def parse_native_status(text: str) -> dict:
    """The game's own tcp_status: per slot position, health, shots and hits on this map (0.35.0 and later)."""
    out = {}
    for line in text.splitlines():
        m = NATIVE_PLAYER.match(line.strip())
        if not m:
            continue
        kv = dict(re.findall(r"(\w+)=(\S+)", m.group(1)))
        try:
            x, y, z = (float(v) for v in kv.get("xyz", "0,0,0").split(","))
            out[int(kv["slot"])] = {"x": x, "y": y, "z": z, "hp": int(kv.get("hp", 0)), "shots": int(kv.get("shots", 0)),
                                    "hits": int(kv.get("hits", 0)), "kills": int(kv.get("kills", 0)),
                                    "deaths": int(kv.get("deaths", 0)), "team": int(kv.get("team", 0)),
                                    "begun": kv.get("begun") == "1"}
        except (KeyError, ValueError):
            continue
    return out


CVAR_REPLY = re.compile(r'"([A-Za-z0-9_]+)" is:\s*"(.*?)(?:\^7)?"')


def parse_cvar(text: str) -> str | None:
    m = CVAR_REPLY.search(text or "")
    return m.group(2) if m else None


BAN_LINE = re.compile(r"^#(\d+)\s+ip\s+(\S+)\s+guid\s+(\S+)\s+name\s+'(.*?)'\s+added\s+(\S+(?: \S+)?)(.*)$")


def parse_banlist(text: str) -> list:
    bans = []
    for line in text.splitlines():
        m = BAN_LINE.match(line.strip())
        if not m:
            continue
        rest = m.group(6)
        left = re.search(r"\((\d+) min left\)", rest)
        reason = re.search(r"reason:\s*(.*)$", rest)
        puid = re.search(r"\bpuid (\S+)", rest)
        bans.append({"number": int(m.group(1)), "ip": "" if m.group(2) == "-" else m.group(2),
                     "guid": "" if m.group(3) == "-" else m.group(3), "name": m.group(4),
                     "added": m.group(5).strip(), "minutes_left": int(left.group(1)) if left else 0,
                     "reason": reason.group(1).strip() if reason else "", "puid": puid.group(1) if puid else ""})
    return bans


# ----------------------------------------------------------------------------- storage

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, discord_id TEXT, name TEXT, avatar TEXT, role TEXT,
  csrf TEXT, created INTEGER, seen INTEGER, checked INTEGER, token TEXT, ip TEXT);
CREATE TABLE IF NOT EXISTS staff(discord_id TEXT PRIMARY KEY, name TEXT, role TEXT, note TEXT, added_by TEXT,
  created INTEGER, last_login INTEGER);
CREATE TABLE IF NOT EXISTS staff_keys(id TEXT PRIMARY KEY, discord_id TEXT, name TEXT, public TEXT, created INTEGER,
  revoked INTEGER DEFAULT 0, revoked_by TEXT);
CREATE INDEX IF NOT EXISTS staff_keys_owner ON staff_keys(discord_id);
CREATE TABLE IF NOT EXISTS staff_key_codes(code_hash TEXT PRIMARY KEY, discord_id TEXT, name TEXT, expires INTEGER);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER, discord_id TEXT, staff TEXT,
  role TEXT, action TEXT, server TEXT, target TEXT, target_pid TEXT, detail TEXT, ok INTEGER, result TEXT);
CREATE INDEX IF NOT EXISTS audit_at ON audit(at);
CREATE INDEX IF NOT EXISTS audit_pid ON audit(target_pid);
CREATE TABLE IF NOT EXISTS sightings(pid TEXT, guid TEXT, name TEXT, ip TEXT, puid TEXT, server TEXT,
  first_seen INTEGER, last_seen INTEGER, PRIMARY KEY(pid, name, ip, server));
CREATE INDEX IF NOT EXISTS sightings_name ON sightings(name);
CREATE INDEX IF NOT EXISTS sightings_ip ON sightings(ip);
CREATE INDEX IF NOT EXISTS sightings_seen ON sightings(last_seen);
CREATE TABLE IF NOT EXISTS bans(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, guid TEXT, ip TEXT, puid TEXT,
  name TEXT, reason TEXT, created INTEGER, expires INTEGER, by_id TEXT, by_name TEXT, active INTEGER DEFAULT 1,
  lifted INTEGER, lifted_by TEXT, lift_reason TEXT);
CREATE INDEX IF NOT EXISTS bans_active ON bans(active);
CREATE TABLE IF NOT EXISTS mutes(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, guid TEXT, name TEXT, reason TEXT,
  created INTEGER, expires INTEGER, by_name TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS warnings(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, name TEXT, text TEXT,
  created INTEGER, by_name TEXT, server TEXT);
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, text TEXT, created INTEGER, by_name TEXT);
CREATE TABLE IF NOT EXISTS chat(id INTEGER PRIMARY KEY AUTOINCREMENT, server TEXT, at INTEGER, slot INTEGER,
  team INTEGER, pid TEXT, name TEXT, text TEXT, kind TEXT);
CREATE INDEX IF NOT EXISTS chat_server ON chat(server, id);
CREATE INDEX IF NOT EXISTS chat_pid ON chat(pid);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, file TEXT UNIQUE,
  server TEXT, received INTEGER, data TEXT, target_pid TEXT, target_name TEXT, status TEXT DEFAULT 'open',
  claimed_by TEXT, resolution TEXT, updated INTEGER);
CREATE INDEX IF NOT EXISTS reports_status ON reports(status);
CREATE TABLE IF NOT EXISTS punishments(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, name TEXT, offence TEXT, step TEXT,
  created INTEGER, by_name TEXT, server TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS punishments_pid ON punishments(pid, offence);
CREATE TABLE IF NOT EXISTS filters(id INTEGER PRIMARY KEY AUTOINCREMENT, pattern TEXT, kind TEXT, action TEXT, minutes INTEGER,
  note TEXT, active INTEGER DEFAULT 1, created INTEGER, by_name TEXT, hits INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS watchlist(pid TEXT PRIMARY KEY, name TEXT, reason TEXT, created INTEGER, by_name TEXT);
CREATE TABLE IF NOT EXISTS templates(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, title TEXT, text TEXT, created INTEGER, by_name TEXT);
CREATE TABLE IF NOT EXISTS schedule(id INTEGER PRIMARY KEY AUTOINCREMENT, server TEXT, action TEXT, arg TEXT, next_at INTEGER,
  every_min INTEGER, until INTEGER, created INTEGER, by_name TEXT, by_id TEXT, active INTEGER DEFAULT 1, runs INTEGER DEFAULT 0,
  last_run INTEGER, last_result TEXT);
CREATE TABLE IF NOT EXISTS events(server TEXT PRIMARY KEY, started INTEGER, by_name TEXT, saved TEXT, preset TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS cvar_changes(id INTEGER PRIMARY KEY AUTOINCREMENT, server TEXT, cvar TEXT, old TEXT, new TEXT,
  at INTEGER, by_name TEXT, kind TEXT, kept INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS cvar_overrides(server TEXT, cvar TEXT, value TEXT, set_at INTEGER, by_name TEXT, PRIMARY KEY(server, cvar));
CREATE TABLE IF NOT EXISTS totp(discord_id TEXT PRIMARY KEY, secret TEXT, enabled INTEGER DEFAULT 0, created INTEGER, last_step INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, at INTEGER, kind TEXT, title TEXT, text TEXT,
  pid TEXT, server TEXT, sent INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS alerts_key ON alerts(key, at);
CREATE TABLE IF NOT EXISTS flags(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, name TEXT, server TEXT, kind TEXT, detail TEXT, at INTEGER);
CREATE INDEX IF NOT EXISTS flags_pid ON flags(pid, at);
CREATE TABLE IF NOT EXISTS suspicion(pid TEXT PRIMARY KEY, name TEXT, score INTEGER, reasons TEXT, updated INTEGER, peak INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS peaks(day TEXT, server TEXT, peak INTEGER, PRIMARY KEY(day, server));
CREATE TABLE IF NOT EXISTS appeals(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, ban_id INTEGER, pid TEXT, name TEXT, text TEXT,
  contact TEXT, created INTEGER, status TEXT DEFAULT 'open', answer TEXT, answered_by TEXT, updated INTEGER, from_hash TEXT);
CREATE INDEX IF NOT EXISTS appeals_code ON appeals(code);
CREATE INDEX IF NOT EXISTS reports_target ON reports(target_pid);
CREATE INDEX IF NOT EXISTS bans_pid ON bans(pid);
CREATE INDEX IF NOT EXISTS mutes_pid ON mutes(pid, active);
CREATE INDEX IF NOT EXISTS warnings_pid ON warnings(pid);
CREATE INDEX IF NOT EXISTS sightings_puid ON sightings(puid);
CREATE INDEX IF NOT EXISTS alerts_at ON alerts(at);
CREATE TABLE IF NOT EXISTS undo(audit_id INTEGER PRIMARY KEY, kind TEXT, ref INTEGER, by_id TEXT, expires INTEGER, done INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS samples(at INTEGER, server TEXT, online INTEGER, humans INTEGER, bots INTEGER, map TEXT);
CREATE INDEX IF NOT EXISTS samples_at ON samples(at);
CREATE TABLE IF NOT EXISTS player_sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, server TEXT, name TEXT, joined INTEGER,
  left_at INTEGER);
CREATE INDEX IF NOT EXISTS player_sessions_pid ON player_sessions(pid, joined);
CREATE INDEX IF NOT EXISTS player_sessions_open ON player_sessions(left_at);
CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, status TEXT DEFAULT 'open', pid TEXT, name TEXT,
  summary TEXT, assignee TEXT, created INTEGER, created_by TEXT, updated INTEGER, outcome TEXT);
CREATE INDEX IF NOT EXISTS cases_status ON cases(status, updated);
CREATE INDEX IF NOT EXISTS cases_pid ON cases(pid);
CREATE TABLE IF NOT EXISTS case_items(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER, at INTEGER, by_name TEXT, kind TEXT,
  ref INTEGER, text TEXT);
CREATE INDEX IF NOT EXISTS case_items_case ON case_items(case_id);
CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER, pid TEXT, kind TEXT, title TEXT, file TEXT,
  mime TEXT, size INTEGER, sha256 TEXT, text TEXT, at INTEGER, by_name TEXT, deleted INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS evidence_case ON evidence(case_id);
CREATE INDEX IF NOT EXISTS evidence_pid ON evidence(pid);
CREATE TABLE IF NOT EXISTS duty(discord_id TEXT PRIMARY KEY, name TEXT, since INTEGER, until INTEGER);
CREATE TABLE IF NOT EXISTS push_subs(endpoint TEXT PRIMARY KEY, discord_id TEXT, name TEXT, created INTEGER, last_ok INTEGER,
  fails INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS ac_queue(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, pid TEXT, name TEXT, server TEXT, at INTEGER,
  detail TEXT, score INTEGER DEFAULT 0, status TEXT DEFAULT 'open', by_name TEXT, resolved INTEGER, note TEXT);
CREATE INDEX IF NOT EXISTS ac_queue_status ON ac_queue(status, at);
CREATE INDEX IF NOT EXISTS ac_queue_pid ON ac_queue(pid, kind);
CREATE TABLE IF NOT EXISTS ban_ids(ban_id INTEGER, kind TEXT, value TEXT, added INTEGER, via TEXT,
  PRIMARY KEY(ban_id, kind, value));
CREATE INDEX IF NOT EXISTS ban_ids_value ON ban_ids(kind, value);
CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY AUTOINCREMENT, ids TEXT UNIQUE, pid TEXT, kid TEXT, puid TEXT,
  hw TEXT, iptag TEXT, name TEXT, build TEXT, first_seen INTEGER, last_seen INTEGER, checks INTEGER DEFAULT 0, blocked INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS devices_pid ON devices(pid);
CREATE INDEX IF NOT EXISTS devices_name ON devices(name);
CREATE INDEX IF NOT EXISTS devices_seen ON devices(last_seen);
"""

# Columns added after 1.0.0, applied to an existing database on start.
MIGRATIONS = [
    "ALTER TABLE bans ADD COLUMN appeal_code TEXT",
    "ALTER TABLE sessions ADD COLUMN mfa INTEGER DEFAULT 0",
    "ALTER TABLE chat ADD COLUMN flag TEXT",
    "ALTER TABLE mutes ADD COLUMN server TEXT",
    "CREATE INDEX IF NOT EXISTS bans_code ON bans(appeal_code)",
    "ALTER TABLE staff ADD COLUMN perms_add TEXT",
    "ALTER TABLE staff ADD COLUMN perms_remove TEXT",
    "ALTER TABLE bans ADD COLUMN game INTEGER DEFAULT 0",     # 1.7.0: banned from the whole game, not only our servers
]


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript(SCHEMA)
            for sql in MIGRATIONS:
                try:
                    self.db.execute(sql)
                except sqlite3.OperationalError:       # the column is already there
                    pass

    def q(self, sql: str, args=()) -> list:
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def one(self, sql: str, args=()):
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def x(self, sql: str, args=()) -> int:
        with self.lock:
            cur = self.db.execute(sql, args)
            return cur.lastrowid

    on_audit = None

    def audit(self, who: dict, action: str, server: str = "", target: str = "", pid: str = "",
              detail: str = "", ok: bool = True, result: str = "") -> int:
        if self.on_audit:
            self.on_audit(action)
        return self.x("INSERT INTO audit(at,discord_id,staff,role,action,server,target,target_pid,detail,ok,result) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
               (now(), who.get("discord_id", ""), who.get("name", "system"), who.get("role", ""), action, server,
                target, pid, detail[:500], 1 if ok else 0, (result or "")[:500]))


# ----------------------------------------------------------------------------- live servers

class GameServer:
    """One game server: rcon, the latest snapshot and what the portal knows about its players."""

    def __init__(self, cfg: dict, store: Store):
        self.cfg = cfg
        self.key = cfg["key"]
        self.name = cfg.get("name", self.key)
        self.host = cfg.get("host", "127.0.0.1")
        self.port = int(cfg["port"])
        self.store = store
        self.lock = threading.RLock()
        self.cmd_lock = threading.Lock()
        self.snapshot = {"key": self.key, "name": self.name, "online": False, "players": [], "updated": 0}
        self.guids = {}          # slot -> (connect marker, guid, ip, userinfo name)
        self.names = {}          # slot -> last known name (chat lines arrive after a player leaves too)
        self.caps = None         # TCP_STAFF_CAPS features, or [] on a server without the staff commands
        self.caps_at = 0
        self.info = {}
        self.info_at = 0
        self.error = ""
        self.positions = {}
        self.positions_at = 0

    # -- rcon
    def run(self, command: str, timeout: float = 1.5, settle: float = 0.2) -> str:
        with self.cmd_lock:                      # one command at a time per server: replies never mix
            return rcon(self.host, self.port, read_password(self.cfg), command, timeout=timeout, settle=settle)

    def has(self, feature: str) -> bool:
        return bool(self.caps) and feature in self.caps

    def cvar(self, name: str) -> str | None:
        """A cvar's current value over rcon, or None when the server does not know it."""
        # One short packet (the reply fits the 240-byte redirect buffer) and every query has its own socket, so a short
        # settle is enough: the Settings page reads 60+ of these one after the other.
        return parse_cvar(self.run(name, settle=0.02))

    def set_cvar(self, name: str, value: str) -> str:
        return self.run('set %s "%s"' % (name, value), settle=0.06)

    # -- polling
    def poll(self) -> None:
        t = now()
        try:
            if self.caps is None or t - self.caps_at > 300:
                text = self.run("tcp_staffcaps")
                m = re.search(r"TCP_STAFF_CAPS (\d+) (.*)", text)
                self.caps = m.group(2).split() if m else []
                self.caps_at = t
            if t - self.info_at > 30 or not self.info:
                self.info = parse_info(self.run("serverinfo"))
                self.info_at = t
            status = parse_status(self.run("status"))
            ac = parse_acstatus(self.run("acstatus"))
            staff = parse_staff_players(self.run("tcp_players")) if self.has("players") else {"match": {}, "players": {}}
            native = parse_native_status(self.run("tcp_status")) if status["players"] else {}
        except (RconError, OSError) as e:
            with self.lock:
                self.error = str(e)
                self.snapshot = dict(self.snapshot, online=False, error=self.error, updated=t)
            return
        players = []
        for slot, p in sorted(status["players"].items()):
            extra = staff["players"].get(slot, {})
            acp = ac["players"].get(slot, {})
            bot = p["bot"] or bool(extra.get("bot"))
            row = {
                "slot": slot, "name": extra.get("name") or p["name"], "score": p["score"], "ping": p["ping"],
                "state": p["state"], "bot": bot, "connected_s": p["connected_s"],
                "team": extra.get("team"), "spectator": bool(extra.get("spec")), "alive": bool(extra.get("alive")),
                "muted_s": extra.get("muted", 0), "kills": extra.get("kills"), "deaths": extra.get("deaths"),
                "team_kills": extra.get("team_kills"), "damage": extra.get("damage"),
                "eac": acp.get("eac", ""), "files": acp.get("files", ""), "detections": acp.get("detections", 0),
                "puid": acp.get("puid", ""), "ip": "" if bot else host_of(p["address"]),
            }
            live = native.get(slot)
            if live:
                row.update({"shots": live["shots"], "hits": live["hits"], "hp": live["hp"]})
                if row["kills"] is None:
                    row["kills"], row["deaths"] = live["kills"], live["deaths"]
                if row["team"] is None:
                    row["team"] = live["team"]
            if not bot:
                self._identify(slot, row)
            self.names[slot] = row["name"]
            players.append(row)
        live = {p["slot"] for p in players}
        for slot in list(self.guids):
            if slot not in live:
                del self.guids[slot]
        snap = {
            "key": self.key, "name": self.name, "online": True, "updated": t, "error": "",
            "address": self.cfg.get("public_address", "%s:%d" % (self.host, self.port)),
            "kind": self.cfg.get("kind", "official"), "unit": self.cfg.get("unit", ""),
            "hostname": plain(self.info.get("sv_hostname", self.name)),
            "map": status["map"] or self.info.get("mapname", ""),
            "mode": self.info.get("tcp_mode", ""), "max_players": int(self.info.get("sv_maxclients", "0") or 0),
            "ranked": self.info.get("tcp_ranked", "") == "1" or "Ranked" in self.name and "Unranked" not in self.name,
            "eac": ac.get("eac_mode") or {"2": "required", "1": "on"}.get(self.info.get("sv_eac", "0"), "off"),
            "needpass": self.info.get("g_needpass", "0") == "1",
            "rotation": self.info.get("sv_mapRotation", ""),
            "match": staff.get("match", {}), "staff_commands": self.caps or [],
            "humans": sum(1 for p in players if not p["bot"]), "bots": sum(1 for p in players if p["bot"]),
            "players": players,
        }
        with self.lock:
            self.error = ""
            self.snapshot = snap
            # positions stay out of the snapshot: only the live map asks for them, and that view is audited
            self.positions = {slot: dict(v, name=next((p["name"] for p in players if p["slot"] == slot), ""))
                              for slot, v in native.items()}
            self.positions_at = t
        self._reapply_mutes(players)

    def _identify(self, slot: int, row: dict) -> None:
        marker = (row["ip"], row["name"]) if not row["connected_s"] else (row["ip"],)
        known = self.guids.get(slot)
        if not known or known[0] != marker:
            try:
                info = parse_info(self.run("dumpuser %d" % slot))
            except RconError:
                info = {}
            guid = info.get("cl_guid", "")
            ip = host_of(info.get("ip", "")) or row["ip"]
            self.guids[slot] = known = (marker, guid, ip)
        _, guid, ip = known
        row["guid"] = guid
        row["pid"] = player_pid(guid)
        row["ip"] = ip or row["ip"]
        if row["pid"]:
            t = now()
            self.store.x("INSERT INTO sightings(pid,guid,name,ip,puid,server,first_seen,last_seen) VALUES(?,?,?,?,?,?,?,?) "
                         "ON CONFLICT(pid,name,ip,server) DO UPDATE SET last_seen=excluded.last_seen, "
                         "puid=CASE WHEN excluded.puid<>'' THEN excluded.puid ELSE sightings.puid END, guid=excluded.guid",
                         (row["pid"], guid, row["name"], row["ip"], row.get("puid", ""), self.key, t, t))

    def _reapply_mutes(self, players: list) -> None:
        """Mutes live in the game only until the map changes; the portal puts them back."""
        if not self.has("mute"):
            return
        t = now()
        for p in players:
            if p["bot"] or not p.get("pid") or p.get("muted_s"):
                continue
            m = self.store.one("SELECT * FROM mutes WHERE pid=? AND active=1 AND (expires=0 OR expires>?) "
                               "ORDER BY id DESC LIMIT 1", (p["pid"], t))
            if m:
                left = 0 if not m["expires"] else max(1, (m["expires"] - t + 59) // 60)
                try:
                    self.run("mute %d %d %s" % (p["slot"], left, safe_arg(m["reason"], 80)))
                    self.run("voicemute %d" % p["slot"])
                except RconError:
                    pass

    def slot_player(self, slot: int) -> dict | None:
        with self.lock:
            for p in self.snapshot.get("players", []):
                if p["slot"] == slot:
                    return dict(p)
        return None

    def view(self) -> dict:
        with self.lock:
            return json.loads(json.dumps(self.snapshot))


# ----------------------------------------------------------------------------- moderation core
# Player actions, bans, the punishment ladder and undo. The API, the chat filter, the AFK and team-kill watch
# and the scheduler all go through these, so every path is checked and audited the same way.

class Moderation:
    def act(self, who: dict, srv: GameServer, slot: int, p: dict, act: str, reason: str = "", length: str = "",
            team: str = "") -> tuple:
        """kick | warn | mute | unmute | move. Returns (server answer, audit id)."""
        reason = safe_arg(reason, 100)
        detail, result, mute_id = reason, "", None
        if act == "kick":
            if not reason:
                raise ApiError(400, "Give a reason. The player sees it.")
            result = srv.run("clientkick %d %s" % (slot, reason))
        elif act == "warn":
            if not reason:
                raise ApiError(400, "Write the warning.")
            if not srv.has("warn"):
                raise ApiError(409, "This server needs the 0.36.0 server update for private warnings.")
            result = srv.run("warn %d %s" % (slot, reason))
            self.store.x("INSERT INTO warnings(pid,name,text,created,by_name,server) VALUES(?,?,?,?,?,?)",
                         (p.get("pid", ""), p["name"], reason, now(), who["name"], srv.key))
        elif act in ("mute", "unmute"):
            if not srv.has("mute"):
                raise ApiError(409, "This server needs the 0.36.0 server update for mutes.")
            if act == "mute":
                minutes = duration_minutes(length or "30m")
                detail = "%s, %s" % (engine_length(minutes) or "until lifted", reason)
                result = srv.run("mute %d %d %s" % (slot, min(minutes, 10080) if minutes else 0, reason))
                srv.run("voicemute %d" % slot)        # 0.36.0 voice chat; an unknown command on older servers
                if p.get("pid"):
                    self.store.x("UPDATE mutes SET active=0 WHERE pid=? AND active=1", (p["pid"],))
                    mute_id = self.store.x("INSERT INTO mutes(pid,guid,name,reason,created,expires,by_name,server) "
                                           "VALUES(?,?,?,?,?,?,?,?)",
                                           (p["pid"], p.get("guid", ""), p["name"], reason, now(),
                                            now() + minutes * 60 if minutes else 0, who["name"], srv.key))
            else:
                result = srv.run("unmute %d" % slot)
                srv.run("voiceunmute %d" % slot)
                if p.get("pid"):
                    self.store.x("UPDATE mutes SET active=0 WHERE pid=? AND active=1", (p["pid"],))
        elif act == "move":
            if team not in ("r", "b", "s"):
                raise ApiError(400, "Pick a team.")
            detail = {"r": "to Terrorists", "b": "to Specops", "s": "to spectators"}[team] + (", " + reason if reason else "")
            if srv.has("putteam"):
                result = srv.run("putteam %d %s" % (slot, team))
            elif team == "s":
                result = srv.run("spectate %d" % slot)
            else:
                raise ApiError(409, "This server needs the 0.36.0 server update to move players between teams.")
        else:
            raise ApiError(400, "Unknown action.")
        ok = "usage:" not in result.lower() and "refused" not in result.lower()
        aid = self.store.audit(who, act, server=srv.key, target=p["name"], pid=p.get("pid", ""), detail=detail,
                               ok=ok, result=plain(result).strip())
        if not ok:
            raise ApiError(409, "The server refused: %s" % plain(result).strip()[:200])
        if mute_id:
            self.undoable(aid, "mute", mute_id, who)
        return plain(result).strip(), aid

    # -- bans
    def ban_text(self, b: dict) -> str:
        """The reason the banned player sees, with the appeal code when appeals are on."""
        reason = safe_arg(b.get("reason", ""), 100)
        code = b.get("appeal_code")
        if not code:
            return reason
        where = re.sub(r"^https?://", "", self.appeal_url())
        return safe_arg("%s - appeal at %s code %s" % (reason[:48], where, code), 120)

    def appeal_url(self) -> str:
        return str(self.cfg.get("appeal_url") or self.cfg.get("public_url", "https://staff.truecombat.eu").rstrip("/") + "/appeal")

    def ban_player(self, who: dict, target: dict, minutes: int, reason: str, ip_ban: bool = True,
                   srv: GameServer | None = None, slot: int | None = None, via: str = "", game: bool = False) -> dict:
        """target: pid, guid, ip, puid, name (and iptag, kid, hw). Applies the ban on every server; srv/slot also kicks
        the player now. game: banned from the whole game, on every identity the portal knows for the player."""
        reason = safe_arg(reason, 100)
        if not reason:
            raise ApiError(400, "Give a reason. The player sees it.")
        if game and not allowed(who.get("role"), "ban.perm") and who.get("role") != "system":
            raise ApiError(403, "Only admins can ban a player from the whole game.")
        if minutes > MOD_BAN_LIMIT or minutes == 0:
            if not allowed(who.get("role"), "ban.perm") and who.get("role") != "system":
                raise ApiError(403, "Moderators can ban for up to 24 hours. Ask an admin for longer bans.")
        b = {k: target.get(k, "") or "" for k in ("pid", "guid", "ip", "puid", "name")}
        if not ip_ban:
            b["ip"] = ""
        code = appeal_code() if self.cfg.get("appeals", True) else ""
        b.update({"reason": reason, "expires": now() + minutes * 60 if minutes else 0, "appeal_code": code})
        bid = self.store.x("INSERT INTO bans(pid,guid,ip,puid,name,reason,created,expires,by_id,by_name,appeal_code) "
                           "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (b["pid"], b["guid"], b["ip"], b["puid"], b["name"], reason, now(), b["expires"],
                            who.get("discord_id", ""), who["name"], code))
        ids = []
        if game:
            self.store.x("UPDATE bans SET game=1 WHERE id=?", (bid,))
            ids = self.ban_identities(target, ip_ban)
            for kind, value in ids:
                self.store.x("INSERT OR IGNORE INTO ban_ids(ban_id,kind,value,added,via) VALUES(?,?,?,?,'staff')",
                             (bid, kind, value, now()))
            self.store.x("UPDATE devices SET blocked=1 WHERE pid=? OR kid IN (SELECT value FROM ban_ids WHERE ban_id=? AND kind='kid')",
                         (b["pid"], bid))
        results = {}
        for key in self.order:
            server = self.servers[key]
            try:
                out = self._apply_ban(server, b, slot if server is srv else None)
                results[key] = plain(" ".join(out)).strip()[:200] or "ok"
            except RconError as e:
                results[key] = "offline, applied at the next sync: %s" % e
        aid = self.store.audit(who, "game ban" if game else "ban", server=srv.key if srv else "", target=b["name"], pid=b["pid"],
                               detail="%s, %s%s%s" % (engine_length(minutes) or "permanent", reason, via,
                                                      ", whole game, %d identities" % len(ids) if game else ""),
                               result=json.dumps(results))
        self.undoable(aid, "ban", bid, who)
        if who.get("role") == "moderator":
            self.alert("mod_ban", "Ban by a moderator", "%s banned **%s** for %s: %s" % (
                who["name"], b["name"], human_length(minutes), reason), pid=b["pid"])
        self.watch_cache.clear()
        return {"id": bid, "servers": results, "audit_id": aid, "appeal_code": code, "identities": len(ids), "game": game}

    def ban_target(self, pid: str) -> dict:
        """Identity of a player who is not online, from what the portal has seen: servers, bug reports, game starts."""
        if not PID.match(pid or ""):
            raise ApiError(400, "Pick a player.")
        last = self.store.one("SELECT * FROM sightings WHERE pid=? ORDER BY last_seen DESC LIMIT 1", (pid,))
        if last:
            puid = self.store.one("SELECT puid FROM sightings WHERE pid=? AND puid<>'' ORDER BY last_seen DESC LIMIT 1", (pid,))
            return {"pid": pid, "guid": last["guid"], "ip": last["ip"], "puid": puid["puid"] if puid else "", "name": last["name"]}
        t = {"pid": pid, "guid": "", "ip": "", "puid": "", "name": ""}
        for r in self.store.q("SELECT data, target_name FROM reports WHERE target_pid=? ORDER BY id DESC LIMIT 50", (pid,)):
            d = json.loads(r["data"] or "{}")
            t["name"] = t["name"] or r["target_name"] or d.get("name", "")
            t["puid"] = t["puid"] or str(d.get("puid") or "")
        dev = self.store.one("SELECT * FROM devices WHERE pid=? ORDER BY last_seen DESC LIMIT 1", (pid,))
        if dev:
            t["name"] = t["name"] or dev["name"]
            t["puid"] = t["puid"] or dev["puid"]
        if not t["name"] and not dev and not self.store.one("SELECT id FROM reports WHERE target_pid=?", (pid,)):
            raise ApiError(404, "The portal has never seen this player: not on a server, in a bug report or starting the game.")
        t["name"] = t["name"] or "player " + pid[:8]
        return t

    def report_target(self, report_id: int) -> dict:
        """The sender of a bug report, as a ban target (works when the report carries no player id too)."""
        r = self.store.one("SELECT * FROM reports WHERE id=? AND source='bug'", (report_id,))
        if not r:
            raise ApiError(404, "No such bug report.")
        d = json.loads(r["data"] or "{}")
        if r["target_pid"]:
            t = self.ban_target(r["target_pid"])
        else:
            t = {"pid": "", "guid": "", "ip": "", "puid": str(d.get("puid") or ""), "name": d.get("name") or "bug reporter #%d" % r["id"]}
        t["iptag"] = d.get("from", "")
        t["kid"] = d.get("kid", "")
        t["hw"] = d.get("hwid") or []
        return t

    def ban_identities(self, target: dict, ip_ban: bool) -> list:
        """Every identity the portal links to this player, one hop out through shared PC keys and hardware."""
        pid = target.get("pid", "")
        ids = set(id_pairs(pid, target.get("puid", ""), target.get("kid", ""), target.get("hw") or (),
                           target.get("iptag", "") or (self.ip_tag(target["ip"]) if target.get("ip") else "")))
        if pid:
            for r in self.store.q("SELECT DISTINCT ip, puid FROM sightings WHERE pid=?", (pid,)):
                ids.update(id_pairs(puid=r["puid"], iptag=self.ip_tag(r["ip"]) if r["ip"] else ""))
            for r in self.store.q("SELECT data FROM reports WHERE source='bug' AND target_pid=?", (pid,)):
                d = json.loads(r["data"] or "{}")
                ids.update(id_pairs(puid=d.get("puid", ""), kid=d.get("kid", ""), hw=d.get("hwid") or (), iptag=d.get("from", "")))
        for _ in range(2):                       # devices: the same PC key or hardware under other names and installs
            kids = [v for k, v in ids if k == "kid"]
            hws = [v for k, v in ids if k == "hw"]
            pids = [v for k, v in ids if k == "pid"]
            for dev in self.devices_matching(pids, kids, hws):
                ids.update(id_pairs(dev["pid"], dev["puid"], dev["kid"], json.loads(dev["hw"] or "[]"), dev["iptag"]))
        if not ip_ban:
            ids = {x for x in ids if x[0] != "ip"}
        return sorted(ids)

    def devices_matching(self, pids: list, kids: list, hws: list) -> list:
        out = {}
        for col, vals in (("pid", pids), ("kid", kids)):
            for i in range(0, len(vals), 200):
                part = vals[i:i + 200]
                for r in self.store.q("SELECT * FROM devices WHERE %s IN (%s)" % (col, ",".join("?" * len(part))), part):
                    out[r["id"]] = r
        for h in hws[:50]:
            for r in self.store.q("SELECT * FROM devices WHERE hw LIKE ?", ('%"' + h + '"%',)):
                out[r["id"]] = r
        return list(out.values())

    def game_ban_for(self, pairs: list, learn: bool = True, via: str = "game") -> dict | None:
        """The active whole-game ban that any of these identities falls under. learn: a match on a strong identity
        adds the other identities to that ban (a new install, name or anti-cheat account on a banned PC)."""
        if not pairs:
            return None
        cond = " OR ".join("(i.kind=? AND i.value=?)" for _ in pairs)
        args = [x for p in pairs for x in p]
        rows = self.store.q("SELECT b.*, i.kind hit FROM ban_ids i JOIN bans b ON b.id=i.ban_id WHERE b.active=1 AND b.game=1 "
                            "AND (b.expires=0 OR b.expires>?) AND (%s) ORDER BY b.id" % cond, [now()] + args)
        if not rows:
            return None
        strong = [r for r in rows if r["hit"] in STRONG_KINDS]
        b = (strong or rows)[0]
        if learn and strong:
            count = "SELECT COUNT(*) n FROM ban_ids WHERE ban_id=?"
            before = self.store.one(count, (b["id"],))["n"]
            for kind, value in pairs:
                if kind == "ip" and not self.store.one("SELECT 1 FROM ban_ids WHERE ban_id=? AND kind='ip'", (b["id"],)):
                    continue                     # the ban was made without the IP: do not start banning addresses now
                self.store.x("INSERT OR IGNORE INTO ban_ids(ban_id,kind,value,added,via) VALUES(?,?,?,?,?)",
                             (b["id"], kind, value, now(), via))
            added = self.store.one(count, (b["id"],))["n"] - before
            if added:
                self.alert("dodger", "Banned player tried again",
                           "**%s** (ban #%d) came back with %d new identit%s; the ban now covers them too." % (
                               b["name"], b["id"], added, "y" if added == 1 else "ies"),
                           key="gameban-learn:%d" % b["id"], window=3600, pid=b["pid"])
        return b

    def gamecheck(self, j: dict, ip: str) -> dict:
        """POST /api/gamecheck from the launcher and the game at start: may this PC play?"""
        guid = clean_text(j.get("guid"), 64).strip()
        pid = player_pid(guid) if guid else ""
        puid = clean_text(j.get("puid"), 64).strip().lower()
        kid = clean_text(j.get("kid"), 64).strip().lower()
        hw = hw_ids(j.get("hwid"))
        iptag = self.ip_tag(ip)
        pairs = id_pairs(pid, puid, kid, hw, iptag)
        strong = [p for p in pairs if p[0] in STRONG_KINDS]
        name = re.sub(r"\^[^^]", "", clean_text(j.get("name"), 64)).strip()
        build = clean_text(j.get("build"), 64).strip()
        b = self.game_ban_for(pairs)
        if strong:
            key = hashlib.sha256(json.dumps(sorted(strong)).encode()).hexdigest()[:32]
            self.store.x("INSERT INTO devices(ids,pid,kid,puid,hw,iptag,name,build,first_seen,last_seen,checks,blocked) "
                         "VALUES(?,?,?,?,?,?,?,?,?,?,1,?) ON CONFLICT(ids) DO UPDATE SET iptag=excluded.iptag, name=excluded.name, "
                         "build=excluded.build, last_seen=excluded.last_seen, checks=checks+1, blocked=excluded.blocked",
                         (key, pid, kid if re.fullmatch(GAMEBAN_KINDS["kid"], kid) else "",
                          puid if re.fullmatch(GAMEBAN_KINDS["puid"], puid) else "", json.dumps(hw), iptag, name, build,
                          now(), now(), 1 if b else 0))
        out = {"play": True} if not b else {
            "play": False, "reason": b["reason"], "expires": b["expires"] or 0,
            "appeal_url": self.appeal_url() if b["appeal_code"] else "", "appeal_code": b["appeal_code"] or ""}
        nonce = str(j.get("nonce") or "").lower()
        key = self.gamecheck_key()
        if key and re.fullmatch(r"[0-9a-f]{32}", nonce):
            out["time"] = now()
            out["sig"] = ed25519_sign(key[0], gamecheck_message(nonce, out["play"], out["time"])).hex()
        return out

    def gamecheck_key(self):
        """(seed, public) that signs start-check answers, derived from the staff root (one secret to keep and
        back up); None without a root, and the answers then go out unsigned (the 0.39.8 game refuses those)."""
        if not hasattr(self, "_gc_key"):
            if not hasattr(self, "_staff_root"):
                self._staff_root, self._staff_certs = load_staff_root(self.cfg), {}
            root = self._staff_root
            self._gc_key = None
            if root:
                seed = hmac.new(root[1], b"tcp-gamecheck-key-1", hashlib.sha256).digest()
                self._gc_key = (seed, ed25519_public(seed))
        return self._gc_key

    def lift_ban(self, who: dict, b: dict, reason: str, action: str = "unban") -> dict:
        res = self._lift_everywhere(b)
        self.store.x("UPDATE bans SET active=0, lifted=?, lifted_by=?, lift_reason=? WHERE id=?",
                     (now(), who["name"], safe_arg(reason, 200), b["id"]))
        self.store.audit(who, action, target=b["name"], pid=b["pid"], detail=safe_arg(reason, 200) or "#%d" % b["id"],
                         result=json.dumps(res))
        self.watch_cache.clear()
        return res

    # -- undo (ban and mute, for UNDO_SECONDS)
    def undoable(self, audit_id: int, kind: str, ref: int, who: dict) -> None:
        if who.get("role") in RANK:
            self.store.x("INSERT OR REPLACE INTO undo(audit_id,kind,ref,by_id,expires) VALUES(?,?,?,?,?)",
                         (audit_id, kind, ref, who.get("discord_id", ""), now() + UNDO_SECONDS))

    def undo(self, who: dict, audit_id: int) -> str:
        u = self.store.one("SELECT * FROM undo WHERE audit_id=?", (audit_id,))
        if not u or u["done"]:
            raise ApiError(404, "There is nothing to undo for that action.")
        if u["expires"] < now():
            raise ApiError(409, "The 5-minute undo window has passed. Lift it the normal way.")
        if u["by_id"] != who["discord_id"] and not allowed(who, "ban.remove"):
            raise ApiError(403, "Only the person who did it, or an admin, can undo this.")
        self.store.x("UPDATE undo SET done=1 WHERE audit_id=?", (audit_id,))
        if u["kind"] == "ban":
            b = self.store.one("SELECT * FROM bans WHERE id=?", (u["ref"],))
            if b and b["active"]:
                self.lift_ban(who, b, "undone", action="undo ban")
            return "Ban undone on every server."
        m = self.store.one("SELECT * FROM mutes WHERE id=?", (u["ref"],))
        if m:
            self.store.x("UPDATE mutes SET active=0 WHERE id=?", (m["id"],))
            for s in self.servers.values():
                for p in s.view().get("players", []):
                    if p.get("pid") == m["pid"] and s.has("mute"):
                        try:
                            s.run("unmute %d" % p["slot"])
                            s.run("voiceunmute %d" % p["slot"])
                        except RconError:
                            pass
            self.store.audit(who, "undo mute", target=m["name"], pid=m["pid"], detail="#%d" % m["id"])
        return "Mute undone."

    # -- punishment ladder
    def ladder(self) -> dict:
        return self.cfg.get("ladder") or DEFAULT_LADDER

    def next_step(self, pid: str, offence: str) -> dict:
        lad = self.ladder().get(offence)
        if not lad:
            raise ApiError(400, "Pick an offence.")
        days = int(self.cfg.get("ladder_days", 90))
        n = self.store.one("SELECT COUNT(*) n FROM punishments WHERE pid=? AND offence=? AND created>?",
                           (pid, offence, now() - days * 86400))["n"] if pid else 0
        i = min(n, len(lad["steps"]) - 1)
        return {"offence": offence, "label": lad["label"], "index": i, "of": len(lad["steps"]), "earlier": n,
                "step": lad["steps"][i], "action": step_label(lad["steps"][i]), "days": days,
                "steps": [step_label(x) for x in lad["steps"]]}

    def punish(self, who: dict, offence: str, note: str = "", srv: GameServer | None = None, slot: int | None = None,
               p: dict | None = None, pid: str = "") -> dict:
        pid = (p or {}).get("pid") or pid
        if not pid:
            raise ApiError(409, "The portal has not identified this player yet. Use the normal buttons.")
        nxt = self.next_step(pid, offence)
        action, minutes = parse_step(nxt["step"])
        reason = safe_arg(nxt["label"] + (": " + note if note else ""), 100)
        if action == "ban" and (minutes == 0 or minutes > MOD_BAN_LIMIT) and not allowed(who, "ban.perm"):
            raise ApiError(403, "This is step %d of %d for %s: %s. Ask an admin to apply it." % (
                nxt["index"] + 1, nxt["of"], nxt["label"].lower(), nxt["action"].lower()))
        via = " (ladder step %d of %d)" % (nxt["index"] + 1, nxt["of"])
        if action != "ban" and p is None:
            raise ApiError(409, "Step %d is %s, and the player is not on a server right now." % (nxt["index"] + 1, nxt["action"].lower()))
        result = ""
        if action == "ban":
            target = dict(p) if p else self.ban_target(pid)
            r = self.ban_player(who, target, minutes, reason, srv=srv if p else None, slot=slot if p else None, via=via)
            result, aid = "banned", r["audit_id"]
        elif action == "warn" and not srv.has("warn"):
            # 0.35.0 servers have no private warning: the ladder warns in public chat instead
            srv.run("say ^8[STAFF]^7 %s: %s" % (safe_arg(p["name"], 32), reason))
            self.store.x("INSERT INTO warnings(pid,name,text,created,by_name,server) VALUES(?,?,?,?,?,?)",
                         (pid, p["name"], reason, now(), who["name"], srv.key))
            aid = self.store.audit(who, "warn", server=srv.key, target=p["name"], pid=pid, detail=reason + via + ", in public chat")
            result = "warned in public chat"
        else:
            result, aid = self.act(who, srv, slot, p, action, reason=reason + (via if action == "kick" else ""),
                                   length="%dm" % minutes if action == "mute" else "")
        self.store.x("INSERT INTO punishments(pid,name,offence,step,created,by_name,server,note) VALUES(?,?,?,?,?,?,?,?)",
                     (pid, (p or {}).get("name") or self.ban_target(pid)["name"], offence, nxt["step"], now(), who["name"],
                      srv.key if srv else "", safe_arg(note, 200)))
        return {"ok": True, "step": nxt["index"] + 1, "of": nxt["of"], "action": nxt["action"], "result": result, "audit_id": aid}


# ----------------------------------------------------------------------------- watchers
# Chat filter, joins (watchlist, ban dodgers), AFK and team-kill watch, suspicion score, server up and down.

class Watchers:
    SEVERITY = {"flag": 0, "warn": 1, "mute": 2, "kick": 3}

    # -- chat filter
    def filters(self) -> list:
        if self._filters is None:
            out = []
            for f in self.store.q("SELECT * FROM filters WHERE active=1"):
                try:
                    out.append((f, self.compile_filter(f["pattern"], f["kind"])))
                except (re.error, ValueError):
                    continue
            self._filters = out
        return self._filters

    @staticmethod
    def compile_filter(pattern: str, kind: str):
        pattern = str(pattern or "").strip()
        if not pattern or len(pattern) > 200:
            raise ValueError("Write a word or pattern of up to 200 characters.")
        if kind == "regex":
            # every chat line runs through these: refuse nested repeats like (a+)+ that can take forever
            if re.search(r"\((?:[^()\\]|\\.)*[+*}](?:[^()\\]|\\.)*\)\s*[+*{]", pattern):
                raise ValueError("Repeats inside a repeated group can stall the chat feed. Simplify the pattern.")
            return re.compile(pattern, re.I)
        if kind != "word":
            raise ValueError("Unknown filter type.")
        parts = [normalise_chat(x).strip() for x in pattern.split("*")]
        if not "".join(parts):
            raise ValueError("The word has no letters or digits.")
        return re.compile(r"(?<= )" + "[a-z0-9]*".join(re.escape(x) for x in parts) + r"(?= )")

    def filter_hits(self, text: str) -> list:
        norm = normalise_chat(text)
        raw = plain(text)
        return [f for f, rx in self.filters() if rx.search(norm if f["kind"] == "word" else raw)]

    def check_chat(self, srv: GameServer, slot: int, p: dict, text: str, chat_id: int) -> None:
        hits = self.filter_hits(text)
        if not hits:
            return
        f = max(hits, key=lambda h: self.SEVERITY.get(h["action"], 0))
        for h in hits:
            self.store.x("UPDATE filters SET hits=hits+1 WHERE id=?", (h["id"],))
        label = f["note"] or "filter #%d" % f["id"]
        self.store.x("UPDATE chat SET flag=? WHERE id=?", (label[:60], chat_id))
        name, pid = p.get("name") or "slot %d" % slot, p.get("pid", "")
        self.flag(pid, name, srv.key, "chat filter", "%s: %s" % (label, plain(text)[:120]))
        self.alert("filter", "Chat filter on %s" % srv.name, "**%s**: %s\nMatched %s." % (name, plain(text)[:200], label),
                   key="filter:" + (pid or name), window=900, pid=pid, server=srv.key)
        if not p or p.get("bot") or f["action"] == "flag" or self.limited("filter:%s:%s" % (srv.key, pid or slot), 1, 60):
            return
        who = dict(SYSTEM, name="Chat filter")
        reason = f["note"] or "Language"
        try:
            if f["action"] == "warn" and srv.has("warn"):
                self.act(who, srv, slot, p, "warn", reason="Watch your language (%s)." % reason)
            elif f["action"] == "mute" and srv.has("mute"):
                self.act(who, srv, slot, p, "mute", reason=reason, length="%dm" % (f["minutes"] or 10))
            elif f["action"] == "kick":
                self.act(who, srv, slot, p, "kick", reason=reason)
        except (ApiError, RconError) as e:
            log.info("chat filter action failed: %s", e)

    # -- flags and alerts
    def flag(self, pid: str, name: str, server: str, kind: str, detail: str) -> None:
        self.store.x("INSERT INTO flags(pid,name,server,kind,detail,at) VALUES(?,?,?,?,?,?)",
                     (pid, name, server, kind, detail[:300], now()))

    def alert(self, kind: str, title: str, text: str, key: str = "", window: int = 0, pid: str = "",
              server: str = "", urgent: bool = False) -> bool:
        """Records an alert for the portal's feed and queues it for the staff Discord channel. Same key within window: dropped."""
        key = key or kind + ":" + title
        if window and self.store.one("SELECT id FROM alerts WHERE key=? AND at>?", (key, now() - window)):
            return False
        aid = self.store.x("INSERT INTO alerts(key,at,kind,title,text,pid,server) VALUES(?,?,?,?,?,?,?)",
                           (key, now(), kind, title[:200], text[:1800], pid, server))
        self.bus.emit("alert", kind=kind, id=aid)
        self.push_queue.put((aid, urgent))
        if kind in ("suspicion", "dodger") and pid:
            name = self.store.one("SELECT name FROM sightings WHERE pid=? ORDER BY last_seen DESC LIMIT 1", (pid,))
            score = re.match(r"Suspicion (\d+)", title)
            self.ac_add(kind, pid, name["name"] if name else "", server, plain(text).replace("**", ""),
                        score=int(score.group(1)) if score else (90 if urgent else 60))
        kinds = self.cfg.get("alerts", {}).get("kinds")
        if kinds is None or kind in kinds:
            self.alert_queue.put((aid, urgent))
        return True

    def webhook_url(self) -> str:
        cred = os.environ.get("CREDENTIALS_DIRECTORY")
        if cred and (Path(cred) / "staff-webhook").exists():
            url = (Path(cred) / "staff-webhook").read_text(encoding="utf-8").strip()
        else:
            url = str(self.cfg.get("alerts", {}).get("webhook_url", "") or "")
        # alerts carry player names and IP hints: only ever to Discord over https (tests may point at loopback)
        if url and not re.match(r"^https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+$", url):
            if not (os.environ.get("TCP_STAFF_DEV") == "1" and url.startswith("http://127.0.0.1:")):
                log.warning("staff webhook ignored: not a Discord webhook URL")
                return ""
        return url

    COLOURS = {"server_down": 0xD63B3B, "server_up": 0x4FBF7A, "suspicion": 0xD63B3B, "dodger": 0xD63B3B,
               "reports": 0xE7A73C, "mod_ban": 0x5B9BD5, "watch": 0xE7A73C, "appeal": 0x5B9BD5, "filter": 0xE7A73C,
               "teamkill": 0xE7A73C, "weekly": 0xFF9914, "bugreport": 0x9AA3B3, "backup": 0xD63B3B,
               "comments": 0xE7A73C}
    LINKS = {"suspicion": "player", "dodger": "player", "reports": "reports", "watch": "player", "appeal": "reports",
             "mod_ban": "bans", "filter": "chat", "teamkill": "player", "server_down": "health", "server_up": "health",
             "weekly": "weekly", "bugreport": "reports", "backup": "health",
             "comments": "comments"}

    def alert_loop(self) -> None:
        import queue
        while not self.stop.is_set():
            try:
                aid, urgent = self.alert_queue.get(timeout=5)
            except queue.Empty:
                continue
            url = self.webhook_url()
            a = self.store.one("SELECT * FROM alerts WHERE id=?", (aid,))
            if not url or not a:
                continue
            base = self.cfg.get("public_url", "").rstrip("/")
            page = self.LINKS.get(a["kind"], "alerts")
            if page == "player":
                page = "player/" + a["pid"] if a["pid"] else "alerts"
            link = "%s/#/%s" % (base, page)
            ping = self.cfg.get("alerts", {}).get("ping_role_id")
            payload = {"username": "Staff Portal", "allowed_mentions": {"parse": [], "roles": [str(ping)] if ping and urgent else []},
                       "embeds": [{"title": a["title"], "description": a["text"], "color": self.COLOURS.get(a["kind"], 0x9AA3B3),
                                   "timestamp": iso(a["at"])}]}
            if base.startswith("https://"):
                payload["embeds"][0]["url"] = link
            if ping and urgent:
                payload["content"] = "<@&%s>" % ping
            for _ in range(3):
                try:
                    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
                        "Content-Type": "application/json", "User-Agent": "TrueCombatStaffPortal/%s" % VERSION})
                    urllib.request.urlopen(req, timeout=8).read()
                    self.store.x("UPDATE alerts SET sent=1 WHERE id=?", (aid,))
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        try:
                            wait = float(json.loads(e.read().decode()).get("retry_after", 2))
                        except (ValueError, OSError):
                            wait = 2
                        self.stop.wait(min(wait, 30))
                        continue
                    log.warning("staff webhook refused alert %d: %s", aid, e)
                    break
                except (urllib.error.URLError, OSError) as e:
                    log.warning("staff webhook unreachable: %s", e)
                    self.stop.wait(5)
            self.stop.wait(float(self.cfg.get("alerts", {}).get("gap_seconds", 1.2)))   # well under Discord's webhook limit

    # -- after every poll of a server
    def watch(self, srv: GameServer) -> None:
        v = srv.view()
        t = now()
        if not v.get("online"):
            first = self.down_since.setdefault(srv.key, t)
            if t - first >= int(self.cfg.get("down_alert_seconds", 90)) and srv.key not in self.down_alerted:
                self.down_alerted.add(srv.key)
                self.alert("server_down", "%s is down" % srv.name, "No answer for %d seconds: %s" % (t - first, v.get("error") or "no reply"),
                           key="down:" + srv.key, server=srv.key, urgent=True)
            self.track_sessions(srv, {}, {}, False)
            return
        if srv.key in self.down_alerted:
            self.down_alerted.discard(srv.key)
            self.alert("server_up", "%s is back" % srv.name, "Answering again after %s." % human_length(max(1, (t - self.down_since.get(srv.key, t)) // 60)),
                       key="up:%s:%d" % (srv.key, t), server=srv.key)
        self.down_since.pop(srv.key, None)
        players = [p for p in v.get("players", []) if not p["bot"]]
        day = time.strftime("%Y-%m-%d", time.gmtime(t))
        self.store.x("INSERT INTO peaks(day,server,peak) VALUES(?,?,?) ON CONFLICT(day,server) DO UPDATE SET "
                     "peak=MAX(peak, excluded.peak)", (day, srv.key, len(players)))
        online = {}
        for p in players:
            pid = p.get("pid")
            if not pid:
                continue
            online[pid] = p["slot"]
            mark = (pid, p.get("puid", ""), p.get("ip", ""))
            if self.watch_cache.get((srv.key, p["slot"])) != mark:
                self.watch_cache[(srv.key, p["slot"])] = mark
                self.on_join(srv, p, first=(pid not in self.online.get(srv.key, {})))
        self.online[srv.key] = online
        self.track_sessions(srv, online, {p["pid"]: p["name"] for p in players if p.get("pid")}, True)
        self.ac_watch(srv, players)
        self.afk_and_tk(srv, v, players)

    def on_join(self, srv: GameServer, p: dict, first: bool) -> None:
        pid, name = p["pid"], p["name"]
        w = self.store.one("SELECT * FROM watchlist WHERE pid=?", (pid,))
        if w and first:
            self.alert("watch", "Watched player joined %s" % srv.name, "**%s** is on %s. Watch reason: %s" % (name, srv.name, w["reason"] or "none given"),
                       key="watch:%s:%s" % (pid, srv.key), window=1800, pid=pid, server=srv.key)
        for hit in self.dodger_hits(pid, p.get("puid", ""), p.get("ip", "")):
            strong = hit["why"] == "anti-cheat account"
            detail = "Shares the %s of banned player %s (ban #%d: %s)" % (hit["why"], hit["name"], hit["id"], hit["reason"])
            if self.store.one("SELECT id FROM flags WHERE pid=? AND kind=? AND detail=? AND at>?",
                              (pid, "ban dodger" if strong else "possible alt", detail, now() - 86400)):
                continue
            self.flag(pid, name, srv.key, "ban dodger" if strong else "possible alt", detail)
            self.alert("dodger", ("Ban dodger on %s" if strong else "Possible alt of a banned player on %s") % srv.name,
                       "**%s**: %s." % (name, detail), key="dodger:%s:%d" % (pid, hit["id"]), window=86400, pid=pid,
                       server=srv.key, urgent=strong)

    def dodger_hits(self, pid: str, puid: str, ip: str) -> list:
        """Active bans on other identities that share this player's anti-cheat account (strong) or address (weak)."""
        out, seen = [], set()
        if puid:
            for b in self.store.q("SELECT id,name,reason,pid FROM bans WHERE active=1 AND pid<>? AND ((puid<>'' AND puid=?) OR "
                                  "pid IN (SELECT pid FROM sightings WHERE puid=? AND pid<>?))", (pid, puid, puid, pid)):
                seen.add(b["id"])
                out.append(dict(b, why="anti-cheat account"))
        if ip and self.cfg.get("dodger_ip_check", True):
            for b in self.store.q("SELECT id,name,reason,pid FROM bans WHERE active=1 AND pid<>? AND ((ip<>'' AND ip=?) OR "
                                  "pid IN (SELECT pid FROM sightings WHERE ip=? AND pid<>?))", (pid, ip, ip, pid)):
                if b["id"] not in seen:
                    out.append(dict(b, why="internet address"))
        return out

    def afk_and_tk(self, srv: GameServer, v: dict, players: list) -> None:
        t = now()
        afk_flag = int(self.cfg.get("afk_flag_seconds", 120))
        afk_spec = int(self.cfg.get("afk_spectate_seconds", 300))
        with srv.lock:
            pos = dict(srv.positions)
        live = set()
        for p in players:
            pid = p.get("pid")
            if not pid:
                continue
            key = (srv.key, pid)
            live.add(key)
            here = pos.get(p["slot"])
            if p.get("spectator") or p.get("team") not in (1, 2) or not here or here["hp"] <= 0 or not here["begun"]:
                self.afk.pop(key, None)
            else:
                a = self.afk.get(key)
                if not a or abs(here["x"] - a["x"]) + abs(here["y"] - a["y"]) + abs(here["z"] - a["z"]) > 32:
                    self.afk[key] = {"x": here["x"], "y": here["y"], "z": here["z"], "since": t, "flagged": False}
                else:
                    still = t - a["since"]
                    if afk_flag and still >= afk_flag and not a["flagged"]:
                        a["flagged"] = True
                        self.flag(pid, p["name"], srv.key, "afk", "Alive and not moving for %d seconds" % still)
                    if afk_spec and still >= afk_spec:
                        try:
                            self.act(dict(SYSTEM, name="AFK watch"), srv, p["slot"], p, "move", team="s",
                                     reason="not moving for %d minutes" % (still // 60))
                        except (ApiError, RconError) as e:
                            log.info("AFK move failed: %s", e)
                        self.afk.pop(key, None)
            # team kills: the 0.36.0 player list counts them per map
            tk = p.get("team_kills")
            if tk is None:
                continue
            mark = (srv.key, pid, v.get("map", ""))
            done = self.tk_seen.setdefault(mark, set())
            warn_at = int(self.cfg.get("tk_warn_at", 2))
            flag_at = int(self.cfg.get("tk_flag_at", 3))
            if warn_at and tk >= warn_at and "warn" not in done:
                done.add("warn")
                if srv.has("warn"):
                    try:
                        self.act(dict(SYSTEM, name="Team-kill watch"), srv, p["slot"], p, "warn",
                                 reason="%d team kills on this map. Watch your fire." % tk)
                    except (ApiError, RconError) as e:
                        log.info("team-kill warning failed: %s", e)
            if flag_at and tk >= flag_at and "flag" not in done:
                done.add("flag")
                self.flag(pid, p["name"], srv.key, "team kills", "%d team kills on %s" % (tk, v.get("map", "")))
                self.alert("teamkill", "Team killing on %s" % srv.name, "**%s** has %d team kills on %s." % (p["name"], tk, v.get("map", "")),
                           key="tk:%s:%s:%s" % (srv.key, pid, v.get("map", "")), window=3600, pid=pid, server=srv.key)
        for key in [k for k in self.afk if k[0] == srv.key and k not in live]:
            del self.afk[key]
        if len(self.tk_seen) > 2000:
            self.tk_seen.clear()

    # -- suspicion score
    def suspicion_loop(self) -> None:
        while not self.stop.is_set():
            self.suspicion_pass()
            self.stop.wait(float(self.cfg.get("suspicion_seconds", 60)))

    def suspicion_pass(self) -> None:
        threshold = int(self.cfg.get("suspicion_alert", 60))
        for srv in self.servers.values():
            for p in srv.view().get("players", []):
                if p["bot"] or not p.get("pid"):
                    continue
                score, reasons = self.suspicion(p)
                prev = self.store.one("SELECT score, peak FROM suspicion WHERE pid=?", (p["pid"],))
                self.store.x("INSERT INTO suspicion(pid,name,score,reasons,updated,peak) VALUES(?,?,?,?,?,?) ON CONFLICT(pid) DO UPDATE SET "
                             "name=excluded.name, score=excluded.score, reasons=excluded.reasons, updated=excluded.updated, "
                             "peak=MAX(suspicion.peak, excluded.score)", (p["pid"], p["name"], score, json.dumps(reasons), now(), score))
                if score >= threshold and (not prev or prev["score"] < threshold):
                    self.alert("suspicion", "Suspicion %d: %s on %s" % (score, p["name"], srv.name),
                               "\n".join("- " + r for r in reasons), key="sus:" + p["pid"], window=6 * 3600,
                               pid=p["pid"], server=srv.key, urgent=score >= 85)

    def suspicion(self, p: dict) -> tuple:
        """0-100 and the reasons. A pointer for staff to look closer, never proof on its own."""
        pid, score, why = p.get("pid", ""), 0, []
        det = int(p.get("detections") or 0)
        if det:
            score += min(60, 40 + 10 * (det - 1))
            why.append("%d anti-cheat detection%s this session" % (det, "" if det == 1 else "s"))
        week = now() - 7 * 86400
        reporters, autos = set(), 0
        for r in self.store.q("SELECT source, data FROM reports WHERE target_pid=? AND received>? AND source IN ('player','auto')", (pid, week)):
            if r["source"] == "auto":
                autos += 1
                continue
            try:
                by = json.loads(r["data"]).get("reporter") or {}
            except ValueError:
                by = {}
            reporters.add(str(by.get("id") or plain(by.get("name")) or "?"))
        if reporters:
            score += min(30, 8 * len(reporters))
            why.append("reported by %d player%s in 7 days" % (len(reporters), "" if len(reporters) == 1 else "s"))
        if autos:
            score += min(36, 12 * autos)
            why.append("%d automatic flag%s in 7 days" % (autos, "" if autos == 1 else "s"))
        shots, hits = int(p.get("shots") or 0), int(p.get("hits") or 0)
        if shots >= 60 and hits <= shots:        # shotguns count every pellet as a hit; those numbers say nothing
            acc = hits / shots
            if acc >= 0.55:
                score += 25 if acc >= 0.70 else 15
                why.append("%d%% accuracy on this map (%d shots)" % (round(acc * 100), shots))
        kills, deaths = int(p.get("kills") or 0), int(p.get("deaths") or 0)
        if kills >= 15 and kills / max(1, deaths) >= 4:
            kd = kills / max(1, deaths)
            score += 15 if kd >= 6 else 10
            why.append("%d kills, %d deaths on this map" % (kills, deaths))
        st = self.cached_stats(pid)
        if st:
            rk = sum(int(m.get("kills") or 0) for m in st.get("recent", []))
            hs = sum(int(m.get("headshots") or 0) for m in st.get("recent", []))
            if rk >= 60 and hs / rk >= 0.45:
                score += 20 if hs / rk >= 0.60 else 10
                why.append("%d%% headshot kills over the last %d matches" % (round(100 * hs / rk), len(st.get("recent", []))))
        for hit in self.dodger_hits(pid, p.get("puid", ""), p.get("ip", "")):
            if hit["why"] == "anti-cheat account":
                score += 50
                why.append("same anti-cheat account as banned player %s" % hit["name"])
            else:
                score += 15
                why.append("same internet address as banned player %s" % hit["name"])
            break
        return min(100, score), why

    def cached_stats(self, pid: str):
        t, data = self.stats_cache.get(pid, (0, None))
        if time.time() - t > 1800:
            data = self.stats("player.json", id=pid)
            self.stats_cache[pid] = (time.time(), data)
            if len(self.stats_cache) > 2000:
                self.stats_cache.clear()
        return data


# ----------------------------------------------------------------------------- operations
# Appeals, scheduled actions, event mode, the config editor, the weekly report, server demos,
# linked Discord accounts, the stats review queue and the live map.

DEMO_NAME = re.compile(r"_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})_[^/]*\.sv_?\d+$")
SCHEDULE_ACTIONS = {"say": "server.say", "map": "schedule", "nextmap": "schedule", "restart": "schedule"}


def iso_to_unix(text) -> int | None:
    try:
        import datetime as dt
        return int(dt.datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def brussels(t: float):
    import datetime as dt
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.fromtimestamp(t, ZoneInfo("Europe/Brussels"))
    except Exception:  # noqa: BLE001  (no tz database: CET is close enough for a weekly report)
        return dt.datetime.fromtimestamp(t, dt.timezone(dt.timedelta(hours=1)))


class Operations:
    # -- server commands shared by the API and the scheduler
    def server_command(self, who: dict, act: str, keys: list, text: str = "", m: str = "", maps: str = "", via: str = "") -> dict:
        text = safe_arg(text, 200)
        results = {}
        for key in keys:
            srv = self.servers[key]
            try:
                if act in ("say", "chat"):
                    if not text:
                        raise ApiError(400, "Write a message.")
                    staff_name = safe_arg(who["name"], 24) or "Staff"
                    if srv.has("staffsay"):
                        cmd = "staffsay %s %s" % (staff_name.replace(" ", "_"), text)
                    else:
                        cmd = "say ^8[STAFF] %s^7: %s" % (staff_name, text)
                    results[key] = srv.run(cmd)
                    # rcon output never reaches the server log, so the portal records staff lines itself
                    self.store.x("INSERT INTO chat(server,at,slot,team,pid,name,text,kind) VALUES(?,?,?,?,?,?,?,?)",
                                 (srv.key, now(), -1, None, "", staff_name, text, "staff"))
                elif act == "map":
                    if not MAP_NAME.match(m or ""):
                        raise ApiError(400, "Pick a map.")
                    results[key] = srv.run("map %s" % m, timeout=4)
                    text = m
                elif act == "nextmap":
                    if m and not MAP_NAME.match(m):
                        raise ApiError(400, "Pick a map.")
                    results[key] = srv.run(("nextmap %s" % (m or "")).strip(), timeout=4)
                    text = m or "next in rotation"
                elif act == "restart":
                    results[key] = srv.run("map_restart 0", timeout=4)
                    text = "match restart"
                elif act == "rotation":
                    names = [x for x in str(maps or "").split() if MAP_NAME.match(x)]
                    if not names:
                        raise ApiError(400, "List at least one map.")
                    results[key] = srv.run("maprotation %s" % " ".join(names[:20]), timeout=3)
                    text = " ".join(names[:20])
                else:
                    raise ApiError(400, "Unknown action.")
            except RconError as e:
                results[key] = "offline: %s" % e
        self.store.audit(who, "server " + act, server=",".join(keys), detail=text + via,
                         result=json.dumps({k: plain(v).strip()[:200] for k, v in results.items()}))
        return {k: plain(v).strip()[:300] for k, v in results.items()}

    # -- appeals
    def appeal_submit(self, code: str, text: str, contact: str, sender: str) -> dict:
        code = re.sub(r"[^A-Z0-9]", "", str(code or "").upper())
        b = self.store.one("SELECT * FROM bans WHERE appeal_code=? AND active=1", (code,)) if len(code) == 6 else None
        if not b:
            raise ApiError(404, "No active ban has that code. Check the code in the message you saw when you were removed.")
        text = str(text or "").replace("\x00", "").strip()[:2000]
        if len(text) < 20:
            raise ApiError(400, "Tell us in a few sentences why the ban should be lifted.")
        if self.store.one("SELECT id FROM appeals WHERE ban_id=? AND status='open'", (b["id"],)):
            raise ApiError(409, "An appeal for this ban is already waiting. Check its status with the same code.")
        if self.store.one("SELECT COUNT(*) n FROM appeals WHERE ban_id=?", (b["id"],))["n"] >= 3:
            raise ApiError(409, "This ban has been appealed three times. Staff will not review it again.")
        contact = safe_arg(contact, 100)
        aid = self.store.x("INSERT INTO appeals(code,ban_id,pid,name,text,contact,created,updated,from_hash) VALUES(?,?,?,?,?,?,?,?,?)",
                           (code, b["id"], b["pid"], b["name"], text, contact, now(), now(), sender))
        data = {"appeal_id": aid, "code": code, "text": text, "contact": contact,
                "ban": {"id": b["id"], "reason": b["reason"], "created": b["created"], "expires": b["expires"], "by": b["by_name"]}}
        self.store.x("INSERT INTO reports(source,file,server,received,data,target_pid,target_name,status,updated) VALUES(?,?,?,?,?,?,?,?,?)",
                     ("appeal", "appeal/%d" % aid, "", now(), json.dumps(data), b["pid"], b["name"], "open", now()))
        self.alert("appeal", "Ban appeal from %s" % b["name"], "Ban #%d (%s). %s" % (b["id"], b["reason"], text[:300]),
                   key="appeal:%d" % aid, pid=b["pid"])
        return {"ok": True, "status": "open"}

    def appeal_status(self, code: str) -> dict:
        code = re.sub(r"[^A-Z0-9]", "", str(code or "").upper())
        b = self.store.one("SELECT * FROM bans WHERE appeal_code=?", (code,)) if len(code) == 6 else None
        if not b:
            raise ApiError(404, "No ban has that code.")
        a = self.store.one("SELECT status, answer, created, updated FROM appeals WHERE ban_id=? ORDER BY id DESC LIMIT 1", (b["id"],))
        return {"ban": {"reason": b["reason"], "since": b["created"], "expires": b["expires"], "active": bool(b["active"])},
                "appeal": a}

    def appeal_answer(self, who: dict, appeal_id: int, decision: str, answer: str) -> dict:
        a = self.store.one("SELECT * FROM appeals WHERE id=?", (appeal_id,))
        if not a:
            raise ApiError(404, "No such appeal.")
        if a["status"] != "open":
            raise ApiError(409, "This appeal was already answered.")
        if decision not in ("accept", "deny"):
            raise ApiError(400, "Accept or deny.")
        answer = str(answer or "").strip()[:1000]
        if not answer:
            raise ApiError(400, "Write the answer the player will read.")
        b = self.store.one("SELECT * FROM bans WHERE id=?", (a["ban_id"],))
        if b and b["by_id"] and b["by_id"] == who.get("discord_id"):
            # the appeal page promises a reviewer who was not involved; the owner can still lift the ban from the Bans page
            raise ApiError(403, "You made this ban. Another admin answers the appeal, as the appeal page promises.")
        if decision == "accept":
            if b and b["active"]:
                self.lift_ban(who, b, "appeal accepted")
        status = "accepted" if decision == "accept" else "denied"
        self.store.x("UPDATE appeals SET status=?, answer=?, answered_by=?, updated=? WHERE id=?", (status, answer, who["name"], now(), a["id"]))
        self.store.x("UPDATE reports SET status='closed', claimed_by=?, resolution=?, updated=? WHERE file=?",
                     (who["name"], "Appeal %s: %s" % (status, answer[:300]), now(), "appeal/%d" % a["id"]))
        self.store.audit(who, "appeal " + status, target=a["name"], pid=a["pid"], detail=answer[:300])
        return {"ok": True, "status": status}

    # -- linked Discord accounts (the Discord bot's /link table, read only)
    def discord_links(self, pid: str = "", discord_id: str = "") -> list | None:
        path = self.cfg.get("discord_bot_db")
        if not path or not Path(path).exists():
            return None
        # read only; if the bot's WAL index cannot be shared, fall back to the last checkpointed state
        for mode in ("mode=ro", "mode=ro&immutable=1"):
            try:
                con = sqlite3.connect("file:%s?%s" % (urllib.parse.quote(str(path)), mode), uri=True, timeout=2)
                try:
                    con.row_factory = sqlite3.Row
                    if pid:
                        rows = con.execute("SELECT discord_id, pid, name, linked_at FROM links WHERE pid=?", (pid,)).fetchall()
                    else:
                        rows = con.execute("SELECT discord_id, pid, name, linked_at FROM links WHERE discord_id=?", (int(discord_id),)).fetchall()
                    return [{k: str(r[k]) if k == "discord_id" else r[k] for k in r.keys()} for r in rows]
                finally:
                    con.close()
            except (sqlite3.Error, ValueError, OSError) as e:
                log.info("Discord link lookup (%s) failed: %s", mode, e)
        return None

    # -- scheduled actions
    def schedule_loop(self) -> None:
        while not self.stop.is_set():
            self.run_schedule()
            self.stop.wait(10)

    def run_schedule(self) -> int:
        ran = 0
        t = now()
        for job in self.store.q("SELECT * FROM schedule WHERE active=1 AND next_at<=?", (t,)):
            who = {"discord_id": job["by_id"], "name": job["by_name"], "role": "system"}
            owner = job["by_id"] in {str(x) for x in self.cfg.get("owners", [])}
            staff = self.store.one("SELECT role FROM staff WHERE discord_id=?", (job["by_id"],))
            if not owner and staff and staff["role"] == "revoked":
                self.store.x("UPDATE schedule SET active=0, last_result=? WHERE id=?", ("cancelled: %s no longer has staff access" % job["by_name"], job["id"]))
                self.store.audit(SYSTEM, "schedule cancel", server=job["server"], detail="#%d %s: creator revoked" % (job["id"], job["action"]))
                continue
            keys = self.order if job["server"] == "*" else [job["server"]] if job["server"] in self.servers else []
            try:
                if not keys:
                    raise ApiError(404, "server no longer configured")
                res = self.server_command(who, job["action"], keys, text=job["arg"] if job["action"] == "say" else "",
                                          m=job["arg"] if job["action"] in ("map", "nextmap") else "", via=" (scheduled #%d)" % job["id"])
                result = "; ".join("%s: %s" % (k, v or "ok") for k, v in res.items())
            except ApiError as e:
                result = "failed: " + e.message
            nxt, active = 0, 0
            if job["every_min"]:
                nxt = job["next_at"]
                while nxt <= t:
                    nxt += job["every_min"] * 60
                active = 1 if not job["until"] or nxt <= job["until"] else 0
            self.store.x("UPDATE schedule SET runs=runs+1, last_run=?, last_result=?, next_at=?, active=? WHERE id=?",
                         (t, result[:300], nxt or job["next_at"], active, job["id"]))
            ran += 1
        return ran

    # -- event mode and the config editor share one rule: the portal keeps live values where staff put them
    def event_start(self, who: dict, srv: GameServer, password: str = "", note: str = "") -> dict:
        if self.store.one("SELECT server FROM events WHERE server=?", (srv.key,)):
            raise ApiError(409, "Event mode is already on for this server.")
        preset = {k: str(v) for k, v in (self.cfg.get("event_preset") or EVENT_PRESET).items()}
        if password:
            if not re.fullmatch(r"[A-Za-z0-9_-]{4,24}", password):
                raise ApiError(400, "Use 4 to 24 letters, digits, - or _ for the password.")
            preset["g_password"] = password
        elif preset.get("g_password") == "*random*":
            preset["g_password"] = "".join(secrets.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(8))
        for k, v in preset.items():
            if not re.fullmatch(r"[A-Za-z0-9_]{1,40}", k) or not CVAR_VALUE.match(v):
                raise ApiError(500, "The event preset in the config has a bad entry: %s" % k)
        saved = {}
        for k in list(preset):
            val = srv.cvar(k)
            if val is None:                      # a setting this server does not have: leave it alone, never create it
                del preset[k]
                continue
            saved[k] = val
        applied = []
        try:
            for k, v in preset.items():
                srv.set_cvar(k, v)
                applied.append(k)
        except RconError as e:
            for k in applied:                    # put back what already changed, so no password is left without an event
                try:
                    srv.set_cvar(k, saved[k])
                except RconError:
                    pass
            raise ApiError(502, "The server stopped answering while event mode was switching on, so nothing was changed. Try again.") from e
        for k, v in preset.items():
            self.store.x("INSERT INTO cvar_changes(server,cvar,old,new,at,by_name,kind) VALUES(?,?,?,?,?,?,'event')",
                         (srv.key, k, saved[k], v if k != "g_password" else "(event password)", now(), who["name"]))
        self.store.x("INSERT INTO events(server,started,by_name,saved,preset,note) VALUES(?,?,?,?,?,?)",
                     (srv.key, now(), who["name"], json.dumps(saved), json.dumps(preset), safe_arg(note, 120)))
        self.store.audit(who, "event start", server=srv.key, detail=safe_arg(note, 120) or "event mode on")
        return {"ok": True, "password": preset.get("g_password", ""), "preset": preset}

    def event_stop(self, who: dict, srv: GameServer) -> dict:
        e = self.store.one("SELECT * FROM events WHERE server=?", (srv.key,))
        if not e:
            raise ApiError(409, "Event mode is not on for this server.")
        saved = json.loads(e["saved"] or "{}")
        failed = []
        for k, v in saved.items():
            override = self.store.one("SELECT value FROM cvar_overrides WHERE server=? AND cvar=?", (srv.key, k))
            value = override["value"] if override else v
            try:
                srv.set_cvar(k, value)
                self.store.x("INSERT INTO cvar_changes(server,cvar,old,new,at,by_name,kind) VALUES(?,?,?,?,?,?,'event end')",
                             (srv.key, k, "(event)" if k == "g_password" else json.loads(e["preset"]).get(k, ""), value if k != "g_password" else "(restored)",
                              now(), who["name"]))
            except RconError:
                failed.append(k)
        if failed:
            # keep the event (and its saved values) so a second Stop can finish the job; never strand a server on the event password
            self.store.audit(who, "event stop", server=srv.key, detail="server did not answer", ok=False, result=", ".join(failed))
            raise ApiError(502, "The server did not take %s back. Event mode stays on; try Stop again in a moment." % ", ".join(failed))
        self.store.x("DELETE FROM events WHERE server=?", (srv.key,))
        self.store.audit(who, "event stop", server=srv.key, detail="restored %d settings" % (len(saved) - len(failed)),
                         ok=not failed, result=", ".join(failed))
        return {"ok": True, "restored": len(saved) - len(failed), "failed": failed}

    def wanted_cvars(self, key: str) -> dict:
        out = {r["cvar"]: r["value"] for r in self.store.q("SELECT cvar, value FROM cvar_overrides WHERE server=?", (key,))}
        e = self.store.one("SELECT preset FROM events WHERE server=?", (key,))
        if e:
            out.update(json.loads(e["preset"] or "{}"))
        return out

    def enforce_loop(self) -> None:
        while not self.stop.is_set():
            self.stop.wait(float(self.cfg.get("enforce_seconds", 60)))
            self.enforce()

    def enforce(self) -> int:
        """After a server restart or a cfg reload, put kept settings and the event preset back."""
        fixed = 0
        for srv in self.servers.values():
            want = self.wanted_cvars(srv.key)
            if not want or not srv.view().get("online"):
                continue
            for k, v in want.items():
                try:
                    live = srv.cvar(k)
                    if live is not None and live != v:
                        srv.set_cvar(k, v)
                        fixed += 1
                        if not self.limited("reapply:%s:%s" % (srv.key, k), 1, 3600):
                            self.store.x("INSERT INTO cvar_changes(server,cvar,old,new,at,by_name,kind) VALUES(?,?,?,?,?,?,'re-applied')",
                                         (srv.key, k, live if k != "g_password" else "(changed)", v if k != "g_password" else "(event)", now(), "Portal"))
                except RconError:
                    break
        return fixed

    def cvar_list(self) -> dict:
        return self.cfg.get("cvars") or CVARS

    def cvars_view(self, srv: GameServer) -> dict:
        overrides = {r["cvar"]: r for r in self.store.q("SELECT * FROM cvar_overrides WHERE server=?", (srv.key,))}
        e = self.store.one("SELECT * FROM events WHERE server=?", (srv.key,))
        event = json.loads(e["preset"]) if e else {}
        rows, down = [], False
        for name, label in self.cvar_list().items():
            try:
                val = None if down else srv.cvar(name)
            except RconError:
                val, down = None, True             # one missed answer: do not wait 1.5 s for each of the others
            meta = CVAR_META.get(name, {})
            row = {"name": name, "label": label, "value": val, "kept": overrides.get(name, {}).get("value"),
                   "event": name in event, "group": meta.get("group", "Other"), "help": meta.get("help", ""),
                   "type": meta.get("type", "text"), "view": bool(meta.get("view")), "next_map": bool(meta.get("next_map"))}
            for k in ("min", "max", "words"):
                if k in meta:
                    row[k] = meta[k]
            if "choices" in meta:
                row["choices"] = [list(c) for c in meta["choices"]]
            if name == "tcp_wx" and val:
                row["shown"] = weather_text(val)
            rows.append(row)
        hist = self.store.q("SELECT * FROM cvar_changes WHERE server=? ORDER BY id DESC LIMIT 60", (srv.key,))
        return {"cvars": rows, "history": hist, "offline": down, "groups": CVAR_GROUPS}

    def cvar_set(self, who: dict, srv: GameServer, name: str, value: str, keep: bool, kind: str = "set") -> dict:
        if name not in self.cvar_list() or CVAR_META.get(name, {}).get("view"):
            raise ApiError(400, "That setting cannot be changed from the portal.")
        value = str(value if value is not None else "").strip()
        try:
            value = cvar_check(name, value, CVAR_META.get(name))
        except ValueError as e:
            raise ApiError(400, str(e))
        if self.store.one("SELECT server FROM events WHERE server=? AND preset LIKE ?", (srv.key, '%"' + name + '"%')):
            raise ApiError(409, "Event mode controls this setting right now. Stop the event first.")
        old = srv.cvar(name)
        if old is None:
            raise ApiError(409, "The server does not know the setting %s." % name)
        srv.set_cvar(name, value)
        now_val = srv.cvar(name)
        if keep:
            self.store.x("INSERT INTO cvar_overrides(server,cvar,value,set_at,by_name) VALUES(?,?,?,?,?) ON CONFLICT(server,cvar) "
                         "DO UPDATE SET value=excluded.value, set_at=excluded.set_at, by_name=excluded.by_name",
                         (srv.key, name, value, now(), who["name"]))
        else:
            self.store.x("DELETE FROM cvar_overrides WHERE server=? AND cvar=?", (srv.key, name))
        cid = self.store.x("INSERT INTO cvar_changes(server,cvar,old,new,at,by_name,kind,kept) VALUES(?,?,?,?,?,?,?,?)",
                           (srv.key, name, old, value, now(), who["name"], kind, 1 if keep else 0))
        self.store.audit(who, "setting " + kind, server=srv.key, target=name, detail="%s -> %s%s" % (old, value, ", kept" if keep else ""),
                         ok=now_val == value, result="now %s" % now_val)
        note = "" if now_val == value else "The server reports %s. Some settings only change at the next map." % now_val
        if not note and CVAR_META.get(name, {}).get("next_map"):
            note = "%s is now %s. The server uses it from the next map." % (name, now_val or "empty")
        return {"ok": True, "id": cid, "old": old, "value": now_val, "note": note}

    def cvar_rollback(self, who: dict, change_id: int) -> dict:
        c = self.store.one("SELECT * FROM cvar_changes WHERE id=?", (change_id,))
        if not c or c["kind"] not in ("set", "rollback"):
            raise ApiError(404, "Only changes made in the editor can be rolled back.")
        srv = self.server(c["server"])
        return self.cvar_set(who, srv, c["cvar"], c["old"], keep=False, kind="rollback")

    # -- weekly staff report
    def weekly(self, end: int | None = None) -> dict:
        end = end or now()
        start = end - 7 * 86400
        q, one = self.store.q, self.store.one
        acts = q("SELECT action, COUNT(*) n FROM audit WHERE at>=? AND at<? AND ok=1 GROUP BY action", (start, end))
        by_action = {a["action"]: a["n"] for a in acts}
        moderation = ("kick", "warn", "mute", "ban", "unban", "move", "report closed", "appeal accepted", "appeal denied")
        staff = q("SELECT staff, role, COUNT(*) n FROM audit WHERE at>=? AND at<? AND ok=1 AND role IN ('moderator','admin','owner') "
                  "AND action IN (%s) GROUP BY staff ORDER BY n DESC" % ",".join("?" * len(moderation)), [start, end, *moderation])
        closed = q("SELECT received, updated FROM reports WHERE status='closed' AND updated>=? AND updated<? AND source<>'bug'", (start, end))
        waits = sorted(r["updated"] - r["received"] for r in closed if r["updated"] >= r["received"])
        peaks = q("SELECT server, MAX(peak) peak FROM peaks WHERE day>=? AND day<=? GROUP BY server",
                  (time.strftime("%Y-%m-%d", time.gmtime(start)), time.strftime("%Y-%m-%d", time.gmtime(end))))
        daily = q("SELECT day, SUM(peak) peak FROM peaks WHERE day>=? AND day<=? GROUP BY day ORDER BY day",
                  (time.strftime("%Y-%m-%d", time.gmtime(start)), time.strftime("%Y-%m-%d", time.gmtime(end))))
        return {
            "from": start, "to": end,
            "players": one("SELECT COUNT(DISTINCT pid) n FROM sightings WHERE last_seen>=?", (start,))["n"],
            "new_players": one("SELECT COUNT(*) n FROM (SELECT pid, MIN(first_seen) f FROM sightings GROUP BY pid) WHERE f>=? AND f<?", (start, end))["n"],
            "peaks": {p["server"]: p["peak"] for p in peaks}, "daily_peak": daily,
            "actions": {k: by_action.get(k, 0) for k in ("kick", "warn", "mute", "ban", "unban", "move")},
            "auto_actions": one("SELECT COUNT(*) n FROM audit WHERE at>=? AND at<? AND role='system'", (start, end))["n"],
            "bans_by_moderators": one("SELECT COUNT(*) n FROM audit WHERE at>=? AND at<? AND action='ban' AND role='moderator'", (start, end))["n"],
            "reports_in": {r["source"]: r["n"] for r in q("SELECT source, COUNT(*) n FROM reports WHERE received>=? AND received<? GROUP BY source", (start, end))},
            "reports_closed": len(closed), "median_close_minutes": waits[len(waits) // 2] // 60 if waits else None,
            "open_now": one("SELECT COUNT(*) n FROM reports WHERE status<>'closed'")["n"],
            "appeals": {r["status"]: r["n"] for r in q("SELECT status, COUNT(*) n FROM appeals WHERE created>=? AND created<? GROUP BY status", (start, end))},
            "flags": {r["kind"]: r["n"] for r in q("SELECT kind, COUNT(*) n FROM flags WHERE at>=? AND at<? GROUP BY kind", (start, end))},
            "staff": staff,
        }

    def weekly_text(self, w: dict) -> str:
        a = w["actions"]
        lines = [
            "**Players**: %d played, %d new. Peak: %s." % (w["players"], w["new_players"],
                                                           ", ".join("%s %d" % (k, v) for k, v in w["peaks"].items()) or "none"),
            "**Actions**: %d bans (%d by moderators), %d kicks, %d mutes, %d warnings, %d lifted. %d automatic." % (
                a["ban"], w["bans_by_moderators"], a["kick"], a["mute"], a["warn"], a["unban"], w["auto_actions"]),
            "**Reports**: %d in, %d closed%s, %d still open." % (
                sum(w["reports_in"].values()), w["reports_closed"],
                ", median %s to close" % human_length(max(1, w["median_close_minutes"])) if w["median_close_minutes"] is not None else "",
                w["open_now"]),
        ]
        if w["appeals"]:
            lines.append("**Appeals**: " + ", ".join("%d %s" % (v, k) for k, v in w["appeals"].items()) + ".")
        if w["flags"]:
            lines.append("**Flags**: " + ", ".join("%d %s" % (v, k) for k, v in sorted(w["flags"].items(), key=lambda kv: -kv[1])) + ".")
        if w["staff"]:
            lines.append("**Most active staff**: " + ", ".join("%s %d" % (s["staff"], s["n"]) for s in w["staff"][:5]) + ".")
        return "\n".join(lines)

    def weekly_loop(self) -> None:
        while not self.stop.is_set():
            local = brussels(time.time())
            week = "%d-W%02d" % local.isocalendar()[:2]
            if local.weekday() == 0 and local.hour >= 8 and self.meta("weekly_sent") != week:
                self.meta("weekly_sent", week)
                self.alert("weekly", "Staff report, week %s" % week.split("-W")[1], self.weekly_text(self.weekly()), key="weekly:" + week)
            self.stop.wait(600)

    def meta(self, key: str, value: str | None = None) -> str | None:
        if value is None:
            r = self.store.one("SELECT value FROM meta WHERE key=?", (key,))
            return r["value"] if r else None
        self.store.x("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        return value

    # -- server demos for reports
    def demo_for(self, report_id: int) -> dict:
        r = self.store.one("SELECT * FROM reports WHERE id=?", (report_id,))
        if not r or r["source"] not in ("player", "auto"):
            raise ApiError(404, "No such player report.")
        srv = self.servers.get(r["server"])
        if not srv:
            raise ApiError(404, "The server of this report is no longer configured.")
        folder = srv.cfg.get("demos_dir") or (str(Path(srv.cfg["reports_dir"]).parent / "svdemos") if srv.cfg.get("reports_dir") else "")
        try:
            data = json.loads(r["data"])
        except ValueError:
            data = {}
        when = iso_to_unix(data.get("time")) or r["received"]
        try:
            from zoneinfo import ZoneInfo
            import datetime as dt
            zone = ZoneInfo(srv.cfg.get("demo_timezone", self.cfg.get("demo_timezone", "UTC")))
        except Exception:  # noqa: BLE001
            import datetime as dt
            zone = dt.timezone.utc
        best = None
        try:
            files = list(Path(folder).glob("*.sv*")) if folder else []
        except OSError:
            files = []
        for f in files:
            m = DEMO_NAME.search(f.name)
            if not m:
                continue
            try:
                begin = int(dt.datetime(*map(int, m.groups()), tzinfo=zone).timestamp())
                st = f.stat()
            except (ValueError, OSError):
                continue
            if begin <= when <= int(st.st_mtime) + 5 and (best is None or begin > best[1]):
                best = (f, begin, st.st_size)
        if not best:
            raise ApiError(404, "No server demo covers this moment. Servers record demos only while sv_autoDemo is on "
                                "(Settings page), and old demos are cleaned up.")
        f, begin, size = best
        return {"file": f.name, "path": str(f), "offset_s": when - begin, "size": size, "server": srv.key, "at": when}

    # -- website insights (tcp_insights.py on this machine; key from the systemd credential 'insights-key')
    def insights(self, days: int) -> dict:
        base = self.cfg.get("insights_api", "http://127.0.0.1:8094")
        cred = os.environ.get("CREDENTIALS_DIRECTORY")
        key = ""
        if cred and (Path(cred) / "insights-key").exists():
            key = (Path(cred) / "insights-key").read_text(encoding="utf-8").strip()
        key = key or str(self.cfg.get("insights_key", "") or "")
        if not base or not key:
            raise ApiError(409, "Website insights are not connected yet (run install.sh insights-link on the VPS).")
        req = urllib.request.Request("%s/insights/stats.json?days=%d" % (base.rstrip("/"), days),
                                     headers={"Authorization": "Bearer " + key, "User-Agent": "TCPStaff"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise ApiError(502 if e.code >= 500 else 409, "The insights service said: %s" % e.code) from e
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise ApiError(502, "The insights service did not answer.") from e

    # -- devlog comments (tools/accounts/tcp_comments.py: the accounts service's /internal/comments/*, loopback only;
    #    token from the systemd credential 'accounts-token', filled by install.sh accounts-link)
    def accounts_token(self) -> str:
        cred = os.environ.get("CREDENTIALS_DIRECTORY")
        token = ""
        if cred and (Path(cred) / "accounts-token").exists():
            token = (Path(cred) / "accounts-token").read_text(encoding="utf-8").strip()
        return token or str(self.cfg.get("accounts_token", "") or "")

    def comments_api(self, method: str, sub: str, body: dict | None = None, qs: dict | None = None) -> dict:
        base = str(self.cfg.get("accounts_api", "http://127.0.0.1:8095")).rstrip("/")
        token = self.accounts_token()
        if not token:
            raise ApiError(409, "Devlog comments are not connected yet (run install.sh accounts-link on the VPS).")
        url = "%s/internal/comments/%s" % (base, sub)
        if qs:
            url += "?" + urllib.parse.urlencode({k: v for k, v in qs.items() if v not in (None, "")})
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "X-Accounts-Token": token, "User-Agent": "TCPStaff", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode()).get("error") or ""
            except (ValueError, OSError, AttributeError):
                msg = ""
            if e.code == 404 and msg in ("", "Not found."):     # an old accounts service, or a token it does not know
                msg = "The accounts service refused: it needs accounts 1.3.0 and the token from install.sh accounts-link."
            raise ApiError(e.code if 400 <= e.code < 500 else 502, msg or "The accounts service said: %s" % e.code) from e
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise ApiError(502, "The accounts service did not answer.") from e

    def comments_loop(self) -> None:
        """Every minute: when more comments wait for staff than before, one alert (no comment text in it)."""
        while not self.stop.is_set():
            if self.accounts_token():
                try:
                    st = self.comments_api("GET", "stats")
                    n = int(st.get("needs") or 0)
                    last = int(self.meta("comments_needs") or 0)
                    if n > last:
                        held, rep = int(st.get("held") or 0), int(st.get("reported") or 0) + int(st.get("hidden") or 0)
                        self.alert("comments", "Devlog comments: %d waiting" % n,
                                   "%d held for a check, %d reported or hidden. Open Devlog comments in the portal." % (held, rep),
                                   key="comments:%d:%d" % (n, now() // 600))
                    if n != last:
                        self.meta("comments_needs", str(n))
                except ApiError as e:
                    log.debug("comments check: %s", e.message)
            self.stop.wait(60)

    def comments_audit(self, who: dict, action: str, row: dict | None, detail: str = "") -> None:
        author = ((row or {}).get("author") or {})
        target = author.get("name", "")
        text = ((row or {}).get("text") or "").replace("\n", " ")
        self.store.audit(who, "comment." + action, target=target,
                         detail=(detail + " · " if detail else "") + ("#%s on %s: %s" % ((row or {}).get("id", ""), (row or {}).get("post", ""), text[:200]) if row else ""))

    # -- stats review queue (the stats service's staff routes, loopback only)
    def stats_staff(self, method: str, route: str, body: dict | None = None):
        base = self.cfg.get("stats_api")
        cred = os.environ.get("CREDENTIALS_DIRECTORY")
        token = ""
        if cred and (Path(cred) / "stats-token").exists():
            token = (Path(cred) / "stats-token").read_text(encoding="utf-8").strip()
        token = token or str(self.cfg.get("stats_token", "") or "")
        if not base or not token:
            raise ApiError(409, "The stats review queue is not connected yet (stats service token missing).")
        req = urllib.request.Request("%s%s" % (base.rstrip("/"), route), method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"X-Staff-Token": token, "Content-Type": "application/json", "User-Agent": "TCPStaff"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode()).get("error", "")
            except (ValueError, OSError):
                msg = ""
            raise ApiError(502 if e.code >= 500 else 409, "The stats service said: %s" % (msg or e.code)) from e
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise ApiError(502, "The stats service did not answer.") from e

    # -- live map
    def map_layouts(self) -> dict:
        if self._layouts is None:
            try:
                self._layouts = json.loads((STATIC / "maps" / "maps.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._layouts = {}
        return self._layouts

    def positions(self, srv: GameServer) -> dict:
        v = srv.view()
        layout = self.map_layouts().get(v.get("map", ""))
        with srv.lock:
            pos = {k: dict(p) for k, p in srv.positions.items()}
            at = srv.positions_at
        bots = {p["slot"]: p["bot"] for p in v.get("players", [])}
        spec = {p["slot"]: p.get("spectator") for p in v.get("players", [])}
        out = []
        for slot, p in sorted(pos.items()):
            if not p.get("begun") or spec.get(slot) or p["team"] not in (1, 2):
                continue
            item = {"slot": slot, "name": p["name"], "team": p["team"], "alive": p["hp"] > 0, "hp": p["hp"], "bot": bots.get(slot, False)}
            if layout:
                (x0, y0), (x1, y1) = layout["mins"], layout["maxs"]
                item["u"] = round((p["x"] - x0) / (x1 - x0), 4)
                item["v"] = round((y1 - p["y"]) / (y1 - y0), 4)
            out.append(item)
        return {"server": srv.key, "map": v.get("map", ""), "layout": {"image": "/static/maps/" + layout["image"], "w": layout["w"],
                "h": layout["h"]} if layout else None, "players": out, "updated": at}


# ----------------------------------------------------------------------------- overview (1.4)
# The home dashboard, global search, player-count samples for the history charts, and the nightly database
# snapshot that the off-site backup picks up.

MODERATION_ACTIONS = ("kick", "warn", "mute", "unmute", "ban", "unban", "move", "undo ban", "undo mute", "report closed",
                      "report claimed", "appeal accepted", "appeal denied", "watch")
APPEAL_CODE = re.compile(r"^[A-HJ-NP-Z2-9]{6}$")


class Overview:
    # -- player-count samples (every sample_seconds, 90 days): the dashboard sparkline and the history page
    def record_samples(self, force: bool = False) -> int:
        t = now()
        every = int(self.cfg.get("sample_seconds", 300))
        if not force and t - getattr(self, "_sampled_at", 0) < every:
            return 0
        self._sampled_at = t
        n = 0
        for key in self.order:
            v = self.servers[key].view()
            online = bool(v.get("online"))
            self.store.x("INSERT INTO samples(at,server,online,humans,bots,map) VALUES(?,?,?,?,?,?)",
                         (t, key, 1 if online else 0, int(v.get("humans") or 0) if online else 0,
                          int(v.get("bots") or 0) if online else 0, str(v.get("map") or "")[:48]))
            n += 1
        return n

    # -- the home dashboard
    def dashboard(self, who: dict) -> dict:
        t = now()
        out = {"time": t, "version": VERSION}
        servers = []
        for key in self.order:
            v = self.servers[key].view()
            servers.append({k: v.get(k) for k in ("key", "name", "online", "humans", "bots", "max_players", "map", "mode",
                                                  "ranked", "eac", "error", "kind", "needpass")})
        out["servers"] = servers
        out["players_online"] = sum(int(s["humans"] or 0) for s in servers if s["online"])
        out["servers_up"] = sum(1 for s in servers if s["online"])
        if allowed(who, "reports"):
            rows = self.store.q("SELECT source, status, COUNT(*) n FROM reports WHERE status<>'closed' GROUP BY source, status")
            out["reports"] = {"open": sum(r["n"] for r in rows if r["status"] == "open"),
                              "claimed": sum(r["n"] for r in rows if r["status"] == "claimed"),
                              "by_source": {}}
            for r in rows:
                out["reports"]["by_source"][r["source"]] = out["reports"]["by_source"].get(r["source"], 0) + r["n"]
            out["reports"]["mine"] = self.store.one("SELECT COUNT(*) n FROM reports WHERE status='claimed' AND claimed_by=?",
                                                    (who.get("name", ""),))["n"]
            oldest = self.store.one("SELECT MIN(received) t FROM reports WHERE status='open' AND source IN ('player','auto','appeal')")
            out["reports"]["oldest_open"] = oldest["t"] if oldest else None
        out["on_duty"] = [{"name": d["name"], "until": d["until"]} for d in self.duty_list()]
        if allowed(who, "cases"):
            out["cases"] = {"open": self.store.one("SELECT COUNT(*) n FROM cases WHERE status='open'")["n"],
                            "mine": self.store.one("SELECT COUNT(*) n FROM cases WHERE status='open' AND assignee=?",
                                                   (who.get("name", ""),))["n"]}
        out["alerts"] = self.store.q("SELECT id, at, kind, title, pid, server FROM alerts WHERE at>? ORDER BY id DESC LIMIT 8",
                                     (t - 86400,))
        out["alerts_24h"] = self.store.one("SELECT COUNT(*) n FROM alerts WHERE at>?", (t - 86400,))["n"]
        out["urgent_24h"] = self.store.one("SELECT COUNT(*) n FROM alerts WHERE at>? AND kind IN ('server_down','dodger','suspicion')",
                                           (t - 86400,))["n"]
        marks = ",".join("?" * len(MODERATION_ACTIONS))
        out["activity"] = self.store.q("SELECT id, at, staff, role, action, server, target, target_pid FROM audit WHERE ok=1 AND "
                                       "action IN (%s) ORDER BY id DESC LIMIT 12" % marks, MODERATION_ACTIONS)
        online = {p.get("pid"): (s.key, p["name"]) for s in self.servers.values() for p in s.view().get("players", []) if p.get("pid")}
        sus = self.store.q("SELECT pid, name, score, reasons FROM suspicion WHERE updated>? AND score>=25 ORDER BY score DESC LIMIT 5",
                           (t - 600,))
        for r in sus:
            r["reasons"] = json.loads(r["reasons"] or "[]")[:2]
            r["server"] = online.get(r["pid"], ("", ""))[0]
        out["suspicion"] = sus
        watched = self.store.q("SELECT pid, name, reason FROM watchlist")
        out["watch_online"] = [dict(w, server=online[w["pid"]][0]) for w in watched if w["pid"] in online]
        out["bans_24h"] = self.store.one("SELECT COUNT(*) n FROM bans WHERE created>?", (t - 86400,))["n"]
        out["bans_active"] = self.store.one("SELECT COUNT(*) n FROM bans WHERE active=1")["n"]
        out["appeals_open"] = self.store.one("SELECT COUNT(*) n FROM appeals WHERE status='open'")["n"]
        out["schedule"] = self.store.q("SELECT id, server, action, arg, next_at, every_min FROM schedule WHERE active=1 "
                                       "ORDER BY next_at LIMIT 4")
        out["events"] = self.store.q("SELECT server, started, by_name, note FROM events")
        # players online over the last 24 hours, every server added up, one point per sample time
        rows = self.store.q("SELECT at, SUM(humans) humans FROM samples WHERE at>? GROUP BY at ORDER BY at", (t - 86400,))
        out["spark"] = [[r["at"], r["humans"]] for r in rows]
        day = time.strftime("%Y-%m-%d", time.gmtime(t))
        peak = self.store.one("SELECT MAX(s) p FROM (SELECT SUM(humans) s FROM samples WHERE at>=? GROUP BY at)",
                              (t - t % 86400,))
        out["peak_today"] = max(int((peak or {}).get("p") or 0), out["players_online"])
        out["new_players_24h"] = self.store.one("SELECT COUNT(*) n FROM (SELECT pid, MIN(first_seen) f FROM sightings GROUP BY pid) "
                                                "WHERE f>?", (t - 86400,))["n"]
        out["day"] = day
        if allowed(who, "health"):
            h = self.health()
            out["services_down"] = [{"name": u["name"], "state": u["state"]} for u in h.get("services", [])
                                    if u.get("state") not in ("active", "unknown")]
            if h.get("disk_total_gb"):
                out["disk_used_pct"] = round(100 - 100 * h["disk_free_gb"] / h["disk_total_gb"])
            if h.get("mem_total_mb"):
                out["mem_used_pct"] = round(100 - 100 * h["mem_available_mb"] / h["mem_total_mb"])
        if allowed(who, "audit"):
            out["backup"] = self.backup_status()
        return out

    # -- global search (Ctrl+K)
    def search(self, who: dict, query: str) -> dict:
        q = str(query or "").strip()[:80]
        out = {"q": q, "players": [], "online": [], "bans": [], "reports": [], "staff": []}
        if not q:
            return out
        low = q.lower().lstrip("@")
        for s in self.servers.values():
            for p in s.view().get("players", []):
                if p.get("bot"):
                    continue
                if low in plain(p["name"]).lower() or (p.get("pid") and p["pid"] == low):
                    out["online"].append({"server": s.key, "server_name": s.name, "slot": p["slot"], "name": p["name"],
                                          "pid": p.get("pid", ""), "muted": bool(p.get("muted_s"))})
        out["online"] = out["online"][:8]
        if allowed(who, "lookup") and len(q) >= 2:
            out["players"] = self.lookup(q, allowed(who, "lookup.ip"))[:8]
        num = re.fullmatch(r"#?(\d{1,9})", q)
        code = q.upper() if APPEAL_CODE.match(q.upper()) else ""
        if num:
            out["bans"] = self.store.q("SELECT id, pid, name, reason, active, expires FROM bans WHERE id=?", (int(num.group(1)),))
        elif code:
            out["bans"] = self.store.q("SELECT id, pid, name, reason, active, expires FROM bans WHERE appeal_code=?", (code,))
        if len(q) >= 2 and not out["bans"]:
            like = "%" + q.replace("%", "").replace("_", "") + "%"
            out["bans"] = self.store.q("SELECT id, pid, name, reason, active, expires FROM bans WHERE name LIKE ? OR reason LIKE ? "
                                       "ORDER BY active DESC, id DESC LIMIT 5", (like, like))
        if allowed(who, "reports"):
            if num:
                rows = self.store.q("SELECT * FROM reports WHERE id=?", (int(num.group(1)),))
            elif len(q) >= 3:
                like = "%" + q.replace("%", "").replace("_", "") + "%"
                rows = self.store.q("SELECT * FROM reports WHERE target_name LIKE ? OR data LIKE ? ORDER BY id DESC LIMIT 5", (like, like))
            else:
                rows = []
            for r in rows:
                d = self._report_row(r).get("data") or {}
                out["reports"].append({"id": r["id"], "source": r["source"], "status": r["status"], "target_name": r["target_name"],
                                       "target_pid": r["target_pid"], "received": r["received"],
                                       "summary": str(d.get("summary") or d.get("reason") or d.get("text") or "")[:120]})
        out["cases"] = []
        if allowed(who, "cases"):
            cnum = re.fullmatch(r"(?:case\s*)?#?(\d{1,9})", q, re.I)
            if cnum:
                out["cases"] = self.store.q("SELECT id, title, status, name, pid, assignee FROM cases WHERE id=?", (int(cnum.group(1)),))
            if len(q) >= 3 and not out["cases"]:
                like = "%" + q.replace("%", "").replace("_", "") + "%"
                out["cases"] = self.store.q("SELECT id, title, status, name, pid, assignee FROM cases WHERE title LIKE ? OR name LIKE ? "
                                            "OR pid=? ORDER BY status='closed', updated DESC LIMIT 5", (like, like, q))
        if allowed(who, "staff.manage") and len(q) >= 2:
            like = "%" + q.replace("%", "").replace("_", "") + "%"
            out["staff"] = self.store.q("SELECT discord_id, name, role, last_login FROM staff WHERE name LIKE ? OR discord_id=? LIMIT 5",
                                        (like, q))
        return out

    # -- nightly database snapshot for the off-site backup
    # The copy leaves out sign-in sessions (they hold Discord tokens), one-time key links and the undo list; the
    # off-site backup (tcp_offsite_backup.py) encrypts it with its own passphrase before it leaves the machine.
    def backup_dir(self) -> Path:
        return Path(self.cfg.get("data_dir", "/var/lib/tcp-staff-portal")) / "backups"

    def backup_now(self) -> dict:
        d = self.backup_dir()
        d.mkdir(parents=True, exist_ok=True)
        os.chmod(d, 0o750)
        tmp = d / (".snapshot-%s.tmp" % secrets.token_hex(4))
        status = {"at": now(), "ok": False}
        try:
            dst = sqlite3.connect(str(tmp))
            try:
                with self.store.lock:
                    self.store.db.backup(dst)
                for table in ("sessions", "staff_key_codes", "undo"):
                    dst.execute("DELETE FROM %s" % table)
                dst.commit()
                dst.execute("VACUUM")
                tables = dst.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
                ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                dst.close()
            if ok != "ok":
                raise sqlite3.DatabaseError("integrity check: %s" % ok)
            os.chmod(tmp, 0o640)
            target = d / "portal-snapshot.db"
            os.replace(tmp, target)
            h = hashlib.sha256(target.read_bytes()).hexdigest()
            status.update(ok=True, file=str(target), size=target.stat().st_size, sha256=h, tables=tables)
        except (OSError, sqlite3.Error) as e:
            status["error"] = str(e)[:300]
            log.warning("database snapshot failed: %s", e)
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
        self.meta("backup_status", json.dumps(status))
        if not status["ok"]:
            self.alert("backup", "Staff portal snapshot failed", status.get("error", "unknown error"), key="backup-fail", window=20 * 3600)
        return status

    def backup_status(self) -> dict:
        try:
            st = json.loads(self.meta("backup_status") or "{}")
        except ValueError:
            st = {}
        st["hour_utc"] = self.cfg.get("backup_time_utc", "04:20")
        st["stale"] = not st.get("ok") or now() - int(st.get("at") or 0) > 30 * 3600
        return st

    def backup_loop(self) -> None:
        while not self.stop.is_set():
            hh, _, mm = str(self.cfg.get("backup_time_utc", "04:20")).partition(":")
            g = time.gmtime()
            day = time.strftime("%Y-%m-%d", g)
            due = (g.tm_hour, g.tm_min) >= (int(hh or 4), int(mm or 0))
            if due and self.meta("backup_day") != day:
                self.meta("backup_day", day)
                self.backup_now()
            self.stop.wait(300)


# ----------------------------------------------------------------------------- the portal

# ----------------------------------------------------------------------------- live updates, cases, timeline, evidence (1.4.1)

class EventBus:
    """What changed, for the open portal pages (/api/stream). Events name a kind and an id, never content: the page asks
    the normal API for the data, so every permission check stays where it is."""

    def __init__(self, keep: int = 300):
        self.cond = threading.Condition()
        self.seq = 0
        self.items = collections.deque(maxlen=keep)
        self.streams = {}                       # discord_id -> open streams
        self.lock = threading.Lock()

    def emit(self, event: str, **data) -> None:
        with self.cond:
            if event == "servers" and self.items and self.items[-1][1] == "servers":
                self.items.pop()                # one pending "servers" is enough
            self.seq += 1
            self.items.append((self.seq, event, data))
            self.cond.notify_all()

    def since(self, after: int, timeout: float) -> list:
        with self.cond:
            if after > self.seq:                # the portal restarted: start from now
                after = self.seq
            if not self.items or self.items[-1][0] <= after:
                self.cond.wait(timeout)
            return [i for i in self.items if i[0] > after]

    def open(self, who: str, per_person: int, total: int) -> bool:
        with self.lock:
            if self.streams.get(who, 0) >= per_person or sum(self.streams.values()) >= total:
                return False
            self.streams[who] = self.streams.get(who, 0) + 1
            return True

    def close(self, who: str) -> None:
        with self.lock:
            n = self.streams.get(who, 0) - 1
            if n > 0:
                self.streams[who] = n
            else:
                self.streams.pop(who, None)


CASE_LINKS = ("report", "ban", "appeal", "action", "evidence")
IMAGE_MAGIC = ((b"\xff\xd8\xff", "image/jpeg", "jpg"), (b"\x89PNG\r\n\x1a\n", "image/png", "png"))


def image_kind(data: bytes):
    for magic, mime, ext in IMAGE_MAGIC:
        if data.startswith(magic):
            return mime, ext
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


class Casework:
    # -- play sessions, for the player timeline
    def track_sessions(self, srv, online: dict, names: dict, up: bool) -> None:
        t = now()
        before = self.session_open.get(srv.key, set())
        current = set(online) if up else set()
        for pid in current - before:
            self.store.x("INSERT INTO player_sessions(pid,server,name,joined) VALUES(?,?,?,?)", (pid, srv.key, names.get(pid, "")[:64], t))
        for pid in before - current:
            self.store.x("UPDATE player_sessions SET left_at=? WHERE pid=? AND server=? AND left_at IS NULL", (t, pid, srv.key))
        self.session_open[srv.key] = current

    def close_stale_sessions(self) -> None:
        """After a restart: sessions left open end at the player's last sighting on that server."""
        self.store.x("UPDATE player_sessions SET left_at=MAX(joined, COALESCE((SELECT MAX(last_seen) FROM sightings s WHERE "
                     "s.pid=player_sessions.pid AND s.server=player_sessions.server), joined)) WHERE left_at IS NULL")

    def timeline(self, pid: str, show_ip: bool) -> dict:
        if not PID.match(pid):
            raise ApiError(400, "That is not a player id.")
        ev = []

        def add(at, kind, title, detail="", server="", tone="", link="", **extra):
            if at:
                ev.append(dict(at=int(at), kind=kind, title=title, detail=str(detail or "")[:300], server=server or "",
                               tone=tone, link=link, **extra))
        chat_at = [r["at"] for r in self.store.q("SELECT at FROM chat WHERE pid=? ORDER BY at DESC LIMIT 5000", (pid,))]
        for s in self.store.q("SELECT * FROM player_sessions WHERE pid=? ORDER BY joined DESC LIMIT 200", (pid,)):
            end = s["left_at"] or now()
            said = sum(1 for a in chat_at if s["joined"] <= a <= end)
            add(s["joined"], "session", "Played on %s" % s["server"], "as %s" % s["name"], s["server"],
                until=s["left_at"], minutes=max(1, (end - s["joined"]) // 60), chat=said)
        names = {}
        for r in self.store.q("SELECT name, MIN(first_seen) f FROM sightings WHERE pid=? GROUP BY name", (pid,)):
            names[r["name"]] = r["f"]
        first = min(names.values(), default=None)
        for n, f in names.items():
            add(f, "name", "First seen" if f == first else "New name", n)
        for b in self.store.q("SELECT * FROM bans WHERE pid=?", (pid,)):
            add(b["created"], "ban", "Banned" + ("" if b["expires"] else " permanently"), b["reason"], tone="bad", by=b["by_name"],
                ref=b["id"], expires=b["expires"])
            if b["lifted"]:
                add(b["lifted"], "unban", "Ban lifted", b["lift_reason"], tone="ok", by=b["lifted_by"], ref=b["id"])
        for m in self.store.q("SELECT * FROM mutes WHERE pid=?", (pid,)):
            add(m["created"], "mute", "Muted", m["reason"], m["server"] or "", tone="warn", by=m["by_name"])
        for w in self.store.q("SELECT * FROM warnings WHERE pid=?", (pid,)):
            add(w["created"], "warning", "Warned", w["text"], w["server"], tone="warn", by=w["by_name"])
        for a in self.store.q("SELECT * FROM audit WHERE target_pid=? AND ok=1 AND action IN ('kick','move','unmute','watch',"
                              "'unwatch','undo ban','undo mute') ORDER BY id DESC LIMIT 200", (pid,)):
            add(a["at"], "action", a["action"].capitalize(), a["detail"], a["server"], by=a["staff"], ref=a["id"])
        for n in self.store.q("SELECT * FROM notes WHERE pid=?", (pid,)):
            add(n["created"], "note", "Staff note", n["text"], by=n["by_name"])
        for r in self.store.q("SELECT * FROM reports WHERE target_pid=? ORDER BY id DESC LIMIT 100", (pid,)):
            d = self._report_row(r).get("data") or {}
            title = {"auto": "Automatic flag", "appeal": "Ban appeal", "bug": "Sent a bug report"}.get(r["source"], "Reported")
            add(r["received"], "report", title, d.get("reason") or d.get("summary") or d.get("text") or "", r["server"],
                tone="" if r["source"] == "bug" else "warn", ref=r["id"], status=r["status"])
        for f in self.store.q("SELECT * FROM flags WHERE pid=? ORDER BY id DESC LIMIT 100", (pid,)):
            add(f["at"], "flag", f["kind"].capitalize(), f["detail"], f["server"], tone="bad" if f["kind"] == "ban dodger" else "warn")
        for a in self.store.q("SELECT * FROM alerts WHERE pid=? AND kind IN ('watch','suspicion','reports') ORDER BY id DESC LIMIT 50", (pid,)):
            add(a["at"], "alert", plain(a["title"]), plain(a["text"]).replace("**", ""), a["server"])
        for p in self.store.q("SELECT * FROM punishments WHERE pid=?", (pid,)):
            add(p["created"], "ladder", "Punishment ladder: %s" % self.ladder().get(p["offence"], {}).get("label", p["offence"]),
                step_label(p["step"]), p["server"], by=p["by_name"])
        for c in self.store.q("SELECT * FROM cases WHERE pid=?", (pid,)):
            add(c["created"], "case", "Case #%d opened" % c["id"], c["title"], by=c["created_by"], link="#/case/%d" % c["id"])
        for e in self.store.q("SELECT id, kind, title, at, by_name, case_id FROM evidence WHERE pid=? AND deleted=0", (pid,)):
            add(e["at"], "evidence", "Evidence saved", e["title"], by=e["by_name"],
                link=("#/case/%d" % e["case_id"]) if e["case_id"] else "")
        ev.sort(key=lambda e: -e["at"])
        return {"pid": pid, "events": ev[:600], "online": [s.key for s in self.servers.values()
                                                           for p in s.view().get("players", []) if p.get("pid") == pid]}

    # -- cases: one place for everything about one problem
    def case_row(self, cid: int) -> dict:
        c = self.store.one("SELECT * FROM cases WHERE id=?", (int(cid or 0),))
        if not c:
            raise ApiError(404, "No such case.")
        return c

    def cases(self, status: str = "open", mine: str = "", pid: str = "") -> list:
        where, args = [], []
        if status in ("open", "closed"):
            where.append("status=?")
            args.append(status)
        if mine:
            where.append("assignee=?")
            args.append(mine)
        if pid:
            where.append("pid=?")
            args.append(pid)
        return self.store.q("SELECT c.*, (SELECT COUNT(*) FROM case_items i WHERE i.case_id=c.id) items, (SELECT COUNT(*) FROM "
                            "evidence e WHERE e.case_id=c.id AND e.deleted=0) evidence FROM cases c%s ORDER BY status='closed', "
                            "updated DESC LIMIT 300" % (" WHERE " + " AND ".join(where) if where else ""), args)

    def case_open(self, who: dict, title: str, pid: str = "", name: str = "", summary: str = "", report: int = 0) -> int:
        r = None
        if report:
            r = self.store.one("SELECT * FROM reports WHERE id=?", (int(report),))
            if not r:
                raise ApiError(404, "No such report.")
            pid = pid or r["target_pid"] or ""
            name = name or r["target_name"] or ""
        if pid and not PID.match(pid):
            raise ApiError(400, "That is not a player id.")
        if pid and not name:
            n = self.store.one("SELECT name FROM sightings WHERE pid=? ORDER BY last_seen DESC LIMIT 1", (pid,))
            name = n["name"] if n else ""
        title = str(title or "").strip()[:120] or ("%s" % (name or "New case"))
        t = now()
        cid = self.store.x("INSERT INTO cases(title,status,pid,name,summary,assignee,created,created_by,updated) VALUES(?,?,?,?,?,?,?,?,?)",
                           (title, "open", pid, plain(name)[:64], str(summary or "")[:2000], who["name"], t, who["name"], t))
        if r:
            self.case_link(who, cid, "report", r["id"], quiet=True)
        self.store.audit(who, "case opened", target=name or title, pid=pid, detail="#%d %s" % (cid, title))
        self.bus.emit("cases", id=cid)
        return cid

    def case_update(self, who: dict, cid: int, d: dict) -> dict:
        c = self.case_row(cid)
        sets, args, notes = [], [], []
        if "title" in d and str(d["title"]).strip():
            sets.append("title=?")
            args.append(str(d["title"]).strip()[:120])
        if "summary" in d:
            sets.append("summary=?")
            args.append(str(d["summary"] or "")[:2000])
        if "assignee" in d:
            a = who["name"] if d["assignee"] == "me" else str(d["assignee"] or "")[:64]
            sets.append("assignee=?")
            args.append(a)
            notes.append("taken by %s" % a if a else "left unassigned")
        if d.get("status") in ("open", "closed") and d["status"] != c["status"]:
            sets.append("status=?")
            args.append(d["status"])
            if d["status"] == "closed":
                outcome = str(d.get("outcome") or "").strip()[:500]
                if not outcome:
                    raise ApiError(400, "Write what came out of the case before you close it.")
                sets.append("outcome=?")
                args.append(outcome)
                notes.append("closed: " + outcome)
            else:
                notes.append("reopened")
        if not sets:
            raise ApiError(400, "Nothing to change.")
        sets.append("updated=?")
        args.append(now())
        self.store.x("UPDATE cases SET %s WHERE id=?" % ", ".join(sets), args + [c["id"]])
        for n in notes:
            self.store.x("INSERT INTO case_items(case_id,at,by_name,kind,ref,text) VALUES(?,?,?,?,NULL,?)",
                         (c["id"], now(), who["name"], "status", n))
        action = "case closed" if d.get("status") == "closed" and c["status"] != "closed" else "case updated"
        self.store.audit(who, action, target=c["name"] or c["title"], pid=c["pid"], detail="#%d %s" % (c["id"], "; ".join(notes))[:300])
        self.bus.emit("cases", id=c["id"])
        return self.case_row(c["id"])

    def case_link(self, who: dict, cid: int, kind: str, ref: int, quiet: bool = False) -> None:
        c = self.case_row(cid)
        if kind not in CASE_LINKS:
            raise ApiError(400, "Unknown kind of item.")
        table = {"report": "reports", "ban": "bans", "appeal": "appeals", "action": "audit", "evidence": "evidence"}[kind]
        if not self.store.one("SELECT id FROM %s WHERE id=?" % table, (int(ref),)):
            raise ApiError(404, "That %s does not exist." % kind)
        if self.store.one("SELECT id FROM case_items WHERE case_id=? AND kind=? AND ref=?", (c["id"], kind, int(ref))):
            raise ApiError(409, "Already in this case.")
        self.store.x("INSERT INTO case_items(case_id,at,by_name,kind,ref,text) VALUES(?,?,?,?,?,'')", (c["id"], now(), who["name"], kind, int(ref)))
        if kind == "evidence":
            self.store.x("UPDATE evidence SET case_id=? WHERE id=? AND case_id IS NULL", (c["id"], int(ref)))
        self.store.x("UPDATE cases SET updated=? WHERE id=?", (now(), c["id"]))
        if not quiet:
            self.bus.emit("cases", id=c["id"])

    def case_note(self, who: dict, cid: int, text: str) -> None:
        c = self.case_row(cid)
        text = str(text or "").strip()[:2000]
        if not text:
            raise ApiError(400, "Write a note first.")
        self.store.x("INSERT INTO case_items(case_id,at,by_name,kind,ref,text) VALUES(?,?,?,?,NULL,?)", (c["id"], now(), who["name"], "note", text))
        self.store.x("UPDATE cases SET updated=? WHERE id=?", (now(), c["id"]))
        self.bus.emit("cases", id=c["id"])

    def case_unlink(self, who: dict, cid: int, item: int) -> None:
        c = self.case_row(cid)
        it = self.store.one("SELECT * FROM case_items WHERE id=? AND case_id=?", (int(item), c["id"]))
        if not it:
            raise ApiError(404, "No such item in this case.")
        if it["kind"] == "status":
            raise ApiError(409, "Status changes stay in the case history.")
        if it["kind"] == "note" and it["by_name"] != who["name"] and not allowed(who, "audit"):
            raise ApiError(403, "Only the writer or an admin removes a note.")
        self.store.x("DELETE FROM case_items WHERE id=?", (it["id"],))
        if it["kind"] == "evidence":
            self.store.x("UPDATE evidence SET case_id=NULL WHERE id=? AND case_id=?", (it["ref"], c["id"]))
        self.store.audit(who, "case updated", target=c["name"] or c["title"], pid=c["pid"],
                         detail="#%d removed %s%s" % (c["id"], it["kind"], (" #%d" % it["ref"]) if it["ref"] else ""))
        self.bus.emit("cases", id=c["id"])

    def case_view(self, who: dict, cid: int) -> dict:
        c = self.case_row(cid)
        items = []
        for it in self.store.q("SELECT * FROM case_items WHERE case_id=? ORDER BY at DESC, id DESC", (c["id"],)):
            ref, row = it["ref"], None
            if it["kind"] == "report":
                r = self.store.one("SELECT * FROM reports WHERE id=?", (ref,))
                if r:
                    d = self._report_row(r).get("data") or {}
                    row = {"source": r["source"], "status": r["status"], "server": r["server"], "received": r["received"],
                           "target_name": r["target_name"], "text": str(d.get("reason") or d.get("summary") or d.get("text") or "")[:300]}
            elif it["kind"] == "ban":
                row = self.store.one("SELECT id, name, reason, created, expires, by_name, active, lifted_by FROM bans WHERE id=?", (ref,))
            elif it["kind"] == "appeal":
                row = self.store.one("SELECT id, name, status, text, answer, answered_by, created FROM appeals WHERE id=?", (ref,))
            elif it["kind"] == "action":
                row = self.store.one("SELECT id, at, staff, action, server, target, detail FROM audit WHERE id=?", (ref,))
            elif it["kind"] == "evidence":
                row = self.evidence_row(ref)
            items.append(dict(it, row=row))
        out = dict(c, items=items, evidence=self.evidence_list(case_id=c["id"]))
        if c["pid"]:
            linked = {(i["kind"], i["ref"]) for i in items}
            sug = []
            for r in self.store.q("SELECT id, source, status, received, target_name FROM reports WHERE target_pid=? ORDER BY id DESC LIMIT 15", (c["pid"],)):
                if ("report", r["id"]) not in linked:
                    sug.append({"kind": "report", "ref": r["id"], "at": r["received"], "label": "%s report #%d (%s)" % (r["source"], r["id"], r["status"])})
            for b in self.store.q("SELECT id, reason, created FROM bans WHERE pid=? ORDER BY id DESC LIMIT 10", (c["pid"],)):
                if ("ban", b["id"]) not in linked:
                    sug.append({"kind": "ban", "ref": b["id"], "at": b["created"], "label": "Ban #%d: %s" % (b["id"], b["reason"])})
            for a in self.store.q("SELECT id, code, status, created FROM appeals WHERE pid=? ORDER BY id DESC LIMIT 5", (c["pid"],)):
                if ("appeal", a["id"]) not in linked:
                    sug.append({"kind": "appeal", "ref": a["id"], "at": a["created"], "label": "Appeal #%d (%s)" % (a["id"], a["status"])})
            for a in self.store.q("SELECT id, at, staff, action, detail FROM audit WHERE target_pid=? AND ok=1 AND action IN (%s) "
                                  "ORDER BY id DESC LIMIT 15" % ",".join("?" * len(MODERATION_ACTIONS)), (c["pid"],) + MODERATION_ACTIONS):
                if ("action", a["id"]) not in linked:
                    sug.append({"kind": "action", "ref": a["id"], "at": a["at"], "label": "%s by %s: %s" % (a["action"], a["staff"], a["detail"])[:140]})
            for e in self.store.q("SELECT id, title, at FROM evidence WHERE pid=? AND case_id IS NULL AND deleted=0 ORDER BY id DESC LIMIT 10", (c["pid"],)):
                sug.append({"kind": "evidence", "ref": e["id"], "at": e["at"], "label": "Evidence: %s" % e["title"]})
            out["suggest"] = sorted(sug, key=lambda x: -x["at"])[:30]
        else:
            out["suggest"] = []
        return out

    # -- evidence locker: screenshots, server demos, chat excerpts and links, kept with a case or a player
    def evidence_dir(self) -> Path:
        d = Path(self.cfg.get("data_dir", "/var/lib/tcp-staff-portal")) / "evidence"
        d.mkdir(parents=True, exist_ok=True)
        os.chmod(d, 0o750)
        return d

    def evidence_bytes(self) -> int:
        return int(self.store.one("SELECT COALESCE(SUM(size),0) n FROM (SELECT DISTINCT file, size FROM evidence WHERE deleted=0 "
                                  "AND file<>'')")["n"])

    def evidence_row(self, eid: int):
        e = self.store.one("SELECT id, case_id, pid, kind, title, mime, size, sha256, text, at, by_name FROM evidence WHERE id=? AND deleted=0",
                           (int(eid or 0),))
        if e and e["kind"] in ("chat", "demo"):
            try:
                e["text"] = json.loads(e["text"] or "null")
            except ValueError:
                pass
        return e

    def evidence_list(self, case_id: int = 0, pid: str = "") -> list:
        if case_id:
            rows = self.store.q("SELECT id FROM evidence WHERE case_id=? AND deleted=0 ORDER BY id DESC", (case_id,))
        else:
            rows = self.store.q("SELECT id FROM evidence WHERE pid=? AND deleted=0 ORDER BY id DESC LIMIT 100", (pid,))
        return [self.evidence_row(r["id"]) for r in rows]

    def _store_file(self, data: bytes, ext: str) -> tuple:
        h = hashlib.sha256(data).hexdigest()
        name = "%s.%s" % (h, ext)
        path = self.evidence_dir() / name
        if not path.exists():
            tmp = path.with_suffix(".tmp-%s" % secrets.token_hex(3))
            tmp.write_bytes(data)
            os.chmod(tmp, 0o640)
            os.replace(tmp, path)
        return name, h

    def evidence_add(self, who: dict, d: dict) -> int:
        kind = d.get("kind")
        case_id = int(d.get("case") or 0) or None
        pid = str(d.get("pid") or "")
        if case_id:
            c = self.case_row(case_id)
            pid = pid or c["pid"] or ""
        if pid and not PID.match(pid):
            raise ApiError(400, "That is not a player id.")
        if not case_id and not pid:
            raise ApiError(400, "Evidence belongs to a case or a player.")
        title = str(d.get("title") or "").strip()[:160]
        file, mime, size, h, text = "", "", 0, "", ""
        if kind == "image":
            try:
                data = base64.b64decode(str(d.get("data") or ""), validate=True)
            except (ValueError, binascii.Error) as e:
                raise ApiError(400, "The picture did not arrive in one piece.") from e
            got = image_kind(data)
            if not got:
                raise ApiError(415, "Only JPEG, PNG or WebP pictures.")
            if len(data) > int(self.cfg.get("evidence_image_mb", 8)) * 1024 * 1024:
                raise ApiError(413, "That picture is too big.")
            if self.evidence_bytes() + len(data) > int(self.cfg.get("evidence_quota_mb", 2000)) * 1024 * 1024:
                raise ApiError(507, "The evidence locker is full. An admin can remove old evidence.")
            mime = got[0]
            file, h = self._store_file(data, got[1])
            size = len(data)
            title = title or "Screenshot"
        elif kind == "demo":
            rep = int(d.get("report") or 0)
            dm = self.demo_for(rep)
            limit = int(self.cfg.get("evidence_demo_mb", 300)) * 1024 * 1024
            if dm["size"] > limit:
                raise ApiError(413, "That demo is too big to keep.")
            if self.evidence_bytes() + dm["size"] > int(self.cfg.get("evidence_quota_mb", 2000)) * 1024 * 1024:
                raise ApiError(507, "The evidence locker is full. An admin can remove old evidence.")
            src = Path(dm["path"])
            hs = hashlib.sha256()
            with src.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    hs.update(chunk)
            h = hs.hexdigest()
            ext = src.suffix.lstrip(".")[:8] or "dm"
            file = "%s.%s" % (h, re.sub(r"[^A-Za-z0-9]", "", ext))
            dst = self.evidence_dir() / file
            if not dst.exists():
                tmp = dst.with_suffix(".tmp-%s" % secrets.token_hex(3))
                shutil.copyfile(src, tmp)
                os.chmod(tmp, 0o640)
                os.replace(tmp, dst)
            size = dm["size"]
            text = json.dumps({"file": dm["file"], "offset_s": dm["offset_s"], "server": dm["server"], "report": rep})
            title = title or "Server demo for report #%d" % rep
        elif kind == "chat":
            at = int(d.get("at") or now())
            minutes = max(1, min(60, int(d.get("minutes") or 10)))
            server = str(d.get("server") or "")
            if server and server not in self.servers:
                raise ApiError(400, "Unknown server.")
            if server:
                rows = self.store.q("SELECT server, at, kind, pid, name, text, flag FROM chat WHERE server=? AND at BETWEEN ? AND ? "
                                    "ORDER BY id LIMIT 400", (server, at - minutes * 60, at + minutes * 60))
            elif pid:
                rows = self.store.q("SELECT server, at, kind, pid, name, text, flag FROM chat WHERE pid=? AND at BETWEEN ? AND ? "
                                    "ORDER BY id LIMIT 400", (pid, at - minutes * 60, at + minutes * 60))
            else:
                rows = []
            if not rows:
                raise ApiError(404, "No chat recorded around that time.")
            text = json.dumps(rows)
            title = title or "Chat %s, %d minutes either side" % (time.strftime("%d %b %H:%M UTC", time.gmtime(at)), minutes)
        elif kind == "link":
            url = str(d.get("url") or "").strip()
            if not re.fullmatch(r"https://[^\s<>\"']{4,500}", url):
                raise ApiError(400, "Use a full https:// link.")
            text = url
            title = title or url[:160]
        elif kind == "text":
            text = str(d.get("text") or "").strip()[:4000]
            if not text:
                raise ApiError(400, "Write something first.")
            title = title or "Statement"
        else:
            raise ApiError(400, "Unknown kind of evidence.")
        eid = self.store.x("INSERT INTO evidence(case_id,pid,kind,title,file,mime,size,sha256,text,at,by_name) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (case_id, pid, kind, title, file, mime, size, h, text, now(), who["name"]))
        if case_id:
            self.case_link(who, case_id, "evidence", eid)
        self.store.audit(who, "evidence added", target=title, pid=pid, detail="#%d %s%s" % (eid, kind, (" case #%d" % case_id) if case_id else ""))
        return eid

    def evidence_file(self, eid: int):
        e = self.store.one("SELECT * FROM evidence WHERE id=? AND deleted=0 AND file<>''", (int(eid or 0),))
        if not e:
            raise ApiError(404, "No such file.")
        path = self.evidence_dir() / e["file"]
        if not re.fullmatch(r"[0-9a-f]{64}\.[A-Za-z0-9]{1,8}", e["file"]) or not path.is_file():
            raise ApiError(404, "The file is gone.")
        return e, path

    def evidence_delete(self, who: dict, eid: int, reason: str = "") -> None:
        e = self.store.one("SELECT * FROM evidence WHERE id=? AND deleted=0", (int(eid or 0),))
        if not e:
            raise ApiError(404, "No such evidence.")
        self.store.x("UPDATE evidence SET deleted=? WHERE id=?", (now(), e["id"]))
        self.store.x("DELETE FROM case_items WHERE kind='evidence' AND ref=?", (e["id"],))
        self._drop_file(e["file"])
        self.store.audit(who, "evidence removed", target=e["title"], pid=e["pid"], detail="#%d %s" % (e["id"], reason[:200]))
        if e["case_id"]:
            self.bus.emit("cases", id=e["case_id"])

    def _drop_file(self, file: str) -> None:
        if file and not self.store.one("SELECT id FROM evidence WHERE file=? AND deleted=0", (file,)):
            try:
                (self.evidence_dir() / file).unlink()
            except OSError:
                pass

    def prune_evidence(self) -> None:
        """Evidence outside an open case goes after evidence_days (365); the files go with the last reference."""
        cut = now() - int(self.cfg.get("evidence_days", 365)) * 86400
        for e in self.store.q("SELECT e.id, e.file FROM evidence e LEFT JOIN cases c ON c.id=e.case_id WHERE e.deleted=0 AND e.at<? "
                              "AND (c.id IS NULL OR c.status='closed')", (cut,)):
            self.store.x("UPDATE evidence SET deleted=? WHERE id=?", (now(), e["id"]))
            self._drop_file(e["file"])

# ----------------------------------------------------------------------------- 1.4.2: push, roles, duty, history, quality, anti-cheat queue

# P-256 (secp256r1) for VAPID: Web Push needs an ES256-signed token. Standard library only, so the curve is here.
_P256_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
_P256_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_P256_A = _P256_P - 3
_P256_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
_P256_G = (0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
           0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5)


def _p256_add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    p = _P256_P
    if a[0] == b[0]:
        if (a[1] + b[1]) % p == 0:
            return None
        lam = (3 * a[0] * a[0] + _P256_A) * pow(2 * a[1], p - 2, p) % p
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], p - 2, p) % p
    x = (lam * lam - a[0] - b[0]) % p
    return x, (lam * (a[0] - x) - a[1]) % p


def _p256_mul(k: int, pt=_P256_G):
    out = None
    while k:
        if k & 1:
            out = _p256_add(out, pt)
        pt = _p256_add(pt, pt)
        k >>= 1
    return out


def p256_keypair() -> tuple:
    d = secrets.randbelow(_P256_N - 1) + 1
    x, y = _p256_mul(d)
    return d, b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


def p256_public(d: int) -> bytes:
    x, y = _p256_mul(d)
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


def es256_sign(d: int, msg: bytes) -> bytes:
    z = int.from_bytes(hashlib.sha256(msg).digest(), "big")
    while True:
        k = secrets.randbelow(_P256_N - 1) + 1
        r = _p256_mul(k)[0] % _P256_N
        if not r:
            continue
        s = pow(k, _P256_N - 2, _P256_N) * (z + r * d) % _P256_N
        if s:
            return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def vapid_header(d: int, public: bytes, endpoint: str, subject: str) -> str:
    u = urllib.parse.urlsplit(endpoint)
    head = b64url(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    body = b64url(json.dumps({"aud": "%s://%s" % (u.scheme, u.netloc), "exp": now() + 12 * 3600, "sub": subject},
                             separators=(",", ":")).encode())
    sig = b64url(es256_sign(d, ("%s.%s" % (head, body)).encode()))
    return "vapid t=%s.%s.%s, k=%s" % (head, body, sig, b64url(public))


# browsers' own push services; a subscription anywhere else is refused (the portal would otherwise call any URL)
PUSH_HOSTS = re.compile(r"^(fcm\.googleapis\.com|updates\.push\.services\.mozilla\.com|[a-z0-9.-]+\.push\.apple\.com|"
                        r"[a-z0-9.-]+\.notify\.windows\.com|push\.services\.mozilla\.com)$")

# per-person extras on top of a role (1.4.2); admin-level grants still need two-step sign-in
GRANT_PRESETS = {
    "event-host": {"label": "Event host", "perms": ["event", "schedule", "server.map"]},
    "appeals": {"label": "Appeals reviewer", "perms": ["appeals.answer"]},
    "anticheat": {"label": "Anti-cheat reviewer", "perms": ["anticheat", "review"]},
    "readonly": {"label": "Read only", "remove": ["player.kick", "player.mute", "player.move", "ban.temp", "punish", "chat.reply",
                                                  "server.say"]},
}


def grants_of(row) -> tuple:
    try:
        add = [p for p in json.loads((row or {}).get("perms_add") or "[]") if p in PERMS]
        rem = [p for p in json.loads((row or {}).get("perms_remove") or "[]") if p in PERMS]
    except (TypeError, ValueError):
        add, rem = [], []
    return add, rem


AC_KINDS = {"detection": "Anti-cheat detection", "suspicion": "High suspicion score", "dodger": "Ban dodger or alt", "review": "Stats stand out"}


class Team:
    # -- per-person permissions
    def effective_perms(self, discord_id: str, role: str):
        """None when the person has no extras (the role decides), else the full list of what they may do."""
        if role == "owner":
            return None
        row = self.store.one("SELECT perms_add, perms_remove FROM staff WHERE discord_id=?", (discord_id,))
        add, rem = grants_of(row)
        if not add and not rem:
            return None
        base = {p for p in PERMS if allowed(role, p)}
        return sorted((base | set(add)) - set(rem))

    def set_grants(self, who: dict, did: str, add: list, remove: list) -> dict:
        add = sorted({p for p in add if p in PERMS})
        remove = sorted({p for p in remove if p in PERMS} - set(add))
        if not self.store.one("SELECT discord_id FROM staff WHERE discord_id=?", (did,)):
            raise ApiError(404, "Add this person to the staff list first.")
        if did in {str(x) for x in self.cfg.get("owners", [])}:
            raise ApiError(403, "Owners have every right already.")
        high = [p for p in add if RANK[PERMS[p]] >= RANK["admin"]]
        if high and who.get("role") != "owner":
            raise ApiError(403, "Only the owner grants admin tools: %s." % ", ".join(high))
        if any(p in ("staff.manage", "2fa.reset") for p in add):
            raise ApiError(403, "Staff management comes with the admin role only.")
        self.store.x("UPDATE staff SET perms_add=?, perms_remove=? WHERE discord_id=?", (json.dumps(add), json.dumps(remove), did))
        self.store.x("UPDATE sessions SET checked=0 WHERE discord_id=?", (did,))
        self.store.audit(who, "staff rights", target=did, detail="+%s -%s" % (",".join(add) or "none", ",".join(remove) or "none"))
        return {"add": add, "remove": remove}

    # -- on duty
    def duty_list(self) -> list:
        return self.store.q("SELECT discord_id, name, since, until FROM duty WHERE until>? ORDER BY since", (now(),))

    def duty_set(self, who: dict, on: bool, hours: float = 4) -> dict:
        t = now()
        if on:
            hours = max(0.5, min(12.0, float(hours or 4)))
            self.store.x("INSERT INTO duty(discord_id,name,since,until) VALUES(?,?,?,?) ON CONFLICT(discord_id) DO UPDATE SET "
                         "name=excluded.name, since=CASE WHEN duty.until>? THEN duty.since ELSE excluded.since END, until=excluded.until",
                         (who["discord_id"], who["name"], t, t + int(hours * 3600), t))
        else:
            self.store.x("UPDATE duty SET until=? WHERE discord_id=?", (t, who["discord_id"]))
        self.store.audit(who, "duty on" if on else "duty off", detail=("%g h" % hours) if on else "")
        self.bus.emit("duty")
        r = self.store.one("SELECT since, until FROM duty WHERE discord_id=? AND until>?", (who["discord_id"], t))
        return {"on": bool(r), "since": r["since"] if r else None, "until": r["until"] if r else None}

    # -- phone and desktop notifications (Web Push, no payload: the service worker fetches the alert itself)
    def vapid(self) -> tuple:
        d = self.meta("vapid_d")
        if not d:
            d_int, _ = p256_keypair()
            self.meta("vapid_d", "%064x" % d_int)
            d = self.meta("vapid_d")
        d_int = int(d, 16)
        if getattr(self, "_vapid", (None,))[0] != d_int:
            self._vapid = (d_int, p256_public(d_int))
        return self._vapid

    def push_subscribe(self, who: dict, endpoint: str) -> None:
        u = urllib.parse.urlsplit(str(endpoint or ""))
        if u.scheme != "https" or not PUSH_HOSTS.match(u.hostname or "") or u.port not in (None, 443) or len(endpoint) > 1000:
            if not (os.environ.get("TCP_STAFF_DEV") == "1" and str(endpoint).startswith("http://127.0.0.1:")):
                raise ApiError(400, "That is not a browser push address.")
        self.store.x("INSERT INTO push_subs(endpoint,discord_id,name,created,last_ok,fails) VALUES(?,?,?,?,NULL,0) "
                     "ON CONFLICT(endpoint) DO UPDATE SET discord_id=excluded.discord_id, name=excluded.name, fails=0",
                     (endpoint, who["discord_id"], who["name"], now()))
        self.store.audit(who, "push on", detail=u.hostname or "")

    def push_targets(self, urgent: bool) -> list:
        subs = self.store.q("SELECT * FROM push_subs")
        if urgent:
            return subs
        on = {d["discord_id"] for d in self.duty_list()}
        return [s for s in subs if s["discord_id"] in on]

    def push_send(self, sub: dict, urgent: bool) -> bool:
        d, pub = self.vapid()
        subject = self.cfg.get("push_subject") or self.cfg.get("public_url") or "https://staff.truecombat.eu"
        req = urllib.request.Request(sub["endpoint"], data=b"", method="POST", headers={
            "TTL": "3600", "Urgency": "high" if urgent else "normal", "Content-Length": "0",
            "Authorization": vapid_header(d, pub, sub["endpoint"], subject)})
        try:
            urllib.request.urlopen(req, timeout=8).read()
            self.store.x("UPDATE push_subs SET last_ok=?, fails=0 WHERE endpoint=?", (now(), sub["endpoint"]))
            return True
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):                       # the browser dropped the subscription
                self.store.x("DELETE FROM push_subs WHERE endpoint=?", (sub["endpoint"],))
            else:
                self.store.x("UPDATE push_subs SET fails=fails+1 WHERE endpoint=?", (sub["endpoint"],))
                log.warning("push refused (%d) for %s", e.code, sub["name"])
        except (urllib.error.URLError, OSError) as e:
            self.store.x("UPDATE push_subs SET fails=fails+1 WHERE endpoint=?", (sub["endpoint"],))
            log.warning("push failed for %s: %s", sub["name"], e)
        self.store.x("DELETE FROM push_subs WHERE fails>=20")
        return False

    def push_loop(self) -> None:
        import queue
        while not self.stop.is_set():
            try:
                aid, urgent = self.push_queue.get(timeout=5)
            except queue.Empty:
                continue
            kinds = self.cfg.get("push_kinds")
            a = self.store.one("SELECT kind FROM alerts WHERE id=?", (aid,))
            if not a or a["kind"] == "push_test" or (kinds is not None and a["kind"] not in kinds and not urgent):
                continue
            for sub in self.push_targets(urgent):
                self.push_send(sub, urgent)

    def push_latest(self, who: dict) -> dict:
        a = self.store.one("SELECT id, at, kind, title, text, pid, server FROM alerts WHERE at>? ORDER BY id DESC LIMIT 1", (now() - 900,))
        if not a:
            return {"alert": None}
        page = self.LINKS.get(a["kind"], "alerts")
        if page == "player":
            page = "player/" + a["pid"] if a["pid"] else "alerts"
        text = plain(a["text"]).replace("**", "")
        return {"alert": {"id": a["id"], "title": plain(a["title"]), "body": text[:180], "url": "/#/" + page, "kind": a["kind"]}}

    # -- history: player counts over time
    def history(self, days: int, server: str = "") -> dict:
        days = max(1, min(int(self.cfg.get("history_days", 90)), int(days or 7)))
        t = now()
        start = t - days * 86400
        bucket = 3600 if days <= 14 else 3 * 3600 if days <= 45 else 6 * 3600
        where, args = "at>=?", [start]
        if server:
            where += " AND server=?"
            args.append(server)
        rows = self.store.q("SELECT at, server, online, humans, bots FROM samples WHERE %s ORDER BY at" % where, args)
        by_at = {}
        for r in rows:
            by_at.setdefault(r["at"], []).append(r)
        series = {}
        for at, rs in by_at.items():
            b = at - at % bucket
            s = series.setdefault(b, {"t": b, "sum": 0, "n": 0, "peak": 0})
            total = sum(r["humans"] for r in rs if r["online"])
            s["sum"] += total
            s["n"] += 1
            s["peak"] = max(s["peak"], total)
        points = [{"t": s["t"], "avg": round(s["sum"] / s["n"], 1), "peak": s["peak"]} for s in sorted(series.values(), key=lambda x: x["t"])]
        servers = {}
        for r in rows:
            s = servers.setdefault(r["server"], {"key": r["server"], "samples": 0, "up": 0, "humans": 0, "peak": 0})
            s["samples"] += 1
            s["up"] += 1 if r["online"] else 0
            s["humans"] += r["humans"] if r["online"] else 0
            s["peak"] = max(s["peak"], r["humans"] if r["online"] else 0)
        for s in servers.values():
            s["uptime_pct"] = round(100.0 * s["up"] / s["samples"], 1) if s["samples"] else None
            s["avg"] = round(s["humans"] / s["samples"], 1) if s["samples"] else 0
            s["name"] = self.servers[s["key"]].name if s["key"] in self.servers else s["key"]
        # busiest hours, Belgian time: average players per weekday and hour
        heat = [[[0, 0] for _ in range(24)] for _ in range(7)]
        for at, rs in by_at.items():
            lt = brussels(at)
            cell = heat[lt.weekday()][lt.hour]
            cell[0] += sum(r["humans"] for r in rs if r["online"])
            cell[1] += 1
        heatmap = [[round(c[0] / c[1], 1) if c[1] else None for c in row] for row in heat]
        daily = self.store.q("SELECT day, SUM(peak) peak FROM peaks WHERE day>=? %s GROUP BY day ORDER BY day" %
                             ("AND server=?" if server else ""), [time.strftime("%Y-%m-%d", time.gmtime(start))] + ([server] if server else []))
        maps = self.store.q("SELECT map, COUNT(*) n, AVG(humans) avg FROM samples WHERE %s AND online=1 AND map<>'' GROUP BY map "
                            "ORDER BY avg DESC LIMIT 12" % where, args)
        for m in maps:
            m["avg"] = round(m["avg"] or 0, 1)
            m["hours"] = round(m["n"] * int(self.cfg.get("sample_seconds", 300)) / 3600, 1)
        return {"days": days, "bucket": bucket, "points": points, "servers": sorted(servers.values(), key=lambda s: s["key"]),
                "heatmap": heatmap, "daily": daily, "maps": maps, "samples": len(rows)}

    # -- moderator quality: what each staff member did and how it held up
    def quality(self, days: int) -> dict:
        days = max(1, min(365, int(days or 30)))
        start = now() - days * 86400
        staff = {}

        def row(name):
            return staff.setdefault(name, {"name": name, "actions": 0, "bans": 0, "kicks": 0, "mutes": 0, "warns": 0,
                                           "reports_closed": 0, "take_minutes": [], "close_minutes": [], "bans_overturned": 0,
                                           "bans_lifted": 0, "undos": 0, "appeals_answered": 0, "cases_closed": 0, "notes": 0})
        for a in self.store.q("SELECT staff, action FROM audit WHERE at>=? AND ok=1 AND role<>'system' AND staff<>'Portal'", (start,)):
            r = row(a["staff"])
            act = a["action"]
            if act in MODERATION_ACTIONS:
                r["actions"] += 1
            for k, word in (("bans", "ban"), ("kicks", "kick"), ("mutes", "mute"), ("warns", "warn"), ("notes", "note"),
                            ("cases_closed", "case closed")):
                if act == word:
                    r[k] += 1
            if act in ("undo ban", "undo mute"):
                r["undos"] += 1
            if act in ("appeal accepted", "appeal denied"):
                r["appeals_answered"] += 1
        for rep in self.store.q("SELECT id, received FROM reports WHERE received>=? AND source IN ('player','auto')", (start,)):
            mark = re.compile(r"#%d(?!\d)" % rep["id"])
            evs = [e for e in self.store.q("SELECT at, staff, action, detail FROM audit WHERE action IN ('report claimed','report closed') "
                                           "AND at>=? AND detail LIKE ? ORDER BY id", (rep["received"], "#%d%%" % rep["id"]))
                   if mark.match(e["detail"] or "")]
            took = next((e for e in evs if e["action"] == "report claimed"), None)
            closed = next((e for e in evs if e["action"] == "report closed"), None)
            if took:
                row(took["staff"])["take_minutes"].append((took["at"] - rep["received"]) / 60)
            if closed:
                r = row(closed["staff"])
                r["reports_closed"] += 1
                r["close_minutes"].append((closed["at"] - rep["received"]) / 60)
        for b in self.store.q("SELECT by_name, lifted, lifted_by, lift_reason FROM bans WHERE created>=?", (start,)):
            if b["lifted"] and b["lifted_by"] and b["lifted_by"] != b["by_name"] and b["lifted_by"] != "expired":
                row(b["by_name"])["bans_lifted"] += 1
        for ap in self.store.q("SELECT a.status, b.by_name FROM appeals a JOIN bans b ON b.id=a.ban_id WHERE a.created>=?", (start,)):
            if ap["status"] == "accepted":
                row(ap["by_name"])["bans_overturned"] += 1

        def median(xs):
            xs = sorted(xs)
            return round(xs[len(xs) // 2], 1) if xs else None
        out = []
        for r in staff.values():
            r["take_median_min"] = median(r.pop("take_minutes"))
            r["close_median_min"] = median(r.pop("close_minutes"))
            r["overturn_pct"] = round(100.0 * r["bans_overturned"] / r["bans"], 1) if r["bans"] else None
            if any(r[k] for k in ("actions", "reports_closed", "appeals_answered", "cases_closed", "notes")):
                out.append(r)
        out.sort(key=lambda r: -(r["actions"] + r["reports_closed"]))
        team = {"reports": self.store.one("SELECT COUNT(*) n FROM reports WHERE received>=? AND source IN ('player','auto')", (start,))["n"],
                "untouched": self.store.one("SELECT COUNT(*) n FROM reports WHERE received>=? AND source IN ('player','auto') AND "
                                            "status='open' AND received<?", (start, now() - 86400))["n"],
                "appeals": self.store.one("SELECT COUNT(*) n FROM appeals WHERE created>=?", (start,))["n"],
                "accepted": self.store.one("SELECT COUNT(*) n FROM appeals WHERE created>=? AND status='accepted'", (start,))["n"]}
        return {"days": days, "staff": out, "team": team}

    # -- anti-cheat review queue (admins)
    def ac_add(self, kind: str, pid: str, name: str, server: str, detail: str, score: int = 0) -> bool:
        if not pid or kind not in AC_KINDS:
            return False
        if self.store.one("SELECT id FROM ac_queue WHERE pid=? AND kind=? AND (status='open' OR at>?)", (pid, kind, now() - 86400)):
            self.store.x("UPDATE ac_queue SET detail=?, score=MAX(score, ?), at=? WHERE pid=? AND kind=? AND status='open'",
                         (detail[:500], score, now(), pid, kind))
            return False
        self.store.x("INSERT INTO ac_queue(kind,pid,name,server,at,detail,score,status) VALUES(?,?,?,?,?,?,?,'open')",
                     (kind, pid, plain(name)[:64], server, now(), detail[:500], score))
        self.bus.emit("anticheat")
        return True

    def ac_watch(self, srv, players: list) -> None:
        """A rise in a player's anti-cheat detection count puts them in the queue."""
        for p in players:
            pid = p.get("pid")
            if not pid:
                continue
            n = int(p.get("detections") or 0)
            key = (srv.key, pid)
            before = self.ac_seen.get(key, 0)
            self.ac_seen[key] = n
            if n > before:
                self.ac_add("detection", pid, p["name"], srv.key, "%d detection%s this session (anti-cheat %s, files %s)" % (
                    n, "" if n == 1 else "s", p.get("eac") or "?", p.get("files") or "?"), score=min(100, 50 + 10 * n))

    def ac_list(self, status: str = "open") -> list:
        rows = self.store.q("SELECT * FROM ac_queue WHERE %s ORDER BY status='open' DESC, score DESC, at DESC LIMIT 300" %
                            ("status='open'" if status == "open" else "status<>'open'" if status == "done" else "1=1"))
        online = {p.get("pid"): s.key for s in self.servers.values() for p in s.view().get("players", []) if p.get("pid")}
        for r in rows:
            r["online"] = online.get(r["pid"], "")
            r["banned"] = bool(self.store.one("SELECT id FROM bans WHERE pid=? AND active=1", (r["pid"],)))
            sus = self.store.one("SELECT score FROM suspicion WHERE pid=?", (r["pid"],))
            r["suspicion"] = sus["score"] if sus else None
            r["label"] = AC_KINDS.get(r["kind"], r["kind"])
        return rows

    def ac_resolve(self, who: dict, qid: int, outcome: str, note: str = "") -> None:
        if outcome not in ("cleared", "actioned", "case", "open"):
            raise ApiError(400, "Unknown outcome.")
        r = self.store.one("SELECT * FROM ac_queue WHERE id=?", (int(qid or 0),))
        if not r:
            raise ApiError(404, "No such item.")
        self.store.x("UPDATE ac_queue SET status=?, by_name=?, resolved=?, note=? WHERE id=?",
                     (outcome, who["name"] if outcome != "open" else None, now() if outcome != "open" else None, note[:300], r["id"]))
        self.store.audit(who, "anti-cheat " + outcome, target=r["name"], pid=r["pid"], detail="#%d %s %s" % (r["id"], r["kind"], note[:200]))
        self.bus.emit("anticheat")


class Portal(Moderation, Watchers, Operations, Overview, Casework, Team):
    def __init__(self, cfg: dict):
        self.cfg = cfg
        data = Path(cfg.get("data_dir", "/var/lib/tcp-staff-portal"))
        data.mkdir(parents=True, exist_ok=True)
        self.store = Store(str(data / "portal.db"))
        self.bugshots = data / "bugshots"
        self.servers = {s["key"]: GameServer(s, self.store) for s in cfg.get("servers", [])}
        self.order = [s["key"] for s in cfg.get("servers", [])]
        self.stop = threading.Event()
        self.chat_offsets = {}
        self.rate = {}
        self.rate_lock = threading.Lock()
        self.health_cache = (0, None)
        import queue
        self.alert_queue = queue.Queue()
        self.push_queue = queue.Queue()
        self.ac_seen = {}          # (server, pid) -> anti-cheat detections seen this session
        self._filters = None
        self._layouts = None
        self.watch_cache = {}      # (server, slot) -> identity last checked for watchlist / ban dodgers
        self.online = {}           # server -> {pid: slot}
        self.afk = {}
        self.tk_seen = {}
        self.down_since = {}
        self.down_alerted = set()
        self.stats_cache = {}
        self.map_views = set()
        self.bus = EventBus()
        self.session_open = {}     # server -> pids with an open play session
        self.store.on_audit = lambda action: self.bus.emit("action", action=action)
        self.close_stale_sessions()
        if not self.meta("templates_seeded"):
            for kind, title, text in DEFAULT_TEMPLATES:
                self.store.x("INSERT INTO templates(kind,title,text,created,by_name) VALUES(?,?,?,?,?)", (kind, title, text, now(), "Portal"))
            self.meta("templates_seeded", "1")
        owners = [str(d) for d in cfg.get("owners", [])]
        # someone taken out of "owners" loses owner rights at once, not only at their next Discord check
        self.store.x("UPDATE staff SET role=NULL WHERE role='owner' AND discord_id NOT IN (%s)" % ",".join("?" * len(owners)), owners)
        self.store.x("DELETE FROM sessions WHERE role='owner' AND discord_id NOT IN (%s)" % ",".join("?" * len(owners)), owners)
        for d in owners:
            self.store.x("INSERT INTO staff(discord_id,name,role,note,added_by,created) VALUES(?,?,?,?,?,?) "
                         "ON CONFLICT(discord_id) DO UPDATE SET role='owner'",
                         (str(d), "", "owner", "from config", "config", now()))

    # ------------------------------------------------------------------ background work
    def start(self) -> None:
        loops = [(self.poll_loop, "poll"), (self.report_loop, "reports"), (self.ban_loop, "bans"),
                 (self.prune_loop, "prune"), (self.alert_loop, "alerts"), (self.suspicion_loop, "suspicion"),
                 (self.schedule_loop, "schedule"), (self.enforce_loop, "enforce"), (self.weekly_loop, "weekly"),
                 (self.backup_loop, "backup"), (self.push_loop, "push"), (self.comments_loop, "comments")]
        for s in self.servers.values():
            loops.append((lambda s=s: self.chat_loop(s), "chat-" + s.key))
        for fn, name in loops:
            threading.Thread(target=self._guard, args=(fn, name), name=name, daemon=True).start()

    def _guard(self, fn, name) -> None:
        while not self.stop.is_set():
            try:
                fn()
            except Exception:  # noqa: BLE001
                log.exception("%s loop failed; restarting in 5 s", name)
            self.stop.wait(5)

    def poll_loop(self) -> None:
        every = float(self.cfg.get("poll_seconds", 3))
        while not self.stop.is_set():
            started = time.time()
            threads = [threading.Thread(target=s.poll, daemon=True) for s in self.servers.values()]
            for th in threads:
                th.start()
            for th in threads:
                th.join(10)
            for srv in self.servers.values():
                try:
                    self.watch(srv)
                except Exception:  # noqa: BLE001  (a watcher bug must never stop the live view)
                    log.exception("watchers failed for %s", srv.key)
            try:
                self.record_samples()
            except sqlite3.Error:
                log.exception("player-count sample failed")
            self.bus.emit("servers")
            self.stop.wait(max(0.5, every - (time.time() - started)))

    # chat comes from the game's own log line: TCP_NATIVE_SAY slot=N team=T text
    # Anchored: the marker must open the line (after the console's time stamp). Player names show up inside other log
    # lines, and a name such as "TCP_NATIVE_SAY slot=3 team=0 n00b" must never pass for slot 3 saying something.
    SAY = re.compile(r"^\s*(?:[\d:.]+\s+)?TCP_NATIVE_SAY slot=(\d+) team=(\d+) (.*)$")
    ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

    def chat_loop(self, server: GameServer) -> None:
        src = server.cfg.get("log_file")
        if src:
            self._tail_file(server, Path(src))
        elif server.cfg.get("unit") and shutil.which("journalctl"):
            self._tail_journal(server)
        else:
            self.stop.wait(3600)

    def _chat_line(self, server: GameServer, line: str) -> None:
        line = plain(self.ANSI.sub("", line)).rstrip()
        m = self.SAY.match(line)
        if m:
            slot, team, text = int(m.group(1)), int(m.group(2)), m.group(3)
            p = server.slot_player(slot) or {}
            name = p.get("name") or server.names.get(slot) or "slot %d" % slot
            cid = self.store.x("INSERT INTO chat(server,at,slot,team,pid,name,text,kind) VALUES(?,?,?,?,?,?,?,?)",
                               (server.key, now(), slot, p.get("team") if team else None, p.get("pid", ""), name, text[:300],
                                "team" if team else "all"))
            self.bus.emit("chat", server=server.key, id=cid)
            try:
                self.check_chat(server, slot, p, text[:300], cid)
            except Exception:  # noqa: BLE001
                log.exception("chat filter failed")
            return

    def _tail_journal(self, server: GameServer) -> None:
        cmd = ["journalctl", "-u", server.cfg["unit"], "-f", "-n", "0", "-o", "cat", "--no-pager"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace")
        try:
            for line in p.stdout:
                if self.stop.is_set():
                    break
                if "TCP_NATIVE_SAY" in line:
                    self._chat_line(server, line)
        finally:
            p.kill()

    def _tail_file(self, server: GameServer, path: Path) -> None:
        pos = path.stat().st_size if path.exists() else 0
        while not self.stop.is_set():
            try:
                size = path.stat().st_size
                if size < pos:
                    pos = 0
                if size > pos:
                    with path.open("r", encoding="latin-1", errors="replace") as f:
                        f.seek(pos)
                        for line in f:
                            if line.endswith("\n"):
                                self._chat_line(server, line)
                                pos += len(line.encode("latin-1", "replace"))
                            else:
                                break
            except OSError:
                pass
            self.stop.wait(0.5)

    # player reports written by the game (tcp-report/1); the Discord bot moves them to reports/sent/
    def report_loop(self) -> None:
        while not self.stop.is_set():
            self.scan_reports()
            self.stop.wait(15)

    def scan_reports(self) -> int:
        added = 0
        for s in self.servers.values():
            folder = s.cfg.get("reports_dir")
            if not folder:
                continue
            for d in (Path(folder), Path(folder) / "sent"):
                try:
                    files = sorted(d.glob("*.json"))[-500:]
                except OSError:
                    continue
                for f in files:
                    key = "%s/%s" % (s.key, f.name)
                    if self.store.one("SELECT id FROM reports WHERE file=?", (key,)):
                        continue
                    try:
                        r = json.loads(f.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        continue
                    if not isinstance(r, dict) or not isinstance(r.get("reported"), dict):
                        continue
                    who = r["reported"]
                    self.store.x("INSERT OR IGNORE INTO reports(source,file,server,received,data,target_pid,target_name,status,updated) "
                                 "VALUES(?,?,?,?,?,?,?,?,?)",
                                 ("auto" if r.get("auto") else "player", key, s.key, now(), json.dumps(r),
                                  str(who.get("id") or ""), plain(who.get("name"))[:64], "open", now()))
                    added += 1
                    self.bus.emit("reports")
                    pid = str(who.get("id") or "")
                    if PID.match(pid):
                        n = self.store.one("SELECT COUNT(*) n FROM reports WHERE target_pid=? AND received>? AND source IN ('player','auto')",
                                           (pid, now() - 3600))["n"]
                        if n >= int(self.cfg.get("reports_alert_at", 3)):
                            self.alert("reports", "%d reports on %s in the last hour" % (n, plain(who.get("name"))[:40]),
                                       "Latest on %s: %s" % (s.name, plain(r.get("reason"))[:200]), key="reports:" + pid,
                                       window=3600, pid=pid, server=s.key)
        return added

    # bans: expiry and making sure every server still has every ban
    def ban_loop(self) -> None:
        while not self.stop.is_set():
            self.expire_bans()
            self.reconcile_bans()
            self.stop.wait(float(self.cfg.get("ban_sync_seconds", 300)))

    def expire_bans(self) -> None:
        t = now()
        for b in self.store.q("SELECT * FROM bans WHERE active=1 AND expires>0 AND expires<=?", (t,)):
            self._lift_everywhere(b)
            self.store.x("UPDATE bans SET active=0, lifted=?, lifted_by='expired' WHERE id=?", (t, b["id"]))
        self.store.x("UPDATE mutes SET active=0 WHERE active=1 AND expires>0 AND expires<=?", (t,))

    def reconcile_bans(self) -> dict:
        report = {}
        active = self.store.q("SELECT * FROM bans WHERE active=1")
        for s in self.servers.values():
            try:
                listed = parse_banlist(s.run("banlist", timeout=2))
            except RconError as e:
                report[s.key] = "offline: %s" % e
                continue
            have_guid = {b["guid"].upper() for b in listed if b["guid"]}
            have_puid = {b["puid"].lower() for b in listed if b["puid"]}
            fixed = 0
            for b in active:
                if (b["guid"] and b["guid"].upper() not in have_guid) or (b["puid"] and b["puid"].lower() not in have_puid):
                    self._apply_ban(s, b, slot=None)
                    fixed += 1
            report[s.key] = "ok, %d re-applied" % fixed
        return report

    def _apply_ban(self, s: GameServer, b: dict, slot: int | None) -> list:
        left = 0 if not b["expires"] else max(1, (b["expires"] - now() + 59) // 60)
        length = engine_length(left)
        reason = self.ban_text(b)
        done = []
        if slot is not None:
            done.append(s.run(("ban %d %s %s" % (slot, length, reason)).strip()))
        else:
            if b["guid"]:
                done.append(s.run(("banguid %s %s %s" % (safe_arg(b["guid"], 40), length, reason)).strip()))
            if b["ip"] and self.cfg.get("ban_ip", True):
                done.append(s.run(("banip %s %s %s" % (safe_arg(b["ip"], 60), length, reason)).strip()))
        if b["puid"]:
            done.append(s.run(("banpuid %s %s" % (safe_arg(b["puid"], 64), reason)).strip()))
        return done

    def _lift_everywhere(self, b: dict) -> dict:
        out = self._unban_everywhere(b)
        # "unban <ip>" also lifts another active ban on the same address (or GUID, or anti-cheat account): put those back
        for other in self.store.q("SELECT * FROM bans WHERE active=1 AND id<>? AND ((ip<>'' AND ip=?) OR (guid<>'' AND guid=?) "
                                  "OR (puid<>'' AND puid=?))", (b["id"], b.get("ip") or "", b.get("guid") or "", b.get("puid") or "")):
            for s in self.servers.values():
                try:
                    self._apply_ban(s, other, slot=None)
                except RconError:
                    pass                     # the next sync puts it back
        return out

    def _unban_everywhere(self, b: dict) -> dict:
        out = {}
        for s in self.servers.values():
            res = []
            for v in (b.get("guid"), b.get("ip"), b.get("puid")):
                if v:
                    try:
                        res.append(s.run("unban %s" % safe_arg(v, 64)).strip())
                    except RconError as e:
                        res.append("offline: %s" % e)
            out[s.key] = "; ".join(x for x in res if x) or "nothing to lift"
        return out

    def prune_loop(self) -> None:
        while not self.stop.is_set():
            try:                                   # one bad hour (a locked database, a full disk) never ends the loop
                self.prune_once()
            except Exception:  # noqa: BLE001
                log.exception("hourly clean-up failed; trying again in an hour")
            for job in (self.prune_bugshots, self.publish_staff_keys):
                try:
                    job()
                except Exception:  # noqa: BLE001
                    log.exception("%s failed", job.__name__)
            self.stop.wait(3600)

    def prune_once(self) -> None:
        days = int(self.cfg.get("retention_days", 90))
        cut = now() - days * 86400
        self.store.x("DELETE FROM chat WHERE at<?", (now() - int(self.cfg.get("chat_days", 30)) * 86400,))
        self.store.x("DELETE FROM sightings WHERE last_seen<?", (cut,))
        self.store.x("DELETE FROM sessions WHERE seen<?", (now() - 86400,))
        self.store.x("DELETE FROM flags WHERE at<?", (cut,))
        self.store.x("DELETE FROM alerts WHERE at<?", (cut,))
        self.store.x("DELETE FROM undo WHERE expires<?", (now() - 86400,))
        self.store.x("DELETE FROM peaks WHERE day<?", (time.strftime("%Y-%m-%d", time.gmtime(cut)),))
        self.store.x("DELETE FROM suspicion WHERE updated<?", (cut,))
        self.store.x("DELETE FROM reports WHERE source='bug' AND status='closed' AND updated<?", (cut,))
        self.store.x("DELETE FROM devices WHERE blocked=0 AND last_seen<?", (now() - int(self.cfg.get("device_days", 90)) * 86400,))
        self.store.x("DELETE FROM staff_key_codes WHERE expires<?", (now(),))
        self.store.x("DELETE FROM samples WHERE at<?", (now() - int(self.cfg.get("history_days", 90)) * 86400,))
        self.store.x("DELETE FROM player_sessions WHERE joined<? AND left_at IS NOT NULL", (cut,))
        self.prune_evidence()
        self.store.x("DELETE FROM ac_queue WHERE status<>'open' AND resolved<?", (cut,))
        self.store.x("DELETE FROM duty WHERE until<?", (now() - 86400,))

    # ------------------------------------------------------------------ queries used by the API
    def server(self, key: str) -> GameServer:
        s = self.servers.get(str(key or ""))
        if not s:
            raise ApiError(404, "Unknown server.")
        return s

    def servers_view(self, show_ip: bool = False) -> list:
        out = []
        for key in self.order:
            v = self.servers[key].view()
            if not show_ip:                          # addresses are admin-only, as on the player page
                for p in v.get("players", []):
                    p.pop("ip", None)
                    p.pop("guid", None)
            pids = [p.get("pid") for p in v.get("players", []) if p.get("pid")]
            flags = self._flags(pids)
            for p in v.get("players", []):
                p.update(flags.get(p.get("pid"), {}))
            out.append(v)
        return out

    def _flags(self, pids: list) -> dict:
        out = {}
        if not pids:
            return out
        marks = ",".join("?" * len(pids))
        t = now()
        for r in self.store.q("SELECT target_pid pid, COUNT(*) n FROM reports WHERE status<>'closed' AND target_pid IN (%s) "
                              "GROUP BY target_pid" % marks, pids):
            out.setdefault(r["pid"], {})["open_reports"] = r["n"]
        for r in self.store.q("SELECT pid, COUNT(*) n FROM warnings WHERE pid IN (%s) GROUP BY pid" % marks, pids):
            out.setdefault(r["pid"], {})["warnings"] = r["n"]
        for r in self.store.q("SELECT pid, COUNT(*) n FROM bans WHERE pid IN (%s) GROUP BY pid" % marks, pids):
            out.setdefault(r["pid"], {})["past_bans"] = r["n"]
        for r in self.store.q("SELECT pid, expires FROM mutes WHERE active=1 AND (expires=0 OR expires>?) AND pid IN (%s)" % marks,
                              [t] + pids):
            out.setdefault(r["pid"], {})["mute_until"] = r["expires"]
        for r in self.store.q("SELECT pid FROM watchlist WHERE pid IN (%s)" % marks, pids):
            out.setdefault(r["pid"], {})["watched"] = True
        for r in self.store.q("SELECT pid, score FROM suspicion WHERE updated>? AND pid IN (%s)" % marks, [t - 600] + pids):
            out.setdefault(r["pid"], {})["suspicion"] = r["score"]
        for r in self.store.q("SELECT pid, kind FROM flags WHERE at>? AND kind IN ('ban dodger','possible alt','afk','team kills') "
                              "AND pid IN (%s) GROUP BY pid, kind" % marks, [t - 3 * 3600] + pids):
            out.setdefault(r["pid"], {}).setdefault("live_flags", []).append(r["kind"])
        return out

    def stats(self, route: str, **params):
        """The stats service's own JSON API (the bridge on 127.0.0.1:8090): no access to its database file needed."""
        base = self.cfg.get("stats_api")
        if not base:
            return None
        url = "%s/%s?%s" % (base.rstrip("/"), route, urllib.parse.urlencode(params))
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "TCPStaff"}), timeout=4) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def lookup(self, query: str, show_ip: bool) -> list:
        q = query.strip()
        if len(q) < 2:
            return []
        rows = {}
        like = "%" + q.replace("%", "").replace("_", "") + "%"
        params = [like, q.lower(), q]
        sql = ("SELECT pid, MAX(last_seen) last_seen, MIN(first_seen) first_seen FROM sightings "
               "WHERE name LIKE ? OR pid=? OR guid=?")
        try:
            ipaddress.ip_address(q)
            if show_ip:
                sql += " OR ip=?"
                params.append(q)
        except ValueError:
            pass
        sql += " GROUP BY pid ORDER BY last_seen DESC LIMIT 50"
        if re.fullmatch(r"\d{15,21}", q):
            for link in self.discord_links(discord_id=q) or []:
                rows[link["pid"]] = {"pid": link["pid"], "stats_name": link.get("name") or "", "discord": True}
        for r in self.store.q(sql, params):
            rows[r["pid"]] = {"pid": r["pid"], "last_seen": r["last_seen"], "first_seen": r["first_seen"]}
        guid_pid = player_pid(q) if re.fullmatch(r"[0-9A-Fa-f]{32}", q) else ""
        for r in self.store.q("SELECT target_pid pid, MAX(received) at FROM reports WHERE target_pid<>'' AND (target_name LIKE ? "
                              "OR target_pid=? OR target_pid=?) GROUP BY target_pid ORDER BY at DESC LIMIT 50", (like, q.lower(), guid_pid)):
            rows.setdefault(r["pid"], {"pid": r["pid"], "seen_in": "bug reports"})
        for r in self.store.q("SELECT pid, name, MAX(last_seen) at FROM devices WHERE pid<>'' AND (name LIKE ? OR pid=? OR pid=? "
                              "OR kid=? OR puid=?) GROUP BY pid ORDER BY at DESC LIMIT 50", (like, q.lower(), guid_pid, q.lower(), q.lower())):
            rows.setdefault(r["pid"], {"pid": r["pid"], "stats_name": r["name"], "seen_in": "game starts", "last_seen": r["at"]})
        found = self.stats("search.json", q=q) or {}
        for r in found.get("players", []):
            if PID.match(str(r.get("id", ""))):
                rows.setdefault(r["id"], {"pid": r["id"], "stats_name": r.get("name", "")})
        out = []
        for pid, r in list(rows.items())[:50]:
            names = self.store.q("SELECT name, MAX(last_seen) at FROM sightings WHERE pid=? GROUP BY name ORDER BY at DESC LIMIT 5", (pid,))
            r["names"] = [n["name"] for n in names] or ([r["stats_name"]] if r.get("stats_name") else [])
            if not r["names"]:
                rep = self.store.one("SELECT target_name FROM reports WHERE target_pid=? AND target_name<>'' ORDER BY id DESC", (pid,))
                r["names"] = [rep["target_name"]] if rep else []
            ban = self.store.one("SELECT game FROM bans WHERE pid=? AND active=1 ORDER BY game DESC", (pid,))
            r["banned"] = bool(ban)
            r["game_banned"] = bool(ban and ban["game"])
            out.append(r)
        return out

    def player(self, pid: str, show_ip: bool) -> dict:
        if not PID.match(pid):
            raise ApiError(400, "That is not a player id.")
        out = {"pid": pid}
        seen = self.store.q("SELECT name, ip, puid, guid, server, first_seen, last_seen FROM sightings WHERE pid=? "
                            "ORDER BY last_seen DESC LIMIT 200", (pid,))
        names = {}
        for s in seen:
            n = names.setdefault(s["name"], {"name": s["name"], "first_seen": s["first_seen"], "last_seen": s["last_seen"]})
            n["first_seen"] = min(n["first_seen"], s["first_seen"])
            n["last_seen"] = max(n["last_seen"], s["last_seen"])
        out["names"] = sorted(names.values(), key=lambda n: -n["last_seen"])
        out["servers"] = sorted({s["server"] for s in seen})
        out["puids"] = sorted({s["puid"] for s in seen if s["puid"]})
        out["first_seen"] = min((s["first_seen"] for s in seen), default=None)
        out["last_seen"] = max((s["last_seen"] for s in seen), default=None)
        if show_ip:
            ips = {}
            for s in seen:
                if s["ip"]:
                    ips[s["ip"]] = max(ips.get(s["ip"], 0), s["last_seen"])
            out["ips"] = [{"ip": k, "last_seen": v} for k, v in sorted(ips.items(), key=lambda kv: -kv[1])]
            alts = set()
            for ip in ips:
                for r in self.store.q("SELECT DISTINCT pid FROM sightings WHERE ip=? AND pid<>?", (ip, pid)):
                    alts.add(r["pid"])
            out["shared_ip"] = sorted(alts)[:20]
        out["bans"] = self.store.q("SELECT id,name,reason,created,expires,by_name,active,lifted,lifted_by,lift_reason,game "
                                   "FROM bans WHERE pid=? ORDER BY id DESC", (pid,))
        if not out["names"]:                     # never on a server: names from bug reports and game starts
            for r in self.store.q("SELECT target_name name, MIN(received) f, MAX(received) l FROM reports WHERE target_pid=? "
                                  "AND target_name<>'' GROUP BY target_name UNION SELECT name, MIN(first_seen), MAX(last_seen) "
                                  "FROM devices WHERE pid=? AND name<>'' GROUP BY name", (pid, pid)):
                out["names"].append({"name": r["name"], "first_seen": r["f"], "last_seen": r["l"]})
            out["names"].sort(key=lambda n: -(n["last_seen"] or 0))
        dev = self.store.one("SELECT MAX(last_seen) at, COUNT(*) n FROM devices WHERE pid=?", (pid,))
        out["game_starts"] = {"last": dev["at"], "installs": dev["n"]} if dev and dev["n"] else None
        out["mutes"] = self.store.q("SELECT id,name,reason,created,expires,by_name,active FROM mutes WHERE pid=? ORDER BY id DESC", (pid,))
        out["warnings"] = self.store.q("SELECT id,name,text,created,by_name,server FROM warnings WHERE pid=? ORDER BY id DESC", (pid,))
        out["notes"] = self.store.q("SELECT id,text,created,by_name FROM notes WHERE pid=? ORDER BY id DESC", (pid,))
        out["reports"] = [self._report_row(r) for r in self.store.q(
            "SELECT * FROM reports WHERE target_pid=? ORDER BY id DESC LIMIT 50", (pid,))]
        out["actions"] = self.store.q("SELECT at, staff, action, server, detail, ok FROM audit WHERE target_pid=? "
                                      "ORDER BY id DESC LIMIT 100", (pid,))
        out["chat"] = self.store.q("SELECT server, at, kind, name, text FROM chat WHERE pid=? ORDER BY id DESC LIMIT 100", (pid,))
        out["online"] = [{"server": s.key, "slot": p["slot"], "name": p["name"]}
                         for s in self.servers.values() for p in s.view().get("players", []) if p.get("pid") == pid]
        st = self.stats("player.json", id=pid)
        out["stats"] = st
        out["matches"] = (st or {}).get("recent", [])
        out["profile_url"] = "%s/player?id=%s" % (self.cfg.get("site", "https://truecombat.eu").rstrip("/"), pid)
        out["discord"] = self.discord_links(pid=pid)
        out["watch"] = self.store.one("SELECT reason, created, by_name FROM watchlist WHERE pid=?", (pid,))
        out["flags"] = self.store.q("SELECT kind, detail, server, at FROM flags WHERE pid=? ORDER BY id DESC LIMIT 50", (pid,))
        out["punishments"] = self.store.q("SELECT offence, step, created, by_name, note FROM punishments WHERE pid=? ORDER BY id DESC LIMIT 50", (pid,))
        live = next(({**p, "server": s.key} for s in self.servers.values() for p in s.view().get("players", []) if p.get("pid") == pid), None)
        sus = self.store.one("SELECT score, reasons, updated, peak FROM suspicion WHERE pid=?", (pid,))
        if live:
            score, reasons = self.suspicion(live)
            out["suspicion"] = {"score": score, "reasons": reasons, "live": True, "peak": max(score, (sus or {}).get("peak") or 0)}
        elif sus:
            out["suspicion"] = {"score": sus["score"], "reasons": json.loads(sus["reasons"] or "[]"), "live": False,
                                "updated": sus["updated"], "peak": sus["peak"]}
        else:
            out["suspicion"] = None
        alts = {}
        for pu in out["puids"]:
            for r in self.store.q("SELECT pid, MAX(name) name FROM sightings WHERE puid=? AND pid<>? GROUP BY pid", (pu, pid)):
                alts[r["pid"]] = {"pid": r["pid"], "name": r["name"], "why": "anti-cheat account"}
        if show_ip:
            for alt in out.get("shared_ip", []):
                if alt not in alts:
                    r = self.store.one("SELECT name FROM sightings WHERE pid=? ORDER BY last_seen DESC LIMIT 1", (alt,))
                    alts[alt] = {"pid": alt, "name": r["name"] if r else alt, "why": "internet address"}
        for a in alts.values():
            a["banned"] = bool(self.store.one("SELECT id FROM bans WHERE pid=? AND active=1", (a["pid"],)))
        out["alts"] = list(alts.values())[:30]
        out["appeals"] = self.store.q("SELECT id, status, text, answer, created, answered_by FROM appeals WHERE pid=? ORDER BY id DESC", (pid,))
        return out

    def _report_row(self, r: dict, full: bool = False) -> dict:
        r = dict(r)
        try:
            r["data"] = json.loads(r["data"])
        except (TypeError, ValueError):
            r["data"] = {}
        if r["source"] == "bug" and not full and isinstance(r["data"], dict):
            # the list stays light: the console tail and hardware come with the single report
            r["data"]["has_console"] = bool(r["data"].pop("console", ""))
            r["data"].pop("hw", None)
        return r

    def server_by_address(self, addr: str):
        """Our server behind an ip:port a player was connected to, matched on the port and the public host or its IP."""
        m = re.fullmatch(r"\[?([^\]]*?)\]?:(\d+)", addr.strip())
        if not m:
            return None
        host, port = m.group(1).lower(), int(m.group(2))
        for srv in self.servers.values():
            pub = str(srv.cfg.get("public_address", ""))
            phost, _, pport = pub.rpartition(":")
            if not pport.isdigit() or int(pport) != port:
                continue
            if host == phost.lower() or host in self.public_ips(phost):
                return srv
        return None

    def public_ips(self, host: str) -> set:
        cache = getattr(self, "_ip_cache", {})
        hit = cache.get(host)
        if hit and hit[0] > time.time() - 3600:
            return hit[1]
        try:
            ips = {a[4][0].lower() for a in socket.getaddrinfo(host, None)}
        except OSError:
            ips = set()
        cache[host] = (time.time(), ips)
        self._ip_cache = cache
        return ips

    def bugshots_bytes(self) -> int:
        try:
            return sum(f.stat().st_size for f in self.bugshots.glob("*.jpg")) if self.bugshots.is_dir() else 0
        except OSError:
            return 0

    def bugshot_path(self, key: str) -> Path:
        return self.bugshots / (re.sub(r"[^A-Za-z0-9_-]", "_", key) + ".jpg")

    # ---------------------------------------------------------------- in-game staff badge keys
    # Staff make their own key pair in the browser; the portal only ever sees the public half. The game servers
    # read the list below (cvar g_staffKeyFile, 0.36.0+) next to the keys built into the game.
    def staff_key_valid_sql(self) -> tuple:
        idle = int(self.cfg.get("staff_key_idle_days", 60))
        owners = sorted({str(x) for x in self.cfg.get("owners", [])})
        sql = ("SELECT k.* FROM staff_keys k LEFT JOIN staff s ON s.discord_id=k.discord_id WHERE k.revoked=0 "
               "AND COALESCE(s.role,'')<>'revoked'")
        args = []
        if idle > 0:
            sql += " AND (COALESCE(s.last_login,0)>=? OR k.discord_id IN (%s))" % (",".join("?" * len(owners)) or "''")
            args = [now() - idle * 86400] + owners
        return sql + " ORDER BY k.created", args

    def staff_key_lines(self) -> str:
        sql, args = self.staff_key_valid_sql()
        out = ["# TrueCombat Platinum staff keys, written by the staff portal. Do not edit by hand.",
               "# TCPSTAFFKEY1 <key id> <role> <Ed25519 public key> <name>"]
        for k in self.store.q(sql, args):
            out.append("TCPSTAFFKEY1 %s 1 %s %s" % (k["id"], k["public"], k["name"]))
        return "\n".join(out) + "\n"

    def staff_cert(self, kid: str) -> dict | None:
        """A fresh certificate for an active staff key, or None (unknown, revoked, idle, or no root set up).
        Certificates last staff_cert_days (30); a cached one is reused while it has at least 25 days left."""
        if not hasattr(self, "_staff_root"):
            self._staff_root, self._staff_certs = load_staff_root(self.cfg), {}
        if not self._staff_root or not re.fullmatch(r"k[0-9a-f]{10}", kid or ""):
            return None
        sql, args = self.staff_key_valid_sql()
        k = self.store.one("SELECT * FROM (%s) WHERE id=?" % sql, args + [kid])
        if not k:
            self._staff_certs.pop(kid, None)
            return None
        days = max(1, min(90, int(self.cfg.get("staff_cert_days", 30))))
        hit = self._staff_certs.get(kid)
        if hit and hit["public"] == k["public"] and hit["expires"] - now() > (days - 5) * 86400:
            return hit
        root_id, seed, _pub = self._staff_root
        issued = now() - 60
        expires = issued + days * 86400
        name_hex = (k["name"] or "staff").encode("ascii", "replace")[:24].hex()
        sig = ed25519_sign(seed, staff_cert_message(root_id, kid, 1, issued, expires, k["public"], name_hex))
        line = " ".join([STAFF_CERT_TAG, root_id, kid, "1", str(issued), str(expires), k["public"], name_hex, sig.hex()])
        self._staff_certs[kid] = {"cert": line, "expires": expires, "public": k["public"]}
        return self._staff_certs[kid]

    def publish_staff_keys(self) -> list:
        """Writes the key list for every server that has staff_keys_file and asks it to reload. Returns problems."""
        text, problems = self.staff_key_lines(), []
        for key in self.order:
            srv = self.servers[key]
            path = self.staff_keys_file(srv)
            if not path:
                continue
            try:
                if path.exists() and path.read_text(encoding="utf-8") == text:
                    continue                     # unchanged: the server already has it
                tmp = path.with_name(".%s.%s.tmp" % (path.name, secrets.token_hex(4)))
                tmp.write_text(text, encoding="utf-8")
                os.chmod(tmp, 0o644)
                os.replace(tmp, path)
            except OSError as e:
                problems.append("%s: %s" % (srv.name, e))
                log.warning("staff key list for %s not written: %s", srv.name, e)
                continue
            try:
                srv.run("staffkeys_reload")
            except Exception as e:  # noqa: BLE001 - an offline server reads the file when it starts
                log.info("staff key reload on %s: %s", srv.name, e)
        return problems

    @staticmethod
    def staff_keys_file(srv) -> Path | None:
        """staff_keys_file from the config, else <game dir>/staffkeys/staffkeys.txt once install.sh made that folder."""
        if srv.cfg.get("staff_keys_file"):
            return Path(srv.cfg["staff_keys_file"])
        if srv.cfg.get("reports_dir"):
            d = Path(srv.cfg["reports_dir"]).parent / "staffkeys"
            if d.is_dir():
                return d / "staffkeys.txt"
        return None

    def create_staff_key(self, discord_id: str, name: str, pub: str) -> tuple:
        """Replaces the person's key with a new public key; returns (key id, servers that did not take it)."""
        self.store.x("UPDATE staff_keys SET revoked=?, revoked_by='replaced' WHERE discord_id=? AND revoked=0", (now(), discord_id))
        kid = "k" + secrets.token_hex(5)
        clean = re.sub(r"[^\w .|*\[\]()-]", "", name, flags=re.ASCII).strip()[:24] or "staff"
        self.store.x("INSERT INTO staff_keys(id,discord_id,name,public,created) VALUES(?,?,?,?,?)", (kid, discord_id, clean, pub, now()))
        return kid, self.publish_staff_keys()

    def revoke_staff_keys(self, discord_id: str, by: str) -> int:
        n = self.store.one("SELECT COUNT(*) n FROM staff_keys WHERE discord_id=? AND revoked=0", (discord_id,))["n"]
        if n:
            self.store.x("UPDATE staff_keys SET revoked=?, revoked_by=? WHERE discord_id=? AND revoked=0", (now(), by, discord_id))
            self.store.audit({"discord_id": "", "name": "Staff keys"}, "staff key revoked", target=discord_id, detail=by)
            self.publish_staff_keys()
        return n

    def prune_bugshots(self) -> None:
        """Screenshots whose report is gone (closed reports are pruned after the retention time)."""
        if not self.bugshots.is_dir():
            return
        keep = {self.bugshot_path(r["file"]).name for r in self.store.q("SELECT file FROM reports WHERE source='bug'")}
        for f in self.bugshots.glob("*.jpg"):
            if f.name not in keep and f.stat().st_mtime < time.time() - 3600:
                f.unlink(missing_ok=True)

    def health(self) -> dict:
        t, cached = self.health_cache
        if cached and time.time() - t < 5:
            return cached
        h = {"time": now(), "portal_version": VERSION}
        try:
            h["load"] = [float(x) for x in Path("/proc/loadavg").read_text().split()[:3]]
            h["cpus"] = os.cpu_count()
            mem = dict(re.findall(r"^(\w+):\s+(\d+)", Path("/proc/meminfo").read_text(), re.M))
            h["mem_total_mb"] = int(mem.get("MemTotal", 0)) // 1024
            h["mem_available_mb"] = int(mem.get("MemAvailable", 0)) // 1024
            h["uptime_s"] = int(float(Path("/proc/uptime").read_text().split()[0]))
        except (OSError, ValueError):
            pass
        try:
            st = os.statvfs(self.cfg.get("disk_path", "/"))
            h["disk_total_gb"] = round(st.f_blocks * st.f_frsize / 1e9, 1)
            h["disk_free_gb"] = round(st.f_bavail * st.f_frsize / 1e9, 1)
        except OSError:
            pass
        units = []
        for s in self.servers.values():
            units.append(self._unit(s.cfg.get("unit"), s.key, s.name))
        for extra in self.cfg.get("services", []):
            units.append(self._unit(extra.get("unit"), extra.get("key", extra.get("unit")), extra.get("name", extra.get("unit"))))
        h["services"] = units
        self.health_cache = (time.time(), h)
        return h

    def _unit(self, unit: str | None, key: str, name: str) -> dict:
        row = {"key": key, "name": name, "unit": unit or "", "state": "unknown"}
        if not unit or not shutil.which("systemctl"):
            return row
        try:
            out = subprocess.run(["systemctl", "show", unit, "--no-pager", "-p",
                                  "ActiveState,SubState,ActiveEnterTimestamp,NRestarts,MemoryCurrent,CPUUsageNSec,MainPID"],
                                 capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.SubprocessError):
            return row
        p = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
        row["state"] = p.get("ActiveState", "unknown")
        row["sub"] = p.get("SubState", "")
        row["since"] = p.get("ActiveEnterTimestamp", "")
        row["restarts"] = int(p["NRestarts"]) if p.get("NRestarts", "").isdigit() else None
        row["memory_mb"] = int(p["MemoryCurrent"]) // 1048576 if p.get("MemoryCurrent", "").isdigit() else None
        row["cpu_s"] = int(p["CPUUsageNSec"]) // 10**9 if p.get("CPUUsageNSec", "").isdigit() else None
        try:
            j = subprocess.run(["journalctl", "-u", unit, "--since", "-24h", "--no-pager", "-o", "cat",
                                "--grep", r"segfault|core dumped|Main process exited|Failed with result"],
                               capture_output=True, text=True, timeout=5).stdout
            lines = [x for x in j.splitlines() if x.strip() and not x.startswith("-- ")]
            row["problems_24h"] = len(lines)
            row["last_problem"] = lines[-1][:200] if lines else ""
        except (OSError, subprocess.SubprocessError):
            pass
        return row

    def ip_tag(self, ip: str) -> str:
        """A stable tag for an address that cannot be turned back into it (keyed, unlike a plain hash of an IPv4)."""
        key = self.meta("ip_tag_key") or self.meta("ip_tag_key", secrets.token_hex(32))
        return hmac.new(key.encode(), ip.encode(), hashlib.sha256).hexdigest()[:12]

    # ------------------------------------------------------------------ rate limit (per key, per window)
    def limited(self, key: str, limit: int, window: int, peek: bool = False) -> bool:
        """True when key used its limit within window; otherwise counts this use (peek: only looks)."""
        t = time.time()
        with self.rate_lock:
            hits = [x for x in self.rate.get(key, []) if t - x < window]
            if len(hits) >= limit:
                self.rate[key] = hits
                return True
            if peek:
                return False
            hits.append(t)
            self.rate[key] = hits
            if len(self.rate) > 5000:
                self.rate = {k: v for k, v in self.rate.items() if v and t - v[-1] < 3600}
            return False


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ----------------------------------------------------------------------------- Discord sign-in

DISCORD_API = "https://discord.com/api/v10"


def http_json(url: str, data: dict | None = None, token: str | None = None, timeout: float = 8) -> dict:
    headers = {"User-Agent": "TrueCombatStaffPortal/%s" % VERSION, "Accept": "application/json"}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def secret(cfg: dict, name: str) -> str:
    cred = os.environ.get("CREDENTIALS_DIRECTORY")
    if cred and (Path(cred) / name).exists():
        return (Path(cred) / name).read_text(encoding="utf-8").strip()
    return str(cfg.get("discord", {}).get(name.replace("-", "_"), "") or "")


def resolve_role(portal: Portal, discord_id: str, member_roles: list) -> str | None:
    """Highest role from: the manual staff list (which can also revoke), owners, Discord roles."""
    d = portal.cfg.get("discord", {})
    row = portal.store.one("SELECT role FROM staff WHERE discord_id=?", (discord_id,))
    if row and row["role"] == "revoked":
        return None
    best = row["role"] if row and row["role"] in ("trial", "moderator", "admin") else None     # owner only ever from the config
    if str(discord_id) in {str(x) for x in portal.cfg.get("owners", [])}:
        best = "owner"
    roles = {str(r) for r in member_roles or []}
    for role, ids in (("admin", d.get("admin_role_ids", [])), ("moderator", d.get("moderator_role_ids", [])),
                      ("trial", d.get("trial_role_ids", []))):
        if roles & {str(x) for x in ids} and RANK[role] > RANK.get(best, 0):
            best = role
    return best


# ----------------------------------------------------------------------------- HTTP

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": ("default-src 'self'; img-src 'self' data: https://cdn.discordapp.com; "
                                "style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                                "base-uri 'none'; form-action 'self' https://discord.com"),
}
SESSION_HOURS = 12
RECHECK_SECONDS = 600


def make_handler(portal: Portal):
    cfg = portal.cfg
    public = cfg.get("public_url", "http://127.0.0.1:%d" % cfg.get("port", 8097)).rstrip("/")
    secure_cookie = public.startswith("https://")
    cookie_name = ("__Host-" if secure_cookie else "") + "tcpstaff"
    dev_login = bool(cfg.get("dev_login")) and os.environ.get("TCP_STAFF_DEV") == "1"

    class Handler(BaseHTTPRequestHandler):
        server_version = "TCPStaff"
        timeout = 30                       # a client that stops sending frees its thread
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # noqa: D401
            # the request log keeps only a shortened address (IPv4 /24, IPv6 /48); sign-in and
            # security events keep the full address in their own audit records
            log.info("%s %s", short_ip(self.client_ip()), fmt % args)

        # -- plumbing
        def client_ip(self) -> str:
            ip = self.client_address[0]
            if ip in ("127.0.0.1", "::1") and self.headers.get("X-Forwarded-For"):
                return self.headers["X-Forwarded-For"].split(",")[-1].strip()
            return ip

        def send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
            try:
                unread = int(self.headers.get("Content-Length") or 0) != 0 and not getattr(self, "_body_read", False)
            except ValueError:
                unread = True
            self.send_response(status)
            if unread:                       # an early refusal left the body in the stream: never reuse it
                self.close_connection = True
                self.send_header("Connection", "close")
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in SECURITY_HEADERS.items():
                self.send_header(k, v)
            if secure_cookie:
                self.send_header("Strict-Transport-Security", "max-age=31536000")
            for k, v in (extra or {}).items():
                if isinstance(v, list):
                    for item in v:
                        self.send_header(k, item)
                else:
                    self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def json(self, data, status: int = 200, extra: dict | None = None) -> None:
            self.send(status, json.dumps(data, separators=(",", ":")).encode(), "application/json; charset=utf-8", extra)

        def redirect(self, to: str, cookies: list | None = None) -> None:
            self.send(302, b"", "text/plain", {"Location": to, "Set-Cookie": cookies or []})

        def body(self, limit: int = 65536) -> bytes:
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError as e:
                raise ApiError(400, "Bad request.") from e
            if n < 0:                            # a negative length would read until the client stops sending
                raise ApiError(400, "Bad request.")
            if n > limit:
                if n <= 4 * 1024 * 1024:         # read a moderate overshoot away, so the client gets the answer
                    left = n                     # instead of a reset connection; anything bigger is just cut off
                    while left > 0:
                        chunk = self.rfile.read(min(left, 65536))
                        if not chunk:
                            break
                        left -= len(chunk)
                    self._body_read = True
                raise ApiError(413, "Too much data.")
            self._body_read = True
            return self.rfile.read(n) if n else b""

        def body_json(self, limit: int = 65536) -> dict:
            try:
                data = json.loads(self.body(limit) or b"{}")
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

        # -- sessions
        def session(self) -> dict | None:
            sid = self.cookie(cookie_name)
            if not sid or not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", sid):
                return None
            s = portal.store.one("SELECT * FROM sessions WHERE id=?", (hashlib.sha256(sid.encode()).hexdigest(),))
            if not s:
                return None
            t = now()
            if t - s["created"] > SESSION_HOURS * 3600:
                portal.store.x("DELETE FROM sessions WHERE id=?", (s["id"],))
                return None
            if t - (s["checked"] or 0) > RECHECK_SECONDS:
                role = self.recheck(s)
                if not role:
                    portal.store.x("DELETE FROM sessions WHERE id=?", (s["id"],))
                    portal.revoke_staff_keys(s["discord_id"], "lost staff role")
                    return None
                s["role"] = role
                portal.store.x("UPDATE sessions SET role=?, checked=? WHERE id=?", (role, t, s["id"]))
            if t - s["seen"] > 60:
                portal.store.x("UPDATE sessions SET seen=? WHERE id=?", (t, s["id"]))
            s["perms"] = portal.effective_perms(s["discord_id"], s["role"])
            return s

        def recheck(self, s: dict) -> str | None:
            """Staff rights follow Discord: a removed role or a revoked entry ends the session within minutes."""
            if s["token"] == "dev":
                return resolve_role(portal, s["discord_id"], []) or s["role"]
            guild = cfg.get("discord", {}).get("guild_id")
            try:
                member = http_json("%s/users/@me/guilds/%s/member" % (DISCORD_API, guild), token=s["token"])
                roles = member.get("roles", [])
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404):
                    roles = []
                else:
                    return s["role"]          # Discord trouble: keep the session for now
            except (urllib.error.URLError, OSError, ValueError):
                return s["role"]
            return resolve_role(portal, s["discord_id"], roles)

        def new_session(self, discord_id: str, name: str, avatar: str, role: str, token: str) -> str:
            sid = secrets.token_urlsafe(32)
            t = now()
            portal.store.x("INSERT INTO sessions(id,discord_id,name,avatar,role,csrf,created,seen,checked,token,ip) "
                           "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (hashlib.sha256(sid.encode()).hexdigest(), discord_id, name, avatar, role,
                            secrets.token_urlsafe(24), t, t, t, token, self.client_ip()))
            portal.store.x("INSERT INTO staff(discord_id,name,role,note,added_by,created,last_login) VALUES(?,?,NULL,'',"
                           "'discord',?,?) ON CONFLICT(discord_id) DO UPDATE SET name=excluded.name, last_login=excluded.last_login",
                           (discord_id, name, t, t))
            portal.store.audit({"discord_id": discord_id, "name": name, "role": role}, "sign-in", detail=self.client_ip())
            return sid

        def need(self, s: dict | None, perm: str) -> dict:
            if not s:
                raise ApiError(401, "Please sign in.")
            if not allowed(s, perm):
                raise ApiError(403, "Your role cannot do that.")
            if RANK[PERMS[perm]] >= RANK["admin"] and cfg.get("require_2fa", True) and not self.totp_on(s):
                raise ApiError(403, "Admin tools need two-step sign-in. Turn it on under your name, bottom left.")
            return s

        def totp_on(self, s: dict) -> bool:
            r = portal.store.one("SELECT enabled FROM totp WHERE discord_id=?", (s["discord_id"],))
            return bool(r and r["enabled"])

        def mfa_pending(self, s: dict | None) -> bool:
            return bool(s) and not s.get("mfa") and self.totp_on(s)

        # -- routing
        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            self.dispatch("GET")

        def do_POST(self):
            self.dispatch("POST")

        def dispatch(self, method: str) -> None:
            url = urllib.parse.urlsplit(self.path)
            path = url.path
            qs = dict(urllib.parse.parse_qsl(url.query))
            try:
                if method == "GET" and (path == "/" or path == "/index.html"):
                    return self.static("index.html")
                if method == "GET" and path == "/sw.js":         # at the root, so it may handle the whole portal
                    return self.static("sw.js")
                if method == "GET" and path.startswith("/static/"):
                    return self.static(path[len("/static/"):])
                if path == "/healthz":
                    return self.json({"ok": True, "version": VERSION})
                if path.startswith("/auth/"):
                    return self.auth(method, path, qs)
                if path == "/api/bugreport" and method == "POST":
                    return self.bugreport()
                if path == "/api/gamecheck" and method == "POST":
                    return self.gamecheck()
                if path == "/api/gamecheck/public" and method == "GET":
                    k = portal.gamecheck_key()
                    return self.json({"public": k[1].hex() if k else ""})
                if path == "/api/staffkey/claim" and method == "POST":
                    return self.staffkey_claim()
                if path == "/api/staffcert" and method == "GET":
                    return self.staffcert(qs)
                if path in ("/appeal", "/appeal/") and method == "GET":
                    return self.static("appeal.html")
                if path.startswith("/appeal/"):
                    return self.appeal(method, path, qs)
                if path.startswith("/bot/"):
                    return self.bot_api(method, path[len("/bot/"):], qs)
                if path.startswith("/api/"):
                    s = self.session()
                    route = path[len("/api/"):]
                    if self.mfa_pending(s) and route not in ("me", "2fa", "2fa/verify"):
                        raise ApiError(401, "Enter the code from your authenticator app first.")
                    if method == "POST":
                        if not s:
                            raise ApiError(401, "Please sign in.")
                        if not hmac.compare_digest(self.headers.get("X-CSRF", ""), s["csrf"]):
                            raise ApiError(403, "Your session expired. Reload the page.")
                        origin = self.headers.get("Origin")
                        if origin and origin.rstrip("/") != public:
                            raise ApiError(403, "Wrong origin.")
                    return self.api(method, path[len("/api/"):], qs, s)
                raise ApiError(404, "Not found.")
            except (BrokenPipeError, ConnectionResetError):
                return
            except ApiError as e:
                self.json({"error": e.message}, e.status)
            except ValueError as e:
                msg = str(e)
                self.json({"error": msg if msg.startswith("Use ") else "Check the values you entered."}, 400)
            except RconError as e:
                self.json({"error": "The game server did not take the command: %s" % e}, 502)
            except Exception:  # noqa: BLE001
                log.exception("request failed: %s %s", method, path)
                self.json({"error": "Something went wrong on the portal. It has been logged."}, 500)

        def static(self, name: str) -> None:
            target = (STATIC / name).resolve()
            if STATIC.resolve() not in target.parents or not target.is_file():
                raise ApiError(404, "Not found.")
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript",):
                ctype += "; charset=utf-8"
            self.send(200, target.read_bytes(), ctype)

        # -- sign-in
        def auth(self, method: str, path: str, qs: dict) -> None:
            d = cfg.get("discord", {})
            if path == "/auth/login":
                state = secrets.token_urlsafe(24)
                url = "https://discord.com/oauth2/authorize?" + urllib.parse.urlencode({
                    "client_id": d.get("client_id", ""), "response_type": "code",
                    "redirect_uri": public + "/auth/callback", "scope": "identify guilds.members.read",
                    "state": state, "prompt": "none"})
                return self.redirect(url, [self.set_cookie("tcpstaff_state", state, 600)])
            if path == "/auth/callback":
                state = self.cookie("tcpstaff_state")
                if not state or not hmac.compare_digest(state, qs.get("state", "")) or not qs.get("code"):
                    return self.redirect("/?signin=failed")
                if portal.limited("login:" + self.client_ip(), 10, 600):
                    return self.redirect("/?signin=slow")
                try:
                    tok = http_json(DISCORD_API + "/oauth2/token", {
                        "client_id": d.get("client_id", ""), "client_secret": secret(cfg, "client-secret"),
                        "grant_type": "authorization_code", "code": qs["code"],
                        "redirect_uri": public + "/auth/callback"})
                    token = tok["access_token"]
                    me = http_json(DISCORD_API + "/users/@me", token=token)
                    try:
                        member = http_json("%s/users/@me/guilds/%s/member" % (DISCORD_API, d.get("guild_id")), token=token)
                    except urllib.error.HTTPError:
                        member = {}
                except (urllib.error.URLError, OSError, ValueError, KeyError):
                    log.exception("Discord sign-in failed")
                    return self.redirect("/?signin=discord")
                discord_id = str(me.get("id"))
                role = resolve_role(portal, discord_id, member.get("roles", []))
                name = member.get("nick") or me.get("global_name") or me.get("username") or "Staff"
                if not role:
                    portal.store.audit({"discord_id": discord_id, "name": name}, "sign-in refused", detail=self.client_ip(), ok=False)
                    return self.redirect("/?signin=denied", [self.set_cookie("tcpstaff_state", "", 0)])
                avatar = ("https://cdn.discordapp.com/avatars/%s/%s.png?size=64" % (discord_id, me["avatar"])) if me.get("avatar") else ""
                sid = self.new_session(discord_id, name, avatar, role, token)
                return self.redirect("/", [self.set_cookie(cookie_name, sid, SESSION_HOURS * 3600),
                                           self.set_cookie("tcpstaff_state", "", 0)])
            if (path == "/auth/dev" and dev_login and self.client_address[0] in ("127.0.0.1", "::1")
                    and not self.headers.get("X-Forwarded-For")):          # never through the reverse proxy
                role = qs.get("role", "owner")
                if role not in RANK:
                    raise ApiError(400, "Unknown role.")
                did = qs.get("id", "dev-" + role)
                sid = self.new_session(did, qs.get("name", "Dev " + role.title()), "", role, "dev")
                return self.redirect("/", [self.set_cookie(cookie_name, sid, SESSION_HOURS * 3600)])
            if path == "/auth/logout" and method == "POST":
                s = self.session()
                if s and hmac.compare_digest(self.headers.get("X-CSRF", ""), s["csrf"]):
                    portal.store.x("DELETE FROM sessions WHERE id=?", (s["id"],))
                return self.json({"ok": True}, extra={"Set-Cookie": [self.set_cookie(cookie_name, "", 0)]})
            raise ApiError(404, "Not found.")

        # -- the launcher renews the certificate of an installed key (public data; no session needed)
        def staffcert(self, qs: dict) -> None:
            if portal.limited("staffcert:" + self.client_ip(), 60, 3600):
                raise ApiError(429, "Too many tries. Try again later.")
            c = portal.staff_cert(str(qs.get("id", "")))
            if not c:
                raise ApiError(404, "No certificate for this key.")
            return self.json({"cert": c["cert"], "expires": c["expires"]})

        # -- the launcher claims a one-time "Install in game" link: it sends the public half of a key pair it made
        def staffkey_claim(self) -> None:
            ip = self.client_ip()
            if portal.limited("keyclaim:" + ip, 10, 3600):
                raise ApiError(429, "Too many tries. Try again later.")
            d = self.body_json()
            code, pub = str(d.get("code", "")).lower(), str(d.get("public", "")).lower()
            if not re.fullmatch(r"[0-9a-f]{32}", code) or not re.fullmatch(r"[0-9a-f]{64}", pub) or pub == "0" * 64:
                raise ApiError(400, "Bad request.")
            h = hashlib.sha256(code.encode()).hexdigest()
            with portal.store.lock:
                row = portal.store.one("SELECT * FROM staff_key_codes WHERE code_hash=?", (h,))
                portal.store.x("DELETE FROM staff_key_codes WHERE code_hash=?", (h,))        # single use, right or wrong
            if not row or row["expires"] < now():
                raise ApiError(410, "This link has expired. Make a new one in the staff portal.")
            # access ends sessions, so a link only works while the person who made it still has a portal session
            staff = portal.store.one("SELECT role FROM staff WHERE discord_id=?", (row["discord_id"],))
            if (staff and staff["role"] == "revoked") or not portal.store.one(
                    "SELECT 1 x FROM sessions WHERE discord_id=?", (row["discord_id"],)):
                raise ApiError(403, "This account no longer has staff access.")
            if portal.limited("staffkey:" + row["discord_id"], 5, 86400):
                raise ApiError(429, "Five keys were made for this account today. Try again tomorrow.")
            kid, problems = portal.create_staff_key(row["discord_id"], row["name"], pub)
            portal.store.audit({"discord_id": row["discord_id"], "name": row["name"]}, "staff key made", target=kid,
                               detail="installed by the launcher")
            c = portal.staff_cert(kid)
            self.json(dict({"id": kid, "name": row["name"]}, **({"cert": c["cert"], "expires": c["expires"]} if c else {})), 201)

        # -- public start check: the launcher and the game ask before they let the player in (0.39.8+)
        def gamecheck(self) -> None:
            ip = self.client_ip()
            if portal.limited("gc:" + ip, int(cfg.get("gamecheck_per_hour", 60)), 3600):
                raise ApiError(429, "Too many checks from this address. Try again later.")
            try:
                j = json.loads(self.body(limit=8 * 1024).decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                raise ApiError(400, "Bad JSON.") from e
            if not isinstance(j, dict) or j.get("format") != "tcp-gamecheck/1":
                raise ApiError(400, "Unknown check format.")
            self.json(portal.gamecheck(j, ip))

        # -- public bug report intake: F12 in game (0.36.0+) posts JSON "tcp-bugreport/1"; older tools post plain text
        def bugreport(self) -> None:
            ip = self.client_ip()
            if portal.limited("bug:" + ip, int(cfg.get("bugreport_per_hour", 6)), 3600) or portal.limited("bug:*", 300, 86400):
                raise ApiError(429, "Too many reports from this address. Try again later.")
            if portal.store.one("SELECT COUNT(*) n FROM reports WHERE source='bug' AND status<>'closed'")["n"] >= int(cfg.get("bugreport_open_max", 1000)):
                raise ApiError(503, "The bug report inbox is full. Try again later.")
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            raw = self.body(limit=int(cfg.get("bugreport_max_bytes", 1600 * 1024)))
            key = "bug/%d-%s" % (now(), secrets.token_hex(4))
            shot = b""
            if ctype == "application/json":
                try:
                    j = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError) as e:
                    raise ApiError(400, "Bad JSON.") from e
                if not isinstance(j, dict) or j.get("format") != "tcp-bugreport/1":
                    raise ApiError(400, "Unknown report format.")
                data, shot = bug_fields(j)
                text = data["text"]
            else:
                text = clean_text(raw.decode("utf-8", "replace"), 96 * 1024)
                data = {"category": bug_category(self.headers.get("X-Report-Category", "")), "text": text}
            if len(text.strip()) < 10:
                raise ApiError(400, "The report is empty.")
            data["summary"] = next((ln for ln in text.splitlines() if ln.strip()), "")[:120]
            data["from"] = portal.ip_tag(ip)
            if portal.game_ban_for(id_pairs(data.get("pid", ""), data.get("puid", ""), data.get("kid", ""),
                                            data.get("hwid") or (), data["from"]), via="bug report"):
                portal.store.x("INSERT INTO meta(key,value) VALUES('bugreports_dropped','1') ON CONFLICT(key) DO UPDATE "
                               "SET value=CAST(value AS INTEGER)+1")
                return self.json({"ok": True, "id": key}, 201)   # banned from the game: dropped, and nothing tells the sender
            if shot and portal.bugshots_bytes() + len(shot) > int(cfg.get("bugshot_max_mb", 500)) * 1024 * 1024:
                shot = b""                       # disk guard: the report still arrives, without its picture
                data["shot_dropped"] = True
            if shot:
                path = portal.bugshot_path(key)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(shot)
                data["shot"] = True
            if data.get("server"):
                srv = portal.server_by_address(data["server"])
                if srv:
                    data["server_name"] = srv.name
            pid = data.get("pid", "")
            portal.store.x("INSERT INTO reports(source,file,server,received,data,target_pid,target_name,status,updated) "
                           "VALUES('bug',?,?,?,?,?,?,'open',?)",
                           (key, data.get("server_name", ""), now(), json.dumps(data), pid, data.get("name", ""), now()))
            where = " on %s" % data["map"] if data.get("map") else ""
            by = " from %s" % data["name"] if data.get("name") else ""
            # one alert per report, but a player sending many in a row raises one alert per ten minutes
            portal.alert("bugreport", discord_plain("%s report%s%s" % (data["category"], by, where)),
                         discord_plain(data["summary"]) + ("\nBuild %s" % discord_plain(data["build"]) if data.get("build") else ""),
                         key=("bugreport:" + pid) if pid else key, window=600 if pid else 0, pid=pid)
            self.json({"ok": True, "id": key}, 201)

        # -- API
        def api(self, method: str, route: str, qs: dict, s: dict | None) -> None:
            if route == "me" and method == "GET":
                if not s:
                    return self.json({"signed_in": False, "dev_login": dev_login})
                perms = sorted(p for p in PERMS if allowed(s, p))
                return self.json({"signed_in": True, "name": s["name"], "avatar": s["avatar"], "role": s["role"],
                                  "discord_id": s["discord_id"], "csrf": s["csrf"], "perms": perms,
                                  "mfa_pending": self.mfa_pending(s), "mfa_on": self.totp_on(s),
                                  "mfa_required": bool(cfg.get("require_2fa", True)) and RANK.get(s["role"], 0) >= RANK["admin"],
                                  "ladder": {k: {"label": v["label"], "steps": [step_label(x) for x in v["steps"]]}
                                             for k, v in portal.ladder().items()},
                                  "undo_seconds": UNDO_SECONDS,
                                  "mod_ban_limit": MOD_BAN_LIMIT, "version": VERSION,
                                  "maps": cfg.get("maps", []), "site": cfg.get("site", "https://truecombat.eu")})
            if route == "servers" and method == "GET":
                who = self.need(s, "view")
                return self.json({"servers": portal.servers_view(allowed(who, "lookup.ip")), "time": now()})
            if route == "dashboard" and method == "GET":
                who = self.need(s, "view")
                return self.json(portal.dashboard(who))
            if route == "search" and method == "GET":
                who = self.need(s, "view")
                if portal.limited("search:" + who["discord_id"], 120, 60):
                    raise ApiError(429, "Slow down a little.")
                return self.json(portal.search(who, qs.get("q", "")))
            if route == "backup" and method == "GET":
                self.need(s, "backup")
                return self.json(portal.backup_status())
            if route == "backup" and method == "POST":
                who = self.need(s, "backup")
                if portal.limited("backup-now", 3, 3600):
                    raise ApiError(429, "Three snapshots were made in the last hour. Try again later.")
                st = portal.backup_now()
                portal.store.audit(who, "backup snapshot", ok=st["ok"], result=st.get("error", "") or "%d bytes" % st.get("size", 0))
                return self.json(st)
            if route == "chat" and method == "GET":
                self.need(s, "view")
                after = int(qs.get("after") or 0)
                server = qs.get("server", "")
                args, sql = [after], "SELECT * FROM chat WHERE id>?"
                if server:
                    sql += " AND server=?"
                    args.append(server)
                if after:
                    sql += " ORDER BY id ASC LIMIT 200"
                    rows = portal.store.q(sql, args)
                else:
                    rows = list(reversed(portal.store.q(sql + " ORDER BY id DESC LIMIT 150", args)))
                return self.json({"lines": rows})
            if route == "action" and method == "POST":
                return self.player_action(s, self.body_json())
            if route == "server" and method == "POST":
                return self.server_action(s, self.body_json())
            if route == "bans" and method == "GET":
                self.need(s, "view")
                show = qs.get("show", "active")
                where = "active=1" if show == "active" else "1=1"
                bans = portal.store.q("SELECT id,pid,name,reason,created,expires,by_name,active,lifted,lifted_by,lift_reason,appeal_code,"
                                      "guid<>'' has_guid, ip<>'' has_ip, puid<>'' has_puid, game, (SELECT COUNT(*) FROM ban_ids WHERE ban_id=bans.id) identities, (SELECT audit_id FROM undo WHERE kind='ban' "
                                      "AND ref=bans.id AND done=0 AND expires>? AND (by_id=? OR ?)) undo FROM bans WHERE %s "
                                      "ORDER BY id DESC LIMIT 500" % where, (now(), s["discord_id"], 1 if allowed(s, "ban.remove") else 0))
                return self.json({"bans": bans})
            if route == "bans" and method == "POST":
                return self.ban(s, self.body_json())
            if route == "bans/lift" and method == "POST":
                return self.unban(s, self.body_json())
            if route == "bans/server" and method == "GET":
                self.need(s, "ban.remove")
                out = {}
                for key in portal.order:
                    try:
                        out[key] = parse_banlist(portal.servers[key].run("banlist", timeout=2))
                    except RconError as e:
                        out[key] = {"error": str(e)}
                return self.json({"servers": out})
            if route == "bans/sync" and method == "POST":
                who = self.need(s, "ban.remove")
                rep = portal.reconcile_bans()
                portal.store.audit(who, "ban sync", detail=json.dumps(rep))
                return self.json({"result": rep})
            if route == "lookup" and method == "GET":
                who = self.need(s, "lookup")
                return self.json({"players": portal.lookup(qs.get("q", ""), allowed(who, "lookup.ip"))})
            if route.startswith("player/") and method == "GET":
                who = self.need(s, "lookup")
                return self.json(portal.player(route[len("player/"):], allowed(who, "lookup.ip")))
            if route == "notes" and method == "POST":
                who = self.need(s, "lookup")
                d = self.body_json()
                pid, text = str(d.get("pid", "")), str(d.get("text", "")).strip()[:1000]
                if not PID.match(pid) or not text:
                    raise ApiError(400, "Write a note first.")
                portal.store.x("INSERT INTO notes(pid,text,created,by_name) VALUES(?,?,?,?)", (pid, text, now(), who["name"]))
                portal.store.audit(who, "note", target=pid, pid=pid, detail=text[:200])
                return self.json({"ok": True})
            if route == "reports" and method == "GET":
                self.need(s, "reports")
                portal.scan_reports()
                status = qs.get("status", "open")
                where, args = ("status=?", [status]) if status in ("open", "claimed", "closed") else ("1=1", [])
                if qs.get("source") in ("player", "auto", "bug", "appeal"):
                    where += " AND source=?"
                    args.append(qs["source"])
                rows = [portal._report_row(r) for r in portal.store.q(
                    "SELECT * FROM reports WHERE %s ORDER BY id DESC LIMIT 300" % where, args)]
                counts = {r["status"]: r["n"] for r in portal.store.q("SELECT status, COUNT(*) n FROM reports GROUP BY status")}
                return self.json({"reports": rows, "counts": counts})
            if route == "reports/bug" and method == "GET":
                self.need(s, "reports")
                r = portal.store.one("SELECT * FROM reports WHERE id=? AND source='bug'", (int(qs.get("id") or 0),))
                if not r:
                    raise ApiError(404, "No such report.")
                return self.json({"report": portal._report_row(r, full=True)})
            if route == "reports/bugshot" and method == "GET":
                self.need(s, "reports")
                r = portal.store.one("SELECT file FROM reports WHERE id=? AND source='bug'", (int(qs.get("id") or 0),))
                path = portal.bugshot_path(r["file"]) if r else None
                if not path or not path.is_file():
                    raise ApiError(404, "No screenshot.")
                return self.send_file(path, path.name, "image/jpeg", cache="private, max-age=86400")
            if route == "reports/update" and method == "POST":
                who = self.need(s, "reports")
                d = self.body_json()
                r = portal.store.one("SELECT * FROM reports WHERE id=?", (int(d.get("id") or 0),))
                if not r:
                    raise ApiError(404, "No such report.")
                status = d.get("status")
                if status not in ("open", "claimed", "closed"):
                    raise ApiError(400, "Unknown status.")
                if r["source"] == "appeal" and status != "claimed":
                    raise ApiError(409, "Answer the appeal with Accept or Deny; the player reads that answer.")
                resolution = str(d.get("resolution") or "").strip()[:500]
                portal.store.x("UPDATE reports SET status=?, claimed_by=?, resolution=?, updated=? WHERE id=?",
                               (status, who["name"] if status != "open" else None, resolution or r["resolution"], now(), r["id"]))
                portal.store.audit(who, "report " + status, server=r["server"], target=r["target_name"],
                                   pid=r["target_pid"], detail=("#%d %s" % (r["id"], resolution)).strip())
                return self.json({"ok": True})
            if route == "audit" and method == "GET":
                self.need(s, "audit")
                args, where = [], "1=1"
                if qs.get("q"):
                    where = "(staff LIKE ? OR action LIKE ? OR target LIKE ? OR detail LIKE ? OR target_pid=?)"
                    like = "%" + qs["q"] + "%"
                    args = [like, like, like, like, qs["q"]]
                before = int(qs.get("before") or 0)
                if before:
                    where += " AND id<?"
                    args.append(before)
                return self.json({"entries": portal.store.q("SELECT * FROM audit WHERE %s ORDER BY id DESC LIMIT 200" % where, args)})
            if route == "staff" and method == "GET":
                self.need(s, "staff.manage")
                return self.json({"staff": portal.store.q("SELECT * FROM staff ORDER BY last_login DESC")})
            if route == "staff" and method == "POST":
                return self.staff_change(s, self.body_json())
            if route == "health" and method == "GET":
                self.need(s, "health")
                return self.json(portal.health())
            if route == "health/restart" and method == "POST":
                return self.restart(s, self.body_json())
            return self.api2(method, route, qs, s)

        # -- API, round two: moderation tools, alerts, operations and two-step sign-in
        def api2(self, method: str, route: str, qs: dict, s: dict | None) -> None:
            G, P = method == "GET", method == "POST"
            # 1.4.2: push, duty, history, quality, anti-cheat queue, per-person rights
            if route == "push/key" and G:
                self.need(s, "view")
                return self.json({"key": b64url(portal.vapid()[1])})
            if route == "push/subscribe" and P:
                who = self.need(s, "view")
                d = self.body_json()
                portal.push_subscribe(who, str(d.get("endpoint") or ""))
                return self.json({"ok": True})
            if route == "push/unsubscribe" and P:
                who = self.need(s, "view")
                d = self.body_json()
                portal.store.x("DELETE FROM push_subs WHERE endpoint=? AND discord_id=?", (str(d.get("endpoint") or ""), who["discord_id"]))
                return self.json({"ok": True})
            if route == "push/test" and P:
                who = self.need(s, "view")
                if portal.limited("pushtest:" + who["discord_id"], 5, 600):
                    raise ApiError(429, "Five test notifications in ten minutes is enough.")
                portal.alert("push_test", "Test notification", "%s checked that alerts reach their device." % who["name"],
                             key="push-test:%s:%d" % (who["discord_id"], now()))
                subs = portal.store.q("SELECT * FROM push_subs WHERE discord_id=?", (who["discord_id"],))
                sent = sum(1 for x in subs if portal.push_send(x, True))
                return self.json({"ok": True, "devices": len(subs), "sent": sent})
            if route == "push/latest" and G:
                who = self.need(s, "view")
                return self.json(portal.push_latest(who))
            if route == "duty" and G:
                who = self.need(s, "view")
                mine = portal.store.one("SELECT since, until FROM duty WHERE discord_id=? AND until>?", (who["discord_id"], now()))
                return self.json({"on_duty": portal.duty_list(), "me": {"on": bool(mine), **(mine or {})},
                                  "devices": portal.store.one("SELECT COUNT(*) n FROM push_subs WHERE discord_id=?", (who["discord_id"],))["n"]})
            if route == "duty" and P:
                who = self.need(s, "duty")
                d = self.body_json()
                return self.json(portal.duty_set(who, bool(d.get("on")), d.get("hours") or 4))
            if route == "history" and G:
                self.need(s, "history")
                server = qs.get("server", "")
                if server and server not in portal.servers:
                    raise ApiError(404, "Unknown server.")
                return self.json(portal.history(int(qs.get("days") or 7), server))
            if route == "quality" and G:
                self.need(s, "quality")
                return self.json(portal.quality(int(qs.get("days") or 30)))
            if route == "anticheat" and G:
                self.need(s, "anticheat")
                return self.json({"items": portal.ac_list(qs.get("status", "open")),
                                  "counts": {r["status"]: r["n"] for r in portal.store.q("SELECT status, COUNT(*) n FROM ac_queue GROUP BY status")}})
            if route == "anticheat" and P:
                who = self.need(s, "anticheat")
                d = self.body_json()
                portal.ac_resolve(who, int(d.get("id") or 0), str(d.get("outcome") or ""), str(d.get("note") or ""))
                return self.json({"ok": True})
            if route == "staff/rights" and G:
                self.need(s, "staff.manage")
                did = qs.get("id", "")
                row = portal.store.one("SELECT discord_id, name, role, perms_add, perms_remove FROM staff WHERE discord_id=?", (did,))
                if not row:
                    raise ApiError(404, "Not on the staff list.")
                add, rem = grants_of(row)
                return self.json({"discord_id": did, "name": row["name"], "role": row["role"], "add": add, "remove": rem,
                                  "perms": {k: v for k, v in PERMS.items()}, "presets": GRANT_PRESETS, "roles": ROLES})
            if route == "staff/rights" and P:
                who = self.need(s, "staff.manage")
                d = self.body_json()
                did = str(d.get("discord_id") or "")
                target = portal.store.one("SELECT role FROM staff WHERE discord_id=?", (did,))
                live = portal.store.one("SELECT 1 x FROM sessions WHERE discord_id=? AND role IN ('admin','owner')", (did,))
                if ((target and target["role"] == "admin") or live) and who["role"] != "owner":
                    raise ApiError(403, "Only the owner changes an admin.")
                return self.json({"ok": True, **portal.set_grants(who, did, list(d.get("add") or []), list(d.get("remove") or []))})
            # live updates (1.4.1)
            if route == "stream" and G:
                return self.stream(self.need(s, "view"))
            # cases
            if route == "cases" and G:
                who = self.need(s, "cases")
                mine = who["name"] if qs.get("mine") else ""
                pid = qs.get("pid", "")
                return self.json({"cases": portal.cases(qs.get("status", "open") if not pid else "all", mine, pid)})
            if route.startswith("case/") and route[5:].isdigit() and G:
                who = self.need(s, "cases")
                return self.json(portal.case_view(who, int(route[5:])))
            if route == "cases" and P:
                who = self.need(s, "cases")
                d = self.body_json()
                if portal.limited("case:" + who["discord_id"], 30, 3600):
                    raise ApiError(429, "That is a lot of new cases. Wait a little.")
                cid = portal.case_open(who, d.get("title", ""), str(d.get("pid") or ""), str(d.get("name") or ""),
                                       str(d.get("summary") or ""), int(d.get("report") or 0))
                return self.json({"ok": True, "id": cid}, 201)
            if route == "case/update" and P:
                who = self.need(s, "cases")
                d = self.body_json()
                return self.json({"ok": True, "case": portal.case_update(who, int(d.get("id") or 0), d)})
            if route == "case/link" and P:
                who = self.need(s, "cases")
                d = self.body_json()
                portal.case_link(who, int(d.get("id") or 0), str(d.get("kind") or ""), int(d.get("ref") or 0))
                c = portal.case_row(int(d.get("id") or 0))
                portal.store.audit(who, "case updated", target=c["name"] or c["title"], pid=c["pid"],
                                   detail="#%d added %s #%d" % (c["id"], d.get("kind"), int(d.get("ref") or 0)))
                return self.json({"ok": True})
            if route == "case/unlink" and P:
                who = self.need(s, "cases")
                d = self.body_json()
                portal.case_unlink(who, int(d.get("id") or 0), int(d.get("item") or 0))
                return self.json({"ok": True})
            if route == "case/note" and P:
                who = self.need(s, "cases")
                d = self.body_json()
                portal.case_note(who, int(d.get("id") or 0), d.get("text", ""))
                return self.json({"ok": True})
            # player timeline
            if route.startswith("timeline/") and G:
                who = self.need(s, "lookup")
                return self.json(portal.timeline(route[len("timeline/"):], allowed(who, "lookup.ip")))
            # evidence locker
            if route == "evidence" and G:
                self.need(s, "evidence")
                if qs.get("case"):
                    return self.json({"evidence": portal.evidence_list(case_id=int(qs["case"] or 0))})
                if not PID.match(qs.get("pid", "")):
                    raise ApiError(400, "Name a case or a player.")
                return self.json({"evidence": portal.evidence_list(pid=qs["pid"]),
                                  "used_mb": round(portal.evidence_bytes() / 1048576, 1),
                                  "quota_mb": int(cfg.get("evidence_quota_mb", 2000))})
            if route == "evidence" and P:
                who = self.need(s, "evidence")
                if portal.limited("evidence:" + who["discord_id"], 60, 3600):
                    raise ApiError(429, "That is a lot of evidence in an hour. Wait a little.")
                d = self.body_json(limit=int(cfg.get("evidence_image_mb", 8)) * 1024 * 1024 * 4 // 3 + 4096)
                return self.json({"ok": True, "id": portal.evidence_add(who, d)}, 201)
            if route == "evidence/file" and G:
                who = self.need(s, "evidence")
                e, path = portal.evidence_file(int(qs.get("id") or 0))
                if e["kind"] == "image":
                    return self.send_file(path, path.name, e["mime"], cache="private, max-age=86400")
                portal.store.audit(who, "evidence download", target=e["title"], pid=e["pid"], detail="#%d" % e["id"])
                meta = json.loads(e["text"] or "{}") if e["kind"] == "demo" else {}
                return self.send_file(path, meta.get("file") or path.name)
            if route == "evidence/delete" and P:
                who = self.need(s, "evidence.delete")
                d = self.body_json()
                portal.evidence_delete(who, int(d.get("id") or 0), str(d.get("reason") or ""))
                return self.json({"ok": True})
            if route == "undo" and P:
                who = self.need(s, "view")
                d = self.body_json()
                return self.json({"ok": True, "message": portal.undo(who, int(d.get("id") or 0))})
            # punishment ladder
            if route == "punish/next" and G:
                self.need(s, "punish")
                pid = qs.get("pid", "")
                if not PID.match(pid):
                    raise ApiError(400, "Pick a player.")
                return self.json({"steps": [portal.next_step(pid, k) for k in portal.ladder()]})
            if route == "punish" and P:
                who = self.need(s, "punish")
                d = self.body_json()
                if portal.limited("act:" + who["discord_id"], 40, 60):
                    raise ApiError(429, "Slow down a little.")
                if d.get("server") is not None and d.get("slot") is not None:
                    srv, slot, p = self.target(d)
                    if p["bot"]:
                        raise ApiError(400, "That is a bot.")
                    return self.json(portal.punish(who, str(d.get("offence")), d.get("note", ""), srv=srv, slot=slot, p=p))
                return self.json(portal.punish(who, str(d.get("offence")), d.get("note", ""), pid=str(d.get("pid", ""))))
            # chat filter
            if route == "filters" and G:
                self.need(s, "view")
                return self.json({"filters": portal.store.q("SELECT * FROM filters ORDER BY active DESC, id DESC"),
                                  "flagged": portal.store.q("SELECT * FROM chat WHERE flag IS NOT NULL ORDER BY id DESC LIMIT 50")})
            if route == "filters" and P:
                who = self.need(s, "filters.manage")
                d = self.body_json()
                kind, action = d.get("kind", "word"), d.get("action", "flag")
                if action not in Watchers.SEVERITY:
                    raise ApiError(400, "Pick what the filter does.")
                try:
                    Watchers.compile_filter(d.get("pattern", ""), kind)
                except re.error as e:
                    raise ApiError(400, "That pattern does not work: %s" % e) from e
                except ValueError as e:
                    raise ApiError(400, str(e)) from e
                minutes = duration_minutes(d.get("length") or "10m") if action == "mute" else 0
                vals = (str(d["pattern"]).strip()[:200], kind, action, minutes, safe_arg(d.get("note", ""), 60), 1 if d.get("active", True) else 0)
                if d.get("id"):
                    portal.store.x("UPDATE filters SET pattern=?, kind=?, action=?, minutes=?, note=?, active=? WHERE id=?", vals + (int(d["id"]),))
                else:
                    portal.store.x("INSERT INTO filters(pattern,kind,action,minutes,note,active,created,by_name) VALUES(?,?,?,?,?,?,?,?)",
                                   vals + (now(), who["name"]))
                portal._filters = None
                portal.store.audit(who, "filter " + ("change" if d.get("id") else "add"), detail="%s %s -> %s" % (kind, vals[0], action))
                return self.json({"ok": True})
            if route == "filters/delete" and P:
                who = self.need(s, "filters.manage")
                fid = int(self.body_json().get("id") or 0)
                f = portal.store.one("SELECT * FROM filters WHERE id=?", (fid,))
                if not f:
                    raise ApiError(404, "No such filter.")
                portal.store.x("DELETE FROM filters WHERE id=?", (fid,))
                portal._filters = None
                portal.store.audit(who, "filter delete", detail="%s %s" % (f["kind"], f["pattern"]))
                return self.json({"ok": True})
            if route == "filters/test" and P:
                self.need(s, "view")
                text = str(self.body_json().get("text", ""))[:300]
                return self.json({"matches": [{"id": f["id"], "pattern": f["pattern"], "action": f["action"], "note": f["note"]}
                                              for f in portal.filter_hits(text)]})
            # watchlist
            if route == "watchlist" and G:
                self.need(s, "view")
                rows = portal.store.q("SELECT * FROM watchlist ORDER BY created DESC")
                online = {p.get("pid"): k for k, srv in portal.servers.items() for p in srv.view().get("players", []) if p.get("pid")}
                for r in rows:
                    r["online"] = online.get(r["pid"])
                return self.json({"watchlist": rows})
            if route == "watchlist" and P:
                who = self.need(s, "watch")
                d = self.body_json()
                pid = str(d.get("pid", ""))
                if not PID.match(pid):
                    raise ApiError(400, "Pick a player.")
                if d.get("remove"):
                    portal.store.x("DELETE FROM watchlist WHERE pid=?", (pid,))
                    portal.store.audit(who, "unwatch", target=pid, pid=pid)
                else:
                    name = safe_arg(d.get("name", ""), 40) or (portal.store.one(
                        "SELECT name FROM sightings WHERE pid=? ORDER BY last_seen DESC LIMIT 1", (pid,)) or {}).get("name", pid)
                    portal.store.x("INSERT INTO watchlist(pid,name,reason,created,by_name) VALUES(?,?,?,?,?) ON CONFLICT(pid) DO UPDATE SET "
                                   "reason=excluded.reason", (pid, name, safe_arg(d.get("reason", ""), 200), now(), who["name"]))
                    portal.store.audit(who, "watch", target=name, pid=pid, detail=safe_arg(d.get("reason", ""), 200))
                return self.json({"ok": True})
            # saved replies
            if route == "templates" and G:
                self.need(s, "view")
                return self.json({"templates": portal.store.q("SELECT * FROM templates ORDER BY kind, title")})
            if route == "templates" and P:
                who = self.need(s, "templates.manage")
                d = self.body_json()
                if d.get("delete"):
                    portal.store.x("DELETE FROM templates WHERE id=?", (int(d.get("id") or 0),))
                    portal.store.audit(who, "saved reply delete", detail="#%s" % d.get("id"))
                    return self.json({"ok": True})
                kind = d.get("kind")
                if kind not in ("warn", "kick", "mute", "ban", "chat", "appeal", "close"):
                    raise ApiError(400, "Pick where the reply is used.")
                title, text = safe_arg(d.get("title", ""), 40), str(d.get("text", "")).strip()[:500]
                if not title or not text:
                    raise ApiError(400, "Give the reply a name and a text.")
                if d.get("id"):
                    portal.store.x("UPDATE templates SET kind=?, title=?, text=? WHERE id=?", (kind, title, text, int(d["id"])))
                else:
                    portal.store.x("INSERT INTO templates(kind,title,text,created,by_name) VALUES(?,?,?,?,?)", (kind, title, text, now(), who["name"]))
                portal.store.audit(who, "saved reply", detail="%s: %s" % (kind, title))
                return self.json({"ok": True})
            # alerts and flags
            if route == "alerts" and G:
                self.need(s, "view")
                before = int(qs.get("before") or 0) or 2 ** 62
                return self.json({"alerts": portal.store.q("SELECT id,at,kind,title,text,pid,server,sent FROM alerts WHERE id<? ORDER BY id DESC LIMIT 100", (before,)),
                                  "webhook": bool(portal.webhook_url())})
            if route == "suspicion" and G:
                self.need(s, "view")
                rows = portal.store.q("SELECT * FROM suspicion WHERE updated>? AND score>0 ORDER BY score DESC LIMIT 50", (now() - 600,))
                for r in rows:
                    r["reasons"] = json.loads(r["reasons"] or "[]")
                return self.json({"players": rows, "threshold": int(cfg.get("suspicion_alert", 60))})
            # appeals (staff side; the player side is /appeal/*)
            if route == "appeals/answer" and P:
                who = self.need(s, "appeals.answer")
                d = self.body_json()
                return self.json(portal.appeal_answer(who, int(d.get("id") or 0), d.get("decision"), d.get("answer")))
            # scheduled actions
            if route == "schedule" and G:
                self.need(s, "view")
                return self.json({"jobs": portal.store.q("SELECT * FROM schedule WHERE active=1 ORDER BY next_at"),
                                  "done": portal.store.q("SELECT * FROM schedule WHERE active=0 ORDER BY COALESCE(last_run, created) DESC LIMIT 20")})
            if route == "schedule" and P:
                d = self.body_json()
                act = d.get("action")
                if act not in SCHEDULE_ACTIONS:
                    raise ApiError(400, "Pick what to do.")
                who = self.need(s, SCHEDULE_ACTIONS[act])
                server = str(d.get("server", ""))
                if server != "*" and server not in portal.servers or (server == "*" and act != "say"):
                    raise ApiError(400, "Pick a server.")
                at = int(d.get("at") or 0)
                every = int(d.get("every_min") or 0)
                until = int(d.get("until") or 0)
                if at < now() - 60 or at > now() + 60 * 86400:
                    raise ApiError(400, "Pick a time in the next 60 days.")
                if every and (every < 5 or every > 10080):
                    raise ApiError(400, "Repeat every 5 minutes to 7 days.")
                if until and until <= at:
                    raise ApiError(400, "The end must be after the first run.")
                arg = safe_arg(d.get("text", ""), 200) if act == "say" else str(d.get("map", "") or "")
                if act == "say" and not arg:
                    raise ApiError(400, "Write the message.")
                if act == "map" and not MAP_NAME.match(arg) or act == "nextmap" and arg and not MAP_NAME.match(arg):
                    raise ApiError(400, "Pick a map.")
                if portal.store.one("SELECT COUNT(*) n FROM schedule WHERE active=1")["n"] >= 100:
                    raise ApiError(409, "100 scheduled actions are waiting already. Cancel some first.")
                jid = portal.store.x("INSERT INTO schedule(server,action,arg,next_at,every_min,until,created,by_name,by_id) VALUES(?,?,?,?,?,?,?,?,?)",
                                     (server, act, arg, max(at, now()), every, until, now(), who["name"], who["discord_id"]))
                portal.store.audit(who, "schedule " + act, server=server, detail="%s at %s%s" % (
                    arg, iso(at), ", every %d min" % every if every else ""))
                return self.json({"ok": True, "id": jid})
            if route == "schedule/cancel" and P:
                who = self.need(s, "server.say")
                job = portal.store.one("SELECT * FROM schedule WHERE id=? AND active=1", (int(self.body_json().get("id") or 0),))
                if not job:
                    raise ApiError(404, "No such scheduled action.")
                self.need(s, SCHEDULE_ACTIONS.get(job["action"], "schedule"))
                portal.store.x("UPDATE schedule SET active=0, last_result='cancelled by ' || ? WHERE id=?", (who["name"], job["id"]))
                portal.store.audit(who, "schedule cancel", server=job["server"], detail="#%d %s %s" % (job["id"], job["action"], job["arg"]))
                return self.json({"ok": True})
            # event mode and the config editor
            if route == "event" and G:
                self.need(s, "view")
                rows = portal.store.q("SELECT server, started, by_name, preset, note FROM events")
                for r in rows:
                    r["preset"] = json.loads(r["preset"] or "{}")
                    r["password"] = r["preset"].get("g_password", "") if allowed(s, "event") else ""
                    if not allowed(s, "event"):
                        r["preset"].pop("g_password", None)
                return self.json({"events": rows})
            if route == "event" and P:
                who = self.need(s, "event")
                d = self.body_json()
                srv = portal.server(d.get("server"))
                if d.get("action") == "start":
                    return self.json(portal.event_start(who, srv, str(d.get("password") or ""), d.get("note", "")))
                if d.get("action") == "stop":
                    return self.json(portal.event_stop(who, srv))
                raise ApiError(400, "Start or stop.")
            if route == "cvars" and G:
                self.need(s, "cvars")
                return self.json(portal.cvars_view(portal.server(qs.get("server"))))
            if route == "cvars" and P:
                who = self.need(s, "cvars")
                d = self.body_json()
                return self.json(portal.cvar_set(who, portal.server(d.get("server")), str(d.get("cvar", "")), d.get("value"), bool(d.get("keep"))))
            if route == "cvars/rollback" and P:
                who = self.need(s, "cvars")
                return self.json(portal.cvar_rollback(who, int(self.body_json().get("id") or 0)))
            if route == "cvars/release" and P:
                who = self.need(s, "cvars")
                d = self.body_json()
                portal.store.x("DELETE FROM cvar_overrides WHERE server=? AND cvar=?", (str(d.get("server")), str(d.get("cvar"))))
                portal.store.audit(who, "setting release", server=str(d.get("server")), target=str(d.get("cvar")))
                return self.json({"ok": True})
            # live map
            if route == "positions" and G:
                who = self.need(s, "livemap")
                srv = portal.server(qs.get("server"))
                mine = {x["pid"] for x in portal.discord_links(discord_id=who["discord_id"]) or []} if who["discord_id"].isdigit() else set()
                if mine & {p.get("pid") for p in srv.view().get("players", []) if not p.get("spectator")}:
                    raise ApiError(403, "You are playing on this server. The live map stays closed until you leave or spectate.")
                mark = (s["id"], srv.key)
                if mark not in portal.map_views:
                    portal.map_views.add(mark)
                    portal.store.audit(who, "live map", server=srv.key, detail="opened the live map")
                return self.json(portal.positions(srv))
            # weekly report
            if route == "weekly" and G:
                self.need(s, "weekly")
                weeks = max(0, min(52, int(qs.get("weeks_ago") or 0)))
                w = portal.weekly(now() - weeks * 7 * 86400)
                return self.json(dict(w, text=portal.weekly_text(w)))
            # devlog comments (accounts service)
            if route == "comments/stats" and G:
                self.need(s, "comments")
                return self.json(portal.comments_api("GET", "stats"))
            if route == "comments" and G:
                self.need(s, "comments")
                tab = qs.get("tab", "needs") if qs.get("tab") in ("needs", "recent", "hidden", "paused") else "needs"
                return self.json(portal.comments_api("GET", "queue", qs={"tab": tab, "post": qs.get("post", "")[:80],
                                                                          "q": qs.get("q", "")[:40]}))
            if route == "comments/act" and P:
                self.need(s, "comments")
                d = self.body_json()
                action = str(d.get("action", ""))
                if action not in ("publish", "hide", "restore", "remove", "dismiss", "pin", "unpin"):
                    raise ApiError(400, "Unknown action.")
                out = portal.comments_api("POST", "act", {"id": d.get("id"), "action": action, "by": s["name"]})
                portal.comments_audit(s, action, out.get("comment"))
                return self.json(out)
            if route == "comments/pause" and P:
                self.need(s, "comments")
                d = self.body_json()
                out = portal.comments_api("POST", "pause", {"account": d.get("account"), "name": d.get("name"),
                                                            "days": d.get("days", 0), "reason": d.get("reason", ""), "by": s["name"]})
                portal.store.audit(s, "comment.pause", target=out.get("name", ""),
                                   detail="%s · %s" % ("for good" if out.get("until") == -1 else "%s days" % d.get("days"), d.get("reason", "")))
                return self.json(out)
            if route == "comments/unpause" and P:
                self.need(s, "comments")
                d = self.body_json()
                out = portal.comments_api("POST", "unpause", {"account": d.get("account"), "by": s["name"]})
                portal.store.audit(s, "comment.unpause", target=str(d.get("name", "")))
                return self.json(out)
            if route == "comments/close" and P:
                self.need(s, "comments.close")
                d = self.body_json()
                out = portal.comments_api("POST", "close", {"post": d.get("post"), "closed": d.get("closed") is not False, "by": s["name"]})
                portal.store.audit(s, "comment.close" if out.get("closed") else "comment.reopen", target=str(out.get("post", "")))
                return self.json(out)
            if route == "comments/reply" and P:
                self.need(s, "comments")
                d = self.body_json()
                out = portal.comments_api("POST", "reply", {"parent": d.get("parent"), "text": d.get("text", ""),
                                                            "discord": s["discord_id"], "by": s["name"]})
                portal.store.audit(s, "comment.reply", detail="on #%s: %s" % (d.get("parent"), str(d.get("text", ""))[:200]))
                return self.json(out)
            # website insights
            if route == "insights" and G:
                self.need(s, "insights")
                try:
                    days = int(qs.get("days") or 30)
                except ValueError:
                    days = 30
                return self.json(portal.insights(days if days in (7, 30, 90, 365) else 30))
            # stats review queue
            if route == "review" and G:
                self.need(s, "review")
                rows = portal.stats_staff("GET", "/staff/review.json").get("review", [])
                done = {r["key"]: r for r in portal.store.q("SELECT key, value FROM meta WHERE key LIKE 'review:%'")}
                for r in rows:
                    r["checked"] = (done.get("review:%s:%s:%s" % (r.get("pid"), r.get("match_id"), r.get("reason"))) or {}).get("value")
                return self.json({"review": rows})
            if route == "review" and P:
                who = self.need(s, "review")
                d = self.body_json()
                act, kind, ident = d.get("action"), d.get("kind"), str(d.get("id", ""))
                if kind not in ("match", "player") or not PID.match(ident):
                    raise ApiError(400, "Pick a player or a match.")
                if act == "checked":
                    portal.meta("review:%s:%s:%s" % (d.get("pid"), d.get("match_id"), d.get("reason")), "%s, %s" % (who["name"], iso()))
                    portal.store.audit(who, "stats checked", target=ident, pid=ident if kind == "player" else "", detail=str(d.get("reason", ""))[:200])
                    return self.json({"ok": True})
                if act not in ("void", "unvoid"):
                    raise ApiError(400, "Void or restore.")
                r = portal.stats_staff("POST", "/staff/" + act, {"kind": kind, "id": ident, "reason": safe_arg(d.get("reason", ""), 200)})
                portal.store.audit(who, "stats " + act, target=ident, pid=ident if kind == "player" else "", detail="%s %s" % (kind, d.get("reason", "")))
                return self.json(r)
            # server demos for reports
            if route == "demo" and G:
                self.need(s, "reports")
                d = portal.demo_for(int(qs.get("report") or 0))
                d.pop("path")
                return self.json(d)
            if route == "demo/file" and G:
                who = self.need(s, "reports")
                d = portal.demo_for(int(qs.get("report") or 0))
                portal.store.audit(who, "demo download", server=d["server"], detail="%s, from %ss" % (d["file"], d["offset_s"]))
                return self.send_file(Path(d["path"]), d["file"])
            # two-step sign-in
            # in-game staff badge keys
            if route == "staffkey" and G:
                who = self.need(s, "view")
                k = portal.store.one("SELECT id, created FROM staff_keys WHERE discord_id=? AND revoked=0 ORDER BY created DESC",
                                     (who["discord_id"],))
                sql, args = portal.staff_key_valid_sql()
                live = bool(k) and bool(portal.store.one("SELECT 1 x FROM (%s) WHERE id=?" % sql, args + [k["id"]]))
                return self.json({"key": k, "active": live, "servers": sum(1 for x in portal.servers.values() if portal.staff_keys_file(x)),
                                  "launcher": bool(cfg.get("launcher_key_install", False))})
            if route == "staffkey" and P:
                who = self.need(s, "view")
                d = self.body_json()
                pub = str(d.get("public", "")).lower()
                if not re.fullmatch(r"[0-9a-f]{64}", pub) or pub == "0" * 64:
                    raise ApiError(400, "That is not an Ed25519 public key.")
                if portal.limited("staffkey:" + who["discord_id"], 5, 86400):
                    raise ApiError(429, "You made five keys today. Try again tomorrow.")
                kid, problems = portal.create_staff_key(who["discord_id"], who["name"], pub)
                portal.store.audit(who, "staff key made", target=kid, detail="downloaded")
                return self.json({"id": kid, "problems": problems}, 201)
            if route == "staffkey/link" and P:
                # "Install in game": a one-time link the launcher claims; the launcher makes the key pair itself
                who = self.need(s, "view")
                if portal.limited("staffkey:" + who["discord_id"], 5, 86400, peek=True):
                    raise ApiError(429, "You made five keys today. Try again tomorrow.")
                code = secrets.token_hex(16)
                portal.store.x("DELETE FROM staff_key_codes WHERE discord_id=? OR expires<?", (who["discord_id"], now()))
                portal.store.x("INSERT INTO staff_key_codes(code_hash,discord_id,name,expires) VALUES(?,?,?,?)",
                               (hashlib.sha256(code.encode()).hexdigest(), who["discord_id"], who["name"], now() + STAFF_KEY_LINK_SECONDS))
                return self.json({"link": "truecombat://staffkey/" + code, "expires": now() + STAFF_KEY_LINK_SECONDS})
            if route == "staffkeys" and G:
                self.need(s, "staff.manage")
                sql, args = portal.staff_key_valid_sql()
                live = {r["id"] for r in portal.store.q(sql, args)}
                rows = portal.store.q("SELECT id, discord_id, name, created FROM staff_keys WHERE revoked=0 ORDER BY created DESC")
                portal.staff_cert("")                       # loads the root once
                root = getattr(portal, "_staff_root", None)
                return self.json({"keys": [dict(r, active=r["id"] in live) for r in rows],
                                  "idle_days": int(cfg.get("staff_key_idle_days", 60)),
                                  "cert_root": root[0] if root else None, "cert_days": int(cfg.get("staff_cert_days", 30))})
            if route == "staffkey/revoke" and P:
                who = self.need(s, "view")
                d = self.body_json()
                k = portal.store.one("SELECT * FROM staff_keys WHERE id=? AND revoked=0", (str(d.get("id", "")),))
                if not k:
                    raise ApiError(404, "No such key.")
                if k["discord_id"] != who["discord_id"]:
                    self.need(s, "staff.manage")
                portal.store.x("UPDATE staff_keys SET revoked=?, revoked_by=? WHERE id=?", (now(), who["name"], k["id"]))
                portal.publish_staff_keys()
                portal.store.audit(who, "staff key revoked", target=k["id"], detail=k["name"])
                return self.json({"ok": True})
            if route == "2fa" and G:
                if not s:
                    raise ApiError(401, "Please sign in.")
                return self.json({"enabled": self.totp_on(s), "pending": self.mfa_pending(s),
                                  "required": bool(cfg.get("require_2fa", True)) and RANK.get(s["role"], 0) >= RANK["admin"]})
            if route == "2fa/setup" and P:
                who = self.need(s, "view")
                if self.totp_on(who):
                    raise ApiError(409, "Two-step sign-in is already on.")
                secret_b32 = totp_secret()
                portal.store.x("INSERT INTO totp(discord_id,secret,enabled,created,last_step) VALUES(?,?,0,?,0) ON CONFLICT(discord_id) "
                               "DO UPDATE SET secret=excluded.secret, enabled=0, created=excluded.created, last_step=0",
                               (who["discord_id"], secret_b32, now()))
                label = urllib.parse.quote("TrueCombat Staff:%s" % who["name"])
                uri = "otpauth://totp/%s?secret=%s&issuer=%s&digits=6&period=30" % (
                    label, secret_b32, urllib.parse.quote("TrueCombat Staff"))
                return self.json({"secret": secret_b32, "uri": uri, "qr": qr_svg_data_uri(uri)})
            if route in ("2fa/enable", "2fa/verify", "2fa/disable") and P:
                if not s:
                    raise ApiError(401, "Please sign in.")
                if portal.limited("2fa:" + s["discord_id"], 5, 300):
                    raise ApiError(429, "Too many tries. Wait five minutes.")
                if route == "2fa/disable" and bool(cfg.get("require_2fa", True)) and RANK.get(s["role"], 0) >= RANK["admin"]:
                    raise ApiError(409, "Admins and owners must keep two-step sign-in on.")
                row = portal.store.one("SELECT * FROM totp WHERE discord_id=?", (s["discord_id"],))
                if not row or (route == "2fa/enable") == bool(row["enabled"]):
                    raise ApiError(409, "Start the setup first." if route == "2fa/enable" else "Two-step sign-in is not on.")
                step = totp_match(row["secret"], self.body_json().get("code"), row["last_step"])
                if not step:
                    portal.store.audit(s, "2fa failed", detail=self.client_ip(), ok=False)
                    if portal.limited("2fa-day:" + s["discord_id"], 20, 86400):
                        # 5 tries per 5 minutes still adds up over days: 20 misses in a day signs the account out everywhere
                        portal.store.x("DELETE FROM sessions WHERE discord_id=?", (s["discord_id"],))
                        portal.alert("mod_ban", "Two-step sign-in locked for %s" % s["name"],
                                     "20 wrong codes in a day from %s. All of this account's sessions were ended." % self.client_ip(),
                                     key="2fa-lock:" + s["discord_id"], window=3600, urgent=True)
                        raise ApiError(401, "Too many wrong codes. You have been signed out everywhere; an alert went to staff.")
                    raise ApiError(400, "That code is not right. Check the time on your phone and try the next code.")
                if route == "2fa/disable":
                    portal.store.x("DELETE FROM totp WHERE discord_id=?", (s["discord_id"],))
                    portal.store.audit(s, "2fa off")
                    return self.json({"ok": True})
                portal.store.x("UPDATE totp SET enabled=1, last_step=? WHERE discord_id=?", (step, s["discord_id"]))
                portal.store.x("UPDATE sessions SET mfa=1 WHERE id=?", (s["id"],))
                portal.store.audit(s, "2fa on" if route == "2fa/enable" else "2fa ok", detail=self.client_ip())
                return self.json({"ok": True})
            if route == "2fa/reset" and P:
                who = self.need(s, "2fa.reset")
                did = str(self.body_json().get("discord_id", ""))
                portal.store.x("DELETE FROM totp WHERE discord_id=?", (did,))
                portal.store.x("DELETE FROM sessions WHERE discord_id=?", (did,))
                portal.store.audit(who, "2fa reset", target=did)
                return self.json({"ok": True})
            raise ApiError(404, "Not found.")

        # -- staff commands from our Discord bot (1.4.3): loopback only, a shared token, and the Discord user's own staff
        # rights. No two-step sign-in on Discord, so admin-level tools stay in the portal.
        def bot_actor(self) -> dict:
            token = secret(cfg, "bot-api-token")
            if not token:
                raise ApiError(404, "Not found.")
            if self.client_address[0] not in ("127.0.0.1", "::1") or self.headers.get("X-Forwarded-For"):
                raise ApiError(404, "Not found.")
            if not hmac.compare_digest(self.headers.get("X-Bot-Token", ""), token):
                raise ApiError(401, "Bad bot token.")
            did = self.headers.get("X-Discord-Id", "")
            if not re.fullmatch(r"\d{15,21}", did):
                raise ApiError(400, "Missing Discord user.")
            roles = [r for r in (self.headers.get("X-Discord-Roles") or "").split(",") if r.strip().isdigit()]
            role = resolve_role(portal, did, roles)
            if not role:
                raise ApiError(403, "You are not on the staff team.")
            name = plain(urllib.parse.unquote(self.headers.get("X-Discord-Name", "")))[:40] or "Discord staff"
            perms = portal.effective_perms(did, role) or [p for p in PERMS if allowed(role, p)]
            perms = [p for p in perms if RANK[PERMS[p]] < RANK["admin"]]
            return {"discord_id": did, "name": name, "role": role, "perms": perms, "via": "discord"}

        def bot_api(self, method: str, route: str, qs: dict) -> None:
            who = self.bot_actor()
            if portal.limited("bot:" + who["discord_id"], 60, 60):
                raise ApiError(429, "Slow down a little.")
            G, P = method == "GET", method == "POST"
            if route == "me" and G:
                return self.json({"name": who["name"], "role": who["role"], "perms": who["perms"]})
            if route == "summary" and G:
                self.need(who, "view")
                d = portal.dashboard(who)
                return self.json({k: d.get(k) for k in ("players_online", "servers_up", "servers", "reports", "cases", "on_duty",
                                                         "appeals_open", "bans_24h", "urgent_24h")})
            if route == "online" and G:
                self.need(who, "view")
                return self.json({"servers": [{"key": x["key"], "name": x["name"], "online": x["online"],
                                               "players": [{"slot": p["slot"], "name": p["name"], "pid": p.get("pid", "")}
                                                           for p in x.get("players", []) if not p["bot"]]}
                                              for x in portal.servers_view(False)]})
            if route == "reports" and G:
                self.need(who, "reports")
                rows = portal.store.q("SELECT * FROM reports WHERE status IN ('open','claimed') AND source IN ('player','auto','appeal') "
                                      "ORDER BY status='claimed', id DESC LIMIT 15")
                out = []
                for r in rows:
                    dd = portal._report_row(r).get("data") or {}
                    out.append({"id": r["id"], "source": r["source"], "status": r["status"], "server": r["server"],
                                "target": r["target_name"], "pid": r["target_pid"], "claimed_by": r["claimed_by"], "received": r["received"],
                                "reason": str(dd.get("reason") or dd.get("text") or "")[:200]})
                return self.json({"reports": out})
            if route == "report" and P:
                self.need(who, "reports")
                d = self.body_json()
                r = portal.store.one("SELECT * FROM reports WHERE id=?", (int(d.get("id") or 0),))
                if not r:
                    raise ApiError(404, "No such report.")
                status = {"take": "claimed", "close": "closed", "reopen": "open"}.get(d.get("action"))
                if not status:
                    raise ApiError(400, "Unknown action.")
                if r["source"] == "appeal" and status != "claimed":
                    raise ApiError(409, "Appeals are answered in the portal.")
                res = str(d.get("resolution") or "").strip()[:500]
                if status == "closed" and not res:
                    raise ApiError(400, "Say what was done.")
                portal.store.x("UPDATE reports SET status=?, claimed_by=?, resolution=?, updated=? WHERE id=?",
                               (status, who["name"] if status != "open" else None, res or r["resolution"], now(), r["id"]))
                portal.store.audit(who, "report " + status, server=r["server"], target=r["target_name"], pid=r["target_pid"],
                                   detail=("#%d %s (Discord)" % (r["id"], res)).strip())
                portal.bus.emit("reports")
                return self.json({"ok": True, "status": status})
            if route == "lookup" and G:
                self.need(who, "lookup")
                rows = portal.lookup(qs.get("q", ""), False)[:5]
                return self.json({"players": [{"pid": x["pid"], "names": x["names"][:4], "last_seen": x.get("last_seen"),
                                               "banned": x.get("banned")} for x in rows]})
            if route == "action" and P:
                d = self.body_json()
                if d.get("action") == "ban":
                    return self.ban(who, d)
                if d.get("action") not in ("warn", "mute", "kick"):
                    raise ApiError(400, "Use warn, mute, kick or ban.")
                return self.player_action(who, d)
            if route == "duty" and P:
                self.need(who, "duty")
                d = self.body_json()
                return self.json(portal.duty_set(who, bool(d.get("on")), d.get("hours") or 4))
            raise ApiError(404, "Not found.")

        def stream(self, who: dict) -> None:
            """Server-sent events: what changed, so open pages refresh at once instead of waiting for their next poll."""
            key = who["discord_id"] or who["name"]
            if not portal.bus.open(key, int(cfg.get("stream_per_person", 4)), int(cfg.get("stream_max", 60))):
                raise ApiError(429, "Too many open live connections.")
            try:
                self.close_connection = True
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.send_header("X-Accel-Buffering", "no")
                for k, v in SECURITY_HEADERS.items():
                    self.send_header(k, v)
                self.end_headers()
                try:
                    last = int(self.headers.get("Last-Event-ID") or 0)
                except ValueError:
                    last = 0
                last = last or portal.bus.seq
                self.wfile.write(b"retry: 4000\n: live\n\n")
                self.wfile.flush()
                ends = time.time() + int(cfg.get("stream_seconds", 1800))
                checked = time.time()
                while time.time() < ends and not portal.stop.is_set():
                    items = portal.bus.since(last, float(cfg.get("stream_keepalive", 20)))
                    out = []
                    for seq, kind, data in items:
                        last = seq
                        out.append("id: %d\nevent: %s\ndata: %s\n\n" % (seq, kind, json.dumps(data, separators=(",", ":"))))
                    if not out:
                        out.append(": keepalive\n\n")
                    self.wfile.write("".join(out).encode())
                    self.wfile.flush()
                    if time.time() - checked > 60:              # a signed-out or demoted session stops here
                        checked = time.time()
                        if not self.session():
                            break
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                portal.bus.close(key)

        def send_file(self, path: Path, name: str, ctype: str = "", cache: str = "no-store") -> None:
            try:
                f = path.open("rb")
            except OSError as e:
                raise ApiError(404, "The file could not be read.") from e
            with f:
                size = os.fstat(f.fileno()).st_size
                self.send_response(200)
                self.send_header("Content-Type", ctype or "application/octet-stream")
                self.send_header("Content-Length", str(size))
                self.send_header("Content-Disposition", '%s; filename="%s"' % ("inline" if ctype else "attachment",
                                                                               re.sub(r'[^A-Za-z0-9_.-]', "_", name)))
                self.send_header("Cache-Control", cache)
                for k, v in SECURITY_HEADERS.items():
                    self.send_header(k, v)
                self.end_headers()
                if self.command != "HEAD":
                    shutil.copyfileobj(f, self.wfile, 256 * 1024)

        # -- public ban appeals: the only pages a player can reach
        def appeal(self, method: str, path: str, qs: dict) -> None:
            ip = self.client_ip()
            sender = portal.ip_tag(ip)
            if path == "/appeal/status" and method == "GET":
                if portal.limited("appeal-status:" + ip, 30, 3600):
                    raise ApiError(429, "Too many lookups. Try again later.")
                return self.json(portal.appeal_status(qs.get("code", "")))
            if path == "/appeal/submit" and method == "POST":
                origin = self.headers.get("Origin")
                if origin and origin.rstrip("/") != public:
                    raise ApiError(403, "Wrong origin.")
                if portal.limited("appeal:" + ip, 6, 3600) or portal.limited("appeal:*", 100, 86400):
                    raise ApiError(429, "Too many appeals from this connection. Try again later.")
                d = self.body_json()
                return self.json(portal.appeal_submit(d.get("code"), d.get("text"), d.get("contact", ""), sender), 201)
            raise ApiError(404, "Not found.")

        # -- player actions
        def target(self, d: dict) -> tuple:
            srv = portal.server(d.get("server"))
            try:
                slot = int(d.get("slot"))
            except (TypeError, ValueError) as e:
                raise ApiError(400, "Pick a player.") from e
            p = srv.slot_player(slot)
            if not p:
                raise ApiError(409, "That player is no longer on the server.")
            if d.get("name") and plain(d["name"]) != p["name"]:
                raise ApiError(409, "That slot now belongs to someone else. Refresh and try again.")
            return srv, slot, p

        def player_action(self, s: dict | None, d: dict) -> None:
            act = d.get("action")
            perm = {"kick": "player.kick", "warn": "player.warn", "mute": "player.mute", "unmute": "player.mute",
                    "move": "player.move"}.get(act)
            if not perm:
                raise ApiError(400, "Unknown action.")
            who = self.need(s, perm)
            if portal.limited("act:" + who["discord_id"], 40, 60):
                raise ApiError(429, "Slow down a little.")
            srv, slot, p = self.target(d)
            result, aid = portal.act(who, srv, slot, p, act, reason=d.get("reason", ""), length=d.get("length") or "",
                                     team=d.get("team") or "")
            self.json({"ok": True, "result": result, "undo": aid if act == "mute" else None})

        def ban(self, s: dict | None, d: dict) -> None:
            minutes = duration_minutes(d.get("length", ""))
            who = self.need(s, "ban.temp")          # ban_player refuses moderators past MOD_BAN_LIMIT
            srv = slot = None
            if d.get("server") is not None and d.get("slot") is not None:
                srv, slot, p = self.target(d)
                if p["bot"]:
                    raise ApiError(400, "That is a bot.")
                target = p
            elif d.get("report"):
                target = portal.report_target(int(d.get("report") or 0))
            else:
                target = portal.ban_target(str(d.get("pid", "")))
            game = bool(d.get("game"))
            r = portal.ban_player(who, target, minutes, d.get("reason", ""), ip_ban=bool(d.get("ip_ban", True)), srv=srv, slot=slot,
                                  game=game, via=" (from bug report #%d)" % int(d["report"]) if d.get("report") else "")
            self.json({"ok": True, "id": r["id"], "servers": r["servers"], "undo": r["audit_id"], "appeal_code": r["appeal_code"],
                       "game": game, "identities": r["identities"]})

        def unban(self, s: dict | None, d: dict) -> None:
            who = self.need(s, "ban.remove")
            b = portal.store.one("SELECT * FROM bans WHERE id=? AND active=1", (int(d.get("id") or 0),))
            if not b:
                raise ApiError(404, "No active ban with that number.")
            self.json({"ok": True, "servers": portal.lift_ban(who, b, d.get("reason", ""))})

        def server_action(self, s: dict | None, d: dict) -> None:
            act = d.get("action")
            perm = {"say": "server.say", "chat": "chat.reply", "map": "server.map", "nextmap": "server.map",
                    "restart": "server.restart", "rotation": "server.map"}.get(act)
            if not perm:
                raise ApiError(400, "Unknown action.")
            who = self.need(s, perm)
            if portal.limited("srv:" + who["discord_id"], 30, 60):
                raise ApiError(429, "Slow down a little.")
            keys = portal.order if d.get("server") == "*" and act in ("say", "chat") else [portal.server(d.get("server")).key]
            res = portal.server_command(who, act, keys, text=d.get("text", ""), m=str(d.get("map", "") or ""), maps=str(d.get("maps", "")))
            self.json({"ok": True, "servers": res})

        def staff_change(self, s: dict | None, d: dict) -> None:
            who = self.need(s, "staff.manage")
            did = str(d.get("discord_id", "")).strip()
            role = d.get("role")
            if not re.fullmatch(r"\d{15,21}", did):
                raise ApiError(400, "Use the Discord user id (Developer Mode, right-click the user, Copy User ID).")
            if role not in ("trial", "moderator", "admin", "revoked", "discord"):
                raise ApiError(400, "Unknown role.")
            if did in {str(x) for x in cfg.get("owners", [])}:
                raise ApiError(403, "Owners are set in the portal configuration.")
            if role == "admin" and who["role"] != "owner":
                raise ApiError(403, "Only the owner can make admins.")
            current = portal.store.one("SELECT role FROM staff WHERE discord_id=?", (did,))
            live = portal.store.one("SELECT 1 x FROM sessions WHERE discord_id=? AND role IN ('admin','owner')", (did,))
            if ((current and current["role"] == "admin") or live) and who["role"] != "owner":
                raise ApiError(403, "Only the owner can change an admin.")
            stored = None if role == "discord" else role
            portal.store.x("INSERT INTO staff(discord_id,name,role,note,added_by,created) VALUES(?,?,?,?,?,?) "
                           "ON CONFLICT(discord_id) DO UPDATE SET role=excluded.role, note=excluded.note, added_by=excluded.added_by",
                           (did, safe_arg(d.get("name", ""), 40), stored, safe_arg(d.get("note", ""), 120), who["name"], now()))
            if role == "revoked":
                portal.store.x("DELETE FROM sessions WHERE discord_id=?", (did,))
                portal.revoke_staff_keys(did, "access removed by " + who["name"])
            else:
                portal.store.x("UPDATE sessions SET checked=0 WHERE discord_id=?", (did,))
            portal.store.audit(who, "staff " + role, target=did, detail=safe_arg(d.get("note", ""), 120))
            self.json({"ok": True})

        def restart(self, s: dict | None, d: dict) -> None:
            who = self.need(s, "health.restart")
            srv = portal.server(d.get("server"))
            unit = srv.cfg.get("unit")
            if not unit or not re.fullmatch(r"[A-Za-z0-9@_.-]+\.service|[A-Za-z0-9@_.-]+", unit):
                raise ApiError(409, "This server has no service to restart.")
            humans = srv.view().get("humans", 0)
            if humans and not d.get("confirm_players"):
                raise ApiError(409, "%d players are on this server. Confirm to restart anyway." % humans)
            if portal.limited("restart:" + srv.key, 2, 600):
                raise ApiError(429, "This server was restarted twice in the last 10 minutes. Check the logs first.")
            steps = []
            for cmd in cfg.get("restart_prefix", []):
                steps.append(subprocess.run(cmd, capture_output=True, text=True, timeout=30))
            # allowed for this service's user by a polkit rule that names exactly these units (deploy/install.sh)
            p = subprocess.run(["systemctl", "restart", "--no-ask-password", unit], capture_output=True, text=True, timeout=90)
            for cmd in cfg.get("restart_suffix", []):
                steps.append(subprocess.run(cmd, capture_output=True, text=True, timeout=30))
            ok = p.returncode == 0
            portal.store.audit(who, "service restart", server=srv.key, target=unit, detail="%d players on" % humans,
                               ok=ok, result=(p.stderr or p.stdout).strip()[:300])
            portal.health_cache = (0, None)
            if not ok:
                raise ApiError(500, "The restart failed: %s" % (p.stderr or p.stdout).strip()[:200])
            self.json({"ok": True})

    return Handler


# ----------------------------------------------------------------------------- main

def load_config(path: str) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    keys = [s.get("key") for s in cfg.get("servers", [])]
    if len(keys) != len(set(keys)) or not all(keys):
        raise SystemExit("every server needs a unique key")
    return cfg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--listen", help="host:port (default from the config, 127.0.0.1:8097)")
    ap.add_argument("--make-staff-root", metavar="ROOT_ID", help="write a new staff certificate root to the --root-out file "
                    "(0600) and print its PUBLIC key for tcp_staff_roots.h, then exit")
    ap.add_argument("--root-out", metavar="FILE", help="with --make-staff-root: where the root line goes (must not exist)")
    ap.add_argument("--reset-2fa", metavar="DISCORD_ID", help="turn off two-step sign-in for one account (lost phone) and exit")
    a = ap.parse_args(argv)
    if a.make_staff_root:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,15}", a.make_staff_root) or not a.root_out:
            print("usage: --make-staff-root r1 --root-out /etc/tcp-staff-portal/staff-root", file=sys.stderr)
            return 2
        out = Path(a.root_out)
        seed = secrets.token_bytes(32)
        fd = os.open(str(out), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as fh:
            fh.write("TCPSTAFFROOT1 %s %s\n" % (a.make_staff_root, seed.hex()))
        pub = ed25519_public(seed)
        print("root %s public key (paste into game_src/native/tcp_staff_roots.h):" % a.make_staff_root)
        print("    {\"%s\",{%s}}," % (a.make_staff_root, ",".join("0x%02x" % b for b in pub)))
        return 0
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config(a.config)
    if a.reset_2fa:
        store = Store(str(Path(cfg.get("data_dir", "/var/lib/tcp-staff-portal")) / "portal.db"))
        store.x("DELETE FROM totp WHERE discord_id=?", (a.reset_2fa,))
        store.x("DELETE FROM sessions WHERE discord_id=?", (a.reset_2fa,))
        store.audit({"name": "console", "role": "system"}, "2fa reset", target=a.reset_2fa, detail="from the command line")
        print("two-step sign-in reset for %s; they set it up again at the next sign-in" % a.reset_2fa)
        return 0
    if cfg.get("dev_login") and str(cfg.get("public_url", "")).startswith("https://"):
        raise SystemExit("dev_login is for local tests only; remove it from a public portal's config")
    host, _, port = (a.listen or "%s:%s" % (cfg.get("host", "127.0.0.1"), cfg.get("port", 8097))).rpartition(":")
    portal = Portal(cfg)
    portal.start()
    ThreadingHTTPServer.request_queue_size = 128   # the default 5 overflows under a burst behind Caddy
    httpd = ThreadingHTTPServer((host, int(port)), make_handler(portal))
    httpd.daemon_threads = True
    log.info("staff portal %s on http://%s:%s (%d servers)", VERSION, host, port, len(portal.servers))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        portal.stop.set()
    return 0


if __name__ == "__main__":
    sys.exit(main())
