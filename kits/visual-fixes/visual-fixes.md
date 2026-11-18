# visual-fixes (0.39.1)

Owner thread: Plan engine upgrades for stunning visuals. Gianni's reports of 18 Nov 18:01Z and 18:09Z.

GATE PASSED 2026-11-18T18:27:28Z on the FINAL 0.39.0 source zip (gate kit = 03 + 04 + 05; SUMMARY.md here). 04 sha dc1bdc68, 05 sha 0e2c5990.

Apply AFTER dx12-fixes patch 03 (04 sits on top of 03 in dx12_core.cpp). Order: 03, 04, 05.
Checked together with audit-0391 09-11, stance-smooth 01, muzzle-flash 01 (git apply, any of those before 05): all apply clean.
05 uses 1-line context on purpose so it does not collide with stance-smooth and muzzle-flash in tcp_player_models.h.

## 04-sky-brightness-0391.patch (renderer)

1. Brightness default 1.3 -> 1.0 (Gianni: "looks a lot better on 1.0 ... more darker areas, with lit areas").
   - renderer_vk/tr_init.c (DX12 build, file is on the export_patch EXISTING list): r_gamma is registered with "1.0"
     just before R_Register, so 1.0 becomes the reset value. tr_cvars.c is untouched (not on the list).
   - renderer/tr_cvars.c (OpenGL fallback): default "1.0".
   - Players who never moved the slider get 1.0 (r_gamma is CVAR_ARCHIVE_ND, the default is never written to the
     config). A brightness a player set keeps its value. Launcher "Keep in-game calibration" now means 1.0.
2. Sky flicker on Ultra: the Ultra-only sun shafts and sun glare (0.39.0, composite pass) tested "is this pixel sky"
   one pixel at a time on the jittered depth, after anti-aliasing. Wires, antennas and roof edges near the sun flipped
   between sky and not-sky every frame, so the shafts and the glare pulsed over the sky. Now SkyCover() = open-sky
   fraction of a 5x5 px footprint (4 taps), used by the shaft march, the self term and the disc visibility; the disc
   visibility uses 13 footprints on a 1.5% and a 3% ring instead of 12 single pixels on a 1% ring.
   Cost: Ultra only, inside 1.4 view heights of the sun.
   If Gianni still sees flicker: `r_dx12SunShafts 0; r_dx12SunGlare 0` tells whether it is this pass.

## 05-no-shadow-when-dead-0391.patch (cgame)

"When dead and spectating, you can still see your own shadow." The local body (self 1) is hidden from the eye view
but kept as a sun shadow caster, and a followed teammate is drawn the same way, so a body shadow stayed under the
camera after death (death camera) and while following a teammate.
- pmAddPlayer self 2 = hidden like self 1, plus RF_FIRST_PERSON so sun shadow views skip it (renderer rule in
  tr_main.c: shadow views never take RF_FIRST_PERSON entities; RF_THIRD_PERSON | RF_FIRST_PERSON is drawn nowhere).
  No blob shadow (cg_shadows 1) either.
- Local body: self 2 when dead (health <= 0 or PM_DEAD) and not following; alive stays self 1 (own shadow kept).
- Followed teammate: self 2 (was 1). Other players still see that teammate's shadow; only the spectator's own
  camera view loses the body shadow under it. Nothing hides an enemy.
- After the death camera hands over to the follow camera, your own corpse is drawn as before (self 0) with its shadow.

## Not in this kit (0.39.2)

- Floating dark rectangles on walls (Railhouse). The Railhouse roof skylights are 72 func_explosive glass panes
  (textures/bruce/window_b1_nightlight_trans, blended + depthwrite). The shadow caster filter skips blended draws, so
  in code they should not cast; needs a PC look with r_dx12ContactShadows 0 / r_dx12Shadows 1 to pin the source.

## PC checks (Ultra)

- Brightness: fresh config shows Brightness 1.0; a config with r_gamma set keeps it.
- Northport + Railhouse, Ultra, look near the sun past wires and roof edges: no pulsing glare or shafts.
- Die with teammates alive: death camera shows no body shadow at the camera; follow camera: no shadow under the
  camera; alive: own shadow still there. Other players see the followed teammate's shadow.

## Patch notes lines (public)

- Brightness now defaults to 1.0 for a darker, more defined image (your own brightness setting is kept).
- Fixed sky flicker around the sun on Ultra.
- Your shadow no longer stays on screen after you die or while spectating a teammate.
