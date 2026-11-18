#!/usr/bin/env python3
"""Virus scan of a release CANDIDATE, the evening it is built instead of at publish time.

Antivirus verdicts used to show up only after the draft release was uploaded (0.39.0: the launcher's
Defender ML hit held the publish). This checks the candidate's program files the moment they exist, so a
false positive can be reported to the vendor while the regression gate still runs.

On the PC (needs gh logged in with repo scope; nothing is published, the draft is hidden and deleted after):

    python tools/release/candidate_scan.py pc --label 0391-dev-20261127-1800 <file> [<file> ...]
    e.g. the candidate's TrueCombatPlatinum.exe, engine/platinum-engine.bin, server/platinum-server.bin,
         every .dll under engine/ and tcetest/, and TrueCombat-Platinum-Setup.exe once a dry run made one.

  1. creates a hidden draft release vt-<label> holding only those files
  2. starts the "Candidate virus scan" workflow for it and waits (VirusTotal free tier: ~1 min per file)
  3. reads the vt-candidate.json result the workflow attaches to the draft, prints it with the
     false-positive submission links, deletes the draft, and exits 1 when any engine flags a file.

On GitHub Actions (.github/workflows/candidate-scan.yml): `candidate_scan.py ci --tag vt-<label>`.
Results stay in the hidden draft (public workflow logs only show counts)."""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import virusscan  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "Annoximeme/TrueCombat-Platinum")
RESULT = "vt-candidate.json"
FP_LINKS = {
    "Microsoft": "https://www.microsoft.com/en-us/wdsi/filesubmission (Software developer, 'Incorrectly detected as malware')",
    "default": "see /mnt/project-files/virus-scan/false-positive-reports.md for the vendor contacts",
}


def gh(*args, capture=True):
    r = subprocess.run(["gh", *args], capture_output=capture, text=True)
    if r.returncode:
        raise SystemExit("gh %s failed: %s" % (" ".join(args[:3]), (r.stderr or "")[-400:]))
    return r.stdout


def ci(tag):
    key = os.environ.get("VT_API_KEY", "").strip()
    if not key:
        sys.exit("VT_API_KEY missing")
    rel = next((r for r in virusscan.releases({tag}) if r["tag_name"] == tag), None)
    if not rel or not rel.get("draft"):
        sys.exit("%s is not a draft release" % tag)
    vt, out = virusscan.VirusTotal(key, 400), []
    with tempfile.TemporaryDirectory() as tmp:
        for asset in rel["assets"]:
            if asset["name"] == RESULT:
                continue
            path = virusscan.download_asset(asset, tmp)
            sha = virusscan.sha256_file(path)
            result = vt.report(sha)
            if not result:
                analysis = vt.upload(path)
                for _ in range(60):
                    if vt.analysis_done(analysis):
                        break
                    time.sleep(30)
                result = vt.report(sha) or {"malicious": 0, "suspicious": 0, "engines": 0, "flagged_by": [], "pending": True}
            out.append({"file": asset["name"], "sha256": sha, **result, "flagged": virusscan.flagged(result),
                        "report": "https://www.virustotal.com/gui/file/" + sha})
            print("scanned %d file(s), %d flagged so far" % (len(out), sum(1 for o in out if o["flagged"])), flush=True)
        res = pathlib.Path(tmp) / RESULT
        res.write_text(json.dumps({"tag": tag, "files": out}, indent=1), encoding="utf-8")
        subprocess.run(["gh", "release", "upload", tag, str(res), "--clobber", "--repo", REPO], check=True)


def pc(label, files, keep):
    tag = "vt-" + label
    paths = [pathlib.Path(f) for f in files]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        sys.exit("missing: %s" % missing)
    # release assets need unique names: same-named files (engine/ and server/ EOSSDK dll) go up as <folder>__<name>
    names = [p.name for p in paths]
    stage = tempfile.TemporaryDirectory()
    for i, p in enumerate(paths):
        if names.count(p.name) > 1:
            q = pathlib.Path(stage.name) / ("%s__%s" % (p.parent.name, p.name))
            q.write_bytes(p.read_bytes()); paths[i] = q
    gh("release", "create", tag, "--draft", "--repo", REPO, "--title", tag,
       "--notes", "Hidden candidate scan, deleted after the check. Not a release.")
    try:
        gh("release", "upload", tag, *map(str, paths), "--repo", REPO)
        gh("workflow", "run", "candidate-scan.yml", "--repo", REPO, "-f", "tag=" + tag)
        print("uploaded %d file(s) to hidden draft %s; waiting for the scan" % (len(paths), tag), flush=True)
        deadline = time.time() + 3 * 3600
        while time.time() < deadline:
            time.sleep(60)
            assets = json.loads(gh("release", "view", tag, "--repo", REPO, "--json", "assets"))["assets"]
            if any(a["name"] == RESULT for a in assets):
                break
        else:
            sys.exit("no result after 3 h; the draft %s is kept for a look" % tag)
        with tempfile.TemporaryDirectory() as tmp:
            gh("release", "download", tag, "--repo", REPO, "--pattern", RESULT, "--dir", tmp)
            data = json.loads((pathlib.Path(tmp) / RESULT).read_text(encoding="utf-8"))
    finally:
        if not keep:
            subprocess.run(["gh", "release", "delete", tag, "--yes", "--cleanup-tag", "--repo", REPO], capture_output=True)
    bad = [f for f in data["files"] if f["flagged"]]
    for f in data["files"]:
        print("%-40s %s/%s %s" % (f["file"], f["flagged"], f.get("engines"), "; ".join(f.get("flagged_by", [])) or "clean"))
    if bad:
        print("\nFLAGGED. Report each false positive now, while the gate runs:")
        for f in bad:
            vendors = {e.split(":")[0] for e in f.get("flagged_by", [])}
            for v in sorted(vendors):
                print("  %s %s -> %s" % (f["file"], v, FP_LINKS.get(v, FP_LINKS["default"])))
            print("  report: %s" % f["report"])
    print("CANDIDATE SCAN", "FLAGGED" if bad else "CLEAN")
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pc"); a.add_argument("--label", required=True); a.add_argument("--keep", action="store_true"); a.add_argument("files", nargs="+")
    b = sub.add_parser("ci"); b.add_argument("--tag", required=True)
    args = ap.parse_args()
    if args.cmd == "ci":
        if not args.tag.startswith("vt-"):
            sys.exit("candidate drafts are named vt-<label>")
        ci(args.tag)
    else:
        pc(args.label, args.files, args.keep)


if __name__ == "__main__":
    main()
