# Kit gate: kg3921kit

- Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (sha256 65f45c7063c94df2; game data v0.39.1-sandbox38)
- Kit checksum: c5d76d8202287bb1
- Started: 2026-11-18T20:22:52Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 5 s |
| scan | pass | 15 s |
| toolchain | pass | 0 s |
| windows | pass | 127 s |
| scan-built | pass | 1 s |
| linux | pass | 25 s |
| bots | pass | 414 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1481 | 329 | 4 % / 5 % |  |
| obj_snow | pass | 12 | 11x | 1246 | 255 | 5 % / 6 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 11 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 68 s |
| qagame-build | pass | 12 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 0 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 1 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 0 s |
| launcher-build | pass | 11 s |
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
fe48bfc0db8c07b8b8c224b5dd8f9954cf364657922489d878ed2dfad5acc60e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
4083913ea417adde85ab92a9a6174e2e820abe8d4eb400aff062e840e34553b5  game/engine/etl.exe
b381681d9488db21a56e82eec286ff6b451bcfe62aba2c5618b24b0dd99784c0  game/engine/etlded.exe
3b67497936e8f719e319f3025e47f6eb10ea14ad4ac5ce1824b4d7435df84e64  game/engine/renderer_dx12_x64.dll
fe2db1d7a46c1d565026b39a5bf96b35dbd372e804b571b02376ab91bf3d2d7b  game/engine/renderer_opengl1_x64.dll
ada5d15a302b6e3cb87e80c9cd23b0f20b18e05021c51bfff46da7f6d277f1a9  game/tcetest/cgame_mp_x64.dll
9ea31e8e72f46f2b220abfa30694bbbd46eda52918c4a6cbeb849b27a45852a2  game/tcetest/qagame_mp_x64.dll
5508b877bdcf269495bae3b6237f02ca8cf997a78b600a8b43d47bd0118ffc2a  game/tcetest/ui_mp_x64.dll
7dbb7db8014b4f8c6769e81d63b7de230ef3f8996f99bb3e1ed5d7a7011c01c3  probes/native-combat-probe.exe
766955df07f0e5d47b4df8ed3f03abae92c16836fb2e31c2acd5a38a8d3317d0  probes/native-content-probe.exe
1065d86d4c8dff8092515724d962d94770bb8ad6810b75a1dd7c62c29e2dd7e4  probes/native-entity-lifecycle-probe.exe
6c4256469006174e5070eb8a3118da06a75d846f261ee974c0213906869b75d9  probes/native-move-probe.exe
dbcdaed86d019786c3f521ec326e1a51129ebd887ea6efaae2cc45e25932bd47  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T20:32:39Z
