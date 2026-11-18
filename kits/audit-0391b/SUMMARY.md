# Kit gate: kitfinal4

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.39.0-sandbox37)
- Kit checksum: 2cebdc3e6b7cb3a0
- Started: 2026-11-18T18:00:52Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 14 s |
| toolchain | pass | 0 s |
| windows | pass | 121 s |
| scan-built | pass | 2 s |
| linux | pass | 23 s |
| bots | pass | 417 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1741 | 329 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1262 | 269 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 10 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 2 s |
| engine-build | pass | 62 s |
| qagame-build | pass | 12 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 1 s |
| move-probe | pass | 0 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 1 s |
| prediction-probe-build | pass | 0 s |
| prediction-probe | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| entity-lifecycle-probe | pass | 0 s |
| content-probe-build | pass | 0 s |
| content-probe | pass | 0 s |
| launcher-build | pass | 11 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
e8f7a330a5143ed26da108e2f3fc519248a42086dc85c71716f44d678c6da0d8  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
eff3ef7b22e02e9ab4663261424fe71d02f0cd0a744e4e960e6109ed0b4e63cb  game/engine/etl.exe
99fbf1169d6809ed60edb5ce3bd832a1b9d2b2f3f82a03a4279096d96355bb3a  game/engine/etlded.exe
d8ef3fe2f3b9ccd21a2155998b93423785f5aae22de4adb358ac6a703dfd25e9  game/engine/renderer_dx12_x64.dll
cbd3f90e4908483806d357fe7a5cf3f812dd2084f3ea7c29d7ddae97ffbdd688  game/engine/renderer_opengl1_x64.dll
138a7bc6503351994184f6552755e87e303d3936b0ac5638437619c39e8b73d5  game/tcetest/cgame_mp_x64.dll
99bc438dad5471e427f0c993106254c9cf76c577ca94c4c1191215f393cdfb4b  game/tcetest/qagame_mp_x64.dll
e07f45a9a14e9b825a5dc8ba599cd906c8a0955449ebe0ed99871bd30f052c87  game/tcetest/ui_mp_x64.dll
5a19ee0293e180374f9f811464d869f6b335d20fd16a8e130540ca155c547f8e  probes/native-combat-probe.exe
5b5df9500c69d5c44c0adbe06c6b41fdbe21ecabcad6c2fd376a8cc6dab028ab  probes/native-content-probe.exe
8fd94e98ed773f3ad073e3a7de9195cca8dfb4e33c66a89ef99cbcb3ff6dee2a  probes/native-entity-lifecycle-probe.exe
0378d6b1a9cc3fdc87c87f9bad03fd9188ef278b178c5f476cfcf926c224fce7  probes/native-move-probe.exe
bc191c7d26bb18922789a96e34526e5bdef6c885d689e4327554082e5c8a2b41  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T18:10:33Z
