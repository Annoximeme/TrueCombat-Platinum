"""Where the bot's data comes from. All of it is local to the VPS except GitHub.

* Game servers: UDP ``getstatus``, the same query the server browser sends.
* Stats bridge: http://127.0.0.1:8090 (the service behind api.truecombat.eu).
* Devlog: the Atom feed in the website folder Caddy serves.
* Releases: the public GitHub Releases API, with conditional requests. Every
  link the bot posts for a release points at truecombat.eu, never at GitHub.
"""

from __future__ import annotations

import asyncio
import html
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

    async def week(self, pid: str):
        """A player's last seven days against the seven before (tcp-week/1); None on an older stats service."""
        return await self._get("/week.json", {"id": pid}, ttl=0)


# ---------------------------------------------------------------- player accounts
class AccountsUnavailable(Exception):
    pass


class AccountsAPI:
    """The account service on the VPS (127.0.0.1:8095). /internal/* needs the shared token
    (systemd credential, the same value as the service's internal-token). Without a token the
    account features stay off and nothing else changes."""

    def __init__(self, session: aiohttp.ClientSession, base: str, token: str):
        self.session = session
        self.base = base.rstrip("/")
        self.token = token or ""

    @property
    def ready(self) -> bool:
        return bool(self.token)

    async def _call(self, method: str, path: str, body: dict | None = None):
        if not self.ready:
            raise AccountsUnavailable("no accounts token")
        try:
            async with self.session.request(method, self.base + path, json=body,
                                            headers={"X-Accounts-Token": self.token},
                                            timeout=aiohttp.ClientTimeout(total=8)) as r:
                data = await r.json(content_type=None)
                if r.status >= 400:
                    raise AccountsUnavailable((data or {}).get("error") or "HTTP %d" % r.status)
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            log.warning("accounts %s: %s", path, e)
            raise AccountsUnavailable(str(e)) from e

    async def roles(self) -> list[dict]:
        """Every linked account the bot should know: discordId, name, statsId, badges."""
        return (await self._call("GET", "/internal/roles")).get("accounts", [])

    async def weekly(self) -> list[dict]:
        return (await self._call("GET", "/internal/weekly")).get("accounts", [])

    async def lfs(self) -> list[dict]:
        return (await self._call("GET", "/api/account/lfs.json")).get("players", [])

    async def lookup(self, discord_id: int):
        try:
            return await self._call("GET", "/internal/lookup?discord=%d" % int(discord_id))
        except AccountsUnavailable as e:
            if "No such" in str(e) or "404" in str(e):
                return None
            raise

    async def ban(self, *, discord_id: int = 0, name: str = "", kind: str = "ban", reason: str = "", days: int = 0,
                  by: str = "") -> dict:
        return await self._call("POST", "/internal/ban", {"discord": str(discord_id or ""), "name": name, "kind": kind,
                                                          "reason": reason, "days": days, "by": by})

    async def unban(self, ban_id: int) -> dict:
        return await self._call("POST", "/internal/unban", {"ban": int(ban_id)})

    async def bans(self) -> list[dict]:
        return (await self._call("GET", "/internal/bans")).get("bans", [])


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
    """The installer file itself, or "" (callers then link the website's download page)."""
    for a in rel.get("assets") or []:
        if a.get("name") == "TrueCombat-Platinum-Setup.exe":
            return a["browser_download_url"]
    return ""


def release_slug(rel: dict) -> str:
    """'v0.37.0-sandbox30' -> 'release-0-37-0', the website's page for that version
    (same rule as slug() in tools/website/releases.py)."""
    m = re.search(r"(\d+\.\d+\.\d+)", rel.get("tag_name") or rel.get("name") or "")
    return "release-" + m.group(1).replace(".", "-") if m else ""


def release_page_ready(site_root: str, rel: dict) -> bool:
    """True once the website copy on this box has the version's own patch-notes page.
    The site rebuilds itself a few minutes after a release is published."""
    slug = release_slug(rel)
    if not slug:
        return False
    root = Path(site_root or "")
    if not site_root or not root.is_dir():
        return True     # no local copy to look at: trust the site to have it
    return (root / (slug + ".html")).is_file()


def release_notes_url(site: str, site_root: str, rel: dict) -> str:
    """Where a release's patch notes live on truecombat.eu: the version's own page
    when it is up, otherwise its entry on the patch notes page."""
    site = site.rstrip("/")
    slug = release_slug(rel)
    if slug and release_page_ready(site_root, rel):
        return "%s/%s" % (site, slug)
    m = re.search(r"(\d+\.\d+\.\d+)", rel.get("tag_name") or rel.get("name") or "")
    return "%s/news.html#v%s" % (site, m.group(1)) if m else site + "/news.html"


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


def _article_html(site_root: str, url: str) -> str | None:
    """The local copy of a devlog article. The site serves clean addresses
    (/devlog-x) from files named devlog-x.html, so both forms resolve."""
    name = url.split("#", 1)[0].split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    if name and "." not in name:
        name += ".html"
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.html", name or ""):
        return None
    try:
        return (Path(site_root) / name).read_text(encoding="utf-8", errors="replace")[:200000]
    except OSError:
        return None


def _plain_html(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", text)).split())


def article_meta(site_root: str, url: str) -> dict:
    """What the devlog card shows beyond the feed: cover image, read time,
    release state and the post's section headings."""
    page = _article_html(site_root, url)
    if not page:
        return {}
    head = page[:20000]
    meta: dict = {}
    m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', head)
    if m:
        meta["image"] = m.group(1)
    m = re.search(r'"timeRequired"\s*:\s*"PT(\d+)M"', head) or re.search(r"<span>(\d+) min read</span>", page)
    if m:
        meta["minutes"] = int(m.group(1))
    m = re.search(r'class="state[^"]*">([^<]+)<', page)
    if m:
        meta["state"] = _plain_html(m.group(1))
    toc = re.search(r'<nav class="post-toc".*?</nav>', page, re.S)
    if toc:
        meta["sections"] = [_plain_html(x) for x in re.findall(r"<li><a [^>]*>(.*?)</a></li>", toc.group(0), re.S)]
    return meta


def article_image(site_root: str, url: str) -> str | None:
    """og:image of a devlog article, read from the local copy of the site."""
    return article_meta(site_root, url).get("image")

