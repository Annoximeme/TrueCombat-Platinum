#!/usr/bin/env python3
"""Teaser art for devlog posts about a major update or patch.

Takes one clean in-game screenshot (ideally 2560x1440, Ultra preset, no HUD) and turns it into
finished key art: night relight, lamp bloom and light shafts, depth haze, floating dust, a
filmic grade, the game logo and a metal headline.

  landscape  1920x1080 JPG, plus 1280x720 WebP and -640 WebP for docs/img/devlog/
  story      1080x1920 JPG for Instagram stories (top and bottom 250 px stay free of text)

Every format can also be rendered --clean (graded shot only, no logo or text): use that one as the post's
front-matter `image`, because the post header and the share image already print the title.
Put the version with text at the top of the post body.

Example (the 0.38.0 CQB teaser):
  python tools/website/devlog/teaser.py shot.jpg --kicker "UPDATE 0.38.0" --title "CLOSE QUARTERS" \
      --sub "New Harbour map  ·  16 new weapons  ·  CQB Rules" \
      --lights .506,.105 .600,.105 --small-lights .528,.282 .578,.282 --haze .557,.484 \
      --out docs/img/devlog/cqb-teaser --clean

Light positions are fractions of the source image (x, y). --lights are lamps that throw a
beam downwards, --small-lights are distant lamps, --haze is the far end of the scene.
Needs numpy, opencv-python-headless, pillow, fonttools and brotli.
"""
import argparse
import io
import pathlib

import cv2
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DOCS = pathlib.Path(__file__).resolve().parents[3] / "docs"
LUMA = np.float32([.299, .587, .114])
RED = (214, 22, 52)


def font(name, size):
    f = TTFont(DOCS / "fonts" / name)
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    buf.seek(0)
    return ImageFont.truetype(buf, size)


def blur(img, s):
    return cv2.GaussianBlur(img, (0, 0), s)


def filmic(x):
    x = np.maximum(x, 0)
    return (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)


def frame(src, W, H, cx):
    """Cover-crop the source to W:H around horizontal centre cx (fraction). Returns image + mapper."""
    sh, sw = src.shape[:2]
    if sw / sh > W / H:
        ch, cw = sh, round(sh * W / H)
    else:
        cw, ch = sw, round(sw * H / W)
    x0 = int(np.clip(cx * sw - cw / 2, 0, sw - cw))
    y0 = (sh - ch) // 2
    img = cv2.resize(src[y0:y0 + ch, x0:x0 + cw], (W, H), interpolation=cv2.INTER_LANCZOS4 if cw < W else cv2.INTER_AREA)
    k = W / cw
    return img.clip(0, 1), (lambda p: ((p[0] * sw - x0) * k, (p[1] * sh - y0) * k)), k


def grade(a, W, H, to, k, lights, small, haze, focus, rng, story):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = W / 1080 if story else H / 1080  # 1.0 at the reference sizes
    a = cv2.bilateralFilter(a.astype(np.float32), 5, 0.04, 3)
    lum = a @ LUMA
    a = a + (lum - blur(lum, 18 * u))[..., None] * 0.40          # clarity
    a = (a + (a - blur(a, 1.2)) * (0.9 if k > 1 else 0.5)).clip(0, 1)
    a = a ** 1.08
    # deepen and cool the sky
    lum = a @ LUMA
    sky = blur(((np.clip(1 - (yy - 0.10 * H) / (0.26 * H), 0, 1)) * (lum < 0.32)).astype(np.float32), 25 * u)
    a = a * (1 - sky[..., None] * 0.40) + sky[..., None] * np.float32([0, .012, .03])
    # relight: night ambient with pools of light
    L = [to(p) for p in lights]
    S = [to(p) for p in small]
    hz = to(haze) if haze else None
    fc = to(focus)
    def pool(c, rx, ry):
        return np.exp(-(((xx - c[0]) / rx) ** 2 + ((yy - c[1]) / ry) ** 2))
    lm = np.full((H, W), 0.45, np.float32)
    if L:
        cx = np.mean([p[0] for p in L]); cy = np.mean([p[1] for p in L])
        lm += 0.55 * pool((cx, cy + 300 * u), 430 * u, 420 * u)
    if hz:
        lm += 0.35 * pool(hz, 260 * u, 200 * u)
    lm += 0.25 * pool(fc, 260 * u, 300 * u)
    for p in L:
        lm += 0.18 * pool((p[0], p[1] + 850 * u), 200 * u, 260 * u)
    a = a * np.minimum(lm, 1.15)[..., None]
    # teal shadows, amber highlights, less yellow ballast, filmic curve
    lum = a @ LUMA
    sh = np.clip(1 - lum * 2.2, 0, 1)[..., None]
    hi = np.clip((lum - .35) * 1.8, 0, 1)[..., None]
    a = a + sh * np.float32([-.025, .012, .045]) + hi * np.float32([.05, .018, -.04])
    a = lum[..., None] + (a - lum[..., None]) * 1.12
    hsv = cv2.cvtColor(a.clip(0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
    hsv[..., 1] *= 1 - 0.30 * np.exp(-((hsv[..., 0] - 45) / 18) ** 2)
    a = filmic(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) * 0.92) ** 1.12
    # lamps, beams and far glow
    glow = np.zeros((H, W, 3), np.float32)
    def spot(c, r, col, s):
        glow[...] += pool(c, r, r)[..., None] * np.float32(col) * s
    for p in L:
        spot(p, 10 * u, (1, .88, .6), 2.2); spot(p, 45 * u, (1, .6, .25), .7); spot(p, 170 * u, (.9, .45, .15), .2)
        t = np.clip((yy - p[1]) / (900 * u), 0, 1)
        beam = np.exp(-((xx - p[0]) / (12 * u + t * 260 * u)) ** 2) * (yy > p[1]) * (1 - t) ** 1.5
        glow += blur(beam.astype(np.float32), 6 * u)[..., None] * np.float32([.9, .55, .25]) * 0.20
    for p in S:
        spot(p, 6 * u, (1, .85, .6), 1.0); spot(p, 26 * u, (1, .6, .3), .3); spot(p, 90 * u, (.9, .45, .2), .08)
    if hz:
        spot(hz, 180 * u, (1, .6, .3), .18); spot((hz[0], hz[1] + 30 * u), 420 * u, (.7, .45, .3), .06)
    a = a + glow
    if hz:
        vp = pool(hz, 380 * u, 260 * u)[..., None]
        a = a * (1 - vp * .18) + vp * np.float32([.30, .24, .20]) * .18
        mist = (np.clip(1 - abs(yy - hz[1] - 90 * u) / (260 * u), 0, 1) ** 2 * .10)[..., None]
        a = a * (1 - mist) + mist * np.float32([.20, .24, .30])
    # bloom
    lum = a @ LUMA
    br = a * np.clip((lum - .62) / .38, 0, 1)[..., None]
    a = a + blur(br, 6 * u) * .35 + blur(br, 22 * u) * .30 + blur(br, 60 * u) * .25
    # dust in the light
    dust = np.zeros((H, W), np.float32)
    for _ in range(int(260 * W * H / (1080 * 1920))):
        x = rng.uniform(0, W); y = rng.uniform(0.08 * H, 0.65 * H)
        lit = 0.15 + sum(np.exp(-((x - p[0]) / (220 * u)) ** 2) for p in L)
        if hz:
            lit += np.exp(-(((x - hz[0]) / (300 * u)) ** 2 + ((y - hz[1]) / (250 * u)) ** 2))
        cv2.circle(dust, (int(x), int(y)), max(1, int(rng.uniform(.6, 2.4) * u)), float(rng.uniform(.2, 1) * min(lit, 1.3)), -1, cv2.LINE_AA)
    dust = blur(dust, 1.1) + blur(dust, 4 * u) * .6
    a = a + dust[..., None] * np.float32([1, .75, .45]) * .35
    # lens: chromatic fringe toward the edges
    r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    s = 1 + 0.0025 * r2
    a[..., 0] = cv2.remap(a[..., 0], W / 2 + (xx - W / 2) * s, H / 2 + (yy - H / 2) * s, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    a[..., 2] = cv2.remap(a[..., 2], W / 2 + (xx - W / 2) / s, H / 2 + (yy - H / 2) / s, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return a, xx, yy, u


def compose(args, fmt, clean):
    W, H = (1080, 1920) if fmt == "story" else (1920, 1080)
    story = fmt == "story"
    rng = np.random.default_rng(11)
    src = cv2.imread(str(args.src))[:, :, ::-1].astype(np.float32) / 255
    a, to, k = frame(src, W, H, args.crop_x if story else 0.5)
    a, xx, yy, u = grade(a, W, H, to, k, args.lights, args.small_lights, args.haze, args.focus, rng, story)
    # vignette and darkening where the type sits
    vig = 1 - 0.70 * (((xx - W * .55) / (W * .85)) ** 2 + ((yy - H * .5) / (H * .62)) ** 2) ** 1.2
    a *= np.clip(vig, .15, 1)[..., None]
    if story:
        dark = np.maximum(np.clip(1 - yy / 620, 0, 1) ** 1.8 * .75, np.clip((yy - 980) / (H - 980), 0, 1) ** 1.1 * .95)
    else:
        left = np.clip(1 - xx / (W * .62), 0, 1) ** 1.4 * .80
        bottom = np.clip((yy - H * .45) / (H * .55), 0, 1) ** 1.3 * .75
        top = np.clip(1 - yy / (H * .30), 0, 1) ** 2 * .45
        dark = np.clip(np.maximum(left * (0.55 + 0.45 * yy / H), np.maximum(bottom, top)), 0, .92)
        if clean:
            dark = top * .6
    a = a * (1 - dark[..., None]) + dark[..., None] * np.float32([.010, .012, .018])
    a = np.clip(a, 0, 1) ** (1 / 1.08)
    a = (a + blur(rng.normal(0, 1, (H, W)).astype(np.float32), .7)[..., None] * .022).clip(0, 1)
    im = Image.fromarray((a * 255 + .5).astype(np.uint8)).convert("RGBA")
    if clean:  # the page header and share image print their own title, so no logo or text
        return im.convert("RGB")

    # logo with soft shadow and a faint red backlight
    logo = Image.open(DOCS / "img" / "logo.webp").convert("RGBA")
    lw = 780 if story else 600
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    lx, ly = ((W - lw) // 2, 262) if story else (84, 64)
    al = np.zeros((H, W), np.float32)
    al[ly:ly + logo.height, lx:lx + lw] = np.asarray(logo)[..., 3] / 255
    b = np.asarray(im).astype(np.float32) / 255
    b[..., :3] *= 1 - blur(al, 22) [..., None] * .68
    b[..., :3] += blur(al, 60)[..., None] * np.float32([.55, .20, .12]) * .22
    im = Image.fromarray((b.clip(0, 1) * 255).astype(np.uint8))
    im.alpha_composite(logo, (lx, ly))

    head = font("saira-condensed-700-latin.woff2", 150)
    kick = font("saira-condensed-600-latin.woff2", 38)
    subf = font("ibm-plex-sans-latin.woff2", 37)
    ctaf = font("saira-condensed-600-latin.woff2", 42)

    def width(d, s, f, tr):
        return sum(d.textlength(c, font=f) for c in s) + tr * (len(s) - 1)

    def put(d, x, y, s, f, fill, tr):
        for c in s:
            d.text((x, y), c, font=f, fill=fill)
            x += d.textlength(c, font=f) + tr

    def layer():
        return Image.new("RGBA", (W, H), (0, 0, 0, 0))

    def at(w, x_left):  # centred on story, left aligned on landscape
        return (W - w) / 2 if story else x_left

    X = 96
    Y = {"kick": 1318, "head": 1352, "sub": 1530, "cta": 1594} if story else {"kick": 640, "head": 674, "sub": 852, "cta": 920}
    if args.kicker:
        L = layer(); d = ImageDraw.Draw(L); w = width(d, args.kicker, kick, 12); x = at(w, X + 110)
        put(d, x, Y["kick"], args.kicker, kick, (236, 236, 240, 255), 12)
        bars = (x - 110, x + w + 30) if story else (X, )
        for sx in bars:
            d.polygon([(sx, Y["kick"] + 25), (sx + 80, Y["kick"] + 25), (sx + 76, Y["kick"] + 29), (sx + 4, Y["kick"] + 29)], fill=RED)
        im.alpha_composite(L)
    # metal headline
    M = Image.new("L", (W, H), 0); dm = ImageDraw.Draw(M)
    w = width(dm, args.title, head, 3); hx = at(w, X - 6)
    put(dm, hx, Y["head"], args.title, head, 255, 3)
    m = np.asarray(M).astype(np.float32) / 255
    ys = np.nonzero(m > .5)[0]
    tt = np.clip((yy - ys.min()) / (ys.max() - ys.min()), 0, 1)
    metal = .97 - .30 * tt + .10 * np.exp(-((tt - .52) / .05) ** 2) - .10 * np.exp(-((tt - .58) / .06) ** 2)
    metal = (metal + cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), sigmaX=12, sigmaY=.6) * .05).clip(0, 1)
    col = np.dstack([metal * .98, metal * .99, metal * 1.03]).clip(0, 1)
    b = np.asarray(im).astype(np.float32) / 255
    b[..., :3] *= 1 - np.roll(blur(m, 9), (8, 0), (0, 1))[..., None] * .75
    b[..., :3] += blur(m, 26)[..., None] * np.float32([.75, .05, .10]) * .30
    edge = np.clip(m - np.roll(m, 3, 0), 0, 1)
    b[..., :3] = b[..., :3] * (1 - m[..., None]) + col * m[..., None] + edge[..., None] * .25
    im = Image.fromarray((b.clip(0, 1) * 255).astype(np.uint8))
    if args.sub:
        L = layer(); d = ImageDraw.Draw(L); w = width(d, args.sub, subf, 1); x = at(w, X)
        put(d, x + 2, Y["sub"] + 2, args.sub, subf, (0, 0, 0, 170), 1)
        im.alpha_composite(L.filter(ImageFilter.GaussianBlur(3)))
        L = layer(); put(ImageDraw.Draw(L), x, Y["sub"], args.sub, subf, (222, 222, 228, 255), 1); im.alpha_composite(L)
    if args.cta:
        d = ImageDraw.Draw(layer()); w = width(d, args.cta, ctaf, 6); x = at(w, X + 44)
        x0, x1, y0, y1, sk = x - 44, x + w + 44, Y["cta"], Y["cta"] + 62, 14
        P = Image.new("L", (W, H), 0); ImageDraw.Draw(P).polygon([(x0 + sk, y0), (x1, y0), (x1 - sk, y1), (x0, y1)], fill=255)
        p = np.asarray(P).astype(np.float32) / 255
        b = np.asarray(im).astype(np.float32) / 255
        b[..., :3] += blur(p, 22)[..., None] * np.float32([.8, .05, .1]) * .45
        gt = np.clip((yy - y0) / (y1 - y0), 0, 1)
        plate = np.dstack([.92 - .25 * gt, .10 - .05 * gt, .20 - .08 * gt]) + np.exp(-((yy - y0 - 2) / 2) ** 2)[..., None] * .25
        b[..., :3] = b[..., :3] * (1 - p[..., None]) + plate * p[..., None]
        im = Image.fromarray((b.clip(0, 1) * 255).astype(np.uint8))
        L = layer(); put(ImageDraw.Draw(L), x, y0 + 4, args.cta, ctaf, (0, 0, 0, 120), 6); im.alpha_composite(L.filter(ImageFilter.GaussianBlur(2)))
        L = layer(); put(ImageDraw.Draw(L), x, y0 + 3, args.cta, ctaf, (255, 255, 255, 255), 6); im.alpha_composite(L)
    return im.convert("RGB")


def pair(s):
    x, y = s.split(",")
    return float(x), float(y)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=pathlib.Path)
    ap.add_argument("--title", required=True)
    ap.add_argument("--kicker", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--cta", default="", help="red button text; keep timing words out of devlog art")
    ap.add_argument("--format", choices=("landscape", "story", "both"), default="landscape")
    ap.add_argument("--crop-x", type=float, default=0.46, help="story crop centre, fraction of source width")
    ap.add_argument("--lights", type=pair, nargs="*", default=[])
    ap.add_argument("--small-lights", type=pair, nargs="*", default=[])
    ap.add_argument("--haze", type=pair, default=None)
    ap.add_argument("--focus", type=pair, default=(0.6, 0.8), help="area kept readable, e.g. the weapon")
    ap.add_argument("--clean", action="store_true", help="also render a version without logo and text (-clean)")
    ap.add_argument("--out", required=True, help="output path without extension")
    args = ap.parse_args()
    fmts = ("landscape", "story") if args.format == "both" else (args.format,)
    for fmt in fmts:
        for clean in ((False, True) if args.clean else (False,)):
            img = compose(args, fmt, clean)
            stem = args.out + ("-story" if fmt == "story" else "") + ("-clean" if clean else "")
            img.save(stem + ".jpg", quality=95, subsampling=0)
            if fmt == "landscape":
                img.resize((1280, 720), Image.LANCZOS).save(stem + ".webp", quality=90, method=6)
                img.resize((640, 360), Image.LANCZOS).save(stem + "-640.webp", quality=85, method=6)
            print("wrote", stem)


if __name__ == "__main__":
    main()
