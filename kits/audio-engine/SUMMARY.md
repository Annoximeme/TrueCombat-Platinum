# Kit gate: audio-engine-040

- Base: base0393approx.zip (sha256 93befabbb0926f9c; game data v0.39.2-sandbox39)
- Kit checksum: ce2e7f201a07d7f4
- Started: 2026-11-19T01:44:36Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 6 s |
| scan | pass | 14 s |
| toolchain | pass | 0 s |
| windows | pass | 121 s |
| scan-built | pass | 1 s |
| linux | pass | 25 s |
| bots | pass | 415 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1399 | 308 | 4 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1065 | 259 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 11 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 65 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 12 s |
| move-probe-build | pass | 1 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 1 s |
| launcher-build | pass | 11 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=ON, probes run=0

```
f6251a133f64abb22a6017861f1da07fa9403e43ed13d75f5744c007de66db4e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
7760dd96959b9c532eabacd6112cbfb9488c0813106ff2c5073f0269ced2264a  game/engine/etl.exe
2bdfa6a6e03ac471de5e661ff713bb93012829afd353c331b88241c7a1765f61  game/engine/etlded.exe
d71ff57fa0992c04b3471ab09e7624b8076cb7009fe2dd5189d067a88ee4bff0  game/engine/renderer_dx12_x64.dll
85a2888218128852d5e9bd0eb6923de1e879270162ac3c9e22f4e252b3049aaa  game/engine/renderer_opengl1_x64.dll
69e27965e15d206d887aa82281e3bc91163edfe32c79d9d32602fbc9f3b65ca8  game/tcetest/cgame_mp_x64.dll
578d1f085cb0823e7a4a7cafa103554c71eee75780338cb7b4a9daf3eeb66998  game/tcetest/qagame_mp_x64.dll
54ba37806689f74a6520603ff5b014ee92d3a80d470c7800c249bd79a8eb03c5  game/tcetest/ui_mp_x64.dll
13761fe6f629445f988a7df18b3fba181e70ecd681cab988141ca7d2fbb6bd8a  probes/native-combat-probe.exe
5219d2cb8af95bcfc20b37d1ada6eead0b8ad4f53c98f85465d4680336466535  probes/native-content-probe.exe
19d2f169f5b7478ad37230bbb4049d50fecfce9c4ec00d8923fb4ebfe850584d  probes/native-entity-lifecycle-probe.exe
759d0e09d72b449a4b06fc0ba976b5cb6abd17bd6e79803205e2c72c118550e7  probes/native-move-probe.exe
3ef93839dd0540872fcb60f9b5ece08113f23c8e79564e47efbfb4e0f0ea29e4  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-19T01:54:18Z
