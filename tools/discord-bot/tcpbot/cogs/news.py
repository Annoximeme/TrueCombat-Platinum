"""Release and devlog announcements.

Releases: the bot watches GitHub. With releases.mode "draft" (the default) a
new release is staged in the private staff channel with Publish, Add patch
notes and Skip buttons; nothing reaches the community until staff press
Publish. With "auto" the published GitHub release is itself the approval.

Devlog: new articles in the website's Atom feed are posted automatically
(they are already public on the site).
"""

from __future__ import annotations

import logging
import re

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import embeds
from ..bot import UserFacingError, staff_only
from ..sources import article_meta, load_devlog, release_download, release_version
from ..text import split_notes

log = logging.getLogger("tcpbot.news")
KEEP = ("id", "tag_name", "name", "body", "html_url", "published_at", "assets")


def slim(rel: dict) -> dict:
    out = {k: rel.get(k) for k in KEEP}
    out["assets"] = [{"name": a.get("name"), "browser_download_url": a.get("browser_download_url")}
                     for a in rel.get("assets") or []]
    return out


def release_buttons(cfg, rel: dict) -> discord.ui.View:
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Download", url=release_download(rel) or cfg.site + "/#download"))
    v.add_item(discord.ui.Button(label="Patch notes", url=cfg.site + "/news.html"))
    return v


class DraftButton(discord.ui.DynamicItem[discord.ui.Button],
                  template=r"tcp:rel:(?P<action>publish|notes|skip):(?P<rid>\d+)"):
    LABELS = {"publish": ("Publish", discord.ButtonStyle.success),
              "notes": ("Add patch notes", discord.ButtonStyle.primary),
              "skip": ("Skip", discord.ButtonStyle.secondary)}

    def __init__(self, action: str, rid: int):
        label, style = self.LABELS[action]
        super().__init__(discord.ui.Button(label=label, style=style, custom_id="tcp:rel:%s:%d" % (action, rid)))
        self.action, self.rid = action, rid

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(match["action"], int(match["rid"]))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.client.is_staff(interaction.user):
            return True
        await interaction.response.send_message(embed=embeds.error("This is for staff."), ephemeral=True)
        return False

    async def callback(self, interaction: discord.Interaction):
        news: News = interaction.client.get_cog("News")
        draft = news.draft(self.rid)
        if not draft or draft.get("state") != "waiting":
            await interaction.response.send_message(embed=embeds.error("This release was already handled."),
                                                    ephemeral=True)
            return
        if self.action == "notes":
            await interaction.response.send_modal(NotesModal(self.rid))
        elif self.action == "skip":
            draft["state"] = "skipped"
            news.save_draft(self.rid, draft)
            await interaction.response.edit_message(
                content="**%s** · skipped by %s. Nothing was posted." % (
                    release_version(draft["release"]), interaction.user.mention),
                view=None, allowed_mentions=discord.AllowedMentions.none())
        else:
            await interaction.response.defer()
            ok, where = await news.publish(self.rid)
            if ok:
                await interaction.edit_original_response(
                    content="**%s** · published by %s in %s." % (
                        release_version(draft["release"]), interaction.user.mention, where),
                    view=None, allowed_mentions=discord.AllowedMentions.none())
            else:
                await interaction.followup.send(embed=embeds.error(where), ephemeral=True)


def draft_view(rid: int) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for action in ("publish", "notes", "skip"):
        v.add_item(DraftButton(action, rid))
    return v


class NotesModal(discord.ui.Modal, title="Discord patch notes"):
    """Discord limits one text box to 4,000 characters, so long notes go in parts."""

    def __init__(self, rid: int):
        super().__init__()
        self.rid = rid
        self.parts = []
        for i, required in ((1, True), (2, False), (3, False)):
            box = discord.ui.TextInput(label="Part %d" % i, style=discord.TextStyle.paragraph,
                                       required=required, max_length=4000,
                                       placeholder="Paste the raw Discord markup" if i == 1 else "Optional")
            self.parts.append(box)
            self.add_item(box)

    async def on_submit(self, interaction: discord.Interaction):
        news: News = interaction.client.get_cog("News")
        text = "\n\n----- NEXT DISCORD MESSAGE -----\n\n".join(p.value.strip() for p in self.parts if p.value.strip())
        news.set_notes(self.rid, text)
        n = len(split_notes(text))
        await interaction.response.send_message(embed=embeds.notice(
            "Patch notes attached", "%d message%s will follow the announcement when you press **Publish**." % (
                n, "" if n == 1 else "s"), embeds.GREEN), ephemeral=True)


class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.release_loop.change_interval(minutes=max(2, int(self.cfg["releases"]["interval_minutes"])))
        self.devlog_loop.change_interval(minutes=max(2, int(self.cfg["devlog"]["interval_minutes"])))

    async def cog_load(self):
        self.bot.add_dynamic_items(DraftButton)
        if self.cfg["releases"]["enabled"]:
            self.release_loop.start()
        if self.cfg["devlog"]["enabled"]:
            self.devlog_loop.start()

    async def cog_unload(self):
        self.release_loop.cancel()
        self.devlog_loop.cancel()

    # ------------------------------------------------------------ draft storage
    def draft(self, rid: int) -> dict | None:
        return self.bot.store.get("release:%d" % rid)

    def save_draft(self, rid: int, draft: dict):
        self.bot.store.set("release:%d" % rid, draft)

    def set_notes(self, rid: int, text: str):
        d = self.draft(rid)
        if d:
            d["notes"] = text
            self.save_draft(rid, d)

    # ------------------------------------------------------------ releases
    @tasks.loop(minutes=10)
    async def release_loop(self):
        try:
            await self.check_releases()
        except Exception:  # noqa: BLE001
            log.exception("release check failed")

    @release_loop.before_loop
    async def before_releases(self):
        await self.bot.wait_until_ready()

    async def check_releases(self):
        rels = await self.bot.releases.published()
        if not rels:
            return
        seen = self.bot.store.get("releases_seen")
        if seen is None:       # first run: everything already out counts as announced
            self.bot.store.set("releases_seen", [r["id"] for r in rels])
            log.info("release watcher primed with %d releases", len(rels))
            return
        for rel in reversed(rels):          # oldest first
            if rel["id"] in seen:
                continue
            seen.append(rel["id"])
            self.bot.store.set("releases_seen", seen[-50:])
            await self.stage(slim(rel))

    async def stage(self, rel: dict, notes: str = "") -> str:
        """Stage a release: a draft in the staff channel, or an immediate post in auto mode."""
        self.save_draft(rel["id"], {"release": rel, "notes": notes, "state": "waiting"})
        if self.cfg["releases"]["mode"] == "auto":
            ok, where = await self.publish(rel["id"])
            return where
        staff = self.bot.text_channel(self.cfg.channel("staff"))
        if staff is None:
            log.warning("release %s waiting, but channels.staff is not set", rel.get("tag_name"))
            return "No staff channel is configured."
        await staff.send(content=embeds.release_draft_notice(self.cfg, rel, bool(notes)),
                         embed=embeds.release_announcement(self.cfg, rel), view=draft_view(rel["id"]))
        return staff.mention

    async def publish(self, rid: int) -> tuple[bool, str]:
        draft = self.draft(rid)
        channel = self.bot.text_channel(self.cfg.channel("announcements"))
        if not draft or channel is None:
            return False, "No announcements channel is configured."
        rel = draft["release"]
        ping_id = int(self.cfg["releases"].get("ping_role_id") or 0) or self.bot.role_id("patchnotes")
        ping = self.bot.guild.get_role(ping_id) if (ping_id and self.bot.guild) else None
        try:
            first = await channel.send(
                content=ping.mention if ping else None,
                embed=embeds.release_announcement(self.cfg, rel), view=release_buttons(self.cfg, rel),
                allowed_mentions=discord.AllowedMentions(roles=[ping] if ping else False))
            for part in split_notes(draft.get("notes") or ""):
                await channel.send(part, allowed_mentions=discord.AllowedMentions.none(),
                                   suppress_embeds=True)
        except discord.HTTPException as e:
            log.warning("release post failed: %s", e)
            return False, "Posting failed (%s). Check the bot's permissions in %s." % (e.status, channel.mention)
        if isinstance(channel, discord.TextChannel) and channel.is_news():
            try:
                await first.publish()       # announcement channel: push to following servers
            except discord.HTTPException:
                pass
        draft["state"] = "published"
        self.save_draft(rid, draft)
        log.info("release %s announced", rel.get("tag_name"))
        return True, channel.mention

    # ------------------------------------------------------------ devlog
    @tasks.loop(minutes=10)
    async def devlog_loop(self):
        try:
            await self.check_devlog()
        except Exception:  # noqa: BLE001
            log.exception("devlog check failed")

    @devlog_loop.before_loop
    async def before_devlog(self):
        await self.bot.wait_until_ready()

    async def check_devlog(self):
        entries = await load_devlog(self.bot.http_session, self.cfg["devlog"]["feed"])
        if not entries:
            return
        seen = self.bot.store.get("devlog_seen")
        if seen is None:
            self.bot.store.set("devlog_seen", [e["id"] for e in entries])
            log.info("devlog watcher primed with %d articles", len(entries))
            return
        channel = self.bot.text_channel(self.cfg.channel("devlog", "announcements"))
        for entry in reversed(entries):
            if entry["id"] in seen:
                continue
            if channel is None:
                log.warning("new devlog %s not posted: no devlog or announcements channel I can use", entry["url"])
                return
            meta = article_meta(self.cfg["devlog"]["site_root"], entry["url"])
            role = int(self.cfg["devlog"].get("ping_role_id") or 0) or self.bot.role_id("devlog")
            view = _link_view("Read the article", entry["url"], emoji="\N{OPEN BOOK}")
            view.add_item(discord.ui.Button(label="All devlog posts", url=self.cfg.site + "/devlog"))
            try:
                await channel.send(content=embeds.devlog_headline(entry, role),
                                   embed=embeds.devlog_post(self.cfg, entry, meta), view=view,
                                   allowed_mentions=discord.AllowedMentions(roles=bool(role), users=False,
                                                                            everyone=False))
            except discord.HTTPException as e:
                log.warning("devlog post failed: %s", e)
                return
            seen.append(entry["id"])
            self.bot.store.set("devlog_seen", seen[-200:])
            log.info("devlog posted: %s", entry["url"])

    # ------------------------------------------------------------ staff commands
    release = app_commands.Group(name="release", description="Release announcements (staff)",
                                 default_permissions=discord.Permissions(manage_guild=True))

    async def _find(self, version: str | None) -> dict:
        rels = await self.bot.releases.published()
        if not rels:
            raise UserFacingError("GitHub didn't return any releases. Try again in a minute.")
        if not version:
            return rels[0]
        v = version.strip().lstrip("v")
        for r in rels:
            if release_version(r) == v or r.get("tag_name", "").lstrip("v") == v:
                return r
        raise UserFacingError("No published release matches **%s**." % version)

    @release.command(name="announce", description="Stage a release announcement for review in the staff channel")
    @app_commands.describe(version="For example 0.33.0 (default: the newest release)",
                           notes="Optional .txt file with the Discord patch notes")
    @staff_only()
    async def announce(self, interaction: discord.Interaction, version: str | None = None,
                       notes: discord.Attachment | None = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        rel = slim(await self._find(version))
        text = await _read_notes(notes) if notes else ""
        old = self.draft(rel["id"])
        if old and old.get("state") == "published":
            raise UserFacingError("%s was already announced." % release_version(rel))
        where = await self.stage(rel, text)
        await interaction.followup.send(embed=embeds.notice(
            "Release staged", "%s is waiting for review in %s." % (release_version(rel), where)), ephemeral=True)

    @release.command(name="notes", description="Attach Discord patch notes to a release waiting for review")
    @app_commands.describe(file="The .txt file with the raw Discord markup", version="Default: the newest release")
    @staff_only()
    async def notes(self, interaction: discord.Interaction, file: discord.Attachment, version: str | None = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        rel = await self._find(version)
        draft = self.draft(rel["id"])
        if not draft or draft.get("state") != "waiting":
            raise UserFacingError("%s isn't waiting for review. Stage it with `/release announce` first."
                                  % release_version(rel))
        text = await _read_notes(file)
        self.set_notes(rel["id"], text)
        n = len(split_notes(text))
        await interaction.followup.send(embed=embeds.notice(
            "Patch notes attached", "%d message%s will follow the %s announcement." % (
                n, "" if n == 1 else "s", release_version(rel)), embeds.GREEN), ephemeral=True)


async def _read_notes(att: discord.Attachment) -> str:
    if att.size > 64 * 1024:
        raise UserFacingError("That file is too large for patch notes (64 KB at most).")
    if not (att.filename.lower().endswith((".txt", ".md")) or (att.content_type or "").startswith("text/")):
        raise UserFacingError("Upload the patch notes as a .txt or .md file.")
    try:
        return (await att.read()).decode("utf-8-sig").strip()
    except UnicodeDecodeError as e:
        raise UserFacingError("That file isn't UTF-8 text.") from e


def _link_view(label: str, url: str, emoji: str | None = None) -> discord.ui.View:
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label=label, url=url, emoji=emoji))
    return v


async def setup(bot):
    await bot.add_cog(News(bot))
