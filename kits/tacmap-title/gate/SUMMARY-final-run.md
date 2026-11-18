# Kit gate: kit391b

- Base: final039 (sha256 folder; game data v0.39.0-sandbox37)
- Kit checksum: f965cf67dcb04d67
- Started: 2026-11-18T17:17:19Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 14 s |
| toolchain | pass | 1 s |
| windows | pass | 145 s |
| scan-built | pass | 1 s |
| linux | pass | 24 s |
| bots | pass | 284 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_villa2_1 | pass | 12 | 7x | 1076 | 213 | 2 % / 2 % |  |
| obj_village | pass | 12 | 7x | 1052 | 219 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 21 s |
| openal-build | pass | 7 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 65 s |
| qagame-build | pass | 12 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 1 s |
| move-probe | pass | 10 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 0 s |
| prediction-probe-build | pass | 1 s |
| prediction-probe | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| entity-lifecycle-probe | pass | 0 s |
| content-probe-build | pass | 0 s |
| content-probe | pass | 0 s |
| launcher-build | pass | 10 s |
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
e8f7a330a5143ed26da108e2f3fc519248a42086dc85c71716f44d678c6da0d8  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
c6e05b0957c3882ca67d4043a84686b75fad915f83b8cb86a82b4cdc9ac5507f  game/engine/etl.exe
d775fd6a35dc8d484d214ad05a6be1d6ee45fb07a1c007e2baf47feae0a13393  game/engine/etlded.exe
ffbdda397635cceab189745257b39b0e67b1c69c23e8f0d545128f04dc65285f  game/engine/renderer_dx12_x64.dll
1b4367ccf5327f783b609f15402b926331b0eb2c66f6e30a87b333ce45a298ca  game/engine/renderer_opengl1_x64.dll
c76102a8be47acdc7376f8c9ff425abe15cc5f8e99eaa1c06084d1881470be6f  game/tcetest/cgame_mp_x64.dll
1efb4f4a1999277721c1fdb62037912e76d34035938bbb8528d43ff29058cdcc  game/tcetest/qagame_mp_x64.dll
5c43f269f2e7c4c3f320773335abb5014ef572e83cd2cc7be39951526216d5b0  game/tcetest/ui_mp_x64.dll
6f65ed28398aedf5bbd697ad8dd4fcbc0b245088f6f5f7a9d8354b413a49d821  probes/native-combat-probe.exe
10dd6a007fdf2b5c4288976c316aeefa000d5598398c5701bc9eb52ef2792dfb  probes/native-content-probe.exe
01971c540585981a2c6a2f28691429db89858405b9e783a7605f874a83f36c25  probes/native-entity-lifecycle-probe.exe
62ac78b5f7b77701d9c916dc307ac271cc28209f32a653409b340784ced2c0e5  probes/native-move-probe.exe
87934fa4cf197a21d8da4b8c9f1c6772b9d302a5b193f5fb0d57f63bfef363b0  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T17:25:12Z
