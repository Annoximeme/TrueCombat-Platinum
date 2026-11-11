"""Teams, the team ladder, scrims and tournaments.

A team is a name, a tag, a captain and its members (one team per member).
Scrims and tournament matches run on the pickup match servers: the bot sets
the password, match mode and team names, and sends every member of both
teams their join line. The result is read from the stats service (which
side the linked players were on, and whether that side won); when it can't
be read, staff confirm it with /scrim result or /tournament result.
"""

from __future__ import annotations

import logging
import re
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import bracket as B
from .. import embeds
from .. import text as T
from ..bot import UserFacingError, staff_only

log = logging.getLogger("tcpbot.clans")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._'-]{1,22}[A-Za-z0-9.']")
TAG = re.compile(r"[A-Za-z0-9]{2,5}")


def tname(t) -> str:
    return "[%s] %s" % (T.md(t["tag"]), T.md(t["name"]))


# ================================================================ buttons
class TeamButton(discord.ui.DynamicItem[discord.ui.Button],
                 template=r"tcp:team:(?P<action>join|nojoin|yes|no|in|out):(?P<ref>\d+)"):
    STYLES = {"join": ("Join the team", discord.ButtonStyle.success), "nojoin": ("No thanks", discord.ButtonStyle.secondary),
              "yes": ("Accept", discord.ButtonStyle.success), "no": ("Decline", discord.ButtonStyle.danger),
              "in": ("Sign up my team", discord.ButtonStyle.success), "out": ("Withdraw", discord.ButtonStyle.secondary)}

    def __init__(self, action: str, ref: int):
        label, style = self.STYLES[action]
        super().__init__(discord.ui.Button(label=label, style=style, custom_id="tcp:team:%s:%d" % (action, ref)))
        self.action, self.ref = action, ref

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(match["action"], int(match["ref"]))

    async def callback(self, interaction: discord.Interaction):
        cog: Clans = interaction.client.get_cog("Clans")
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            text = await getattr(cog, "on_" + self.action)(interaction.user, self.ref)
        except UserFacingError as e:
            text = str(e)
        await interaction.followup.send(embed=embeds.notice("Teams", text), ephemeral=True)


def view_of(*items) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for action, ref in items:
        v.add_item(TeamButton(action, ref))
    return v


# ================================================================ cog
class Clans(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.tc = bot.cfg["teams"]

    async def cog_load(self):
        self.bot.add_dynamic_items(TeamButton)
        self.tick.start()

    async def cog_unload(self):
        self.tick.cancel()

    @property
    def store(self):
        return self.bot.store

    def channel(self, cid: int = 0):
        return self.bot.text_channel(cid) or self.bot.text_channel(
            self.cfg.channel("teams", "events") or self.cfg.channel("announcements"))

    # ------------------------------------------------------------ helpers
    def my_team(self, uid: int):
        t = self.store.team_of(uid)
        if not t:
            raise UserFacingError("You're not in a team. Create one with `/team create` or ask a captain for an invite.")
        return t

    def my_captaincy(self, uid: int):
        t = self.my_team(uid)
        if t["captain"] != uid:
            raise UserFacingError("Only the captain of **%s** can do that." % T.md(t["name"]))
        return t

    def find(self, name: str):
        name = (name or "").strip()
        t = self.store.team(int(name)) if name.isdigit() else self.store.team_named(name)
        if not t:
            raise UserFacingError("There's no team called **%s**. `/team list` shows them all." % T.md(name[:30]))
        return t

    async def team_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=("[%s] %s" % (t["tag"], t["name"]))[:100], value=str(t["id"]))
                for t in self.store.teams(current.strip())]

    def pickup(self):
        p = self.bot.get_cog("Pickup")
        if p is None or not p.servers():
            raise UserFacingError("Team matches need the match servers, and those aren't set up yet.")
        return p

    def busy(self, team_id: int) -> bool:
        p = self.bot.get_cog("Pickup")
        if p is None:
            return False
        return any(team_id in (m.get("meta") or {}).get("teams", []) for m in p.state()["matches"].values())

    def team_card(self, t) -> discord.Embed:
        members = self.store.team_members(t["id"])
        e = discord.Embed(title="[%s] %s" % (t["tag"], t["name"]), colour=embeds.RED)
        played = t["wins"] + t["losses"]
        e.description = "Team rating **%s** · %d won, %d lost%s" % (
            T.num(round(t["rating"])), t["wins"], t["losses"], "" if played else " · no matches yet")
        e.add_field(name="Captain", value="<@%d>" % t["captain"], inline=True)
        e.add_field(name="Founded", value="<t:%d:D>" % t["created"], inline=True)
        e.add_field(name="Roster (%d/%d)" % (len(members), int(self.tc["max_members"])),
                    value=" ".join("<@%d>" % u for u in members)[:1024] or "—", inline=False)
        return e

    def ladder(self) -> discord.Embed:
        rows = self.store.teams("", 20)
        e = discord.Embed(title="Team ladder", colour=embeds.RED)
        if not rows:
            e.description = "No teams yet. Start one with `/team create`."
            return e
        table = [("#", "Team", "Rating", "W-L", "Players")] + [
            (str(i), "[%s] %s" % (t["tag"], T.clean(t["name"], 18)), T.num(round(t["rating"])),
             "%d-%d" % (t["wins"], t["losses"]), str(t["members"])) for i, t in enumerate(rows, 1)]
        e.description = "```\n%s\n```" % T.mono(T.table(table, "rlrrr"))
        e.set_footer(text="Challenge a team with /scrim challenge. Every scrim and tournament match counts.")
        return e

    def record(self, winner_id: int, loser_id: int) -> tuple[int, int]:
        """Applies a result to the ladder. Returns the rating change of winner and loser."""
        w, l = self.store.team(winner_id), self.store.team(loser_id)
        if not w or not l:
            return 0, 0
        nw, nl = B.elo(w["rating"], l["rating"])
        self.store.team_update(w["id"], rating=nw, wins=w["wins"] + 1)
        self.store.team_update(l["id"], rating=nl, losses=l["losses"] + 1)
        return round(nw - w["rating"]), round(nl - l["rating"])

    def winner_from(self, m: dict, detail: dict | None) -> int | None:
        """Which team won, read from the scoreboard: the side most of a team's linked players
        were on. Returns the team id, or None when it can't be told."""
        if not detail:
            return None
        ids = (m.get("meta") or {}).get("teams") or []
        if len(ids) != 2:
            return None
        won = {r["id"]: bool(r.get("won")) for r in detail.get("players") or [] if r.get("id")}
        score = []
        for side in (m["red"], m["blue"]):
            votes = [won[link["pid"]] for u in side if (link := self.store.linked_player(u)) and link["pid"] in won]
            score.append((sum(votes), len(votes)))
        (aw, an), (bw, bn) = score
        a = aw * 2 > an if an else None
        b = bw * 2 > bn if bn else None
        if a is True and b is not True:
            return ids[0]
        if b is True and a is not True:
            return ids[1]
        if a is False and b is None:
            return ids[1]
        if b is False and a is None:
            return ids[0]
        return None

    # ------------------------------------------------------------ invites
    async def on_join(self, user, team_id: int) -> str:
        t = self.store.team(team_id)
        if not t:
            raise UserFacingError("That team no longer exists.")
        if not self.store.team_invited(team_id, user.id):
            raise UserFacingError("That invite has expired. Ask the captain for a new one.")
        if self.store.team_of(user.id):
            raise UserFacingError("You're already in a team. Leave it first with `/team leave`.")
        if len(self.store.team_members(team_id)) >= int(self.tc["max_members"]):
            raise UserFacingError("**%s** is full." % T.md(t["name"]))
        self.store.team_join(team_id, user.id)
        return "Welcome to **%s**." % T.md(t["name"])

    async def on_nojoin(self, user, team_id: int) -> str:
        return "No problem. The invite will expire on its own."

    # ------------------------------------------------------------ scrims
    def scrim_embed(self, d: dict) -> discord.Embed:
        a, b = self.store.team(d["a"]), self.store.team(d["b"])
        names = (tname(a) if a else "a disbanded team", tname(b) if b else "a disbanded team")
        state = d["state"]
        colour = {"open": embeds.AMBER, "live": embeds.GREEN, "done": embeds.GOLD}.get(state, embeds.STEEL)
        e = discord.Embed(title="Scrim #%d" % d["id"], colour=colour)
        where = " on **%s**" % T.map_label(d["map"]) if d.get("map") else ""
        if state == "open":
            e.description = "%s challenges %s%s.\n<@%d>, accept <t:%d:R>." % (
                names[0], names[1], where, b["captain"] if b else 0, d["expires"])
        elif state == "live":
            e.description = "%s vs %s%s. In progress." % (names[0], names[1], where)
        elif state == "done":
            w = 0 if d["winner"] == d["a"] else 1
            e.description = "**%s** beat %s%s." % (names[w], names[1 - w], where)
            if d.get("delta"):
                e.add_field(name="Ladder", value="%s %s · %s %s" % (
                    names[w], T.signed(d["delta"][0]), names[1 - w], T.signed(d["delta"][1])), inline=False)
        elif state == "review":
            e.description = ("%s vs %s%s is over, but the result couldn't be read from the scoreboard. "
                             "Staff: confirm it with `/scrim result`." % (names[0], names[1], where))
        else:
            e.description = "%s vs %s: %s." % (names[0], names[1], {
                "declined": "declined", "expired": "the challenge expired", "void": d.get("note") or "called off"}.get(state, state))
        return e

    async def refresh_scrim(self, d: dict):
        ch = self.channel(d.get("channel", 0))
        if ch is None:
            return
        e = self.scrim_embed(d)
        v = view_of(("yes", d["id"]), ("no", d["id"])) if d["state"] == "open" else None
        if d.get("message"):
            try:
                await ch.get_partial_message(d["message"]).edit(embed=e, view=v)
                return
            except discord.HTTPException:
                pass
        b = self.store.team(d["b"])
        msg = await ch.send(content="<@%d>" % b["captain"] if b and d["state"] == "open" else None, embed=e, view=v,
                            allowed_mentions=discord.AllowedMentions(users=True))
        d["message"], d["channel"] = msg.id, ch.id
        self.store.doc_save(d)

    def _scrim_for(self, user, ref: int) -> tuple[dict, object]:
        d = self.store.doc("scrim", ref)
        if not d or d["state"] != "open":
            raise UserFacingError("This challenge is no longer open.")
        b = self.store.team(d["b"])
        if not b or b["captain"] != user.id:
            raise UserFacingError("Only the captain of the challenged team can answer.")
        return d, b

    async def on_yes(self, user, ref: int) -> str:
        d, b = self._scrim_for(user, ref)
        a = self.store.team(d["a"])
        if not a:
            d["state"] = "void"
            self.store.doc_save(d)
            await self.refresh_scrim(d)
            raise UserFacingError("The challenging team no longer exists.")
        if self.busy(a["id"]) or self.busy(b["id"]):
            raise UserFacingError("One of the teams is in a match right now. Accept again when it's over.")
        match = await self.start(a, b, "Scrim #%d" % d["id"], d.get("map"), {"scrim": d["id"]}, d.get("channel", 0))
        if match is None:
            raise UserFacingError("Every match server is busy. Accept again in a few minutes.")
        d["state"], d["match"] = "live", match["id"]
        self.store.doc_save(d)
        await self.refresh_scrim(d)
        return "Accepted. Join details are on their way to both teams by DM."

    async def on_no(self, user, ref: int) -> str:
        d, _b = self._scrim_for(user, ref)
        d["state"] = "declined"
        self.store.doc_save(d)
        await self.refresh_scrim(d)
        return "Challenge declined."

    async def start(self, a, b, label: str, mapname: str | None, meta: dict, channel_id: int = 0) -> dict | None:
        p = self.pickup()
        red, blue = self.store.team_members(a["id"]), self.store.team_members(b["id"])
        meta = dict(meta, teams=[a["id"], b["id"]])
        ch = self.channel(channel_id)
        match = await p.start_custom("Clans", "%s · %s vs %s" % (label, a["tag"], b["tag"]), red, blue,
                                     [a["name"], b["name"]], ch.id if ch else 0, mapname, meta)
        if match and match.get("failed"):
            raise UserFacingError("The match server didn't respond. Try again in a minute, or tell staff.")
        return match

    async def on_team_match(self, m: dict, row: dict | None, detail: dict | None, note: str | None):
        """Called by the pickup module when a team match ends."""
        meta = m.get("meta") or {}
        winner = None if note else self.winner_from(m, detail)
        if "tournament" in meta:
            await self.tournament_match_over(meta, winner, note)
            return
        d = self.store.doc("scrim", meta.get("scrim", 0))
        if not d or d["state"] != "live":
            return
        if note:
            d["state"], d["note"] = "void", note[0].lower() + note[1:].rstrip(".")
        elif winner:
            self.close_scrim(d, winner)
        else:
            d["state"] = "review"
        self.store.doc_save(d)
        await self.refresh_scrim(d)

    def close_scrim(self, d: dict, winner: int):
        loser = d["b"] if winner == d["a"] else d["a"]
        d["state"], d["winner"], d["delta"] = "done", winner, list(self.record(winner, loser))

    @tasks.loop(minutes=1)
    async def tick(self):
        now = int(time.time())
        for d in self.store.docs("scrim", "open"):
            if now > d["expires"]:
                d["state"] = "expired"
                self.store.doc_save(d)
                try:
                    await self.refresh_scrim(d)
                except discord.HTTPException:
                    pass

    @tick.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()

    # ------------------------------------------------------------ /team
    team = app_commands.Group(name="team", description="Teams: create one, invite players and climb the team ladder")

    @team.command(name="create", description="Create a team. You become its captain")
    @app_commands.describe(name="Team name, 3 to 24 characters", tag="Short tag, 2 to 5 letters or digits")
    async def team_create(self, interaction: discord.Interaction, name: str, tag: str):
        if not self.tc["enabled"]:
            raise UserFacingError("Teams are switched off right now.")
        name, tag = " ".join(name.split()), tag.strip()
        if not NAME.fullmatch(name):
            raise UserFacingError("A team name is 3 to 24 letters, digits and spaces.")
        if not TAG.fullmatch(tag):
            raise UserFacingError("A tag is 2 to 5 letters or digits, like `TT`.")
        uid = interaction.user.id
        if self.store.team_of(uid):
            raise UserFacingError("You're already in a team. Leave it first with `/team leave`.")
        if self.tc["create_requires_link"] and not self.store.linked_player(uid):
            raise UserFacingError("Link your game profile with `/link` before creating a team.")
        tid = self.store.team_create(name, tag, uid)
        if tid is None:
            raise UserFacingError("That name or tag is taken. Pick another.")
        await interaction.response.send_message(
            content="A new team enters the ladder.", embed=self.team_card(self.store.team(tid)))

    @team.command(name="invite", description="Invite a member to your team (captain)")
    async def team_invite(self, interaction: discord.Interaction, member: discord.Member):
        t = self.my_captaincy(interaction.user.id)
        if member.bot or member.id == interaction.user.id:
            raise UserFacingError("Pick another member.")
        if self.store.team_of(member.id):
            raise UserFacingError("%s is already in a team." % member.display_name)
        if len(self.store.team_members(t["id"])) >= int(self.tc["max_members"]):
            raise UserFacingError("Your roster is full (%d)." % int(self.tc["max_members"]))
        self.store.team_invite(t["id"], member.id)
        e = embeds.notice("Team invite", "%s invited you to join **%s**. The invite is good for seven days." % (
            interaction.user.mention, tname(t)))
        sent = True
        try:
            await member.send(embed=e, view=view_of(("join", t["id"]), ("nojoin", t["id"])))
        except discord.HTTPException:
            sent = False
        await interaction.response.send_message(embed=embeds.notice("Teams", (
            "Invite sent to %s by DM." if sent else
            "%s has DMs closed. Tell them to use `/team join` to accept.") % member.mention), ephemeral=True)

    @team.command(name="join", description="Accept an invite to a team")
    @app_commands.autocomplete(team=team_autocomplete)
    async def team_join(self, interaction: discord.Interaction, team: str):
        t = self.find(team)
        text = await self.on_join(interaction.user, t["id"])
        await interaction.response.send_message(embed=embeds.notice("Teams", text), ephemeral=True)

    @team.command(name="leave", description="Leave your team")
    async def team_leave(self, interaction: discord.Interaction):
        uid = interaction.user.id
        t = self.my_team(uid)
        members = self.store.team_members(t["id"])
        if t["captain"] == uid and len(members) > 1:
            raise UserFacingError("Hand the team over first with `/team captain`, or close it with `/team disband`.")
        self.store.team_leave(uid)
        if len(members) == 1:
            self.store.team_delete(t["id"])
            text = "You left **%s**. It had no players left, so it was closed." % T.md(t["name"])
        else:
            text = "You left **%s**." % T.md(t["name"])
        await interaction.response.send_message(embed=embeds.notice("Teams", text), ephemeral=True)

    @team.command(name="kick", description="Remove a player from your team (captain)")
    async def team_kick(self, interaction: discord.Interaction, member: discord.Member):
        t = self.my_captaincy(interaction.user.id)
        other = self.store.team_of(member.id)
        if not other or other["id"] != t["id"] or member.id == interaction.user.id:
            raise UserFacingError("%s isn't one of your players." % member.display_name)
        self.store.team_leave(member.id)
        await interaction.response.send_message(embed=embeds.notice(
            "Teams", "%s is no longer in **%s**." % (member.mention, T.md(t["name"]))), ephemeral=True)

    @team.command(name="captain", description="Hand your team over to another player (captain)")
    async def team_captain(self, interaction: discord.Interaction, member: discord.Member):
        t = self.my_captaincy(interaction.user.id)
        other = self.store.team_of(member.id)
        if not other or other["id"] != t["id"]:
            raise UserFacingError("%s isn't one of your players." % member.display_name)
        self.store.team_update(t["id"], captain=member.id)
        await interaction.response.send_message(embed=embeds.notice(
            "Teams", "%s is now the captain of **%s**." % (member.mention, T.md(t["name"]))))

    @team.command(name="disband", description="Close your team for good (captain)")
    @app_commands.describe(confirm="Type the team's tag to confirm")
    async def team_disband(self, interaction: discord.Interaction, confirm: str):
        t = self.my_captaincy(interaction.user.id)
        if confirm.strip().lower() != t["tag"].lower():
            raise UserFacingError("Type your team's tag (`%s`) to confirm." % t["tag"])
        if self.busy(t["id"]):
            raise UserFacingError("Your team is in a match right now.")
        self.store.team_delete(t["id"])
        await interaction.response.send_message(embed=embeds.notice("Teams", "**%s** has been closed." % T.md(t["name"])),
                                                ephemeral=True)

    @team.command(name="info", description="A team's roster, rating and record")
    @app_commands.autocomplete(team=team_autocomplete)
    async def team_info(self, interaction: discord.Interaction, team: str | None = None):
        t = self.find(team) if team else self.my_team(interaction.user.id)
        await interaction.response.send_message(embed=self.team_card(t))

    @team.command(name="list", description="The team ladder")
    async def team_list(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.ladder())

    # ------------------------------------------------------------ /scrim
    scrim = app_commands.Group(name="scrim", description="Team against team on a private match server")

    async def _map_choices(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=T.map_label(m), value=m) for m in self.cfg["pickup"]["maps"]
                if current.lower() in T.map_label(m).lower() or current.lower() in m][:25]

    @scrim.command(name="challenge", description="Challenge another team to a scrim (captain)")
    @app_commands.describe(team="The team to challenge", map="Map to play (random when left empty)")
    @app_commands.autocomplete(team=team_autocomplete, map=_map_choices)
    async def scrim_challenge(self, interaction: discord.Interaction, team: str, map: str | None = None):  # noqa: A002
        a = self.my_captaincy(interaction.user.id)
        b = self.find(team)
        if a["id"] == b["id"]:
            raise UserFacingError("You can't challenge your own team.")
        self.pickup()
        if map and map not in self.cfg["pickup"]["maps"]:
            raise UserFacingError("Pick one of the match maps: %s." % ", ".join(
                T.map_label(m) for m in self.cfg["pickup"]["maps"]))
        if any(d["a"] == a["id"] and d["b"] == b["id"] for d in self.store.docs("scrim", "open")):
            raise UserFacingError("You already have an open challenge to **%s**." % T.md(b["name"]))
        d = {"a": a["id"], "b": b["id"], "map": map or "", "message": 0, "channel": 0,
             "expires": int(time.time()) + int(self.tc["challenge_minutes"]) * 60}
        d = self.store.doc("scrim", self.store.doc_add("scrim", d, owner=interaction.user.id))
        await interaction.response.defer(ephemeral=True)
        await self.refresh_scrim(d)
        await interaction.followup.send(embed=embeds.notice(
            "Scrim", "Challenge sent. **%s**'s captain has %d minutes to accept." % (
                T.md(b["name"]), int(self.tc["challenge_minutes"]))), ephemeral=True)

    @scrim.command(name="result", description="Confirm the winner of a scrim (staff)")
    @app_commands.describe(scrim="Scrim number", winner="The team that won")
    @app_commands.autocomplete(winner=team_autocomplete)
    @staff_only()
    async def scrim_result(self, interaction: discord.Interaction, scrim: int, winner: str):
        d = self.store.doc("scrim", scrim)
        if not d or d["state"] not in ("review", "live", "void"):
            raise UserFacingError("Scrim #%d isn't waiting for a result." % scrim)
        w = self.find(winner)
        if w["id"] not in (d["a"], d["b"]):
            raise UserFacingError("**%s** didn't play in scrim #%d." % (T.md(w["name"]), scrim))
        self.close_scrim(d, w["id"])
        self.store.doc_save(d)
        await interaction.response.defer(ephemeral=True)
        await self.refresh_scrim(d)
        await interaction.followup.send(embed=embeds.notice("Scrim", "Result recorded."), ephemeral=True)

    # ------------------------------------------------------------ tournaments
    def tour_embed(self, d: dict) -> discord.Embed:
        state = d["state"]
        e = discord.Embed(title=T.clip(d["name"], 200), colour={"open": embeds.RED, "live": embeds.GREEN,
                                                                 "done": embeds.GOLD}.get(state, embeds.STEEL))
        teams = [t for t in (self.store.team(i) for i in d["teams"]) if t]
        if state == "open":
            e.description = "%s\nSingle elimination · starts <t:%d:F> (<t:%d:R>)\nCaptains sign their team up below." % (
                T.clip(d.get("about") or "", 1500), d["starts"], d["starts"])
            e.add_field(name="Teams (%d/%d)" % (len(teams), d["size"]),
                        value="\n".join(tname(t) for t in teams)[:1024] or "Be the first.", inline=False)
        elif state == "cancelled":
            e.description = "This tournament was cancelled."
        else:
            names = {t["id"]: "[%s] %s" % (t["tag"], T.clean(t["name"], 16)) for t in teams}

            def side(m, k):
                tid = m[k]
                label = names.get(tid, "to be decided") if tid else ("bye" if m["w"] else "to be decided")
                return ("» " if tid and m["w"] == tid else "  ") + label
            for r, rnd in enumerate(d["rounds"]):
                lines = []
                for m in rnd:
                    lines.append("%s\n%s%s" % (side(m, "a"), side(m, "b"), "   (playing)" if m.get("live") else ""))
                e.add_field(name=B.round_name(d["rounds"], r), value="```\n%s\n```" % T.mono("\n\n".join(lines))[:1010],
                            inline=len(rnd) <= 2)
            if state == "done":
                champ = self.store.team(d["champion"])
                e.description = "🏆 **%s** won the tournament." % (tname(champ) if champ else "The champion")
            else:
                e.description = "Under way. Captains start their next match with `/tournament play`."
        e.set_footer(text="Tournament #%d" % d["id"])
        return e

    async def refresh_tour(self, d: dict):
        ch = self.channel(d.get("channel", 0))
        if ch is None:
            return
        e = self.tour_embed(d)
        v = view_of(("in", d["id"]), ("out", d["id"])) if d["state"] == "open" else None
        if d.get("message"):
            try:
                await ch.get_partial_message(d["message"]).edit(embed=e, view=v)
                return
            except discord.HTTPException:
                pass
        msg = await ch.send(embed=e, view=v)
        d["message"], d["channel"] = msg.id, ch.id
        self.store.doc_save(d)

    def _tour(self, ref: int, *states) -> dict:
        d = self.store.doc("tournament", ref)
        if not d:
            raise UserFacingError("There's no tournament #%d." % ref)
        if states and d["state"] not in states:
            raise UserFacingError("Tournament #%d is %s." % (ref, {
                "open": "still taking sign-ups", "live": "already under way", "done": "over",
                "cancelled": "cancelled"}[d["state"]]))
        return d

    async def on_in(self, user, ref: int) -> str:
        d = self._tour(ref, "open")
        t = self.my_captaincy(user.id)
        if t["id"] in d["teams"]:
            return "**%s** is already signed up." % T.md(t["name"])
        if len(d["teams"]) >= d["size"]:
            raise UserFacingError("The tournament is full.")
        d["teams"].append(t["id"])
        self.store.doc_save(d)
        await self.refresh_tour(d)
        return "**%s** is signed up. Good luck." % T.md(t["name"])

    async def on_out(self, user, ref: int) -> str:
        d = self._tour(ref, "open")
        t = self.my_captaincy(user.id)
        if t["id"] not in d["teams"]:
            return "**%s** isn't signed up." % T.md(t["name"])
        d["teams"].remove(t["id"])
        self.store.doc_save(d)
        await self.refresh_tour(d)
        return "**%s** has withdrawn." % T.md(t["name"])

    async def tournament_match_over(self, meta: dict, winner: int | None, note: str | None):
        d = self.store.doc("tournament", meta["tournament"])
        if not d or d["state"] != "live":
            return
        r, i = meta["round"], meta["slot"]
        d["rounds"][r][i]["live"] = False
        if winner:
            await self.advance(d, r, i, winner)
            return
        self.store.doc_save(d)
        await self.refresh_tour(d)
        m = d["rounds"][r][i]
        a, b = self.store.team(m["a"]), self.store.team(m["b"])
        staff = self.bot.text_channel(self.cfg.channel("staff"))
        if staff and a and b:
            await staff.send(embed=embeds.notice(
                "Tournament result needed", "%s vs %s in **%s** %s. Confirm the winner with `/tournament result`, "
                "or the captains can replay with `/tournament play`." % (
                    tname(a), tname(b), T.md(d["name"]),
                    "was called off (%s)" % note.rstrip(".") if note else "ended, but the scoreboard didn't settle it"),
                embeds.AMBER))

    async def advance(self, d: dict, r: int, i: int, winner: int):
        m = d["rounds"][r][i]
        loser = m["b"] if winner == m["a"] else m["a"]
        champion = B.report(d["rounds"], r, i, winner)
        self.record(winner, loser)
        if champion:
            d["state"], d["champion"] = "done", champion
        self.store.doc_save(d)
        await self.refresh_tour(d)
        ch = self.channel(d.get("channel", 0))
        w, l = self.store.team(winner), self.store.team(loser)
        if ch and w and l:
            if champion:
                text = "🏆 **%s** beat %s in the final and won **%s**." % (tname(w), tname(l), T.md(d["name"]))
                roster = " ".join("<@%d>" % u for u in self.store.team_members(w["id"]))
                await ch.send(content=roster or None, embed=embeds.notice("We have a champion", text, embeds.GOLD),
                              allowed_mentions=discord.AllowedMentions(users=True))
            else:
                await ch.send(embed=embeds.notice(T.md(d["name"]), "**%s** beat %s and moves on to the %s." % (
                    tname(w), tname(l), B.round_name(d["rounds"], r + 1).lower().rstrip("s")), embeds.GREEN))

    tournament = app_commands.Group(name="tournament", description="Team tournaments: sign up, play your bracket, win")

    async def _tours(self, interaction: discord.Interaction, current: str):
        rows = self.store.docs("tournament", limit=25)
        return [app_commands.Choice(name=("#%d %s" % (d["id"], d["name"]))[:100], value=d["id"]) for d in rows
                if current.lower() in d["name"].lower() and d["state"] in ("open", "live")]

    def _current(self, ref: int | None, *states) -> dict:
        if ref:
            return self._tour(ref, *states)
        rows = [d for d in self.store.docs("tournament") if d["state"] in (states or ("open", "live"))]
        if not rows:
            raise UserFacingError("There's no tournament for that right now.")
        return rows[0]

    @tournament.command(name="create", description="Open a tournament for sign-ups (staff)")
    @app_commands.describe(name="Tournament name", when="Start, in Belgian time: 'saturday 20:00', '2026-12-05 20:00'",
                           teams="Most teams that can enter", about="A line or two about format and prizes")
    @staff_only()
    async def tour_create(self, interaction: discord.Interaction, name: app_commands.Range[str, 3, 80], when: str,
                          teams: app_commands.Range[int, 2, 32] = 8, about: app_commands.Range[str, 0, 500] = ""):
        self.pickup()
        try:
            starts = T.parse_when(when, self.cfg["timezone"])
        except T.TimeError as e:
            raise UserFacingError(str(e)) from e
        d = {"name": name, "about": about, "starts": int(starts.timestamp()), "size": teams, "teams": [], "rounds": [],
             "message": 0, "channel": 0}
        d = self.store.doc("tournament", self.store.doc_add("tournament", d, owner=interaction.user.id))
        await interaction.response.defer(ephemeral=True)
        await self.refresh_tour(d)
        await interaction.followup.send(embed=embeds.notice(
            "Tournament", "Tournament #%d is open for sign-ups. Start it with `/tournament start` when the teams are in."
            % d["id"]), ephemeral=True)

    @tournament.command(name="start", description="Close sign-ups and draw the bracket (staff)")
    @app_commands.autocomplete(tournament=_tours)
    @staff_only()
    async def tour_start(self, interaction: discord.Interaction, tournament: int | None = None):
        d = self._current(tournament, "open")
        teams = sorted((t for t in (self.store.team(i) for i in d["teams"]) if t), key=lambda t: -t["rating"])
        if len(teams) < 2:
            raise UserFacingError("A tournament needs at least two teams.")
        d["teams"] = [t["id"] for t in teams]
        d["rounds"], d["state"] = B.build(d["teams"]), "live"
        self.store.doc_save(d)
        await interaction.response.defer(ephemeral=True)
        await self.refresh_tour(d)
        ch = self.channel(d.get("channel", 0))
        if ch:
            caps = " ".join("<@%d>" % t["captain"] for t in teams)
            await ch.send(content=caps, embed=embeds.notice(
                T.md(d["name"]), "The bracket is drawn, seeded on team rating. Captains: when both teams are ready, "
                "either of you starts the match with `/tournament play`.", embeds.GREEN),
                allowed_mentions=discord.AllowedMentions(users=True))
        await interaction.followup.send(embed=embeds.notice("Tournament", "Bracket drawn for %d teams." % len(teams)),
                                        ephemeral=True)

    @tournament.command(name="play", description="Start your team's next tournament match (captain)")
    @app_commands.autocomplete(tournament=_tours)
    async def tour_play(self, interaction: discord.Interaction, tournament: int | None = None):
        d = self._current(tournament, "live")
        t = self.my_captaincy(interaction.user.id)
        mine = B.pending(d["rounds"], t["id"])
        if not mine:
            raise UserFacingError("**%s** has no match to play right now." % T.md(t["name"]))
        r, i, m = mine[0]
        if m.get("live"):
            raise UserFacingError("That match is already running. Check your DMs for the join details.")
        a, b = self.store.team(m["a"]), self.store.team(m["b"])
        if not a or not b:
            raise UserFacingError("Your opponent's team no longer exists. Ask staff to settle it with `/tournament result`.")
        if self.busy(a["id"]) or self.busy(b["id"]):
            raise UserFacingError("One of the teams is in another match right now.")
        await interaction.response.defer(ephemeral=True)
        match = await self.start(a, b, B.round_name(d["rounds"], r).rstrip("s"), None,
                                 {"tournament": d["id"], "round": r, "slot": i}, d.get("channel", 0))
        if match is None:
            raise UserFacingError("Every match server is busy. Try again in a few minutes.")
        d = self.store.doc("tournament", d["id"])
        d["rounds"][r][i]["live"] = True
        self.store.doc_save(d)
        await self.refresh_tour(d)
        await interaction.followup.send(embed=embeds.notice(
            "Tournament", "Server is up. Join details went to both teams by DM."), ephemeral=True)

    @tournament.command(name="result", description="Set the winner of a tournament match (staff)")
    @app_commands.describe(winner="The team that won its current match")
    @app_commands.autocomplete(winner=team_autocomplete, tournament=_tours)
    @staff_only()
    async def tour_result(self, interaction: discord.Interaction, winner: str, tournament: int | None = None):
        d = self._current(tournament, "live")
        w = self.find(winner)
        mine = B.pending(d["rounds"], w["id"])
        if not mine:
            raise UserFacingError("**%s** has no open match in this tournament." % T.md(w["name"]))
        await interaction.response.defer(ephemeral=True)
        await self.advance(d, mine[0][0], mine[0][1], w["id"])
        await interaction.followup.send(embed=embeds.notice("Tournament", "Result recorded."), ephemeral=True)

    @tournament.command(name="bracket", description="Show a tournament's bracket or sign-ups")
    @app_commands.autocomplete(tournament=_tours)
    async def tour_bracket(self, interaction: discord.Interaction, tournament: int | None = None):
        d = self._current(tournament) if not tournament else self._tour(tournament)
        await interaction.response.send_message(embed=self.tour_embed(d))

    @tournament.command(name="cancel", description="Cancel a tournament (staff)")
    @app_commands.autocomplete(tournament=_tours)
    @staff_only()
    async def tour_cancel(self, interaction: discord.Interaction, tournament: int):
        d = self._tour(tournament, "open", "live")
        d["state"] = "cancelled"
        self.store.doc_save(d)
        await interaction.response.defer(ephemeral=True)
        await self.refresh_tour(d)
        await interaction.followup.send(embed=embeds.notice("Tournament", "Tournament #%d cancelled." % d["id"]),
                                        ephemeral=True)


async def setup(bot):
    await bot.add_cog(Clans(bot))
