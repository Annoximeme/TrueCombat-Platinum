# Release upload tools

Most of a release is identical to the one before it: of the ~4.3 GB we attach to
every release, typically only 60 to 150 MB actually changes. These tools upload
only that part from the release PC and let GitHub build the rest.

| File | Runs on | What it does |
|---|---|---|
| `fast_publish.py` | release PC | Compares the release with the previous one, uploads changed files and small patches plus a plan (`_fill.json`), starts **Release fill**, waits, checks the draft. Publishes only with `--publish`. |
| `fill_release.py` | GitHub Actions (`.github/workflows/release-fill.yml`) | Checks the plan against `update.txt` and `files.txt`, copies unchanged assets from the previous release, rebuilds patched ones, re-hashes every asset on the draft, removes the staging files. Never publishes. |
| `zippatch.py` | both | Patch format for zip and pk3 files: unchanged entries are copied from the old file, the rest is stored. Applying checks the exact size and SHA-256. |

## Release steps (replaces the per-version `publish.py`)

1. Package as usual (`package_from_candidate.py`, `finalize`, `make_update_feed.py --delta`, signing, scans).
2. Create the draft release with its notes (as before).
3. Plan only, to see what will be sent:

       python -X utf8 tools/release/fast_publish.py --root <project root> --version 0.36.0-sandbox28 \
           --base-version 0.35.0-sandbox27 --feed <path>/update.txt --dry-run

4. Upload and fill the draft (no publish):

       python -X utf8 tools/release/fast_publish.py --root <project root> --version 0.36.0-sandbox28 \
           --base-version 0.35.0-sandbox27 --feed <path>/update.txt

5. Publish only after the owner's go: run the same command with `--publish`
   (it re-checks the draft and publishes).

`--base-version` must be the previous **published** release, and that release must
stay on GitHub. Each release still carries its complete set of assets, so every
launcher version and the Versions list keep working unchanged.

If anything goes wrong, nothing is published: rerun the same command (finished
uploads are skipped), or use `--full` to upload everything from the PC the old way.

## Virus scan and checksums

`virusscan.py` checks every release with VirusTotal and records the SHA-256 of the
installer and of every program file (.exe, .dll) in `tools/website/scans.json`. The
website shows the result in a badge beside each download button, in the "Download
safety" panel on the download page and on every release page, together with the
installer's checksum. Detections are shown as they are, with a link to the full report.

It runs by itself, with no manual steps:

* `fast_publish.py` starts the **Virus scan** workflow on the draft after the upload and
  prints the result before publishing. If any engine flags a file, `--publish` stops until
  the owner has seen the report (rerun with `--accept-detections`). `--no-scan` skips it.
* `.github/workflows/virus-scan.yml` runs again when the release is published and once a
  day, to pick up late detections and finish scans the free API limit left open.

Setup, once: the repository secret `VT_API_KEY` holds a free VirusTotal API key
(Settings, Secrets and variables, Actions). The key is never stored in the repository.
Without it the checksums are still recorded and shown. The free API allows 4 requests a
minute and 500 a day; the script paces itself (16 s per request, at most 110 per run).
Files VirusTotal already knows cost one lookup, so a typical release takes a few minutes.

## Candidate virus scan (pipeline plan item 7)

`candidate_scan.py pc --label <version>-<run> <files...>` runs on the PC right after a candidate is built
(launcher, engine and server .bin, every .dll, and Setup once a package dry run made one). It puts only
those files in a hidden `vt-<label>` draft, starts the **Candidate virus scan** workflow, prints each
file's VirusTotal verdict with the false-positive submission link per vendor, deletes the draft, and
exits 1 when anything is flagged. Never touches the website or a published release.
