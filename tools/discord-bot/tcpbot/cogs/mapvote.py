"""Map votes: the community picks the maps for the coming week.

A vote opens on a schedule (or with /mapvote start), shows one button per
map, and gives every member a few votes. When it closes the winners are
announced, staff get the result, and with map_votes.apply = "rcon" the
rotation on the listed servers is set straight away.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import time
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import embeds
from .. import text as T
from ..bot import UserFacingError, staff_only
from ..rcon import RconError, server_rcon

log = logging.getLogger("tcpbot.mapvote")
MAP = re.compile(r"[a-z0-9_]{2,40}")


def tally(d: dict) -> list[tuple[str, int]]:
    """Maps with their votes, most wanted first. Ties keep the order of the ballot."""
    counts = {m: 0 for m in d["maps"]}
    for picks in d["votes"].values():
        for m in picks:
            if m in counts:
                counts[m] += 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], d["maps"].index(kv[0])))


def vote_embed(d: dict) -> discord.Embed:
    ranked = tally(d)
    voters = len([v for v in d["votes"].values() if v])
    if d["state"] == "open":
        e = discord.Embed(title="Map vote", colour=embeds.RED)
        e.description = ("Which maps should run on the official servers next? Pick up to **%d**; press a map again to "
                         "take your vote back.\nCloses <t:%d:R>." % (d["per_member"], d["closes"]))
    else:
        e = discord.Embed(title="Map vote · result", colour=embeds.GOLD)
        e.description = "The community picked **%s**." % ", ".join(T.map_label(m) for m in d.get("winners") or [])
    top = max((c for _, c in ranked), default=0) or 1
    rows = [(T.map_label(m), "█" * round(8 * c / top) or "·", str(c)) for m, c in ranked]
    e.add_field(name="%d member%s voted" % (voters, "" if voters == 1 else "s"),
                value="```\n%s\n```" % T.table(rows, "llr"), inline=False)
    return e


class MapButton(discord.ui.DynamicItem[discord.ui.Button], template=r"tcp:mv:(?P<ref>\d+):(?P<idx>\d+)"):
    def __init__(self, ref: int, idx: int, label: str = "Map"):
        super().__init__(discord.ui.Button(label=label[:80], style=discord.ButtonStyle.secondary,
                                           custom_id="tcp:mv:%d:%d" % (ref, idx), row=idx // 5))
        self.ref, self.idx = ref, idx

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(int(match["ref"]), int(match["idx"]), item.label or "Map")

    async def callback(self, interaction: discord.Interaction):
        cog: MapVote = interaction.client.get_cog("MapVote")
        try:
            d, text = cog.cast(interaction.user.id, self.ref, self.idx)
        except UserFacingError as e:
            await interaction.response.send_message(embed=embeds.error(str(e)), ephemeral=True)
            return
        await interaction.response.edit_message(embed=vote_embed(d))
        await interaction.followup.send(embed=embeds.notice("Map vote", text), ephemeral=True)


def vote_view(d: dict) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for i, m in enumerate(d["maps"]):
        v.add_item(MapButton(d["id"], i, T.map_label(m)))
    return v


class MapVote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.mc = bot.cfg["map_votes"]

    async def cog_load(self):
        self.bot.add_dynamic_items(MapButton)
        self.tick.start()

    async def cog_unload(self):
        self.tick.cancel()

    def channel(self):
        return self.bot.text_channel(self.cfg.channel("votes", "announcements"))

    def open_vote(self) -> dict | None:
        rows = self.bot.store.docs("mapvote", "open", limit=1)
        return rows[0] if rows else None

    def cast(self, uid: int, ref: int, idx: int) -> tuple[dict, str]:
        d = self.bot.store.doc("mapvote", ref)
        if not d or d["state"] != "open" or idx >= len(d["maps"]):
            raise UserFacingError("This vote has closed.")
        m = d["maps"][idx]
        picks = d["votes"].setdefault(str(uid), [])
        if m in picks:
            picks.remove(m)
            text = "Vote for **%s** taken back." % T.map_label(m)
        elif len(picks) >= d["per_member"]:
            raise UserFacingError("You've used your %d votes (%s). Press one of those again to free it up." % (
                d["per_member"], ", ".join(T.map_label(x) for x in picks)))
        else:
            picks.append(m)
            left = d["per_member"] - len(picks)
            text = "Voted for **%s**. %s" % (T.map_label(m), "%d vote%s left." % (left, "" if left == 1 else "s")
                                            if left else "That was your last vote.")
        self.bot.store.doc_save(d)
        return d, text

    async def start(self, hours: float, maps: list[str] | None = None) -> dict:
        ch = self.channel()
        if ch is None:
            raise UserFacingError("Set `channels.votes` (or announcements) first.")
        if self.open_vote():
            raise UserFacingError("A map vote is already open.")
        maps = [m for m in dict.fromkeys(maps or self.mc["maps"]) if MAP.fullmatch(m)][:20]
        if len(maps) < 2:
            raise UserFacingError("A vote needs at least two maps.")
        d = {"maps": maps, "votes": {}, "closes": int(time.time() + hours * 3600), "message": 0, "channel": ch.id,
             "per_member": max(1, min(int(self.mc["votes_per_member"]), len(maps) - 1)),
             "winners_wanted": max(1, min(int(self.mc["winners"]), len(maps)))}
        d = self.bot.store.doc("mapvote", self.bot.store.doc_add("mapvote", d))
        msg = await ch.send(embed=vote_embed(d), view=vote_view(d))
        d["message"] = msg.id
        self.bot.store.doc_save(d)
        return d

    async def close(self, d: dict):
        ranked = tally(d)
        d["winners"] = [m for m, _ in ranked[: d["winners_wanted"]]]
        d["state"] = "closed"
        self.bot.store.doc_save(d)
        ch = self.bot.text_channel(d.get("channel", 0)) or self.channel()
        if ch and d.get("message"):
            try:
                await ch.get_partial_message(d["message"]).edit(embed=vote_embed(d), view=None)
            except discord.HTTPException:
                pass
        if not any(c for _, c in ranked):
            return                               # nobody voted: leave the rotation alone
        applied = []
        if self.mc["apply"] == "rcon":
            cmd = self.mc["rotation_command"].replace("{maps}", " ".join(d["winners"]))
            for key in self.mc["servers"]:
                server = self.cfg.server(key)
                try:
                    if server is None:
                        raise RconError("unknown server")
                    await server_rcon(server, cmd)
                    applied.append("%s: rotation set" % key)
                except (RconError, OSError) as e:
                    applied.append("%s: **not set** (%s)" % (key, e))
        staff = self.bot.text_channel(self.cfg.channel("staff"))
        if staff:
            text = "Winners: **%s**\n`%s`" % (", ".join(T.map_label(m) for m in d["winners"]), " ".join(d["winners"]))
            text += "\n" + ("\n".join(applied) if applied else "The rotation was not changed automatically.")
            await staff.send(embed=embeds.notice("Map vote closed", text, embeds.BLUE))

    @tasks.loop(minutes=2)
    async def tick(self):
        try:
            await self.housekeeping(dt.datetime.now(dt.timezone.utc))
        except Exception:  # noqa: BLE001
            log.exception("map vote tick failed")

    @tick.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()

    async def housekeeping(self, now: dt.datetime):
        d = self.open_vote()
        if d and now.timestamp() >= d["closes"]:
            await self.close(d)
            return
        if d or not self.mc["enabled"]:
            return
        local = now.astimezone(ZoneInfo(self.cfg["timezone"]))
        week = "%d-W%02d" % local.isocalendar()[:2]
        if local.weekday() == int(self.mc["weekday"]) and local.hour >= int(self.mc["hour"]) and \
                self.bot.store.get("mapvote_week") != week:
            self.bot.store.set("mapvote_week", week)
            try:
                await self.start(float(self.mc["hours_open"]))
            except UserFacingError as e:
                log.warning("map vote not started: %s", e)

    group = app_commands.Group(name="mapvote", description="Map votes", default_permissions=discord.Permissions(manage_guild=True))

    @group.command(name="start", description="Open a map vote now (staff)")
    @app_commands.describe(hours="How long the vote stays open", maps="Maps on the ballot, separated by spaces "
                                                                     "(empty = the configured list)")
    @staff_only()
    async def cmd_start(self, interaction: discord.Interaction, hours: app_commands.Range[int, 1, 168] = 48,
                        maps: str | None = None):
        await interaction.response.defer(ephemeral=True)
        picked = [m.lower() for m in re.split(r"[\s,]+", maps.strip())] if maps else None
        d = await self.start(hours, picked)
        await interaction.followup.send(embed=embeds.notice(
            "Map vote", "Opened with %d maps. It closes <t:%d:R>." % (len(d["maps"]), d["closes"])), ephemeral=True)

    @group.command(name="close", description="Close the open map vote now (staff)")
    @staff_only()
    async def cmd_close(self, interaction: discord.Interaction):
        d = self.open_vote()
        if not d:
            raise UserFacingError("No map vote is open.")
        await interaction.response.defer(ephemeral=True)
        await self.close(d)
        await interaction.followup.send(embed=embeds.notice("Map vote", "Closed. Winners: %s." % ", ".join(
            T.map_label(m) for m in d["winners"])), ephemeral=True)


async def setup(bot):
    await bot.add_cog(MapVote(bot))
