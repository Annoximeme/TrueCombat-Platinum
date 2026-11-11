"""Where the bot's data comes from. All of it is local to the VPS except GitHub.

* Game servers: UDP ``getstatus``, the same query the server browser sends.
* Stats bridge: http://127.0.0.1:8090 (the service behind api.truecombat.eu).
* Devlog: the Atom feed in the website folder Caddy serves.
* Releases: the public GitHub Releases API, with conditional requests.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import aiohttp

from .text import clean

log = logging.getLogger("tcpbot.sources")
USER_AGENT = "TrueCombatBot/1.0 (+https://truecombat.eu)"


# ---------------------------------------------------------------- game servers
class _StatusProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.future: asyncio.Future = asyncio.get_running_loop().create_future()

    def datagram_received(self, data, addr):
        if not self.future.done():
            self.future.set_result(data)

    def error_received(self, exc):
        if not self.future.done():
            self.future.set_exception(exc)


def parse_status(data: bytes):
    head = b"\xff\xff\xff\xffstatusResponse"
    if not data.startswith(head):
        return None
    lines = [l for l in data[len(head):].decode("latin-1").split("\n") if l]
    if not lines:
        return None
    parts = lines[0].split("\\")[1:]
    cvars = {parts[i].lower(): parts[i + 1] for i in range(0, len(parts) - 1, 2)}
    players = []
    for line in lines[1:]:
        m = re.match(r'^(-?\d+)\s+(-?\d+)\s+"(.*)"', line.strip())
        if m:
            players.append({"score": int(m.group(1)), "ping": int(m.group(2)), "name": clean(m.group(3))})
    return {"cvars": cvars, "players": players}


async def query_game(host: str, port: int, tries: int = 2, timeout: float = 2.0):
    """Returns {"cvars": {...}, "players": [...]} or None when the server doesn't answer."""
    loop = asyncio.get_running_loop()
    for _ in range(tries):
        transport = None
        try:
            transport, proto = await loop.create_datagram_endpoint(_StatusProtocol, remote_addr=(host, int(port)))
            transport.sendto(b"\xff\xff\xff\xffgetstatus")
            data = await asyncio.wait_for(proto.future, timeout)
            result = parse_status(data)
            if result:
                return result
        except (asyncio.TimeoutError, OSError):
            continue
        finally:
            if transport:
                transport.close()
    return None


def is_bot(player: dict, pattern: str = "") -> bool:
    """Engine bots answer with ping 0; stress-test clients are matched by name."""
    return player["ping"] <= 0 or bool(pattern and re.search(pattern, player["name"], re.I))


# ---------------------------------------------------------------- stats bridge
class StatsAPI:
    """Small client for the stats bridge, with a short cache so a busy channel
    doesn't hammer it."""

    def __init__(self, session: aiohttp.ClientSession, base: str, ttl: float = 30.0):
        self.session = session
        self.base = base.rstrip("/")
        self.ttl = ttl
        self._cache: dict[str, tuple[float, object]] = {}

    async def _get(self, path: str, params: dict | None = None, ttl: float | None = None):
        key = path + "?" + "&".join("%s=%s" % kv for kv in sorted((params or {}).items()))
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < (self.ttl if ttl is None else ttl):
            return hit[1]
        try:
            async with self.session.get(self.base + path, params=params,
                                        timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 404:
                    data = None
                else:
                    r.raise_for_status()
                    data = await r.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            log.warning("stats api %s: %s", path, e)
            raise StatsUnavailable() from e
        self._cache[key] = (time.monotonic(), data)
        if len(self._cache) > 500:
            self._cache.clear()
        return data

    async def servers(self):
        return await self._get("/servers.json", ttl=20)

    async def leaderboard(self, sort="rating", period="all", limit=10, fresh=False, since="", until=""):
        params = {"sort": sort, "period": period, "limit": limit}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return await self._get("/leaderboard.json", params, ttl=0 if fresh else None)

    async def match(self, match_id: str):
        """One finished match with its scoreboard (by its public id from recent matches), or None
        when the stats service doesn't have it or is an older version without match pages."""
        return await self._get("/match.json", {"id": match_id}, ttl=300)

    async def recap(self, days: int = 7):
        """Totals and standout players of the last days; None on an older stats service."""
        return await self._get("/recap.json", {"days": days}, ttl=60)

    async def player(self, pid: str, fresh=False):
        return await self._get("/player.json", {"id": pid}, ttl=0 if fresh else None)

    async def search(self, q: str):
        data = await self._get("/search.json", {"q": q}, ttl=60)
        return (data or {}).get("players", [])

    async def recent(self, fresh=False):
        return await self._get("/recent.json", ttl=0 if fresh else None)


class StatsUnavailable(Exception):
    pass


# ---------------------------------------------------------------- GitHub releases
class Releases:
    def __init__(self, session: aiohttp.ClientSession, repo: str):
        self.session = session
        self.url = "https://api.github.com/repos/%s/releases?per_page=10" % repo
        self.etag = None
        self.cached: list[dict] = []

    async def published(self) -> list[dict]:
        """Published (non-draft) releases, newest first. Uses ETags, so unchanged
        polls don't count against GitHub's rate limit."""
        headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.etag:
            headers["If-None-Match"] = self.etag
        try:
            async with self.session.get(self.url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 304:
                    return self.cached
                r.raise_for_status()
                data = await r.json()
                self.etag = r.headers.get("ETag")
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            log.warning("github releases: %s", e)
            return self.cached
        rels = [x for x in data if not x.get("draft") and x.get("published_at")]
        rels.sort(key=lambda x: x["published_at"], reverse=True)
        self.cached = rels
        return rels


def release_version(rel: dict) -> str:
    """'v0.33.0-sandbox24' -> '0.33.0'"""
    m = re.search(r"(\d+\.\d+\.\d+)", rel.get("tag_name") or rel.get("name") or "")
    return m.group(1) if m else (rel.get("tag_name") or "")


def release_download(rel: dict) -> str:
    for a in rel.get("assets") or []:
        if a.get("name") == "TrueCombat-Platinum-Setup.exe":
            return a["browser_download_url"]
    return rel.get("html_url") or ""


# ---------------------------------------------------------------- devlog
ATOM = "{http://www.w3.org/2005/Atom}"


def parse_devlog(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall(ATOM + "entry"):
        link = e.find(ATOM + "link")
        cat = e.find(ATOM + "category")
        out.append({
            "id": (e.findtext(ATOM + "id") or "").strip(),
            "title": (e.findtext(ATOM + "title") or "").strip(),
            "url": link.get("href") if link is not None else "",
            "summary": (e.findtext(ATOM + "summary") or "").strip(),
            "published": (e.findtext(ATOM + "published") or e.findtext(ATOM + "updated") or "").strip(),
            "category": cat.get("term") if cat is not None else "",
        })
    return out


async def load_devlog(session: aiohttp.ClientSession, feed: str) -> list[dict]:
    try:
        if feed.startswith(("http://", "https://")):
            async with session.get(feed, timeout=aiohttp.ClientTimeout(total=10)) as r:
                r.raise_for_status()
                text = await r.text()
        else:
            text = Path(feed).read_text(encoding="utf-8")
        return parse_devlog(text)
    except (OSError, aiohttp.ClientError, asyncio.TimeoutError, ET.ParseError) as e:
        log.warning("devlog feed %s: %s", feed, e)
        return []


def article_image(site_root: str, url: str) -> str | None:
    """og:image of a devlog article, read from the local copy of the site."""
    name = url.rstrip("/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.html", name or ""):
        return None
    try:
        html = (Path(site_root) / name).read_text(encoding="utf-8", errors="replace")[:20000]
    except OSError:
        return None
    m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
    return m.group(1) if m else None

