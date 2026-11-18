# Occasional tracer rounds (0.39.2)

Thread "Improve the game's particle effects". Gianni 2026-11-18 19:12Z (via the coordinator): "I was wondering if tracers is an option. Not continous tracer rounds, but more at times, similar to real life." 19:19Z asked for the next patch, 19:20Z: "Do for .2". 19:52Z: "Tweak it further." (comet head, ignition, ricochets). 20:11Z: "Make them for every weapon. Don't make it over the top. Making it for every weapon makes it fair for all." and "I want the tracers to glow up surfaces too" (this version). Gated on the FINAL 0.39.0 source; re-gate on the 0.39.1 source once that is published.

## 1. Kit
Folder: /mnt/project-files/integ0392/kits/tracers/

| file | use |
|---|---|
| patches/01-tracers-0392.patch | cgame only plus one acReleasePaks row. Adds `game_src/native/tcp_tracer_cg.h`; small hooks in `tcp_cgame.c` (prototype, include, shot loop, own shots, scene call, round wipe, console command) and `tcp_impacts.h` (impact point). One row in `reference/etlegacy/src/server/sv_anticheat.c` acReleasePaks: `tcetest/zz_platinum_tracer` -1987474557. `git apply` at the source root. |
| paks/zz_platinum_tracer.pk3 | NEW base pak for tcetest (17 KB): `gfx/platinum/tracer.tga` (128x32 white streak, alpha gives the shape) and `scripts/platinum_tracer.shader` (additive, vertex colour, nofog). Pak checksum -1987474557. Client only: the server never reads it. Not a remaster pak, so Classic and Remastered both load it. Add it to the installer/update file list and the EAC file catalogue like the other zz_platinum client paks. Built deterministically (zip -X -D, fixed dates). |

sha256 of both files: SUMMARY.md. No cvar, no UI pak change, no server or protocol change.

## 2. What it does
- One round in five is a tracer, per shooter, picked from the shooter's shot counter (`effect1Time` for other players, the own `TCP_STAT_SHOTS`, both taken mod 65536). Every client sees the same rounds glow. The shooter's number shifts the phase, so two players firing together do not glow in step.
- Weapons: every firearm, same one in five: pistols, akimbo, SMGs, rifles, shotguns, snipers, suppressed weapons too (Gianni: fair for all). A shotgun shot shows one tracer, not one per pellet. Knife and grenades have none.
- Look: an orange-red comet, about 300 units long, travelling at 13000 units/s: a bright, slightly flickering head (burning compound) and a tail that fades out behind it, in a soft red halo. Then a 70 ms afterglow at the end. At least about 1.4 px wide at any distance, so far tracers still read. Whole life about 0.1 to 0.25 s.
- Ignition: like real tracer compound it does not glow at the muzzle. It is dark for the first 70 units and lights up over the next 260, so no laser line comes out of the barrel.
- End: at the impact the server reported for that shooter (spread, player hits), or without one at the first wall on the aim line. A round that hits a player stops there. For a round that goes through a wall, the entry point counts.
- Ricochet: a round that strikes the world at a shallow angle sometimes glances off: 40 percent below about 20 degrees, 12 percent up to about 37 degrees, never steeper or off a player or the sky. It flies off 180 to 600 units, mirrored off the surface with lost speed, some scatter and a kick upward, at 60 percent brightness, and stops at the next wall. Chance and direction come from the shot number and the surface, so every client draws the same ricochet. Visual only: the server's bullet does not ricochet.
- Surface glow: the burning head carries a small orange dynamic light (radius about 100, soft), so walls, floor and grass it passes glow briefly; also along a ricochet, dimmer. At most the 6 nearest tracers light at once. Kept subtle on purpose (Gianni: not over the top).
- Seen by everyone, from every point of view: other players' tracers start at their third-person muzzle; your own and the player you follow start at the first-person muzzle. Not drawn in the round-end replay.
- Draws from its own pool (64 rounds) and poly buffers; `cg_particles` does not change it.

## 3. Fairness
- Same for everyone: every firearm, both teams, no cvar, no client option, same rounds on every client, same look in Classic and Remastered.
- A tracer shows where a shot came from, for every weapon alike (Gianni's call, 20:11Z: every weapon makes it fair for all).
- The surface glow is a dynamic light: a player with dynamic lights off in the renderer sees the streak but not the glow on walls. The streak itself always draws.
- A client that deletes the pak sees no tracers (shader missing, nothing drawn); it gains nothing.

## 4. Cvars and commands
- No new cvars.
- `trTest [n] [distance] [slow] [ground]` is a developer preview on your own screen: n tracers (default 3) from beside the camera across the view; `slow` 0.01..1 slows them for a screenshot; `ground` sends them in from the far side to glance off the floor ahead (shows ricochets).

## 5. Checked (cloud OpenGL client, Village)
- `trTest` streaks at 0.03x speed: orange-red with a hot core, tapered tail.
- `trTest 6 380 0.03 ground`: rounds glanced off the floor and flew off past the fence, dimmer; grass and tree trunk lit orange where the heads passed (6 at once, slowed; in play one or two at a time).
- Own M4 fire, 8 rounds: 1 tracer (1 in 5 phase), from the first-person muzzle.
- 8 bots fighting, spectator, about 40 s: 44 tracers from other players.
- Build on the FINAL 0.39.0 source: no warnings.

## 6. Test checklist
`map | renderer | steps | pass rule | shot`
- obj_village | DX12 | watch bots fight from the side and from behind a shooter | roughly every fifth round of every gun shows a short orange-red streak, one per shotgun shot | y
- obj_railhouse | DX12 | tracers along a dark corridor wall | the wall glows softly where the head passes, not a flood of light | y
- obj_village | DX12 | fire the M4 full auto at a wall | own tracers light up a little past the muzzle, end at the impact | y
- obj_village | DX12 | fire the M4 low along a floor or wall at a shallow angle | some tracers glance off and fly on dimmer; none off a head-on hit | y
- obj_village | either | same match on two clients | same rounds glow on both | n
- any | either | Classic and Remastered | identical tracers | n
- any | n/a | client with the new pak on an official server | no AC kick (row in patch 01) | n

Patch notes line: "Every gun now fires an occasional tracer round, about one in five, the same for every player. Tracers light up just past the muzzle, glow on the walls they pass and sometimes ricochet off hard surfaces at a shallow angle."
