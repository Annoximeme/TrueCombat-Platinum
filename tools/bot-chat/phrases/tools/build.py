"""Build phrases.json and phrases.txt from the source modules, and validate them."""
import importlib, json, re, sys, os
import meta
SRC = ["p_contact","p_action","p_damage","p_objective","p_round","p_orders","x_contact","x_action","x_social","x_more1","x_more2","x_more3"]
out = sys.argv[1]
bank = {k: {p: [] for p in meta.PERSONALITIES} for k in meta.SITUATIONS}
errors = []; warn = []
for m in SRC:
    for sit, per in importlib.import_module(m).L.items():
        if sit not in bank: errors.append(f"{m}: unknown situation {sit}"); continue
        for p, s in per.items():
            if p not in bank[sit]: errors.append(f"{m}: unknown personality {p}"); continue
            for line in s.strip().split("\n"):
                line = line.strip()
                if line: bank[sit][p].append(line)
import glob
OPT = {}; EDITS = []
PMAP = {"e":"entry","a":"anchor","l":"lurker","s":"support","m":"marksman"}
here = os.path.dirname(os.path.abspath(__file__))
for fn in sorted(glob.glob(os.path.join(here, "*.bank"))):
    sit = None; cur = []
    for raw in open(fn, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"): continue
        if line.startswith("@"):
            parts = [x.strip() for x in line[1:].split("|")]
            sit = parts[0]; cur = []
            if len(parts) == 7:
                if sit in meta.SITUATIONS: errors.append(f"{fn}: {sit} defined twice")
                meta.SITUATIONS[sit] = (parts[1], parts[2], int(parts[3]), parts[4].split(), parts[6])
                OPT[sit] = parts[5].split()
                bank[sit] = {p: [] for p in meta.PERSONALITIES}
            elif len(parts) != 1 or sit not in meta.SITUATIONS:
                errors.append(f"{fn}: bad header {line}")
        elif line.startswith("=") and len(line) <= 6:
            cur = [PMAP[c] for c in line[1:]]
        else:
            if sit not in bank or not cur: errors.append(f"{fn}: stray line {line}"); continue
            for p in cur: bank[sit][p].append(line)
ef = os.path.join(here, "edits.txt")
if os.path.exists(ef):
    for raw in open(ef, encoding="utf-8"):
        raw = raw.strip()
        if not raw or raw.startswith("#"): continue
        op, rest = raw.split(" ", 1)
        if op == "move": src, dst, rx = rest.split(" ", 2)
        elif op in ("drop", "keep"): (src, rx), dst = rest.split(" ", 1), None
        else: errors.append(f"edits: bad rule {raw}"); continue
        if src not in bank or (dst and dst not in bank): errors.append(f"edits: unknown situation in {raw}"); continue
        rxc = re.compile(rx, re.I); hit = 0
        for p in meta.PERSONALITIES:
            keep = []
            for line in bank[src][p]:
                if bool(rxc.search(line)) != (op == "keep"):
                    hit += 1
                    if dst: bank[dst][p].append(line)
                else: keep.append(line)
            bank[src][p] = keep
        if not hit: errors.append(f"edits: rule matched nothing: {raw}")
        EDITS.append((op, src, dst, hit))
PH = re.compile(r"\{[a-z]+\}")
total = 0; dups = 0
sitjson = {}
for sit, (group, chan, cd, req, desc) in meta.SITUATIONS.items():
    opt = re.findall(r"(\{[a-z]+\})(?:,? and \{[a-z]+\})? optional", desc)
    opt = sorted(set(re.findall(r"\{[a-z]+\}", " ".join(re.findall(r"((?:\{[a-z]+\}(?:,? and )?)+) optional", desc)))))
    if sit in OPT: opt = sorted(OPT[sit])
    allowed = set(req) | set(opt)
    for p in meta.PERSONALITIES:
        seen = set(); clean = []
        for line in bank[sit][p]:
            key = line.lower().rstrip(".!?")
            if key in seen: dups += 1; continue
            seen.add(key); clean.append(line)
            for ph in PH.findall(line):
                if ph not in meta.PLACEHOLDERS: errors.append(f"{sit}/{p}: unknown placeholder {ph}: {line}")
                elif ph not in allowed: errors.append(f"{sit}/{p}: {ph} not available here: {line}")
            if "—" in line or "–" in line or "\t" in line: errors.append(f"{sit}/{p}: bad char: {line}")
            if len(line) > 70: errors.append(f"{sit}/{p}: too long: {line}")
        if not clean: errors.append(f"{sit}/{p}: no lines")
        bank[sit][p] = clean; total += len(clean)
    sitjson[sit] = {"group": group, "channel": chan, "cooldown_s": cd, "always": req, "maybe": opt,
                    "description": desc, "lines": bank[sit]}
if errors:
    print("\n".join(errors)); sys.exit(1)
os.makedirs(out, exist_ok=True)
doc = {"name": "TrueCombat: Platinum bot phrase bank", "version": "1.4.0", "date": "2026-11-11",
       "line_count": total, "personalities": meta.PERSONALITIES, "placeholders": meta.PLACEHOLDERS,
       "situations": sitjson}
json.dump(doc, open(f"{out}/phrases.json", "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
with open(f"{out}/phrases.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write("# TrueCombat: Platinum bot phrase bank 1.4.0 (generated from phrases.json, same content)\n")
    f.write("# Format: one line per phrase: situation<TAB>personality<TAB>text. Lines starting with # are comments.\n")
    f.write("# Situation header: @situation<TAB>group<TAB>channel<TAB>cooldown_s<TAB>placeholders_always<TAB>placeholders_maybe\n")
    for sit, d in sitjson.items():
        f.write(f"\n@{sit}\t{d['group']}\t{d['channel']}\t{d['cooldown_s']}\t{','.join(d['always'])}\t{','.join(d['maybe'])}\n")
        for p in meta.PERSONALITIES:
            for line in d["lines"][p]:
                f.write(f"{sit}\t{p}\t{line}\n")
ORDER = ["contact","action","damage","objective","clutch","round","orders","followup"]
idx = ["# Situation index (phrase bank %s)\n" % doc["version"], "%d situations, %d lines. `always` placeholders are filled every time; `maybe` only when known.\n" % (len(sitjson), total)]
for grp in ORDER:
    idx.append("\n## %s\n\n| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |\n|---|---|---|---|---|---|---|" % grp)
    for k, v in sitjson.items():
        if v["group"] != grp: continue
        desc = re.sub(r"\s*(\{[a-z]+\}(,? and | )?)+ optional[^.]*\.", "", v["description"]).strip()
        idx.append("| `%s` | %s | %s | %s | %s | %s | %d |" % (k, desc, v["channel"], v["cooldown_s"] or "-", " ".join(v["always"]) or "-", " ".join(v["maybe"]) or "-", sum(len(x) for x in v["lines"].values())))
unknown = [k for k, v in sitjson.items() if v["group"] not in ORDER]
if unknown: print("unknown group for", unknown); sys.exit(1)
open(f"{out}/SITUATIONS.md", "w", encoding="utf-8", newline="\n").write("\n".join(idx) + "\n")
print("edits:", ", ".join(f"{o} {a}{"->"+b if b else ""} {h}" for o,a,b,h in EDITS))
print("total", total, "dups removed", dups)
for p in meta.PERSONALITIES: print(p, sum(len(d["lines"][p]) for d in sitjson.values()))
from collections import Counter
print("groups", Counter(d["group"] for d in sitjson.values()), "situations", len(sitjson))
small = [(s,p,len(d["lines"][p])) for s,d in sitjson.items() for p in meta.PERSONALITIES if len(d["lines"][p])<4]
print("thin buckets (<4):", len(small), [x for x in small if x[2]<2][:20])
