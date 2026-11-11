"""Game chat in Discord, and a line back into the game.

Each bridged server is followed through its console log (a file, or the
service's journal). Public chat lines are posted to the server's channel in
small batches. Team chat and anything that looks like a command (such as a
link code) never leaves the server.

Discord to game goes through /chat, because the bot deliberately doesn't read
channel messages. Who may use it is chat_bridge.relay_to_game.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import embeds
from .. import text as T
from ..bot import UserFacingError
from ..rcon import RconError, parse_status, safe_arg, server_rcon

log = logging.getLogger("tcpbot.chat")
COMMAND = re.compile(r"^\s*[!/\\]")


def parse_line(line: str, patterns: list[re.Pattern]) -> dict | None:
    """A public chat line as {"name" or "slot", "text"}; None for anything else."""
    line = line.rstrip("\r\n")
    for pat in patterns:
        m = pat.search(line)
        if not m:
            continue
        g = m.groupdict()
        if (g.get("team") or "0") not in ("0", ""):
            return None                              # team chat stays in the team
        text = T.clean(g.get("text") or "", 200)
        if not text or COMMAND.match(text):
            return None
        out = {"text": text}
        if g.get("name"):
            out["name"] = T.clean(g["name"])
        elif g.get("slot") is not None:
            out["slot"] = int(g["slot"])
        else:
            return None
        return out
    return None


class Follower:
    """Yields new lines of a log file, surviving rotation and restarts."""

    def __init__(self, path: str):
        self.path, self.pos, self.inode, self.rest = path, None, None, ""

    def read(self) -> list[str]:
        try:
            st = os.stat(self.path)
        except OSError:
            return []
        if self.pos is None:                         # start at the end: old chat is not news
            self.pos, self.inode = st.st_size, st.st_ino
            return []
        if st.st_ino != self.inode or st.st_size < self.pos:
            self.pos, self.inode, self.rest = 0, st.st_ino, ""
        if st.st_size == self.pos:
            return []
        try:
            with open(self.path, "rb") as f:
                f.seek(self.pos)
                data = f.read(256 * 1024)
                self.pos = f.tell()
        except OSError:
            return []
        lines = (self.rest + data.decode("utf-8", "replace")).split("\n")
        self.rest = lines.pop()
        return lines


class ChatBridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.cfg
        self.cc = bot.cfg["chat_bridge"]
        self.patterns = [re.compile(p) for p in self.cc["patterns"]]
        self.followers: dict[str, Follower] = {}
        self.journals: dict[str, asyncio.Task] = {}
        self.queues: dict[str, list[str]] = {}
        self.names: dict[str, tuple[float, dict[int, str]]] = {}
        self.last_relay: dict[int, float] = {}

    async def cog_load(self):
        if self.cc["enabled"]:
            self.pump.start()

    async def cog_unload(self):
        self.pump.cancel()
        for t in self.journals.values():
            t.cancel()

    def servers(self) -> list[dict]:
        return list(self.cc["servers"]) if self.cc["enabled"] else []

    # ------------------------------------------------------------ game -> Discord
    async def slot_name(self, entry: dict, slot: int) -> str:
        key = entry["key"]
        cached = self.names.get(key)
        if not cached or time.monotonic() - cached[0] > 20 or slot not in cached[1]:
            server = self.cfg.server(key)
            names = {}
            if server:
                try:
                    names = {p["slot"]: T.clean(p["name"]) for p in parse_status(await server_rcon(server, "status"))["players"]}
                except (RconError, OSError):
                    names = cached[1] if cached else {}
            self.names[key] = (time.monotonic(), names)
            cached = self.names[key]
        return cached[1].get(slot) or "Player %d" % slot

    async def take(self, entry: dict, line: str):
        msg = parse_line(line, self.patterns)
        if not msg:
            return
        name = msg.get("name") or await self.slot_name(entry, msg["slot"])
        self.queues.setdefault(entry["key"], []).append("**%s**: %s" % (T.md(name), T.md(msg["text"])))

    async def follow_journal(self, entry: dict):
        """Follows a systemd unit's log. Needs the service to be in the systemd-journal group."""
        while True:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "journalctl", "-u", entry["unit"], "-f", "-n", "0", "-o", "cat",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                async for raw in proc.stdout:
                    await self.take(entry, raw.decode("utf-8", "replace"))
                await proc.wait()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                log.warning("journal of %s: %s", entry.get("unit"), e)
            await asyncio.sleep(15)

    @tasks.loop(seconds=2)
    async def pump(self):
        for entry in self.servers():
            key = entry["key"]
            try:
                if entry.get("log"):
                    f = self.followers.setdefault(key, Follower(entry["log"]))
                    for line in f.read():
                        await self.take(entry, line)
                elif key not in self.journals or self.journals[key].done():
                    self.journals[key] = asyncio.create_task(self.follow_journal(entry))
                await self.flush(entry)
            except Exception:  # noqa: BLE001
                log.exception("chat bridge %s failed", key)

    @pump.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()

    async def flush(self, entry: dict):
        lines = self.queues.get(entry["key"])
        if not lines:
            return
        self.queues[entry["key"]] = []
        ch = self.bot.text_channel(entry.get("channel", 0))
        if ch is None:
            return
        extra = len(lines) - 15
        text = "\n".join(lines[:15]) + ("\n+%d more lines" % extra if extra > 0 else "")
        await ch.send(content=T.clip(text, 1900), allowed_mentions=discord.AllowedMentions.none())

    # ------------------------------------------------------------ Discord -> game
    async def _servers(self, interaction: discord.Interaction, current: str):
        out = []
        for e in self.servers():
            s = self.cfg.server(e["key"]) or {}
            name = s.get("name", e["key"]).split("|")[-1].strip()
            if current.lower() in name.lower():
                out.append(app_commands.Choice(name=name[:100], value=e["key"]))
        return out[:25]

    def relay_line(self, member, message: str) -> str:
        link = self.bot.store.linked_player(member.id)
        name = safe_arg(link["name"] if link else member.display_name, 24) or "Member"
        return 'say "[Discord] %s: %s"' % (name, safe_arg(message, 120))

    @app_commands.command(name="chat", description="Send a line to the game chat of a bridged server")
    @app_commands.describe(message="What to say", server="Which server (default: the one bridged to this channel)")
    @app_commands.autocomplete(server=_servers)
    async def cmd_chat(self, interaction: discord.Interaction, message: app_commands.Range[str, 1, 120],
                       server: str | None = None):
        mode = self.cc["relay_to_game"]
        if not self.cc["enabled"] or mode == "off":
            raise UserFacingError("The chat bridge to the game is switched off.")
        if mode == "staff" and not self.bot.is_staff(interaction.user):
            raise UserFacingError("Only staff can talk into the game from Discord right now.")
        if mode == "linked" and not (self.bot.store.linked_player(interaction.user.id) or self.bot.is_staff(interaction.user)):
            raise UserFacingError("Link your game profile with `/link` first.")
        entries = self.servers()
        entry = next((e for e in entries if e["key"] == server), None) if server else (
            next((e for e in entries if int(e.get("channel") or 0) == interaction.channel_id), None)
            or (entries[0] if len(entries) == 1 else None))
        if entry is None:
            raise UserFacingError("Pick a server, or use this in a bridged chat channel.")
        game = self.cfg.server(entry["key"])
        if game is None:
            raise UserFacingError("That server isn't in the bot's server list.")
        wait = float(self.cc["relay_cooldown_seconds"]) - (time.monotonic() - self.last_relay.get(interaction.user.id, -1e9))
        if wait > 0 and not self.bot.is_staff(interaction.user):
            raise UserFacingError("One line every %d seconds. Try again in %d." % (
                int(self.cc["relay_cooldown_seconds"]), int(wait) + 1))
        if not safe_arg(message, 120):
            raise UserFacingError("There's nothing to send in that message.")
        await interaction.response.defer(ephemeral=True)
        try:
            await server_rcon(game, self.relay_line(interaction.user, message))
        except (RconError, OSError) as e:
            raise UserFacingError("The server didn't take the message. Try again in a moment.") from e
        self.last_relay[interaction.user.id] = time.monotonic()
        ch = self.bot.text_channel(entry.get("channel", 0))
        if ch:
            await ch.send(content="**%s** (Discord): %s" % (T.md(interaction.user.display_name), T.md(safe_arg(message, 120))),
                          allowed_mentions=discord.AllowedMentions.none())
        await interaction.followup.send(embed=embeds.notice("Sent", "Your line is in the game chat.", embeds.GREEN),
                                        ephemeral=True)


async def setup(bot):
    await bot.add_cog(ChatBridge(bot))
