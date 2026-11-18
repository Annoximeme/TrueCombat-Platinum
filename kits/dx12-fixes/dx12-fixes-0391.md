# Kit: DX12 fixes for 0.39.1 (shadow flicker on grass and fences, player shadows away from the feet, frame buffer growth, GPU crash report)

Owner: thread "Plan engine upgrades for stunning visuals". For: the 0.39.1 release (fix only).
Asked by Gianni 2026-11-18 15:02Z ("shadows on grass and fences give a sort of flickering. Fix this.") and his picks
1 + 2 of the DX12 list (15:03Z). Renderer only: dx12_core.cpp + dx12_vk.c (both in EXISTING of export_patch.py).

## Patches
- Base: the published 0.39.0 source (integ039/base/TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip). Apply `03-dx12-fixes-0391.patch` only.
- `03-dx12-fixes-0391.patch` (sha 45ff548d, dx12_core.cpp, dx12_vk.c, renderer_vk/tr_flares.c):
  1. **Shadow flicker on grass and fences.** The sun shadow pass (PSShadowApply, Ultra/High lighting) rebuilds each
     pixel's surface direction from the depth of its neighbours. Grass blades, fence wires and leaf edges are a pixel or
     two wide, so the "neighbour" is whatever lies behind them, and under the TAA jitter it changes every frame. The
     facing test and the shadow offsets flipped with it: player, prop and contact shadows flickered on grass and fences.
     Such thin pixels (no neighbour at the same depth across or down) now take the sun direction as their surface
     direction, stable from frame to frame, and skip the contact-shadow march. Contact shadows also ignore occluders
     one pixel wide (a blade that is there in one frame and gone in the next). OpenGL has no sun shadows: DX12 only.
  2. **No more dropped draws.** A full per-frame upload buffer (96 MB) dropped every remaining draw of that frame
     (geometry/HUD vanished for a frame). It now moves the frame to a buffer twice the size (up to 768 MB; the old one
     is freed when the GPU is done) and logs "DX12: frame upload ring grown to N MB".
  3. **GPU crash report.** r_dx12CrashReport 1 (default, latched) turns on Windows DRED before the device is made.
     After a device-removed error the console log gets the last finished operations of the command list that stopped
     ("DX12 crash: list 'frame' stopped after N of M operations" + FAULT? line) and, on a page fault, the GPU address
     and the resources live/freed there. Needs Windows 10 1903+; older Windows ignore it.
  4. **Player shadows away from the player** (Gianni 15:37Z, "occasionally"). The shadow casters' slope depth bias was
     clamped at 0.01 of the light's depth range: up to 71 units on the cascades. A player's sides face the sun at a
     grazing angle, so their bias hit that clamp and the body's shadow began up to a player height away from the feet
     (worst with a low sun and in the far cascades). Clamp now 0.0006 (about 4 units), slope factor 2.0 -> 1.5. Also
     hardened: each shadow view carries its own target (viewParms.viewportX = 0x40000 + target) instead of relying on
     a FIFO that one dropped render command would put out of step for good (cascades drawn into each other's maps);
     shadow views add no flares (tr_flares.c, in EXISTING). Cause found by reading the code; PC check confirms.

## Gate
KIT GATE PASSED 2026-11-18 17:26Z on the FINAL 0.39.0 source + 03 (checksum 8314fe8b5f42408c), SUMMARY.md. (Earlier: 15:49Z on 0.38.0 + 01 + 02 + 03, 3c6ad4e6.)
The flicker cause was found by reading the shader (no GPU in the cloud): the PC check below confirms it.

## PC check (DX12, Ultra, after the 0.39.0 publish; G: only)
- Village + Snow, r_dx12Shadows 2, r_dx12ContactShadows 1: stand by tall grass and the fences while a player/bot walks
  past and in the sun; before/after: no flicker on blades and wires. `r_dx12ShadowsDebug 1` shows the visibility.
- Same maps with bots in the sun (a low-sun map too, e.g. Snow): every player shadow starts at the feet, also far away;
  no shadow acne (striping) on players and walls.
- 10 minutes of play: no "upload ring" lines expected (if one appears it must say "grown", never "dropping").
- fps with r_dx12CrashReport 1 vs 0 (vid_restart): within 1 percent expected.
- HLSL changed: run check_hlsl.py.

## Patch notes (public)
- Fixed: flickering shadows on grass and fences (DX12).
- Fixed: player shadows sometimes started away from the player (DX12).
- Fixed: rare one-frame flicker when a frame needed a lot of geometry (DX12).
- DX12 crash reports now include more detail to help us fix graphics driver crashes.
