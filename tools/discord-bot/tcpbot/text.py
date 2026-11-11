"""Formatting helpers shared by every part of the bot.

Everything here is pure (no Discord or network calls), so it is covered by the
unit tests and can be reused by the preview command.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Iterable
from zoneinfo import ZoneInfo

COLOUR_CODE = re.compile(r"\^[0-9A-Za-z]")
MD_SPECIAL = re.compile(r"([\\*_~`|>#\[\]()-])")

MAP_NAMES = {
    "obj_delta": "Delta", "obj_northport": "Northport", "obj_railhouse": "Railhouse",
    "obj_snow": "Snow", "obj_stadtrand": "Stadtrand", "obj_village": "Village",
}

# Rank tiers used for Discord roles. Levels follow tools/server-bridge/tcp_stats.py
# (1 Recruit ... 21 General).
RANK_TIERS = [
    # key, role name, first level, colour
    ("enlisted", "Enlisted", 1, 0x8E9AAF),
    ("nco", "Non-Commissioned Officer", 5, 0x5B9BD5),
    ("officer", "Officer", 12, 0xC9A227),
    ("general", "General Staff", 18, 0xE5533D),
]

SORT_LABELS = {
    "rating": "Skill rating", "xp": "Experience", "kills": "Kills",
    "kd": "K/D ratio", "headshots": "Headshots", "wins": "Match wins",
}


# ---------------------------------------------------------------- names
def clean(text: str | None, limit: int = 36) -> str:
    """Strip Quake colour codes and unprintable characters from a player name."""
    text = COLOUR_CODE.sub("", text or "")
    text = "".join(ch for ch in text if ch.isprintable())
    return text.strip()[:limit]


def md(text: str | None) -> str:
    """Escape Discord markdown and neutralise mentions in player-chosen text."""
    text = MD_SPECIAL.sub(r"\\\1", text or "")
    return text.replace("@", "@​") or "Unnamed"


def mono(text: str | None) -> str:
    """Make text safe inside a ``` code block."""
    return (text or "").replace("`", "'")


# ---------------------------------------------------------------- maps
def map_label(name: str | None) -> str:
    key = (name or "").lower()
    if key in MAP_NAMES:
        return MAP_NAMES[key]
    base = re.sub(r"^(obj|ctf|tdm|bomb)_", "", key)
    return base.replace("_", " ").title() or "Unknown"


def map_image(site: str, name: str | None) -> str | None:
    if (name or "").lower() not in MAP_NAMES:
        return None
    return "%s/img/maps/%s-hd.webp" % (site.rstrip("/"), map_label(name).lower())


# ---------------------------------------------------------------- numbers
def num(value) -> str:
    if isinstance(value, float) and not value.is_integer():
        return "{:,.2f}".format(value)
    try:
        return "{:,}".format(int(value or 0))
    except (TypeError, ValueError):
        return "-"


def pct(part, whole) -> str:
    return "%d%%" % round(100.0 * part / whole) if whole else "-"


def duration(seconds) -> str:
    seconds = int(seconds or 0)
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    if hours:
        return "%dh %02dm" % (hours, minutes)
    return "%dm" % minutes


def signed(value: int) -> str:
    return "+%d" % value if value > 0 else ("%d" % value if value < 0 else "±0")


def progress_bar(current: int, start: int, end: int | None, width: int = 12) -> str:
    """A text progress bar for rank XP. Uses block characters that render in every client."""
    if not end or end <= start:
        return "█" * width
    share = max(0.0, min(1.0, (current - start) / float(end - start)))
    filled = int(round(share * width))
    return "█" * filled + "░" * (width - filled)


def tier_for_level(level: int) -> str:
    key = RANK_TIERS[0][0]
    for k, _name, first, _colour in RANK_TIERS:
        if level >= first:
            key = k
    return key


def iso_to_unix(text: str | None) -> int | None:
    if not text:
        return None
    try:
        return int(dt.datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


# ---------------------------------------------------------------- tables
def table(rows: Iterable[Iterable[str]], align: str) -> str:
    """Monospace table for code blocks. align is a string of 'l'/'r' per column."""
    rows = [[mono(str(c)) for c in r] for r in rows]
    if not rows:
        return ""
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out = []
    for r in rows:
        cells = [c.ljust(w) if a == "l" else c.rjust(w) for c, w, a in zip(r, widths, align)]
        out.append("  ".join(cells).rstrip())
    return "\n".join(out)


# ---------------------------------------------------------------- release notes
NOTES_SPLIT = re.compile(r"^-{3,}\s*NEXT DISCORD MESSAGE\s*-{3,}\s*$", re.M | re.I)
BOLD_LINE = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")
TITLE_HINT = re.compile(r"TRUECOMBAT|\bv?\d+\.\d+\.\d+")


def parse_release_body(body: str) -> dict:
    """Split a release body in the house format into header lines, intro and sections.

    Format (see the GitHub releases): a few bold header lines, an intro
    paragraph, then sections of ``**HEADING**`` followed by ``- item`` lines.
    """
    header, intro, sections = [], [], []
    current = None
    for raw in (body or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = BOLD_LINE.match(line)
        if m and not m.group(2) and m.group(1).upper() == m.group(1) and not line.startswith("- "):
            # an all-caps bold line opens a section, unless it is the title line
            if not sections and not intro and TITLE_HINT.search(m.group(1)):
                header.append(m.group(1))
                continue
            current = {"title": m.group(1).strip(), "items": []}
            sections.append(current)
            continue
        if line.startswith(("- ", "* ", "• ")):
            if current is None:
                current = {"title": "Highlights", "items": []}
                sections.append(current)
            current["items"].append(line[2:].strip())
            continue
        if m and not sections and not intro:
            header.append((m.group(1) + " " + m.group(2)).strip())
            continue
        if current is None:
            intro.append(line)
        else:
            # a plain line after a section (rare): keep it as an item
            current["items"].append(line)
    return {"header": header, "intro": " ".join(intro), "sections": sections}


def split_notes(text: str, limit: int = 2000) -> list[str]:
    """Split Discord patch notes into messages.

    Honours explicit ``----- NEXT DISCORD MESSAGE -----`` markers, then
    splits anything still too long at blank lines, then at line ends.
    """
    parts = []
    for block in NOTES_SPLIT.split((text or "").replace("\r\n", "\n")):
        block = block.strip()
        if not block:
            continue
        if len(block) <= limit:
            parts.append(block)
            continue
        chunk = ""
        for para in block.split("\n\n"):
            for piece in _hard_split(para, limit):
                candidate = (chunk + "\n\n" + piece) if chunk else piece
                if len(candidate) <= limit:
                    chunk = candidate
                else:
                    if chunk:
                        parts.append(chunk)
                    chunk = piece
        if chunk:
            parts.append(chunk)
    return parts


def _hard_split(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    out, chunk = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            out.append(line[:limit])
            line = line[limit:]
        candidate = (chunk + "\n" + line) if chunk else line
        if len(candidate) <= limit:
            chunk = candidate
        else:
            out.append(chunk)
            chunk = line
    if chunk:
        out.append(chunk)
    return out


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------- event times
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
TIME_RE = r"(?P<h>\d{1,2})[:.h](?P<m>\d{2})"


class TimeError(ValueError):
    pass


def parse_when(text: str, tz_name: str = "Europe/Brussels", now: dt.datetime | None = None) -> dt.datetime:
    """Parse a friendly start time for events into an aware UTC datetime.

    Accepts: ``2026-11-15 20:00``, ``15/11 20:00``, ``15-11-2026 20:00``,
    ``today 20:00``, ``tomorrow 20:30``, ``sat 20:00``, ``20:00`` (next
    occurrence), ``in 90m`` and ``in 2h``. Times are read in the staff time
    zone; Discord shows them to every member in their own.
    """
    tz = ZoneInfo(tz_name)
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(tz)
    s = " ".join((text or "").lower().split())
    if not s:
        raise TimeError("Give a start time, for example `sat 20:00` or `2026-11-15 20:00`.")

    m = re.fullmatch(r"in (\d+)\s*(m|min|mins|minutes|h|hr|hrs|hours)", s)
    if m:
        amount = int(m.group(1))
        delta = dt.timedelta(hours=amount) if m.group(2).startswith("h") else dt.timedelta(minutes=amount)
        return _future((now + delta).replace(second=0, microsecond=0), now)

    def at(day: dt.date, h: str, mi: str) -> dt.datetime:
        hour, minute = int(h), int(mi)
        if hour > 23 or minute > 59:
            raise TimeError("That time of day doesn't exist.")
        return dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)

    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})[ t]" + TIME_RE, s)
    if m:
        return _future(at(_date(int(m.group(1)), int(m.group(2)), int(m.group(3))), m.group("h"), m.group("m")), now)

    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))? " + TIME_RE, s)
    if m:
        year = int(m.group(3)) if m.group(3) else now.year
        when = at(_date(year, int(m.group(2)), int(m.group(1))), m.group("h"), m.group("m"))
        if not m.group(3) and when < now:
            when = at(_date(year + 1, int(m.group(2)), int(m.group(1))), m.group("h"), m.group("m"))
        return _future(when, now)

    m = re.fullmatch(r"(today|tonight|tomorrow|[a-z]{3,9})? ?" + TIME_RE, s)
    if m:
        word = m.group(1) or ""
        if word in ("", "today", "tonight"):
            when = at(now.date(), m.group("h"), m.group("m"))
            if not word and when < now:
                when += dt.timedelta(days=1)
            return _future(when, now)
        if word == "tomorrow":
            return _future(at(now.date() + dt.timedelta(days=1), m.group("h"), m.group("m")), now)
        if word[:3] in WEEKDAYS:
            ahead = (WEEKDAYS.index(word[:3]) - now.weekday()) % 7
            when = at(now.date() + dt.timedelta(days=ahead), m.group("h"), m.group("m"))
            if when < now:
                when += dt.timedelta(days=7)
            return _future(when, now)
    raise TimeError("I couldn't read that time. Try `sat 20:00`, `tomorrow 21:30` or `2026-11-15 20:00`.")


def _date(y: int, mo: int, d: int) -> dt.date:
    try:
        return dt.date(y, mo, d)
    except ValueError as e:
        raise TimeError("That date doesn't exist.") from e


def _future(when: dt.datetime, now: dt.datetime) -> dt.datetime:
    if when <= now:
        raise TimeError("That time is in the past.")
    if when - now > dt.timedelta(days=180):
        raise TimeError("Events can be scheduled up to six months ahead.")
    return when.astimezone(dt.timezone.utc)
