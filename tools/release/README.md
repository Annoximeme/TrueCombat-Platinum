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
