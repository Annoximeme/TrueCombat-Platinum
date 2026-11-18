# Kit gate: k391f

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.37.3-sandbox33)
- Kit checksum: 8314fe8b5f42408c
- Started: 2026-11-18T17:17:31Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 12 s |
| toolchain | pass | 0 s |
| windows | pass | 109 s |
| scan-built | pass | 1 s |
| linux | pass | 21 s |
| bots | pass | 408 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1741 | 329 | 2 % / 3 % |  |
| obj_snow | pass | 12 | 11x | 1262 | 269 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 18 s |
| openal-build | pass | 4 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 52 s |
| qagame-build | pass | 10 s |
| cgame-build | pass | 10 s |
| move-probe-build | pass | 1 s |
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
90d87e035961ecb1529a76de469ee69be2b91eaaf05245ba34e6aef4e1975c2d  game/engine/etl.exe
af9d69d1b98b036e66e3b565954bebf5d8f35550377948bedfd9818f45189b27  game/engine/etlded.exe
d6e2beddff8b240eeb175e81cddbc63277c52ab7554961a7f7ca3a01c8755099  game/engine/renderer_dx12_x64.dll
938dce1a497a43db8d35d1e1668b1206f2bb3163b6136623a0706f1078ee755c  game/engine/renderer_opengl1_x64.dll
313b2c5e9dd75962ced005da2cee3eaeb480f2939b54daa01c336d09cdfc50f0  game/tcetest/cgame_mp_x64.dll
796acfdbd4a586d9fb15acf413c507cbb43e6741a5463cbc04032374c5f9baa7  game/tcetest/qagame_mp_x64.dll
7c7e3612e6e1a8616522d7483e8f44f20f23f876127b81489ac990854755ac60  game/tcetest/ui_mp_x64.dll
3d2d2ff961b04246c34494866295753f7bd6f0a6512299996741e47ec228d9f0  probes/native-combat-probe.exe
a853e9518022e72b7477d071bb1cadf1ee3e714c724f1ac4b1610ce20a832eaf  probes/native-content-probe.exe
ce0207b38e65fce9564de628428f432bd21545fc10c0fca910898687405f75c6  probes/native-entity-lifecycle-probe.exe
1441d26d8b5ad70bd974d370dc83e4ff2968ccd510b770f0d93f6148e88869cd  probes/native-move-probe.exe
90c18ab4f1c4b333a96d54587c68991e9c0cd5dacfaf1cdbc3cb398707a13fe9  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T17:26:46Z
