# Kit gate: voice-0391: KIT GATE PASSED on the FINAL 0.39.0 source

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc...), game data v0.39.0-sandbox37
- Patch 01-voice-engine.patch sha256 401541ba410d56b2...; kit checksum afe03faffa616d9d (the gate ran on a copy; gate/ and SUMMARY.md excluded); 2026-11-18 18:22-18:32Z
- compose, scan, toolchain, windows (all modules, launcher, installer), scan-built, linux, bots (obj_village, obj_snow, 12 bots): all pass. Probes built, not run (no wine in this container; the kit does not touch game modules).
- The source zip has no libs/opus, so the gate's Windows build compiles cl_voip.c without TCP_VOIP. Extra check with voice ON: same base + patch + official libopus 1.5.2 tarball (sha256 65c1d2f7...a7ce1, = the PC's libs/opus version) via tools/ci/build-windows.sh: engine configure "Voice chat: libopus from libs/opus", etl.exe built with no warnings from cl_voip.c (contains voip_nextDevice, cl_voipMeter, cl_voipVADLevel2).
- ui-patches/02-voice-options-page.patch is for the PC tree only (analysis_scripts is not in the source zip): git apply --check passes on integ039\src\analysis_scripts\platinum_quick.py (md5 266d6810...). Needs the UI pak rebuild + acReleasePaks sync and a PC look.
Full table: /mnt/project-files/voice-chat/voice-0391-gate-run.md (kept outside the kit so the checksum stays)
