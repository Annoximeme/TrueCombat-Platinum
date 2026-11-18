# Kit: audit-polish for the 0.39.0 rebuild (0.39 audit fixes)

Owner: thread "Audit 0.39 for bugs and polish". For: thread "Build and package 0.39.0".
Gianni 2026-11-18 12:45Z in the project chat: "All of them." (answer to the coordinator's list of what to add to the
0.39.0 rebuild; item 1 = the HUD/game-mode audit fixes). Patches 04 and 05 (hitch fixes): approved by Gianni on a
card in the audit thread 12:54Z, see "Status of 04/05" below.

Base: /mnt/project-files/integ039/base/TrueCombat-Platinum-0.39.0-sandbox37-source.zip (sha256 20e7673fd96f0b2c...).
Folder: /mnt/project-files/integ039/kits/audit-polish/ (patches/ only; SUMMARY.md after the gate).
SECOND CUT 2026-11-18: patches 06, 07, 08 added (see "Second cut" below); 01a to 05 unchanged.

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
| 06-match-end-menus.patch | tcp_deploy_menu.h, tcp_cgame.c | SECOND CUT. Deployment closes (and cannot open) once the match is over; the connection card stays away while the map vote card says LOADING |
| 07-bugreport-shot-size.patch | tcp_bugreport_cg.h, tcp_cgame.c | SECOND CUT, Gianni's bug "screenshots are too large for upload": the F12 report shot is written at a JPEG quality picked from the pixel count |
| 08-m68-single-dot.patch | tcp_cgame.c | SECOND CUT, Gianni's bug "two red dots": the M4 SOPMOD's sight model no longer draws its own dot next to the HUD dot |

Item list with the before/after for each: /mnt/project-files/game-audit/round3/kit-polish/kit.md (items 1 to 9ab) and
(items 3 to 45). Evidence shots: /mnt/project-files/game-audit/round3/evidence/.

New since the patches you may have seen (v12, pass 4, 2026-11-18): FPS counter under the minimap instead of across it;
"In-game UI size" under 100% only shrinks as far as its text fits; Classic scoreboard shows a round number only in round
modes; no Deployment/radio/vote menu over demo playback; "CONNECTION INTERRUPTED" card after 1.5 s without an answer
from the server.

## Second cut (2026-11-18, before the 15:00Z cut-off): patches 06, 07, 08
01a to 05 are byte-identical to the first cut; 06 to 08 are new files that apply on top, in name order. Each one can be
left out on its own (08 does not depend on 06/07).

- 06: found in the re-run of the HUD scenes on the real source. With Deployment open when the match ended, the menu
  stayed over the podium and the map vote; and the new connection card (item 9ab) showed over the vote card's "LOADING"
  while the server changed map. Seen fixed on screen (runs depend2, depend3).
- 07: Gianni 13:19Z in the project chat: "Bug reporting sometimes shows screenshots are too large for upload".
  Cause: the report shot is a normal screenshot at r_screenshotJpegQuality 90; the upload takes 1 MiB. Measured in the
  cloud at 3840x2160: 3.0 to 3.1 MB at quality 90 (so 1440p and 4K were nearly always over, 1080p sometimes). Now the
  quality is set from the pixel count for that one shot (1080p 75, 1440p 60, 4K 20) and the player's own value is put
  back four frames and half a second later, and at shutdown. Measured at 4K: quality 20 = 0.52 MB, 40 = 0.53 MB,
  50 = 0.82 MB (different views). Client only; the portal's limit is untouched. NOT tested end to end: the audit rig
  never runs `bugreport` (no uploads to the live portal), so the PC pass should send one F12 report at 1440p or 4K and
  see "Report sent" without "(screenshot kept locally: too large)", and check `r_screenshotJpegQuality` is back at its
  old value afterwards.
- 08: Gianni 13:21Z: "Small bug with the two red dots". Cause: the HUD draws the M68 dot at the screen centre (0.36.0,
  because the model's own dot quad was sub-pixel at 1080p); at 1440p and 4K the model's quad is visible too, and it
  moves with the gun, so a second dot wanders around the first while walking. Reproduced in the cloud at 3840x2160 on
  Village (stock dot) and Harbour (CQB dot). Fix, cgame only: the HUD dot gets its own shader (same stages, made with
  the engine's dynamic shader call, no pak change) and the model's reticle shader is remapped to one that draws nothing.
  If either shader cannot be made, nothing is remapped and it behaves as before. Console line at load:
  `TCP_NATIVE_M68DOT dot=1 hide=1`. Uses two engine calls this cgame did not use before (CG_R_LOADDYNAMICSHADER,
  CG_R_REMAP_SHADER; both live in the shared renderer front end, tr_shader.c / tr_shade.c of renderer and renderer_vk).
  Seen on OpenGL only, so the DX12 look is the PC pass: aim the M4 SOPMOD (M68) and walk: exactly one dot, at the
  centre; same on Harbour with CQB optics. If DX12 shows anything else, drop 08 and tell the audit thread.
  The model's dot is hidden only while the M4 SOPMOD is in hand. Known and not changed: the AK-74M Spetsnaz mounts
  the same sight but has no HUD dot, and its own dot quad is too small to see (no dot at 4K in the rig, stock map and
  Harbour); follow-up question for Gianni, not in this kit.

## Rebase onto the real 0.39.0 source
The six commits were cherry-picked from the audit tree (cloud rebuild of 0.39) onto the zip. One hand-merge: first
line of frame() in tcp_cgame.c, now `hudNow=time;gpNow=time; /* 0.39.0 */demoPlaying=demo;`. Everything else merged
by itself; per-file line counts equal the audit tree's (16 files, +296 -73). The six files apply on the zip in order
and reproduce the rebased tree exactly (checked in a clean worktree).

## Status of 04/05
APPROVED: Gianni chose "Yes, add both hitch fixes" on the card in the audit thread, 2026-11-18 12:54Z (card
cmsg_01267kFSMwnKiipVDcuLPiLKPykiSsWACTjhTnT57jEBxL). All six patches go into the 0.39.0 rebuild.

## Gate
SECOND CUT (all nine patches): SUMMARY.md in the folder (copy: audit-polish-SUMMARY.md), kit checksum e19fdc96b7721b42,
base sha256 20e7673fd96f0b2c, started 2026-11-18 14:00:03Z, finished 14:07:51Z. compose, toolchain, windows (+ probes,
-Werror), scan-built, linux, bots (Village, Snow: 12 bots, 1304 / 1205 hits, server CPU 4 % avg): all PASS. scan: FAIL
with the one hit that is in the base itself (analysis_scripts/x64/preflight_release.py line 241, "c2pa label"), accepted
by the release thread for this rebuild (option c, 12:51Z). The summary's last line therefore reads "KIT GATE FAILED";
the note under it explains. First cut (01a-05): checksum e6227a187e75a48b, 13:00:57Z, same result.

## Checks beyond the gate (cloud, OpenGL client under Xvfb, 1600x900 unless said)
- Every item was looked at on screen before and after (runs listed in kit.md and round3/NOTES.md).
- Memory-error builds (ASan + UBSan, client and server): 8 of 8 matches clean on v11; v12 on the real source: see
  "Re-run on the real source" below.
- Re-run on the real source (cgame built from the zip + patches 01a-05): the HUD scenes of scripts/p4reg.sh look as
  on the audit tree (resolutions, defuse, range, FPS chip, match end, movement); ASan + UBSan matches 8 of 8 clean in
  game code (Village x2, Harbour CQB Rules, Snow Bomb, Railhouse TDM, Snowtown Flag, Northport, Delta; finished 13:50Z).
- Second cut (06-08): each fix seen on screen (runs depend2/depend3, dotvc/dothc/dot2 at 3840x2160, dot2f across a map
  change: `TCP_NATIVE_M68DOT dot=1 hide=1` on both maps, no renderer warnings). No ASan run on 06-08 yet.

## Release thread steps
1. `git apply --check` then apply the files in order on the rel039 game tree (game_src/native). cgame rebuild only.
2. No new pak, no new cvar that needs a menu row. New client cvars: none. New console text: none.
3. Full 19-case gate as usual. Suggested looks in the PC pass: scoreboard and tactical map titles, a Bomb round end,
   Capture Point card + minimap marker, firing range panel under the minimap with the FPS counter on, Railhouse glass
   fronts (walk, lean, break a pane: no rubber-banding), a flash grenade with the minimap open.
   Second cut: M4 SOPMOD aimed while walking (one dot, DX12, stock map and Harbour); one F12 report at 1440p/4K
   ("Report sent" with the screenshot); Deployment left open through a match end.
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
- Second cut: Bug reports (F12) from 1440p and 4K screens now include their screenshot.
- Second cut: The M4 SOPMOD's red dot sight shows a single dot at high resolutions.
- Second cut: The Deployment menu closes when the match ends.
