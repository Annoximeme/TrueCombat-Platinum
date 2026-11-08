#!/usr/bin/env python3
"""Builds the overhead map layouts on maps.html from the original map files.

For every map it reads maps/obj_<name>.bsp (IBSP version 47, as shipped in the
TC:E pak files), draws a top-down plan of the playable level (floors shaded by
height, walls as lines, roofs and foliage left out) and collects the game's own
data: team spawn points, bomb sites, flag positions and the in-game location
names (target_location). It writes:

  docs/img/maps/layout-<name>.webp      the plan image
  tools/website/maplayouts.json         spawns, sites, flags and callouts in image pixels

build.py turns the JSON into the SVG overlay on maps.html, so only rerun this when
a map changes. Needs numpy and Pillow.

  python tools/website/maplayout.py <folder with obj_*.bsp files>
"""
import json
import pathlib
import re
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAPS = ["delta", "northport", "railhouse", "snow", "stadtrand", "village"]
PX = 1400          # long side of the output image
MARGIN = 420       # game units around the playable area
BG = (13, 16, 22)


# ---------------------------------------------------------------- BSP reading
def load(path):
    d = pathlib.Path(path).read_bytes()
    magic, ver = struct.unpack_from("<4si", d, 0)
    if magic != b"IBSP" or ver != 47:
        raise ValueError("%s: not an IBSP v47 map" % path)
    lumps = [struct.unpack_from("<ii", d, 8 + 8 * i) for i in range(17)]
    lump = lambda i: d[lumps[i][0]:lumps[i][0] + lumps[i][1]]
    shaders = [struct.unpack_from("<64sii", lump(1), i * 72) for i in range(len(lump(1)) // 72)]
    shaders = [(n.split(b"\0")[0].decode("latin1"), sf) for n, sf, _ in shaders]
    verts = np.frombuffer(lump(10), dtype=np.dtype([("xyz", "<f4", 3), ("st", "<f4", 2), ("lm", "<f4", 2), ("n", "<f4", 3), ("c", "u1", 4)]))
    surfs = np.frombuffer(lump(13), dtype=np.dtype([
        ("shader", "<i4"), ("fog", "<i4"), ("type", "<i4"), ("fv", "<i4"), ("nv", "<i4"), ("fi", "<i4"), ("ni", "<i4"),
        ("lmi", "<i4"), ("lmxy", "<i4", 4), ("lmo", "<f4", 3), ("lmv", "<f4", 9), ("pw", "<i4"), ("ph", "<i4")]))
    models = np.frombuffer(lump(7), dtype=np.dtype([("mins", "<f4", 3), ("maxs", "<f4", 3), ("fs", "<i4"), ("ns", "<i4"), ("fb", "<i4"), ("nb", "<i4")]))
    ents = [dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', b)) for b in re.findall(r"\{([^{}]*)\}", lump(0).rstrip(b"\0").decode("latin1"))]
    return dict(shaders=shaders, verts=verts, idx=np.frombuffer(lump(11), dtype="<i4"), surfs=surfs, models=models, ents=ents)


SKIP = re.compile(r"common/|sky|caulk|clip|nodraw|trigger|hint|skip|water|fog|decal", re.I)
CLUTTER = re.compile(r"tree|foliage|bush|plant|flant|wire|light|bottle|pebble|bag|grass|leaf|flacon|corona|lamp", re.I)


def triangles(m):
    """World triangles (model 0) without sky, tool brushes, decals and foliage."""
    v, idx, out = m["verts"]["xyz"], m["idx"], []
    world = m["models"][0]
    for s in m["surfs"][world["fs"]:world["fs"] + world["ns"]]:
        name, flags = m["shaders"][s["shader"]]
        if flags & (0x4 | 0x80) or SKIP.search(name) or (name.startswith("models/") and CLUTTER.search(name)):
            continue
        if s["type"] in (1, 3):
            out.append(v[idx[s["fi"]:s["fi"] + s["ni"]] + s["fv"]].reshape(-1, 3, 3))
        elif s["type"] == 2:
            w, h = s["pw"], s["ph"]
            cp = v[s["fv"]:s["fv"] + w * h].reshape(h, w, 3)
            tl = [t for y in range(h - 1) for x in range(w - 1)
                  for t in ([cp[y, x], cp[y, x + 1], cp[y + 1, x + 1]], [cp[y, x], cp[y + 1, x + 1], cp[y + 1, x]])]
            if tl:
                out.append(np.array(tl))
    return np.concatenate(out)


# ---------------------------------------------------------------- drawing
def draw(m, cut, mins, maxs, ss=2):
    T = triangles(m)
    n = np.cross(T[:, 2] - T[:, 0], T[:, 1] - T[:, 0])   # Q3 winding is clockwise
    ln = np.linalg.norm(n, axis=1)
    keep = (ln > 1e-3) & (T[:, :, 2].min(1) <= cut)     # leave out roofs and upper geometry
    T, n = T[keep], n[keep] / ln[keep, None]
    scale = PX * ss / max(maxs - mins)
    size = (int((maxs[0] - mins[0]) * scale) + 1, int((maxs[1] - mins[1]) * scale) + 1)
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img)
    proj = lambda P: [((p[0] - mins[0]) * scale, (maxs[1] - p[1]) * scale) for p in P]
    zt = T[:, :, 2].mean(1)
    floors = np.where(n[:, 2] > 0.35)[0]
    lo, hi = np.percentile(zt[floors], 3), np.percentile(zt[floors], 97)
    for i in floors[np.argsort(T[floors, :, 2].max(1))]:
        k = float(np.clip((zt[i] - lo) / max(1, hi - lo), 0, 1))
        g = int(46 + 64 * k)
        d.polygon(proj(T[i]), fill=(g, g + 5, g + 14))
    for i in np.where(np.abs(n[:, 2]) < 0.25)[0]:
        P = proj(T[i])
        d.line(P + [P[0]], fill=(206, 213, 226), width=ss)
    return img.resize((size[0] // ss, size[1] // ss), Image.LANCZOS)


# ---------------------------------------------------------------- game data
def origin(e):
    return [float(x) for x in e["origin"].split()]


def layout(path):
    m = load(path)
    E, M = m["ents"], m["models"]
    spawns = {"terrorists": [origin(e) for e in E if e.get("classname") == "team_CTF_redspawn"],
              "specops": [origin(e) for e in E if e.get("classname") == "team_CTF_bluespawn"]}
    locs, seen = [], set()
    for e in E:
        if e.get("classname") == "target_location" and e["message"] not in seen:
            seen.add(e["message"])
            locs.append((e["message"], origin(e)))
    sites = []
    for e in E:
        if e.get("classname") == "trigger_objective_info" and (e.get("spawnflags") == "130" or e.get("target", "").startswith("bombsite")):
            mdl = M[int(e["model"][1:])]
            track = e.get("track", "")
            name = re.sub(r"\s*\[\w\]", "", track).strip()
            sites.append((re.search(r"\[(\w)\]", track).group(1), "" if name.lower().startswith("to the bomb") else name,
                          mdl["mins"][:2].astype(float), mdl["maxs"][:2].astype(float)))
    flags = [("terrorists" if "red" in e["classname"] else "specops", origin(e))
             for e in E if e.get("classname") in ("team_CTF_redflag", "team_CTF_blueflag")]
    pts = np.array([p[:2] for t in spawns.values() for p in t] + [o[:2] for _, o in locs] + [o[:2] for _, o in flags]
                   + [s[2] for s in sites] + [s[3] for s in sites])
    mins, maxs = pts.min(0) - MARGIN, pts.max(0) + MARGIN
    cut = float(np.percentile([p[2] for t in spawns.values() for p in t], 90)) + 140
    img = draw(m, cut, mins, maxs)
    W, H = img.size
    px = lambda x, y: [round((x - mins[0]) / (maxs[0] - mins[0]) * W, 1), round((maxs[1] - y) / (maxs[1] - mins[1]) * H, 1)]
    data = {
        "w": W, "h": H,
        "spawns": {t: [px(*p[:2]) for p in ps] for t, ps in spawns.items()},
        "sites": [{"site": s, "name": nm, "a": px(lo[0], hi[1]), "b": px(hi[0], lo[1])} for s, nm, lo, hi in sorted(sites)],
        "flags": [{"team": t, "p": px(*o[:2])} for t, o in flags],
        "callouts": [{"name": nm, "p": px(*o[:2])} for nm, o in locs],
    }
    return img, data


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1])
    out = ROOT / "docs" / "img" / "maps"
    result = {}
    for name in MAPS:
        f = next(iter(sorted(src.glob("*obj_%s.bsp" % name))), None)
        if not f:
            sys.exit("no obj_%s.bsp in %s" % (name, src))
        img, data = layout(f)
        img.save(out / ("layout-%s.webp" % name), quality=82, method=6)
        result[name] = data
        print("layout-%s.webp %dx%d, %d callouts, %d sites" % (name, data["w"], data["h"], len(data["callouts"]), len(data["sites"])))
    (ROOT / "tools" / "website" / "maplayouts.json").write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
