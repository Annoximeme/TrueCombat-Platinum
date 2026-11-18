# Kit gate: kvf2

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.37.3-sandbox33)
- Kit checksum: 4621b7a19f052ad1
- Started: 2026-11-18T18:18:24Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 6 s |
| scan | pass | 11 s |
| toolchain | pass | 0 s |
| windows | pass | 101 s |
| scan-built | pass | 1 s |
| linux | pass | 20 s |
| bots | pass | 405 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1741 | 329 | 2 % / 3 % |  |
| obj_snow | pass | 12 | 11x | 1262 | 269 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 10 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 0 s |
| engine-build | pass | 55 s |
| qagame-build | pass | 9 s |
| cgame-build | pass | 10 s |
| move-probe-build | pass | 0 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 0 s |
| launcher-build | pass | 9 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
e8f7a330a5143ed26da108e2f3fc519248a42086dc85c71716f44d678c6da0d8  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
ef7f6a1782e51b4963e7cc894fb3e46c5a119a14542e85832ccc0aa7f3226a56  game/engine/etl.exe
62dca105f3679b6832bafb94fd0141c7cd06356726873a01876af86c537ae057  game/engine/etlded.exe
905103e3a19faf7e041af866830eb1c351f436dd0515a0e9ba20343b9252b6c0  game/engine/renderer_dx12_x64.dll
5f4e0327efca3900b82fcccbd5c098c20c1c4166e32f21ffeddc9c53941e5057  game/engine/renderer_opengl1_x64.dll
fe852c3c8ed8cadb51df2f632d069ec79c7af6a2b8554c975a187af2a280ecaf  game/tcetest/cgame_mp_x64.dll
1184aa770901cb617b85b6feedffbe456863dc8d183f73e58af73c06b4829b4f  game/tcetest/qagame_mp_x64.dll
96f97bb02bc444f123ee24c19d4c11b993a5b52c9013f3ea79036a02cdc5d0e2  game/tcetest/ui_mp_x64.dll
c87fea08c929548e6cd469a9c5779ffa6d355f69e0c4dde4133d4643d33a4727  probes/native-combat-probe.exe
15670e51523caf1376efd290c55b81f65e91ad96190866428002659074fee0ea  probes/native-content-probe.exe
5d63c639e539b4dd86c64be74b8e3d20a0eeadc11d413e8cd38409e50c3fd40a  probes/native-entity-lifecycle-probe.exe
ac0672cd2b8fdbf41a2dbd0846d86ee0c32fa6fd64af4405e9e3994a1b935c20  probes/native-move-probe.exe
772a16793df61281e0135cfafb0e9571ac110c89a82eda185bdc621b948f1a94  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T18:27:28Z
