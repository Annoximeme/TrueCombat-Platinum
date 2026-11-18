# light-contrast (0.39.2)

Owner thread: Plan engine upgrades for stunning visuals (renamed "Make map lighting darker with real light and shadow").
Gianni 18 Nov 18:27Z / 18:30Z: "make the world look more darker and lit ... actual darkness in spots where it's
supposed to be dark, and places or areas where everything gets lit up by nearby lights or the sun or moon.
Brightness stays at 1.0".

RE-GATED on the 0.39.1 source zip (TrueCombat-Platinum-0.39.1-sandbox38-source.zip, 65f45c70): 06 alone, see SUMMARY.md.
Earlier: GATE PASSED 2026-11-18T18:46:42Z (03+04+05+06 on the FINAL 0.39.0 zip, kit checksum dc316379).

Patch 06-light-contrast-0392.patch (sha 9a8b27a0). Touches only renderer/tr_bsp.c, renderer_vk/tr_bsp.c (on the
export_patch EXISTING list) and the new renderercommon/tcp_light_contrast.h, so it applies on the FINAL 0.39.0 source
alone or on top of dx12-fixes 03 + visual-fixes 04/05. Gate: 03 + 04 + 05 + 06 on the FINAL 0.39.0 zip (SUMMARY.md here).

## What it does

Why the maps look flat: the TC:E lightmaps have a baked minimum (Railhouse/Stadtrand: no texel under ~24/255, the
5th percentile), from hidden fill lights and _minlight. With the x4 overbright shift (r_mapOverBrightBits 2,
r_overBrightBits 0) that floor is still 37 % of full light, while everything sunlit clips at 100 %.
Lightmap stats (luma of lm_*.tga, percentiles 5/25/50/75/95): Northport 0/38/113/176/242, Railhouse 24/26/57/86/159,
Snow 0/0/25/64/161, Village 0/24/129/227/250, Delta 0/28/57/91/185, Stadtrand 24/39/112/188/251.

At map load, in R_ColorShiftLightingBytes (after the shift, before the clip), light below full brightness becomes
L * L^0.8, never below 0.45 x L. Full light and brighter is unchanged. Examples: the 37 % floor -> 17 %, 60 % -> 40 %,
90 % -> 83 %. Same curve for lightmaps (internal and external, before the 0.39.0 smoothing) and vertex light, so
everything stays matched. Light grid (players, weapons, props): ambient gets a gentle curve (k x 0.35, at least 75 %
kept), directed light untouched, so players stay readable in dark corners (fair play).

Cvar r_lightContrast 0..1.5 (default 1), CVAR_CHEAT | CVAR_LATCH: everyone on a server sees the same light; with
sv_cheats (devmap) it can be set for tuning, vid_restart to apply.

Cost: load time only. Works in DX12 and OpenGL.

## Not proven yet (needs the PC)

- The look itself: Ultra before/after on Railhouse, Village, Northport, Snow, Delta, Stadtrand (r_lightContrast 0 vs 1).
- That runtime shift is 2 (r_mapOverBrightBits 2 - tr.overbrightBits 0). If a config runs r_overBrightBits 1, the
  shift is 1 and the curve sees half the light: darker than intended. Check `r_overBrightBits` in the PC config.
- DX12 sun-shadow source from the light grid (maps without q3map_sun) reads directed vs ambient; a lower ambient can
  make more cells count as sunlit (shadows slightly stronger). Check Railhouse and Snow.

## Next (0.40)

Sun/moon pools on High/Ultra (static sun map: sunlit spots brighter, sun-shadowed side darker), lamp pools from the
0.40 lamp lights, per-map strength tied to weather and atmosphere (map mood table).

## Patch notes line (public, once approved)

- Maps have real light and dark now: shadowed corners are darker, lit areas stand out.
