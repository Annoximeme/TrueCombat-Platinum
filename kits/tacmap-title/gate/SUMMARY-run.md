# Kit gate: kit391b

- Base: t391c (sha256 folder; game data v0.38.2-sandbox36)
- Kit checksum: f965cf67dcb04d67
- Started: 2026-11-18T15:46:25Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 3 s |
| scan | **FAIL** | 15 s |
| toolchain | pass | 0 s |
| windows | pass | 125 s |
| scan-built | pass | 1 s |
| linux | pass | 25 s |
| bots | pass | 253 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_villa2_1 | pass | 12 | 7x | 1047 | 215 | 2 % / 2 % |  |
| obj_village | pass | 12 | 7x | 824 | 193 | 4 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 11 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 66 s |
| qagame-build | pass | 12 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 0 s |
| move-probe | pass | 1 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 0 s |
| prediction-probe-build | pass | 1 s |
| prediction-probe | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| entity-lifecycle-probe | pass | 0 s |
| content-probe-build | pass | 0 s |
| content-probe | pass | 0 s |
| launcher-build | pass | 10 s |
| installer-build | pass | 2 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
0943745925681de94444661623705300488a4cabc7fa899c9f56fc846a553d49  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
aaafce058b2d35b1b9f4c02fa690ea2d9085cbe106ff38e548e1f74f2faee393  game/engine/etl.exe
f50dd44e1d2508df360f794f2a0df69b0a0102eb22b6aeab40c53874cf1a0d42  game/engine/etlded.exe
e0422cef8b3a4b5dcd4663c1c380e01c4cceb1c4e2d1d645db596612020921af  game/engine/renderer_dx12_x64.dll
d2badcc9aa5e8aff4e49313900ce4e04a3d857f850b0fc3afdd9dfc652e9074d  game/engine/renderer_opengl1_x64.dll
b72d1f46fd8f7eece777592e661adebbd57776d18bb0260753f04b9911422d75  game/tcetest/cgame_mp_x64.dll
5e21075714b1ba111c3654660bc0ae047428c866eece1845947d2819b059c22e  game/tcetest/qagame_mp_x64.dll
665244ed98da694cc23c8f1a7560ab84e9b04b8df2b7b8794c9cebef52e8ca65  game/tcetest/ui_mp_x64.dll
68ccf8381d79a80d02e62cfc1172431dcb9dad08baf178285626ad34dccca36b  probes/native-combat-probe.exe
09584f21cd3e00e18271f8f2c456f311a0003741d55f8a9af94a060f181aa7d6  probes/native-content-probe.exe
690a2d71de26b17b1528c9f4089ed27e69564799e4faec9a5842b1ffb0d84067  probes/native-entity-lifecycle-probe.exe
9476d622b909f1e17a1980e9909f470b8a0e334d85a2926b952593acefc35518  probes/native-move-probe.exe
6a748250943329c4f74cb8cc13d68d505c9b6cb2bc0f1aff6e0b32e254016ee9  probes/native-prediction-probe.exe
```

**KIT GATE FAILED** 2026-11-18T15:53:27Z
