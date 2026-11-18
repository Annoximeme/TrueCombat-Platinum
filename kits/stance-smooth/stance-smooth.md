# Smoother stand, crouch and prone changes (0.39.1)

Thread "Improve player and weapon animations". Gianni 2026-11-18 18:10Z: "Animations from standing and proning and crouching need to be way smoother." This kit is the small, safe part for 0.39.1; new transition animations (kneel-down, drop to prone, get-up) are planned for 0.40.

## 1. Kit
Folder: /mnt/project-files/integ0391/kits/stance-smooth/

| file | use |
|---|---|
| patches/01-stance-smooth-0391.patch | cgame only, 2 files (+23 -5): game_src/native/tcp_viewfx.h and tcp_player_models.h. `git apply` at the source root. Applies on the FINAL 0.39.0 source alone and on top of audit-0391 09-11, dx12-fixes 03, tacmap-title 01, launcher-patchnotes 01 and muzzle-flash 01 (checked in that order). |

No pak, no cvar, no server change, no protocol change.

## 2. What changes
- First person: the eye's glide on a stance change now eases in and out (smoothstep) instead of moving at a constant speed that starts and stops with a jolt. Same lengths as 0.39.0 (250 ms stand/crouch, 750 ms to or from prone), so the eye arrives exactly when it did. A change during a glide continues from where the eye is.
- Third person: when a player stands, crouches or goes prone, the body blends from the old pose over 150 ms (200 ms to or from prone), eased, instead of one animation frame (about 50-70 ms). Only blends that start within 100 ms of a stance change are affected; every other animation keeps its own blend.
- Fairness: hit boxes, view height, movement and timing are server-side and unchanged. The visible body can trail the server's stance by up to about 100-130 ms more than before (blend midpoint at 75 / 100 ms), which is why the blends are kept short.

## 3. Test checklist
`map | renderer | steps | pass rule | shot`
- obj_village | DX12 | first person: stand to crouch to stand, stand to prone to stand, crouch spam | eye moves smoothly, no jolt at start or end, ends at the same height | n
- obj_village | DX12 | watch a player or bot crouch and go prone | body eases into the new pose, no pop, no wrong pose left behind | y
- any | both | crouch while shooting and reloading | shot and reload rows still play | n

## 4. Status
- Kit gate: see SUMMARY.md in this folder (base TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip, game data v0.39.0-sandbox37).
- Gate result and cloud OpenGL client check: in SUMMARY.md (this file is part of the kit checksum, so it is not edited after the gate).
