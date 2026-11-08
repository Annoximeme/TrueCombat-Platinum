#!/usr/bin/env python3
"""Builds the 1200x630 share images (docs/img/og-<page>.jpg) that Discord, X and
other sites show when a page link is posted. The home page keeps docs/img/og.jpg.

Needs Pillow, fonttools and brotli (pip install pillow fonttools brotli).
Run it after changing a page's key art or title:   python tools/website/og.py
"""
import io
import pathlib

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"
W, H = 1200, 630

PAGES = {
    "maps": ("map-delta.webp", "Maps", "Six original TrueCombat: Elite maps, rendered in DirectX 12"),
    "weapons": ("media-grenade.webp", "Arsenal", "Every weapon, with the original TC:E values"),
    "media": ("map-northport.webp", "Screenshots", "Captured in-game on the DirectX 12 renderer"),
    "guide": ("media-village-yard.webp", "Basic training", "Everything you need before your first match"),
    "servers": ("shot-hosted.webp", "Find a match", "Official and community servers, live"),
    "leaderboards": ("media-map-vote.webp", "Leaderboards", "Rank, rating and combat record from every ranked match"),
    "player": ("map-stadtrand.webp", "Player profiles", "Rank, weapons and recent matches for every ranked player"),
    "news": ("map-railhouse.webp", "Patch notes", "Every update since the first public build"),
    "press": ("map-snow.webp", "Press kit", "Logos, unedited screenshots and a fact sheet"),
    "studio": ("map-village.webp", "Team Terminus", "The studio behind TrueCombat: Platinum"),
}


def font(name, size):
    """Loads one of the site's self-hosted woff2 fonts."""
    f = TTFont(DOCS / "fonts" / name)
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    buf.seek(0)
    return ImageFont.truetype(buf, size)


def cover(img):
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def main():
    logo = Image.open(DOCS / "img" / "logo.webp").convert("RGBA")
    logo = logo.resize((300, round(300 * logo.height / logo.width)), Image.LANCZOS)
    title_f = font("saira-condensed-800-latin.woff2", 132)
    sub_f = font("ibm-plex-sans-latin.woff2", 34)
    for page, (art, title, sub) in PAGES.items():
        bg = cover(Image.open(DOCS / "img" / art).convert("RGB")).filter(ImageFilter.GaussianBlur(1.2))
        shade = Image.new("L", (W, H))
        px = shade.load()
        for x in range(W):
            a = int(235 - 150 * min(1, x / (W * 0.85)))
            for y in range(H):
                px[x, y] = min(255, a + int(30 * (y / H)))
        dark = Image.new("RGB", (W, H), (13, 16, 22))
        img = Image.composite(dark, bg, shade).convert("RGBA")
        img.alpha_composite(logo, (64, 52))
        d = ImageDraw.Draw(img)
        d.rectangle((64, 322, 128, 328), fill=(230, 72, 72))
        d.text((58, 290), title.upper(), font=title_f, fill=(240, 242, 246))
        d.text((64, 470), sub, font=sub_f, fill=(178, 186, 200))
        d.text((64, 536), "truecombat.eu", font=font("jetbrains-mono-latin.woff2", 24), fill=(231, 167, 60))
        img.convert("RGB").save(DOCS / "img" / ("og-%s.jpg" % page), quality=84, optimize=True, progressive=True)
        print("og-%s.jpg" % page)


if __name__ == "__main__":
    main()
