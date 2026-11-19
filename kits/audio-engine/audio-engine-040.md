# Kit audio-engine-040: audio engine upgrades for 0.40.0

Gianni 18 Nov 23:25Z "Add it all" (7 engine items, plan doc "Platinum Acoustics", section Audio engine upgrades),
release picked 23:26Z: engine upgrades in 0.40.0 (gate 18 Dec). OpenAL Soft only, no Steam Audio.
Everything sits behind the Remastered option (cl_remaster, from the remaster switch kit; unset counts as
Remastered): with cl_remaster 0 (Classic) the engine sound is exactly 0.39. Applies on the 0.39.2 source, and on top of the 0.39.3 weapon sounds kit (its patch 03 touches the same file; offsets only).

## 01 Shooter's room reverb (snd_openal.c)

Before: one EFX reverb for every sound, tuned to the listener's surroundings (TCP_SpatialReverb). A rifle fired
inside a warehouse sounded dry to a player in the street.

Now:
- Context asks for 3 auxiliary sends (was 2). Send 1 = listener's room (as before), send 2 = shooter's room.
- 3 extra reverb slots ("zones"). Gunfire and blasts (TCP_SfxClass GUNFIRE/BLAST) more than 384 units away get
  a send into a zone tuned to the room at the source: same 14-ray probe as the listener's room
  (TCP_RoomProbe, now shared), cached per 128-unit cell (256 cells).
- A zoned source's listener-room send drops to 40 %; its shooter's-room send is muffled by the same walls as the
  dry sound (gain 1-0.35 occ, HF (1-0.75 occ) x air absorption), so a hall heard through a doorway blooms out
  muffled.
- Not zoned when the shooter's room is the same kind of space as the listener's (distance < 0.35:
  2 x |open diff| + |ln size ratio|).
- A zone is retuned only after its last sound rang out (decay + 0.6 s); until then the closest tuned zone
  is shared.
- s_alReverb 0 silences the zones too. New cvar s_alSourceReverb (default 1, archive) turns only this off.
- Refactor: TCP_RoomParams (room -> reverb), TCP_ReverbWrite (effect + slot), TCP_RoomProbe; a listener probe
  from inside a wall keeps the last room instead of morphing toward nonsense.
- Debug: s_alSpatialDebug 1 prints TCP_AUDIO_ZONES zones=3 assigns retunes shares probes skips decay;
  s_alSpatialInfo shows zones= and sourcereverb=.
- Falls back to the 0.39 behaviour when the device gives fewer than 3 sends.

PC listen: obj_village, a bot firing inside the big barn while you stand in the street (should boom out of the
barn, muffled), then swap; s_alSourceReverb 0/1 A/B; s_alSpatialDebug 1 shows assigns climbing.

## 02 Doorways (snd_openal.c)

Before: a blocked sound was muffled in place; four probes next to the source softened it near openings, but it
was still heard straight through the wall, from the source's own direction.

Now (s_alPortals, default 1, archive): a blocked sound (occlusion > 0.3) looks for the opening it really
reaches the listener through. 32 candidate points (8 directions x 4 rings: 35 % and 70 % of the distance
around the listener, 35 % and 15 % around the source, at mid height) are tested for a clear listener leg and a
clear source leg; the shortest detour wins, if it is under 2.2x the straight distance.
- Heard from the opening's direction, at the detour's length (OpenAL distance falloff makes it a little
  quieter), smoothed over ~120 ms so nothing jumps; glides back to the true position when the line clears.
- Muffling through an opening: 0.15 (straight through a door) to 0.6 (dog-leg), instead of up to 1.0 through
  masonry; the shooter's-room send (01) follows the same occlusion.
- Searched at the start of a non-looping blocked sound (heard through the door from its first sample) and every
  250 ms while it plays and stays blocked; at most 4 searches a frame. Early outs before tracing keep it
  cheap (a candidate longer than the best so far costs no traces).
- Debug: TCP_AUDIO_PORTALS searches found active (s_alSpatialDebug 1).

PC listen: obj_village, stand in a house with one door; a bot firing outside should come from the door
side, not through the wall; s_alPortals 0/1 A/B.

## 03 Loudness-priority mix (snd_openal.c)

Plan: "the loudest event in the scene sets a short window, and quieter sounds below it are lowered for a
moment and come back smoothly ... footsteps are never pushed under the level they have today."

- The loudest fresh (150 ms) gunshot or blast, by its perceived level (gain x wall muffling x OpenAL
  distance falloff; blasts count double), is held with a ~350 ms fall.
- Other gunfire, impacts, debris, casings and other one-shots more than 12 dB under it step back by up to 4 dB
  (linear in how far under: 0 dB at -12 dB, -4 dB at silence), 30 ms down, 300 ms back.
- Never touched: footsteps, near-miss snaps, tinnitus, voice, music, streams, menus, ambience loops (they keep
  their own ducking), and every local (own) sound.
- Same rule for every player. s_alMixPriority (default 1, archive) or Classic turns it off.
- Debug: TCP_AUDIO_PRIORITY loud ducked.

PC listen: 8 bots on obj_village, fire a full magazine near a distant firefight: distant shots and impacts
dip under your shots and come back between them; footsteps nearby stay exactly as loud.

## 04 Wall slaps and travel delay (snd_openal.c)

Plan: "Early reflections from nearby walls (7 traces within 40 m), sound travel delay of about 0.3 s per 100 m,
and the supersonic crack arriving before the report at range."

- Travel delay: gunfire and blasts more than 400 units away start after distance / 13504 units/s (1 unit =
  1 inch; ~0.3 s per 100 m) from a 96-entry queue (TCP_DelayFrame at the top of S_AL_Update). The cgame's
  near-miss crack still plays when the bullet passes, so at range the crack lands before the report.
  FAIRNESS: applies to every player, Classic included, and s_alTravelDelay is CVAR_CHEAT (default 1), so
  nobody can hear shots earlier than anyone else.
- Wall slaps (Remastered only, s_alWallSlaps default 1, archive): 7 traces around the listener (6 horizontal
  + up, within 1575 units = 40 m, refreshed every 150 ms). Each gunshot or blast, own shots included, throws
  back up to two copies from the strongest walls: delayed by the extra path, at most 0.32 (-10 dB) of the
  direct sound and lower with the extra distance (OpenAL's falloff over the wall's short distance is
  compensated), only when the shooter can reach the wall, never under 8 ms (fuses with the direct sound).
  Limits: one set per shooter per 90 ms, six slaps per 100 ms.
- Queued sounds are dropped by S_AL_StopAllSounds and a sound restart.
- Debug: TCP_AUDIO_TIMING delayed slaps queue dropped.

PC listen: fire in the obj_village alley (two slaps, short), then in the open field (none); a bot 100 m away:
crack, then the report ~0.3 s later.

## 05 More voices, 48 kHz, smarter stealing (snd_openal.c)
- s_alSources default 192 -> 240 (old saved 96 and 192 migrate to 240).
- s_alMixRate (default 48000, archive, latch): sets ALC_FREQUENCY when Remastered; Classic keeps the device default.
- When all voices are busy and Remastered, the voice stolen is the one heard quietest right now
  (TCP_Perceived: level x wall muffling x distance falloff), not the oldest.
- Not done: streaming of long ambience beds (deferred, no gain at 240 voices).

## 06 Ears react (cgame: tcp_audio.h, tcp_cgame.c; needs the 0.39.3 weapon-sounds kit)
- Remastered only (cl_remaster). An unsuppressed shot fired by someone else within 160 units of you dulls your
  hearing briefly and leaves a faint ring: strength by calibre (pistol .35, SMG .4, rifle .5, sniper and shotgun
  .6), less with distance (40 % at 160 units); recovery 1 to 3 s.
- Feeds the existing blast muffle (s_alConcussion via drawStun) capped at .45 (a blast reaches 1). The ring is
  the soft tinnitus loop at no more than 18 % of a blast's, and only when no blast ring plays.
- Own shots never count. cg_concussionMuffle 0 turns it off with the blast muffle; cg_tinnitus 0 turns off the ring.

## 07 Footsteps through the same room logic (snd_openal.c)
- Footsteps more than 384 units away ring in the walker's room (a zone send like gunfire), at 60 % of the
  gunfire wet level, 80 % highs. They already take the doorway path (02) and are already never ducked (03).
- FAIRNESS: only the wet send is added. Footstep level, range, falloff, occlusion and doorway path are
  unchanged and the same for every player.

PC listen (05-07): Remastered, stand beside a bot firing a rifle (short dull + faint ring, back in ~2 s);
a bot running down the obj_village hall 600 units away (footsteps carry that hall's echo).
