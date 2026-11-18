# Kit: audit-0391e for 0.39.1 (no firing while the gun is pulled back at a wall)

Owner: thread "Audit 0.39 for bugs and polish". For: the 0.39.1 release thread.
Gianni 18:01Z: "When facing a wall, your weapon now faces down but you can still shoot in front of you. When this
happens, you shouldn't be able to shoot at all. Tweak this further until it feels right."

Base: the FINAL 0.39.0 source zip. Applies AFTER audit-0391 (09-11), -0391b (12), -0391c (13), -0391d (14).

| Patch | Files | What |
|---|---|---|
| 15-wall-holds-fire.patch | tcp_lagpredict.c/.h (shared), tcp_game.c (server), tcp_cgame.c, tcp_lagclient.h, tcp_viewfx.h (client) | see below |

- New shared TCP_MuzzleBlocked: a 6 u box from the shot origin (eye, with the lean offset the server's fire() uses)
  20 u along the view; solid world and doors/movers only (not players, not player clip). While it hits, the gun does
  not fire and stays held 200 ms after the wall is clear (while it comes back up). The server think and the client's
  shot prediction both apply it, so no predicted shots or ammo that the server then takes back.
- Gun pose (client): the 0.38.0 wall pose now reaches full exactly where firing stops (20 u, was ~16 u), and while it
  cannot fire the gun is fully pulled back even when aimed (aimed it was a third of the pose, so the gun still
  pointed at the wall).
- Grenades, knife and dynamite are not affected.
Checked in a live match (Harbour, cloud client, shot log): open fire 5 shots; hip at the wall 0 shots; aimed at the
wall 0 shots; backed off 11 shots; walking back from the wall with the trigger held: firing resumes at once.
Known and unchanged (doc item 55, question to Gianni): at full pose from the hip the gun is off the screen.

Gate: run with 09-15 together on the FINAL zip: KIT GATE PASSED 2026-11-18T18:40:47Z, SUMMARY.md here.

Patch notes (player wording): "You can no longer fire while your weapon is pulled back against a wall."
