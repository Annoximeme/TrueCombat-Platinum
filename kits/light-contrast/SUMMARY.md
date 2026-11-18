# Kit gate: kvf4

- Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (sha256 65f45c7063c94df2; game data v0.37.3-sandbox33)
- Kit checksum: 54137da049b4eb8f
- Started: 2026-11-18T20:22:50Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 5 s |
| scan | pass | 12 s |
| toolchain | pass | 0 s |
| windows | pass | 112 s |
| scan-built | pass | 1 s |
| linux | pass | 20 s |
| bots | pass | 404 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1480 | 329 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1245 | 255 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 20 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 52 s |
| qagame-build | pass | 10 s |
| cgame-build | pass | 10 s |
| move-probe-build | pass | 1 s |
| combat-probe-build | pass | 1 s |
| prediction-probe-build | pass | 1 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 0 s |
| launcher-build | pass | 8 s |
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
fe48bfc0db8c07b8b8c224b5dd8f9954cf364657922489d878ed2dfad5acc60e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
615d3202f928215cf4013f2f6ed02324f693a849725f95d4eb60494b8a5fa309  game/engine/etl.exe
7d85671b7b14930e9686903fc840f7bc224db065a7c31f35cf3ca2d741e1e198  game/engine/etlded.exe
e5e7eedabbbfb577804e09badbf411f4fb979268d21508c2b69bc3cd122a58ef  game/engine/renderer_dx12_x64.dll
14bd34bd1a53df84b49e9660a4eb284130abc0814a7d10f6f2a8b62c1ef4897c  game/engine/renderer_opengl1_x64.dll
fceb6d99616da36e1e99a60f3851b1f023ecea6a6e56cc0d380399d58dffc7bf  game/tcetest/cgame_mp_x64.dll
12761f0761187530d51db13186b163aba8d3bbff983f5e2bd747fc10f2323de8  game/tcetest/qagame_mp_x64.dll
7c9f7a62c9791f7c4d569877a3f99ac24f3550c49aa38ebd0ca634d9d5bc77c7  game/tcetest/ui_mp_x64.dll
d5a05b5c5398631d369e665dc489376b5d431789a3fa713b2df767729aadf9fd  probes/native-combat-probe.exe
d824fe0a8d47ddd42f23e86acdb760978dbc4b06847bb926516cc25049dafbcc  probes/native-content-probe.exe
8817f94d699c7fcfc443dc987cf8eb73eaedbfa3b7a321530ef5e28d3c270b1e  probes/native-entity-lifecycle-probe.exe
83de1b06533770350c2c5f53712e1f6a7229e9c8e877c2232f37ad44de80c97b  probes/native-move-probe.exe
c0a85f62890a2ab32e7875a8db27e1f3442d1f495fed32d778377848732f1fb4  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T20:32:04Z
