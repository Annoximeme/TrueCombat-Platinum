"""Live server cards, the "new #1" post and match alerts.

Replaces the webhook feed (tcp-status): one card per official server, edited
in place every minute, with a "How to join" button.
"""

from __future__ import annotations

import json
import logging
import re
import time

import discord
from discord.ext import commands, tasks

from .. import embeds
from ..sources import StatsUnavailable, is_bot, query_game

log = logging.getLogger("tcpbot.status")


class JoinButton(discord.ui.DynamicItem[discord.ui.Button], template=r"tcp:join:(?P<key>[a-z0-9_-]+)"):
    def __init__(self, key: str):
        super().__init__(discord.ui.Button(label="How to join", style=discord.ButtonStyle.danger,
                                           custom_id="tcp:join:%s" % key))
        self.key = key

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(match["key"])

    async def callback(self, interaction: discord.Interaction):
        server = interaction.client.cfg.server(self.key)
        if not server:
            await interaction.response.send_message(embed=embeds.error("That server is no longer listed."),
                                                    ephemeral=True)
            return
        await interaction.response.send_message(embed=embeds.how_to_join(interaction.client.cfg, server),
                                                ephemeral=True)


def card_view(cfg, key: str) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    v.add_item(JoinButton(key))
    v.add_item(discord.ui.Button(label="Server list", url=cfg.site + "/servers.html"))
    v.add_item(discord.ui.Button(label="Leaderboards", url=cfg.site + "/leaderboards.html"))
    return v


def signature(embed: discord.Embed) -> str:
    d = embed.to_dict()
    d.pop("timestamp", None)
    return json.dumps(d, sort_keys=True)


class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.loop.change_interval(seconds=max(30, int(self.cfg["status"]["interval_seconds"])))

    async def cog_load(self):
        self.bot.add_dynamic_items(JoinButton)
        self.loop.start()

    async def cog_unload(self):
        self.loop.cancel()

    @tasks.loop(seconds=60)
    async def loop(self):
        try:
            await self.tick()
        except Exception:  # noqa: BLE001 - one bad pass must not stop the loop
            log.exception("status pass failed")

    @loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    async def tick(self):
        stats = self.bot.stats
        try:
            board = await stats.leaderboard("rating", "all", 5, fresh=True)
        except StatsUnavailable:
            board = None
        try:
            servers = await stats.servers() if self.cfg["status"].get("show_community") else None
        except StatsUnavailable:
            servers = None

        for server in self.cfg["servers"]:
            status = await query_game(server["host"], server["port"])
            shown, offline_since = self.track(server, status)
            await self.update_card(server, shown, board, servers, offline_since)
            if status and server.get("match_alerts", True):
                await self.check_match(server, status)
        if board:
            await self.check_leader(board)

    # ------------------------------------------------------------ server state
    def track(self, server: dict, status: dict | None):
        """Debounces outages: a server that misses one answer is shown as last seen."""
        key = "srv:%s" % server["key"]
        st = self.bot.store.get(key, {})
        need = int(self.cfg["status"]["offline_after"])
        if status:
            st.update(misses=0, offline_since=None, last=status)
            self.bot.store.set(key, st)
            return status, None
        st["misses"] = st.get("misses", 0) + 1
        if st["misses"] < need and st.get("last"):
            self.bot.store.set(key, st)
            return st["last"], None
        if not st.get("offline_since"):
            st["offline_since"] = int(time.time()) - 60 * (need - 1)
        self.bot.store.set(key, st)
        return None, st["offline_since"]

    async def update_card(self, server, status, board, servers, offline_since):
        cid = int(server.get("channel") or self.cfg.channel("status"))
        channel = self.bot.text_channel(cid)
        if channel is None:
            return
        embed = embeds.server_card(self.cfg, server, status, board, servers, offline_since)
        sig = signature(embed)
        key = "card:%s" % server["key"]
        card = self.bot.store.get(key, {})
        stale = time.time() - card.get("at", 0) >= int(self.cfg["status"]["refresh_minutes"]) * 60
        if card.get("message") and card.get("channel") == cid:
            if card.get("sig") == sig and not stale:
                return
            try:
                await channel.get_partial_message(card["message"]).edit(
                    embed=embed, view=card_view(self.cfg, server["key"]))
                card.update(sig=sig, at=time.time())
                self.bot.store.set(key, card)
                return
            except discord.NotFound:
                log.info("status card for %s was deleted, posting a new one", server["key"])
            except discord.HTTPException as e:
                log.warning("could not edit status card %s: %s", server["key"], e)
                return
        try:
            msg = await channel.send(embed=embed, view=card_view(self.cfg, server["key"]))
        except discord.HTTPException as e:
            log.warning("could not post status card %s: %s", server["key"], e)
            return
        self.bot.store.set(key, {"channel": cid, "message": msg.id, "sig": sig, "at": time.time()})

    # ------------------------------------------------------------ announcements
    async def check_leader(self, board: dict):
        if not self.cfg["leader"]["enabled"] or not board.get("players"):
            return
        top = board["players"][0]
        st = self.bot.store.get("leader", {})
        known = st.get("current")
        if known is None:             # first run: remember quietly
            self.bot.store.set("leader", {"current": {"id": top["id"], "name": top["name"]}})
            return
        if top["id"] == known["id"]:
            st.pop("pending", None)
            self.bot.store.set("leader", st)
            return
        pending = st.get("pending") or {}
        if pending.get("id") != top["id"]:
            pending = {"id": top["id"], "seen": 0}
        pending["seen"] += 1
        st["pending"] = pending
        if pending["seen"] < max(1, int(self.cfg["leader"]["confirm_checks"])):
            self.bot.store.set("leader", st)
            return
        channel = self.bot.text_channel(self.cfg.channel("feed", "status"))
        if channel:
            try:
                await channel.send(embed=embeds.new_leader(self.cfg, top, known))
            except discord.HTTPException as e:
                log.warning("leader post failed: %s", e)
                return
        self.bot.store.set("leader", {"current": {"id": top["id"], "name": top["name"]}})

    async def check_match(self, server: dict, status: dict):
        ma = self.cfg["match_alerts"]
        if not ma["enabled"]:
            return
        humans = len([p for p in status["players"] if not is_bot(p, self.cfg["bot_name_pattern"])])
        key = "match:%s" % server["key"]
        st = self.bot.store.get(key, {"humans": 0, "last": 0})
        was, st["humans"] = st["humans"], humans
        need = int(ma["min_players"])
        fire = humans >= need > was and time.time() - st["last"] >= int(ma["cooldown_minutes"]) * 60
        if fire:
            channel = self.bot.text_channel(self.cfg.channel("feed", "status"))
            role = self.bot.role("alerts")
            if channel:
                try:
                    await channel.send(
                        content=role.mention if role else None,
                        embed=embeds.match_on(self.cfg, server, status, humans),
                        view=card_view(self.cfg, server["key"]),
                        allowed_mentions=discord.AllowedMentions(roles=[role] if role else False))
                    st["last"] = time.time()
                except discord.HTTPException as e:
                    log.warning("match alert failed: %s", e)
        self.bot.store.set(key, st)


async def setup(bot):
    await bot.add_cog(Status(bot))
