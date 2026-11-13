#!/usr/bin/env python3
"""Builds the Platinum icon family from the Lucide sources in src/ (see icons.json).

  python tools/design/icons/build_icons.py

Writes tools/design/out/icons/:
  svg/<name>.svg           24x24, currentColor, Direction A stroke (2 px, square caps, mitred joins)
  png/<size>/<name>.png    white on transparent, 16 20 24 32 48 64 px (launcher, staff portal)
  tga/<name>.tga           64 px white with alpha (in-game menus and HUD, gfx/platinum/icons/)
  sprite.svg               every icon as a <symbol id="i-<name>"> (website, staff portal)
and returns inline SVG strings to the website build (inline()).
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "icons"
MAP = {k: v for k, v in json.loads((HERE / "icons.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}
SIZES = [16, 20, 24, 32, 48, 64]


def body(name):
    raw = (HERE / "src" / (MAP[name] + ".svg")).read_text(encoding="utf-8")
    return re.search(r"<svg[^>]*>(.*)</svg>", raw, re.S).group(1).strip()


def svg(name, size=24, extra=""):
    inner = re.sub(r"\s*\n\s*", "", body(name))
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true"%s>%s</svg>') % (size, size, extra, inner)


def inline(name, size=18):
    """For the website build: one icon as inline SVG."""
    return svg(name, size)


def main():
    (OUT / "svg").mkdir(parents=True, exist_ok=True)
    symbols = []
    for name in MAP:
        (OUT / "svg" / (name + ".svg")).write_text(svg(name).replace(' aria-hidden="true"', ' xmlns="http://www.w3.org/2000/svg"') + "\n", encoding="utf-8")
        symbols.append('<symbol id="i-%s" viewBox="0 0 24 24">%s</symbol>' % (name, re.sub(r"\s*\n\s*", "", body(name))))
    (OUT / "sprite.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" stroke-linejoin="miter">\n'
        + "\n".join(symbols) + "\n</svg>\n", encoding="utf-8")
    try:
        import cairosvg
        from PIL import Image
    except ImportError:
        print("icons: svg + sprite written; pip install cairosvg pillow for the png/tga sizes")
        return
    import io
    for name in MAP:
        white = svg(name).replace("currentColor", "#ffffff").replace(' aria-hidden="true"', ' xmlns="http://www.w3.org/2000/svg"')
        for s in SIZES:
            d = OUT / "png" / str(s)
            d.mkdir(parents=True, exist_ok=True)
            cairosvg.svg2png(bytestring=white.encode(), write_to=str(d / (name + ".png")), output_width=s, output_height=s)
        (OUT / "tga").mkdir(exist_ok=True)
        im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=white.encode(), output_width=64, output_height=64))).convert("RGBA")
        im.save(OUT / "tga" / (name + ".tga"), rle=False)
    print("icons: %d icons, %d png sizes, tga, sprite" % (len(MAP), len(SIZES)))


if __name__ == "__main__":
    main()
