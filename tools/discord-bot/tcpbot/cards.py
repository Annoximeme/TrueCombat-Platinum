"""Image cards and icon art, drawn with Pillow in the game's HUD style.

Everything here is pure: data in, PNG bytes out. The cogs call these through
asyncio.to_thread so drawing never blocks the bot. Fonts are the website's own
(SIL Open Font License), converted to TTF in assets/fonts.
"""

from __future__ import annotations

import io
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import text as T

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FONTS = ASSETS / "fonts"



def _token(name: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    """A colour from assets/tokens.json, the shared design tokens (website repo tools/design)."""
    try:
        import json
        value = json.loads((ASSETS / "tokens.json").read_text(encoding="utf-8"))[name].lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except (OSError, ValueError, KeyError, TypeError):
        return fallback


# Palette: the shared design tokens, with the bot's own extras (medals, card edges) below
INK = _token("bg", (13, 16, 22))
PANEL = _token("panel", (20, 25, 34))
PANEL_HI = _token("panel2", (26, 32, 43))
LINE = (52, 61, 76)            # card edges sit a step brighter than web hairlines
TEXT = _token("fg", (232, 234, 239))
MUTED = _token("muted", (154, 163, 179))
RED = _token("red", (214, 59, 59))
AMBER = _token("amber", (231, 167, 60))
GREEN = _token("ok", (79, 191, 122))
GOLD = (201, 162, 39)
BLUE = (91, 155, 213)
SILVER = (176, 186, 199)
BRONZE = (184, 115, 51)
GREY = (110, 118, 132)

ORANGE = (242, 157, 31)       # Spec Ops orange, as in the game's own team emblem
TEAM_COLOURS = {"specops": ORANGE, "blue": BLUE, "terrorists": RED, "red": RED}
GAME_ICONS = ASSETS / "game-icons"

# The game's own rank insignia (gfx/hud/ranks), mapped onto the 21 player levels of tcp_stats.
# Level:     1-4 PFC chevron, 5 corporal, 6-11 sergeant, 12-13 lieutenant, 14 captain, 15-16 major,
#            17 colonel, 18 one star, 19 two stars, 20-21 three stars.
INSIGNIA = ["rank02"] * 4 + ["rank03"] + ["rank04"] * 6 + ["rank05"] * 2 + ["rank06"] + ["rank07"] * 2 + \
           ["rank08", "rank09", "rank10", "rank11", "rank11"]
INSIGNIA_FILES = {"rank02": "rank02_private_first_class", "rank03": "rank03_corporal", "rank04": "rank04_sergeant",
                  "rank05": "rank05_lieutenant", "rank06": "rank06_captain", "rank07": "rank07_major",
                  "rank08": "rank08_colonel", "rank09": "rank09_brigadier_general",
                  "rank10": "rank10_lieutenant_general", "rank11": "rank11_general"}


def insignia_key(level: int) -> str:
    return INSIGNIA[max(1, min(len(INSIGNIA), int(level or 1))) - 1]


@lru_cache(maxsize=32)
def _game_icon(name: str) -> Image.Image | None:
    p = GAME_ICONS / ("%s.png" % name)
    try:
        return Image.open(p).convert("RGBA")
    except OSError:
        return None


def _square(icon: Image.Image, size: int = 128, pad: float = 0.06) -> Image.Image:
    """Centres an icon on a transparent square, keeping its proportions."""
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = int(size * (1 - 2 * pad))
    pic = icon.copy()
    pic.thumbnail((inner, inner), Image.LANCZOS)
    out.paste(pic, ((size - pic.width) // 2, (size - pic.height) // 2), pic)
    return out


def insignia(level: int, size: int = 128) -> Image.Image:
    pic = _game_icon(INSIGNIA_FILES[insignia_key(level)])
    return _square(pic, size) if pic is not None else rank_icon(T.tier_for_level(level or 1)).resize((size, size))
TIER_COLOURS = {k: ((c >> 16) & 255, (c >> 8) & 255, c & 255) for k, _n, _f, c in T.RANK_TIERS}


# ================================================================ basics
@lru_cache(maxsize=64)
def font(kind: str, size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    name = {"head": "saira-condensed-600-latin.ttf", "body": "ibm-plex-sans-latin.ttf",
            "mono": "jetbrains-mono-latin.ttf"}[kind]
    f = ImageFont.truetype(str(FONTS / name), size)
    if kind != "head":
        try:
            f.set_variation_by_axes([weight])
        except (OSError, ValueError):
            pass
    return f


def png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _fit(text: str, f: ImageFont.FreeTypeFont, width: int) -> str:
    text = text or ""
    if f.getlength(text) <= width:
        return text
    while text and f.getlength(text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _tint(c, k: float):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def _mix(a, b, t: float):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _background(w: int, h: int, art: Path | None = None, dim: float = 0.28) -> Image.Image:
    """Dark panel, or the map's artwork dimmed and blurred behind the content."""
    img = Image.new("RGB", (w, h), INK)
    if art and art.is_file():
        try:
            pic = Image.open(art).convert("RGB")
            scale = max(w / pic.width, h / pic.height)
            pic = pic.resize((math.ceil(pic.width * scale), math.ceil(pic.height * scale)), Image.LANCZOS)
            left, top = (pic.width - w) // 2, (pic.height - h) // 2
            pic = pic.crop((left, top, left + w, top + h)).filter(ImageFilter.GaussianBlur(3))
            img = Image.blend(img, pic, dim)
        except OSError:
            pass
    # soft vertical shade so text always reads
    shade = Image.new("L", (1, h))
    for y in range(h):
        shade.putpixel((0, y), int(70 + 120 * (y / max(1, h - 1))))
    img.paste(Image.new("RGB", (w, h), INK), (0, 0), shade.resize((w, h)))
    return img


def _header(d: ImageDraw.ImageDraw, w: int, kicker: str, title: str, accent=RED, right: str = "") -> int:
    d.rectangle((0, 0, w, 6), fill=accent)
    d.rectangle((40, 38, 46, 92), fill=accent)
    d.text((62, 34), kicker.upper(), font=font("body", 20, 600), fill=MUTED)
    d.text((60, 56), _fit(title, font("head", 46), w - 380), font=font("head", 46), fill=TEXT)
    if right:
        f = font("head", 26)
        d.text((w - 40 - f.getlength(right), 50), right, font=f, fill=MUTED)
    return 120


def _footer(d: ImageDraw.ImageDraw, w: int, h: int, left: str = "truecombat.eu"):
    d.line((40, h - 46, w - 40, h - 46), fill=LINE, width=1)
    d.text((40, h - 36), "TRUECOMBAT: PLATINUM", font=font("head", 20), fill=MUTED)
    f = font("mono", 16)
    d.text((w - 40 - f.getlength(left), h - 33), left, font=f, fill=AMBER)


def map_art(site_root: str | None, mapname: str | None) -> Path | None:
    """The website's artwork for a map, read from the local copy of the site."""
    if not site_root or (mapname or "").lower() not in T.MAP_NAMES:
        return None
    label = T.map_label(mapname).lower()
    for rel in ("img/maps/%s-hd.webp" % label, "img/map-%s.webp" % label):
        p = Path(site_root) / rel
        if p.is_file():
            return p
    return None


# ================================================================ icons
def _canvas(size: int = 128):
    img = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), size * 4


def _done(img: Image.Image, size: int = 128) -> Image.Image:
    return img.resize((size, size), Image.LANCZOS)


def _chevron(d, cx, y, w, h, thick, fill):
    d.polygon([(cx - w, y), (cx, y + h), (cx + w, y), (cx + w, y + thick), (cx, y + h + thick),
               (cx - w, y + thick)], fill=fill)


def _star(d, cx, cy, r, fill, points=5):
    pts = []
    for i in range(points * 2):
        a = math.pi / points * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def _shield(d, s, fill, edge):
    m = s * 0.08
    pts = [(m, m * 1.2), (s - m, m * 1.2), (s - m, s * 0.55), (s / 2, s - m * 0.6), (m, s * 0.55)]
    d.polygon(pts, fill=edge)
    k = s * 0.05
    inner = [(m + k, m * 1.2 + k), (s - m - k, m * 1.2 + k), (s - m - k, s * 0.55 - k * 0.3),
             (s / 2, s - m * 0.6 - k * 1.6), (m + k, s * 0.55 - k * 0.3)]
    d.polygon(inner, fill=fill)


def rank_icon(tier: str) -> Image.Image:
    """Insignia per rank tier: chevrons for enlisted and NCOs, bars for officers, stars for generals."""
    img, d, s = _canvas()
    col = TIER_COLOURS.get(tier, SILVER)
    _shield(d, s, _tint(col, 0.22), col)
    cx = s / 2
    if tier == "enlisted":
        _chevron(d, cx, s * 0.30, s * 0.26, s * 0.20, s * 0.09, col)
    elif tier == "nco":
        for i in range(3):
            _chevron(d, cx, s * (0.22 + 0.12 * i), s * 0.26, s * 0.18, s * 0.07, col)
    elif tier == "officer":
        for i in range(2):
            y = s * (0.30 + 0.17 * i)
            d.rounded_rectangle((s * 0.27, y, s * 0.73, y + s * 0.10), radius=s * 0.02, fill=col)
    else:
        _star(d, cx, s * 0.36, s * 0.16, col)
        _star(d, cx - s * 0.17, s * 0.58, s * 0.10, col)
        _star(d, cx + s * 0.17, s * 0.58, s * 0.10, col)
    return _done(img)


def medal_icon(place: int) -> Image.Image:
    img, d, s = _canvas()
    col = {1: GOLD, 2: SILVER, 3: BRONZE}.get(place, GREY)
    d.polygon([(s * 0.30, 0), (s * 0.45, 0), (s * 0.58, s * 0.40), (s * 0.43, s * 0.40)], fill=_tint(RED, 0.9))
    d.polygon([(s * 0.55, 0), (s * 0.70, 0), (s * 0.57, s * 0.40), (s * 0.42, s * 0.40)], fill=_tint(BLUE, 0.9))
    d.ellipse((s * 0.18, s * 0.32, s * 0.82, s * 0.96), fill=_tint(col, 0.55))
    d.ellipse((s * 0.23, s * 0.37, s * 0.77, s * 0.91), fill=col)
    f = ImageFont.truetype(str(FONTS / "saira-condensed-600-latin.ttf"), int(s * 0.38))
    t = str(place)
    d.text((s / 2 - f.getlength(t) / 2, s * 0.40), t, font=f, fill=_tint(col, 0.35))
    return _done(img)


def team_icon(team: str) -> Image.Image:
    key = {"blue": "specops", "red": "terrorists"}.get(team, team)
    pic = _game_icon("flag_" + key) if key in ("specops", "terrorists") else None
    if pic is not None:
        sq = _square(pic, 128, 0.04)
        mask = Image.new("L", sq.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((5, 5, 123, 123), radius=18, fill=255)
        sq.putalpha(Image.composite(sq.getchannel("A"), mask, mask))
        return sq
    img, d, s = _canvas()
    col = TEAM_COLOURS.get(team, GREY)
    _shield(d, s, _tint(col, 0.30), col)
    if team in ("specops", "blue"):
        # crosshair: the counter-terror unit
        cx, cy, r = s / 2, s * 0.47, s * 0.20
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=int(s * 0.05))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            d.line((cx + dx * r * 0.5, cy + dy * r * 0.5, cx + dx * r * 1.45, cy + dy * r * 1.45),
                   fill=col, width=int(s * 0.05))
    else:
        # crossed blades
        w = int(s * 0.07)
        d.line((s * 0.30, s * 0.25, s * 0.70, s * 0.70), fill=col, width=w)
        d.line((s * 0.70, s * 0.25, s * 0.30, s * 0.70), fill=col, width=w)
    return _done(img)


def dot_icon(colour) -> Image.Image:
    img, d, s = _canvas()
    d.ellipse((s * 0.14, s * 0.14, s * 0.86, s * 0.86), fill=_tint(colour, 0.35))
    d.ellipse((s * 0.26, s * 0.26, s * 0.74, s * 0.74), fill=colour)
    return _done(img)


def star_icon(colour=GOLD) -> Image.Image:
    img, d, s = _canvas()
    _star(d, s / 2, s * 0.53, s * 0.46, _tint(colour, 0.5))
    _star(d, s / 2, s * 0.53, s * 0.38, colour)
    return _done(img)


def icon_set() -> dict[str, Image.Image]:
    """Every bot emoji, by name. Names are prefixed so they never clash with server emoji."""
    out = {"tcp_" + k: insignia(INSIGNIA.index(k) + 1) for k in INSIGNIA_FILES}
    out.update({"tcp_medal%d" % i: medal_icon(i) for i in (1, 2, 3)})
    out.update({"tcp_specops": team_icon("specops"), "tcp_terrorists": team_icon("terrorists")})
    out.update({"tcp_live": dot_icon(GREEN), "tcp_filling": dot_icon(AMBER), "tcp_empty": dot_icon(GREY),
                "tcp_offline": dot_icon(RED), "tcp_mvp": star_icon(GOLD)})
    return out


# ================================================================ cards
def _tier_badge(img: Image.Image, level: int, x: int, y: int, size: int):
    badge = insignia(level, size)
    img.paste(badge, (x, y), badge)


def _bar(d, x, y, w, h, share, colour, back=PANEL_HI):
    d.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=back)
    if share > 0:
        d.rounded_rectangle((x, y, x + max(h, int(w * min(1.0, share))), y + h), radius=h // 2, fill=colour)


def _stat(d, x, y, label, value, colour=TEXT, w=230):
    d.text((x, y), label.upper(), font=font("body", 17, 600), fill=MUTED)
    d.text((x, y + 22), _fit(value, font("head", 40), w), font=font("head", 40), fill=colour)


def profile_card(p: dict, site_root: str | None = None) -> bytes:
    W, H = 1200, 630
    recent = p.get("recent") or []
    art = map_art(site_root, recent[0]["map"]) if recent else None
    img = _background(W, H, art, 0.22)
    d = ImageDraw.Draw(img)
    rank = p.get("rank") or {}
    pos = p.get("position")
    _header(d, W, "Player profile", T.clean(p.get("name"), 32) or "Unknown", RED,
            ("#%d" % pos) if pos else "Unranked")

    # rank block
    _tier_badge(img, rank.get("level") or 1, 40, 140, 120)
    d.text((180, 146), (rank.get("title") or "Recruit").upper(), font=font("head", 40), fill=TEXT)
    d.text((180, 192), "Level %d" % (rank.get("level") or 1), font=font("body", 22, 500), fill=MUTED)
    xp, lo, hi = rank.get("xp") or 0, rank.get("xpThis") or 0, rank.get("xpNext")
    share = 1.0 if not hi or hi <= lo else (xp - lo) / float(hi - lo)
    _bar(d, 180, 232, 560, 14, share, TIER_COLOURS.get(T.tier_for_level(rank.get("level") or 1), RED))
    d.text((750, 226), ("%s / %s XP" % (T.num(xp), T.num(hi))) if hi else "%s XP · top rank" % T.num(xp),
           font=font("mono", 18), fill=MUTED)

    # headline stats
    matches = p.get("matches") or 0
    stats = [("Skill rating", T.num(p.get("rating")), AMBER),
             ("K/D", str(p.get("kd", 0)), TEXT),
             ("Win rate", T.pct(p.get("wins", 0), matches), TEXT),
             ("Headshots", T.pct(p.get("headshots", 0), p.get("kills", 0)), TEXT),
             ("Matches", T.num(matches), TEXT)]
    x = 40
    for label, value, colour in stats:
        _stat(d, x, 290, label, value, colour, 200)
        x += 228

    # weapons
    d.text((40, 384), "WEAPONS", font=font("body", 17, 600), fill=MUTED)
    weapons = [w for w in p.get("weapons") or [] if w.get("kills")][:4]
    top = max([w["kills"] for w in weapons] or [1])
    y = 414
    for wpn in weapons:
        d.text((40, y), _fit(wpn["name"], font("body", 22, 500), 200), font=font("body", 22, 500), fill=TEXT)
        _bar(d, 250, y + 9, 260, 10, wpn["kills"] / float(top), RED)
        d.text((524, y + 1), "%s" % T.num(wpn["kills"]), font=font("mono", 19), fill=MUTED)
        y += 38
    if not weapons:
        d.text((40, y), "No kills recorded yet", font=font("body", 22), fill=MUTED)

    # recent form
    d.text((640, 384), "RECENT MATCHES", font=font("body", 17, 600), fill=MUTED)
    y = 414
    for m in recent[:4]:
        won = m.get("won")
        d.rounded_rectangle((640, y, 676, y + 28), radius=5, fill=GREEN if won else _tint(RED, 0.85))
        d.text((658, y + 14), "W" if won else "L", font=font("head", 24), fill=INK, anchor="mm")
        d.text((690, y + 1), T.map_label(m.get("map")), font=font("body", 22, 500), fill=TEXT)
        d.text((860, y + 2), "%d-%d" % (m.get("kills", 0), m.get("deaths", 0)), font=font("mono", 19), fill=MUTED)
        ch = int(m.get("ratingChange") or 0)
        t = T.signed(ch)
        f = font("mono", 19)
        d.text((W - 40 - f.getlength(t), y + 2), t, font=f, fill=GREEN if ch > 0 else (RED if ch < 0 else MUTED))
        y += 38
    if not recent:
        d.text((640, y), "No ranked matches yet", font=font("body", 22), fill=MUTED)
    _footer(d, W, H, "truecombat.eu/player")
    return png(img)


def leaderboard_card(board: dict, sort: str = "rating", period: str = "all") -> bytes:
    players = (board.get("players") or [])[:10]
    W = 1200
    H = 200 + 56 * max(1, len(players)) + 60
    img = _background(W, H)
    d = ImageDraw.Draw(img)
    label = T.SORT_LABELS.get(sort, "Skill rating")
    _header(d, W, "Leaderboard" + (" · last 30 days" if period == "30d" else ""), label, GOLD,
            "%s matches" % T.num(board.get("matches")) if board.get("matches") else "")
    y = 140
    cols = [(40, "#"), (120, "PLAYER"), (640, "RANK"), (960, label.split(" ")[0].upper())]
    for x, t in cols:
        d.text((x, y), t, font=font("body", 16, 600), fill=MUTED)
    y += 34

    def value(p):
        return {"rating": T.num(p["rating"]), "xp": T.num(p["rank"]["xp"]), "kills": T.num(p["kills"]),
                "kd": "%.2f" % p["kd"], "headshots": T.num(p["headshots"]), "wins": T.num(p["wins"])}.get(sort, "")

    if not players:
        d.text((40, y + 6), "Nobody has qualified yet. Finish a ranked match to get on the board.",
               font=font("body", 24), fill=MUTED)
    for i, p in enumerate(players):
        if i % 2 == 0:
            d.rectangle((30, y - 6, W - 30, y + 46), fill=PANEL)
        place = p.get("position") or i + 1
        if place <= 3:
            m = medal_icon(place).resize((40, 40), Image.LANCZOS)
            img.paste(m, (36, y - 1), m)
        else:
            d.text((44, y), str(place), font=font("head", 32), fill=MUTED)
        name_col = TEXT if place > 3 else (GOLD, SILVER, BRONZE)[place - 1]
        d.text((120, y), _fit(T.clean(p["name"], 32), font("head", 32), 500), font=font("head", 32), fill=name_col)
        _tier_badge(img, p["rank"].get("level") or 1, 640, y, 36)
        d.text((686, y + 4), _fit(p["rank"]["title"], font("body", 22, 500), 260), font=font("body", 22, 500), fill=TEXT)
        v = value(p)
        f = font("head", 32)
        d.text((W - 60 - f.getlength(v), y), v, font=f, fill=AMBER if i == 0 else TEXT)
        y += 56
    _footer(d, W, H, "truecombat.eu/leaderboards")
    return png(img)


def match_card(row: dict, detail: dict | None, site_root: str | None = None) -> bytes:
    m = detail or row
    players = (detail or {}).get("players") or []
    teams: dict[str, list[dict]] = {}
    for p in players:
        teams.setdefault(p.get("team") or "", []).append(p)
    winner = m.get("winner")
    order = sorted(teams, key=lambda t: (t != winner, t))[:2] or ["specops", "terrorists"]
    rows = max([min(8, len(teams.get(t, []))) for t in order] or [0])
    W, H = 1200, 300 + 44 * max(rows, 1) + 120
    img = _background(W, H, map_art(site_root, m.get("map")), 0.35)
    d = ImageDraw.Draw(img)
    sub = " · ".join(x for x in (m.get("mode"), "%d rounds" % m["rounds"] if m.get("rounds") else "",
                                 T.duration(m["duration"]) if m.get("duration") else "") if x)
    _header(d, W, "Match report" + (" · " + sub if sub else ""), T.map_label(m.get("map")), GOLD)

    # scoreline
    score = (detail or {}).get("score") or {}
    names = {t: _team_name(t) for t in order}
    cx = W // 2
    left, right = (order + ["", ""])[:2]
    fs = font("head", 84)
    a, b = str(score.get(left, "")), str(score.get(right, ""))
    if a and b:
        d.text((cx - 40 - fs.getlength(a), 118), a, font=fs, fill=TEAM_COLOURS.get(left, TEXT))
        d.text((cx - 10, 130), "–", font=font("head", 60), fill=MUTED)
        d.text((cx + 40, 118), b, font=fs, fill=TEAM_COLOURS.get(right, TEXT))
    fh = font("head", 34)
    for t, x, align in ((left, cx - 150, "r"), (right, cx + 150, "l")):
        if not t:
            continue
        label = names[t].upper()
        tx = x - fh.getlength(label) if align == "r" else x
        d.text((tx, 150), label, font=fh, fill=TEXT)
        icon = team_icon(t).resize((56, 56), Image.LANCZOS)
        ix = int(tx - 70) if align == "r" else int(tx + fh.getlength(label) + 14)
        img.paste(icon, (ix, 143), icon)
        if t == winner:
            tag = "WINNER"
            ft = font("body", 16, 700)
            wx = x - ft.getlength(tag) if align == "r" else x
            d.text((wx, 194), tag, font=ft, fill=GOLD)

    # team tables
    y0 = 250
    best = max(players, key=lambda p: (p.get("xp") or 0, p["kills"])) if players else None
    for i, t in enumerate(order):
        x0 = 40 if i == 0 else cx + 20
        wcol = cx - 60
        col = TEAM_COLOURS.get(t, GREY)
        d.rectangle((x0, y0, x0 + wcol, y0 + 4), fill=col)
        d.text((x0, y0 + 12), "PLAYER", font=font("body", 15, 600), fill=MUTED)
        for lx, lab in ((x0 + wcol - 190, "K-D"), (x0 + wcol - 70, "RATING")):
            d.text((lx, y0 + 12), lab, font=font("body", 15, 600), fill=MUTED)
        y = y0 + 40
        for p in sorted(teams.get(t, []), key=lambda p: (-p["kills"], p["deaths"]))[:8]:
            star = best is not None and p is best
            nm = _fit(T.clean(p["name"], 24), font("body", 24, 500), wcol - 250)
            d.text((x0, y), nm, font=font("body", 24, 500), fill=GOLD if star else TEXT)
            if star:
                s = star_icon().resize((24, 24), Image.LANCZOS)
                img.paste(s, (int(x0 + font("body", 24, 500).getlength(nm) + 8), y + 5), s)
            d.text((x0 + wcol - 190, y + 2), "%d-%d" % (p["kills"], p["deaths"]), font=font("mono", 21), fill=TEXT)
            ch = int(p.get("ratingChange") or 0)
            d.text((x0 + wcol - 70, y + 2), T.signed(ch), font=font("mono", 21),
                   fill=GREEN if ch > 0 else (RED if ch < 0 else MUTED))
            y += 44
    if not players:
        d.text((40, y0 + 40), "The full scoreboard isn't available for this match.", font=font("body", 24), fill=MUTED)
    if best:
        bits = ["%d kills" % best["kills"]]
        if best.get("headshots"):
            bits.append("%d headshots" % best["headshots"])
        if best.get("topWeapon"):
            bits.append(best["topWeapon"])
        y = H - 100
        s = star_icon().resize((30, 30), Image.LANCZOS)
        img.paste(s, (40, y + 2), s)
        d.text((80, y), "PLAYER OF THE MATCH", font=font("body", 16, 700), fill=GOLD)
        d.text((80, y + 20), "%s · %s" % (T.clean(best["name"], 32), ", ".join(bits)), font=font("body", 22, 500),
               fill=TEXT)
    _footer(d, W, H, "truecombat.eu/match")
    return png(img)


def _team_name(key: str) -> str:
    return {"specops": "Special Ops", "terrorists": "Terrorists", "red": "Red", "blue": "Blue"}.get(
        (key or "").lower(), (key or "Team").title())


def banner(site_root: str | None = None) -> bytes:
    """The bot's profile banner (shown at 600x240). The avatar overlaps the bottom left,
    so the logo and line sit on the right over dimmed map art."""
    W, H = 1500, 600
    art = None
    if site_root:
        for name in ("railhouse", "village", "snow"):
            p = Path(site_root) / "img" / "maps" / ("%s-hd.webp" % name)
            if p.is_file():
                art = p
                break
    img = _background(W, H, art, 0.55)
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 12, W, H), fill=RED)
    logo = Path(site_root) / "img" / "logo.webp" if site_root else None
    x0 = W - 820
    if logo is not None and logo.is_file():
        pic = Image.open(logo).convert("RGBA")
        pic.thumbnail((720, 380), Image.LANCZOS)
        img.paste(pic, (x0 + (720 - pic.width) // 2, 40), pic)
        y = 40 + pic.height + 10
    else:
        d.text((x0, 120), "TRUECOMBAT", font=font("head", 130), fill=TEXT)
        d.text((x0 + 4, 250), "PLATINUM", font=font("head", 76), fill=MUTED)
        y = 370
    line = "Tactical team combat, rebuilt."
    f = font("body", 40, 500)
    d.text((x0 + (720 - f.getlength(line)) / 2, y), line, font=f, fill=TEXT)
    f = font("mono", 30)
    d.text((x0 + (720 - f.getlength("truecombat.eu")) / 2, y + 60), "truecombat.eu", font=f, fill=AMBER)
    return png(img)
