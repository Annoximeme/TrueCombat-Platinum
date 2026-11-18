#!/usr/bin/env python3
"""Builds the fixed parts of the live server banners (tools/server-bridge/tcp_banner.py).

The bridge draws the live text itself with the standard library only, so everything that
needs Pillow happens here, once: a background per map and banner size (map art, shading,
the TrueCombat: Platinum wordmark and the site address) and a glyph atlas per text style.
Rerun it when the map art, the wordmark or the banner layout changes.

Needs Pillow, fonttools and brotli (pip install pillow fonttools brotli).

  python tools/website/banner_assets.py
"""
import json
import pathlib

from PIL import Image, ImageDraw, ImageFilter

import og

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
OUT = ROOT / "tools" / "server-bridge" / "banner"
MAPS = ["delta", "northport", "railhouse", "snow", "stadtrand", "village"]
SIZES = {"wide": (600, 120), "small": (468, 60)}
BG = (13, 16, 22)
RED = (214, 59, 59)
# text styles the bridge can draw: (font file, pixel size)
STYLES = {
    "wide-big": ("saira-condensed-800-latin.woff2", 46),
    "wide-title": ("saira-condensed-700-latin.woff2", 25),
    "wide-sub": ("saira-condensed-600-latin.woff2", 17),
    "wide-label": ("saira-condensed-700-latin.woff2", 12),
    "small-big": ("saira-condensed-800-latin.woff2", 30),
    "small-title": ("saira-condensed-700-latin.woff2", 18),
    "small-sub": ("saira-condensed-600-latin.woff2", 13),
    "small-label": ("saira-condensed-700-latin.woff2", 10),
}
CHARS = "".join(chr(c) for c in range(32, 127)) + "·–—’‘“”…ÀÁÂÄÇÈÉÊËÍÎÏÑÓÔÖØÙÚÛÜßàáâäçèéêëíîïñóôöøùúûüÿ"


def cover(img, W, H):
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def background(art, size):
    W, H = size
    img = cover(Image.open(DOCS / "img" / art).convert("RGB"), W, H)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    # dark panel on the left for the text, the map shows through on the right
    shade = Image.new("L", size)
    px = shade.load()
    for x in range(W):
        k = min(1.0, max(0.0, (x - W * 0.30) / (W * 0.55)))
        a = int(250 - 120 * k)
        for y in range(H):
            px[x, y] = a
    img = Image.composite(Image.new("RGB", size, BG), img, shade)
    # right edge darkened again behind the player count
    glow = Image.new("L", size)
    gp = glow.load()
    for x in range(W):
        k = max(0.0, (x - W * 0.70) / (W * 0.30))
        for y in range(H):
            gp[x, y] = int(150 * k)
    img = Image.composite(Image.new("RGB", size, BG), img, glow)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 3, W, H], fill=RED)                     # red base line, like the site's top bar
    d.rectangle([0, 0, W - 1, H - 1], outline=(38, 46, 59))
    wm = Image.open(DOCS / "img" / "wordmark.webp").convert("RGBA")
    wh = 22 if W >= 600 else 15
    wm = wm.resize((round(wm.width * wh / wm.height), wh), Image.LANCZOS)
    if W >= 600:
        img.paste(wm, (18, 14), wm)
        f = og.font("saira-condensed-600-latin.woff2", 13)
        d.text((18, H - 22), "TRUECOMBAT.EU", font=f, fill=(154, 163, 179))
    else:
        img.paste(wm, (W - wm.width - 12, H - wm.height - 8), wm)
    return img


def atlas(style):
    name, px = STYLES[style]
    f = og.font(name, px)
    asc, desc = f.getmetrics()
    H = asc + desc
    glyphs, x, cells = {}, 0, []
    for ch in CHARS:
        try:
            l, t, r, b = f.getbbox(ch, anchor="ls")
            adv = f.getlength(ch)
        except Exception:
            continue
        w = max(0, r - l)
        cells.append((ch, l, w, adv))
        glyphs[ch] = [x, w, round(adv, 2), l]
        x += w + 2
    img = Image.new("L", (max(1, x), H))
    d = ImageDraw.Draw(img)
    for ch, l, w, adv in cells:
        d.text((glyphs[ch][0] - l, asc), ch, font=f, fill=255, anchor="ls")
    return img, {"h": H, "asc": asc, "g": glyphs}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for size, wh in SIZES.items():
        for m in MAPS + ["default"]:
            art = ("map-%s.webp" % m) if m != "default" else "hero-village-rooftop.webp"
            background(art, wh).save(OUT / ("bg-%s-%s.png" % (size, m)), optimize=True)
    meta = {}
    for style in STYLES:
        img, info = atlas(style)
        img.save(OUT / ("font-%s.png" % style), optimize=True)
        meta[style] = info
    (OUT / "fonts.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print("banner assets in", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
