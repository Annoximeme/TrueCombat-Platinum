# Kit: audit-0391 (0.39 audit fixes after the 0.39.0 cut-off)

Owner: thread "Audit 0.39 for bugs and polish". For: the 0.39.1 release.
Base: the published 0.39.0 source, integ039/base/TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256
8032095307abdbfc..., already holds audit-polish 01a-08). Apply in name order with plain `git apply` (CRLF kept).
GATE PASSED 2026-11-18 17:48:38Z on that zip, all steps green incl. scan (kit checksum 029a45adb5fc1e22): SUMMARY.md here.
Gianni's decision (card in the audit thread, 2026-11-18 15:28Z): "Keep it for 0.39.1" (09). 10 and 11 were found after it,
in passes 7 and 8, and follow the same rule (cut-off closed, next release).

| Patch | Side | What (doc items) |
|---|---|---|
| 09-wall-dot-and-out-of-breath.patch | client + SERVER | M4 SOPMOD red dot no longer floats at a wall (53); out of breath with the sprint key held no longer predicted as a sprint: no stutter / rubber-banding, gun not in the sprint pose (54). Uses stance stat bits 0x10 / 0x20. |
| 10-team-change-answer.patch | client | Answers to a team change and to the competitive match commands (queued "You will join ... when you next deploy", refused, locked, timeouts) show as a popup instead of the console only (56). |
| 11-competitive-match-texts.patch | client + one SERVER line | Competitive matches: right round numbers (knife round is not round 1), no "Next round in" after the knife round or the last round, nothing drawn over the scoreboard, no "has joined" line per player at a side swap (57-60). Normal matches unchanged. |

Each patch can be left out on its own (checked: 11 applies without 09 and 10). 0.39.1 needs the server module rebuilt (09, 11).
Mixed versions are safe: an old server with the new client behaves as 0.39.0, an old client ignores the new bits.
No new cvar, no pak, no menu file, no new engine call.

Checks beyond the gate (cloud, OpenGL, details in game-audit/round3/kit-0391/kit.md and round3/NOTES.md passes 5-8):
each item seen on screen before and after; ASan + UBSan client and server 4 of 4 matches clean on 09; prediction
corrections 0 in every movement state, also at ~200 ms ping with 3 % loss and at 250 FPS; normal Bomb regression run on
09+10+11 shows the stock texts unchanged.
Suggested PC looks (DX12): M4 SOPMOD aimed nose to a wall (dot gone once the gun drops); sprint until out of breath
with the key held (no stutter); change team from Deployment while alive in a Bomb round (popup).

Patch notes (player wording):
- The M4 SOPMOD's red dot no longer hangs in the air when you push the gun against a wall.
- Running out of breath while holding sprint no longer makes your view stutter.
- Changing team now tells you on screen when the switch happens, or why it was refused.
- Competitive matches: round numbers, round results and the scoreboard now follow the match, and side swaps no longer
  flood the feed.
