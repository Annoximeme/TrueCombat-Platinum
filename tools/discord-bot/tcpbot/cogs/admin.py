"""Server administration from Discord, for staff only.

Every command talks to our own game servers over rcon on the VPS. Bans are
shared: a ban issued here is written to every server in ``servers`` (and the
pickup servers), so a cheater banned on #1 can't walk onto #2. Each action is
logged in the staff channel with who did it.

Ban lengths use the server's own syntax: 30m, 12h, 7d, 2w, or permanent.
"""

from __future__ import annotations

import asyncio
import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

from .. import embeds
from ..bot import UserFacingError, staff_only
from ..rcon import RconError, parse_banlist, parse_status, safe_arg, server_rcon
from ..text import clean, md

log = logging.getLogger("tcpbot.admin")
DURATION = re.compile(r"^(\d{1,4})([mhdw])$")
GUID = re.compile(r"^[0-9A-Fa-f]{32}$")
MAP = re.compile(r"^[A-Za-z0-9_-]{1,48}$")
LENGTHS = [
    app_commands.Choice(name="30 minutes", value="30m"),
    app_commands.Choice(name="2 hours", value="2h"),
    app_commands.Choice(name="1 day", value="1d"),
    app_commands.Choice(name="7 days", value="7d"),
    app_commands.Choice(name="30 days", value="30d"),
    app_commands.Choice(name="Permanent", value="perm"),
]


def length_label(value: str) -> str:
    m = DURATION.match(value or "")
    if not m:
        return "permanently"
    n, unit = int(m.group(1)), m.group(2)
    word = {"m": "minute", "h": "hour", "d": "day", "w": "week"}[unit]
    return "for %d %s%s" % (n, word, "" if n == 1 else "s")


def admin_servers(cfg) -> list[dict]:
    """Every server the bot can administer: official servers plus pickup servers, with rcon set up."""
    out = [s for s in cfg["servers"] if s.get("rcon_credential") or s.get("rcon_password_file")]
    for s in (cfg.get("pickup") or {}).get("servers", []):
        if s.get("rcon_credential") or s.get("rcon_password_file"):
            out.append(s)
    return out


def log_embed(actor: discord.abc.User, action: str, detail: str, colour: int = embeds.AMBER) -> discord.Embed:
    e = discord.Embed(title=action, description=detail, colour=colour)
    e.set_footer(text="By %s" % actor.display_name)
    e.timestamp = discord.utils.utcnow()
    return e


class Admin(commands.Cog):
    group = app_commands.Group(name="admin", description="Moderate the official servers (staff)",
                               default_permissions=discord.Permissions(kick_members=True), guild_only=True)

    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg

    # ------------------------------------------------------------ helpers
    def server(self, key: str) -> dict:
        s = next((s for s in admin_servers(self.cfg) if s["key"] == key), None)
        if not s:
            raise UserFacingError("I can't administer that server. Pick one from the list.")
        return s

    async def run(self, server: dict, command: str) -> str:
        try:
            return await server_rcon(server, command)
        except RconError as e:
            raise UserFacingError("%s: %s" % (server.get("name", server["key"]), e)) from e

    async def audit(self, embed: discord.Embed):
        ch = self.bot.text_channel(self.cfg.channel("staff"))
        if ch:
            try:
                await ch.send(embed=embed)
            except discord.HTTPException:
                log.warning("could not post the admin log entry")

    async def server_choices(self, interaction, current: str):
        cur = current.lower()
        return [app_commands.Choice(name=s.get("name", s["key"])[:100], value=s["key"])
                for s in admin_servers(self.cfg) if cur in s.get("name", s["key"]).lower()][:25]

    async def player_choices(self, interaction, current: str):
        key = getattr(interaction.namespace, "server", None)
        servers = [s for s in admin_servers(self.cfg) if not key or s["key"] == key]
        out = []
        for s in servers[:3]:
            try:
                st = parse_status(await server_rcon(s, "status", timeout=1.0))
            except (RconError, OSError):
                continue
            for p in st["players"]:
                if p["bot"]:
                    continue
                label = "%s (slot %d)" % (p["name"], p["slot"])
                if current.lower() in label.lower():
                    out.append(app_commands.Choice(name=label[:100], value=str(p["slot"])))
        return out[:25]

    async def push_guid_ban(self, guid: str, length: str, reason: str, skip: str = "") -> list[str]:
        """banguid on every administered server. Returns the names of servers that failed."""
        cmd = "banguid %s %s%s" % (guid, "" if length == "perm" else length + " ", safe_arg(reason))
        failed = []

        async def one(s):
            if s["key"] == skip:
                return
            try:
                await server_rcon(s, cmd.strip())
            except (RconError, OSError):
                failed.append(s.get("name", s["key"]))
        await asyncio.gather(*(one(s) for s in admin_servers(self.cfg)))
        return failed

    # ------------------------------------------------------------ commands
    @group.command(name="players", description="Who is on a server right now, with slot numbers")
    @app_commands.describe(server="Server")
    @app_commands.autocomplete(server=server_choices)
    @staff_only()
    async def players(self, interaction: discord.Interaction, server: str):
        s = self.server(server)
        await interaction.response.defer(ephemeral=True)
        st = parse_status(await self.run(s, "status"))
        humans = [p for p in st["players"] if not p["bot"]]
        bots = len(st["players"]) - len(humans)
        e = discord.Embed(title=s.get("name", s["key"]), colour=embeds.STEEL)
        e.description = "\n".join("`%2d` %s · %s ms" % (p["slot"], md(clean(p["name"])), p["ping"]) for p in humans) \
            or "No players."
        e.set_footer(text="%s · %d bot%s" % (st["map"] or "?", bots, "" if bots == 1 else "s"))
        await interaction.followup.send(embed=e, ephemeral=True)

    @group.command(name="kick", description="Kick a player from a server")
    @app_commands.describe(server="Server", player="Player (name or slot)", reason="Shown to the player")
    @app_commands.autocomplete(server=server_choices, player=player_choices)
    @staff_only()
    async def kick(self, interaction: discord.Interaction, server: str, player: str, reason: str):
        s = self.server(server)
        await interaction.response.defer(ephemeral=True)
        out = await self.run(s, "kick %s %s" % (safe_arg(player, 40), safe_arg(reason)))
        if "No player" in out or "matches" in out:
            raise UserFacingError(clean(out.strip(), 200))
        await self.audit(log_embed(interaction.user, "Kick · %s" % s.get("name", s["key"]),
                                   "Player `%s`\nReason: %s" % (safe_arg(player, 40), md(safe_arg(reason)))))
        await interaction.followup.send(embed=embeds.notice("Kicked", "Done. Logged in the staff channel.",
                                                            embeds.GREEN), ephemeral=True)

    @group.command(name="ban", description="Ban a player on every official server")
    @app_commands.describe(server="Server the player is on", player="Player (name or slot)",
                           length="How long", reason="Shown to the player when they try to join")
    @app_commands.autocomplete(server=server_choices, player=player_choices)
    @app_commands.choices(length=LENGTHS)
    @staff_only()
    async def ban(self, interaction: discord.Interaction, server: str, player: str,
                  length: app_commands.Choice[str], reason: str):
        s = self.server(server)
        await interaction.response.defer(ephemeral=True)
        dur = "" if length.value == "perm" else length.value + " "
        out = await self.run(s, "ban %s %s%s" % (safe_arg(player, 40), dur, safe_arg(reason)))
        if "No player" in out or "matches" in out or "Cannot" in out:
            raise UserFacingError(clean(out.strip(), 200))
        bans = parse_banlist(await self.run(s, "banlist"))
        guid = bans[-1]["guid"] if bans else ""
        failed = await self.push_guid_ban(guid, length.value, reason, skip=s["key"]) if guid else []
        detail = "Player `%s` %s\nReason: %s" % (bans[-1]["name"] if bans else safe_arg(player, 40),
                                                 length_label(length.value), md(safe_arg(reason)))
        if failed:
            detail += "\n**Not copied to:** %s" % ", ".join(failed)
        elif not guid:
            detail += "\nNo game key on this player, so the ban is by address on this server only."
        await self.audit(log_embed(interaction.user, "Ban · %s" % s.get("name", s["key"]), detail, embeds.RED))
        await interaction.followup.send(embed=embeds.notice("Banned", detail, embeds.GREEN), ephemeral=True)

    @group.command(name="banguid", description="Ban a game key (cl_guid) on every official server")
    @app_commands.describe(guid="32-character game key from banlist or the logs", length="How long",
                           reason="Shown to the player")
    @app_commands.choices(length=LENGTHS)
    @staff_only()
    async def banguid(self, interaction: discord.Interaction, guid: str, length: app_commands.Choice[str],
                      reason: str):
        if not GUID.match(guid.strip()):
            raise UserFacingError("A game key is 32 hexadecimal characters.")
        await interaction.response.defer(ephemeral=True)
        failed = await self.push_guid_ban(guid.strip().upper(), length.value, reason)
        detail = "Key `%s` %s\nReason: %s" % (guid.strip().upper(), length_label(length.value), md(safe_arg(reason)))
        if failed:
            detail += "\n**Failed on:** %s" % ", ".join(failed)
        await self.audit(log_embed(interaction.user, "Ban by game key", detail, embeds.RED))
        await interaction.followup.send(embed=embeds.notice("Banned", detail, embeds.GREEN), ephemeral=True)

    @group.command(name="unban", description="Lift a ban on every official server")
    @app_commands.describe(target="Game key or IP address from /admin banlist")
    @staff_only()
    async def unban(self, interaction: discord.Interaction, target: str):
        t = safe_arg(target, 64).replace(" ", "")
        if not (GUID.match(t) or re.match(r"^[0-9a-fA-F.:*]{3,45}$", t)):
            raise UserFacingError("Give the game key or IP address exactly as /admin banlist shows it.")
        await interaction.response.defer(ephemeral=True)
        done, failed = [], []
        for s in admin_servers(self.cfg):
            try:
                out = await server_rcon(s, "unban %s" % t)
                if "No ban matches" not in out:
                    done.append(s.get("name", s["key"]))
            except (RconError, OSError):
                failed.append(s.get("name", s["key"]))
        if not done and not failed:
            raise UserFacingError("No server has a ban for `%s`." % t)
        detail = "`%s` lifted on %s" % (t, ", ".join(done) or "no server")
        if failed:
            detail += "\n**Failed on:** %s" % ", ".join(failed)
        await self.audit(log_embed(interaction.user, "Unban", detail, embeds.GREEN))
        await interaction.followup.send(embed=embeds.notice("Unbanned", detail, embeds.GREEN), ephemeral=True)

    @group.command(name="banlist", description="Current bans on a server")
    @app_commands.describe(server="Server")
    @app_commands.autocomplete(server=server_choices)
    @staff_only()
    async def banlist(self, interaction: discord.Interaction, server: str):
        s = self.server(server)
        await interaction.response.defer(ephemeral=True)
        bans = parse_banlist(await self.run(s, "banlist"))
        e = discord.Embed(title="Bans · %s" % s.get("name", s["key"]), colour=embeds.STEEL)
        lines = []
        for b in bans[-20:]:
            left = ("%d min left" % b["minutes_left"]) if b["minutes_left"] else "permanent"
            lines.append("`#%d` **%s** · %s · %s\n`%s`%s" % (
                b["number"], md(clean(b["name"]) or "?"), left, md(clean(b["reason"], 60) or "no reason"),
                b["guid"] or b["ip"] or b["puid"], "" if not (b["guid"] and b["ip"]) else " · " + b["ip"]))
        e.description = "\n".join(lines) or "No bans."
        if len(bans) > 20:
            e.set_footer(text="Newest 20 of %d" % len(bans))
        await interaction.followup.send(embed=e, ephemeral=True)

    @group.command(name="map", description="Change the map now, or go to the next map in the rotation")
    @app_commands.describe(server="Server", map="Map name, empty for the next map")
    @app_commands.autocomplete(server=server_choices)
    @staff_only()
    async def map(self, interaction: discord.Interaction, server: str, map: str | None = None):
        s = self.server(server)
        if map and not MAP.match(map):
            raise UserFacingError("That isn't a map name.")
        await interaction.response.defer(ephemeral=True)
        out = await self.run(s, "nextmap %s" % (map or ""))
        if "not" in out.lower() and "found" in out.lower():
            raise UserFacingError(clean(out.strip(), 200))
        await self.audit(log_embed(interaction.user, "Map change · %s" % s.get("name", s["key"]),
                                   map or "Next map in the rotation", embeds.BLUE))
        await interaction.followup.send(embed=embeds.notice("Map change", "Changing to %s." % (map or "the next map"),
                                                            embeds.GREEN), ephemeral=True)

    @group.command(name="say", description="Post a message in the game chat as the server")
    @app_commands.describe(server="Server", message="Message")
    @app_commands.autocomplete(server=server_choices)
    @staff_only()
    async def say(self, interaction: discord.Interaction, server: str, message: str):
        s = self.server(server)
        await interaction.response.defer(ephemeral=True)
        await self.run(s, "say \"%s\"" % safe_arg(message, 150))
        await self.audit(log_embed(interaction.user, "Server message · %s" % s.get("name", s["key"]),
                                   md(safe_arg(message, 150)), embeds.BLUE))
        await interaction.followup.send(embed=embeds.notice("Sent", md(safe_arg(message, 150)), embeds.GREEN),
                                        ephemeral=True)


async def setup(bot):
    await bot.add_cog(Admin(bot))
