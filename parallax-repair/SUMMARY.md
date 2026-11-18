# Kit gate: par039

- Base: 0.38.0-v0380l-source.zip (sha256 175a1a83347a57a0; game data v0.37.3-sandbox33)
- Kit checksum: 0b7797e6d045631a
- Started: 2026-11-18T12:26:15Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 11 s |
| toolchain | pass | 1 s |
| windows | pass | 107 s |
| scan-built | pass | 1 s |
| linux | pass | 20 s |
| bots | pass | 403 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1493 | 286 | 2 % / 3 % |  |
| obj_snow | pass | 12 | 11x | 1261 | 260 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 18 s |
| openal-build | pass | 4 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 52 s |
| qagame-build | pass | 9 s |
| cgame-build | pass | 10 s |
| move-probe-build | pass | 1 s |
| combat-probe-build | pass | 1 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 1 s |
| launcher-build | pass | 7 s |
| installer-build | pass | 2 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
8cd958ef3f8c0b3f7a444164f92031abcd20525a7301e83223ffef7b0fcd1e7a  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
b775da602260eaa129b23514acf2dc3826a26e43b5d438e6225cd928007d5e4c  game/engine/etl.exe
3c9093f836ce9604a0347c9611f7bcf5e3e1a51006eb580bfcc0ed0ff7ab6529  game/engine/etlded.exe
cc0946804cd7aff09757b44199fa6977e9841e49bc227f4f7f9507397db99ada  game/engine/renderer_dx12_x64.dll
ad181ef9967e8860922c3a0743e6781f881616eaef1017eee5bda306ddad3a35  game/engine/renderer_opengl1_x64.dll
2e364faac5d3c1da2c6a2cb1f6be1be2eb3b9bef662b6e708ddcc8b1c04cfd6c  game/tcetest/cgame_mp_x64.dll
c1d8a4c0a5bd931d2e8704977b99105098413c40de38568b43fdd250943853d6  game/tcetest/qagame_mp_x64.dll
24c5218152caefe3c1539abb7b9f20c43f4f4aa42f585c80c3225294f13a74c0  game/tcetest/ui_mp_x64.dll
76987f1ac73b8f61dc6ae53719047a650c53bb9a7cdce0bbed4aa1c8d5f9c011  probes/native-combat-probe.exe
4a40e8ac925ddf426149c07d9d2cff29d73549584596efa6acb244868c63229f  probes/native-content-probe.exe
55f8303f095530fe7784582b45b38ed0aee2a35a27ea3df0a9d84521b152b284  probes/native-entity-lifecycle-probe.exe
c01aeea985fc0e9257f1a9cec721a831898d9a34098efdfbc80c7cf197a1153c  probes/native-move-probe.exe
9a557fc068d415a7916e46535ceb4b14bfe50908b6c4a555efa9a6659f280afe  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T12:35:22Z
