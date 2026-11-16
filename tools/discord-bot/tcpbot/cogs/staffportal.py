"""/staff: the staff portal from Discord.

Every command goes through the staff portal on the VPS (loopback, shared token), acting as the Discord member who
typed it with their own portal rights. So a warn, mute, kick or ban from Discord is the same as one from the portal:
bans hold on every server, the punishment shows on the player's record and timeline, and the audit log names the
person. Admin-level tools (long and permanent bans, lifting bans, server settings) stay in the portal, behind its
two-step sign-in.

Off until the portal's token is present (staff portal ``install.sh bot-link``, then this bot's install.sh again).
"""

from __future__ import annotations

import logging
import time
import urllib.parse

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .. import embeds
from ..bot import UserFacingError, staff_only
from ..text import clean, md
from .feedback import secret

log = logging.getLogger("tcpbot.staffportal")
LENGTHS = [
    app_commands.Choice(name="30 minutes", value="30m"),
    app_commands.Choice(name="2 hours", value="2h"),
    app_commands.Choice(name="12 hours", value="12h"),
    app_commands.Choice(name="1 day", value="1d"),
]
MUTES = [
    app_commands.Choice(name="15 minutes", value="15m"),
    app_commands.Choice(name="1 hour", value="1h"),
    app_commands.Choice(name="1 day", value="1d"),
]


def headers_for(member, token: str) -> dict:
    roles = [str(r.id) for r in getattr(member, "roles", []) if getattr(r, "id", None)]
    return {"X-Bot-Token": token, "X-Discord-Id": str(member.id), "X-Discord-Roles": ",".join(roles)[:2000],
            "X-Discord-Name": urllib.parse.quote(getattr(member, "display_name", "") or str(member))[:200]}


class PortalAPI:
    def __init__(self, session: aiohttp.ClientSession, url: str, token: str):
        self.session, self.url, self.token = session, url.rstrip("/"), token

    @property
    def on(self) -> bool:
        return bool(self.token)

    async def call(self, member, method: str, path: str, body: dict | None = None) -> dict:
        if not self.on:
            raise UserFacingError("The staff portal is not linked to the bot yet.")
        try:
            async with self.session.request(method, self.url + "/bot/" + path, json=body, headers=headers_for(member, self.token),
                                            timeout=aiohttp.ClientTimeout(total=10)) as r:
                try:
                    data = await r.json(content_type=None)
                except ValueError:
                    data = {}
                if r.status >= 400:
                    raise UserFacingError((data or {}).get("error") or "The staff portal said no (%d)." % r.status)
                return data or {}
        except (aiohttp.ClientError, TimeoutError) as e:
            raise UserFacingError("The staff portal isn't answering. Try again in a minute.") from e


def ago(t) -> str:
    if not t:
        return "never"
    s = max(0, int(time.time() - int(t)))
    return "%ds ago" % s if s < 60 else "%dm ago" % (s // 60) if s < 3600 else "%dh ago" % (s // 3600) if s < 86400 else "%dd ago" % (s // 86400)


class StaffPortal(commands.Cog):
    group = app_commands.Group(name="staff", description="The staff portal from Discord (staff)",
                               default_permissions=discord.Permissions(kick_members=True), guild_only=True)

    def __init__(self, bot):
        self.bot = bot
        cfg = bot.cfg.get("portal") or {}
        self.api = PortalAPI(bot.http_session, cfg.get("url", "http://127.0.0.1:8097"), secret(cfg.get("token_credential", "portal-token")))
        self.public = cfg.get("public_url", "https://staff.truecombat.eu")

    async def online(self, member) -> list:
        return (await self.api.call(member, "GET", "online")).get("servers", [])

    async def player_choices(self, interaction: discord.Interaction, current: str):
        try:
            servers = await self.online(interaction.user)
        except UserFacingError:
            return []
        out = []
        for s in servers:
            for p in s["players"]:
                label = "%s · %s" % (p["name"], s["name"])
                if current.lower() in label.lower():
                    out.append(app_commands.Choice(name=label[:100], value="%s:%d:%s" % (s["key"], p["slot"], p["name"][:40])))
        return out[:25]

    def parse_player(self, value: str) -> dict:
        try:
            key, slot, name = value.split(":", 2)
            return {"server": key, "slot": int(slot), "name": name}
        except ValueError as e:
            raise UserFacingError("Pick the player from the list.") from e

    async def act(self, interaction, action: str, player: str, reason: str, length: str = "") -> None:
        target = self.parse_player(player)
        await interaction.response.defer(ephemeral=True)
        body = dict(target, action=action, reason=reason, length=length)
        r = await self.api.call(interaction.user, "POST", "action", body)
        word = {"warn": "Warned", "mute": "Muted", "kick": "Kicked", "ban": "Banned"}[action]
        detail = "**%s** on %s\nReason: %s" % (md(clean(target["name"])), target["server"], md(clean(reason, 200)))
        if action == "ban" and r.get("appeal_code"):
            detail += "\nBan #%s · appeal code `%s` · holds on every server" % (r.get("id"), r["appeal_code"])
        detail += "\nIn the portal audit log under your name."
        await interaction.followup.send(embed=embeds.notice(word, detail, embeds.GREEN), ephemeral=True)

    # ------------------------------------------------------------ commands
    @group.command(name="summary", description="Players, reports, cases and who is on duty")
    @staff_only()
    async def summary(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        d = await self.api.call(interaction.user, "GET", "summary")
        rep = d.get("reports") or {}
        e = discord.Embed(title="Staff summary", colour=embeds.STEEL, url=self.public)
        e.add_field(name="Players", value="%d on %d server%s" % (d.get("players_online", 0), d.get("servers_up", 0),
                                                                "" if d.get("servers_up") == 1 else "s"))
        e.add_field(name="Reports", value="%d open · %d in progress" % (rep.get("open", 0), rep.get("claimed", 0)))
        if d.get("cases"):
            e.add_field(name="Cases", value="%d open · %d yours" % (d["cases"]["open"], d["cases"]["mine"]))
        e.add_field(name="Appeals waiting", value=str(d.get("appeals_open", 0)))
        e.add_field(name="Urgent alerts, 24 h", value=str(d.get("urgent_24h", 0)))
        duty = d.get("on_duty") or []
        e.add_field(name="On duty", value=", ".join(md(clean(x["name"])) for x in duty) or "Nobody", inline=False)
        await interaction.followup.send(embed=e, ephemeral=True)

    @group.command(name="reports", description="Open and in-progress player reports")
    @staff_only()
    async def reports(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows = (await self.api.call(interaction.user, "GET", "reports")).get("reports", [])
        e = discord.Embed(title="Reports", colour=embeds.AMBER, url=self.public + "/#/reports")
        e.description = "\n".join("`#%d` **%s** · %s · %s%s\n%s" % (
            r["id"], md(clean(r["target"] or "?")), r["server"] or r["source"], ago(r["received"]),
            " · with %s" % md(clean(r["claimed_by"])) if r["status"] == "claimed" else "", md(clean(r["reason"], 120)))
            for r in rows[:10]) or "Nothing open. Good."
        await interaction.followup.send(embed=e, ephemeral=True)

    @group.command(name="take", description="Take a report so others know you have it")
    @app_commands.describe(report="Report number")
    @staff_only()
    async def take(self, interaction: discord.Interaction, report: int):
        await interaction.response.defer(ephemeral=True)
        await self.api.call(interaction.user, "POST", "report", {"id": report, "action": "take"})
        await interaction.followup.send(embed=embeds.notice("Report #%d is yours" % report, "Shown as yours in the portal.", embeds.GREEN),
                                        ephemeral=True)

    @group.command(name="close", description="Close a report with what was done")
    @app_commands.describe(report="Report number", resolution="What was done")
    @staff_only()
    async def close(self, interaction: discord.Interaction, report: int, resolution: str):
        await interaction.response.defer(ephemeral=True)
        await self.api.call(interaction.user, "POST", "report", {"id": report, "action": "close", "resolution": resolution})
        await interaction.followup.send(embed=embeds.notice("Report #%d closed" % report, md(clean(resolution, 300)), embeds.GREEN),
                                        ephemeral=True)

    @group.command(name="lookup", description="Find a player by any name they have used")
    @app_commands.describe(name="Part of a name")
    @staff_only()
    async def lookup(self, interaction: discord.Interaction, name: str):
        if len(name.strip()) < 2:
            raise UserFacingError("Type at least two characters.")
        await interaction.response.defer(ephemeral=True)
        rows = (await self.api.call(interaction.user, "GET", "lookup?q=" + urllib.parse.quote(name.strip()))).get("players", [])
        e = discord.Embed(title="Players matching %s" % clean(name, 40), colour=embeds.STEEL)
        e.description = "\n".join("**[%s](%s/#/player/%s)**%s · seen %s%s" % (
            md(clean(p["names"][0] if p["names"] else p["pid"])), self.public, p["pid"],
            " (also %s)" % md(clean(", ".join(p["names"][1:]), 80)) if len(p["names"]) > 1 else "", ago(p.get("last_seen")),
            " · **banned**" if p.get("banned") else "") for p in rows) or "Nobody by that name."
        await interaction.followup.send(embed=e, ephemeral=True)

    @group.command(name="warn", description="Warn a player in game (private message)")
    @app_commands.describe(player="Player", reason="What they see")
    @app_commands.autocomplete(player=player_choices)
    @staff_only()
    async def warn(self, interaction: discord.Interaction, player: str, reason: str):
        await self.act(interaction, "warn", player, reason)

    @group.command(name="mute", description="Mute a player's text and voice chat")
    @app_commands.describe(player="Player", length="How long", reason="Why")
    @app_commands.autocomplete(player=player_choices)
    @app_commands.choices(length=MUTES)
    @staff_only()
    async def mute(self, interaction: discord.Interaction, player: str, length: app_commands.Choice[str], reason: str):
        await self.act(interaction, "mute", player, reason, length.value)

    @group.command(name="kick", description="Kick a player")
    @app_commands.describe(player="Player", reason="What they see")
    @app_commands.autocomplete(player=player_choices)
    @staff_only()
    async def kick(self, interaction: discord.Interaction, player: str, reason: str):
        await self.act(interaction, "kick", player, reason)

    @group.command(name="ban", description="Ban a player on every server, up to a day (longer bans in the portal)")
    @app_commands.describe(player="Player", length="How long", reason="Shown to the player with an appeal code")
    @app_commands.autocomplete(player=player_choices)
    @app_commands.choices(length=LENGTHS)
    @staff_only()
    async def ban(self, interaction: discord.Interaction, player: str, length: app_commands.Choice[str], reason: str):
        await self.act(interaction, "ban", player, reason, length.value)

    @group.command(name="duty", description="Go on or off duty (all staff alerts reach your devices while on duty)")
    @app_commands.describe(on="On or off", hours="For how long")
    @app_commands.choices(hours=[app_commands.Choice(name="%d hour%s" % (h, "" if h == 1 else "s"), value=h) for h in (1, 2, 4, 8)])
    @staff_only()
    async def duty(self, interaction: discord.Interaction, on: bool, hours: app_commands.Choice[int] | None = None):
        await interaction.response.defer(ephemeral=True)
        r = await self.api.call(interaction.user, "POST", "duty", {"on": on, "hours": hours.value if hours else 4})
        text = "On duty until <t:%d:t>." % r["until"] if r.get("on") else "You are off duty."
        await interaction.followup.send(embed=embeds.notice("Duty", text, embeds.GREEN), ephemeral=True)


async def setup(bot):
    await bot.add_cog(StaffPortal(bot))
