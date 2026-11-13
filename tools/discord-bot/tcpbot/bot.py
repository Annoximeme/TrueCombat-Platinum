"""The bot process: Discord connection, shared services and the feature modules."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from . import __version__, embeds
from . import emoji as E
from .config import Config
from .sources import AccountsAPI, Releases, StatsAPI, StatsUnavailable
from .store import Store

log = logging.getLogger("tcpbot")

# Shown under "About me" on the bot's profile
ABOUT = ("The official bot of TrueCombat: Platinum, the modern return of TrueCombat: Elite.\n\n"
         "Live server status, player profiles and leaderboards, pickup games, match reports and "
         "devlog news. Try /profile, /top and /servers.\n\n"
         "truecombat.eu")

EXTENSIONS = (
    "tcpbot.cogs.status",
    "tcpbot.cogs.stats",
    "tcpbot.cogs.linking",
    "tcpbot.cogs.news",
    "tcpbot.cogs.community",
    "tcpbot.cogs.reports",
    "tcpbot.cogs.admin",
    "tcpbot.cogs.pickup",
    "tcpbot.cogs.highlights",
    "tcpbot.cogs.alerts",
    "tcpbot.cogs.clans",
    "tcpbot.cogs.feedback",
    "tcpbot.cogs.mapvote",
    "tcpbot.cogs.chatbridge",
    "tcpbot.cogs.support",
    "tcpbot.cogs.accounts",
)


class UserFacingError(app_commands.AppCommandError):
    """An error whose message is safe and useful to show to the member."""


class TCPBot(commands.Bot):
    def __init__(self, cfg: Config, store: Store):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True          # welcome messages and rank roles (privileged, enable in the portal)
        super().__init__(
            command_prefix=commands.when_mentioned,   # no text commands; slash commands only
            intents=intents,
            help_command=None,
            allowed_mentions=discord.AllowedMentions.none(),
            activity=discord.Activity(type=discord.ActivityType.watching, name=cfg["presence"]),
        )
        self.cfg = cfg
        self.store = store
        self.http_session: aiohttp.ClientSession | None = None
        self.stats: StatsAPI | None = None
        self.releases: Releases | None = None
        self.accounts: AccountsAPI | None = None
        self.tree.on_error = self.on_app_command_error

    # ------------------------------------------------------------ lifecycle
    async def setup_hook(self):
        self.http_session = aiohttp.ClientSession(headers={"User-Agent": "TrueCombatBot/%s" % __version__})
        self.stats = StatsAPI(self.http_session, self.cfg["api_url"])
        self.releases = Releases(self.http_session, self.cfg["releases"]["repo"])
        from .cogs.feedback import secret
        self.accounts = AccountsAPI(self.http_session, self.cfg["accounts"]["url"],
                                    secret(self.cfg["accounts"]["token_credential"]))
        for ext in EXTENSIONS:
            await self.load_extension(ext)
        guild = discord.Object(id=int(self.cfg["guild_id"]))
        self.tree.copy_global_to(guild=guild)
        self.tree.clear_commands(guild=None)
        synced = await self.tree.sync(guild=guild)
        await self.tree.sync()   # removes any stale global commands
        log.info("synced %d slash commands to guild %s", len(synced), guild.id)

    async def close(self):
        if self.http_session:
            await self.http_session.close()
        await super().close()

    async def on_ready(self):
        log.info("connected as %s (%s), version %s", self.user, self.user.id, __version__)
        await self.sync_avatar()
        if not getattr(self, "_dressed", False):
            self._dressed = True
            await self.sync_profile()
            await E.sync(self)

    async def sync_profile(self):
        """Banner and About me, uploaded once per design change (both are rate-limited by Discord)."""
        from . import cards
        try:
            banner = await asyncio.to_thread(cards.banner, self.cfg["devlog"]["site_root"])
        except OSError as e:
            log.warning("could not draw the banner: %s", e)
            return
        digest = hashlib.sha256(banner + ABOUT.encode()).hexdigest()
        if self.store.get("profile_sha256") == digest:
            return
        try:
            await self.user.edit(banner=banner)
            info = await self.application_info()
            await info.edit(description=ABOUT)
        except discord.HTTPException as e:
            log.warning("could not update the bot profile yet (%s); will retry on the next start", e)
            return
        self.store.set("profile_sha256", digest)
        log.info("profile banner and About me updated")

    async def set_presence(self, text: str):
        """The line under the bot's name. Only sent when it changes."""
        text = (text or self.cfg["presence"])[:120]
        if text == getattr(self, "_presence", None):
            return
        self._presence = text
        try:
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
        except (discord.HTTPException, ConnectionError) as e:
            log.debug("presence not updated: %s", e)

    async def sync_avatar(self):
        """Uploads assets/avatar.png as the bot's profile picture when it changed.
        Discord rate-limits avatar changes, so the hash of the last upload is remembered."""
        path = Path(self.cfg["avatar"])
        try:
            data = path.read_bytes()
        except OSError:
            log.warning("avatar file not found: %s", path)
            return
        digest = hashlib.sha256(data).hexdigest()
        if self.store.get("avatar_sha256") == digest:
            return
        try:
            await self.user.edit(avatar=data)
        except discord.HTTPException as e:
            log.warning("could not set the avatar yet (%s); will retry on the next start", e)
            return
        self.store.set("avatar_sha256", digest)
        log.info("profile picture updated from %s", path)

    # ------------------------------------------------------------ helpers
    async def draw(self, name: str, fn, *args) -> discord.File | None:
        """Renders an image card off the event loop. None (and a plain text card) when drawing fails."""
        if not self.cfg["cards"]["enabled"]:
            return None
        try:
            data = await asyncio.to_thread(fn, *args)
        except Exception:  # noqa: BLE001 - a broken card must never cost the member their answer
            log.exception("could not draw %s", name)
            return None
        import io
        return discord.File(io.BytesIO(data), filename=name)

    @property
    def guild(self) -> discord.Guild | None:
        return self.get_guild(int(self.cfg["guild_id"]))

    def text_channel(self, cid: int) -> discord.abc.Messageable | None:
        ch = self.get_channel(int(cid or 0))
        return ch if isinstance(ch, (discord.TextChannel, discord.Thread)) else None

    def is_staff(self, member: discord.abc.User) -> bool:
        if not isinstance(member, discord.Member):
            return False
        if member.guild_permissions.manage_guild or member.guild_permissions.administrator:
            return True
        staff = {int(r) for r in self.cfg["staff_role_ids"]}
        return any(r.id in staff for r in member.roles)

    def role_id(self, key: str) -> int:
        return int((self.store.get("roles") or {}).get(key) or 0)

    def role(self, key: str) -> discord.Role | None:
        g = self.guild
        return g.get_role(self.role_id(key)) if g else None

    # ------------------------------------------------------------ errors
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original = getattr(error, "original", error)
        if isinstance(error, UserFacingError):
            text = str(error)
        elif isinstance(original, StatsUnavailable):
            text = "The stats service isn't answering right now. Give it a minute and try again."
        elif isinstance(error, app_commands.CheckFailure):
            text = "This command is for staff."
        elif isinstance(original, discord.Forbidden):
            text = ("I don't have permission to do that in this channel. Give my role View Channel, "
                    "Send Messages, Embed Links, Attach Files and Read Message History here, then try again.")
        elif isinstance(error, app_commands.CommandOnCooldown):
            text = "Easy there. Try again in %d seconds." % max(1, round(error.retry_after))
        else:
            log.exception("command %s failed", interaction.command and interaction.command.qualified_name,
                          exc_info=original)
            text = "Something went wrong on our side. The team has been notified in the logs."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embeds.error(text), ephemeral=True)
            else:
                await interaction.response.send_message(embed=embeds.error(text), ephemeral=True)
        except discord.HTTPException:
            pass


def staff_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.client.is_staff(interaction.user)
    return app_commands.check(predicate)
