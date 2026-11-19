# weapon-sounds (0.39.3)

Owner thread: Overhaul weapon sounds with indoor and outdoor acoustics.
Gianni 18 Nov: complete realistic weapon sound overhaul, loud with a kick when you fire (23:04Z); 23:26Z card:
"Gun sounds in 0.39.x, engine 0.40.0"; 23:33Z: "Just build an original weapon sounds or remastered sound,
separate option." So this is its own setting (cg_weaponSounds), independent of the 0.40.0 cl_remaster switch.

## What it does

- Options > Audio > "Weapon sounds: Remastered / Original" (cg_weaponSounds, archived, default 1 Remastered).
- v2 after Gianni's listening 23:54-23:57Z ("a lot of weapons sound the same, pistols"; "keep the original but
  remaster it" when there is no distinct recording; "miss the kick"; "make it loud, also in-game"; "reverb needs to
  be good too"):
  - Every in-game weapon has its own source. 35 weapon files use a real recording of that gun or its closest
    relative (no two guns share one, except akimbo/iron-sight twins of the same gun); 12 use their ORIGINAL TC:E
    sound remastered (USP, MAC-10, UMP45, MP9, SIG 552, SIG 550, AKS-74U SD, SIG 550 SD, M4 SOPMOD x3,
    AK-74M Spetsnaz): same file, re-cut, with kick, 4 variations by small pitch/tone spread.
  - Kick on everything: per-calibre falling sine thump + dark body + soft drive (0.7 for other players' guns,
    1.6 for your own).
  - Loud: other players' guns +3 dB over the original (rms first 50 ms), capped at -4 dBFS rms; your own gun +7 dB,
    capped at -3 dBFS rms (louder is only distortion). Ranges/falloff unchanged; same for every Remastered player.
  - Reverb: imsShotLayers (tcp_immersion_cg.h) plays new rendered room tails per space (room, hall, outdoor,
    snow) x calibre group (pistol/SMG, rifle, DMR/sniper/shotgun) x 2, from the calibrated acoustics-lab renderer
    (living room / corridor, warehouse / parking garage, street / open field with tree line and hills, forest /
    open snow field). Original keeps TC:E's sound/reverb set.
- Original: the .weap flashSounds and TC:E tails exactly as 0.39.2. Both sets are registered at map load, the switch
  is instant.
- CQB suppressor attachments (TCP_ES_SUPPRESSED, cqbQuietFire) keep their 0.39.2 sound. Echo/far layers unchanged.
- Weapons with no fire sound in the game files (luger, microuzi, mp40, sten, thompson, vc100, g36c, g3a4, m590,
  akimbo_colt, *_old) get nothing and keep whatever they play today.

## Files

| file | what |
|---|---|
| patches/01-weapon-sounds-0393.patch | `game_src/native/tcp_immersion_cg.h` (Remastered tails per space x calibre group, registered only when present) + `game_src/native/tcp_audio.h` (cvar, recorded set per weapon, pick in taFire; checks the pak has fire<n> + fp<n> before registering, so no default-sound warnings) + one acReleasePaks row in `reference/etlegacy/src/server/sv_anticheat.c` (`tcetest/zz_platinum_gunfire` 99618356, anchored after zz_platinum_cqbweapons so it applies on 0.39.1 and 0.39.2). |
| ui-patches/02-weapon-sounds-ui-0393.patch | PC UI pak rebuild (like discord-invite): `analysis_scripts/platinum_audio.py` + generated `release_src/platinum_ui/{ui,ui_obj,ui_robj,ui_tdm}/main.menu`. Right column now 22 px steps with "Weapon sounds" on top; Output row 362 -> 366; RESET AUDIO sets cg_weaponSounds 1. Made against rel0392 (G:\TrueCombatWork\integ0392\rel0392, main.menu md5 218fd4d7). Rebuild the UI pak and update its acReleasePaks row as usual. |
| paks/zz_platinum_gunfire.pk3 | NEW client pak for tcetest, 12.9 MB: sound/remaster/weapons/<weap file>/fire1-4.wav + fp1-4.wav for 47 weapon files, sound/remaster/reverb/<set>_<group>_<n>.wav (24 tails), 48 kHz mono 16-bit, + sound/remaster/CREDITS-gunfire.txt. Pak checksum 99618356. Deterministic (zip -X -D, fixed dates). Client only, server never reads it. NOT a z_remaster_ pak: it must stay visible in Classic (0.40.0), because the setting is separate. Add to installer/update list and the EAC file catalogue like the other zz_platinum client paks. Sonniss audio: only inside this pak, never loose or in a public repo. |

## PC look (with bots, DX12)

1. Options > Audio: "Weapon sounds" row on top of the right column, nothing overlaps (Output row moved down 4 px).
2. Remastered: fire every gun class (pistol, SMG, rifle, DMR, sniper, shotgun, suppressed) in the practice range;
   own shots punchy, no clicks at the end of a shot, full auto does not cut off. Bots firing nearby: about as loud as
   Original (switch back and forth).
3. Original: identical to 0.39.2.
4. Console with cg_audioDebug 1 on map load: `TCP_NATIVE_AUDIO weapon ... recorded=4` for every gun.

## Sources and tools

Build script: /mnt/project-files/weapon-sound-overhaul/tools/build_remaster_guns.py (recordings on
G:\TrueCombatWork\sound-upgrade\downloads, current sounds from the game paks). Report with per-shot levels:
/mnt/project-files/weapon-sound-overhaul/kit-0393/REPORT-guns.json.

## Impacts, fly-bys and near-miss snaps (added 19 Nov, patch 02-impacts-0393.patch)

Gianni: impacts must "seamlessly integrate with the originals", with more variations.

- The five TC:E sounds per surface stay. Remastered (cg_weaponSounds 1) adds variations 6..12 from
  `sound/remaster/impact/<name><n>.wav` (flesh, metal, wood, glass, stone, tin, fence, foliage, fly-by), so each
  surface picks from 12. Never the same file twice in a row.
- Every new variant is matched to its set's originals: average 1/3-octave spectrum, rms level (+-1.5 dB),
  peak ceiling, length; long-ringing sets (metal, tin, fence) carry an original's ring under the new hit.
  Kinds: real recorded hits (EQ/level matched, with the original's 6 ms "tick"), hybrids (original
  transient + recorded body) and re-voiced originals (+-4..9 % pitch, tilt, tail swap).
- New: soft ground (dirt, soil, mud, gravel, snow, sand, grass), silent in TC:E, gets `dirt1..12` at a quiet
  level (foliage + 4 dB, low-passed). Original mode keeps it silent.
- Near-miss snaps: crack and whizz go from 4 to 12 (`sound/remaster/snap/crack5..12`, `whizz5..12`).
- Original mode (cg_weaponSounds 0) plays only the original sounds, as before.
- Console line `TCP_NATIVE_IMPACTS variants ...` shows how many per surface loaded (expect 12, dirt 12).
- Builder: /mnt/project-files/weapon-sound-overhaul/tools/build_impacts.py; REPORT-impacts.json.

PC look additions: shoot concrete, metal, wood, glass, a fence, a bush and dirt on obj_village and obj_snow with
Remastered on and off; listen that the new ones are indistinguishable in character from the originals.
