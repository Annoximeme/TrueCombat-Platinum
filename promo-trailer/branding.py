"""Branded trailer pieces for TrueCombat: Platinum.

Renders, at 1920x1080 / 60 fps:
  intro_ident.mp4   Team Terminus presents (4.5 s)
  end_card.mp4      TrueCombat: Platinum logo reveal + call to action (7 s)
  title_card(...)   overlay frames for gameplay text cards (used by the editor)

Usage: python branding.py OUTDIR
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
A = HERE / "assets"
W, H, FPS = 1920, 1080, 60
RED = (200, 16, 46)

LOGO = Image.open(A / "truecombat-platinum-logo.png").convert("RGBA")
EMBLEM = Image.open(A / "team-terminus-emblem.png").convert("RGBA")


def font(size, plex=False):
    return ImageFont.truetype(str(A / ("ibm-plex-sans-latin.ttf" if plex else "saira-condensed-600-latin.ttf")), size)


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = min(max(t, 0.0), 1.0)
    return 3 * t * t - 2 * t * t * t


def ramp(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


# ---------- background: deep black, soft vignette, slow drifting dust, film grain
_rng = np.random.default_rng(7)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_vig = 1.0 - 0.75 * (((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.70)) ** 2)
_vig = np.clip(_vig, 0.0, 1.0)
_DUST = _rng.random((140, 4)).astype(np.float32)  # x, y, size, speed


def background(t, glow=0.0):
    base = 9 + 14 * _vig
    img = np.stack([base * 1.02, base, base * 1.06], axis=-1)
    if glow > 0:  # faint red light behind the centre
        g = np.exp(-(((_xx - W / 2) / 520) ** 2 + ((_yy - H / 2) / 300) ** 2)) * glow
        img[..., 0] += 70 * g
        img[..., 1] += 8 * g
        img[..., 2] += 12 * g
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    for x, y, s, v in _DUST:
        px = (x * W + t * 18 * (0.3 + v)) % W
        py = (y * H - t * 9 * (0.3 + v)) % H
        r = 0.6 + s * 1.8
        a = int(40 + 70 * s)
        d.ellipse((px - r, py - r, px + r, py + r), fill=(200, 200, 210, a))
    return im


def grain(im, amount=7):
    a = np.asarray(im).astype(np.int16)
    n = _rng.normal(0, amount, (H, W, 1)).astype(np.int16)
    return Image.fromarray(np.clip(a + n, 0, 255).astype(np.uint8))


def scaled(src, width, scale=1.0):
    w = max(1, int(width * scale))
    h = max(1, int(src.height * w / src.width))
    return src.resize((w, h), Image.LANCZOS)


def sweep(layer, pos, width=0.10, strength=0.85, angle=0.35):
    """Add a diagonal light band across a layer's opaque pixels. pos 0..1 travels left to right."""
    arr = np.asarray(layer).astype(np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx + yy * angle) / (w + h * angle)
    band = np.exp(-((u - (pos * 1.4 - 0.2)) / width) ** 2) * strength
    alpha = arr[..., 3:4] / 255.0
    arr[..., :3] = np.clip(arr[..., :3] + 255 * band[..., None] * alpha, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def paste_center(bg, layer, dy=0, opacity=1.0):
    if opacity < 1.0:
        a = np.asarray(layer).copy()
        a[..., 3] = (a[..., 3].astype(np.float32) * opacity).astype(np.uint8)
        layer = Image.fromarray(a, "RGBA")
    bg.paste(layer, ((W - layer.width) // 2, (H - layer.height) // 2 + dy), layer)


def layer():
    """Transparent RGBA layer + drawer. Pillow ignores fill alpha for text drawn on RGB images,
    so all text goes on a layer that is alpha-composited onto the frame."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return lay, ImageDraw.Draw(lay)


def comp(im, lay):
    return Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB")


def spaced_text(draw, cx, y, text, fnt, fill, spacing):
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = cx - total / 2
    for c, cw in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill)
        x += cw + spacing


def flare(im, x, y, size, alpha):
    if alpha <= 0:
        return im
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fl)
    for r, a in ((size, 60), (size * 0.45, 120), (size * 0.15, 255)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(a * alpha)))
    d.line((x - size * 3.2, y, x + size * 3.2, y), fill=(255, 235, 235, int(170 * alpha)), width=2)
    fl = fl.filter(ImageFilter.GaussianBlur(size * 0.12))
    return Image.alpha_composite(im.convert("RGBA"), fl).convert("RGB")


# ---------- pieces
def intro_frame(i):
    t = i / FPS
    dur = 4.5
    im = background(t, glow=0.55 * ease_in_out(ramp(t, 0.2, 1.6)))
    s = 1.06 - 0.06 * ease_out(ramp(t, 0.0, 2.2))
    em = scaled(EMBLEM, 470, s)
    em = sweep(em, ramp(t, 1.0, 2.3))
    op = ease_out(ramp(t, 0.15, 1.1))
    paste_center(im, em, dy=-70, opacity=op)
    lay, d = layer()
    a = int(255 * ease_out(ramp(t, 1.5, 2.3)))
    spaced_text(d, W / 2, H / 2 + 205, "PRESENTS", font(34), (215, 215, 220, a), 14)
    im = comp(im, lay)
    im = flare(im, W / 2 + 175, H / 2 - 210, 70, math.sin(math.pi * ramp(t, 1.55, 2.15)) * 0.9)
    fade = 1 - ease_in_out(ramp(t, dur - 0.7, dur))
    im = Image.fromarray((np.asarray(im).astype(np.float32) * fade).astype(np.uint8))
    return grain(im, 5)


def end_frame(i):
    t = i / FPS
    dur = 7.0
    im = background(t, glow=0.75)
    # impact: logo arrives fast from 1.25x with a white flash and a short shake
    k = ease_out(ramp(t, 0.0, 0.32))
    s = 1.25 - 0.25 * k
    lg = scaled(LOGO, 1080, s)
    lg = sweep(lg, ramp(t, 0.9, 2.1), width=0.08)
    shake = 0
    if 0.30 < t < 0.55:
        shake = int(10 * math.sin(t * 90) * (0.55 - t) / 0.25)
    blur = max(0.0, 6 * (1 - k))
    if blur > 0.3:
        lg = lg.filter(ImageFilter.GaussianBlur(blur))
    paste_center(im, lg, dy=-95 + shake, opacity=ease_out(ramp(t, 0.0, 0.12)))
    flash = max(0.0, 1 - abs(t - 0.32) / 0.12) * 0.55
    if flash > 0:
        im = Image.fromarray(np.clip(np.asarray(im).astype(np.float32) + 255 * flash, 0, 255).astype(np.uint8))
    im = flare(im, W / 2 - 420, H / 2 - 160, 60, math.sin(math.pi * ramp(t, 1.0, 1.7)) * 0.8)
    lay, d = layer()
    a1 = int(255 * ease_out(ramp(t, 1.9, 2.6)))
    a2 = int(255 * ease_out(ramp(t, 2.4, 3.1)))
    a3 = int(255 * ease_out(ramp(t, 3.0, 3.7)))
    spaced_text(d, W / 2, H / 2 + 210, "FREE ON WINDOWS", font(44), (235, 235, 238, a1), 10)
    rw = int(150 * ease_out(ramp(t, 1.9, 2.6)))
    cy = H / 2 + 237
    d.rectangle((W / 2 - 300 - rw, cy, W / 2 - 300, cy + 3), fill=RED + (a1,))
    d.rectangle((W / 2 + 300, cy, W / 2 + 300 + rw, cy + 3), fill=RED + (a1,))
    spaced_text(d, W / 2, H / 2 + 277, "TRUECOMBAT.EU", font(56), (255, 255, 255, a2), 8)
    im = comp(im, lay)
    # studio mark + legal line
    em = scaled(EMBLEM, 78)
    paste_center(im, em, dy=H // 2 - 128, opacity=a3 / 255)
    lay, d = layer()
    legal = ("A fan project by Team Terminus. TrueCombat: Elite was created by Team Terminator. "
             "Not affiliated with or endorsed by Team Terminator, Splash Damage, id Software or Activision.")
    f = font(17, plex=True)
    lw = d.textlength(legal, font=f)
    d.text(((W - lw) / 2, H - 42), legal, font=f, fill=(150, 150, 155, int(a3 * 0.8)))
    music = "Music: 'Venom' by Scott Buckley, released under CC-BY 4.0. www.scottbuckley.com.au"
    mw = d.textlength(music, font=f)
    d.text(((W - mw) / 2, H - 68), music, font=f, fill=(150, 150, 155, int(a3 * 0.8)))
    im = comp(im, lay)
    fade = 1 - ease_in_out(ramp(t, dur - 0.6, dur))
    im = Image.fromarray((np.asarray(im).astype(np.float32) * fade).astype(np.uint8))
    return grain(im, 5)


def title_card(frame_rgb, t, text, sub=None, dur=2.2):
    """Overlay a text card on a gameplay frame (PIL RGB, 1920x1080). t = seconds into the card."""
    a_in = ease_out(ramp(t, 0.0, 0.35))
    a_out = 1 - ease_in_out(ramp(t, dur - 0.35, dur))
    a = a_in * a_out
    if a <= 0:
        return frame_rgb
    arr = np.asarray(frame_rgb).astype(np.float32)
    band = np.exp(-((_yy - H * 0.5) / 210) ** 2)[..., None]
    arr *= 1 - 0.6 * a * band
    im = Image.fromarray(arr.astype(np.uint8))
    drift = 18 * (1 - a_in)
    al = int(255 * a)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    spaced_text(sd, W / 2 + drift, H / 2 - 50, text, font(88), (0, 0, 0, int(200 * a)), 12)
    if sub:
        spaced_text(sd, W / 2, H / 2 + 86, sub, font(32), (0, 0, 0, int(200 * a)), 6)
    im = Image.alpha_composite(im.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(10))).convert("RGB")
    lay, d = layer()
    spaced_text(d, W / 2 + drift, H / 2 - 52, text, font(88), (255, 255, 255, al), 12)
    rw = int(110 * a_in)
    y = H / 2 + 62
    d.rectangle((W / 2 - rw, y, W / 2 + rw, y + 4), fill=RED + (al,))
    if sub:
        spaced_text(d, W / 2, y + 22, sub, font(32), (220, 220, 225, int(al * 0.9)), 6)
    return comp(im, lay)


def render(path, frame_fn, frames):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "14",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(frames):
        p.stdin.write(frame_fn(i).convert("RGB").tobytes())
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "out")
    out.mkdir(parents=True, exist_ok=True)
    render(out / "intro_ident.mp4", intro_frame, int(4.5 * FPS))
    render(out / "end_card.mp4", end_frame, int(7.0 * FPS))
    for name, fn, t in (("intro_still.jpg", intro_frame, 2.6), ("end_still.jpg", end_frame, 4.5)):
        fn(int(t * FPS)).save(out / name, quality=92)
    print("done", out)
