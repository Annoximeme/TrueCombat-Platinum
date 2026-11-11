"""Personal alerts by DM: a player you follow joins a server, a map you like
comes up, or someone passes you on the leaderboard.

Every alert has its own cooldown, and a member who closes their DMs simply
stops receiving them. Nothing is posted in public channels.
"""

from __future__ import annotations

import logging
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import embeds
from .. import text as T
from ..bot import UserFacingError
from ..sources import StatsUnavailable, is_bot, query_game

log = logging.getLogger("tcpbot.alerts")


def name_key(name: str) -> str:
    return T.clean(name, 40).casefold()


class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.ac = bot.cfg["alerts"]
        self.online: dict[str, set[str]] = {}      # server key -> names seen on the last check
        self.maps: dict[str, str] = {}
        if self.ac["enabled"]:
            self.tick.start()
            self.ranks.start()

    def cog_unload(self):
        self.tick.cancel()
        self.ranks.cancel()

    async def dm(self, row, embed: discord.Embed, cooldown_minutes: int, view=None) -> bool:
        if time.time() - row["last_sent"] < cooldown_minutes * 60:
            return False
        user = self.bot.get_user(row["discord_id"])
        if user is None:
            return False
        self.bot.store.alert_sent(row["discord_id"], row["kind"], row["target"])
        try:
            if view is not None:
                await user.send(embed=embed, view=view)
            else:
                await user.send(embed=embed)
        except discord.HTTPException:
            return False
        return True

    def join_view(self, server: dict) -> discord.ui.View:
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label="Server list", url=self.cfg.site + "/servers.html"))
        return v

    # ------------------------------------------------------------ players and maps
    @tasks.loop(seconds=60)
    async def tick(self):
        for server in self.cfg["servers"]:
            try:
                status = await query_game(server["host"], server["port"])
                if status is not None:
                    await self.check_server(server, status)
            except Exception:  # noqa: BLE001
                log.exception("alerts for %s failed", server.get("key"))

    @tick.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()

    async def check_server(self, server: dict, status: dict):
        key = server["key"]
        humans = [p for p in status["players"] if not is_bot(p, self.cfg["bot_name_pattern"])]
        names = {name_key(p["name"]): T.clean(p["name"]) for p in humans}
        mapname = (status["cvars"].get("mapname") or "").lower()
        first = key not in self.online
        joined = set(names) - self.online.get(key, set())
        map_changed = self.maps.get(key) != mapname
        self.online[key], self.maps[key] = set(names), mapname
        if first:
            return                     # after a restart, whoever is already playing is not news
        addr = server["public_address"]
        short = server["name"].split("|")[-1].strip()
        for n in joined:
            for row in self.bot.store.alerts_for("player", n):
                e = embeds.notice("%s is playing" % T.md(names[n]),
                                  "**%s** just joined **%s** on %s, %d playing.\n`/connect %s`" % (
                                      T.md(names[n]), T.md(short), T.map_label(mapname), len(humans), addr), embeds.GREEN)
                e.set_footer(text="You follow this player. /alerts list to change that.")
                await self.dm(row, e, int(self.ac["player_cooldown_minutes"]), self.join_view(server))
        if map_changed and mapname and len(humans) >= int(self.ac["map_min_players"]):
            for row in self.bot.store.alerts_for("map", mapname):
                e = embeds.notice("%s is up" % T.map_label(mapname),
                                  "**%s** just loaded on **%s** with %d playing.\n`/connect %s`" % (
                                      T.map_label(mapname), T.md(short), len(humans), addr), embeds.GREEN)
                img = T.map_image(self.cfg.site, mapname)
                if img:
                    e.set_thumbnail(url=img)
                e.set_footer(text="You asked for this map. /alerts list to change that.")
                await self.dm(row, e, int(self.ac["map_cooldown_minutes"]), self.join_view(server))

    # ------------------------------------------------------------ leaderboard
    @tasks.loop(minutes=10)
    async def ranks(self):
        try:
            await self.check_ranks()
        except StatsUnavailable:
            pass
        except Exception:  # noqa: BLE001
            log.exception("rank alerts failed")

    @ranks.before_loop
    async def _ready2(self):
        await self.bot.wait_until_ready()

    async def check_ranks(self):
        rows = self.bot.store.alerts_for("rank")
        if not rows:
            return
        board = await self.bot.stats.leaderboard("rating", "all", 100, fresh=True)
        players = (board or {}).get("players") or []
        now_pos = {p["id"]: i for i, p in enumerate(players, 1)}
        before = self.bot.store.get("rank_positions") or {}
        self.bot.store.set("rank_positions", now_pos)
        if not before:
            return
        for row in rows:
            link = self.bot.store.linked_player(row["discord_id"])
            if not link:
                continue
            old, new = before.get(link["pid"]), now_pos.get(link["pid"])
            if not old or not new or new <= old:
                continue
            # whoever sits above now and sat below (or nowhere) before has passed them
            passed = [p for p in players[: new - 1] if before.get(p["id"], 10 ** 6) > old]
            if not passed:
                continue
            who = passed[-1]
            e = embeds.notice("You've been passed", "**%s** moved ahead of you on the leaderboard. You're now **#%d** "
                              "(was #%d), %s rating behind." % (
                                  T.md(T.clean(who["name"])), new, old,
                                  T.num(max(0, who["rating"] - players[new - 1]["rating"]))), embeds.AMBER)
            e.set_footer(text="A ranked match is the way back. /alerts rank to turn this off.")
            await self.dm(row, e, int(self.ac["rank_cooldown_minutes"]))

    # ------------------------------------------------------------ commands
    group = app_commands.Group(name="alerts", description="Personal alerts by DM: players, maps and your leaderboard place")

    def _room(self, uid: int):
        if not self.ac["enabled"]:
            raise UserFacingError("Personal alerts are switched off right now.")
        if len(self.bot.store.alerts_of(uid)) >= int(self.ac["max_follows"]):
            raise UserFacingError("You have %d alerts, which is the limit. Remove one with `/alerts remove` first."
                                  % int(self.ac["max_follows"]))

    @group.command(name="player", description="Get a DM when a player joins an official server")
    @app_commands.describe(name="The player's in-game name, exactly as they write it")
    async def cmd_player(self, interaction: discord.Interaction, name: app_commands.Range[str, 2, 36]):
        self._room(interaction.user.id)
        key = name_key(name)
        if not key:
            raise UserFacingError("That doesn't look like a player name.")
        self.bot.store.alert_add(interaction.user.id, "player", key, T.clean(name))
        await interaction.response.send_message(embed=embeds.notice(
            "Alert set", "I'll DM you when **%s** joins an official server, at most once every %s. "
            "Make sure your DMs are open for this server." % (
                T.md(T.clean(name)), T.duration(int(self.ac["player_cooldown_minutes"]) * 60))), ephemeral=True)

    async def _maps(self, interaction: discord.Interaction, current: str):
        known = sorted(set(self.cfg["pickup"]["maps"]) | set(self.cfg["map_votes"]["maps"]) | set(self.maps.values()) - {""})
        cur = current.lower()
        return [app_commands.Choice(name=T.map_label(m), value=m) for m in known
                if cur in m or cur in T.map_label(m).lower()][:25]

    @group.command(name="map", description="Get a DM when a map comes up on an official server with players on it")
    @app_commands.describe(map="The map, for example Snow")
    @app_commands.autocomplete(map=_maps)
    async def cmd_map(self, interaction: discord.Interaction, map: app_commands.Range[str, 2, 40]):  # noqa: A002
        self._room(interaction.user.id)
        key = map.strip().lower().replace(" ", "_")
        if not key.replace("_", "").isalnum():
            raise UserFacingError("That doesn't look like a map name.")
        if "_" not in key:
            key = next((m for m in await self._known() if T.map_label(m).lower() == key), "obj_" + key)
        self.bot.store.alert_add(interaction.user.id, "map", key, T.map_label(key))
        await interaction.response.send_message(embed=embeds.notice(
            "Alert set", "I'll DM you when **%s** loads on an official server with at least %d playing."
            % (T.map_label(key), int(self.ac["map_min_players"]))), ephemeral=True)

    async def _known(self):
        return sorted(set(self.cfg["pickup"]["maps"]) | set(self.cfg["map_votes"]["maps"]))

    @group.command(name="rank", description="Get a DM when someone passes you on the leaderboard (on or off)")
    async def cmd_rank(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if self.bot.store.alert_remove(uid, "rank"):
            text = "Leaderboard alerts are off."
        else:
            if not self.bot.store.linked_player(uid):
                raise UserFacingError("Link your game profile with `/link` first, so I know which player you are.")
            self._room(uid)
            self.bot.store.alert_add(uid, "rank", "self", "Leaderboard place")
            text = "I'll DM you when someone passes you in the top 100. Press it again to turn it off."
        await interaction.response.send_message(embed=embeds.notice("Leaderboard alerts", text), ephemeral=True)

    @group.command(name="list", description="Your alerts")
    async def cmd_list(self, interaction: discord.Interaction):
        rows = self.bot.store.alerts_of(interaction.user.id)
        kinds = {"player": "Player", "map": "Map", "rank": "Leaderboard"}
        text = "\n".join("**%s** · %s" % (kinds[r["kind"]], T.md(r["label"])) for r in rows) or (
            "None yet. Try `/alerts player`, `/alerts map` or `/alerts rank`.")
        await interaction.response.send_message(embed=embeds.notice("Your alerts", text), ephemeral=True)

    async def _mine(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=("%s: %s" % (r["kind"], r["label"]))[:100], value="%s:%s" % (r["kind"], r["target"]))
                for r in self.bot.store.alerts_of(interaction.user.id) if current.lower() in r["label"].lower()][:25]

    @group.command(name="remove", description="Remove one alert, or all of them")
    @app_commands.describe(alert="Which alert (leave empty to remove them all)")
    @app_commands.autocomplete(alert=_mine)
    async def cmd_remove(self, interaction: discord.Interaction, alert: str | None = None):
        if alert:
            kind, _, target = alert.partition(":")
            n = self.bot.store.alert_remove(interaction.user.id, kind, target)
        else:
            n = self.bot.store.alert_remove(interaction.user.id)
        await interaction.response.send_message(embed=embeds.notice(
            "Your alerts", "Removed %d alert%s." % (n, "" if n == 1 else "s") if n else "Nothing to remove."),
            ephemeral=True)


async def setup(bot):
    await bot.add_cog(Alerts(bot))
