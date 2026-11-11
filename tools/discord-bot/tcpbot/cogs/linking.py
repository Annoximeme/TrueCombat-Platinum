"""Linking a Discord account to a game profile.

1. ``/link`` gives the member a one-time code (valid 15 minutes).
2. In game they enter ``/link CODE`` (or ``!link CODE`` in chat) on an official
   server. The game server writes ``links/<CODE>.json`` with the player's
   cl_guid into its game folder (see game/link-command.patch).
3. This module picks the file up within seconds, turns the guid into the
   public player id exactly like the stats service does, stores the link and
   deletes the file. The guid never leaves the VPS and is never stored.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import embeds
from ..bot import UserFacingError, staff_only
from ..text import clean

log = logging.getLogger("tcpbot.linking")
GUID = re.compile(r"[0-9A-Fa-f]{32}")
CODE = re.compile(r"[A-Z0-9]{6}")


def player_id(guid: str) -> str:
    """Same one-way id as tools/server-bridge/tcp_stats.py player_id()."""
    return hashlib.sha256(("tcp-lb:" + guid.upper()).encode()).hexdigest()[:16]


def read_request(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    code = str(data.get("code") or "").upper()
    guid = str(data.get("guid") or "")
    if not CODE.fullmatch(code) or not GUID.fullmatch(guid):
        return None
    return {"code": code, "pid": player_id(guid), "name": clean(data.get("name")) or "Player"}


class Linking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.pending: dict[str, discord.Interaction] = {}   # code -> the /link interaction, to update it

    async def cog_load(self):
        if self.cfg["linking"]["enabled"]:
            self.watch.start()

    async def cog_unload(self):
        self.watch.cancel()

    # ------------------------------------------------------------ member commands
    @app_commands.command(name="link", description="Link your Discord account to your game profile")
    @app_commands.checks.cooldown(2, 60.0)
    async def link(self, interaction: discord.Interaction):
        if not self.cfg["linking"]["enabled"]:
            raise UserFacingError("Linking isn't switched on yet.")
        minutes = int(self.cfg["linking"]["code_minutes"])
        code = self.bot.store.new_link_code(interaction.user.id, minutes)
        current = self.bot.store.linked_player(interaction.user.id)
        e = embeds.link_instructions(code, minutes)
        if current:
            e.add_field(name="Currently linked", value="**%s**. Linking again replaces it." % current["name"])
        await interaction.response.send_message(embed=e, ephemeral=True)
        self.pending[code] = interaction
        for c, i in list(self.pending.items()):     # forget interactions whose token has expired
            if time.time() - i.created_at.timestamp() > 14 * 60:
                self.pending.pop(c, None)

    @app_commands.command(name="unlink", description="Remove the link between your Discord account and game profile")
    async def unlink(self, interaction: discord.Interaction):
        if self.bot.store.unlink(interaction.user.id):
            await self.bot.get_cog("Community").sync_member_roles(interaction.user.id)
            await interaction.response.send_message(embed=embeds.notice(
                "Profile unlinked", "Your rank roles will be removed shortly. Your stats are not affected."),
                ephemeral=True)
        else:
            await interaction.response.send_message(embed=embeds.error("Your account isn't linked."), ephemeral=True)

    # ------------------------------------------------------------ staff
    admin = app_commands.Group(name="link-admin", description="Manage profile links (staff)",
                               default_permissions=discord.Permissions(manage_guild=True))

    @admin.command(name="show", description="Show which game profile a member is linked to")
    @staff_only()
    async def admin_show(self, interaction: discord.Interaction, member: discord.Member):
        link = self.bot.store.linked_player(member.id)
        text = ("%s is linked to **[%s](%s)** since <t:%d:D>." % (
            member.mention, link["name"], embeds.profile_url(self.cfg.site, link["pid"]), link["linked_at"])
            if link else "%s has no linked profile." % member.mention)
        await interaction.response.send_message(embed=embeds.notice("Profile link", text), ephemeral=True)

    @admin.command(name="remove", description="Remove a member's profile link")
    @staff_only()
    async def admin_remove(self, interaction: discord.Interaction, member: discord.Member):
        ok = self.bot.store.unlink(member.id)
        if ok:
            await self.bot.get_cog("Community").sync_member_roles(member.id)
        await interaction.response.send_message(embed=embeds.notice(
            "Profile link", "Link removed." if ok else "%s had no linked profile." % member.mention), ephemeral=True)

    # ------------------------------------------------------------ watcher
    @tasks.loop(seconds=5)
    async def watch(self):
        for folder in self.cfg["linking"]["dirs"]:
            d = Path(folder)
            try:
                files = sorted(d.glob("*.json"))
            except OSError:
                continue
            for path in files[:50]:
                try:
                    await self.handle(path)
                except Exception:  # noqa: BLE001
                    log.exception("link request %s failed", path.name)

    @watch.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    async def handle(self, path: Path):
        req = read_request(path)
        try:
            path.unlink()
        except OSError as e:
            log.warning("cannot remove %s (%s); check the folder permissions", path, e)
            return
        if not req:
            return
        user_id = self.bot.store.redeem_link_code(req["code"])
        if not user_id:
            log.info("link code %s is unknown or expired", req["code"])
            return
        prev = self.bot.store.link(user_id, req["pid"], req["name"])
        log.info("linked discord user %s to player %s", user_id, req["pid"])
        interaction = self.pending.pop(req["code"], None)
        done = embeds.link_done(self.cfg, req["name"], req["pid"])
        if interaction:
            try:
                await interaction.edit_original_response(embed=done)
            except discord.HTTPException:
                interaction = None
        if not interaction:
            user = self.bot.get_user(user_id)
            if user:
                try:
                    await user.send(embed=done)
                except discord.HTTPException:
                    pass
        community = self.bot.get_cog("Community")
        if community:
            await community.sync_member_roles(user_id)
            if prev:
                await community.sync_member_roles(prev)


async def setup(bot):
    await bot.add_cog(Linking(bot))
