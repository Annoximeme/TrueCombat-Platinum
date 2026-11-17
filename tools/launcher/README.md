# Launcher 2.6.2

The launcher hotfix live on v0.38.1-sandbox35 since 17 November 2026 (TrueCombatPlatinum-Launcher.exe,
SHA-256 27fe8c54b5bd713f0bbfd08f05a98e15523d65f11ef860f44047087203baf4aa).

## Why

During the 0.38.0 update, a player's antivirus removed the new engine from the update. Launcher 2.6.1 kept the old
engine next to the new data and showed only "Update check failed". It gave no reason, the repair refused to run
without the engine, and PLAY kept offering INSTALL.

## What 2.6.2 does

- **Reasons, not "Update check failed".** Settings > Updates, the status rail, its tooltip and the PLAY button show
  why an update failed. An action the player started explains a failure once in a message.
  `updates\launcher-update.log` records every step: time, host, HTTP status, WinHTTP/Windows error and file. It rotates at 256 KB.
- **Antivirus-aware.** Access denied, errors 225/226 and a file that vanishes right after it is written produce
  "Your antivirus blocked <file>. Add the TrueCombat Platinum folder as an exception, then click Try again."
  Each file gets three tries, and the reason survives the fall-back from per-file downloads to the full zip.
  A blocked download host is named.
- **Self-repairing installs.** Missing or wrong-size files are found at start and repaired. A missing engine on an
  older install fetches the update. Verify and repair works from any state, re-hashes after the download and after
  the copy, and reports "Repaired N files". Leftover staging and partial zips are cleared, and an interrupted copy
  is detected on the next start.
- **Launcher updates never wait on the game.** The launcher's own update is offered after every feed read, also when
  the game update failed. The shipped 2.6.1 updates itself to 2.6.2, which was verified live.

## Release gate

- `tests/launcher_repair/run_suite.py`: 11 broken-install cases against a loopback copy of a real release (old engine
  on a newer build, an antivirus blocking or removing a file, a blocked asset host, leftover staging and a partial
  zip, the restart after a failed apply, the previous launcher updating itself, offline, a bad signature, a corrupted
  pak, a missing engine). It passed 11/11 on the shipped binary.
- `analysis_scripts/x64/launcher_release_build.py`: the one reproducible build of a shipped launcher.
- `analysis_scripts/x64/launcher_gate.py`: packaging and the feed tool refuse a launcher without a passing run for
  its exact SHA-256.
- `analysis_scripts/x64/release_canary.py`: after a publish, checks the live signed feed, files.txt, 3 random assets,
  the launcher and the installer from the public download host.

## Files

- `launcher-2.6.2-on-0.38.1.mbox`: the five commits, for `git am` on the 0.38.1 release source (rel0381).
- `src/`: the changed and new files as they are after those commits, for reading.

Launcher 3.0.1 for 0.39.0 carries the same changes, merged with 3.0's pause/resume and translated.
