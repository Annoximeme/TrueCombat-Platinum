"""Raid watch, AutoMod set-up, ban appeals and /ask.

The bot doesn't read messages, so message filtering is handed to Discord's own
AutoMod (/mod automod creates the rules). What the bot adds is what Discord
doesn't do: noticing a wave of joins, a pause button for invites, an appeal
form for game bans, and instant answers to common questions.
"""

from __future__ import annotations

import collections
import datetime as dt
import logging
import re
import time

import discord
from discord import app_commands
from discord.ext import commands

from .. import embeds, faq
from .. import text as T
from ..bot import UserFacingError, staff_only

log = logging.getLogger("tcpbot.support")
RULE_PREFIX = "TrueCombat · "


def plain(text: str) -> str:
    return (text or "").strip().replace("@", "@​")


# ================================================================ buttons
class SupportButton(discord.ui.DynamicItem[discord.ui.Button],
                    template=r"tcp:sup:(?P<action>raid|accept|deny|staff):(?P<ref>\d+)"):
    STYLES = {"raid": ("Pause invites for 30 minutes", discord.ButtonStyle.danger),
              "accept": ("Accept appeal", discord.ButtonStyle.success), "deny": ("Deny appeal", discord.ButtonStyle.danger),
              "staff": ("Ask staff instead", discord.ButtonStyle.secondary)}

    def __init__(self, action: str, ref: int = 0):
        label, style = self.STYLES[action]
        super().__init__(discord.ui.Button(label=label, style=style, custom_id="tcp:sup:%s:%d" % (action, ref)))
        self.action, self.ref = action, ref

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(match["action"], int(match["ref"]))

    async def callback(self, interaction: discord.Interaction):
        cog: Support = interaction.client.get_cog("Support")
        try:
            await getattr(cog, "on_" + self.action)(interaction, self.ref)
        except UserFacingError as e:
            send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
            await send(embed=embeds.error(str(e)), ephemeral=True)


def one(action: str, ref: int = 0) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    v.add_item(SupportButton(action, ref))
    return v


class AppealForm(discord.ui.Modal, title="Appeal a game ban"):
    name = discord.ui.TextInput(label="Your in-game name", max_length=36, min_length=2)
    what = discord.ui.TextInput(label="What happened?", style=discord.TextStyle.paragraph, max_length=1000, min_length=20,
                                placeholder="When you were banned, on which server, and what led to it.")
    why = discord.ui.TextInput(label="Why should the ban be lifted?", style=discord.TextStyle.paragraph,
                               max_length=1000, min_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        cog: Support = interaction.client.get_cog("Support")
        await cog.new_appeal(interaction, str(self.name), str(self.what), str(self.why))


def appeal_embed(cfg, d: dict) -> discord.Embed:
    state = d["state"]
    colour = {"open": embeds.AMBER, "accepted": embeds.GREEN, "denied": embeds.STEEL}[state]
    e = discord.Embed(title="Ban appeal #%d · %s" % (d["id"], T.md(T.clean(d["name"]))), colour=colour)
    if d.get("pid"):
        e.url = embeds.profile_url(cfg.site, d["pid"])
    e.add_field(name="What happened", value=T.clip(d["what"], 1024), inline=False)
    e.add_field(name="Why lift it", value=T.clip(d["why"], 1024), inline=False)
    e.add_field(name="From", value="<@%d>" % d["owner"], inline=True)
    e.add_field(name="Earlier appeals", value=str(d.get("earlier", 0)), inline=True)
    if state == "open":
        e.set_footer(text="Accepting doesn't lift the ban by itself: use /admin unban, then press Accept.")
    else:
        e.add_field(name="Decision", value="%s by <@%d>" % (state.title(), d.get("by", 0)), inline=True)
    return e


# ================================================================ cog
class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.mc = bot.cfg["moderation"]
        self.joins: collections.deque = collections.deque(maxlen=200)
        self.alerted = 0.0

    async def cog_load(self):
        self.bot.add_dynamic_items(SupportButton)

    def staff_channel(self):
        return self.bot.text_channel(self.cfg.channel("staff"))

    def support_channel(self):
        return self.bot.text_channel(self.cfg.channel("support", "staff"))

    # ------------------------------------------------------------ raid watch
    def note_join(self, member, now: float) -> list | None:
        """Records a join. Returns the recent joiners when this one makes it a wave."""
        self.joins.append((now, member))
        window = float(self.mc["raid_seconds"])
        recent = [m for t, m in self.joins if now - t <= window]
        if len(recent) >= int(self.mc["raid_joins"]) and now - self.alerted > 600:
            self.alerted = now
            return recent
        return None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != int(self.cfg["guild_id"]) or member.bot:
            return
        wave = self.note_join(member, time.time())
        ch = self.staff_channel()
        if wave and ch:
            await ch.send(embed=self.raid_embed(wave), view=one("raid"))

    def raid_embed(self, wave: list) -> discord.Embed:
        now = dt.datetime.now(dt.timezone.utc)
        fresh_days = int(self.mc["new_account_days"])
        lines, fresh = [], 0
        for m in wave[-20:]:
            age = (now - m.created_at).days
            fresh += age < fresh_days
            lines.append("<@%d> · account %s" % (m.id, "created today" if age < 1 else "%d days old" % age))
        e = discord.Embed(title="Join wave: %d members in %d seconds" % (len(wave), int(self.mc["raid_seconds"])),
                          colour=embeds.RED, description="\n".join(lines)[:3900])
        e.add_field(name="New accounts", value="%d of the last %d are younger than %d days" % (
            fresh, min(len(wave), 20), fresh_days), inline=False)
        e.set_footer(text="If this is an event or a shout-out, ignore it. If not, pause invites and check the list.")
        return e

    async def pause_invites(self, minutes: int | None) -> str:
        guild = self.bot.guild
        if guild is None:
            raise UserFacingError("I can't see the server right now.")
        until = None if not minutes else dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=minutes)
        try:
            await guild.edit(invites_disabled_until=until, reason="Raid watch")
        except discord.Forbidden as e:
            raise UserFacingError("I need the **Manage Server** permission to pause invites. You can do it by hand "
                                  "under Server Settings → Invites.") from e
        except discord.HTTPException as e:
            raise UserFacingError("Discord refused that (%s)." % e.text) from e
        return "Invites are paused until <t:%d:t>. Nobody new can join until then." % until.timestamp() if until \
            else "Invites are open again."

    async def on_raid(self, interaction, _ref: int):
        if not self.bot.is_staff(interaction.user):
            raise UserFacingError("Only staff can do that.")
        await interaction.response.defer()
        text = await self.pause_invites(int(self.mc["raid_minutes"]))
        await interaction.followup.send(embed=embeds.notice("Raid mode", "%s Turned on by %s. `/mod raid` opens them "
                                                            "again sooner." % (text, interaction.user.mention), embeds.AMBER))

    group = app_commands.Group(name="mod", description="Moderation tools",
                               default_permissions=discord.Permissions(manage_guild=True))

    @group.command(name="raid", description="Pause or reopen invites during a join wave (staff)")
    @app_commands.describe(state="Pause invites or open them again", minutes="How long to pause for")
    @app_commands.choices(state=[app_commands.Choice(name="Pause invites", value="on"),
                                 app_commands.Choice(name="Open invites", value="off")])
    @staff_only()
    async def cmd_raid(self, interaction: discord.Interaction, state: str, minutes: app_commands.Range[int, 5, 1440] = 30):
        await interaction.response.defer(ephemeral=True)
        text = await self.pause_invites(minutes if state == "on" else None)
        await interaction.followup.send(embed=embeds.notice("Raid mode", text, embeds.AMBER), ephemeral=True)

    def automod_rules(self, alert: discord.abc.Snowflake | None):
        A, T_ = discord.AutoModRuleAction, discord.AutoModTrigger
        block = A(custom_message="That message was stopped by the server's filter.")
        alerts = [A(channel_id=alert.id)] if alert else []
        return [
            ("Mention spam", T_(type=discord.AutoModRuleTriggerType.mention_spam, mention_limit=6),
             [block, A(duration=dt.timedelta(minutes=10))] + alerts),
            ("Spam", T_(type=discord.AutoModRuleTriggerType.spam), [A()] + alerts),
            ("Slurs and explicit content", T_(presets=discord.AutoModPresets(slurs=True, sexual_content=True)),
             [block] + alerts),
        ]

    @group.command(name="automod", description="Create Discord AutoMod rules for spam, mention floods and slurs (staff)")
    @staff_only()
    async def cmd_automod(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True)
        try:
            have = {r.name for r in await guild.fetch_automod_rules()}
        except discord.Forbidden as e:
            raise UserFacingError("I need the **Manage Server** permission to set up AutoMod.") from e
        lines = []
        for name, trigger, actions in self.automod_rules(self.staff_channel()):
            full = RULE_PREFIX + name
            if full in have:
                lines.append("**%s**: already there" % name)
                continue
            try:
                await guild.create_automod_rule(name=full, event_type=discord.AutoModRuleEventType.message_send,
                                                trigger=trigger, actions=actions, enabled=True,
                                                reason="Set up with /mod automod")
                lines.append("**%s**: created" % name)
            except discord.HTTPException as e:
                lines.append("**%s**: not created (%s)" % (name, e.text or e.status))
        lines.append("\nBlocked messages are reported in the staff channel. Fine-tune the rules under "
                     "Server Settings → AutoMod; staff with Manage Server are never filtered.")
        await interaction.followup.send(embed=embeds.notice("AutoMod", "\n".join(lines)), ephemeral=True)

    # ------------------------------------------------------------ appeals
    @app_commands.command(name="appeal", description="Appeal a ban from the game servers")
    async def cmd_appeal(self, interaction: discord.Interaction):
        if self.support_channel() is None:
            raise UserFacingError("Appeals aren't set up yet. Message a staff member directly.")
        mine = self.bot.store.docs("appeal", owner=interaction.user.id, limit=5)
        if any(d["state"] == "open" for d in mine):
            raise UserFacingError("Your appeal is with staff already. You'll get a DM when it's decided.")
        days = int(self.mc["appeal_cooldown_days"])
        denied = [d for d in mine if d["state"] == "denied" and time.time() - d.get("decided", 0) < days * 86400]
        if denied:
            raise UserFacingError("Your last appeal was denied. You can appeal again <t:%d:R>." % (
                denied[0]["decided"] + days * 86400))
        await interaction.response.send_modal(AppealForm())

    async def new_appeal(self, interaction, name: str, what: str, why: str):
        ch = self.support_channel()
        if ch is None:
            raise UserFacingError("Appeals aren't set up yet. Message a staff member directly.")
        uid = interaction.user.id
        link = self.bot.store.linked_player(uid)
        d = {"name": plain(name), "what": plain(what), "why": plain(why), "pid": link["pid"] if link else "",
             "earlier": len(self.bot.store.docs("appeal", owner=uid)), "message": 0}
        d = self.bot.store.doc("appeal", self.bot.store.doc_add("appeal", d, owner=uid))
        v = discord.ui.View(timeout=None)
        v.add_item(SupportButton("accept", d["id"]))
        v.add_item(SupportButton("deny", d["id"]))
        msg = await ch.send(embed=appeal_embed(self.cfg, d), view=v)
        d["message"], d["channel"] = msg.id, ch.id
        self.bot.store.doc_save(d)
        await interaction.response.send_message(embed=embeds.notice(
            "Appeal received", "Staff will read it and you'll get the answer by DM. Please keep your DMs open for "
            "this server.", embeds.GREEN), ephemeral=True)

    async def decide(self, interaction, ref: int, state: str):
        if not self.bot.is_staff(interaction.user):
            raise UserFacingError("Only staff can decide appeals.")
        d = self.bot.store.doc("appeal", ref)
        if not d or d["state"] != "open":
            raise UserFacingError("This appeal has already been decided.")
        d["state"], d["by"], d["decided"] = state, interaction.user.id, int(time.time())
        self.bot.store.doc_save(d)
        await interaction.response.edit_message(embed=appeal_embed(self.cfg, d), view=None)
        user = self.bot.get_user(d["owner"])
        if user:
            text = ("Your appeal was accepted and the ban has been lifted. See you on the servers, and thanks for "
                    "sorting it out the right way.") if state == "accepted" else (
                "Staff looked at your appeal and the ban stays in place. You can appeal again in %d days."
                % int(self.mc["appeal_cooldown_days"]))
            try:
                await user.send(embed=embeds.notice("Your ban appeal", text,
                                                    embeds.GREEN if state == "accepted" else embeds.STEEL))
            except discord.HTTPException:
                pass

    async def on_accept(self, interaction, ref: int):
        await self.decide(interaction, ref, "accepted")

    async def on_deny(self, interaction, ref: int):
        await self.decide(interaction, ref, "denied")

    # ------------------------------------------------------------ /ask
    def fill(self, text: str) -> str:
        return text.replace("{site}", self.cfg.site).replace("{invite}", self.cfg["discord_invite"])

    def answer(self, question: str) -> discord.Embed | None:
        hits = faq.search(question)
        if not hits:
            return None
        q, a, _extra, url = faq.ENTRIES[hits[0][0]]
        e = discord.Embed(title=q, description=self.fill(a), colour=embeds.RED)
        if url:
            e.url = self.cfg.site + url
        more = [faq.ENTRIES[i][0] for i, s in hits[1:] if s >= hits[0][1] * 0.5]
        if more:
            e.add_field(name="Related", value="\n".join("· " + m for m in more), inline=False)
        e.set_footer(text="Answers are written by the team. Not what you were after? Ask staff.")
        return e

    async def _questions(self, interaction: discord.Interaction, current: str):
        if len(current.strip()) < 2:
            picks = range(min(10, len(faq.ENTRIES)))
        else:
            picks = [i for i, _ in faq.search(current, 10)]
        return [app_commands.Choice(name=faq.ENTRIES[i][0][:100], value=faq.ENTRIES[i][0][:100]) for i in picks]

    @app_commands.command(name="ask", description="Get an answer to a question about the game, right away")
    @app_commands.describe(question="Your question, in your own words")
    @app_commands.autocomplete(question=_questions)
    @app_commands.checks.cooldown(3, 20.0)
    async def cmd_ask(self, interaction: discord.Interaction, question: app_commands.Range[str, 3, 200]):
        if not self.cfg["support"]["enabled"]:
            raise UserFacingError("`/ask` is switched off right now. Ask in chat and someone will help.")
        e = self.answer(question)
        ref = self.bot.store.doc_add("question", {"q": plain(question), "answered": bool(e)}, owner=interaction.user.id)
        can_escalate = self.support_channel() is not None
        if e is None:
            e = embeds.notice("I don't have that one", "I only know the questions the team has written answers for."
                              + (" Press the button and staff will pick it up." if can_escalate else
                                 " Ask in chat and someone will help."), embeds.STEEL)
        if can_escalate:
            await interaction.response.send_message(embed=e, view=one("staff", ref), ephemeral=True)
        else:
            await interaction.response.send_message(embed=e, ephemeral=True)

    async def on_staff(self, interaction, ref: int):
        d = self.bot.store.doc("question", ref)
        ch = self.support_channel()
        if not d or ch is None or d["owner"] != interaction.user.id:
            raise UserFacingError("That question can't be passed on any more. Ask it in chat.")
        if d["state"] != "open":
            raise UserFacingError("Staff already have this question.")
        d["state"] = "sent"
        self.bot.store.doc_save(d)
        e = embeds.notice("Question for staff", T.clip(d["q"], 1000), embeds.BLUE)
        e.add_field(name="From", value=interaction.user.mention, inline=True)
        e.add_field(name="Bot had an answer", value="Yes, but it didn't help" if d.get("answered") else "No", inline=True)
        e.set_footer(text="Worth adding to tcpbot/faq.py if it comes up again.")
        await ch.send(embed=e)
        await interaction.response.send_message(embed=embeds.notice(
            "Passed on", "Staff have your question and will get back to you here on Discord.", embeds.GREEN), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Support(bot))
