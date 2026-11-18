# Kit: parallax repair for 0.39.0 (real height maps)

Owner: thread "Plan engine upgrades for stunning visuals". For: thread "Build and package 0.39.0".
Gianni 2026-11-18: "Hold 0.39.0 for a real repair" (12:22Z), then "Real height maps (best look)" (12:35Z).
So `r_dx12Parallax` stays default **1**. The default-0 route (G:\TrueCombatWork\integ039\parallax0) is OFF.

## What it fixes (audit F01, DX12 Ultra pass)
The 0.39 wall depth effect guessed depth from the albedo's brightness, so stains and dark bricks became pits and brick
walls broke up into a sawtooth at grazing angles. Now:
- Real height maps: `<texture>_rmaoh.dds` (BC7, rmao in RGB, height in alpha, full mips) for the 38 brick, cobble,
  gravel and rock textures with material maps on the 0.39 maps (6 stock, 4 community, Harbour). Heights come from each
  texture's own shipped normal map (FFT integration, coarse blotches above 8 cycles per texture removed), so the depth
  agrees with the lighting: mortar joints and chipped edges sink, brick faces stay up.
- Shader: depth fades out at grazing angles and on faces looking down, 8 to 24 steps by angle, plaster and ceilings
  never get depth, the brightness guess (textures without a height map) is 0.75x as deep.

## Files
- `patches/02-parallax-repair-0390.patch`: dx12_core.cpp + dx12_vk.c (51 lines added), gate tree layout
  (`reference/etlegacy/src/...`). `patches/parallax-repair-0390-src-layout.patch`: same, `src/renderer_dx12/...`
  layout of the engine tree. `01-gfx-immersion-0390.patch` is only there so the gate can rebuild 0.39's renderer on the
  0.38 base; it is already in 0.39.0, do NOT apply it again.
- `data/zzz_hd_v1_heights.pk3` (stored, 12.3 MiB, sha256 108fcadabd77d4b2dd2a063bd964def479bac5cdc212bfe6996a6827a1e83158),
  `data/manifest.json` (per-file sha256), `data/heights-labelled.jpg` (contact sheet: dark = low).
  Name sorts after zzz_hd_materials.pk3 and BEFORE 0.40's zzz_hd_v2_heights.pk3, so the 0.40 HD pack still wins.
- `tools/build_heights_039.py` (`--materials mat_in.pk3 --only tools/heights-039-textures.txt --highpass 8
  --full-relief 0.006 --pak-name zzz_hd_v1_heights.pk3`), `tools/extract_relief_materials.py` (PC side input copy).

## Gate
KIT GATE PASSED 2026-11-18 12:35Z (kit checksum 0b7797e6d045631a, base 0.38.0-v0380l + 01 gfx039 + 02), SUMMARY.md.
The patch applies cleanly (`git apply --check`) to G:\TrueCombatWork\integ039\parallax0-engine\src (0.39 engine).
That copy has `r_dx12Parallax` default "0": use the real rel039 source, where the default is "1".

## Release thread steps
1. Apply `parallax-repair-0390-src-layout.patch` to the rel039 engine tree (`prepare --check` first).
2. `check_hlsl.py` on the PC (the HLSL changed), rebuild renderer_dx12_x64.dll.
3. Add `zzz_hd_v1_heights.pk3` to tcetest (base install, not optional), to acReleasePaks and to the EAC catalogue.
4. Full 19-case gate; DX12 Ultra look at the audit's five brick spots (audit thread redoes them).
5. Patch notes line (public wording): "Brick and stone walls now use real height maps for their depth effect: no more
   broken-up bricks at shallow angles."
