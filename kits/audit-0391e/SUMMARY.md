# Kit gate: kitfinal7

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.39.0-sandbox37)
- Kit checksum: 5a660aa3652423e6
- Started: 2026-11-18T18:30:48Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 5 s |
| scan | pass | 14 s |
| toolchain | pass | 0 s |
| windows | pass | 138 s |
| scan-built | pass | 1 s |
| linux | pass | 26 s |
| bots | pass | 415 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1480 | 329 | 4 % / 5 % |  |
| obj_snow | pass | 12 | 11x | 1246 | 255 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 12 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 75 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 12 s |
| move-probe-build | pass | 1 s |
| move-probe | pass | 0 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 6 s |
| prediction-probe-build | pass | 0 s |
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
defd9e974389302499b618cca6c35d498bbd8a790fdf2700c8459c4bd0d73f0f  game/engine/etl.exe
2e7b63d64d0d127fa538c38f62501c249a579d375140237ed80d77491835044c  game/engine/etlded.exe
0dcf188efc3e125a5f7ddea156ac6906cdb507478e5beff09049e82b0f5e8f64  game/engine/renderer_dx12_x64.dll
dde43a9ed5116a7b51821ac81e635c89e323f374e2a44bfb6131db075dea5791  game/engine/renderer_opengl1_x64.dll
d7dfb65060011cab60f0c8be842f778fb29976e2460cd11ca21a02154fbadcae  game/tcetest/cgame_mp_x64.dll
0287e59bbc92574b28ca06b9679932553634bbad73c7f9eb3932e188aa94249d  game/tcetest/qagame_mp_x64.dll
8c906847ad82b74c632013d309f0e02c2a058f3e838bee95d2c38318dcd7db04  game/tcetest/ui_mp_x64.dll
fd1dcc2cbd6f8997df06eb372b428f9c8f91619d447089f7d0bee5d9d13feea5  probes/native-combat-probe.exe
776b6f3f5bd53676c9cf9758f84a84c13cb6a18a7e3ef55e0923e9e458685525  probes/native-content-probe.exe
89331c184fb5c5cf8fd49fd09c667ec0ab2b2add9632c4ce45a0c51297726c02  probes/native-entity-lifecycle-probe.exe
c70e40b142efea6996f5bc80c61d6fa51b15fa5d6518f19d6201398e5ab97dda  probes/native-move-probe.exe
2e0d75977014eb470bd71d184631438db1498c5fdb638db5907b55e9d0a0b200  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T18:40:47Z
