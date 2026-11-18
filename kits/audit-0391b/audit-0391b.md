# Kit: audit-0391b for 0.39.1 (side-swap spawn spread)

Owner: thread "Audit 0.39 for bugs and polish". For: the 0.39.1 release thread.
Rule: Gianni 18:08Z "I want all bugfixies in 0.39.1", "As soon as possible. Today preferably."

Base: the FINAL 0.39.0 source zip (integ039/base/...-FINAL-source.zip). Applies AFTER kit audit-0391 (09-11):
12 touches the same matchSwapSides lines as 11.

| Patch | Files | What |
|---|---|---|
| 12-swap-spawn-spread.patch | tcp_game.c (server), tcp_match.h | Competitive match side swap: all players were respawned in one frame and several landed on the same spawn spot (stuck inside each other). The swap now spreads players over free spots; spawning outside a swap is unchanged. |

Server module (qagame) only. No client change, no new cvar, no pak.

Gate: SUMMARY.md here, run with 09-12 together on the FINAL zip, KIT GATE PASSED 2026-11-18T18:10:33Z.
Seen on screen: competitive match on Village with 12 bots, each side swap gave no stacked players (doc item 61).

Patch notes (player wording): "Competitive matches: players no longer spawn inside each other after the side swap."
