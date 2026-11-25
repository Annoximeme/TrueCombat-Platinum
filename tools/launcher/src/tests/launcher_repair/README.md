# Launcher update and repair gate

Since launcher 2.6.2, no launcher ships unless this suite has passed on **exactly that file**
(same SHA-256). It came out of the 0.38.0 antivirus incident: on a player's PC, the antivirus removed the
new engine from the update, the launcher kept the old one next to the new data, and Settings > Updates
only said "Update check failed", with no reason, no repair and nothing in a log.

## What it covers

| case | broken state | what must happen |
|---|---|---|
| `friend` | previous release with an even older engine, HD textures on, leftover `updates\staging` and `package.zip.part` | leftovers cleared on start, update to the current release, every file (HD included) matches the signed list, next start is clean |
| `engine_missing` | current release without `engine\platinum-engine.bin` | repaired on start; the next start reports "Repaired 1 file" |
| `corrupt_pak` | one byte flipped in a pak (same size) | Verify and repair finds it, replaces it and re-hashes it |
| `av_write_denied` | a game file cannot be written (access denied, as a blocking scanner answers) | the failure names the file and asks for an antivirus exception; it is fetched once the block is gone |
| `av_deleted` | the staged engine vanishes right after it is written | the result names the file; the next start repairs it |
| `blocked_host` | the asset host drops every connection while the feed host answers (a web shield) | the failure names the blocked host |
| `offline` | nothing answers | "Could not reach ..." with the Windows error |
| `bad_signature` | one byte of update.txt changed | rejected as unsigned |
| `update_failed` | restart after a failed apply (`--update-failed`) | Settings > Updates shows the reason (screenshot in the run's `out` folder) |
| `self_update` | the **previous released** launcher, in a broken install with an update pending | updates itself to the launcher under test |
| `self_current` | the launcher under test | reports itself current |

Errors 225 and 226 (virus detected or removed) take the same code path as access denied. Without an
antivirus they cannot be produced on demand, so they are covered by `av_write_denied` and code review.

## How it runs

Everything runs on loopback. The release's own `update.txt` is rewritten to point at a local server and
re-signed with the release key, which never leaves the PC. Each case installs a real copy (no hard links:
Easy Anti-Cheat refuses them), and the copies are deleted afterwards. It uses CPU and disk only: no GPU and
no `suite.lock`, so it can run next to an in-game pass. A full run takes about 5 minutes.

```
python analysis_scripts/x64/launcher_release_build.py --out <dir>\TrueCombatPlatinum.exe --symbols <dir>
python tests/launcher_repair/run_suite.py --launcher <dir>\TrueCombatPlatinum.exe ^
    --previous-launcher dist\assets-<current release>\TrueCombatPlatinum-Launcher.exe ^
    --dist dist --current <current release> --old <previous release> ^
    --old-engine <engine of an older release> --work G:\TrueCombatWork\lrs
python analysis_scripts/x64/launcher_gate.py <dir>\TrueCombatPlatinum.exe
```

A complete run is recorded in `experiments/launcher-gate/<sha256>.json`. The launcher build is reproducible
(`launcher_release_build.py` is the only way a shipped launcher is built), so the file the packager builds
has the same SHA-256 as the one the suite tested.

## Where it is enforced

- `package_from_candidate.py` (full packages and `--launcher-only`) builds the launcher, then refuses to go on
  unless `launcher_gate.py` passes for it.
- `make_update_feed.py` refuses to name a launcher in any feed, including a `--launcher-hotfix`, unless that
  launcher passed.
- `preflight_release.py` (0.39.0 and later) reports BLOCK while the candidate's launcher has no passing run.
- `release_canary.py` runs after every publish. It downloads the live update.txt, files.txt and 3 random assets
  from release-assets.githubusercontent.com, plus the launcher and the website installer, and checks the
  signature and every SHA-256. The publish is not done until it passes.

CI: the suite needs a full release (several GB) and the signing key, so it runs on the release PC only, not in
the cloud kit gate or GitHub Actions. The kit gate already builds the launcher with `-Werror`.
