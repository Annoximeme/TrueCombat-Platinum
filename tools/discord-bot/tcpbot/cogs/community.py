"""Community features: roles, welcome, the get-started panel, events and playtests."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import re
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import embeds
from ..bot import UserFacingError, staff_only
from ..sources import StatsUnavailable
from ..text import RANK_TIERS, TimeError, clean, parse_when, tier_for_level

log = logging.getLogger("tcpbot.community")

# Opt-in roles members toggle themselves
OPT_IN = {
    "alerts": ("Match alerts", 0xD63B3B, "a ping when a match is filling up"),
    "playtester": ("Playtester", 0xE7A73C, "early builds and playtest sessions"),
    "events": ("Event alerts", 0x5B9BD5, "scrims, community nights and tournaments"),
    "patchnotes": ("Patch notes", 0xC9A227, "a ping the moment a new update is out"),
    "devlog": ("Devlog", 0x4FBF7A, "a ping when a new devlog article goes live"),
}
# Roles the bot assigns
EARNED = {
    "verified": ("Verified player", 0x4FBF7A),
    "top10": ("Top 10", 0xF2C94C),
    "champion": ("Season champion", 0xC9A227),
    "clean": ("Clean record", 0x8FD3A8),
    "trusted": ("Trusted player", 0xE7A73C),
}
BADGE_ROLES = ("clean", "trusted")
for _key, _name, _first, _colour in RANK_TIERS:
    EARNED["tier_" + _key] = (_name, _colour)

EVENT_LENGTH = 2 * 3600


# ================================================================ opt-in buttons
class OptInButton(discord.ui.DynamicItem[discord.ui.Button], template=r"tcp:role:(?P<key>alerts|playtester|events|patchnotes|devlog)"):
    def __init__(self, key: str):
        super().__init__(discord.ui.Button(label=OPT_IN[key][0], style=discord.ButtonStyle.secondary,
                                           custom_id="tcp:role:%s" % key))
        self.key = key

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(match["key"])

    async def callback(self, interaction: discord.Interaction):
        bot = interaction.client
        role = bot.role(self.key)
        member = interaction.user
        if role is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(embed=embeds.error(
                "This role isn't set up yet. Staff can create it with `/setup roles`."), ephemeral=True)
            return
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Opted out")
                text = "You'll no longer get **%s**." % role.name
            else:
                await member.add_roles(role, reason="Opted in")
                text = "You'll now get **%s**: %s." % (role.name, OPT_IN[self.key][2])
        except discord.Forbidden:
            text = "I'm not allowed to change that role. Staff: move my role above it in Server Settings."
        await interaction.response.send_message(embed=embeds.notice("Notifications", text), ephemeral=True)


def _link_row(cfg) -> discord.ui.ActionRow:
    return discord.ui.ActionRow(
        discord.ui.Button(label="Download", url=cfg.site + "/download", emoji="\N{DOWNWARDS BLACK ARROW}"),
        discord.ui.Button(label="Player guide", url=cfg.site + "/guide"),
        discord.ui.Button(label="Servers", url=cfg.site + "/servers"),
        discord.ui.Button(label="Leaderboards", url=cfg.site + "/leaderboards"))


def _opt_in_lines() -> str:
    return "\n".join("**%s** · %s" % (name, about) for name, _c, about in OPT_IN.values())


def panel_layout(cfg) -> discord.ui.LayoutView:
    """The get-started panel in Discord's newer layout: banner, choices and buttons in one framed card."""
    v = discord.ui.LayoutView(timeout=None)
    v.add_item(discord.ui.Container(
        discord.ui.MediaGallery(discord.MediaGalleryItem(cfg.site + "/img/og.jpg")),
        discord.ui.TextDisplay("## Get set up\nPick what you want to hear about. Press a button again to turn "
                               "it off, any time."),
        discord.ui.Separator(),
        discord.ui.TextDisplay(_opt_in_lines()),
        discord.ui.ActionRow(*(OptInButton(k) for k in OPT_IN)),
        discord.ui.Separator(),
        discord.ui.TextDisplay("-# Link your game profile with `/link` for your rank role and `/profile`."),
        _link_row(cfg),
        accent_colour=0xD63B3B))
    return v


def welcome_layout(cfg, member: discord.Member) -> discord.ui.LayoutView:
    v = discord.ui.LayoutView(timeout=None)
    v.add_item(discord.ui.Container(
        discord.ui.Section(
            discord.ui.TextDisplay("## Welcome to the front, %s" % member.mention),
            discord.ui.TextDisplay("TrueCombat: Platinum is the modern return of TrueCombat: Elite, the tactical "
                                   "shooter built on Wolfenstein: Enemy Territory. Here is how to get into a match."),
            accessory=discord.ui.Thumbnail(member.display_avatar.url)),
        discord.ui.Separator(),
        discord.ui.TextDisplay(
            "**1 · Install** · [Download the installer](%s/download). The launcher keeps the game up to date.\n"
            "**2 · Learn the basics** · Start with the [player guide](%s/guide), then warm up against bots with "
            "**Practice** in the launcher.\n"
            "**3 · Find a match** · `/servers` shows who is playing right now.\n"
            "**4 · Make it yours** · `/link` connects your game profile for your rank role and `/profile`."
            % (cfg.site, cfg.site)),
        discord.ui.MediaGallery(discord.MediaGalleryItem(cfg.site + "/img/og.jpg")),
        discord.ui.TextDisplay("-# Choose your alerts:"),
        discord.ui.ActionRow(*(OptInButton(k) for k in OPT_IN)),
        accent_colour=0xD63B3B))
    return v


def opt_in_view(cfg) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for key in OPT_IN:
        v.add_item(OptInButton(key))
    v.add_item(discord.ui.Button(label="Download", url=cfg.site + "/#download", row=1))
    v.add_item(discord.ui.Button(label="Player guide", url=cfg.site + "/guide.html", row=1))
    return v


# ================================================================ event buttons
class RSVPButton(discord.ui.DynamicItem[discord.ui.Button], template=r"tcp:ev:(?P<action>going|maybe|leave):(?P<eid>\d+)"):
    LABELS = {"going": ("Going", discord.ButtonStyle.success), "maybe": ("Maybe", discord.ButtonStyle.secondary),
              "leave": ("Can't make it", discord.ButtonStyle.secondary)}

    def __init__(self, action: str, eid: int, disabled: bool = False):
        label, style = self.LABELS[action]
        super().__init__(discord.ui.Button(label=label, style=style, disabled=disabled,
                                           custom_id="tcp:ev:%s:%d" % (action, eid)))
        self.action, self.eid = action, eid

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(match["action"], int(match["eid"]))

    async def callback(self, interaction: discord.Interaction):
        cog: Community = interaction.client.get_cog("Community")
        await cog.rsvp(interaction, self.eid, self.action)


def event_view(eid: int, closed: bool = False) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for action in ("going", "maybe", "leave"):
        v.add_item(RSVPButton(action, eid, disabled=closed))
    return v


# ================================================================ cog
class Community(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.role_loop.change_interval(minutes=max(2, int(self.cfg["roles"]["sync_minutes"])))
        self.lock = asyncio.Lock()
        self.account_links: dict[int, dict] = {}   # Discord id -> account (statsId, badges), from the last sync

    async def cog_load(self):
        self.bot.add_dynamic_items(OptInButton, RSVPButton)
        self.role_loop.start()
        self.event_loop.start()

    async def cog_unload(self):
        self.role_loop.cancel()
        self.event_loop.cancel()

    # ------------------------------------------------------------ welcome
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot or not self.cfg["welcome"]["enabled"] or member.guild.id != int(self.cfg["guild_id"]):
            return
        e = embeds.welcome(self.cfg, member)
        channel = self.bot.text_channel(self.cfg.channel("welcome"))
        if channel:
            try:
                await channel.send(view=welcome_layout(self.cfg, member),
                                   allowed_mentions=discord.AllowedMentions(users=[member]))
            except discord.HTTPException as ex:
                log.warning("welcome post failed: %s", ex)
        if self.cfg["welcome"]["dm"]:
            try:
                await member.send(embed=e)
            except discord.HTTPException:
                pass
        if self.bot.store.linked_player(member.id):     # someone who left and came back
            await self.sync_member_roles(member.id)

    # ------------------------------------------------------------ /notify
    @app_commands.command(name="notify", description="Choose which alerts you get")
    async def notify(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=embeds.onboarding_panel(self.cfg),
                                                view=opt_in_view(self.cfg), ephemeral=True)

    # ------------------------------------------------------------ setup (staff)
    setup = app_commands.Group(name="setup", description="Set the bot up on this server (staff)",
                               default_permissions=discord.Permissions(manage_guild=True))

    @setup.command(name="roles", description="Create any missing bot roles (alerts, playtester, rank tiers, Top 10)")
    @staff_only()
    async def setup_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        ids = dict(self.bot.store.get("roles") or {})
        created, kept = [], []
        wanted = {k: (v[0], v[1]) for k, v in OPT_IN.items()}
        roles_cfg = self.cfg["roles"]
        for k, v in EARNED.items():
            if (k == "verified" and not roles_cfg["verified"]) or (k == "top10" and not roles_cfg["top10"]) \
                    or (k.startswith("tier_") and not roles_cfg["rank_tiers"]) \
                    or (k in BADGE_ROLES and not roles_cfg.get("badges", True)) \
                    or (k == "champion" and not (self.cfg["seasons"]["enabled"] and self.cfg["seasons"]["champion_role"])):
                continue
            wanted[k] = v
        for key, (name, colour) in wanted.items():
            role = guild.get_role(int(ids.get(key) or 0)) or discord.utils.get(guild.roles, name=name)
            if role is None:
                try:
                    role = await guild.create_role(name=name, colour=discord.Colour(colour),
                                                   mentionable=key in OPT_IN,
                                                   hoist=key in ("top10",),
                                                   reason="TrueCombat bot setup")
                except discord.Forbidden as e:
                    raise UserFacingError("I need the **Manage Roles** permission to create roles.") from e
                created.append(role)
            else:
                kept.append(role)
            ids[key] = role.id
        self.bot.store.set("roles", ids)
        lines = []
        if created:
            lines.append("Created: " + ", ".join(r.mention for r in created))
        if kept:
            lines.append("Already there: " + ", ".join(r.mention for r in kept))
        me = guild.me
        low = [r for r in created + kept if r >= me.top_role]
        if low:
            lines.append("\n**One step left:** in Server Settings → Roles, drag my role above %s so I can "
                         "assign them." % ", ".join(r.mention for r in low))
        await interaction.followup.send(embed=embeds.notice("Roles ready", "\n".join(lines)), ephemeral=True)
        self.role_loop.restart()

    @setup.command(name="panel", description="Post the get-started panel with alert buttons in this channel")
    @staff_only()
    async def setup_panel(self, interaction: discord.Interaction):
        await interaction.channel.send(view=panel_layout(self.cfg))
        await interaction.response.send_message(embed=embeds.notice("Panel posted", "Members can pick their "
                                                "alerts here at any time."), ephemeral=True)

    @setup.command(name="check", description="Check the bot's configuration, channels and permissions")
    @staff_only()
    async def setup_check(self, interaction: discord.Interaction):
        cfg, guild = self.cfg, interaction.guild
        me = guild.me
        lines = []
        for problem in cfg.problems:
            lines.append("✗ " + problem)
        need = ("send_messages", "embed_links", "view_channel")
        for name in ("status", "feed", "announcements", "devlog", "welcome", "staff", "events", "reports",
                     "matches", "teams", "bugs", "suggestions", "votes", "support"):
            cid = cfg.channel(name)
            if not cid:
                lines.append("· channels.%s is not set%s" % (name, {
                    "feed": " (uses the status channel)", "devlog": " (uses announcements)",
                    "events": " (uses announcements)", "reports": " (uses staff)", "matches": " (uses feed)",
                    "teams": " (uses events)", "bugs": " (uses staff)", "votes": " (uses announcements)",
                    "support": " (uses staff)", "suggestions": " (`/suggest` stays off)"}.get(name, "")))
                continue
            ch = guild.get_channel(cid)
            if ch is None:
                lines.append("✗ channels.%s: channel %d not found" % (name, cid))
                continue
            p = ch.permissions_for(me)
            missing = [x for x in need if not getattr(p, x)]
            lines.append(("✗ %s missing %s" % (ch.mention, ", ".join(missing))) if missing else "✓ %s" % ch.mention)
        if not me.guild_permissions.manage_roles:
            lines.append("✗ Manage Roles is missing (rank and alert roles won't work)")
        if not me.guild_permissions.manage_events:
            lines.append("· Manage Events is missing (events won't appear in the Discord event list)")
        if not me.guild_permissions.manage_guild:
            lines.append("· Manage Server is missing (only needed for `/mod raid` and `/mod automod`)")
        ids = self.bot.store.get("roles") or {}
        if not ids:
            lines.append("· Roles not set up yet: run `/setup roles`")
        elif cfg["seasons"]["enabled"] and cfg["seasons"]["champion_role"] and not ids.get("champion"):
            lines.append("· Season champion role missing: run `/setup roles` again")
        await interaction.response.send_message(embed=embeds.notice("Setup check", "\n".join(lines) or "All good."),
                                                ephemeral=True)

    # ------------------------------------------------------------ rank roles
    @tasks.loop(minutes=10)
    async def role_loop(self):
        try:
            await self.sync_all_roles()
        except StatsUnavailable:
            pass
        except Exception:  # noqa: BLE001
            log.exception("role sync failed")

    @role_loop.before_loop
    async def before_roles(self):
        await self.bot.wait_until_ready()

    async def _top10(self) -> set[str]:
        if not self.cfg["roles"]["top10"]:
            return set()
        board = await self.bot.stats.leaderboard("rating", "all", 10, fresh=True)
        return {p["id"] for p in (board or {}).get("players", [])}

    async def sync_all_roles(self):
        guild = self.bot.guild
        if guild is None or not self.bot.store.get("roles"):
            return
        top = await self._top10()
        linked = {r["discord_id"]: r for r in self.bot.store.all_links()}
        accounts = await self.account_roles()
        if accounts is not None:
            self.account_links = accounts
        for uid, a in self.account_links.items():
            # an account is the stronger link: its stats id holds every linked PC
            linked[uid] = dict(linked.get(uid) or {}, discord_id=uid, pid=a["statsId"], badges=a.get("badges") or [])
        # members who hold a bot-assigned role but are no longer linked
        managed = {self.bot.role_id(k) for k in EARNED if k != "champion"} - {0}   # champion: see highlights
        holders = {m.id for rid in managed if (r := guild.get_role(rid)) for m in r.members}
        for uid in set(linked) | holders:
            await self.sync_member_roles(uid, top=top, link=linked.get(uid))
            await asyncio.sleep(0.2)   # stay well under Discord's role-edit rate limit

    async def account_roles(self) -> dict[int, dict] | None:
        """Accounts by Discord id, or None when the account service is off or not answering."""
        api = getattr(self.bot, "accounts", None)
        if api is None or not api.ready:
            return None
        try:
            rows = await api.roles()
        except Exception as e:  # noqa: BLE001
            log.warning("account roles unavailable: %s", e)
            return None
        out = {}
        for r in rows:
            try:
                out[int(r["discordId"])] = r
            except (KeyError, TypeError, ValueError):
                continue
        return out

    async def sync_member_roles(self, user_id: int, top: set[str] | None = None, link=None):
        guild = self.bot.guild
        if guild is None or not self.bot.store.get("roles"):
            return
        member = guild.get_member(user_id)
        if member is None:
            return
        if link is None:
            a = self.account_links.get(user_id)
            link = dict(self.bot.store.linked_player(user_id) or {}, discord_id=user_id, pid=a["statsId"],
                        badges=a.get("badges") or []) if a else self.bot.store.linked_player(user_id)
        want: set[int] = set()
        if link:
            if top is None:
                try:
                    top = await self._top10()
                except StatsUnavailable:
                    top = set()
            try:
                p = await self.bot.stats.player(link["pid"])
            except StatsUnavailable:
                return            # don't strip roles because the stats service is down
            if p:
                self.bot.store.rename_link(link["pid"], clean(p["name"]))
                if self.cfg["roles"]["rank_tiers"]:
                    want.add(self.bot.role_id("tier_" + tier_for_level(p["rank"]["level"])))
            if self.cfg["roles"]["verified"]:
                want.add(self.bot.role_id("verified"))
            if link["pid"] in (top or set()):
                want.add(self.bot.role_id("top10"))
            if self.cfg["roles"].get("badges", True):
                for b in (link.get("badges") if isinstance(link, dict) else None) or []:
                    if b in BADGE_ROLES:
                        want.add(self.bot.role_id(b))
        want.discard(0)
        managed = {self.bot.role_id(k) for k in EARNED if k != "champion"} - {0}   # champion: see highlights
        if not (isinstance(link, dict) and "badges" in link) and not self.account_links:
            # the account service has not answered yet: leave badge roles as they are
            managed -= {self.bot.role_id(k) for k in BADGE_ROLES}
        have = {r.id for r in member.roles} & managed
        add = [guild.get_role(r) for r in want - have]
        remove = [guild.get_role(r) for r in have - want]
        try:
            if add:
                await member.add_roles(*[r for r in add if r], reason="Linked profile")
            if remove:
                await member.remove_roles(*[r for r in remove if r], reason="Linked profile")
        except discord.Forbidden:
            log.warning("cannot change roles for %s: move the bot role above the managed roles", member)
        except discord.HTTPException as e:
            log.warning("role update for %s failed: %s", member, e)

    # ------------------------------------------------------------ events
    event = app_commands.Group(name="event", description="Events and playtests (staff)",
                               default_permissions=discord.Permissions(manage_events=True))

    @event.command(name="create", description="Announce an event or playtest with sign-up buttons")
    @app_commands.describe(
        title="For example: Friday night scrims",
        when="Start time in Belgian time, e.g. sat 20:00, tomorrow 21:30 or 2026-11-15 20:00",
        kind="Event or playtest (playtests ping the Playtester role)",
        details="What it's about, rules, what to bring",
        slots="Maximum players (0 = no limit). Extra sign-ups go on a waitlist",
        server="Server address players should join, e.g. 2.24.59.195:27960")
    @app_commands.choices(kind=[app_commands.Choice(name="Event", value="event"),
                                app_commands.Choice(name="Playtest", value="playtest")])
    @staff_only()
    async def event_create(self, interaction: discord.Interaction, title: app_commands.Range[str, 3, 100],
                           when: str, kind: str = "event", details: app_commands.Range[str, 0, 1500] = "",
                           slots: app_commands.Range[int, 0, 64] = 0, server: str = ""):
        try:
            starts = parse_when(when, self.cfg["timezone"])
        except TimeError as e:
            raise UserFacingError(str(e)) from e
        server = server.strip()
        if server and not re.fullmatch(r"[A-Za-z0-9.-]+(:\d{1,5})?", server):
            raise UserFacingError("The server should look like `2.24.59.195:27960`.")
        channel = self.bot.text_channel(self.cfg.channel("events", "announcements")) or interaction.channel
        await interaction.response.defer(ephemeral=True, thinking=True)
        eid = self.bot.store.add_event(kind, title.strip(), details.strip(), int(starts.timestamp()), slots, server,
                                       interaction.user.id)
        ev = self.bot.store.event(eid)
        role = self.bot.role("playtester" if kind == "playtest" else "events")
        msg = await channel.send(content=role.mention if role else None,
                                 embed=embeds.event_card(self.cfg, ev, {}, interaction.user.display_name),
                                 view=event_view(eid),
                                 allowed_mentions=discord.AllowedMentions(roles=[role] if role else False))
        fields = {"channel_id": channel.id, "message_id": msg.id}
        if self.cfg["events"]["create_discord_event"] and interaction.guild.me.guild_permissions.manage_events:
            try:
                se = await interaction.guild.create_scheduled_event(
                    name=title.strip()[:100], start_time=starts, end_time=starts + dt.timedelta(seconds=EVENT_LENGTH),
                    entity_type=discord.EntityType.external, privacy_level=discord.PrivacyLevel.guild_only,
                    location=("/connect " + server) if server else "TrueCombat: Platinum",
                    description=(details.strip() + "\n\nSign up: " + msg.jump_url)[:1000])
                fields["scheduled_id"] = se.id
            except discord.HTTPException as e:
                log.warning("scheduled event failed: %s", e)
        self.bot.store.update_event(eid, **fields)
        await interaction.followup.send(embed=embeds.notice(
            "%s posted" % ("Playtest" if kind == "playtest" else "Event"),
            "[%s](%s) starts <t:%d:F>. I'll remind everyone who signed up %d minutes before." % (
                title, msg.jump_url, int(starts.timestamp()), self.cfg["events"]["reminder_minutes"])), ephemeral=True)

    async def _event_choices(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=("#%d · %s" % (e["id"], e["title"]))[:100], value=e["id"])
                for e in self.bot.store.open_events() if current.lower() in e["title"].lower()][:25]

    @event.command(name="cancel", description="Cancel an event and tell everyone who signed up")
    @app_commands.autocomplete(event=_event_choices)
    @staff_only()
    async def event_cancel(self, interaction: discord.Interaction, event: int, reason: str = ""):
        ev = self.bot.store.event(event)
        if not ev or ev["state"] != "open":
            raise UserFacingError("That event isn't open.")
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.bot.store.update_event(event, state="cancelled")
        await self.refresh_card(event)
        r = self.bot.store.rsvps(event)
        people = r.get("going", []) + r.get("maybe", []) + r.get("waitlist", [])
        channel = self.bot.text_channel(ev["channel_id"])
        if channel and people:
            await channel.send("**%s** is cancelled%s. %s" % (
                ev["title"], (": " + reason.strip()) if reason.strip() else "",
                " ".join("<@%d>" % u for u in people[:50])),
                allowed_mentions=discord.AllowedMentions(users=[discord.Object(u) for u in people[:50]]))
        if ev["scheduled_id"] and interaction.guild:
            try:
                se = await interaction.guild.fetch_scheduled_event(ev["scheduled_id"])
                await se.cancel()
            except discord.HTTPException:
                pass
        await interaction.followup.send(embed=embeds.notice("Event cancelled", ev["title"]), ephemeral=True)

    @app_commands.command(name="events", description="Upcoming events and playtests")
    async def events(self, interaction: discord.Interaction):
        rows = self.bot.store.open_events()
        e = discord.Embed(title="Upcoming", colour=embeds.RED)
        if not rows:
            e.description = "Nothing scheduled right now. Turn on **Event alerts** with `/notify` to hear first."
        else:
            lines = []
            for ev in rows[:10]:
                r = self.bot.store.rsvps(ev["id"])
                link = "https://discord.com/channels/%d/%d/%d" % (interaction.guild_id or 0, ev["channel_id"],
                                                                 ev["message_id"])
                lines.append("**[%s](%s)** · %s · <t:%d:F> · %d going" % (
                    ev["title"], link, "Playtest" if ev["kind"] == "playtest" else "Event", ev["starts"],
                    len(r.get("going", []))))
            e.description = "\n".join(lines)
        await interaction.response.send_message(embed=e, ephemeral=True)

    async def rsvp(self, interaction: discord.Interaction, eid: int, action: str):
        async with self.lock:     # keeps the capacity count exact when people click at once
            ev = self.bot.store.event(eid)
            if not ev or ev["state"] != "open":
                await interaction.response.send_message(embed=embeds.error("Sign-ups for this event are closed."),
                                                        ephemeral=True)
                return
            uid = interaction.user.id
            current = self.bot.store.rsvp_status(eid, uid)
            promoted = None
            if action == "leave":
                self.bot.store.rsvp(eid, uid, None)
                text = "You're off the list." if current else "You weren't signed up."
                if current == "going":
                    promoted = self._promote(eid, ev)
            elif action == "maybe":
                self.bot.store.rsvp(eid, uid, "maybe")
                text = "Marked as maybe."
                if current == "going":
                    promoted = self._promote(eid, ev)
            else:
                going = self.bot.store.rsvps(eid).get("going", [])
                if current == "going":
                    text = "You're already signed up."
                elif ev["capacity"] and len(going) >= ev["capacity"]:
                    self.bot.store.rsvp(eid, uid, "waitlist")
                    text = "The event is full, so you're on the waitlist. You'll move up automatically."
                else:
                    self.bot.store.rsvp(eid, uid, "going")
                    text = "You're in. I'll remind you %d minutes before it starts." % (
                        self.cfg["events"]["reminder_minutes"])
        await interaction.response.send_message(embed=embeds.notice(ev["title"], text), ephemeral=True)
        await self.refresh_card(eid)
        if promoted:
            channel = self.bot.text_channel(ev["channel_id"])
            if channel:
                await channel.send("<@%d>, a spot opened up for **%s** and it's yours." % (promoted, ev["title"]),
                                   allowed_mentions=discord.AllowedMentions(users=[discord.Object(promoted)]))

    def _promote(self, eid: int, ev) -> int | None:
        r = self.bot.store.rsvps(eid)
        if ev["capacity"] and r.get("waitlist") and len(r.get("going", [])) < ev["capacity"]:
            uid = r["waitlist"][0]
            self.bot.store.rsvp(eid, uid, "going")
            return uid
        return None

    async def refresh_card(self, eid: int):
        ev = self.bot.store.event(eid)
        channel = self.bot.text_channel(ev["channel_id"]) if ev else None
        if not channel or not ev["message_id"]:
            return
        host = None
        if self.bot.guild and (m := self.bot.guild.get_member(ev["created_by"])):
            host = m.display_name
        try:
            await channel.get_partial_message(ev["message_id"]).edit(
                embed=embeds.event_card(self.cfg, ev, self.bot.store.rsvps(eid), host),
                view=event_view(eid, closed=ev["state"] != "open"))
        except discord.HTTPException as e:
            log.warning("event card %d: %s", eid, e)

    @tasks.loop(minutes=1)
    async def event_loop(self):
        now = int(time.time())
        lead = int(self.cfg["events"]["reminder_minutes"]) * 60
        for ev in self.bot.store.open_events():
            try:
                if not ev["reminded"] and ev["starts"] - lead <= now < ev["starts"] + 600:
                    self.bot.store.update_event(ev["id"], reminded=1)
                    await self.remind(ev)
                elif now >= ev["starts"] + EVENT_LENGTH:
                    self.bot.store.update_event(ev["id"], state="done")
                    await self.refresh_card(ev["id"])
            except Exception:  # noqa: BLE001
                log.exception("event %d", ev["id"])

    @event_loop.before_loop
    async def before_events(self):
        await self.bot.wait_until_ready()

    async def remind(self, ev):
        going = self.bot.store.rsvps(ev["id"]).get("going", [])
        channel = self.bot.text_channel(ev["channel_id"])
        if not channel or not going:
            return
        text = "**%s** starts <t:%d:R>." % (ev["title"], ev["starts"])
        if ev["server"]:
            text += " Join with `/connect %s`." % ev["server"]
        text += "\n" + " ".join("<@%d>" % u for u in going[:80])
        await channel.send(text, allowed_mentions=discord.AllowedMentions(users=[discord.Object(u) for u in going[:80]]))


async def setup(bot):
    await bot.add_cog(Community(bot))
