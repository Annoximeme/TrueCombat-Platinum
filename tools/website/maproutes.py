#!/usr/bin/env python3
"""Route timings for the map pages: how long each team takes to reach the bomb sites
and flags, the path it runs, and who gets where first.

It reads the same maps/obj_<name>.bsp files as maplayout.py and builds the level's real
collision from the map brushes (solid and player clip, plus static and breakable brush
models; doors count as open). Every spot where a player can stand becomes a node, with a
step to each neighbour that a player can walk, step up (18 units) or drop down (up to
200 units). Ladders and jumps are left out, so the times are for plain running.

Times assume a fresh spawn: a full stamina bar of sprint (13 s at 238 units/s with a rifle),
then running at 163 units/s, the values on guide.html.

It writes
  tools/website/maproutes.json              per map: routes (polylines in layout pixels) with times
  docs/img/maps/first-<name>.webp           the "who gets there first" overlay for the layout

and needs numpy, scipy and Pillow:

  python tools/website/maproutes.py <folder with obj_*.bsp files> [map ...]
"""
import json
import pathlib
import struct
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import maplayout  # noqa: E402

ROOT = maplayout.ROOT
C = 8                                   # grid cell, game units (x, y and z)
MINS, MAXS, MAXS_CROUCH = (-18, -18, -24), (18, 18, 48), (18, 18, 16)
STEP, DROP = 18, 200
SPRINT, RUN, CROUCH, STAMINA = 238.0, 163.0, 68.0, 13.0
CONTACT = 1.0                           # seconds: both teams arrive within this of each other
BLOCKING = ("func_static", "func_explosive", "func_plat", "func_invisible_user", "func_constructible")
TERROR, SPEC = (232, 74, 60), (74, 152, 236)   # team colours on the layout (style.css .lo-spawn)


def run_time(dist):
    """Seconds to cover dist units from a fresh spawn: sprint while stamina lasts, then run."""
    full = SPRINT * STAMINA
    return dist / SPRINT if dist <= full else STAMINA + (dist - full) / RUN


def brushes(path, m):
    """Collision brushes as (normals, dists) arrays: the world plus static and breakable brush models."""
    d = pathlib.Path(path).read_bytes()
    lumps = [struct.unpack_from("<ii", d, 8 + 8 * i) for i in range(17)]
    lump = lambda i: d[lumps[i][0]:lumps[i][0] + lumps[i][1]]
    contents = [struct.unpack_from("<64sii", lump(1), i * 72)[2] for i in range(len(lump(1)) // 72)]
    planes = np.frombuffer(lump(2), dtype="<f4").reshape(-1, 4)
    sides = np.frombuffer(lump(9), dtype="<i4").reshape(-1, 2)
    br = np.frombuffer(lump(8), dtype="<i4").reshape(-1, 3)
    models = [0] + [int(e["model"][1:]) for e in m["ents"]
                    if e.get("classname") in BLOCKING and e.get("model", "").startswith("*")]
    out = []
    for mi in models:
        mod = m["models"][mi]
        for b in br[mod["fb"]:mod["fb"] + mod["nb"]]:
            if not contents[b[2]] & (1 | 0x10000):        # CONTENTS_SOLID | CONTENTS_PLAYERCLIP
                continue
            p = planes[sides[b[0]:b[0] + b[1], 0]]
            out.append((p[:, :3].astype(np.float64), p[:, 3].astype(np.float64)))
    return out


def blocked_grid(brs, lo, shape, box_max):
    """True where a player origin at the cell centre would touch a brush (Minkowski-expanded planes)."""
    grid = np.zeros(shape, dtype=bool)
    bmin, bmax = np.array(MINS, float), np.array(box_max, float)
    for n, dist in brs:
        off = np.where(n > 0, n * bmin, n * bmax).sum(1)      # nearest point of the player box along each normal
        de = dist - off
        # bounds from the axial planes, which every compiled brush carries
        lo_b, hi_b = np.full(3, -1e9), np.full(3, 1e9)
        for k in range(3):
            pos = np.isclose(n[:, k], 1) & np.isclose(np.abs(n).sum(1), 1)
            neg = np.isclose(n[:, k], -1) & np.isclose(np.abs(n).sum(1), 1)
            if pos.any():
                hi_b[k] = de[pos].min()
            if neg.any():
                lo_b[k] = -de[neg].max()
        i0 = np.maximum(np.ceil((lo_b - lo) / C - .5).astype(int), 0)
        i1 = np.minimum(np.floor((hi_b - lo) / C - .5).astype(int) + 1, shape)
        if (i1 <= i0).any():
            continue
        ax = [lo[k] + (np.arange(i0[k], i1[k]) + .5) * C for k in range(3)]
        X, Y, Z = np.meshgrid(*ax, indexing="ij")
        P = np.stack([X, Y, Z], -1)
        inside = np.all(P @ n.T < de - 0.01, axis=-1)
        grid[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]] |= inside
    return grid


def build(path):
    m = maplayout.load(path)
    E, M = m["ents"], m["models"]
    o = maplayout.origin
    spawns = {"terrorists": [o(e) for e in E if e.get("classname") == "team_CTF_redspawn"],
              "specops": [o(e) for e in E if e.get("classname") == "team_CTF_bluespawn"]}
    locs = [o(e) for e in E if e.get("classname") == "target_location"]
    sites = []
    for e in E:
        if e.get("classname") == "trigger_objective_info" and (e.get("spawnflags") == "130" or e.get("target", "").startswith("bombsite")):
            mdl = M[int(e["model"][1:])]
            import re
            sites.append((re.search(r"\[(\w)\]", e.get("track", "")).group(1), mdl["mins"].astype(float), mdl["maxs"].astype(float)))
    sites.sort(key=lambda s: s[0])
    flags = [("terrorists" if "red" in e["classname"] else "specops", o(e))
             for e in E if e.get("classname") in ("team_CTF_redflag", "team_CTF_blueflag")]
    # the same frame as maplayout.layout(), so pixels line up with the layout image
    pts = np.array([p[:2] for t in spawns.values() for p in t] + [p[:2] for p in locs] + [f[1][:2] for f in flags]
                   + [s[1][:2] for s in sites] + [s[2][:2] for s in sites])
    fmin, fmax = pts.min(0) - maplayout.MARGIN, pts.max(0) + maplayout.MARGIN
    world = M[0]
    lo = np.array([max(fmin[0], world["mins"][0]), max(fmin[1], world["mins"][1]), world["mins"][2]], float)
    hi = np.array([min(fmax[0], world["maxs"][0]), min(fmax[1], world["maxs"][1]), world["maxs"][2]], float)
    shape = tuple(int(x) for x in np.ceil((hi - lo) / C))
    brs = brushes(path, m)
    stand_blk = blocked_grid(brs, lo, shape, MAXS)
    crouch_blk = blocked_grid(brs, lo, shape, MAXS_CROUCH)
    free = ~crouch_blk
    S = np.zeros(shape, bool)
    S[:, :, 1:] = free[:, :, 1:] & crouch_blk[:, :, :-1]      # free here, the box would touch ground one cell lower
    nodes = np.argwhere(S)
    NX, NY, NZ = shape
    flat = lambda x, y, z: (x * NY + y) * NZ + z
    index = np.full(NX * NY * NZ, -1, np.int64)
    index[flat(*nodes.T)] = np.arange(len(nodes))
    slow = stand_blk[tuple(nodes.T)]                            # crouch-only spots
    rows, cols, wts = [], [], []
    up, down = STEP // C, DROP // C
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        x2, y2 = nodes[:, 0] + dx, nodes[:, 1] + dy
        ok = (x2 >= 0) & (x2 < NX) & (y2 >= 0) & (y2 < NY)
        src = np.where(ok)[0]
        x2, y2, z = x2[ok], y2[ok], nodes[ok, 2]
        found = np.full(len(src), -1, np.int64)
        for k in range(up, -down - 1, -1):                      # highest landing first
            z2 = z + k
            inb = (z2 >= 0) & (z2 < NZ) & (found < 0)
            if not inb.any():
                continue
            ii = np.where(inb)[0]
            tgt = index[flat(x2[ii], y2[ii], z2[ii])]
            # stepping up: room to rise on the spot; dropping: room to walk out at the current height
            if k > 0:
                clear = free[nodes[src[ii], 0], nodes[src[ii], 1], np.minimum(z2[ii], NZ - 1)]
            else:
                clear = free[x2[ii], y2[ii], z[ii]]
            if dx and dy:                                       # no corner cutting through walls
                clear &= free[nodes[src[ii], 0] + dx, nodes[src[ii], 1], z[ii]] & free[nodes[src[ii], 0], nodes[src[ii], 1] + dy, z[ii]]
            hit = (tgt >= 0) & clear
            found[ii[hit]] = tgt[hit]
        good = found >= 0
        a, b = src[good], found[good]
        dist = C * np.hypot(dx, dy) * np.where(slow[a] | slow[b], RUN / CROUCH, 1.0)
        rows.append(a), cols.append(b), wts.append(dist)
    G = csr_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(len(nodes),) * 2)
    cell = lambda p: np.floor((np.asarray(p, float) - lo) / C).astype(int)

    def snap(p, below=12):
        """The node a player standing at p (an origin or a point on the floor) occupies."""
        x, y, z = cell(p)
        best, bd = -1, 1e9
        for ddx in range(-3, 4):
            for ddy in range(-3, 4):
                for dz in range(-below, 6):
                    xx, yy, zz = x + ddx, y + ddy, z + dz
                    if 0 <= xx < NX and 0 <= yy < NY and 0 <= zz < NZ and index[flat(xx, yy, zz)] >= 0:
                        dd = ddx * ddx + ddy * ddy + .5 * dz * dz
                        if dd < bd:
                            best, bd = index[flat(xx, yy, zz)], dd
        return best

    team_src = {t: sorted({s for s in (snap(p) for p in ps) if s >= 0}) for t, ps in spawns.items()}
    field = {}
    for t, srcs in team_src.items():
        dist, pred, _ = dijkstra(G, indices=srcs, min_only=True, return_predecessors=True)
        field[t] = (dist, pred)
    return dict(m=m, nodes=nodes, lo=lo, field=field, sites=sites, flags=flags, fmin=fmin, fmax=fmax,
                index=index, flat=flat, shape=shape, snap=snap)


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = np.array(pts[0]), np.array(pts[-1])
    ab = b - a
    L = np.hypot(*ab) or 1e-9
    d = [abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / L for p in pts[1:-1]]
    i = int(np.argmax(d)) + 1
    if d[i - 1] > eps:
        return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]


def routes_for(name, R, layout):
    W, H = layout["w"], layout["h"]
    fmin, fmax, lo, nodes = R["fmin"], R["fmax"], R["lo"], R["nodes"]
    px = lambda x, y: [round((x - fmin[0]) / (fmax[0] - fmin[0]) * W, 1), round((fmax[1] - y) / (fmax[1] - fmin[1]) * H, 1)]
    world = lambda i: lo + (nodes[i] + .5) * C

    def path(team, target):
        dist, pred = R["field"][team]
        if not np.isfinite(dist[target]):
            return None
        seq, i = [], target
        while i >= 0:
            seq.append(i)
            i = pred[i]
        seq.reverse()
        pts = [px(*world(i)[:2]) for i in seq]
        return {"t": round(run_time(dist[target]), 1), "d": int(dist[target]), "p": rdp(pts, max(W, H) / 400)}

    out = {"sites": [], "flags": []}
    for letter, mn, mx in R["sites"]:
        inside = np.all((lo + (nodes + .5) * C >= mn - 24) & (lo + (nodes + .5) * C <= mx + 24), axis=1)
        idx = np.where(inside)[0]
        row = {"site": letter}
        for t in ("terrorists", "specops"):
            dist = R["field"][t][0]
            if len(idx) and np.isfinite(dist[idx]).any():
                row[t] = path(t, idx[np.nanargmin(np.where(np.isfinite(dist[idx]), dist[idx], np.inf))])
        out["sites"].append(row)
    for team, p in R["flags"]:
        enemy = "specops" if team == "terrorists" else "terrorists"
        tgt = R["snap"](p, below=20)
        if tgt >= 0:
            out["flags"].append({"flag": team, "runner": enemy, "route": path(enemy, tgt),
                                 "home": path(team, tgt)})
    return out


def first_overlay(R, layout):
    """RGBA image at layout size: team colour where that team arrives first, white where they meet."""
    W, H = layout["w"], layout["h"]
    fmin, fmax, lo, nodes = R["fmin"], R["fmax"], R["lo"], R["nodes"]
    tT = np.vectorize(run_time)(R["field"]["terrorists"][0])
    tS = np.vectorize(run_time)(R["field"]["specops"][0])
    ok = np.isfinite(tT) & np.isfinite(tS)
    wz = lo[2] + (nodes[:, 2] + .5) * C
    # one value per column: the lowest reachable floor (the layout shows floors, roofs are cut away)
    order = np.lexsort((wz, nodes[:, 1], nodes[:, 0]))
    order = order[ok[order]]
    key = nodes[order, 0] * R["shape"][1] + nodes[order, 1]
    _, first = np.unique(key, return_index=True)
    pick = order[first]
    gx, gy = nodes[pick, 0], nodes[pick, 1]
    diff = (tT[pick] - tS[pick])                                # < 0: terrorists first
    big = np.zeros((R["shape"][1], R["shape"][0], 4), np.float32)
    col_t, col_s = np.array(TERROR, np.float32), np.array(SPEC, np.float32)
    k = np.clip(np.abs(diff) / 6.0, 0, 1)[:, None]
    base = np.where((diff < 0)[:, None], col_t, col_s)
    rgb = base * (0.55 + 0.45 * k) + 255 * (1 - k) * 0.25
    alpha = 70 + 70 * k[:, 0]
    meet = np.abs(diff) <= CONTACT
    rgb[meet] = (255, 236, 190)
    alpha[meet] = 210
    big[gy, gx, :3] = rgb
    big[gy, gx, 3] = alpha
    big = big[::-1]                                             # image y grows southwards
    img = Image.fromarray(big.astype(np.uint8), "RGBA")
    # place the grid (world lo..) into the layout frame (fmin..fmax)
    sx = float(W / (fmax[0] - fmin[0]) * C)
    sy = float(H / (fmax[1] - fmin[1]) * C)
    img = img.resize((max(1, int(round(img.width * sx))), max(1, int(round(img.height * sy)))), Image.NEAREST)
    img = img.filter(ImageFilter.GaussianBlur(sx * .6))
    top = R["lo"][1] + R["shape"][1] * C                        # world y of the grid's top edge
    ox = int(round((lo[0] - fmin[0]) / (fmax[0] - fmin[0]) * W))
    oy = int(round((fmax[1] - top) / (fmax[1] - fmin[1]) * H))
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(img, (max(0, ox), max(0, oy)), (max(0, -ox), max(0, -oy)))
    return canvas


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1])
    layouts = json.loads((ROOT / "tools" / "website" / "maplayouts.json").read_text(encoding="utf-8"))
    want = sys.argv[2:] or list(layouts)
    jf = ROOT / "tools" / "website" / "maproutes.json"
    result = json.loads(jf.read_text(encoding="utf-8")) if jf.exists() else {}
    for name in want:
        f = next(iter(sorted(src.glob("*obj_%s.bsp" % name))), None)
        if not f:
            sys.exit("no obj_%s.bsp in %s" % (name, src))
        R = build(f)
        result[name] = routes_for(name, R, layouts[name])
        first_overlay(R, layouts[name]).save(ROOT / "docs" / "img" / "maps" / ("first-%s.webp" % name), quality=80, method=6)
        s = ", ".join("%s T %s / S %s" % (r["site"], (r.get("terrorists") or {}).get("t"), (r.get("specops") or {}).get("t"))
                      for r in result[name]["sites"])
        print("%-10s %7d spots  %s" % (name, len(R["nodes"]), s))
    jf.write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
