"""Player accounts in Discord: the weekly report, the looking-for-a-squad board and staff sanctions.

All of it reads the account service on the VPS (tcp_accounts.py). Without its token the cog stays
quiet: no loops run and the staff commands say the service is not connected.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import urllib.parse
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import embeds
from ..bot import UserFacingError, staff_only
from ..sources import AccountsUnavailable, StatsUnavailable
from ..text import clean, md

log = logging.getLogger("tcpbot.accounts")


def safe(text, limit: int = 36) -> str:
    """Player-written text (names, notes, reasons) inside a message: colour codes off, markdown escaped,
    mentions inert, so a note cannot post a link or ping anyone in our channels."""
    t = clean(text, limit)
    return md(t) if t else ""


def profile_link(cfg, name: str) -> str:
    return "%s/u/%s" % (cfg.site, urllib.parse.quote(str(name or ""), safe=""))


def _arrow(now: float, before: float) -> str:
    if now > before:
        return " \N{UPWARDS BLACK ARROW}"
    if now < before:
        return " \N{DOWNWARDS BLACK ARROW}"
    return ""


def weekly_embed(cfg, name: str, stats_id: str, w: dict) -> discord.Embed:
    """The private weekly report: this week in numbers, against the week before."""
    this, before = w.get("week") or {}, w.get("before") or {}
    e = discord.Embed(title="Your week on the front, %s" % clean(name), colour=embeds.RED,
                      url="%s/player?id=%s" % (cfg.site, stats_id))
    wins, matches = this.get("wins", 0), this.get("matches", 0)
    e.description = "**%d** match%s, **%d** won." % (matches, "" if matches == 1 else "es", wins)
    rating = int(this.get("rating") or 0)
    e.add_field(name="Kills", value="%d%s" % (this.get("kills", 0), _arrow(this.get("kills", 0), before.get("kills", 0))))
    e.add_field(name="K/D", value="%.2f%s" % (this.get("kd", 0), _arrow(this.get("kd", 0), before.get("kd", 0))))
    e.add_field(name="Rating", value=("%+d" % rating) if rating else "±0")
    e.add_field(name="Headshots", value=str(this.get("headshots", 0)))
    e.add_field(name="XP", value="+%d" % this.get("xp", 0))
    e.add_field(name="Time played", value="%d min" % round((this.get("timePlayed") or 0) / 60))
    best = w.get("best")
    if best:
        e.add_field(name="Best match", inline=False, value="[%d kills, %d deaths%s](%s/match?id=%s)" % (
            best.get("kills", 0), best.get("deaths", 0), ", won" if best.get("won") else "", cfg.site, best.get("id", "")))
    medals = w.get("newMedals") or []
    if medals:
        e.add_field(name="New medals", inline=False, value=", ".join("**%s**" % m["name"] for m in medals[:10]))
    e.set_footer(text="Turn this report off on truecombat.eu/account")
    return e


def lfs_embed(cfg, players: list[dict]) -> discord.Embed:
    e = discord.Embed(title="Looking for a squad", colour=embeds.GREEN, url=cfg.site + "/account")
    if not players:
        e.description = ("Nobody right now. Want to team up? Turn on **Looking for a squad** on your "
                         "[account page](%s/account) and you show up here." % cfg.site)
    else:
        lines = []
        for p in players[:20]:
            line = "**[%s](%s)**" % (safe(p.get("name")), profile_link(cfg, p.get("name", "")))
            if p.get("note"):
                line += " · %s" % safe(p["note"], 60)
            line += " · until <t:%d:t>" % int(p.get("until") or 0)
            lines.append(line)
        e.description = "\n".join(lines)
    e.set_footer(text="Updated every few minutes · truecombat.eu/account")
    e.timestamp = dt.datetime.now(dt.timezone.utc)
    return e


class Accounts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.lfs_loop.change_interval(minutes=max(1, int(self.cfg["accounts"]["lfs_refresh_minutes"])))

    @property
    def api(self):
        return getattr(self.bot, "accounts", None)

    def ready(self) -> bool:
        return self.api is not None and self.api.ready

    async def cog_load(self):
        if self.ready():
            self.weekly_loop.start()
            if self.cfg.channel("lfs"):
                self.lfs_loop.start()

    async def cog_unload(self):
        self.weekly_loop.cancel()
        self.lfs_loop.cancel()

    # ------------------------------------------------------------ weekly report
    @tasks.loop(minutes=10)
    async def weekly_loop(self):
        try:
            await self.check_weekly(dt.datetime.now(dt.timezone.utc))
        except (AccountsUnavailable, StatsUnavailable):
            pass
        except Exception:  # noqa: BLE001
            log.exception("weekly report failed")

    @weekly_loop.before_loop
    async def _ready_weekly(self):
        await self.bot.wait_until_ready()

    async def check_weekly(self, now: dt.datetime) -> int:
        """Sends the weekly reports once per ISO week; returns how many were sent."""
        wc = self.cfg["accounts"]["weekly"]
        if not wc["enabled"]:
            return 0
        local = now.astimezone(ZoneInfo(self.cfg["timezone"]))
        week = "%d-W%02d" % local.isocalendar()[:2]
        if local.weekday() != int(wc["weekday"]) or local.hour < int(wc["hour"]) or self.bot.store.get("weekly_week") == week:
            return 0
        people = await self.api.weekly()
        self.bot.store.set("weekly_week", week)       # once a week, even if some DMs fail
        sent = 0
        for p in people:
            try:
                w = await self.bot.stats.week(p["statsId"])
            except StatsUnavailable:
                continue
            if not w or not (w.get("week") or {}).get("matches"):
                continue                                   # nothing played: no message
            user = self.bot.get_user(int(p["discordId"]))
            if user is None:
                try:
                    user = await self.bot.fetch_user(int(p["discordId"]))
                except discord.HTTPException:
                    continue
            try:
                await user.send(embed=weekly_embed(self.cfg, p.get("name", ""), p["statsId"], w))
                sent += 1
            except discord.HTTPException:
                pass                                       # DMs closed
            await asyncio.sleep(1)
        log.info("weekly report: %d sent to %d opted-in players", sent, len(people))
        return sent

    # ------------------------------------------------------------ looking for a squad
    @tasks.loop(minutes=2)
    async def lfs_loop(self):
        try:
            await self.refresh_lfs()
        except AccountsUnavailable:
            pass
        except Exception:  # noqa: BLE001
            log.exception("looking-for-a-squad board failed")

    @lfs_loop.before_loop
    async def _ready_lfs(self):
        await self.bot.wait_until_ready()

    async def refresh_lfs(self) -> None:
        ch = self.bot.text_channel(self.cfg.channel("lfs"))
        if ch is None:
            return
        players = await self.api.lfs()
        e = lfs_embed(self.cfg, players)
        key = "lfs_board"
        names = ",".join(sorted(p.get("name", "") + ":" + str(p.get("until")) for p in players))
        saved = self.bot.store.get(key) or {}
        if saved.get("channel") == ch.id and saved.get("message"):
            if saved.get("names") == names:
                return
            try:
                await ch.get_partial_message(int(saved["message"])).edit(embed=e)
                self.bot.store.set(key, dict(saved, names=names))
                return
            except discord.NotFound:
                pass
        m = await ch.send(embed=e)
        self.bot.store.set(key, {"channel": ch.id, "message": m.id, "names": names})

    # ------------------------------------------------------------ staff
    group = app_commands.Group(name="account", description="Player accounts (staff)",
                               default_permissions=discord.Permissions(ban_members=True))

    def _need(self):
        if not self.ready():
            raise UserFacingError("The account service is not connected to the bot yet.")

    @group.command(name="lookup", description="Show a member's player account")
    @app_commands.describe(member="Discord member")
    @staff_only()
    async def lookup(self, interaction: discord.Interaction, member: discord.User):
        self._need()
        await interaction.response.defer(ephemeral=True)
        try:
            a = await self.api.lookup(member.id)
        except AccountsUnavailable as e:
            raise UserFacingError("The account service did not answer: %s" % e) from e
        if not a:
            await interaction.followup.send(embed=embeds.notice("No account", "%s has no player account." % member.mention),
                                            ephemeral=True)
            return
        e = discord.Embed(title=clean(a.get("name")), colour=embeds.STEEL, url=profile_link(self.cfg, a.get("name", "")))
        e.add_field(name="Stats id", value="`%s`" % a.get("statsId", ""))
        e.add_field(name="Profile", value=str(a.get("visibility", "")))
        if isinstance(a.get("created"), int):
            e.add_field(name="Created", value="<t:%d:D>" % a["created"])
        keys = [k for k in a.get("keys") or [] if not k.get("retired")]
        e.add_field(name="Linked PCs", value=", ".join(safe(k.get("label") or "PC") for k in keys) or "None")
        e.add_field(name="Badges", value=", ".join(a.get("badges") or []) or "None")
        sanctions = a.get("sanctions") or []
        e.add_field(name="Banned" if a.get("banned") else "Sanctions", inline=False,
                    value="\n".join("`#%d` %s · %s" % (x["id"], x["kind"], safe(x.get("reason") or "", 80)) for x in sanctions[:5])
                    or "None")
        await interaction.followup.send(embed=e, ephemeral=True)

    @group.command(name="ban", description="Ban a member's account and every PC it has linked")
    @app_commands.describe(member="Discord member", reason="Kept with the ban; shown to the player",
                           days="0 = permanent", kind="ban, or warning (no effect, counts against the clean record)")
    @app_commands.choices(kind=[app_commands.Choice(name="Ban", value="ban"),
                                app_commands.Choice(name="Warning", value="warning")])
    @staff_only()
    async def ban(self, interaction: discord.Interaction, member: discord.User,
                  reason: app_commands.Range[str, 3, 300], days: app_commands.Range[int, 0, 3650] = 0,
                  kind: str = "ban"):
        self._need()
        await interaction.response.defer(ephemeral=True)
        try:
            r = await self.api.ban(discord_id=member.id, kind=kind, reason=reason, days=days,
                                   by="%s (%d)" % (interaction.user.name, interaction.user.id))
        except AccountsUnavailable as e:
            raise UserFacingError("Not done: %s" % e) from e
        what = "Banned" if kind == "ban" else "Warned"
        if kind == "ban":
            span = "for %d day%s" % (days, "" if days == 1 else "s") if days else "permanently"
            text = "Banned **%s** %s (#%d). It covers %d PC%s, and any PC linked later." % (
                safe(r.get("account")), span, r.get("ban", 0), r.get("keys", 0), "" if r.get("keys") == 1 else "s")
        else:
            text = "Warned **%s** (#%d). The clean-record badge is off for 90 days." % (safe(r.get("account")), r.get("ban", 0))
        await interaction.followup.send(embed=embeds.notice("Account %s" % what.lower(), text), ephemeral=True)
        staff = self.bot.text_channel(self.cfg.channel("staff"))
        if staff:
            try:
                await staff.send(embed=embeds.notice("Account %s" % what.lower(), "%s by %s. Reason: %s" % (
                    text, interaction.user.mention, reason.replace("@", "@​"))))
            except discord.HTTPException:
                pass

    @group.command(name="unban", description="Lift an account ban by its number")
    @app_commands.describe(ban="The ban number from /account bans")
    @staff_only()
    async def unban(self, interaction: discord.Interaction, ban: app_commands.Range[int, 1, 10_000_000]):
        self._need()
        await interaction.response.defer(ephemeral=True)
        try:
            await self.api.unban(ban)
        except AccountsUnavailable as e:
            raise UserFacingError("Not done: %s" % e) from e
        await interaction.followup.send(embed=embeds.notice("Ban lifted", "Ban #%d is lifted." % ban), ephemeral=True)

    @group.command(name="bans", description="The latest account bans and warnings")
    @staff_only()
    async def bans(self, interaction: discord.Interaction):
        self._need()
        await interaction.response.defer(ephemeral=True)
        try:
            rows = await self.api.bans()
        except AccountsUnavailable as e:
            raise UserFacingError("The account service did not answer: %s" % e) from e
        lines = []
        for b in rows[:15]:
            state = "lifted" if b.get("lifted") else ("until <t:%d:d>" % b["until"] if b.get("until") else "permanent")
            lines.append("`#%d` %s **%s** · %s · %s" % (b["id"], b.get("kind", "ban"), safe(b.get("account") or "deleted account"),
                                                       state, safe(b.get("reason") or "", 80)))
        await interaction.followup.send(embed=embeds.notice("Account bans", "\n".join(lines) or "None."), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Accounts(bot))
