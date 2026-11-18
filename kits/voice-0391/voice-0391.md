# voice-0391: voice chat fix + Options > Voice device pickers (0.39.1)

Owner thread: "Fix voice chat and add device picker". Gianni 18:13Z 18 Nov: "Voice chat doesn't seem to be working. Make sure people can pick their devices in options."

## Why voice did not work (0.39.0)
Found on Gianni's own 0.39.0 profile and console log (official #2, 18 Nov): the microphone opened fine
("Voice chat: microphone ready (system default)") and the server advertised voice, but his profile has
`cl_voipUseVAD 1` (voice activation) with the default `cl_voipVADThreshold 0.08`.
1. **Voice activation level far too high.** 0.08 frame RMS is about -22 dBFS; normal speech on a real microphone
   sits around -40 .. -25 dBFS (lower again when SDL folds a stereo interface such as a Focusrite to mono). So the
   open microphone never crossed the level and nothing was ever sent. The PC voice tests (0.36.0) used the 440 Hz
   test tone at about -15 dBFS, which is why they passed. 
2. **Push-to-talk keys were ignored with voice activation on.** In VAD mode H / N did nothing, so there was no way
   to force a transmission either.
3. No feedback: Options > Voice had no level meter, and the microphone was a free-text name field.

## Fix
Engine (`patches/01-voice-engine.patch`, client only, `cl_voip.c`; no protocol, server, cgame or pak change):
- default `cl_voipVADThreshold` 0.02 (about -34 dBFS); saved profiles still on the old 0.08 move to 0.02 once
  (flag `cl_voipVADLevel2`).
- H / N always transmit, also with voice activation on (switching radio <-> local starts a new transmission).
- microphone level now on a dB scale (-60..0 dBFS = 0..100), also used by the HUD "You" bar.
- `cl_voipMeter` (read-only): live bar for the menu, `[#####...|....] 43%  sending`, `|` = activation level;
  or "Microphone idle: start the mic test", "No microphone found", "Silence only: muted or blocked by Windows"
  (3 s of pure digital silence, which is what Windows gives when desktop apps may not use the mic; also a console hint).
- `voip_nextDevice` steps `cl_voipCaptureDevice` through the SDL capture devices, then back to the Windows default;
  `voip_nextDevice default` resets it. `ui_voipDevice` (read-only) shows the name.

UI builder (`ui-patches/02-voice-options-page.patch`, PC tree `analysis_scripts/platinum_quick.py`, Options > Voice page):
- Microphone: name + NEXT MICROPHONE / WINDOWS DEFAULT; Output: name (ui_audioDevice) + NEXT OUTPUT / APPLY OUTPUT
  (same s_alNextDevice + snd_restart as Options > Audio); mic gain, transmit mode, activation level 0.003..0.2,
  both key binds, voice volume, MIC TEST ON/OFF with the live meter under it.
- Dropped: the free-text Input device field and the duplicate VOICE ON / VOICE OFF buttons (the Voice chat row stays).

## Integrator steps
1. `git apply patches/01-voice-engine.patch` on rel0391 (CRLF file, apply with core.autocrlf=false).
2. `git apply ui-patches/02-voice-options-page.patch` on rel0391 (made on integ039\src analysis_scripts, md5 of the
   base file 266d68102758a19b0e21b9d66b78191e). Rebuild zz_platinum_ui.pk3 (build_platinum_ui.py) + acReleasePaks
   sync, as for any menu change.
3. PC look (DX12 + GL): Options > Voice page layout; MIC TEST ON moves the meter; NEXT MICROPHONE cycles names.
4. Real-mic check needs Gianni (two humans on one server): see SUMMARY.md / thread.

## Patch note line
- Voice chat: fixed voice activation never transmitting on real microphones, and the push-to-talk keys now always
  transmit. Options > Voice now lets you pick your microphone and output device, with a live microphone level meter.
