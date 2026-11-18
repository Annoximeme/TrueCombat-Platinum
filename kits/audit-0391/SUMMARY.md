# Kit gate: kitfinal3

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.39.0-sandbox37)
- Kit checksum: 029a45adb5fc1e22
- Started: 2026-11-18T17:38:42Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 5 s |
| scan | pass | 13 s |
| toolchain | pass | 0 s |
| windows | pass | 138 s |
| scan-built | pass | 1 s |
| linux | pass | 25 s |
| bots | pass | 414 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1741 | 329 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1262 | 269 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 11 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 81 s |
| qagame-build | pass | 11 s |
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
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
e8f7a330a5143ed26da108e2f3fc519248a42086dc85c71716f44d678c6da0d8  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
16cf48ded78cd8da01f177b29e4071df0b32482f1554bc5dac3a8100dd1b9fb9  game/engine/etl.exe
b314cde016a38d121655fc8cf39ec033ea0ca0413019fed08a003de175247866  game/engine/etlded.exe
90336bbe12e6a05dfa63c513b19555ddcd914a5305f3bf338e58d9701d27f4b9  game/engine/renderer_dx12_x64.dll
d33cf0c3d60340bbddf1f60eaa087f65473caffe0c59915d09e452d5c011f098  game/engine/renderer_opengl1_x64.dll
efb68afcd9e1d9fc2568b64693113f3029861bb6a7b1591002b0c73c067c5111  game/tcetest/cgame_mp_x64.dll
81ca8376c25acfa42c2ba0fe02a8fc7a28542d504c4c38d87a46a6a66037af53  game/tcetest/qagame_mp_x64.dll
23933799f88c89443e0fc87d4b2d88a833f190b7f4f60d3e72dca2272c873af1  game/tcetest/ui_mp_x64.dll
e36e1e3768c45df6d184618dbcb95b9df11c4b3d648524bb4c178b6d90430e2f  probes/native-combat-probe.exe
2e90a51c0dc1a0fcf5e421ecfcf3131973eb5a5fed972007beed1c9fac073ab8  probes/native-content-probe.exe
8885a340e7b08553e4c689a8d509fa666087859e4a91e17d15250d561e4e9f3c  probes/native-entity-lifecycle-probe.exe
889458324fee90d988254e7cd5c2d779e56c6b3273d50a2712c1e44d9e7ac4cd  probes/native-move-probe.exe
57f6d64db1c3aa503e035d59c6932f91939c91addb7f52fe947bbdbbeb51e52f  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T17:48:38Z
