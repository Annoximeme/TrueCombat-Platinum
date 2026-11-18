# 0.39.1 queue (base: final 0.39.0 source zip, once published)

FINAL 0.39.0 source zip (published): /mnt/project-files/integ039/base/TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 80320953...). Gate 0.39.1 kits on this one.

## 0.39.1 SCOPE: ALL BUG FIXES (Gianni 18:08Z 18 Nov: "I want all bugfixies in 0.39.1.")

Release Thu 27 Nov 2026 (typed go in the release thread). Timeline:
- KIT CUT-OFF: Tue 24 Nov 2026 18:00 CET (17:00Z). Gated kit (SUMMARY.md from kit-gate.sh on the FINAL 0.39.0 source zip) in kits/<name>/.
- Integration + PC build Wed 25 Nov, full 19-case regression + soaks Wed/Thu, publish 27 Nov on Gianni's typed go.
- A fix that misses the cut-off moves to 0.39.2 (4 Dec) unless Gianni says otherwise.

Scope tracker (owner thread -> items; status updated by the release thread):
| stream | owner thread | items | status |
|---|---|---|---|
| audit | Audit 0.39 for bugs and polish | 09 wall red dot + out-of-breath stutter (READY in audit-0391); 10, 11 (READY); items 56-60; blocked steps; lowered-weapon firing; callout icons through walls + off switch | 09-11 ready; rest asked 18:1xZ |
| engine | Plan engine upgrades for stunning visuals | grass/fence shadow flicker, floating player shadows, per-frame buffer, GPU crash reports (dx12-fixes READY); sky flicker on Ultra; brightness retune 1.3 -> 1.0; stray wall shadows | dx12-fixes ready; rest asked |
| launcher/UI | Overhaul the in-game UI for 0.40 | launcher patch-note titles + hero text overlap (launcher-patchnotes, 3.0.3) | gated, PC look pending |
| muzzle flash | Fix muzzle flash placement on every gun | muzzle flash placement on every gun | kit folder started, no SUMMARY yet |
| community maps | Recover TC:E community maps | Villa 2.1 title (tacmap-title READY); Chlite sky = no fix (pre-existing log line) | done |

Kits go in /mnt/project-files/integ0391/kits/<name>/ with <name>.md + SUMMARY.md (gate on the published 0.39.0 source zip).

| kit | owner thread | where now | notes |
|---|---|---|---|
| dx12-fixes-0391 | Plan engine upgrades for stunning visuals | /mnt/project-files/engine-visuals/kits/dx12-fixes-0391/ | Gianni 15:02-15:03Z: grass/fence shadow flicker, upload buffer grows instead of dropping draws, DRED crash report. On 0.39.0 apply ONLY patches/03 (3166a272). Gate c615435e. check_hlsl + DX12 look on PC. |
| audit-0391 (09 wall dot + out-of-breath prediction, 10 team change / match command answers, 11 competitive match texts) | Audit 0.39 for bugs and polish | /mnt/project-files/integ0391/kits/audit-0391/ | 09: Gianni card 15:28Z "Keep it for 0.39.1"; 10 and 11 found after it (passes 7-8). Client AND server (09: stance stat bits 0x10/0x20; 11: one line, no join line at side swaps). GATE PASSED 17:48Z on FINAL 0.39.0 source (029a45ad), all green. READY. PC look: wall dot, out of breath, team change popup. |
| (known, 0.40) Shozen bots never take the flag; Chlite bots never plant (no route to sites) | Make bots smarter in matches (navfix-040) | /mnt/project-files/integ040/kits/bot-navfix.md | Not a 0.39.1 kit from the community thread: causes are the 8192 nav-node cap on Shozen and Chlite/Villa NOPATH spots, both already in the bots thread's 0.40 navfix kit (built on botflags). Keep Shozen off Flag Capture and Chlite off Bomb in rotations until then. |
| tacmap-title | Recover TC:E community maps | /mnt/project-files/integ0391/kits/tacmap-title/ | cgame only, one file: tcp_mapvote_cg.h mapVotePretty reads the map data `title` (covers tactical map, scoreboard, vote via audit-polish 01). Patch 0ad804d1, base = sandbox37 + audit-polish + parallax-repair 01; GATE PASSED 17:25Z on FINAL 0.39.0 source (f965cf67), all green. READY. |
| (no fix) Chlite: missing textures/coroner_skies/sunset02_dn.tga | Recover TC:E community maps | - | Checked: pre-existing in original TC:E. Shader coroner_skies/dustsky is in stock pak2.pk3, and stock pak1.pk3 ships sunset02 bk/ft/lf/rt/up but never had _dn. The Chlite pk3 has no sky files. Down face is below the world, never seen. Log line only; leave it. |
| launcher-patchnotes (Launcher 3.0.3) | Overhaul the in-game UI for 0.40 | /mnt/project-files/integ0391/kits/launcher-patchnotes/ | Gianni 17:21Z: Play page Patch notes cards all read "TRUECOMBAT: PLATINUM V..."; hero story fade left ghost text. Cards now "UPDATE 0.39.0" + codename line; story change fades words out then in. Launcher only (release_src/platinum_*.h), 3.0.2 -> 3.0.3. GATE PASSED 17:36Z on FINAL 0.39.0 source (d68b2190). PC look pending. |
