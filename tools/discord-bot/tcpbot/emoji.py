"""The bot's own emoji: rank insignia, medals, team crests and status lights.

They are application emoji, owned by the bot rather than the server, so they
take none of the server's emoji slots and work in every channel. The art is
drawn by cards.py; on start the bot uploads anything missing or changed.
Until the upload has happened every lookup returns an empty string, so a card
never shows a broken emoji.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

import discord

log = logging.getLogger("tcpbot.emoji")

_ids: dict[str, int] = {}


def get(name: str, fallback: str = "") -> str:
    """Inline emoji markup for `name` (without the tcp_ prefix), or the fallback."""
    eid = _ids.get("tcp_" + name)
    return "<:tcp_%s:%d>" % (name, eid) if eid else fallback


def partial(name: str) -> discord.PartialEmoji | None:
    eid = _ids.get("tcp_" + name)
    return discord.PartialEmoji(name="tcp_" + name, id=eid) if eid else None


def tier(level: int) -> str:
    """The game's rank insignia for a player level."""
    from .cards import insignia_key
    return get(insignia_key(level))


def medal(place: int) -> str:
    return get("medal%d" % place) if place in (1, 2, 3) else ""


def team(key: str | None) -> str:
    k = (key or "").lower()
    return get(k) if k in ("specops", "terrorists") else ""


def load(mapping: dict[str, int]):
    """Used by tests and by sync()."""
    _ids.clear()
    _ids.update(mapping)


async def sync(bot) -> None:
    """Upload missing or changed icons. Changed art gets re-uploaded under the same name."""
    from . import cards
    try:
        art = await asyncio.to_thread(lambda: {n: cards.png(img) for n, img in cards.icon_set().items()})
        existing = {e.name: e for e in await bot.fetch_application_emojis()}
        known = bot.store.get("emoji_hashes") or {}
        mapping = {}
        for name, data in art.items():
            digest = hashlib.sha256(data).hexdigest()[:16]
            cur = existing.get(name)
            if cur is not None and known.get(name) not in (None, digest):
                try:
                    await cur.delete()
                except discord.HTTPException as e:
                    log.warning("could not replace emoji %s: %s", name, e)
                cur = None
            if cur is None:
                cur = await bot.create_application_emoji(name=name, image=data)
                log.info("uploaded emoji %s", name)
            known[name] = digest
            mapping[name] = cur.id
        bot.store.set("emoji_hashes", known)
        load(mapping)
        log.info("emoji ready (%d)", len(mapping))
    except discord.HTTPException as e:
        log.warning("emoji sync failed, cards use plain text: %s", e)
