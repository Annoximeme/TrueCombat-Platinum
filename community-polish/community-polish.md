# Community maps polish for the 0.39.0 rebuild (minimaps + loading screens, bot flags, Villa crate)


KIT GATE PASSED 2026-11-18 13:17Z on the 0.39.0 source (only the agreed base scan hit): [SUMMARY.md](SUMMARY.md), kit checksum 06f72e83d03d7c2f.
Thread "Recover TC:E community maps". Gianni approved bringing all three follow-up kits into the 0.39.0 rebuild ("All of them.", 2026-11-18 12:45Z). Base: v0.39.0-sandbox37 source zip (/mnt/project-files/integ039/base/TrueCombat-Platinum-0.39.0-sandbox37-source.zip, sha256 20e7673f...). All three patches apply on it stacked, in order, with line offsets only (no fuzz). The patches are byte-identical to the separately gated kits:
- /mnt/project-files/community-maps/mapdata/kit-mapdata.md
- /mnt/project-files/community-maps/botflags/kit-botflags.md
- /mnt/project-files/community-maps/bombcrate/kit-crate.md

Those docs carry the full cause/fix write-ups.

## 1. Kit
| file | sha256 | use |
|---|---|---|
| patches/01-community-mapdata-acreleasepaks.patch | 333e746c59ba4c51b90504253a9f2d7e551735da38bcba5b40c216b69ee692f2 | `git apply` at the source root. sv_anticheat.c: one acReleasePaks row `tcetest/zz_community_mapdata -872564553` after the zz_platinum_assets row |
| patches/02-bot-flagstands.patch | f1969535c58e63d4efdd3856260c960393f20da02ef040eade1876e8833e4bf6 | game_src/native/tcp_bots.h: bots take flags that sit on stands (Villa 2.1, Shozen) and reach capture zones. The 0.40 bot-navfix kit builds on this patch |
| patches/03-bombsite-crate-order.patch | 5013e98ffa6a7f7858b13b00571c2f3cd312ad2e77e4e8fefd23d4871c7fb6c7 | game_src/native/tcp_game.c: a bomb site's crate is linked even when the crate comes before its trigger (Villa 2.1 site A crate now breaks) |
| data/zz_community_mapdata.pk3 | 4883eb7085920cd12fe7b9740277aa655973cfd127731f20b45290c335900150 | ship in tcetest/ next to the map paks (615 KB). Fixed input: do not re-zip (pak checksum -872564553 is whitelisted by patch 01) |

Pak contents: gfx/platinum/maps/<map>.txt, <map>_layout.jpg and <map>_bg.jpg for obj_villa2_1, obj_shozen, obj_snowtown and obj_chlite. Together these give the minimap, the tactical map plan (sites, flags, callouts) and the loading-screen plan, picture, title and description.

## 2. Build / package steps
- Apply 01, 02, 03 in order; rebuild engine, server (sv_anticheat.c) and qagame (tcp_bots.h, tcp_game.c). No cgame, UI or renderer change.
- Copy data/zz_community_mapdata.pk3 into tcetest/. Add it to the EAC catalogue and the package file list like the other community paks.
- Servers: the qagame changes take effect on every server running the new build. The pak is client data. The servers only need the acReleasePaks row, which ships in the server binary.
- Credits unchanged.

## 3. Public patch notes lines
- Community maps now have minimaps, tactical maps and loading screens with a map plan, picture and description.
- Bots now pick up the flag on Villa 2.1 and Shozen in Flag Capture.
- The site A crate on Villa 2.1 now breaks when the bomb goes off.

## 4. Test checklist (combined pass)
`map | renderer | cvars/commands | look at | pass rule | shot`
- obj_villa2_1, obj_shozen, obj_snowtown, obj_chlite | DX12 | `map <name>` | loading screen | plan, picture, name and description show | y
- same four | DX12 | in game, tactical map key | tactical map + HUD minimap | plan shows, own dot moves the right way, sites/flags in the right places | y
- obj_villa2_1 | either | tcp_native_rounds 5, bots | flags | bots steal and capture | n
- obj_villa2_1 | either | tcp_native_rounds 6 | plant at site A, let it detonate | site A crate breaks | y
- obj_village, obj_snow, obj_stadtrand | either | Flag Capture / Bomb with bots | as in 0.39.0 (flags, both Stadtrand crates) | n
- any community map | DX12 | EAC client on an sv_eac 2 server with the pak | no unknown-pak report | n

## 5. Known gaps
- Shozen: bots reach the flags but rarely within a few minutes (nav graph at its 8192-node cap). The bots thread owns this for 0.40.
- Bots find no route to some Bomb sites on Villa 2.1 and Chlite (navfix kit, 0.40).
- Plans are generated from map geometry. Villa 2.1 and Shozen only have spawn callouts. Needs a look in game.
- Colour casts from the DX12 audit (Snowtown, Shozen, Villa) are not part of this kit.
