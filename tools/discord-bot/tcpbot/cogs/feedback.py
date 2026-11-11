"""Bug reports and suggestions.

/bug opens a short form. The report lands in the private bugs channel as a
tracker card the team moves through Confirmed, Fixed and so on, and the
reporter hears back by DM when its status changes. A card can also be filed
as a GitHub issue when a repository and token are configured.

/suggest posts an idea to the public suggestions channel, where members vote
with one vote each and staff mark it Planned, In progress, Shipped or Declined.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .. import embeds
from .. import text as T
from ..bot import UserFacingError, staff_only

log = logging.getLogger("tcpbot.feedback")

BUG_STATES = {
    "open": ("New", embeds.AMBER, None),
    "confirmed": ("Confirmed", embeds.RED, "The team reproduced it and it's on the fix list."),
    "fixed": ("Fixed", embeds.GREEN, "It's fixed and will be in the next update. Thank you for reporting it."),
    "norepro": ("Can't reproduce", embeds.STEEL, "The team couldn't make it happen. If you see it again, "
                                                 "send another report with the exact steps, map and server."),
    "notabug": ("Works as intended", embeds.STEEL, "After a look, this is how it's meant to work."),
    "duplicate": ("Already known", embeds.STEEL, "This one was already on the list, so it's tracked there."),
}
IDEA_STATES = {
    "open": ("Open for votes", embeds.BLUE),
    "planned": ("Planned", embeds.AMBER),
    "progress": ("In progress", embeds.RED),
    "shipped": ("Shipped", embeds.GREEN),
    "declined": ("Not planned", embeds.STEEL),
}


def secret(name: str) -> str:
    """A secret handed to the service as a systemd credential; empty when there is none."""
    d = os.environ.get("CREDENTIALS_DIRECTORY")
    if not d or not re.fullmatch(r"[a-z0-9_-]+", name or ""):
        return ""
    try:
        return (Path(d) / name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def plain(text: str) -> str:
    """Member-written text, with mentions made inert."""
    return (text or "").strip().replace("@", "@\u200b")


# ================================================================ cards
def bug_embed(d: dict) -> discord.Embed:
    label, colour, _ = BUG_STATES[d["state"]]
    e = discord.Embed(title=T.clip("Bug #%d · %s" % (d["id"], d["title"]), 250), colour=colour)
    e.description = T.clip(d["what"], 2000)
    if d.get("steps"):
        e.add_field(name="Steps to reproduce", value=T.clip(d["steps"], 1024), inline=False)
    if d.get("where"):
        e.add_field(name="Version, map or server", value=T.clip(d["where"], 200), inline=True)
    e.add_field(name="Reported by", value="<@%d>" % d["owner"], inline=True)
    e.add_field(name="Status", value=label + (" · <@%d>" % d["by"] if d.get("by") else ""), inline=True)
    if d.get("issue"):
        e.add_field(name="GitHub", value=d["issue"], inline=False)
    return e


def idea_embed(d: dict) -> discord.Embed:
    label, colour = IDEA_STATES[d["state"]]
    e = discord.Embed(title=T.clip(d["title"], 250), colour=colour)
    e.description = T.clip(d["details"], 3000)
    votes = d.get("votes") or {}
    up = sum(1 for v in votes.values() if v > 0)
    down = len(votes) - up
    e.add_field(name="Votes", value="👍 %d · 👎 %d" % (up, down), inline=True)
    e.add_field(name="Status", value=label, inline=True)
    e.add_field(name="Suggested by", value="<@%d>" % d["owner"], inline=True)
    if d.get("note"):
        e.add_field(name="From the team", value=T.clip(d["note"], 1000), inline=False)
    e.set_footer(text="Suggestion #%d · one vote per member" % d["id"])
    return e


class FeedbackButton(discord.ui.DynamicItem[discord.ui.Button],
                     template=r"tcp:fb:(?P<action>confirmed|fixed|norepro|notabug|duplicate|issue|up|down):(?P<ref>\d+)"):
    STYLES = {"confirmed": ("Confirmed", discord.ButtonStyle.primary), "fixed": ("Fixed", discord.ButtonStyle.success),
              "norepro": ("Can't reproduce", discord.ButtonStyle.secondary),
              "notabug": ("Not a bug", discord.ButtonStyle.secondary),
              "duplicate": ("Duplicate", discord.ButtonStyle.secondary),
              "issue": ("File on GitHub", discord.ButtonStyle.secondary),
              "up": ("👍", discord.ButtonStyle.success), "down": ("👎", discord.ButtonStyle.secondary)}

    def __init__(self, action: str, ref: int):
        label, style = self.STYLES[action]
        super().__init__(discord.ui.Button(label=label, style=style, custom_id="tcp:fb:%s:%d" % (action, ref),
                                           row=1 if action in ("duplicate", "issue") else 0))
        self.action, self.ref = action, ref

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(match["action"], int(match["ref"]))

    async def callback(self, interaction: discord.Interaction):
        cog: Feedback = interaction.client.get_cog("Feedback")
        try:
            if self.action in ("up", "down"):
                await cog.vote(interaction, self.ref, 1 if self.action == "up" else -1)
            elif self.action == "issue":
                await cog.file_issue(interaction, self.ref)
            else:
                await cog.set_bug_state(interaction, self.ref, self.action)
        except UserFacingError as e:
            send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
            await send(embed=embeds.error(str(e)), ephemeral=True)


def bug_view(d: dict, github: bool) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for a in ("confirmed", "fixed", "norepro", "notabug", "duplicate"):
        if a != d["state"]:
            v.add_item(FeedbackButton(a, d["id"]))
    if github and not d.get("issue"):
        v.add_item(FeedbackButton("issue", d["id"]))
    return v


def idea_view(d: dict) -> discord.ui.View | None:
    if d["state"] in ("shipped", "declined"):
        return None
    v = discord.ui.View(timeout=None)
    v.add_item(FeedbackButton("up", d["id"]))
    v.add_item(FeedbackButton("down", d["id"]))
    return v


# ================================================================ forms
class BugForm(discord.ui.Modal, title="Report a bug"):
    summary = discord.ui.TextInput(label="In one line, what's wrong?", max_length=100, min_length=8)
    what = discord.ui.TextInput(label="What happened, and what did you expect?", style=discord.TextStyle.paragraph,
                                max_length=1500, min_length=20)
    steps = discord.ui.TextInput(label="How can we make it happen?", style=discord.TextStyle.paragraph,
                                 max_length=800, required=False, placeholder="1. Join Official #1\n2. ...")
    where = discord.ui.TextInput(label="Game version, map and server", max_length=120, required=False,
                                 placeholder="0.34.1, Snow, Official #1")

    async def on_submit(self, interaction: discord.Interaction):
        cog: Feedback = interaction.client.get_cog("Feedback")
        await cog.new_bug(interaction, str(self.summary), str(self.what), str(self.steps), str(self.where))


class IdeaForm(discord.ui.Modal, title="Suggest something"):
    summary = discord.ui.TextInput(label="Your idea in one line", max_length=100, min_length=8)
    details = discord.ui.TextInput(label="Why would it make the game better?", style=discord.TextStyle.paragraph,
                                   max_length=1500, min_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        cog: Feedback = interaction.client.get_cog("Feedback")
        await cog.new_idea(interaction, str(self.summary), str(self.details))


# ================================================================ cog
class Feedback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.fc = bot.cfg["feedback"]

    async def cog_load(self):
        self.bot.add_dynamic_items(FeedbackButton)

    @property
    def store(self):
        return self.bot.store

    def github(self) -> bool:
        return bool(self.fc["github_repo"] and secret(self.fc["github_credential"]))

    def bug_channel(self):
        return self.bot.text_channel(self.cfg.channel("bugs", "staff"))

    def idea_channel(self):
        return self.bot.text_channel(self.cfg.channel("suggestions"))

    def throttle(self, kind: str, uid: int):
        mins = int(self.fc["bug_cooldown_minutes"])
        last = self.store.docs(kind, owner=uid, limit=1)
        if last and time.time() - last[0]["created"] < mins * 60:
            raise UserFacingError("You sent one a moment ago. You can send the next in a few minutes.")

    async def dm(self, uid: int, embed: discord.Embed):
        user = self.bot.get_user(uid)
        if user:
            try:
                await user.send(embed=embed)
            except discord.HTTPException:
                pass

    # ------------------------------------------------------------ bugs
    async def new_bug(self, interaction, title: str, what: str, steps: str, where: str):
        ch = self.bug_channel()
        if ch is None:
            raise UserFacingError("Bug reports aren't set up yet. Tell the team in chat for now.")
        d = {"title": plain(title), "what": plain(what), "steps": plain(steps), "where": plain(where), "message": 0}
        d = self.store.doc("bug", self.store.doc_add("bug", d, owner=interaction.user.id))
        msg = await ch.send(embed=bug_embed(d), view=bug_view(d, self.github()))
        d["message"], d["channel"] = msg.id, ch.id
        self.store.doc_save(d)
        await interaction.response.send_message(embed=embeds.notice(
            "Thanks, bug #%d is with the team" % d["id"],
            "You'll get a DM when its status changes. If you have a screenshot or clip, post it in chat and mention "
            "**bug #%d**." % d["id"], embeds.GREEN), ephemeral=True)

    async def refresh_bug(self, d: dict):
        ch = self.bot.text_channel(d.get("channel", 0)) or self.bug_channel()
        if ch and d.get("message"):
            try:
                await ch.get_partial_message(d["message"]).edit(embed=bug_embed(d), view=bug_view(d, self.github()))
            except discord.HTTPException as e:
                log.warning("bug card #%d: %s", d["id"], e)

    async def set_bug_state(self, interaction, ref: int, state: str):
        if not self.bot.is_staff(interaction.user):
            raise UserFacingError("Only staff can change a bug's status.")
        d = self.store.doc("bug", ref)
        if not d:
            raise UserFacingError("That report no longer exists.")
        d["state"], d["by"] = state, interaction.user.id
        self.store.doc_save(d)
        await interaction.response.edit_message(embed=bug_embed(d), view=bug_view(d, self.github()))
        label, colour, note = BUG_STATES[state]
        await self.dm(d["owner"], embeds.notice("Bug #%d · %s" % (d["id"], label), "**%s**\n%s" % (
            T.md(T.clip(d["title"], 100)), note), colour))

    async def file_issue(self, interaction, ref: int):
        if not self.bot.is_staff(interaction.user):
            raise UserFacingError("Only staff can file issues.")
        d = self.store.doc("bug", ref)
        token = secret(self.fc["github_credential"])
        if not d or not token or not self.fc["github_repo"]:
            raise UserFacingError("GitHub issues aren't configured.")
        if d.get("issue"):
            raise UserFacingError("Already filed: %s" % d["issue"])
        await interaction.response.defer(ephemeral=True)
        guild = self.bot.guild
        member = guild.get_member(d["owner"]) if guild else None
        body = "%s\n\n" % d["what"]
        if d.get("steps"):
            body += "### Steps to reproduce\n%s\n\n" % d["steps"]
        if d.get("where"):
            body += "### Version, map or server\n%s\n\n" % d["where"]
        body += "Reported on Discord by %s (bug #%d)." % (member.display_name if member else "a community member", d["id"])
        try:
            async with self.bot.http_session.post(
                    "https://api.github.com/repos/%s/issues" % self.fc["github_repo"],
                    json={"title": d["title"].replace("\u200b", ""), "body": body.replace("\u200b", ""),
                          "labels": ["bug"]},
                    headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                             "X-GitHub-Api-Version": "2022-11-28"},
                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                data = await r.json(content_type=None)
                if r.status != 201:
                    raise UserFacingError("GitHub refused the issue (%d). Check the token's access to %s." % (
                        r.status, self.fc["github_repo"]))
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            raise UserFacingError("GitHub didn't answer. Try again in a minute.") from e
        d["issue"] = data.get("html_url", "")
        self.store.doc_save(d)
        await self.refresh_bug(d)
        await interaction.followup.send(embed=embeds.notice("Filed", d["issue"]), ephemeral=True)

    # ------------------------------------------------------------ suggestions
    async def new_idea(self, interaction, title: str, details: str):
        ch = self.idea_channel()
        if ch is None:
            raise UserFacingError("Suggestions aren't open yet.")
        d = {"title": plain(title), "details": plain(details), "votes": {str(interaction.user.id): 1}, "message": 0}
        d = self.store.doc("suggestion", self.store.doc_add("suggestion", d, owner=interaction.user.id))
        msg = await ch.send(embed=idea_embed(d), view=idea_view(d))
        d["message"], d["channel"] = msg.id, ch.id
        self.store.doc_save(d)
        await interaction.response.send_message(embed=embeds.notice(
            "Posted", "Your suggestion is up for votes in %s." % ch.mention, embeds.GREEN), ephemeral=True)

    async def vote(self, interaction, ref: int, value: int):
        d = self.store.doc("suggestion", ref)
        if not d or d["state"] in ("shipped", "declined"):
            raise UserFacingError("Voting on this one is closed.")
        uid = str(interaction.user.id)
        votes = d.setdefault("votes", {})
        if votes.get(uid) == value:
            del votes[uid]                     # pressing your own vote again takes it back
        else:
            votes[uid] = value
        self.store.doc_save(d)
        await interaction.response.edit_message(embed=idea_embed(d), view=idea_view(d))

    # ------------------------------------------------------------ commands
    @app_commands.command(name="bug", description="Report a bug to the team")
    async def cmd_bug(self, interaction: discord.Interaction):
        if self.bug_channel() is None:
            raise UserFacingError("Bug reports aren't set up yet. Tell the team in chat for now.")
        self.throttle("bug", interaction.user.id)
        await interaction.response.send_modal(BugForm())

    @app_commands.command(name="suggest", description="Suggest a feature or change for the community to vote on")
    async def cmd_suggest(self, interaction: discord.Interaction):
        if self.idea_channel() is None:
            raise UserFacingError("Suggestions aren't open yet.")
        self.throttle("suggestion", interaction.user.id)
        await interaction.response.send_modal(IdeaForm())

    group = app_commands.Group(name="suggestion", description="Suggestions: the most wanted, and their status")

    @group.command(name="top", description="The most wanted open suggestions")
    async def cmd_top(self, interaction: discord.Interaction):
        rows = [d for d in self.store.docs("suggestion", limit=200) if d["state"] in ("open", "planned", "progress")]
        rows.sort(key=lambda d: -sum(d.get("votes", {}).values()))
        lines = []
        for d in rows[:10]:
            link = "https://discord.com/channels/%d/%d/%d" % (int(self.cfg["guild_id"]), d.get("channel", 0), d["message"])
            lines.append("**%+d** · [%s](%s) · %s" % (sum(d.get("votes", {}).values()), T.md(T.clip(d["title"], 70)), link,
                                                      IDEA_STATES[d["state"]][0]))
        await interaction.response.send_message(embed=embeds.notice(
            "Most wanted", "\n".join(lines) or "No open suggestions. Add yours with `/suggest`."))

    @group.command(name="status", description="Set the status of a suggestion (staff)")
    @app_commands.describe(suggestion="Suggestion number", status="New status", note="A line from the team (optional)")
    @app_commands.choices(status=[app_commands.Choice(name=v[0], value=k) for k, v in IDEA_STATES.items()])
    @staff_only()
    async def cmd_status(self, interaction: discord.Interaction, suggestion: int, status: str,
                         note: app_commands.Range[str, 0, 500] = ""):
        d = self.store.doc("suggestion", suggestion)
        if not d:
            raise UserFacingError("There's no suggestion #%d." % suggestion)
        d["state"] = status
        if note:
            d["note"] = note
        self.store.doc_save(d)
        ch = self.bot.text_channel(d.get("channel", 0)) or self.idea_channel()
        if ch and d.get("message"):
            try:
                await ch.get_partial_message(d["message"]).edit(embed=idea_embed(d), view=idea_view(d))
            except discord.HTTPException:
                pass
        if status != "open":
            await self.dm(d["owner"], embeds.notice(
                "Your suggestion is now: %s" % IDEA_STATES[status][0],
                "**%s**%s" % (T.md(T.clip(d["title"], 100)), "\n" + note if note else ""), IDEA_STATES[status][1]))
        await interaction.response.send_message(embed=embeds.notice(
            "Suggestion #%d" % d["id"], "Marked **%s**." % IDEA_STATES[status][0]), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Feedback(bot))
