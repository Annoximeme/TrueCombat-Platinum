"""The "Briefing" release post: one framed card in Discord's newer message layout.

Command banner on top, the update's headline and intro, up to four headline
features (each with an in-game thumbnail when the site has one), a one-line
summary per remaining section, and buttons. The full notes stay on
truecombat.eu.

Everything is read from the GitHub release body. An optional block in an HTML
comment (invisible on GitHub) lets the release writer choose the banner title,
the headline features, their pictures and the short summaries:

    <!-- discord
    title: Close Quarters
    chips: Harbour | Battlefield pickups | Firing range | Vaulting
    headline: Battlefield pickups | Weapons now drop when a player falls. ... | pickups.webp
    summary: Aim and Performance | Instant ADS zoom · Aim speed option · 60 to 500 FPS limit
    devlog: https://truecombat.eu/devlog/cqb
    -->

Pictures are file names in the site's img/releases/<release slug>/ folder (or
full https URLs). Without the block the bot picks the headlines itself.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import text as T
from .sources import release_download, release_slug, release_version

BLOCK = re.compile(r"<!--\s*discord\b(.*?)-->", re.S | re.I)
BOLD_ONLY = re.compile(r"^\*\*(.+?)\*\*\s*$")
BOLD_LEAD = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")
ITEM_TITLE = re.compile(r"^\*\*(.+?)[.:]?\*\*[.:]?\s+(.*)$")
HEADING = re.compile(r"^#{1,3}\s+(.+)$")
SENTENCE = re.compile(r"(?<=[.!?])\s+")
IMAGE_EXT = (".webp", ".jpg", ".jpeg", ".png")

MAX_HEADLINES = 4
TEXT_BUDGET = 3800          # Discord allows 4,000 characters of text per message; keep a margin
SKIP_SECTIONS = ("DEVELOPMENT",)


# ================================================================ parsing
def parse(body: str) -> dict:
    """Release body -> header lines, intro, sections (with an optional lead paragraph) and closing lines."""
    body = html.unescape(BLOCK.sub("", (body or "").replace("\r\n", "\n")))
    header, intro, sections, outro = [], [], [], []
    current = None
    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        started = bool(intro or sections)
        h = HEADING.match(line)
        b = BOLD_ONLY.match(line)
        if not started and (b or (h and T.TITLE_HINT.search(h.group(1)))):
            header.append((b or h).group(1).strip())     # title lines above the intro
            continue
        if h or b:
            current = {"title": (h or b).group(1).strip().rstrip(":"), "lead": "", "items": []}
            sections.append(current)
            continue
        if not started:
            m = BOLD_LEAD.match(line)
            if m:
                header.append((m.group(1) + " " + m.group(2)).strip())
                continue
        if line.startswith(("- ", "* ", "• ")):
            if current is None:
                current = {"title": "Highlights", "lead": "", "items": []}
                sections.append(current)
            current["items"].append(_item(line[2:].strip()))
            continue
        if current is None:
            intro.append(line)
        elif not current["items"]:
            current["lead"] = (current["lead"] + " " + line).strip()
        else:
            outro.append(line)
    return {"header": header, "intro": " ".join(intro), "sections": sections, "outro": outro}


def _item(text: str) -> dict:
    m = ITEM_TITLE.match(text)
    if m:
        return {"title": m.group(1).strip().rstrip("."), "text": m.group(2).strip(), "raw": text}
    return {"title": "", "text": text, "raw": text}


def read_block(body: str) -> dict:
    """The optional <!-- discord ... --> block."""
    out = {"title": "", "devlog": "", "hero": "", "chips": [], "headlines": [], "summaries": []}
    m = BLOCK.search(body or "")
    if not m:
        return out
    for raw in m.group(1).split("\n"):
        key, sep, value = raw.strip().partition(":")
        key, value = key.strip().lower(), value.strip()
        if not sep or not value:
            continue
        parts = [p.strip() for p in value.split("|")]
        if key == "headline" and parts[0]:
            out["headlines"].append({"title": parts[0], "text": parts[1] if len(parts) > 1 else "",
                                     "image": parts[2] if len(parts) > 2 else ""})
        elif key == "summary" and len(parts) > 1:
            out["summaries"].append((parts[0], parts[1]))
        elif key == "chips":
            out["chips"] = [p for p in parts if p]
        elif key in ("title", "devlog", "hero"):
            out[key] = value
    return out


# ================================================================ helpers
def hook(text: str, limit: int) -> str:
    """The opening of a text, cut at a sentence end so it still reads as written."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    cut = max(text.rfind(". ", 0, limit), text.rfind("! ", 0, limit), text.rfind("? ", 0, limit))
    return text[: cut + 1] if cut > limit // 3 else T.clip(text, limit)


CLAUSE = re.compile(r",\s|:\s|\s(?:with|so|to|for|from)\s")


def short(item: dict, limit: int = 64) -> str:
    """A short label for one change: its bold title, else its first sentence, else its first full clause."""
    if item["title"]:
        return item["title"]
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", item["text"]).strip()
    first = SENTENCE.split(text, 1)[0].rstrip(".")
    if len(first) <= limit:
        return first
    for m in CLAUSE.finditer(first):
        head = first[: m.start()]
        if len(head) > limit:
            break
        if len(head.split()) >= 4 and "," not in head:
            return head
    cut = first.rfind(" ", 0, limit)
    return first[: cut if cut > 20 else limit].rstrip(",;") + "…"


def summary_line(items: list[dict], limit: int = 170) -> str:
    """Short labels joined with dots; clean labels first, cut ones only if room is left."""
    labels = [short(it) for it in items]
    labels = [l for l in labels if not l.endswith("…")] + [l for l in labels if l.endswith("…")]
    out, used = [], 0
    for n, label in enumerate(labels):
        if out and (used + len(label) + 3 > limit or label.endswith("…")):
            out.append("+%d more" % (len(labels) - n))
            break
        out.append(label)
        used += len(label) + 3
    return " · ".join(out)


def _is_experimental(sec: dict) -> bool:
    return sec["title"].lower().startswith("experimental")


def _is_features(sec: dict) -> bool:
    t = sec["title"].lower()
    return "new feature" in t or t in ("highlights", "headlines")


def release_dir(site_root: str, rel: dict) -> Path | None:
    slug = release_slug(rel)
    if not site_root or not slug:
        return None
    return Path(site_root) / "img" / "releases" / slug


def image_url(site: str, site_root: str, rel: dict, name: str) -> str:
    """A picture for the post: a full https URL, or a file in the site's img/releases/<slug>/ folder."""
    if not name:
        return ""
    if name.startswith("https://"):
        return name
    d = release_dir(site_root, rel)
    if d is None or not (d / name).is_file():
        return ""
    return "%s/img/releases/%s/%s" % (site.rstrip("/"), release_slug(rel), name)


def _numbered_image(site: str, site_root: str, rel: dict, n: int) -> str:
    for ext in IMAGE_EXT:
        url = image_url(site, site_root, rel, "%d%s" % (n, ext))
        if url:
            return url
    return ""


def hero_art(site_root: str, rel: dict, name: str = "") -> Path | None:
    """Art behind the banner: the release's hero picture, else a map from the site."""
    d = release_dir(site_root, rel)
    if d is not None:
        for cand in ([name] if name and not name.startswith("http") else []) + ["hero" + e for e in IMAGE_EXT]:
            if (d / cand).is_file():
                return d / cand
    if site_root:
        for m in ("railhouse", "village", "snow"):
            p = Path(site_root) / "img" / "maps" / ("%s-hd.webp" % m)
            if p.is_file():
                return p
    return None


# ================================================================ plan
@dataclass
class Briefing:
    version: str
    title: str                       # banner title ("" = the version number)
    heading: str                     # the card's ## line
    intro: str
    changes: int
    headlines: list = field(default_factory=list)   # {title, text, sub, image}
    summaries: list = field(default_factory=list)   # (name, line)
    thanks: str = ""
    notes_url: str = ""
    download_url: str = ""
    devlog_url: str = ""
    art: Path | None = None

    chip_list: list = field(default_factory=list)

    @property
    def chips(self) -> list[str]:
        """The short feature names under the banner title."""
        if self.chip_list:
            return self.chip_list
        out = []
        for h in self.headlines:
            if h["sub"]:
                out.append(h["sub"].split(" · ")[0])
            else:
                out.append(h["title"].split(":")[-1].strip())
        return out


def plan(rel: dict, site: str, site_root: str, notes_url: str) -> Briefing:
    body = rel.get("body") or ""
    parsed = parse(body)
    block = read_block(body)
    version = release_version(rel)
    sections = [s for s in parsed["sections"] if s["title"].upper() not in SKIP_SECTIONS and (s["items"] or s["lead"])]

    first, _, rest = parsed["intro"].partition(". ")
    if rest and len(first) <= 64:
        heading, intro = first.strip(), rest.strip()
    else:
        heading, intro = "Update %s" % version, parsed["intro"]
    intro = hook(intro, 420) or "A new update is ready to download."

    used: set[tuple[int, int]] = set()      # (section, item) shown as a headline
    used_sections: set[int] = set()
    headlines = []
    if block["headlines"]:
        for n, h in enumerate(block["headlines"][:MAX_HEADLINES], 1):
            headlines.append({"title": h["title"], "text": h["text"], "sub": "",
                              "image": image_url(site, site_root, rel, h["image"]) or
                              _numbered_image(site, site_root, rel, n)})
            for si, sec in enumerate(sections):          # leave out what the headline already covers
                if sec["title"].lower().startswith(h["title"].lower()):
                    used_sections.add(si)
                for ii, it in enumerate(sec["items"]):
                    if it["title"] and it["title"].lower() == h["title"].lower():
                        used.add((si, ii))
    else:
        for si, sec in enumerate(sections):
            if _is_experimental(sec) and len(headlines) < MAX_HEADLINES:
                headlines.append({"title": sec["title"], "text": hook(sec["lead"], 230) or summary_line(sec["items"]),
                                  "sub": " · ".join(it["title"] for it in sec["items"] if it["title"])})
                used_sections.add(si)
        order = sorted(range(len(sections)), key=lambda i: (not _is_features(sections[i]), i))
        for si in order:
            if si in used_sections:
                continue
            for ii, it in enumerate(sections[si]["items"]):
                if len(headlines) >= MAX_HEADLINES:
                    break
                if it["title"] and len(it["text"]) > 20:
                    headlines.append({"title": it["title"], "text": hook(it["text"], 200), "sub": ""})
                    used.add((si, ii))
        for n, h in enumerate(headlines, 1):
            h["image"] = _numbered_image(site, site_root, rel, n)

    summaries = list(block["summaries"])
    if not summaries:
        for si, sec in enumerate(sections):
            if si in used_sections:
                continue
            left = [it for ii, it in enumerate(sec["items"]) if (si, ii) not in used]
            if not left:
                continue
            name = "Also new" if (_is_features(sec) and len(left) < len(sec["items"])) else sec["title"]
            summaries.append((name, summary_line(left)))

    thanks = next((l for l in parsed["outro"] if l.lower().startswith(("thanks", "thank you to", "with thanks"))), "")
    b = Briefing(version=version, title=block["title"], heading=heading, intro=intro,
                 changes=sum(len(s["items"]) for s in sections), headlines=headlines, summaries=summaries,
                 thanks=T.clip(thanks.strip("*_ "), 200), notes_url=notes_url,
                 download_url=release_download(rel) or site.rstrip("/") + "/download",
                 devlog_url=block["devlog"] if block["devlog"].startswith("https://") else "",
                 art=hero_art(site_root, rel, block["hero"]), chip_list=block["chips"])
    _fit_budget(b)
    return b


def text_size(b: Briefing) -> int:
    n = len(b.heading) + len(b.intro) + len(b.thanks) + 200
    n += sum(len(h["title"]) + len(h["text"]) + len(h["sub"]) + 16 for h in b.headlines)
    n += sum(len(a) + len(c) + 12 for a, c in b.summaries)
    return n


def _fit_budget(b: Briefing):
    """Trim the summaries, then the headline texts, until the card fits Discord's text limit."""
    while text_size(b) > TEXT_BUDGET and b.summaries:
        longest = max(range(len(b.summaries)), key=lambda i: len(b.summaries[i][1]))
        name, line = b.summaries[longest]
        if len(line) > 80:
            b.summaries[longest] = (name, hook(line, len(line) - 40))
        else:
            b.summaries.pop()
    for h in b.headlines:
        if text_size(b) <= TEXT_BUDGET:
            break
        h["text"] = hook(h["text"], 120)


# ================================================================ Discord layout
ACCENT = 0xD63B3B          # tokens.json "red"


def banner_name(b: Briefing) -> str:
    return "patch-notes-%s.jpg" % b.version.replace(".", "-")


def layout(b: Briefing, banner: str, ping: str = "", notify=None):
    """The post itself: one Components V2 container. ``banner`` is an https URL or attachment:// name,
    ``notify`` an optional button (the Patch notes opt-in toggle)."""
    import discord

    ui = discord.ui
    parts = [ui.MediaGallery(discord.MediaGalleryItem(banner, description="TrueCombat: Platinum %s" % b.version)),
             ui.TextDisplay("-# PATCH NOTES · `v%s` · %d changes\n## %s\n%s" % (
                 b.version, b.changes, b.heading, b.intro)),
             ui.Separator(spacing=discord.SeparatorSpacing.large)]
    for n, h in enumerate(b.headlines):
        body = "### %s\n%s" % (h["title"], h["text"])
        if h.get("sub"):
            body += "\n-# %s" % h["sub"]
        if h.get("image"):
            parts.append(ui.Section(ui.TextDisplay(body), accessory=ui.Thumbnail(h["image"], description=h["title"])))
        else:
            parts.append(ui.TextDisplay(body))
        parts.append(ui.Separator(spacing=discord.SeparatorSpacing.large if n == len(b.headlines) - 1
                                  else discord.SeparatorSpacing.small))
    if b.summaries:
        lines = ["### Everything else in %s" % b.version]
        lines += ["**%s**\n-# %s" % (name, line) for name, line in b.summaries]
        parts.append(ui.TextDisplay("\n".join(lines)))
        parts.append(ui.Separator())
    foot = "The launcher updates itself on the next start."
    if b.thanks:
        foot += " " + b.thanks
    parts.append(ui.TextDisplay("-# " + foot))
    row = [ui.Button(label="Full patch notes", url=b.notes_url), ui.Button(label="Download", url=b.download_url)]
    if b.devlog_url:
        row.append(ui.Button(label="Devlog", url=b.devlog_url))
    if notify is not None:
        row.append(notify)
    parts.append(ui.ActionRow(*row))

    v = ui.LayoutView(timeout=None)
    if ping:
        v.add_item(ui.TextDisplay(ping))
    v.add_item(ui.Container(*parts, accent_colour=ACCENT))
    return v
