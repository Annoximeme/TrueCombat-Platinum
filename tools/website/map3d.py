#!/usr/bin/env python3
"""Builds the 3D map models for the map pages (docs/js/map3d.js draws them with WebGL).

Reads the same original map files as maplayout.py (maps/obj_<name>.bsp, IBSP v47) and keeps the
world geometry without sky, tool brushes, decals and foliage, coloured with the map's own baked
vertex lighting. Positions are quantised to 16 bits, so a model is about a megabyte.

  python tools/website/map3d.py <folder with obj_*.bsp files>

Writes docs/img/maps/3d-<name>.bin:
  "TCM1", uint32 vertex count, uint32 index count, float32 min[3], float32 size[3],
  uint16 xyz[n*3] (0..65535 across the box), uint8 rgb[n*3], pad to 4, uint32 index[m],
  then uint32 json length and a JSON block with the callouts, spawns, sites and flags in world units.
"""
import json
import pathlib
import struct
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import maplayout as ml  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
MIN_AREA = 6.0      # square game units: drops specks that no camera distance shows


def mesh(m):
    v, c, idx = m["verts"]["xyz"], m["verts"]["c"][:, :3], m["idx"]
    P, C = [], []
    world = m["models"][0]
    for s in m["surfs"][world["fs"]:world["fs"] + world["ns"]]:
        name, flags = m["shaders"][s["shader"]]
        if flags & (0x4 | 0x80) or ml.SKIP.search(name) or (name.startswith("models/") and ml.CLUTTER.search(name)):
            continue
        if s["type"] in (1, 3):
            ii = idx[s["fi"]:s["fi"] + s["ni"]] + s["fv"]
            P.append(v[ii].reshape(-1, 3, 3))
            C.append(c[ii].reshape(-1, 3, 3))
        elif s["type"] == 2:
            w, h = s["pw"], s["ph"]
            grid = np.arange(s["fv"], s["fv"] + w * h).reshape(h, w)
            tris = [t for y in range(h - 1) for x in range(w - 1)
                    for t in ([grid[y, x], grid[y, x + 1], grid[y + 1, x + 1]], [grid[y, x], grid[y + 1, x + 1], grid[y + 1, x]])]
            if tris:
                tris = np.array(tris)
                P.append(v[tris])
                C.append(c[tris])
    P, C = np.concatenate(P), np.concatenate(C).astype(np.float32)
    area = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1) / 2
    edges = np.stack([np.linalg.norm(P[:, i] - P[:, (i + 1) % 3], axis=1) for i in range(3)], 1).max(1)
    # long slivers are terrain skirts and backdrop cards meant to be seen from inside the map only
    sliver = (edges > 1200) & (2 * area / np.maximum(edges, 1) < 48)
    keep = (area > MIN_AREA) & ~sliver
    return P[keep], C[keep]


def build(path):
    m = ml.load(path)
    P, C = mesh(m)
    # bring the play area into the frame: the layout's bounds, extended upwards to everything inside them
    _, data = ml.layout(path)
    E = m["ents"]
    pts = np.array([ml.origin(e) for e in E if e.get("classname") in ("team_CTF_redspawn", "team_CTF_bluespawn", "target_location")])
    lo2, hi2 = pts[:, :2].min(0) - ml.MARGIN, pts[:, :2].max(0) + ml.MARGIN
    # every corner inside the play box (plus a little): backdrop cards and terrain skirts reach far outside it
    pad = 256
    inside = ((P[:, :, 0] > lo2[0] - pad) & (P[:, :, 0] < hi2[0] + pad) & (P[:, :, 1] > lo2[1] - pad) & (P[:, :, 1] < hi2[1] + pad)).all(1)
    P, C = P[inside], C[inside]
    flat = P.reshape(-1, 3)
    mins, maxs = flat.min(0), flat.max(0)
    size = np.maximum(maxs - mins, 1)
    q = np.round((flat - mins) / size * 65535).astype(np.uint16)
    # baked vertex light varies a lot between maps (overbright daylight on Village): bring every map to the same mid grey
    lum = C.reshape(-1, 3).mean(1)
    col = np.clip(C.reshape(-1, 3) * (118.0 / max(1.0, float(np.median(lum)))), 0, 255).astype(np.uint8)
    key = np.concatenate([q.view(np.uint8).reshape(-1, 6), col], axis=1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    vq = uniq[:, :6].copy().view(np.uint16).reshape(-1, 3)
    vc = uniq[:, 6:9]
    index = inv.reshape(-1).astype(np.uint32)
    # game data in world units
    spawns = {"terrorists": [ml.origin(e) for e in E if e.get("classname") == "team_CTF_redspawn"],
              "specops": [ml.origin(e) for e in E if e.get("classname") == "team_CTF_bluespawn"]}
    seen, callouts = set(), []
    for e in E:
        if e.get("classname") == "target_location" and e["message"] not in seen:
            seen.add(e["message"])
            callouts.append({"name": e["message"], "p": ml.origin(e)})
    sites = []
    for e in E:
        if e.get("classname") == "trigger_objective_info" and (e.get("spawnflags") == "130" or e.get("target", "").startswith("bombsite")):
            mdl = m["models"][int(e["model"][1:])]
            import re
            track = e.get("track", "")
            letter = re.search(r"\[(\w)\]", track)
            sites.append({"site": letter.group(1) if letter else "?", "mins": mdl["mins"].tolist(), "maxs": mdl["maxs"].tolist()})
    flags = [{"team": "terrorists" if "red" in e["classname"] else "specops", "p": ml.origin(e)}
             for e in E if e.get("classname") in ("team_CTF_redflag", "team_CTF_blueflag")]
    meta = json.dumps({"callouts": callouts, "spawns": spawns, "sites": sorted(sites, key=lambda s: s["site"]), "flags": flags},
                      separators=(",", ":")).encode()
    head = struct.pack("<4sII3f3f", b"TCM1", len(vq), len(index), *mins.tolist(), *size.tolist())
    body = vq.astype("<u2").tobytes() + vc.tobytes()
    body += b"\0" * (-(len(head) + len(body)) % 4)
    body += index.astype("<u4").tobytes()
    return head + body + struct.pack("<I", len(meta)) + meta, len(vq), len(index) // 3


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1])
    out = ROOT / "docs" / "img" / "maps"
    for name in ml.MAPS:
        f = next(iter(sorted(src.glob("*obj_%s.bsp" % name))), None)
        if not f:
            sys.exit("no obj_%s.bsp in %s" % (name, src))
        blob, nv, nt = build(f)
        (out / ("3d-%s.bin" % name)).write_bytes(blob)
        print("3d-%s.bin %d KB, %d vertices, %d triangles" % (name, len(blob) // 1024, nv, nt))


if __name__ == "__main__":
    main()
