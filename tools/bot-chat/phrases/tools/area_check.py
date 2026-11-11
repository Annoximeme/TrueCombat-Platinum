#!/usr/bin/env python3
"""Check the phrase bank against real area names.

Usage:
  python area_check.py --names names.txt            one area name per line
  python area_check.py --bsp maps/obj_village.bsp   reads target_location names from a map
  python area_check.py --pk3 pak0.pk3               every maps/*.bsp inside a pk3
  python area_check.py --dir <game folder>          every .pk3 and .bsp below a folder
Options: --bank phrases.json (default: next to this tool's parent), --out report.md, --samples 6

It normalises each name the way the game should before filling {area} (rules in normalise()),
flags names that will read badly, fills every {area} line with every name, and lists the
combinations a runtime picker must skip. Exit code 1 when a name needs a manual alias.
"""
import argparse, json, os, random, re, struct, sys, zipfile

ARTICLES = ("the ", "a ", "an ")
MAX_NAME = 22          # longer names push call-outs past one chat line
MAX_FILLED = 64        # keep bot lines to one short chat line

def normalise(raw):
    """What the game should do to a location name before using it in a line."""
    s = re.sub(r"\^.", "", raw)                 # Quake colour codes (^1, ^7 ...)
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .,:;-_")
    low = s.lower()
    for a in ARTICLES:                           # "the Shed" -> "Shed": players say "one shed"
        if low.startswith(a): s = s[len(a):]; break
    if s.isupper() and len(s) > 3: s = s.title() # "COURTYARD" -> "Courtyard"; keep "A", "B", "CT"
    return s

def problems(raw, name):
    p = []
    if not name: p.append("empty after cleaning"); return p
    if len(name) > MAX_NAME: p.append(f"long ({len(name)} chars): give it a short alias")
    if re.search(r"[^\w '&/().-]", name): p.append("unusual characters")
    if re.match(r"(?i)(near|at|in|on|by|behind|inside|outside|towards?|to)\b", name):
        p.append("starts with a preposition: 'one at %s' will read twice" % name)
    if re.search(r"(?i)\b(spawn|base)\b", name) and not re.search(r"(?i)(red|blue|terror|spec|ops|axis|allied|attack|defen|\bT\b|\bCT\b)", name):
        p.append("ambiguous spawn/base name: say whose")
    if re.fullmatch(r"\d+", name): p.append("number only: reads like a count")
    return p

def bsp_locations(data):
    """target_location 'message' values from a Quake 3 / ET BSP entity lump."""
    if data[:4] not in (b"IBSP", b"RBSP"): return []
    off, ln = struct.unpack_from("<ii", data, 8)   # lump 0 = entities
    text = data[off:off+ln].decode("latin-1", "replace")
    out = []
    for ent in re.findall(r"\{([^{}]*)\}", text):
        kv = dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', ent))
        if kv.get("classname") in ("target_location", "info_location") and kv.get("message"):
            out.append(kv["message"])
    return out

def collect(args):
    names = {}   # source -> [raw names]
    if args.names:
        names[args.names] = [l.strip() for l in open(args.names, encoding="utf-8") if l.strip() and not l.startswith("#")]
    def bsp(path, data): 
        got = bsp_locations(data)
        names[path] = got
    def pk3(path):
        try:
            with zipfile.ZipFile(path) as z:
                for n in z.namelist():
                    if n.lower().endswith(".bsp"): bsp(f"{os.path.basename(path)}:{n}", z.read(n))
        except zipfile.BadZipFile: print("skip (not a zip):", path)
    if args.bsp: bsp(args.bsp, open(args.bsp, "rb").read())
    if args.pk3: pk3(args.pk3)
    if args.dir:
        for root, _, files in os.walk(args.dir):
            for f in files:
                p = os.path.join(root, f)
                if f.lower().endswith(".pk3"): pk3(p)
                elif f.lower().endswith(".bsp"): bsp(p, open(p, "rb").read())
    return names

def words(s): return set(re.findall(r"[a-z0-9]+", s.lower()))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names"); ap.add_argument("--bsp"); ap.add_argument("--pk3"); ap.add_argument("--dir")
    ap.add_argument("--bank", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "phrases.json"))
    ap.add_argument("--out", default="area-report.md"); ap.add_argument("--samples", type=int, default=6)
    a = ap.parse_args()
    bank = json.load(open(a.bank, encoding="utf-8"))
    lines = [(k, p, l) for k, v in bank["situations"].items() for p, ls in v["lines"].items() for l in ls if "{area}" in l]
    src = collect(a)
    if not src: ap.error("give --names, --bsp, --pk3 or --dir")
    rnd = random.Random(7); rep = [f"# Area name check\n\nBank {bank['version']}, {len(lines)} lines use {{area}}.\n"]
    bad = 0; aliases = {}
    for source, raws in src.items():
        uniq = sorted(set(raws))
        rep.append(f"\n## {source}\n\n{len(uniq)} location names" + ("" if uniq else ". **No target_location in this map: the map brain must name the areas.**") + "\n")
        if not uniq: continue
        rep.append("| Map name | Used in chat as | Notes | Lines to skip |\n|---|---|---|---|")
        seen = {}
        for raw in uniq:
            n = normalise(raw); pr = problems(raw, n)
            if n.lower() in seen and seen[n.lower()] != raw: pr.append(f"same as '{seen[n.lower()]}' after cleaning")
            seen.setdefault(n.lower(), raw)
            skip = 0
            for k, p, l in lines:
                rest = words(l.replace("{area}", ""))
                filled = l.replace("{area}", n)
                if (words(n) & rest & {"roof","window","ladder","door","spawn","bomb","site","stairs","water","smoke","back","top","long","mid"}) or len(filled) > MAX_FILLED:
                    skip += 1
            if pr: bad += 1
            if n != raw: aliases[raw] = n
            rep.append(f"| `{raw}` | {n} | {'; '.join(pr) or 'ok'} | {skip} |")
        rep.append("\nSample lines:\n")
        pool = [normalise(r) for r in uniq if normalise(r)]
        for k, p, l in rnd.sample(lines, min(a.samples * 4, len(lines))):
            rep.append(f"- `{k}` ({p}): {l.replace('{area}', rnd.choice(pool)).replace('{count}', str(rnd.choice([2,2,3,3,4]))).replace('{name}', 'RaziC').replace('{enemy}', 'RavoC')}")
    rep.append("\n## Runtime rules this report assumes\n\n1. Clean each name with `normalise()` (strip colour codes and a leading article, fix ALL CAPS).\n"
               "2. Skip a line when a word of the area name already appears in the line (\"he's on the roof Roof\").\n"
               f"3. Skip a line when the filled text is over {MAX_FILLED} characters.\n4. Names flagged above need a short alias in `bots/<map>.areas.json`.\n")
    open(a.out, "w", encoding="utf-8", newline="\n").write("\n".join(rep) + "\n")
    json.dump(aliases, open(os.path.splitext(a.out)[0] + ".aliases.json", "w", encoding="utf-8"), indent=1)
    print(f"{sum(len(set(v)) for v in src.values())} names from {len(src)} sources, {bad} need attention. Report: {a.out}")
    sys.exit(1 if bad else 0)

if __name__ == "__main__": main()
