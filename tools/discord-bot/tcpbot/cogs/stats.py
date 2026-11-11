"""Player stats in Discord: /profile, /top, /servers, /compare and /matches."""

from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

from .. import embeds
from ..bot import UserFacingError
from ..text import SORT_LABELS, clean

PID = re.compile(r"[0-9a-f]{16}")


def profile_buttons(cfg, pid: str) -> discord.ui.View:
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Full profile", url=embeds.profile_url(cfg.site, pid)))
    v.add_item(discord.ui.Button(label="Leaderboards", url=cfg.site + "/leaderboards.html"))
    return v


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg

    # ------------------------------------------------------------ player lookup
    async def player_autocomplete(self, interaction: discord.Interaction, current: str):
        if len(current.strip()) < 2:
            return []
        try:
            found = await self.bot.stats.search(current)
        except Exception:  # noqa: BLE001 - autocomplete must never raise
            return []
        return [app_commands.Choice(name="%s · %s · %d matches" % (clean(p["name"], 40), p["rank"]["title"],
                                                                   p["matches"])[:100], value=p["id"])
                for p in found[:25]]

    async def resolve(self, interaction: discord.Interaction, player: str | None,
                      member: discord.Member | None) -> dict:
        """Find the player a command is about: an autocomplete pick, a typed name,
        a mentioned member's linked profile, or the caller's own."""
        if player:
            player = player.strip()
            if PID.fullmatch(player):
                p = await self.bot.stats.player(player)
                if p:
                    return p
            found = await self.bot.stats.search(player)
            exact = [p for p in found if clean(p["name"]).lower() == clean(player).lower()]
            pick = (exact or found or [None])[0]
            if not pick:
                raise UserFacingError("No player called **%s** has played a ranked match yet." % clean(player))
            p = await self.bot.stats.player(pick["id"])
            if not p:
                raise UserFacingError("That profile isn't available right now.")
            return p
        target = member or interaction.user
        link = self.bot.store.linked_player(target.id)
        if not link:
            if member and member.id != interaction.user.id:
                raise UserFacingError("%s hasn't linked a game profile yet." % member.display_name)
            raise UserFacingError("Your Discord account isn't linked to a game profile yet. Use `/link` to "
                                  "connect it, or search for a player with `/profile player:<name>`.")
        p = await self.bot.stats.player(link["pid"])
        if not p:
            raise UserFacingError("Your linked profile has no ranked matches yet. Finish a match on a ranked "
                                  "server and it will show up here.")
        return p

    # ------------------------------------------------------------ commands
    @app_commands.command(name="profile", description="Rank, rating and recent form of a player")
    @app_commands.describe(player="Player name (start typing to search)", member="A Discord member with a linked profile")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.checks.cooldown(3, 15.0)
    async def profile(self, interaction: discord.Interaction, player: str | None = None,
                      member: discord.Member | None = None):
        await interaction.response.defer(thinking=True)
        p = await self.resolve(interaction, player, member)
        link = self.bot.store.linked_member(p["id"])
        who = None
        if link and interaction.guild:
            who = interaction.guild.get_member(link["discord_id"])
        await interaction.followup.send(embed=embeds.profile(self.cfg, p, who, self.bot.store.achievements(p["id"])), view=profile_buttons(self.cfg, p["id"]))

    @app_commands.command(name="top", description="The leaderboard")
    @app_commands.describe(sort="What to rank by", period="All time or the last 30 days", count="How many players (5-20)")
    @app_commands.choices(
        sort=[app_commands.Choice(name=v, value=k) for k, v in SORT_LABELS.items()],
        period=[app_commands.Choice(name="All time", value="all"), app_commands.Choice(name="Last 30 days", value="30d")])
    @app_commands.checks.cooldown(3, 15.0)
    async def top(self, interaction: discord.Interaction, sort: str = "rating", period: str = "all",
                  count: app_commands.Range[int, 5, 20] = 10):
        await interaction.response.defer(thinking=True)
        board = await self.bot.stats.leaderboard(sort, period, count)
        await interaction.followup.send(embed=embeds.leaderboard(self.cfg, board or {}, sort, period))

    @app_commands.command(name="servers", description="Servers online right now")
    @app_commands.checks.cooldown(3, 15.0)
    async def servers(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        data = await self.bot.stats.servers()
        await interaction.followup.send(embed=embeds.server_list(self.cfg, data or {}))

    @app_commands.command(name="compare", description="Put two players side by side")
    @app_commands.describe(first="First player", second="Second player (leave empty to compare with yourself)")
    @app_commands.autocomplete(first=player_autocomplete, second=player_autocomplete)
    @app_commands.checks.cooldown(3, 15.0)
    async def compare(self, interaction: discord.Interaction, first: str, second: str | None = None):
        await interaction.response.defer(thinking=True)
        a = await self.resolve(interaction, first, None)
        b = await self.resolve(interaction, second, None)
        if a["id"] == b["id"]:
            raise UserFacingError("Pick two different players.")
        await interaction.followup.send(embed=embeds.compare(self.cfg, a, b))

    @app_commands.command(name="matches", description="The latest ranked matches")
    @app_commands.checks.cooldown(3, 15.0)
    async def matches(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await interaction.followup.send(embed=embeds.recent_matches(self.cfg, await self.bot.stats.recent()))

    @app_commands.command(name="help", description="What this bot can do")
    async def help(self, interaction: discord.Interaction):
        e = discord.Embed(title="TrueCombat: Platinum bot", colour=embeds.RED)
        e.description = (
            "`/profile` · rank, rating and recent form, yours or anyone's\n"
            "`/top` · `/season` · the all-time board and this season's race\n"
            "`/achievements` · what you've unlocked and what's next\n"
            "`/compare` · two players side by side\n"
            "`/servers` · `/matches` · `/recap` · who is on, the latest matches, the week in numbers\n"
            "`/link` · connect your game profile for your rank role")
        e.add_field(name="Play together", value=(
            "`/pickup join` · queue for a balanced competitive match\n"
            "`/team create` · `/team invite` · `/team list` · teams and the team ladder\n"
            "`/scrim challenge` · `/tournament bracket` · `/tournament play`\n"
            "`/events` · upcoming events and playtests"), inline=False)
        e.add_field(name="Stay in the loop", value=(
            "`/notify` · match, event and playtest pings\n"
            "`/alerts player` · `/alerts map` · `/alerts rank` · personal alerts by DM"), inline=False)
        e.add_field(name="Help and feedback", value=(
            "`/ask` · instant answers about the game\n"
            "`/bug` · `/suggest` · `/suggestion top`\n"
            "`/appeal` · appeal a game ban"), inline=False)
        if self.bot.is_staff(interaction.user):
            e.add_field(name="Staff", value=(
                "`/event create` · `/event cancel` · `/release announce` · `/release notes`\n"
                "`/setup roles` · `/setup panel` · `/setup check` · `/link-admin`\n"
                "`/admin ...` · `/pickup end` · `/pickup reset` · `/pickup servers`\n"
                "`/tournament create` · `start` · `result` · `cancel` · `/scrim result`\n"
                "`/suggestion status` · `/mapvote start` · `/mapvote close` · `/chat`\n"
                "`/mod raid` · `/mod automod`"), inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Stats(bot))
