"""Player reports from the game (/report in game) in the private staff channel.

The game server writes reports/<time>-<by>-<target>.json (schema tcp-report/1,
see tcp_report.h). This module posts each one to the reports channel (the
staff channel by default) and moves the file to reports/sent/.
Staff close a report with the Handled button.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
from pathlib import Path

import discord
from discord.ext import commands, tasks

from .. import embeds
from ..text import clean, iso_to_unix, map_label, md

log = logging.getLogger("tcpbot.reports")
PID = re.compile(r"[0-9a-f]{16}")


def read_report(path: Path) -> dict | None:
    try:
        r = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(r, dict) or r.get("schema") != "tcp-report/1" or not isinstance(r.get("reported"), dict):
        return None
    return r


DEMO_NAME = re.compile(r"_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})_[^/]*\.sv_?\d+$")


def find_demo(folder: Path, when: int | None, tz: str = "UTC") -> tuple[str, int] | None:
    """The server demo that covers a moment, and how far into it the moment is (seconds).
    Server demos are named <host>_<YYYY-MM-DD-HH-MM-SS>_<map>.sv_84 in the server's local time."""
    if not when:
        return None
    try:
        from zoneinfo import ZoneInfo
        zone = ZoneInfo(tz)
    except Exception:  # noqa: BLE001
        zone = dt.timezone.utc
    best = None
    try:
        files = list(folder.glob("*.sv*"))
    except OSError:
        return None
    for f in files:
        m = DEMO_NAME.search(f.name)
        if not m:
            continue
        try:
            start = int(dt.datetime(*map(int, m.groups()), tzinfo=zone).timestamp())
        except ValueError:
            continue
        try:
            end = int(f.stat().st_mtime)
        except OSError:
            continue
        if start <= when <= end + 5 and (best is None or start > best[1]):
            best = (f.name, start)
    return (best[0], when - best[1]) if best else None


def report_embed(cfg, r: dict, recent: int, demo: tuple[str, int] | None = None) -> discord.Embed:
    who, by = r["reported"], r.get("reporter") or {}
    name = clean(who.get("name")) or "Unknown player"
    auto = bool(r.get("auto"))
    e = discord.Embed(title=("Automatic flag · %s" if auto else "Player report · %s") % name,
                      colour=embeds.RED if auto else embeds.AMBER)
    if PID.fullmatch(str(who.get("id") or "")):
        e.url = embeds.profile_url(cfg.site, who["id"])
    reason = clean(r.get("reason"), 300) or "No reason given"
    e.description = "> %s" % md(reason)
    if recent > 1:
        e.description += "\n\n**%d reports** about this player in the last hour." % recent
    shots, hits = int(who.get("shots") or 0), int(who.get("hits") or 0)
    e.add_field(name="This map", value="%s kills · %s deaths · %s team kills" % (
        who.get("kills", 0), who.get("deaths", 0), who.get("team_kills", 0)), inline=False)
    e.add_field(name="Accuracy", value=("%d%% (%d/%d)" % (round(100 * hits / shots), hits, shots)) if shots else "-",
                inline=True)
    e.add_field(name="Slot", value="%s%s" % (who.get("slot", "?"), " · bot" if who.get("bot") else ""), inline=True)
    if auto:
        e.add_field(name="Headshots", value="%s · %s after a flick" % (who.get("headshots", 0), who.get("flick_heads", 0)),
                    inline=True)
    else:
        e.add_field(name="Reported by", value=md(clean(by.get("name")) or "Unknown"), inline=True)
    where = "%s · %s" % (clean(r.get("server"), 80) or "Server", map_label(r.get("map")))
    when = iso_to_unix(r.get("time"))
    if when:
        where += " · <t:%d:R>" % when
    e.add_field(name="Where", value=where, inline=False)
    if demo:
        name, offset = demo
        e.add_field(name="Server demo", value="`%s` at **%d:%02d**" % (name, offset // 60, offset % 60), inline=False)
        e.set_footer(text="The demo keeps every player's view of this moment")
    else:
        e.set_footer(text="No server demo covers this moment (sv_autoDemo off?)")
    return e


class HandledButton(discord.ui.DynamicItem[discord.ui.Button], template=r"tcp:report:handled"):
    def __init__(self):
        super().__init__(discord.ui.Button(label="Handled", style=discord.ButtonStyle.success,
                                           custom_id="tcp:report:handled"))

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls()

    async def callback(self, interaction: discord.Interaction):
        if not interaction.client.is_staff(interaction.user):
            await interaction.response.send_message(embed=embeds.error("This is for staff."), ephemeral=True)
            return
        e = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
        e.colour = embeds.STEEL
        e.set_footer(text="Handled by %s" % interaction.user.display_name)
        await interaction.response.edit_message(embed=e, view=None)


def report_view(cfg, r: dict) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    v.add_item(HandledButton())
    pid = str(r["reported"].get("id") or "")
    if PID.fullmatch(pid):
        v.add_item(discord.ui.Button(label="Profile", url=embeds.profile_url(cfg.site, pid)))
    return v


class Reports(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.recent: list[tuple[float, str]] = []   # (time, reported id or name) for the "N reports" hint

    async def cog_load(self):
        self.bot.add_dynamic_items(HandledButton)
        if self.cfg["reports"]["enabled"]:
            self.watch.start()

    async def cog_unload(self):
        self.watch.cancel()

    @tasks.loop(seconds=15)
    async def watch(self):
        channel = self.bot.text_channel(self.cfg.channel("reports", "staff"))
        if channel is None:
            return
        for folder in self.cfg["reports"]["dirs"]:
            try:
                files = sorted(Path(folder).glob("*.json"))
            except OSError:
                continue
            for path in files[:20]:
                try:
                    await self.handle(path, channel)
                except Exception:  # noqa: BLE001
                    log.exception("report %s failed", path.name)

    @watch.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    async def handle(self, path: Path, channel) -> bool:
        r = read_report(path)
        sent = path.parent / "sent"
        sent.mkdir(exist_ok=True)
        if r is None:
            path.replace(sent / ("invalid-" + path.name))
            return False
        key = str(r["reported"].get("id") or clean(r["reported"].get("name")))
        now = time.time()
        self.recent = [(t, k) for t, k in self.recent if now - t < 3600] + [(now, key)]
        count = sum(1 for _, k in self.recent if k == key)
        demo = find_demo(path.parent.parent / "svdemos", iso_to_unix(r.get("time")),
                         self.cfg["reports"].get("demo_timezone", "UTC"))
        await channel.send(embed=report_embed(self.cfg, r, count, demo), view=report_view(self.cfg, r))
        path.replace(sent / path.name)     # only after Discord accepted it, so nothing is lost
        return True


async def setup(bot):
    await bot.add_cog(Reports(bot))
