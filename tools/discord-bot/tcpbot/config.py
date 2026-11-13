"""Configuration: one JSON file plus the bot token, which is never stored in it.

The token is read from the systemd credential ``token`` (LoadCredential=), or
from the file named by TCPBOT_TOKEN_FILE when running by hand. It is never
accepted on the command line, so it can't end up in shell history or logs.
"""

from __future__ import annotations

import copy
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = "/etc/tcp-discord-bot/config.json"

DEFAULTS: dict = {
    "guild_id": 0,
    "site_url": "https://truecombat.eu",
    "api_url": "http://127.0.0.1:8090",
    "discord_invite": "https://discord.gg/8kcHdg2Hch",
    "timezone": "Europe/Brussels",
    "state_db": "/var/lib/tcp-discord-bot/bot.db",
    "avatar": "/opt/tcp/discord-bot/assets/avatar.png",
    "presence": "truecombat.eu",
    "staff_role_ids": [],
    "channels": {
        # Live server cards. Separate channels per server are fine too, see "servers".
        "status": 0,
        # New #1 on the board, match on now
        "feed": 0,
        # Release announcements
        "announcements": 0,
        # New devlog articles (defaults to announcements)
        "devlog": 0,
        # Welcome message for new members
        "welcome": 0,
        # Release drafts waiting for approval and other staff notices (private)
        "staff": 0,
        # Events and playtests (defaults to announcements)
        "events": 0,
        # Player reports from the game (private; defaults to staff)
        "reports": 0,
        # Match reports, milestones, weekly recap and season results (defaults to feed)
        "matches": 0,
        # Team challenges, scrims and tournaments (defaults to events)
        "teams": 0,
        # Bug reports for the team to work through (private; defaults to staff)
        "bugs": 0,
        # Suggestions the community votes on (public; /suggest is off without it)
        "suggestions": 0,
        # Map votes (defaults to announcements)
        "votes": 0,
        # Questions passed on to staff with "Ask staff", and ban appeals (private; defaults to staff)
        "support": 0,
        # One live list of players looking for a squad (from player accounts); empty = off
        "lfs": 0,
    },
    "servers": [
        {
            "key": "official1",
            "name": "TrueCombat: Platinum | Official #1 Ranked (EU)",
            "host": "127.0.0.1",
            "port": 27960,
            "public_address": "2.24.59.195:27960",
            "match_type": "Ranked",
            "channel": 0,
            "match_alerts": True,
            # rcon for /admin: systemd credential name (LoadCredential=rcon-official1:...)
            "rcon_credential": "",
        },
    ],
    "bot_name_pattern": "^TCPStress",
    "status": {
        "interval_seconds": 60,
        "refresh_minutes": 5,
        "offline_after": 2,
        "top_players": 3,
        "show_community": True,
    },
    "leader": {"enabled": True, "confirm_checks": 2},
    "match_alerts": {"enabled": True, "min_players": 4, "cooldown_minutes": 180},
    "releases": {
        "enabled": True,
        "repo": "Annoximeme/TrueCombat-Platinum",
        "interval_minutes": 10,
        # "draft": new releases wait in the staff channel for a Publish click.
        # "auto": they are announced straight away (the release itself is the approval).
        "mode": "draft",
        "ping_role_id": 0,   # 0 = the "Patch notes" opt-in role from /setup roles
    },
    # Image cards for /profile, /top and match reports (drawn with Pillow, map art from the site copy)
    "cards": {"enabled": True},
    "devlog": {
        "enabled": True,
        "feed": "/var/www/truecombat/devlog.xml",
        "site_root": "/var/www/truecombat",
        "interval_minutes": 10,
        # Role pinged with every new post. 0 = the "Devlog" opt-in role from /setup roles.
        "ping_role_id": 0,
    },
    "linking": {
        "enabled": True,
        # Folders where game servers drop link requests (<game home>/<fs_game>/links)
        "dirs": ["/var/lib/tcpgame/home/tcetest/links"],
        "code_minutes": 15,
    },
    "reports": {
        "enabled": True,
        # Folders where game servers write /report files (<game home>/<fs_game>/reports)
        "dirs": ["/var/lib/tcpgame/home/tcetest/reports"],
        # Server demos sit next to reports (../svdemos); their names use the server's local time
        "demo_timezone": "UTC",
    },
    "pickup": {
        # Off until the match servers exist (online-play thread: ports 27963-27964, rcon on 127.0.0.1)
        "enabled": False,
        "channel": 0,
        "team_size": 3,
        "mode_name": "Team Elimination",
        "accept_seconds": 60,
        "queue_minutes": 60,
        "join_minutes": 15,
        "max_minutes": 100,
        "map_load_seconds": 8,
        "require_link": False,
        # name the match servers report under in the stats service, to find the result
        "stats_server": "",
        # Website page that hands the join link to the launcher (truecombat://join/...), once launcher 1.5.0 ships:
        # "https://truecombat.eu/join.html". Empty = console instructions only.
        "join_url": "",
        "maps": ["obj_delta", "obj_northport", "obj_railhouse", "obj_snow", "obj_stadtrand", "obj_village"],
        # [{"key": "match1", "host": "127.0.0.1", "port": 27963, "public_address": "2.24.59.195:27963",
        #   "rcon_credential": "rcon-match1",   (stored with install.sh --rcon-from-cfg)
        #   "stats_name": "TrueCombat: Platinum | Pickup #1"}]
        "servers": [],
    },
    "roles": {
        "sync_minutes": 10,
        "rank_tiers": True,
        "top10": True,
        "verified": True,
        # Clean record and Trusted player roles from player accounts
        "badges": True,
    },
    # Player accounts (truecombat.eu/account). The token is the service's internal token, stored as the
    # systemd credential named here (install.sh --secret-stdin accounts-token). Without it all of this is off.
    "accounts": {
        "url": "http://127.0.0.1:8095",
        "token_credential": "accounts-token",
        # The opt-in weekly report by DM: weekday 0 = Monday, hour in the bot's timezone
        "weekly": {"enabled": True, "weekday": 0, "hour": 19},
        "lfs_refresh_minutes": 2,
    },
    "welcome": {"enabled": True, "dm": False},
    # A report card after every finished match on the listed stats servers (empty = every server)
    "match_reports": {"enabled": True, "min_players": 4, "servers": []},
    # Weekly recap: weekday 0 = Monday, hour in the bot's timezone
    "recap": {"enabled": True, "weekday": 0, "hour": 18, "min_matches": 3},
    # Seasons follow the calendar: "month" or "quarter". The winner gets the Season champion role.
    "seasons": {"enabled": True, "length": "month", "top": 10, "champion_role": True},
    "achievements": {"enabled": True},
    # Personal alerts by DM
    "alerts": {"enabled": True, "max_follows": 10, "player_cooldown_minutes": 120, "map_cooldown_minutes": 180,
               "map_min_players": 2, "rank_cooldown_minutes": 360},
    # Teams, scrims and tournaments. Scrims and tournament matches use the pickup match servers.
    "teams": {"enabled": True, "max_members": 8, "create_requires_link": False, "challenge_minutes": 30},
    # Bug reports can also be filed as GitHub issues: "owner/repo" plus a token stored as a systemd
    # credential (install.sh --secret-stdin github-token). Leave empty to keep them in Discord only.
    "feedback": {"github_repo": "", "github_credential": "github-token", "bug_cooldown_minutes": 5},
    # Map votes: weekday 4 = Friday. apply "notice" tells staff the result; "rcon" also sets the
    # rotation on the listed servers (keys from "servers") with rotation_command.
    "map_votes": {"enabled": False, "weekday": 4, "hour": 18, "hours_open": 48, "votes_per_member": 3, "winners": 4,
                  "maps": ["obj_delta", "obj_northport", "obj_railhouse", "obj_snow", "obj_stadtrand", "obj_village"],
                  "apply": "notice", "servers": [], "rotation_command": 'set sv_mapRotation "{maps}"'},
    # Game chat in a Discord channel. Each entry: {"key": "official1", "channel": 0, "log": "/path/to/console.log"}
    # or {"key": ..., "unit": "tcp-official1"} to follow the service's journal. relay_to_game: "off", "staff" or "linked".
    "chat_bridge": {"enabled": False, "servers": [], "relay_to_game": "staff", "relay_cooldown_seconds": 30,
                    "patterns": [r"^say: (?P<name>.+?): (?P<text>.*)$",
                                 r"TCP_NATIVE_SAY slot=(?P<slot>\d+) team=(?P<team>\d+) (?:text=)?(?P<text>.*)$"]},
    # Raid watch: this many joins inside the window alerts staff. Appeals are for game bans.
    "moderation": {"raid_joins": 8, "raid_seconds": 60, "new_account_days": 3, "raid_minutes": 30,
                   "appeal_cooldown_days": 14},
    "support": {"enabled": True},
    "events": {"reminder_minutes": 15, "create_discord_event": True},
}


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


class ConfigError(Exception):
    pass


@dataclass
class Config:
    raw: dict
    path: str = ""
    problems: list[str] = field(default_factory=list)

    def __getitem__(self, key):
        return self.raw[key]

    def get(self, key, default=None):
        return self.raw.get(key, default)

    @property
    def site(self) -> str:
        return self.raw["site_url"].rstrip("/")

    def channel(self, name: str, fallback: str | None = None) -> int:
        cid = int(self.raw["channels"].get(name) or 0)
        if not cid and fallback:
            cid = int(self.raw["channels"].get(fallback) or 0)
        return cid

    def server(self, key: str) -> dict | None:
        return next((s for s in self.raw["servers"] if s["key"] == key), None)


def load(path: str | None = None) -> Config:
    path = path or os.environ.get("TCPBOT_CONFIG") or DEFAULT_CONFIG_PATH
    try:
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
    except FileNotFoundError as e:
        raise ConfigError("config file not found: %s" % path) from e
    except ValueError as e:
        raise ConfigError("config file is not valid JSON: %s (%s)" % (path, e)) from e
    raw = _merge(DEFAULTS, user)
    # servers is a list: user entries replace the default list, each merged onto the default entry
    base_server = DEFAULTS["servers"][0]
    raw["servers"] = [_merge(base_server, s) for s in user.get("servers", DEFAULTS["servers"])]
    cfg = Config(raw=raw, path=path)
    cfg.problems = validate(raw)
    return cfg


def validate(raw: dict) -> list[str]:
    problems = []
    if not int(raw.get("guild_id") or 0):
        problems.append("guild_id is not set: slash commands need the server (guild) id")
    keys = [s.get("key") for s in raw["servers"]]
    if len(keys) != len(set(keys)):
        problems.append("servers: every entry needs a unique key")
    for s in raw["servers"]:
        if not (s.get("channel") or raw["channels"].get("status")):
            problems.append("servers[%s]: no channel and no channels.status" % s.get("key"))
    pk = raw["pickup"]
    if pk["enabled"]:
        if not int(pk.get("channel") or 0):
            problems.append("pickup.channel is not set")
        if not pk["servers"]:
            problems.append("pickup.servers is empty: the queue needs at least one match server")
        if not 1 <= int(pk["team_size"]) <= 8:
            problems.append("pickup.team_size must be 1-8")
        for s in pk["servers"]:
            missing = [k for k in ("key", "host", "port", "public_address") if not s.get(k)]
            if not (s.get("rcon_credential") or s.get("rcon_file") or s.get("rcon_password_file")):
                missing.append("rcon_credential")
            if missing:
                problems.append("pickup.servers[%s]: missing %s" % (s.get("key"), ", ".join(missing)))
            elif s["host"] not in ("127.0.0.1", "localhost", "::1"):
                problems.append("pickup.servers[%s]: rcon is only allowed to servers on this machine" % s["key"])
    if raw["seasons"]["length"] not in ("month", "quarter"):
        problems.append('seasons.length must be "month" or "quarter"')
    mv = raw["map_votes"]
    if mv["apply"] not in ("notice", "rcon"):
        problems.append('map_votes.apply must be "notice" or "rcon"')
    if mv["enabled"] and not 2 <= len(mv["maps"]) <= 20:
        problems.append("map_votes.maps needs 2 to 20 maps")
    if "{maps}" not in mv["rotation_command"]:
        problems.append("map_votes.rotation_command must contain {maps}")
    cb = raw["chat_bridge"]
    if cb["relay_to_game"] not in ("off", "staff", "linked"):
        problems.append('chat_bridge.relay_to_game must be "off", "staff" or "linked"')
    for s in cb["servers"] if cb["enabled"] else []:
        if not s.get("key") or not (s.get("log") or s.get("unit")) or not int(s.get("channel") or 0):
            problems.append("chat_bridge.servers[%s]: needs key, channel and log or unit" % s.get("key"))
    for pat in cb["patterns"]:
        try:
            if "text" not in re.compile(pat).groupindex:
                problems.append("chat_bridge.patterns: every pattern needs a (?P<text>...) group")
        except re.error as e:
            problems.append("chat_bridge.patterns: %s" % e)
    if raw["releases"]["mode"] not in ("draft", "auto"):
        problems.append("releases.mode must be \"draft\" or \"auto\"")
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(raw["timezone"])
    except Exception:  # noqa: BLE001
        problems.append("timezone is not a known time zone: %s" % raw["timezone"])
    return problems


def read_token() -> str:
    cred_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    candidates = []
    if cred_dir:
        candidates.append(Path(cred_dir) / "token")
    if os.environ.get("TCPBOT_TOKEN_FILE"):
        candidates.append(Path(os.environ["TCPBOT_TOKEN_FILE"]))
    for p in candidates:
        try:
            token = p.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if token:
            return token
    raise ConfigError("no bot token: set LoadCredential=token:... in the service, "
                      "or TCPBOT_TOKEN_FILE when running by hand")
