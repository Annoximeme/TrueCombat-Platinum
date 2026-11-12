# Native voice chat: build and test on Gianni-PC

**Round 2 (Squad-style), patch sha256 0e4d29be…:** adds the radio sound on team voice and local 3D voice. Run cases a to k again, then l to p below.

## What this is

- **Patch:** voice-chat.patch, a git diff with `-p1`.
  - It applies on top of the 0.34.1 source with online play round 3 applied (engine-game-round3.patch c9e5fdd6).
  - It keeps CRLF line endings. Apply it with `git apply`, with `core.autocrlf=false` and no .gitattributes in the copy.
- **Target:** 0.36.0. Don't put this in the 0.35.0 tree.
- **Gianni's decisions:**
  - native voice in the engine;
  - voice on by default;
  - dead players can't talk to the living.

## Pieces

### Engine (client and server)

**Protocol**
- New `clc_voipOpus` and `svc_voipOpus`, carried inside the normal game packets.
- Protocol 84 is unchanged:
  - The client only sends voice when serverinfo has `sv_voice 1`.
  - The server only sends voice to clients whose userinfo has `cl_voip 1`.

**Server: sv_voip.c**
- The server relays voice but never decodes it.
- Rate limit: `sv_voipMaxFrames` (60 frames per second).
- A queue of 32 messages per receiver.
- `sv_voip 1` is the admin switch.
- `sv_voice` is read-only in serverinfo. It turns to 1 only once the game module has sent its hearing rules.

**Client: cl_voip.c**
- Microphone input uses SDL2 capture at 48 kHz mono. The build uses FEATURE_OPENAL OFF, so SDL is the sound backend anyway.
- Opus: 20 ms frames at 24 kbps, with in-band FEC (forward error correction) and loss concealment.
- Playback goes to raw stream 64 + slot.
- Cvars:
  - `cl_voip 1`
  - `cl_voipVolume`
  - `cl_voipMicGain`
  - `cl_voipUseVAD 0` (open microphone)
  - `cl_voipVADThreshold`
  - `cl_voipCaptureDevice`
  - `cl_voipMuteEnemies 0`
- Commands: `+voip` / `-voip`, `voip_devices`.
- Test aids: `cl_voipTestTone 1` sends a 440 Hz tone instead of the microphone. `cl_voipDebug 1` or `2` prints `TCP_NATIVE_VOIP` lines.

**Extension traps**
- `trap_TcpVoiceMatrix` (qagame tells the engine who hears whom).
- `trap_TcpVoice` (cgame state and mute list).

**CMake**
- ETLBuildClient.cmake includes libs/opus/tcp_opus.cmake when libs/opus/include/opus.h exists, and defines TCP_VOIP.
- Without libopus, the client still builds, just without voice.

### qagame: tcp_voip.h

**Rules**
- Waiting for players, match warmup, end of match, and modes without teams: everyone hears everyone.
- Live round:
  - team only;
  - living players reach their whole team;
  - dead players reach only dead teammates.
- Countdown and round result: the whole team.
- Spectators: only other spectators.
- With `cl_voipMuteEnemies 1`, a player never hears the other team.

**Admin**
- `voicemute <slot|name>`, `voiceunmute`, `voicemutes` (rcon). A mute is kept by cl_guid until the next map.
- `g_voice 0` turns voice off.

### cgame: tcp_voip_cg.h

- The talking list on the left of the HUD.
- The voice sprite over a speaker's head.
- An icon on the scoreboard next to the speaker's name.
- Your own microphone level bar while you talk.
- The existing mute list (`mute`, `unmute`, mute menu) mutes voice as well. Its popup now says "Their chat and voice are off."
- `+voip` is bound once to the first free key of B, H or Z (cvar `cg_voipBinds`).
- `cg_voipHud 0` hides the list.

## libopus

- Use the official libopus 1.5.2 release: https://downloads.xiph.org/releases/opus/opus-1.5.2.tar.gz, or the v1.5.2 release on github.com/xiph/opus.
  - Check its SHA-256 against the value published with the release.
  - It is BSD-3-Clause, so the licence is no problem.
- Unpack it so that `reference/etlegacy/libs/opus/include/opus.h`, `celt/`, `silk/` and `src/` exist.
  - Keep the patch's `tcp_opus.cmake` and `sources.txt` in that folder.
  - sources.txt lists 137 plain-C files from the 1.5.2 tree (float build). It has no SIMD, no DNN, no silk/fixed, and leaves out opus_compare.c. After editing sources.txt, reconfigure CMake.
- Add libopus's COPYING to the third-party licences that ship with the release.

## Build (private copy only)

1. Work in C:\TrueCombatWork\voice.
   - Don't touch the 0.35.0 integration trees (C:\TrueCombatWork\playtest035, playtest036) or the shared release trees.
2. Get the source:
   - Copy the 0.34.1 source tree that already has round 3 applied (the one used for C:\TrueCombatWork\online-play\round3).
   - Or extract the 0.34.1 source zip and apply engine-game-round3.patch.
   - Then apply voice-chat.patch.
3. Add libopus as described above.
4. Build:
   - the engine client and the dedicated server (analysis_scripts/x64/build_native.py, with its BUILD folder pointed inside the private copy);
   - the modules (build_modules.py).
5. Make a test game copy, like round3\game.

## Test (respect C:\TrueCombatWork\suite.lock)

**Setup**
- Wait while suite.lock exists, then create it with this thread's name and the start time. Delete it afterwards.
- Run one local server on UDP **28150**, with sv_voip 1 and g_balanceSkill 0 (otherwise the round-start balancer moves players).
- Run two clients, A and B.
  - A: `cl_voipTestTone 1` and `cl_voipDebug 1`. Holds `+voip` (for example `+voip` from an exec'd cfg, then `-voip` later).
  - B: `cl_voipDebug 2`.

**Pass criteria**

| # | Situation | Expected on B |
|---|---|---|
| a | Waiting for players / warmup, any teams | `TCP_NATIVE_VOIP recv` lines, tone audible in B's sound (wav capture or `s_info`), talking list shows A |
| b | Live round, A and B on different teams | no recv lines |
| c | Live round, same team, A alive | recv lines |
| d | Live round, same team, A dead, B alive | no recv lines |
| e | Live round, same team, both dead | recv lines |
| f | Warmup, different teams, B `cl_voipMuteEnemies 1` | no recv lines |
| g | rcon `voicemute <A>`, then `voiceunmute <A>` | none while muted, back afterwards; A gets the admin message |
| h | B `mute <A name>` | recv lines with muted=1 and no playback, A not in the talking list; `unmute` restores |
| i | rcon `sv_voip 0` | serverinfo `sv_voice 0`, A sends nothing; `sv_voip 1` turns it back on |
| j | Compatibility | the published 0.34.1 client can join the voice server and play normally; the new client can join a server without voice |
| k | Stability | no crash or ERR_DROP in either client, and no "bad command byte" warnings on the server |

- Screenshots: B's HUD with the talking list, B's scoreboard with the speaker icon, and A's own microphone bar.
- Write the results to C:\TrueCombatWork\voice\PC-TEST-RESULTS.md.
- A real-microphone check needs Gianni at the PC, so it is optional.

## PC test result (2026-11-11, Gianni-PC): 11/11 PASS

- Cases a to k all pass. The 440 Hz tone was checked in B's recorded sound output, together with the recv lines.
- The two problems found are fixed in this patch (sha256 190dbd79…):
  - four files had LF hunks;
  - sources.txt listed the silk/fixed files.
- libopus 1.5.2 matched xiph's SHA256SUMS (65c1d2f7…7ce1).
- Not tested yet: a real microphone. That needs Gianni at the PC.
- Report: C:\TrueCombatWork\voice\PC-TEST-RESULTS.md. Screenshots: C:\TrueCombatWork\voice\shots.

## Round 2: Squad-style voice (Gianni, 2026-11-11 23:56Z)

### Radio sound (client, cl_voip_radio.h)

- Team voice goes through a field-radio filter:
  - band-pass 350 Hz to 3.2 kHz;
  - a +5 dB presence lift at 1.8 kHz;
  - soft clipping;
  - a faint hiss.
- A transmission opens with a 30 ms click and closes with a 90 ms burst of squelch, about 250 ms after the last frame.
- `cl_voipRadio 0` gives clean voice.
- The filter response was measured in the cloud:

| Frequency | Response |
|---|---|
| 100 Hz | -44 dB |
| 350 Hz | -6 dB |
| 1 kHz | +2 dB |
| 1.8 kHz | +4 dB |
| 3 kHz | -2.5 dB |
| 8 kHz | -35 dB |

### Local voice

- Key: `+voiplocal`. It is bound once to the first free key of H, Z and N (cvar `cg_voipBinds2`).
- Wire format: bit 7 of gen marks local voice. The server adds the speaker's origin (3 shorts) to local messages.
- Who hears it (qagame):
  - the speaker must be alive;
  - receivers are every player on a team within `g_voiceLocalRange` (1500 units, in serverinfo), enemies included;
  - mutes and `cl_voipMuteEnemies` still apply;
  - `g_voiceLocal 0` turns it off.
- How it sounds (client):
  - full volume within 250 units, fading to silence at the range;
  - panned left or right by where the speaker stands;
  - slightly quieter from behind;
  - no radio filter.
- HUD:
  - a teammate talking nearby shows in the talking list as "name (nearby)";
  - an enemy talking nearby is heard, but never named or marked;
  - your own row says "You (nearby)".

### Tests (same setup: UDP 28150, g_balanceSkill 0, suite.lock)

Record B's output in stereo.

| # | Situation | Expected |
|---|---|---|
| l | A sends the tone on the radio to B, first with `cl_voipRadio 1`, then with 0 | With 1: a click transient at the start of each transmission, a squelch noise burst after A releases `+voip`, and the tone still clearly there. With 0: none of these. |
| m | Live round, A and B on different teams, close together; A holds `+voiplocal` | B gets recv lines with local=1 and hears the tone |
| n | The same, with B moved more than 1500 units away (setviewpos under devmap, or a far spawn) | no recv lines |
| o | A within range, standing to B's left (B turned so A is at about 90 degrees) | B's left channel is clearly louder than the right; mirrored on the other side |
| p | A dead and holding `+voiplocal` | nobody gets recv lines. Also: a teammate's local voice puts "(nearby)" in B's talking list, and an enemy's local voice adds no row. |
