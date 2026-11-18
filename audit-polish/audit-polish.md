# Kit: audit-polish for the 0.39.0 rebuild (0.39 audit fixes)

Owner: thread "Audit 0.39 for bugs and polish". For: thread "Build and package 0.39.0".
Gianni 2026-11-18 12:45Z in the project chat: "All of them." (answer to the coordinator's list of what to add to the
0.39.0 rebuild; item 1 = the HUD/game-mode audit fixes). Patches 04 and 05 (hitch fixes): approved by Gianni on a
card in the audit thread 12:54Z, see "Status of 04/05" below.

Base: /mnt/project-files/integ039/base/TrueCombat-Platinum-0.39.0-sandbox37-source.zip (sha256 20e7673fd96f0b2c...).
Folder: /mnt/project-files/integ039/kits/audit-polish/ (patches/ only; SUMMARY.md after the gate).

## What is in it
Client game module only: game_src/native/*.h and tcp_cgame.c (CRLF kept). No server code, no engine, no renderer, no
pak, no menu file, no cvar default that a server reads. Apply in name order with plain `git apply`:

| Patch | Files | What |
|---|---|---|
| 01a-hud-polish.patch | 14 cgame files | 39 HUD and game-mode polish items (v12) |
| 01b-match-screen-texts.patch | tcp_bomb_cg.h, tcp_cgame.c, tcp_hud_platinum_cg.h | match screen texts (0.39.x wording; the 0.40 UI kits K6 replace them) |
| 02-flash-covers-hud.patch | tcp_cgame.c, tcp_vux_cg.h | flash white-out also covers minimap, compass, place name, objective card; tactical map stays closed while blind |
| 03-replay-camera.patch | tcp_immersion_cg.h | final-kill replay camera no longer ends inside the killer's head or behind a fence |
| 04-prediction-mover-cull.patch | tcp_cgame.c | Railhouse hitch: prediction skips movers clear of the move box (10,666 -> 76 traces a frame) |
| 05-late-load-precache.patch | tcp_cgame.c | first-use hitches: radio/HQ lines, climb, dry click, bolt, dropped magazines precached at load |

Item list with the before/after for each: /mnt/project-files/game-audit/round3/kit-polish/kit.md (items 1 to 9ab) and
(items 3 to 45). Evidence shots: /mnt/project-files/game-audit/round3/evidence/.

New since the patches you may have seen (v12, pass 4, 2026-11-18): FPS counter under the minimap instead of across it;
"In-game UI size" under 100% only shrinks as far as its text fits; Classic scoreboard shows a round number only in round
modes; no Deployment/radio/vote menu over demo playback; "CONNECTION INTERRUPTED" card after 1.5 s without an answer
from the server.

## Rebase onto the real 0.39.0 source
The six commits were cherry-picked from the audit tree (cloud rebuild of 0.39) onto the zip. One hand-merge: first
line of frame() in tcp_cgame.c, now `hudNow=time;gpNow=time; /* 0.39.0 */demoPlaying=demo;`. Everything else merged
by itself; per-file line counts equal the audit tree's (16 files, +296 -73). The six files apply on the zip in order
and reproduce the rebased tree exactly (checked in a clean worktree).

## Status of 04/05
APPROVED: Gianni chose "Yes, add both hitch fixes" on the card in the audit thread, 2026-11-18 12:54Z (card
cmsg_01267kFSMwnKiipVDcuLPiLKPykiSsWACTjhTnT57jEBxL). All six patches go into the 0.39.0 rebuild.

## Gate
SUMMARY.md in the folder (copy: audit-polish-SUMMARY.md), kit checksum e6227a187e75a48b, base sha256 20e7673fd96f0b2c,
finished 2026-11-18 13:00:57Z. compose, toolchain, windows (+ probes), scan-built, linux, bots (Village, Snow: 12 bots,
1304 / 1205 hits, server CPU 4 % avg): all PASS. scan: FAIL with the one hit that is in the base itself
(analysis_scripts/x64/preflight_release.py line 241, "c2pa label"), accepted by the release thread for this rebuild
(option c, 12:51Z). The summary's last line therefore reads "KIT GATE FAILED"; the note under it explains.

## Checks beyond the gate (cloud, OpenGL client under Xvfb, 1600x900 unless said)
- Every item was looked at on screen before and after (runs listed in kit.md and round3/NOTES.md).
- Memory-error builds (ASan + UBSan, client and server): 8 of 8 matches clean on v11; v12 on the real source: see
  "Re-run on the real source" below.
- Re-run on the real source (cgame built from the zip + this kit): filled in when done.

## Release thread steps
1. `git apply --check` then apply the files in order on the rel039 game tree (game_src/native). cgame rebuild only.
2. No new pak, no new cvar that needs a menu row. New client cvars: none. New console text: none.
3. Full 19-case gate as usual. Suggested looks in the PC pass: scoreboard and tactical map titles, a Bomb round end,
   Capture Point card + minimap marker, firing range panel under the minimap with the FPS counter on, Railhouse glass
   fronts (walk, lean, break a pane: no rubber-banding), a flash grenade with the minimap open.
4. The 0.40 UI stack (thread "Overhaul the in-game UI for 0.40") must be rebased on 0.39.0 WITH this kit; that thread
   has the item list (its K6 05/06 and K5 02 carry the 0.40 versions).

## Patch notes (player wording, pick what fits)
- Clearer match screens: map names read properly on the scoreboard and tactical map, round results name the teams
  ("Terrorists win the round"), and Bomb, Flag and Capture Point objective cards say what to do next.
- Capture Point: the point is now marked on the tactical map and the minimap.
- Team Deathmatch and Flag: waiting players see "Deploying in N" instead of "No more deployments this round".
- Spectators of team matches get the team scoreboard and the right status texts.
- Firing range and practice: the range panel no longer overlaps the minimap, and it says how many targets are up.
- The FPS counter no longer sits on the minimap. Small "In-game UI size" settings keep all text readable.
- Match end: the podium is lit the same on every map, and the game view dims behind the map vote.
- Kill feed, chat box, vote menu, weapon pickup prompt and first-launch tips: fixes for overlapping or cut-off text.
- Flash grenades now also blind the minimap, compass and objective card.
- The final-kill replay camera no longer ends up inside the shooter or behind a fence.
- A "Connection interrupted" notice appears when the server stops answering.
- Recorded demos play back without menus opening over them.
- Smoother movement near the glass fronts on Railhouse, and fewer small freezes the first time a
  sound or effect is used.
