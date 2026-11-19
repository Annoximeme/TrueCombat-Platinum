# 0.39.3 queue

Plan: FAST FOLLOW right after 0.39.2 (Gianni 00:16Z: weapon + impact sounds "into the next patch asap"), with free aim. Publish still needs his typed go.
Base: the published 0.39.2 source (rel0392 after the v0392c publish). Each kit is re-checked against that base before integration.
No packaging, upload or publish without Gianni's typed go in the release thread.

| Kit | What | Location | Status |
|---|---|---|---|
| weapon-sounds | Weapon sound overhaul + impacts + ricochets, new cvar cg_weaponSounds (separate from cl_remaster) | weapon-sound-overhaul/kit-0393/ | GATE PASSED 01:20Z on the published 0.39.2 source (data v0.39.2-sandbox39), kit ca4c85908131c8a3. patches/01 tcp_audio.h + acReleasePaks row ("1365686346"), 02-impacts tcp_impacts.h/tcp_audio.h (12 variants per surface, dirt, snaps, ricochets), 03-sfxclass snd_openal.c (remaster files keep GUNFIRE/IMPACT/SNAP class); ui-patches/02 UI pak rebuild vs rel0392 main.menu; paks/zz_platinum_gunfire.pk3 client-only (sha256 61a73208a0cd7be2, checksum 1365686346), needs the install/update list + EAC catalogue entry. On the PC: G:\TrueCombatWork\integ0393\incoming\weapon-sounds\. Applies together with free-aim 01. READY |
| light-contrast | Darker map lighting with real light and shadow | integ0392/kits/light-contrast/ | Re-gated 20:32Z on 0.39.1 (54137da0). Ultra before/after shots run after 0.39.2, then Gianni picks |
| Railhouse wall rectangles | Engine visual fix | - | Needs a PC look to find the caster (engine thread) |
| ak-twohand (AK one-handed third-person frames) | AK-47, G3, G3A3 held one-handed in third person | integ0393/kits/ak-twohand/ | Cause: tcp_anim_script.h cut human_base.script lines at 255 chars, so two_handed_weapons lost id 33 and those guns played the pistol rows (strafe, run, walk, walk back, crouch idle, jump, swim). cgame only, 1 file (+5 -2), patch 736d099d; no pak/cvar/server change. GATE PASSED 01:34Z on the 0.39.2 source (data v0.39.2-sandbox39), kit 0f65acfb, all green. Cloud client check done (clip animation-upgrade/ak-twohand-0393-compare.mp4). READY. PC look: AK/G3/G3A3 third person (checklist in ak-twohand.md) |
| free-aim | Free aim with a deadzone, cg_freeAim (off by default) | integ0393/kits/free-aim/ | Gianni 23:42Z 18 Nov "get this in asap"; picked OFF by default, option in menu (23:55Z). cg_freeAim 2 Deadzone / 3 Wide deadzone (hip: gun moves before the view turns; aiming brings sights to the gun), 1 TC:E classic kept. Game patch 01 + ui-patches/02 (PC UI pak rebuild, Mouse & View row). GATE PASSED 00:01Z 19 Nov on the 0.39.1 source (kit fb12a6fe), probes pass incl. new freeaim_deadzone_probe under wine; applies cleanly on top of all 0.39.2 kits. READY. PC look checklist in free-aim.md |

## Log
- 23:52Z: queue created; rows from the 0.39.2 queue (moved items) and the coordinator (weapon sounds, free aim).
- 23:52Z: TODO after the 0.39.2 publish: put the published 0.39.2 source zip in integ0393/base/ and message the weapon sound thread (cmsg_01267kFSMwnKiipVDcuLPiLKTBSYhgnuQUEsahZzeN6hwK) to re-run its gate.
- 00:03Z 19 Nov: free-aim GATE PASSED on 0.39.1 (kit fb12a6fe), READY; manifest integ0393/kits/free-aim.md. Re-gate on the 0.39.2 source when it is in integ0393/base/.
- 00:09Z: weapon sounds kit v2 (8d8dc02c919240ca) replaces v1; free aim READY.
- 00:16Z: Gianni wants weapon + impact sounds in the next patch asap; 0.39.3 = fast follow after 0.39.2.
- 00:30Z: weapon sounds kit adds impacts (02-impacts-0393), kit 5750e6f91f3d81d8, pk3 1806898204.
- 01:00Z: 0.39.2 published 00:59:04Z. Base in integ0393/base/TrueCombat-Platinum-0.39.2-sandbox39-source.zip (2a53f089). Weapon sound thread told to re-gate.
- 01:05Z: also for 0.39.3/devlog: a clean real-fire tracer devlog frame.
- 01:20Z: Gianni 01:11Z "Everything that needs to run, needs to run." Re-checked weapon sounds 01 + impacts 02 + free aim 01 together on the 0.39.2 source: all apply. Transport: public kit-0393 5806e0f (no pk3: licensed audio; private-repo push was blocked). Weapon sound thread asked to put the pk3 at G:\TrueCombatWork\integ0393\incoming\weapon-sounds\ (sha256 b40c922b). PC: rel0393 + v0393a build/probes now, full regression via pcqueue (release prio) once the pak is in; look jobs keep running. No packaging without Gianni's typed go.
- 01:16Z: weapon sounds kit updated (ricochets + new 03-sfxclass engine fix): pak 61a73208 / checksum 1365686346, 01 128687a9, 02 28efafdb, 03 5eda0d6f; files on the PC in integ0393\incoming\weapon-sounds. PC told to use those, not kit-0393 5806e0f's weapon-sounds patches. Kit gating on the 0.39.2 source (weapon sound thread).
- 01:20Z: light-contrast + Railhouse stay out of v0393a (shots job runs after the gate); fold into v0393b if Gianni picks before packaging, else 0.39.4.

- 01:20Z: weapon sounds kit (01+02+03, pak 1365686346) GATE PASSED on the 0.39.2 source, kit ca4c85908131c8a3 (weapon sound thread).