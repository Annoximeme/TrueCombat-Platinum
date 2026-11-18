# Third-person support hand stays on the rifle (0.39.2)

Thread "Improve player and weapon animations". Gianni 2026-11-18 18:45Z (via the coordinator): "Also, when crouching or strafing of some sort, the hands of models tweak out in third person." Bug fix, so 0.39.2 (coordinator). Gated on the FINAL 0.39.0 source; re-gate on the 0.39.1 source once that is published (this kit does not touch anything 0.39.1 changes).

## 1. Kit
Folder: /mnt/project-files/integ0392/kits/grip-hands/

| file | sha256 | use |
|---|---|---|
| paks/zz_platinum_grip.pk3 | 1efa1be2aae6afe612c0d35f4d5bb3e41327aff9b1219f7b17fcf9d52fde05ea | REPLACES the 0.39.0 pak of the same name in tcetest. One file: animations/human/base/body.mdx. Pak checksum 1270617611 (was 599439406). EAC file list: same file name, new content. |
| patches/01-grip-hands-acreleasepaks-0392.patch | e93b4adc5bcfc8d0a14cd51dd509c7188d517f371e7ce10d32e044c4cb165b9a | one line in reference/etlegacy/src/server/sv_anticheat.c acReleasePaks: zz_platinum_grip 599439406 to 1270617611. `git apply` at the source root. |

No game code, no cvar, no UI pak rebuild, no protocol change. The 0.39.0 per-gun trim table (tcp_grip3ps) and the one-handed Shorty stay as they are.

## 2. Cause
The 0.39.0 grip pak was built by an offline tool that applied every bone's rotation transposed (vertex = offset x M instead of the engine's M x offset, see tr_animation_mdm.c LocalAddScaledMatrixTransformVectorTranslate and R_GetBoneTag). Its own checks therefore said "hand on the handguard", while in the engine its IK pulled the support hand off the rifle: up to about 6 units standing, 9 strafing (alert_run_2h), 14 walking back (alert_bk_2h) and 5 crouch-walking, and it moved from frame to frame, so the hand flapped next to the gun. Measured with the engine's math, TC:E's stock grip was within 0.7 units of the bore line all along.

## 3. Fix
New body.mdx built from the STOCK body.mdx with the engine's bone math:
- In the same 133 frames of the 11 rifle rows as 0.39.0 (stand_machinegun, firing_machinegun, alert_run_2h, alert_bk_2h, alert_crch_2h, alert_crbk_2h, firing_crch_2h, firing_crbk_2h, firing_rifle, prone_mg_idle, prone_mg_fire), the support hand has one fixed place and angle relative to the firing hand, so relative to the gun on tag_weapon: TC:E's own stand_machinegun grip, centred under the bore, palm resting on the handguard.
- Upper arm and forearm reach it by two-bone IK with the elbow down along the spine, close to the body.
- Changed: left upper arm, forearm, hand and finger bones in those frames only. Header, bone table, tags and every other bone and frame are byte-identical to stock body.mdx. Hit boxes are analytic and the server never reads body.mdx: no gameplay change. Classic hides nothing here (zz_ pak, same as 0.39.0).
- Numbers (engine math, all 29 two-handed guns incl. CQB, idle/aim/run/back/crouch-walk/crouch-fire/fire/prone, with the 0.39.0 trim table): support hand 0.06 to 0.60 units into the handguard underside, at most 0.32 off the bore line, firing hand at most 0.22 from the grip. 0.39.0 pak: up to 13.7 off the bore line. Stock: up to 0.72 off, up to 1.85 into or 1.28 below.
- Cloud OpenGL client check (Village, third person, strafe both ways, crouch idle, crouch-walk forward and back): the hand stays on the rifle, no flapping. Clip (internal): /mnt/project-files/animation-upgrade/hands-0392-compare.mp4.

## 4. Test checklist
`map | renderer | steps | pass rule | shot`
- obj_village | DX12 | bot or second client in third person with M4, AK-47, MP5, SPAS-12, PSG-1: stand, strafe both ways, walk back, crouch, crouch-walk, prone, fire | support hand on the handguard and stays there, elbow natural, no flapping | y
- obj_village | either | reload, grenade throw, knife from a rifle | no arm snap entering or leaving those rows | n
- any | either | pistols, Shorty, akimbo | unchanged | n
- any | n/a | client with the new pak on an official server | no AC kick (row in patch 01) | n

## 5. Tools (not shipped)
/mnt/project-files/integ0392/kits/grip-hands-tools/: fix_grip_hand.py (builds the body.mdx: `python3 fix_grip_hand.py <stock body.mdx> <0.39.0 grip body.mdx> <out>`), grip_numbers_engine.py (the 0.39.0 grip_check numbers with the engine's math), skel-engine-math.diff (the fix to the 0.39.0 grip tools' skel.py; integ039/kits/grip-fix-tools still has the transposed math, do not reuse it unpatched).

## 6. Overlaps
- sprint-040 (0.40 kit): its sprint.mdx was built from the 0.39.0 grip body.mdx, so its left arm has the same fault. Rebuild that pak from this body.mdx before 0.40 (thread "Improve player and weapon animations").
- No other 0.39.x kit ships body.mdx.

## 7. Status
Kit gate: SUMMARY.md in this folder (base TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip, game data v0.39.0-sandbox37). This file is part of the kit checksum, so it is not edited after the gate.

Patch notes line: "Fixed other players' support hand slipping off the rifle in third person while strafing, walking backwards and crouch-walking."
