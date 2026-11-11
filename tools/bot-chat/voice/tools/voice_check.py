#!/usr/bin/env python3
"""Ties the radio concepts in voice_map.txt to the voice lines the game really has.

  python voice_check.py --dir "<game folder>" [--only tcetest] [--map voice_map.txt] [--out voice]
  python voice_check.py --voice file1.voice file2.voice ...

Reads every *.voice script (loose or inside .pk3 files), lists the voice ids with their captions, and for each
concept picks the id whose name or caption matches best. Writes <out>-report.txt (read this, fix by hand in
<out>-ids.txt) and <out>-ids.txt (concept<TAB>voice id; empty id = the game has no such line, bots use text only).
Exit code 1 while any used concept has no voice id, so it can gate a build."""
import argparse, io, os, re, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voice_build import CONCEPTS

def parse_voice(text):
    """ET-style .voice script: `Name { sound/path.wav "caption" ... }`. Returns {name: [captions]}."""
    text = re.sub(r"//[^\n]*", "", text)
    out = {}
    for m in re.finditer(r"([A-Za-z_][\w]*)\s*\{([^}]*)\}", text):
        caps = re.findall(r'"([^"]*)"', m.group(2))
        out.setdefault(m.group(1), []).extend(caps)
    return out

def collect(paths, root, only=None):
    found = {}
    def add(name, data):
        for k, v in parse_voice(data.decode("latin-1", "replace")).items():
            found.setdefault(k, {"captions": [], "files": set()})
            found[k]["captions"] += [c for c in v if c not in found[k]["captions"]]
            found[k]["files"].add(name)
    for p in paths:
        add(p, open(p, "rb").read())
    if root:
        for d, _, files in os.walk(root):
            for fn in files:
                full = os.path.join(d, fn)
                if only and only.lower() not in full.lower(): continue
                if fn.lower().endswith(".voice"): add(full, open(full, "rb").read())
                elif fn.lower().endswith(".pk3"):
                    try:
                        with zipfile.ZipFile(full) as z:
                            for n in z.namelist():
                                if n.lower().endswith(".voice"): add(full + ":" + n, z.read(n))
                    except zipfile.BadZipFile:
                        print("skipped (not a zip):", full)
    return found

def best(concept, found):
    rx = re.compile(CONCEPTS[concept], re.I)
    scored = []
    for vid, info in found.items():
        name = re.sub(r"(?<=[a-z])(?=[A-Z])|_", " ", vid)
        s = (3 if rx.search(name) else 0) + sum(2 for c in info["captions"] if rx.search(c))
        if s: scored.append((s, -len(vid), vid))
    scored.sort(reverse=True)
    return [v for _, _, v in scored]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir"); ap.add_argument("--voice", nargs="*", default=[])
    ap.add_argument("--map", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voice_map.txt"))
    ap.add_argument("--out", default="voice")
    ap.add_argument("--only", help="only read files whose path contains this text, e.g. the mod folder name, so stock engine voice scripts are left out")
    a = ap.parse_args()
    found = collect(a.voice, a.dir, a.only)
    if not found: sys.exit("no .voice scripts found: point --dir at the game folder or pass --voice files")
    used = {}
    for line in open(a.map, encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            k, c = line.rstrip("\n").split("\t"); used.setdefault(c, []).append(k)
    missing = []; taken = set()
    with open(a.out + "-report.txt", "w", encoding="utf-8", newline="\n") as rep, open(a.out + "-ids.txt", "w", encoding="utf-8", newline="\n") as ids:
        rep.write(f"{len(found)} voice ids found in the game files.\n\nCONCEPT -> VOICE ID (other candidates) [situations that use it]\n")
        ids.write("# concept<TAB>voice id. Edit by hand where the automatic pick is wrong; empty = text only.\n")
        for c in sorted(used):
            cands = best(c, found)
            pick = cands[0] if cands else ""
            if not pick: missing.append(c)
            taken.add(pick)
            cap = found[pick]["captions"][0] if pick and found[pick]["captions"] else ""
            rep.write(f"{c:14} -> {pick or 'NONE':22} \"{cap}\"  ({', '.join(cands[1:4])})  [{len(used[c])} situations]\n")
            ids.write(f"{c}\t{pick}\n")
        rep.write("\nVOICE IDS IN THE GAME THAT NO SITUATION USES (possible new triggers)\n")
        for vid in sorted(found):
            if vid not in taken: rep.write(f"  {vid:24} \"{(found[vid]['captions'] or [''])[0]}\"\n")
        rep.write(f"\n{len(missing)} concepts without a voice line: {', '.join(missing) or 'none'}\n")
    print(f"{len(found)} voice ids, {len(used) - len(missing)} of {len(used)} concepts matched. See {a.out}-report.txt")
    sys.exit(1 if missing else 0)
