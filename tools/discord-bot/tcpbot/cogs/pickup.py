"""Pickup (PUG) queue for competitive matches.

Flow: players join the queue (button or /pickup join). When it holds two full
teams, the bot runs a ready check (Accept / Decline, 60 s). When everyone
accepts it balances the teams on skill rating, claims a free match server,
sets a fresh password and competitive match mode over rcon (127.0.0.1 only),
and sends each player their team and join details. When the server empties
after the match it posts the result and returns the server to the pool.

Design: /mnt/project-files/online-play/PICKUP-QUEUE.md. Match mode commands:
competitive/MATCH-MODE.md (match on, match name r|b, ...).
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import embeds
from .. import text as T
from ..bot import UserFacingError, staff_only
from ..rcon import RconError, safe_arg, server_rcon
from ..sources import StatsUnavailable, is_bot, query_game
from ..teams import balance, fill_unrated, password

log = logging.getLogger("tcpbot.pickup")
KEY = "pickup"


def _blank() -> dict:
    return {"queue": [], "check": None, "matches": {}, "next_id": 1, "queue_message": 0, "last_map": ""}


def _mentions(ids) -> str:
    return " ".join("<@%d>" % u for u in ids) or "—"


# ================================================================ buttons
class PickupButton(discord.ui.DynamicItem[discord.ui.Button],
                   template=r"tcp:pug:(?P<action>join|leave|accept|decline|details)(?::(?P<ref>\d+))?"):
    STYLES = {"join": ("Join queue", discord.ButtonStyle.success),
              "leave": ("Leave", discord.ButtonStyle.secondary),
              "accept": ("Accept", discord.ButtonStyle.success),
              "decline": ("Decline", discord.ButtonStyle.danger),
              "details": ("Join details", discord.ButtonStyle.primary)}

    def __init__(self, action: str, ref: int = 0):
        label, style = self.STYLES[action]
        cid = "tcp:pug:%s" % action + (":%d" % ref if ref else "")
        super().__init__(discord.ui.Button(label=label, style=style, custom_id=cid))
        self.action, self.ref = action, ref

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(match["action"], int(match["ref"] or 0))

    async def callback(self, interaction: discord.Interaction):
        cog: Pickup = interaction.client.get_cog("Pickup")
        try:
            text = await getattr(cog, "on_" + self.action)(interaction.user, self.ref)
        except UserFacingError as e:
            text = str(e)
        if isinstance(text, discord.Embed):
            await interaction.response.send_message(embed=text, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embeds.notice("Pickup", text), ephemeral=True)


def view_of(*items) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for action, ref in items:
        v.add_item(PickupButton(action, ref))
    return v


# ================================================================ cog
class Pickup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.pc = self.cfg["pickup"]
        self.lock = asyncio.Lock()
        self.rng = random.Random()
        self.last_scan = 0.0

    async def cog_load(self):
        self.bot.add_dynamic_items(PickupButton)
        if self.pc["enabled"] or self.pc["servers"]:     # team matches use the match servers too
            self.tick.start()

    async def cog_unload(self):
        self.tick.cancel()

    # ------------------------------------------------------------ state
    @property
    def size(self) -> int:
        return int(self.pc["team_size"]) * 2

    def state(self) -> dict:
        st = self.bot.store.get(KEY) or _blank()
        for k, v in _blank().items():
            st.setdefault(k, v)
        return st

    def save(self, st: dict):
        self.bot.store.set(KEY, st)

    def channel(self):
        return self.bot.text_channel(int(self.pc.get("channel") or 0))

    def player_match(self, st: dict, uid: int):
        return next((m for m in st["matches"].values() if uid in m["players"]), None)

    # ------------------------------------------------------------ player actions
    async def on_join(self, user, _ref=0) -> str:
        if not self.pc["enabled"]:
            raise UserFacingError("The pickup queue isn't open yet.")
        if self.pc.get("require_link") and not self.bot.store.linked_player(user.id):
            raise UserFacingError("Link your game profile with `/link` first, so teams can be balanced on your rating.")
        async with self.lock:
            st = self.state()
            if self.player_match(st, user.id):
                raise UserFacingError("You're in a match right now. Finish it first.")
            if st["check"] and user.id in st["check"]["players"]:
                raise UserFacingError("Your match is being confirmed: press **Accept** on the ready check.")
            if any(u == user.id for u, _ in st["queue"]):
                return "You're already in the queue (%d/%d)." % (len(st["queue"]), self.size)
            st["queue"].append([user.id, int(time.time())])
            self.save(st)
            n = len(st["queue"])
        await self.after_change()
        if n >= self.size:
            return "You're in. The queue is full, check the ready check."
        return "You're in the queue (%d/%d). You'll be pinged when the match is ready." % (n, self.size)

    async def on_leave(self, user, _ref=0) -> str:
        async with self.lock:
            st = self.state()
            before = len(st["queue"])
            st["queue"] = [q for q in st["queue"] if q[0] != user.id]
            left = len(st["queue"]) < before
            self.save(st)
            in_check = bool(st["check"] and user.id in st["check"]["players"])
        if in_check:
            return await self.on_decline(user, st["check"]["id"])
        await self.after_change()
        return "You left the queue." if left else "You weren't in the queue."

    async def on_accept(self, user, ref) -> str:
        async with self.lock:
            st = self.state()
            chk = st["check"]
            if not chk or chk["id"] != ref or user.id not in chk["players"]:
                raise UserFacingError("This ready check isn't yours or has already closed.")
            if user.id in chk["accepted"]:
                return "Already accepted. Waiting for the others."
            chk["accepted"].append(user.id)
            self.save(st)
            done = set(chk["accepted"]) == set(chk["players"])
        await self.refresh_check()
        if done:
            asyncio.create_task(self.launch())
            return "Accepted. Everyone's in, setting up the server."
        return "Accepted. Waiting for %d more." % (len(chk["players"]) - len(chk["accepted"]))

    async def on_decline(self, user, ref) -> str:
        async with self.lock:
            st = self.state()
            chk = st["check"]
            if not chk or chk["id"] != ref or user.id not in chk["players"]:
                raise UserFacingError("This ready check isn't yours or has already closed.")
        await self.cancel_check([user.id], "%s declined" % self._name(user.id))
        return "You declined and left the queue."

    async def on_details(self, user, ref) -> discord.Embed:
        st = self.state()
        m = st["matches"].get(str(ref))
        if not m or user.id not in m["players"]:
            raise UserFacingError("These join details are only for the players in this match.")
        return self.details_embed(m, user.id)

    # ------------------------------------------------------------ queue message
    def queue_embed(self, st: dict) -> discord.Embed:
        ts = int(self.pc["team_size"])
        e = discord.Embed(title="Pickup queue · %dv%d %s" % (ts, ts, self.pc["mode_name"]), colour=embeds.RED)
        q = [u for u, _ in st["queue"]]
        e.description = "**%d / %d** in the queue\n%s" % (len(q), self.size, _mentions(q))
        live = [m for m in st["matches"].values()]
        if live:
            e.add_field(name="Matches in progress", value="\n".join(
                "%s on %s · started <t:%d:R>" % (T.map_label(m["map"]), m["server"], m["started"]) for m in live),
                inline=False)
        e.set_footer(text="Teams are balanced on skill rating. You leave the queue after %d minutes."
                          % int(self.pc["queue_minutes"]))
        return e

    async def after_change(self):
        await self.update_queue_message()
        await self.maybe_start_check()

    async def update_queue_message(self):
        ch = self.channel()
        if ch is None or not self.pc["enabled"]:
            return
        st = self.state()
        e = self.queue_embed(st)
        v = view_of(("join", 0), ("leave", 0))
        if st["queue_message"]:
            try:
                await ch.get_partial_message(st["queue_message"]).edit(embed=e, view=v)
                return
            except discord.NotFound:
                pass
            except discord.HTTPException as ex:
                log.warning("queue message: %s", ex)
                return
        msg = await ch.send(embed=e, view=v)
        st = self.state()
        st["queue_message"] = msg.id
        self.save(st)

    # ------------------------------------------------------------ ready check
    async def maybe_start_check(self):
        async with self.lock:
            st = self.state()
            if st["check"] or len(st["queue"]) < self.size:
                return
            players = [u for u, _ in st["queue"][: self.size]]
            st["queue"] = st["queue"][self.size:]
            chk = {"id": st["next_id"], "players": players, "accepted": [], "message": 0,
                   "deadline": int(time.time()) + int(self.pc["accept_seconds"]), "state": "check"}
            st["next_id"] += 1
            st["check"] = chk
            self.save(st)
        ch = self.channel()
        if ch:
            msg = await ch.send(content=_mentions(players), embed=self.check_embed(chk),
                                view=view_of(("accept", chk["id"]), ("decline", chk["id"])),
                                allowed_mentions=discord.AllowedMentions(users=[discord.Object(u) for u in players]))
            async with self.lock:
                st = self.state()
                if st["check"] and st["check"]["id"] == chk["id"]:
                    st["check"]["message"] = msg.id
                    self.save(st)
        await self.update_queue_message()

    def check_embed(self, chk: dict) -> discord.Embed:
        e = discord.Embed(title="Match ready", colour=embeds.AMBER)
        if chk.get("state") == "waiting":
            e.description = ("Everyone accepted. All match servers are busy right now, so you're first in line. "
                             "I'll set you up the moment one frees up.")
        else:
            e.description = "Press **Accept** <t:%d:R>. Anyone who doesn't is dropped and the rest stay queued." % (
                chk["deadline"])
        rows = ["%s %s" % ("✅" if u in chk["accepted"] else "⏳", "<@%d>" % u) for u in chk["players"]]
        e.add_field(name="Players (%d/%d accepted)" % (len(chk["accepted"]), len(chk["players"])),
                    value="\n".join(rows), inline=False)
        return e

    async def refresh_check(self):
        st = self.state()
        chk, ch = st["check"], self.channel()
        if not chk or not ch or not chk["message"]:
            return
        try:
            await ch.get_partial_message(chk["message"]).edit(embed=self.check_embed(chk))
        except discord.HTTPException:
            pass

    async def cancel_check(self, dropped: list[int], reason: str):
        """Close the ready check: accepted players go back to the front of the queue."""
        async with self.lock:
            st = self.state()
            chk = st["check"]
            if not chk:
                return
            keep = [u for u in chk["players"] if u in chk["accepted"] and u not in dropped]
            now = int(time.time())
            st["queue"] = [[u, now] for u in keep] + [q for q in st["queue"] if q[0] not in keep]
            st["check"] = None
            self.save(st)
        ch = self.channel()
        if ch and chk["message"]:
            e = discord.Embed(title="Match cancelled", colour=embeds.STEEL,
                              description="%s. %s back at the front of the queue." % (
                                  reason, "Everyone who accepted is" if keep else "Nobody is"))
            try:
                await ch.get_partial_message(chk["message"]).edit(content=None, embed=e, view=None)
            except discord.HTTPException:
                pass
        await self.after_change()

    # ------------------------------------------------------------ launching
    def servers(self) -> list[dict]:
        return list(self.pc["servers"])

    async def rc(self, server: dict, command: str) -> str | None:
        """One rcon command; None when the server didn't answer or refused."""
        try:
            return await server_rcon(server, command)
        except (RconError, OSError) as e:
            log.warning("rcon %s: %s", server.get("key"), e)
            return None

    async def free_server(self, st: dict) -> dict | None:
        busy = {m["server"] for m in st["matches"].values()}
        for s in self.servers():
            if s["key"] in busy:
                continue
            status = await query_game(s["host"], s["port"])
            if status is None:
                continue
            humans = [p for p in status["players"] if not is_bot(p, self.cfg["bot_name_pattern"])]
            if not humans:
                return s
        return None

    async def ratings(self, players: list[int]) -> dict[int, float]:
        raw: dict[int, float | None] = {}
        for u in players:
            link = self.bot.store.linked_player(u)
            r = None
            if link:
                try:
                    p = await self.bot.stats.player(link["pid"])
                    r = float(p["rating"]) if p and p.get("matches") else None
                except StatsUnavailable:
                    r = None
            raw[u] = r
        return fill_unrated(raw)

    def _name(self, uid: int) -> str:
        g = self.bot.guild
        m = g.get_member(uid) if g else None
        if m:
            return m.display_name
        link = self.bot.store.linked_player(uid)
        return link["name"] if link else "Player"

    def team_name(self, team: list[int]) -> str:
        name = T.clean(self._name(team[0]), 20).replace('"', "").replace(";", "")
        return "Team %s" % (name or "One")

    async def launch(self):
        async with self.lock:
            st = self.state()
            chk = st["check"]
            if not chk or set(chk["accepted"]) != set(chk["players"]):
                return
            server = await self.free_server(st)
            if server is None:
                if chk.get("state") != "waiting":
                    chk["state"] = "waiting"
                    self.save(st)
                    asyncio.create_task(self.refresh_check())
                return
            st["check"] = None
            mid = chk["id"]
            ratings = await self.ratings(chk["players"])
            red, blue = balance(ratings, self.rng)
            maps = [m for m in self.pc["maps"] if m != st.get("last_map")] or self.pc["maps"]
            mapname = self.rng.choice(maps)
            match = {"id": mid, "server": server["key"], "address": server["public_address"], "map": mapname,
                     "players": chk["players"], "red": red, "blue": blue, "password": password(),
                     "ratings": {str(k): round(v) for k, v in ratings.items()}, "started": int(time.time()),
                     "seen": False, "empty_checks": 0, "message": 0,
                     "names": [self.team_name(red), self.team_name(blue)]}
            st["matches"][str(mid)] = match
            st["last_map"] = mapname
            self.save(st)

        ok = await self.prepare_server(server, match)
        ch = self.channel()
        if ch and chk["message"]:
            try:
                await ch.get_partial_message(chk["message"]).edit(content=None, embed=discord.Embed(
                    title="Match ready", colour=embeds.GREEN, description="Everyone accepted. Teams are below."),
                    view=None)
            except discord.HTTPException:
                pass
        if not ok:
            await self.finish(str(mid), "The match server didn't respond, so the match was called off. "
                                        "Sorry about that, please queue again.")
            return
        if ch:
            msg = await ch.send(content=_mentions(match["players"]), embed=self.match_embed(match),
                                view=view_of(("details", mid)),
                                allowed_mentions=discord.AllowedMentions(
                                    users=[discord.Object(u) for u in match["players"]]))
            async with self.lock:
                st = self.state()
                if str(mid) in st["matches"]:
                    st["matches"][str(mid)]["message"] = msg.id
                    self.save(st)
        for u in match["players"]:
            user = self.bot.get_user(u)
            if user:
                try:
                    await user.send(embed=self.details_embed(match, u))
                except discord.HTTPException:
                    pass       # DMs closed: the Join details button covers it
        await self.update_queue_message()

    async def prepare_server(self, server: dict, match: dict) -> bool:
        # g_pugTeams 1: each player lands on the team in their tcp_team userinfo (set by the join link
        # or by the console line in the DM), so nobody has to pick a side by hand.
        steps = ['set g_password "%s"' % match["password"], "set g_competitive 1", "set g_pugTeams 1",
                 "set sv_mapRotationTime 0"]
        for cmd in steps:
            if await self.rc(server, cmd) is None:
                return False
        await self.rc(server, "map %s" % safe_arg(match["map"], 40))    # the reply can be lost while the map loads
        await asyncio.sleep(float(self.pc.get("map_load_seconds", 8)))
        for side, name in (("r", match["names"][0]), ("b", match["names"][1])):
            await self.rc(server, 'match name %s "%s"' % (side, safe_arg(name, 24)))
        return await self.rc(server, "match status") is not None

    async def start_custom(self, owner: str, label: str, red: list[int], blue: list[int], names: list[str],
                           channel_id: int = 0, mapname: str | None = None, meta: dict | None = None) -> dict | None:
        """A match between two fixed teams (scrim, tournament) on a free match server.
        Returns the match, or None when every server is busy. The cog named `owner` is told
        the outcome through on_team_match(match, row, detail, note)."""
        async with self.lock:
            st = self.state()
            server = await self.free_server(st)
            if server is None:
                return None
            mid = st["next_id"]
            st["next_id"] += 1
            maps = [m for m in self.pc["maps"] if m != st.get("last_map")] or self.pc["maps"]
            mapname = mapname or self.rng.choice(maps)
            match = {"id": mid, "server": server["key"], "address": server["public_address"], "map": mapname,
                     "players": red + blue, "red": red, "blue": blue, "password": password(), "ratings": {},
                     "started": int(time.time()), "seen": False, "empty_checks": 0, "message": 0,
                     "names": [safe_arg(n, 24) for n in names], "owner": owner, "label": label,
                     "channel": int(channel_id or 0), "meta": meta or {}}
            st["matches"][str(mid)] = match
            st["last_map"] = mapname
            self.save(st)
        if not await self.prepare_server(server, match):
            await self.finish(str(mid), "The match server didn't respond, so the match was called off.")
            return {"failed": True}
        ch = self.bot.text_channel(match["channel"]) or self.channel()
        if ch:
            await ch.send(content=_mentions(match["players"]), embed=self.match_embed(match),
                          view=view_of(("details", mid)), allowed_mentions=discord.AllowedMentions(
                              users=[discord.Object(u) for u in match["players"]]))
        for u in match["players"]:
            user = self.bot.get_user(u)
            if user:
                try:
                    await user.send(embed=self.details_embed(match, u))
                except discord.HTTPException:
                    pass
        return match

    @staticmethod
    def label(m: dict) -> str:
        return m.get("label") or "Pickup #%d" % m["id"]

    def match_embed(self, m: dict) -> discord.Embed:
        e = discord.Embed(title="%s · %s" % (self.label(m), T.map_label(m["map"])), colour=embeds.RED)
        e.description = ("%sJoin details went to each player by DM; "
                         "use the button if yours didn't arrive. Everyone lands on their team automatically; "
                         "type `ready` in warmup and the knife round decides sides." % (
                             "" if m.get("owner") else "Teams are balanced on skill rating. "))
        for idx, team in enumerate((m["red"], m["blue"])):
            if m.get("owner"):
                e.add_field(name=m["names"][idx], value="\n".join("<@%d>" % u for u in team), inline=True)
                continue
            avg = sum(m["ratings"][str(u)] for u in team) / len(team)
            e.add_field(name="%s · avg %s" % (m["names"][idx], T.num(round(avg))),
                        value="\n".join("<@%d>" % u for u in team), inline=True)
        e.set_footer(text="Server %s" % m["server"])
        return e

    def details_embed(self, m: dict, uid: int) -> discord.Embed:
        side = 0 if uid in m["red"] else 1
        mates = m["red"] if side == 0 else m["blue"]
        e = discord.Embed(title="Your match is ready" if m.get("owner") else "Your pickup match is ready",
                          colour=embeds.GREEN)
        team = "r" if side == 0 else "b"
        url = self.join_url(m, uid)
        how = ("[**Join the match**](%s) opens the launcher and puts you straight on your team.\n"
               "Or paste this into the game console (`~`):" % url) if url else "Paste this into the game console (`~`):"
        e.description = (
            "**%s** on **%s**. %s\n```\n/setu tcp_team %s; password %s; connect %s\n```"
            "You'll join the **%s** side. Type `ready` in warmup; the knife round decides who attacks." % (
                m["names"][side], T.map_label(m["map"]), how, team, m["password"], m["address"],
                "Red" if side == 0 else "Blue"))
        e.add_field(name="Your team", value="\n".join("<@%d>" % u for u in mates), inline=True)
        e.set_footer(text="Keep the password to yourself. It changes for every match.")
        return e

    def join_url(self, m: dict, uid: int) -> str:
        base = (self.pc.get("join_url") or "").strip()
        if not base:
            return ""
        team = "r" if uid in m["red"] else "b"
        return "%s#%s?pw=%s&team=%s" % (base, m["address"], m["password"], team)

    # ------------------------------------------------------------ finishing
    async def finish(self, mid: str, note: str | None = None):
        async with self.lock:
            st = self.state()
            m = st["matches"].pop(mid, None)
            self.save(st)
        if not m:
            return
        server = next((s for s in self.servers() if s["key"] == m["server"]), None)
        if server:
            await self.rc(server, 'set g_password "%s"' % password())     # lock the server until the next match
        owner = self.bot.get_cog(m["owner"]) if m.get("owner") else None
        if owner is not None:
            row = None if note else await self.find_result(m)
            detail = None
            if row and row.get("id"):
                try:
                    detail = await self.bot.stats.match(row["id"])
                except StatsUnavailable:
                    detail = None
            try:
                await owner.on_team_match(m, row, detail, note)
            except Exception:  # noqa: BLE001
                log.exception("%s could not close match %s", m["owner"], m["id"])
        else:
            ch = self.channel()
            if ch:
                e = note and embeds.notice("Pickup #%d" % m["id"], note, embeds.STEEL) or await self.result_embed(m)
                await ch.send(embed=e)
        await self.update_queue_message()
        await self.launch()       # a group may be waiting for this server

    async def find_result(self, m: dict) -> dict | None:
        """The stats service's record of this match, if it has arrived."""
        try:
            recent = (await self.bot.stats.recent(fresh=True)) or {}
        except StatsUnavailable:
            return None
        server = next((s for s in self.servers() if s["key"] == m["server"]), {})
        want = server.get("stats_name") or self.pc.get("stats_server") or ""
        for r in recent.get("matches", []):
            ended = T.iso_to_unix(r.get("ended")) or 0
            if r.get("map") == m["map"] and ended >= m["started"] and (not want or r.get("server") == want):
                return r
        return None

    async def result_embed(self, m: dict) -> discord.Embed:
        e = discord.Embed(title="Pickup #%d finished · %s" % (m["id"], T.map_label(m["map"])), colour=embeds.GOLD,
                          url=self.cfg.site + "/leaderboards.html")
        found = await self.find_result(m)
        if found:
            parts = ["%d rounds" % found.get("rounds", 0), T.duration(found.get("duration"))]
            if found.get("mvp"):
                parts.append("MVP **%s** with %d kills" % (T.md(found["mvp"]["name"]), found["mvp"]["kills"]))
            e.description = " · ".join(parts)
        else:
            e.description = "The match report hasn't reached the leaderboard yet."
        changes = []
        for u in m["players"]:
            link = self.bot.store.linked_player(u)
            if not link:
                continue
            try:
                p = await self.bot.stats.player(link["pid"], fresh=True)
            except StatsUnavailable:
                break
            last = (p or {}).get("recent") or []
            if last and (T.iso_to_unix(last[0].get("ended")) or 0) >= m["started"]:
                changes.append("<@%d> %s" % (u, T.signed(last[0]["ratingChange"])))
        if changes:
            e.add_field(name="Rating changes", value="\n".join(changes)[:1024], inline=False)
        return e

    # ------------------------------------------------------------ background
    @tasks.loop(seconds=10)
    async def tick(self):
        try:
            await self.housekeeping()
        except Exception:  # noqa: BLE001
            log.exception("pickup tick failed")

    @tick.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        await self.update_queue_message()

    async def housekeeping(self):
        now = int(time.time())
        st = self.state()
        # queue expiry
        limit = int(self.pc["queue_minutes"]) * 60
        if any(now - t > limit for _, t in st["queue"]):
            async with self.lock:
                st = self.state()
                st["queue"] = [q for q in st["queue"] if now - q[1] <= limit]
                self.save(st)
            await self.update_queue_message()
        # ready check deadline / waiting for a server
        chk = st["check"]
        if chk and chk.get("state") == "waiting":
            await self.launch()
        elif chk and now > chk["deadline"]:
            missing = [u for u in chk["players"] if u not in chk["accepted"]]
            await self.cancel_check(missing, "%s didn't accept in time" % ", ".join(
                self._name(u) for u in missing) if missing else "Time ran out")
        # live matches: every 30 s
        if now - self.last_scan < 29:
            return
        self.last_scan = now
        for mid, m in list(st["matches"].items()):
            server = next((s for s in self.servers() if s["key"] == m["server"]), None)
            if server is None:
                await self.finish(mid, "The match server was removed from the config.")
                continue
            status = await query_game(server["host"], server["port"])
            humans = len([p for p in (status or {}).get("players", [])
                          if not is_bot(p, self.cfg["bot_name_pattern"])])
            age = now - m["started"]
            if humans:
                m["seen"], m["empty_checks"] = True, 0
            else:
                m["empty_checks"] += 1
            async with self.lock:
                cur = self.state()
                if mid in cur["matches"]:
                    cur["matches"][mid].update(seen=m["seen"], empty_checks=m["empty_checks"])
                    self.save(cur)
            if m["seen"] and m["empty_checks"] >= 2:
                await asyncio.sleep(5)        # give the stats upload a moment
                await self.finish(mid)
            elif not m["seen"] and age > int(self.pc["join_minutes"]) * 60:
                await self.finish(mid, "Nobody joined the server within %d minutes, so the match was called off."
                                  % int(self.pc["join_minutes"]))
            elif age > int(self.pc["max_minutes"]) * 60:
                await self.finish(mid)

    # ------------------------------------------------------------ slash commands
    group = app_commands.Group(name="pickup", description="Pickup matches: queue up for a balanced competitive game")

    @group.command(name="join", description="Join the pickup queue")
    async def cmd_join(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=embeds.notice("Pickup", await self.on_join(interaction.user)),
                                                ephemeral=True)

    @group.command(name="leave", description="Leave the pickup queue")
    async def cmd_leave(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=embeds.notice("Pickup", await self.on_leave(interaction.user)),
                                                ephemeral=True)

    @group.command(name="status", description="Who is queued and which matches are running")
    async def cmd_status(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.queue_embed(self.state()), ephemeral=True)

    @group.command(name="end", description="End a pickup match and free its server (staff)")
    @app_commands.describe(match="Pickup number, e.g. 12")
    @staff_only()
    async def cmd_end(self, interaction: discord.Interaction, match: int):
        if str(match) not in self.state()["matches"]:
            raise UserFacingError("Pickup #%d isn't running." % match)
        await interaction.response.defer(ephemeral=True)
        await self.finish(str(match), "Ended by staff.")
        await interaction.followup.send(embed=embeds.notice("Pickup", "Pickup #%d ended." % match), ephemeral=True)

    @group.command(name="reset", description="Clear the queue and any ready check (staff)")
    @staff_only()
    async def cmd_reset(self, interaction: discord.Interaction):
        async with self.lock:
            st = self.state()
            st["queue"], st["check"] = [], None
            self.save(st)
        await self.update_queue_message()
        await interaction.response.send_message(embed=embeds.notice("Pickup", "Queue cleared."), ephemeral=True)

    @group.command(name="servers", description="Match servers and whether they answer (staff)")
    @staff_only()
    async def cmd_servers(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        st, lines = self.state(), []
        busy = {m["server"]: m["id"] for m in st["matches"].values()}
        for s in self.servers():
            status = await query_game(s["host"], s["port"])
            rc = await self.rc(s, "match status")
            lines.append("**%s** `%s` · %s · rcon %s%s" % (
                s["key"], s["public_address"], "online" if status else "offline", "ok" if rc is not None else "no answer",
                (" · pickup #%d" % busy[s["key"]]) if s["key"] in busy else ""))
        await interaction.followup.send(embed=embeds.notice("Match servers", "\n".join(lines) or
                                                            "No match servers configured."), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Pickup(bot))
