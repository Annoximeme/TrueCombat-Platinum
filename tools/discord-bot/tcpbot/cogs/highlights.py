"""Match reports, achievements, the weekly recap and seasons.

Everything here is driven by the stats service. Match details, the recap and
season windows need its newer endpoints (/match.json, /recap.json and
since/until on the leaderboard). On an older service the match report falls
back to the short form and the rest stays quiet instead of failing.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import achievements as A
from .. import embeds
from ..bot import UserFacingError
from ..sources import StatsUnavailable

log = logging.getLogger("tcpbot.highlights")
SEEN_LIMIT = 300
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")


def _iso(d: dt.datetime) -> str:
    return d.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def season_window(now: dt.datetime, length: str = "month", tz: str = "Europe/Brussels") -> dict:
    """The calendar season `now` falls in: key, display name and its UTC bounds."""
    local = now.astimezone(ZoneInfo(tz))
    if length == "quarter":
        q = (local.month - 1) // 3
        start = local.replace(month=q * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        y, mo = (start.year + 1, 1) if q == 3 else (start.year, q * 3 + 4)
        key, name = "%dQ%d" % (start.year, q + 1), "Season %d · Q%d" % (start.year, q + 1)
    else:
        start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        y, mo = (start.year + 1, 1) if start.month == 12 else (start.year, start.month + 1)
        key, name = "%d-%02d" % (start.year, start.month), "%s %d season" % (MONTHS[start.month - 1], start.year)
    end = dt.datetime(y, mo, 1, tzinfo=ZoneInfo(tz))
    return {"key": key, "name": name, "since": _iso(start), "until": _iso(end), "end_ts": int(end.timestamp())}


def match_key(row: dict) -> str:
    if row.get("id"):
        return str(row["id"])
    return "%s|%s|%s" % (row.get("server", ""), row.get("ended", ""), row.get("map", ""))


class Highlights(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.watch.start()
        self.calendar.start()

    def cog_unload(self):
        self.watch.cancel()
        self.calendar.cancel()

    def channel(self):
        cid = self.cfg.channel("matches", "feed") or self.cfg.channel("status")
        return self.bot.text_channel(cid)

    # ------------------------------------------------------------ match reports
    @tasks.loop(seconds=60)
    async def watch(self):
        try:
            await self.check_matches()
        except StatsUnavailable:
            pass
        except Exception:  # noqa: BLE001
            log.exception("match watch failed")

    @watch.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()

    async def check_matches(self):
        data = await self.bot.stats.recent(fresh=True)
        rows = (data or {}).get("matches") or []
        seen = self.bot.store.get("matches_seen")
        keys = [match_key(r) for r in rows]
        if seen is None:                       # first run: everything already played is old news
            self.bot.store.set("matches_seen", keys[:SEEN_LIMIT])
            return
        new = [r for r in reversed(rows) if match_key(r) not in seen]     # oldest first
        for row in new:
            try:
                await self.handle_match(row)
            finally:
                seen = ([match_key(row)] + seen)[:SEEN_LIMIT]
                self.bot.store.set("matches_seen", seen)

    async def handle_match(self, row: dict):
        detail = None
        if row.get("id"):
            detail = await self.bot.stats.match(row["id"])
        unlocked = await self.award(detail) if detail and self.cfg["achievements"]["enabled"] else []
        mr = self.cfg["match_reports"]
        count = len((detail or {}).get("players") or []) or int(row.get("players") or 0)
        wanted = [s.lower() for s in mr["servers"]]
        if not mr["enabled"] or count < int(mr["min_players"]) or (
                wanted and str(row.get("server") or "").lower() not in wanted):
            return
        ch = self.channel()
        if ch is None:
            return
        mentions = {}
        for p in (detail or {}).get("players") or []:
            link = self.bot.store.linked_member(p["id"])
            if link:
                mentions[p["id"]] = link["discord_id"]
        await ch.send(embed=embeds.match_report(self.cfg, row, detail, unlocked, mentions))

    async def award(self, detail: dict) -> list[tuple[str, str]]:
        """Unlocks what this match earned. Returns [(name, key)] worth announcing."""
        out = []
        board = detail.get("players") or []
        for row in board:
            pid = row.get("id")
            if not pid:
                continue
            try:
                p = await self.bot.stats.player(pid, fresh=True)
            except StatsUnavailable:
                continue
            have = self.bot.store.achievements(pid)
            earned = (A.career(p) if p else []) + A.in_match(row, board)
            new = [k for k in dict.fromkeys(earned) if k not in have]
            if not new:
                continue
            self.bot.store.unlock(pid, new)
            # A player the bot meets for the first time already has a history: their career
            # milestones are recorded quietly, only what this match earned is announced.
            backfill = not have and p and (p.get("matches") or 0) > 1
            for k in A.best_first(new):
                if backfill and k in A.CAREER:
                    continue
                out.append((row.get("name") or "Player", k))
        return sorted(out, key=lambda x: -A.ALL[x[1]][2])

    # ------------------------------------------------------------ weekly recap and seasons
    @tasks.loop(minutes=10)
    async def calendar(self):
        now = dt.datetime.now(dt.timezone.utc)
        for job in (self.check_recap, self.check_season):
            try:
                await job(now)
            except StatsUnavailable:
                pass
            except Exception:  # noqa: BLE001
                log.exception("%s failed", job.__name__)

    @calendar.before_loop
    async def _ready2(self):
        await self.bot.wait_until_ready()

    async def check_recap(self, now: dt.datetime):
        rc = self.cfg["recap"]
        if not rc["enabled"]:
            return
        local = now.astimezone(ZoneInfo(self.cfg["timezone"]))
        week = "%d-W%02d" % local.isocalendar()[:2]
        if local.weekday() != int(rc["weekday"]) or local.hour < int(rc["hour"]) or \
                self.bot.store.get("recap_week") == week:
            return
        data = await self.bot.stats.recap(7)
        if data is None:
            return                               # older stats service: try again later
        self.bot.store.set("recap_week", week)
        ch = self.channel()
        if ch and data.get("matches", 0) >= int(rc["min_matches"]):
            await ch.send(embed=embeds.weekly_recap(self.cfg, data))

    def season(self, now: dt.datetime | None = None) -> dict:
        return season_window(now or dt.datetime.now(dt.timezone.utc), self.cfg["seasons"]["length"], self.cfg["timezone"])

    async def season_standings(self, season: dict, fresh=False) -> dict:
        board = await self.bot.stats.leaderboard("season", "all", int(self.cfg["seasons"]["top"]), fresh=fresh,
                                                 since=season["since"], until=season["until"])
        if not board or not board.get("since"):
            raise UserFacingError("Season standings arrive with the next update of the stats service. "
                                  "`/top` has the all-time board in the meantime.")
        return board

    async def check_season(self, now: dt.datetime):
        if not self.cfg["seasons"]["enabled"]:
            return
        cur = self.season(now)
        prev = self.bot.store.get("season")
        if prev is None or prev["key"] == cur["key"]:
            if prev is None:
                self.bot.store.set("season", cur)
            return
        try:
            board = await self.season_standings(prev, fresh=True)
        except UserFacingError:
            self.bot.store.set("season", cur)
            return
        self.bot.store.set("season", cur)
        players = [p for p in board.get("players") or [] if p.get("periodXp")]
        champion = None
        if players:
            top = players[0]
            self.bot.store.unlock(top["id"], [A.SEASON_KEY])
            link = self.bot.store.linked_member(top["id"])
            champion = link["discord_id"] if link else None
            await self.crown(champion)
        self.bot.store.doc_add("season", {"key": prev["key"], "name": prev["name"], "top": [
            {"id": p["id"], "name": p["name"], "xp": p["periodXp"], "wins": p.get("wins", 0)} for p in players[:10]]},
            state="closed")
        ch = self.bot.text_channel(self.cfg.channel("announcements", "matches")) or self.channel()
        if ch and players:
            await ch.send(embed=embeds.season_board(self.cfg, board, prev, final=True, champion=champion))

    async def crown(self, member_id: int | None):
        """The Season champion role moves to the new winner."""
        role, guild = self.bot.role("champion"), self.bot.guild
        if role is None or guild is None or not self.cfg["seasons"]["champion_role"]:
            return
        try:
            for m in list(role.members):
                if m.id != member_id:
                    await m.remove_roles(role, reason="A new season champion was crowned")
            m = guild.get_member(member_id) if member_id else None
            if m and role not in m.roles:
                await m.add_roles(role, reason="Season champion")
        except discord.HTTPException as e:
            log.warning("champion role: %s", e)

    # ------------------------------------------------------------ commands
    @app_commands.command(name="season", description="This season's standings and when it ends")
    @app_commands.checks.cooldown(3, 15.0)
    async def cmd_season(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        season = self.season()
        board = await self.season_standings(season)
        await interaction.followup.send(embed=embeds.season_board(self.cfg, board, season))

    @app_commands.command(name="recap", description="What happened on the servers in the last seven days")
    @app_commands.checks.cooldown(2, 30.0)
    async def cmd_recap(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        data = await self.bot.stats.recap(7)
        if data is None:
            raise UserFacingError("The weekly recap arrives with the next update of the stats service.")
        await interaction.followup.send(embed=embeds.weekly_recap(self.cfg, data))

    async def _players(self, interaction, current):
        stats = self.bot.get_cog("Stats")
        return await stats.player_autocomplete(interaction, current) if stats else []

    @app_commands.command(name="achievements", description="A player's achievements and what to go for next")
    @app_commands.describe(player="Player name (start typing to search)", member="A Discord member with a linked profile")
    @app_commands.autocomplete(player=_players)
    @app_commands.checks.cooldown(3, 15.0)
    async def cmd_achievements(self, interaction: discord.Interaction, player: str | None = None,
                               member: discord.Member | None = None):
        await interaction.response.defer(thinking=True)
        p = await self.bot.get_cog("Stats").resolve(interaction, player, member)
        have = self.bot.store.achievements(p["id"])
        missing = [k for k in A.career(p) if k not in have]
        if missing:                              # catch up on anything earned before the bot was watching
            self.bot.store.unlock(p["id"], missing)
            have = self.bot.store.achievements(p["id"])
        await interaction.followup.send(embed=embeds.achievements_card(self.cfg, p, have))


async def setup(bot):
    await bot.add_cog(Highlights(bot))
