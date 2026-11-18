# Kit: audit-0391d for 0.39.1 (small steps that block the player)

Owner: thread "Audit 0.39 for bugs and polish". For: the 0.39.1 release thread.
Gianni 18:01Z: "Some small steps and stairs seem to be blocked. You get blocked when trying to [walk] over it."

Base: the FINAL 0.39.0 source zip. Applies AFTER audit-0391 (09-11), audit-0391b (12), audit-0391c (13).

| Patch | Files | What |
|---|---|---|
| 14-steps-low-headroom.patch | tcp_move.c (shared: server movement + client prediction), tests/step_probe.c (new, test only) | see below |

Cause (found with a movement probe that walks the real tcp_move.c into boxes): open steps up to 18 u and open stairs
always worked, at 125, 250, 500 and 1000 fps; the 0.39.0 slope fix plays no part. The step was dropped whenever
anything solid was within 18 u above the head: the code lifted the player 18 u to try the step and gave up if that
lift was cut short. So a 4-9 u step or threshold under a ceiling or door frame 80-87 u up (head at 70 u) stopped the
player dead, although he fits after the step.
Fix: as ET's PM_StepSlideMove, the step is tried with the room there is; and when the 18 u try gets no further (the
raised box hits a low frame over the step), a 9 u try follows. Steps over 18 u and frames lower than the player still
block. Server and client run the same code (no prediction change).
Probe results (tests/step_probe.c, gcc -DMODLIB -I <etlegacy/src> step_probe.c ../native/tcp_move.c -lm): PASS;
on the 0.39.0 code it fails "step under a low ceiling". Existing native_move_probe and slope_probe still pass.
Not checked on a real map spot: Gianni did not say where; if a step still blocks after this, the spot (map + where)
is the next thing to look at.

Gate: run with 09-15 together on the FINAL zip: KIT GATE PASSED 2026-11-18T18:40:47Z, SUMMARY.md here.

Patch notes (player wording): "Small steps and thresholds under low ceilings and door frames no longer stop you."
