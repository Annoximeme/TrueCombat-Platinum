# Models pilot: M67 grenade (PC look check only, not a release kit)

Data-only pak with a rebuilt M67 frag grenade: first-person model (original hand animation), world model and
thrown model, one 1024 texture set (`tcp_m67.jpg`, `_n.jpg`, `_rmao.jpg`) under `models/weapons2/m67/`.
2,472 triangles (was 612). No code change.

Check on the PC (DX12, Ultra preset; then one OpenGL shot):
1. Real copy of the installed game to `G:\TrueCombatWork\models-check` (not hard links). Never touch the install.
2. Baseline shots without the pak, then copy `pak/zzzzz_platinum_models.pk3` into the copy's `tcetest/` and repeat.
3. Local map (`devmap obj_village`, not pure, no Easy Anti-Cheat), then `closelimbomenu`, `weaponbank 4`.
   Shots: grenade in hand, pin pulled (`+attack` held), thrown grenade on the ground if it is easy to frame.
4. Look for load errors on `tcp_m67` and whether the normal and roughness/metal/AO maps were picked up.

The pak is not in the release pak list yet, so it only loads on a non-pure local server. That entry comes with the
real kit for 0.40.0.
