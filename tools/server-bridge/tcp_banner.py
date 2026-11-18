#!/usr/bin/env python3
"""Live server banners for forums, Discord and README files (PNG, standard library only).

  GET /banner/<which>-<size>.png
      which  all          every public server: players online and servers up
             official1    Official #1, official2 Official #2 (matched on the server name)
      size   wide         600 x 120
             small        468 x 60

The fixed parts (map art, wordmark, glyph atlases) are built once by
tools/website/banner_assets.py into the banner/ folder next to this file; this module only
decodes them, draws the live text and encodes the result. A banner is rebuilt only when what
it shows changes, so a busy forum thread costs one render per server refresh at most.
Server addresses and ports are never drawn.
"""
import json
import pathlib
import re
import struct
import threading
import zlib

HERE = pathlib.Path(__file__).resolve().parent / "banner"
SIZES = {"wide": (600, 120), "small": (468, 60)}
MAPS = {"obj_delta": "Delta", "obj_northport": "Northport", "obj_railhouse": "Railhouse", "obj_snow": "Snow",
        "obj_stadtrand": "Stadtrand", "obj_village": "Village"}
WHITE, MUTED, AMBER, GREEN, GREY, RED = (232, 234, 239), (154, 163, 179), (231, 167, 60), (79, 191, 122), (90, 102, 122), (239, 80, 80)
NAME = re.compile(r"^(?P<key>all|official[12])-(?P<size>wide|small)\.png$")


# ------------------------------------------------------------------ PNG in and out
def png_read(path):
    """8-bit grey or RGB, non-interlaced PNG (what banner_assets.py writes) -> (w, h, channels, bytearray)."""
    d = pathlib.Path(path).read_bytes()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    pos, idat, w = 8, [], None
    while pos < len(d):
        n, kind = struct.unpack_from(">I4s", d, pos)
        body = d[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", body)
            if depth != 8 or ctype not in (0, 2) or inter:
                raise ValueError("unsupported PNG layout: %s" % path)
            ch = 1 if ctype == 0 else 3
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + n
    raw = zlib.decompress(b"".join(idat))
    stride = w * ch
    out = bytearray(stride * h)
    prev = bytearray(stride)
    i = 0
    for y in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if f == 1:
            for x in range(ch, stride):
                line[x] = (line[x] + line[x - ch]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                b, c = prev[x], (prev[x - ch] if x >= ch else 0)
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, ch, out


def png_write(w, h, rgb):
    raw = b"".join(b"\x00" + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


# ------------------------------------------------------------------ drawing
class Canvas:
    def __init__(self, w, h, rgb):
        self.w, self.h, self.px = w, h, bytearray(rgb)

    def rect(self, x0, y0, x1, y1, col, alpha=1.0):
        x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(self.w, int(x1)), min(self.h, int(y1))
        for y in range(y0, y1):
            for x in range(x0, x1):
                i = (y * self.w + x) * 3
                for k in range(3):
                    self.px[i + k] = int(self.px[i + k] * (1 - alpha) + col[k] * alpha)

    def dot(self, cx, cy, r, col):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if 0 <= x < self.w and 0 <= y < self.h:
                    d = ((x + .5 - cx) ** 2 + (y + .5 - cy) ** 2) ** .5
                    a = max(0.0, min(1.0, r + .5 - d))
                    if a:
                        i = (y * self.w + x) * 3
                        for k in range(3):
                            self.px[i + k] = int(self.px[i + k] * (1 - a) + col[k] * a)


class Fonts:
    def __init__(self):
        self.meta = json.loads((HERE / "fonts.json").read_text(encoding="utf-8"))
        self.atlas = {s: png_read(HERE / ("font-%s.png" % s)) for s in self.meta}

    def width(self, style, text, track=0.0):
        g = self.meta[style]["g"]
        return sum(g[c][2] if c in g else g[" "][2] for c in text) + track * max(0, len(text) - 1)

    def fit(self, style, text, room, track=0.0):
        """text, shortened with an ellipsis until it fits in room pixels."""
        if self.width(style, text, track) <= room:
            return text
        while text and self.width(style, text + "…", track) > room:
            text = text[:-1]
        return text.rstrip() + "…"

    def draw(self, cv, style, x, baseline, text, col, track=0.0, align="left"):
        m, (aw, ah, _, ap) = self.meta[style], self.atlas[style]
        if align == "right":
            x -= self.width(style, text, track)
        top = baseline - m["asc"]
        for c in text:
            gl = m["g"].get(c) or m["g"][" "]
            ax, gw, adv, left = gl
            gx = int(round(x + left))
            for yy in range(ah):
                py = top + yy
                if not 0 <= py < cv.h:
                    continue
                row = yy * aw
                for xx in range(gw):
                    a = ap[row + ax + xx]
                    px = gx + xx
                    if a and 0 <= px < cv.w:
                        i = (py * cv.w + px) * 3
                        f = a / 255.0
                        for k in range(3):
                            cv.px[i + k] = int(cv.px[i + k] * (1 - f) + col[k] * f)
            x += adv + track


# ------------------------------------------------------------------ banners
def short_name(name):
    return re.sub(r"^TrueCombat:\s*Platinum\s*\|\s*", "", name or "", flags=re.I).strip() or "TrueCombat: Platinum"


def pick(servers, key):
    """The server a banner shows: official #1 or #2 by name (verified first), or None."""
    n = key[-1]
    rx = re.compile(r"official\s*#\s*%s\b" % n, re.I)
    found = [s for s in servers if rx.search(s.get("name", ""))]
    found.sort(key=lambda s: (not s.get("verified"), -(s.get("players") or 0)))
    return found[0] if found else None


def view(servers, key):
    """What a banner says, as plain values (also the cache key)."""
    if key == "all":
        up = len(servers)
        p = sum(s.get("players") or 0 for s in servers)
        busiest = max(servers, key=lambda s: s.get("players") or 0)["map"] if servers else ""
        return ("all", "TrueCombat: Platinum", "%d server%s online" % (up, "" if up == 1 else "s") if up else "Servers offline",
                str(p), "PLAYING NOW", up > 0, busiest, 0, 0)
    s = pick(servers, key)
    label = "Official #%s" % key[-1]
    if not s:
        return (key, label, "Offline right now", "", "OFFLINE", False, "", 0, 0)
    title = short_name(s.get("name"))
    if s.get("ranked") is not None:
        title += " · Ranked" if s.get("ranked") else " · Unranked"
    m = s.get("map", "")
    sub = " · ".join(x for x in (MAPS.get(m.lower(), re.sub(r"^obj_", "", m).capitalize()), s.get("mode", "")) if x)
    p, mx = s.get("players") or 0, s.get("maxPlayers") or 0
    return (key, title, sub, "%d/%d" % (p, mx) if mx else str(p), "PLAYERS", True, m, p, mx)


class Banners:
    def __init__(self):
        self.fonts = Fonts()
        self.bg, self.cache, self.lock = {}, {}, threading.Lock()

    def background(self, size, m):
        name = m.lower().replace("obj_", "") if m else "default"
        k = (size, name)
        if k not in self.bg:
            f = HERE / ("bg-%s-%s.png" % k)
            if not f.exists():
                f = HERE / ("bg-%s-default.png" % size)
            self.bg[k] = png_read(f)
        return self.bg[k]

    def render(self, size, v):
        _, title, sub, big, label, online, m, p, mx = v
        w, h, _, rgb = self.background(size, m)
        cv, F = Canvas(w, h, rgb), self.fonts
        st = lambda s: "%s-%s" % (size, s)
        if size == "wide":
            big_x = w - 22
            room = big_x - F.width(st("big"), big) - 60
            F.draw(cv, st("big"), big_x, 74, big, WHITE if online else MUTED, align="right")
            F.draw(cv, st("label"), big_x, 94, label, AMBER if online else MUTED, track=1.6, align="right")
            if mx:
                bar_w = 120
                cv.rect(big_x - bar_w, 101, big_x, 104, (38, 46, 59))
                cv.rect(big_x - bar_w, 101, big_x - bar_w + bar_w * min(1.0, p / float(mx)), 104, RED)
            cv.dot(24, 62, 4.5, GREEN if online else GREY)
            F.draw(cv, st("title"), 36, 71, F.fit(st("title"), title, room), WHITE)
            F.draw(cv, st("sub"), 36, 92, F.fit(st("sub"), sub, room), MUTED)
        else:
            big_x = w - 14
            right = F.width(st("big"), big)
            room = big_x - max(right, 130) - 46
            F.draw(cv, st("big"), big_x, 32, big, WHITE if online else MUTED, align="right")
            cv.dot(16, 22, 3.5, GREEN if online else GREY)
            F.draw(cv, st("title"), 26, 28, F.fit(st("title"), title, room), WHITE)
            F.draw(cv, st("sub"), 26, 47, F.fit(st("sub"), sub, room), MUTED)
        return png_write(w, h, cv.px)

    def get(self, servers_doc, filename):
        """(png bytes) for /banner/<filename>, or None when the name is not a banner."""
        m = NAME.match(filename or "")
        if not m:
            return None
        v = view((servers_doc or {}).get("servers") or [], m.group("key"))
        k = (m.group("size"), v)
        with self.lock:
            hit = self.cache.get((m.group("key"), m.group("size")))
            if hit and hit[0] == k:
                return hit[1]
        png = self.render(m.group("size"), v)
        with self.lock:
            self.cache[(m.group("key"), m.group("size"))] = (k, png)
        return png


if __name__ == "__main__":       # writes sample banners to the current folder
    import sys
    demo = {"servers": [
        {"name": "TrueCombat: Platinum | Official #1 (EU)", "map": "obj_railhouse", "mode": "Team Elimination", "players": 9, "maxPlayers": 16, "ranked": True, "verified": True},
        {"name": "TrueCombat: Platinum | Official #2 (EU)", "map": "obj_village", "mode": "Bomb", "players": 4, "maxPlayers": 20, "ranked": False, "verified": True},
        {"name": "Community night", "map": "obj_snow", "mode": "Team Deathmatch", "players": 3, "maxPlayers": 12}]}
    b = Banners()
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for key in ("all", "official1", "official2"):
        for size in SIZES:
            (out / ("%s-%s.png" % (key, size))).write_bytes(b.get(demo, "%s-%s.png" % (key, size)))
    (out / "official1-offline-wide.png").write_bytes(b.render("wide", view([], "official1")))
