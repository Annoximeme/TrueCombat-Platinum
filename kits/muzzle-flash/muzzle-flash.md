# Kit: muzzle-flash for 0.39.1 (muzzle flash placement, all guns)

Owner: thread "Tune every gun's muzzle flash". For: the 0.39.1 release thread.
Rule: Gianni 17:18Z "take a look at every gun's muzzle flash and adjust it / correct it ... Tune it to perfection."; 18:08Z "I want all bugfixies in 0.39.1".

Base: the FINAL 0.39.0 source zip (integ039/base/...-FINAL-source.zip). Independent of the other 0.39.1 kits (touches only the two cgame headers below).

| Patch | sha256 | Files | What |
|---|---|---|---|
| 01-muzzle-flash-0391.patch | ac2a06b1a0c31bfd31ff82dfd3285e0b3a240dcd0ac5d9db17599aaaff877777 | game_src/native/tcp_weapon_media.h, game_src/native/tcp_player_models.h (+71/-11) | See below |

What changed and why:
- Third person (other players, bots, own third-person view): the flash now follows the gun's bore. Models whose tag_flash is tilted (M4/M16, pistols) had the flash blooming back over the gun or pointing off-axis; the flash axes now snap to the gun's axes when more than 3 degrees off.
- Flash sits at the barrel end: where tag_flash is set back inside the barrel (M590, SPAS-12 and others), the flash is moved forward to the model's front (only when 0.25 to 6 units behind; nothing else moves).
- Akimbo (all four CQB akimbo pairs + stock akimbo Glock/Beretta): first-person flash appears on the muzzle of the gun that actually fired (left/right by shot parity, per-gun muzzle table), brass ejects from the matching gun, third-person left gun gets its own flash on tag_weapon2.
- Stock akimbo Glock/Beretta first person uses the CQB 1911 view geometry so both guns are on screen (one was off-screen before).
- First-person flash for guns with tags in the main part (tagsInMain or tag_flash on part 0) uses that part, so it follows the slide/barrel instead of the hands' tag.
- New cheat cvar cg_muzzleFlashHold (CVAR_CHEAT, default 0): 1 keeps the flash drawn for inspection, 2 also brightens it. Test aid only; inert on servers without sv_cheats.

Scope: cgame only. No pak, no .weap/model change, no protocol, server or anti-cheat change.

Tests (cloud OpenGL rig, Xvfb + llvmpipe): all 43 guns, hip / ADS / focus / third person, before and after, 173 shots each (/mnt/project-files/muzzle-flash/ sheets). Not yet seen: DX12 Ultra on the PC.
Known and unchanged: no flash through magnified scopes (TC:E behaviour); shotgun/pistol flash size unchanged; akimbo sawn-off left gun pose in third person.

Gate: SUMMARY.md here (kit-gate.sh on the FINAL zip).

Patch notes (player wording): "Muzzle flashes now sit at the end of the barrel and follow the gun on every weapon, in first and third person, including both guns when firing akimbo."
