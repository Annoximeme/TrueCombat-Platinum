# Kit stairs-curbs (0.39.2 or 0.39.3): walk up stairs and curbs without jumping

Thread "Smooth walking up stairs and curbs", 2026-11-18. Gianni 22:35Z: "There's still an issue with walking up stairs
and borders where it goes from the street to a walkpath for example." 22:35Z: "You have to jump to get on it."

Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (integ0391/base). Patch 01-stairs-curbs-0392.patch.
Rebases on audit-0391d (patch 14, already in 0.39.1). Touches only `stepPlain` in game_src/native/tcp_move.c
(server qagame + cgame prediction, same file), plus tests.

## Cause
`stepPlain` threw away a raised step try that had not got past the step face yet, and kept the flat move, whose
slide had already stopped the velocity at the face. Each next frame only rebuilt a few u/s of speed, so the raised
try moved a few hundredths of a unit per frame and never got past the 0.125 u gap the engine trace leaves before a
face. Frame-rate dependent: at 125 fps most steps still worked from the walking speed alone, at 250 fps and up the
player stood at the step until they jumped. Rounded step edges (stair nosing, curbs) had a second trap: the raised try
came down on the steep bevel and was dropped.

## Fix
1. A raised try that gets further than the flat move with nothing under it within the lift is taken (as ET's
   PM_StepSlideMove does), keeping its own vertical speed. Speed builds up and the next frame gets over the step.
2. A raised try that lands on a steep bevel at a step edge is tried again 1.5 u along the move (only when the frame's
   move is under 1.5 u).
3. A flat move that got all the way skips the step tries (same result as before, fewer traces).

## Evidence
- Real-map probe (new game_src/tests/stairs_map_probe.c, engine collision code, every step 2-18 u that a player can
  stand at, walked from a standstill): map-probe-before.txt vs map-probe-after.txt. Before: 0.4-7 % need a jump at
  125 fps, 27-73 % at 250, 52-86 % at 500, 91-100 % at 1000. After: 0 on 8 of 11 maps at every frame rate; the few
  left (Delta 17, Harbour 1, Village 1, Northport 2, Railhouse 1, Stadtrand 1) are probe spots where the player gets up
  and then stops against the next obstacle, or stands half on a ledge, identical at every frame rate.
- CQB movement (g_experimental corner slide) was worse before (Harbour 60 % at 125 fps); after: same as above.
- Steps over 18 u still block; 45 degree ramps at the walkable limit can now be walked onto at every frame rate (before:
  only at some).
- step_probe: new cases, from a standstill at the face, 2-18 u, at 8/4/2/1 ms; sweep now follows cm_trace.c
  (SURFACE_CLIP_EPSILON 0.125). Old code FAILS ("step 2 from a standstill at the face at 4 ms"), new passes.
- Unchanged PASS old and new: native_move_probe, slope_probe, fps_fairness_probe, native_vault_probe, cqb_mech_probe,
  cqb_rules_probe, native_content_probe, native_prediction_probe.
- View: the existing step smoothing (tcp_viewfx.h, 200 ms) covers the step-ups, no camera change needed.

## PC look
Any map, 250 fps or higher: walk (no jump) up stairs and onto the pavement from the street, head-on and at an angle,
standing and crouched, and from a standstill against the curb. Check bots still path normally.

## Patch notes line
- Walking up stairs and onto curbs and pavements works at every frame rate again. At high frame rates players could get
  stuck at the edge and had to jump.
