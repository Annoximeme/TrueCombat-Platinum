# Kit: audit-0391c for 0.39.1 (callout icons through walls + off switch)

Owner: thread "Audit 0.39 for bugs and polish". For: the 0.39.1 release thread.
Gianni 18:06Z: "when doing callouts, I fear it is prone to exploits and information you shouldn't know at times since
the icons above heads show through walls." 18:07Z: "Also make an option to turn it off."

Base: the FINAL 0.39.0 source zip. Applies AFTER audit-0391 (09-11) and audit-0391b (12).

| Patch | Files | What |
|---|---|---|
| 13-voice-icons-team-only.patch | tcp_voice_cg.h (client), tcp_voice_g.h + tcp_game.c (server) | see below |

What was wrong: the voice icon over a speaker's head (radio callouts, combat voice lines like "Reloading" or "Taking
fire", and voice chat) was drawn over every player in the snapshot, enemies included, and it draws through walls. An
enemy's global callout or combat line therefore showed where he stood. The server also sent every combat voice line
(speaker slot + line) to every player on the map.

Fix:
- Client: the icon only shows over team mates of the player you watch. Free spectators (casters) see all; free-for-all
  and practice players see none.
- Server setting `g_voiceSprites` (serverinfo, default 1): 0 hides the icons for everyone (for Ranked if wanted).
- Player setting `cg_voiceSprites` (archived, default 1): 0 hides them for yourself. Console only for now: the Options
  menu lives in the paks (a menu row is a UI-thread item).
- Server: combat voice lines (tcp_vpos) now go only to players within 1600 u of the speaker (the sound fades out by
  1250 u) and to players who are not alive in the round. Radio callouts (vsay / vsay_team) are unchanged: global ones
  still reach everyone as chat text, team ones only the team.
No new pak, no menu file. Does not touch the 0.40 pings (tcp_ping*, already team-only).

Gate: SUMMARY.md here, run with 09-13 together on the FINAL zip, KIT GATE PASSED 2026-11-18T18:25:20Z (kit checksum
3372edf7f0ba98fe; bots: Village 1741 hits / Snow 1263 hits, 12 bots each).

Patch notes (player wording): "Voice and callout icons over heads now only show over your own team mates, so they can
no longer give away an enemy's position through walls. Servers can turn them off completely, and players can hide
them with cg_voiceSprites 0."
