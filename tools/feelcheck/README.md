# Feel check

Proves that a change leaves movement, timing and hits exactly as they were. Engine work (renderer,
threading, asset pipeline) must never change how the game plays, and this is the test that holds
every such change to that.

```
tools/feelcheck/feel-check.sh <base> <kit folder | -> ["obj_village obj_snow"] [seconds per map]
```

- `<base>`: a release tag (`v0.39.4-sandbox41`), a source zip or a source folder, as `tools/ci/kit-gate.sh`.
- `<kit folder>`: `patches/*.patch` (applied in name order) and optionally `files/`, as a kit-gate kit.
  `-` checks the base against itself.
- Result: `feel-check/SUMMARY.md`, exit 0 only when every map matches.

## How it works

1. Both trees get the trace hook (`feeltrace.py` puts `feeltrace.c` into `sv_main.c`, found by code so
   it still applies after engine kits change that file) and `fakeclock.c` (linked into the game module) and are built as Linux dedicated servers. Neither file ever goes into a release build.
2. Each build plays the same seeded bot match per map (`bot_seed`, fixed weather, 12 bots, 128 Hz).
   With `sv_feelTrace` set, every server frame is exactly 8 ms of game time and the game module's
   clock advances per call instead of in real time, so a run no longer depends on how fast the
   machine is.
3. After every game frame the server writes each active player's state (position, velocity, view
   angles, movement and entity flags, weapon, weapon state, ammo, health, events, plus a hash of the
   whole player state) and a hash of every other linked entity (grenades, doors, dropped weapons).
4. The base plays twice. If those two runs differ, the map fails as "not deterministic", because the
   test itself could not be trusted there. Then the kit build's trace must match the base frame for
   frame; `compare.py` names the first frame, player and field that differs.

Because bots react to everything around them, any change to movement, spread, recoil, damage or
timing spreads to every later frame within seconds, so a match that stays identical for the whole
run means the change played exactly like the base.

## Environment

`WORK` (default `./feel-check`), `DATA_TAG` (game data release; default latest, or the base tag),
`DATA` (game data folder, reused between runs), `BOTS` (12), `SEED` (1), `PORT` (28970).

## Proven on 0.39.4

| Test | Result |
| --- | --- |
| 0.39.4 against itself, all six official maps, 90 s each | identical on every map, 11,520 frames each, 615-851 hits per map |
| Sprint 0.8 % faster (one constant in `tcp_move.c`), Village | caught at frame 295 (3.0 s), the first sprinting frame: velocity 136.5 expected, 137.6 found |

A full six-map run takes about 12 minutes in a cloud container (each map plays twice in real time).
