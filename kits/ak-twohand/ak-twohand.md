# AK-47, G3 and G3A3 held with two hands in third person (0.39.3)

Thread "Improve player and weapon animations". Found in the 0.39.2 PC look (release thread, 21:50Z 18 Nov): "On the AK-47, some frames (crouch, strafe right, prone) show the rifle held out one-handed at arm's length." Present since at least 0.39.1, not caused by grip-hands. Queued for 0.39.3 (integ0393/QUEUE.md), coordinator 01:11Z 19 Nov; Gianni 01:11Z "Everything that needs to run, needs to run."

## 1. Kit
Folder: /mnt/project-files/integ0393/kits/ak-twohand/

| file | sha256 | use |
|---|---|---|
| patches/01-ak-twohand-0393.patch | 736d099d5fcc646e01bf3535be941b00ac19b3755c2d21dc4742ecf3f93a14f0 | cgame only, 1 file (+5 -2): game_src/native/tcp_anim_script.h. `git apply` at the source root. Made on the published 0.39.2 source. No other 0.39.3 kit touches this file (free-aim, weapon-sounds checked). |

No pak, no cvar, no server change, no protocol change.

## 2. Cause
tcp_anim_script.h reads TC:E's animations/scripts/human_base.script one line at a time into a 256-byte buffer. Five "set weapons" lines in that script are longer (258 to 728 characters), so their tails were cut off. The important loss: `two_handed_weapons` (374 characters) lost "AKSU-74 SD", which is weapon id 33 = the AK-47, and through the stock-twin rule also the G3 and G3A3. Those guns then missed every "weapons two_handed_weapons" item and fell to the script's `default`, the one-handed pistol rows: alert_run_1h when strafing or running, relaxed_walk_1h_1 walking, alert_bk_1h walking back, alert_crchidle_1h crouched, jump_1step_1h, e_swim_1h. With a rifle on tag_weapon that looks like the gun held out or hanging in one hand. ET 0.49b's own parser reads by token and has no line limit, so TC:E always meant the full lists.

## 3. Fix
Line buffer 256 to 1024 (longest script line is 728). Simulated over every Platinum weapon (row choice for each movement and event list, firing on and off, before and after):
- AK-47, G3, G3A3 (id 33): now the same rifle rows as the M4: alert_run_2h strafe and run, stand_machinegun torso on walk and crouch idle, alert_bk_2h walk back, alert_crbk_2h crouch-walk, jump_1step_2h, e_swim_2h. Events (fire, reload, raise) unchanged.
- M590 Compact and Akimbo Shorty (id 32): swim rows 1h to 2h only.
- Every other weapon: no change.
- Visual only: the server never reads the animation script and hit boxes are analytic, so no gameplay or timing change.

Cloud OpenGL client check on the 0.39.2 source (Village, third person, AK-47 via the deploy command; tcp_debug_anims 1): before = alert_run_1h / relaxed_walk_1h_1 / alert_crchidle_1h, after = alert_run_2h / stand_machinegun / alert_crchidle_2h; the AK is now held with both hands in every state. Clip (internal): /mnt/project-files/animation-upgrade/ak-twohand-0393-compare.mp4.

## 4. Test checklist
`map | renderer | steps | pass rule | shot`
- obj_village | DX12 | bot or second client in third person with AK-47, G3 and G3A3: idle, walk, strafe both ways, walk back, crouch idle, crouch-walk, prone, jump | rifle held with both hands like the M4, support hand on the handguard | y
- obj_village | either | same with M4, MP5, pistols | unchanged | n
- any | either | fire, reload, switch weapons with the AK | rows still play | n

## 5. Status
Kit gate: SUMMARY.md in this folder (base TrueCombat-Platinum-0.39.2-sandbox39-source.zip, game data v0.39.2-sandbox39). This file is part of the kit checksum, so it is not edited after the gate.

Patch notes line: "Fixed the AK-47, G3 and G3A3 being held one-handed in third person while moving or crouched."
