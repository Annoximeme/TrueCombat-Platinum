# Kit gate: stance-smooth

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.39.0-sandbox37)
- Kit checksum: 822630d2fa25776c
- Started: 2026-11-18T18:19:50Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 13 s |
| toolchain | pass | 0 s |
| windows | pass | 115 s |
| scan-built | pass | 1 s |
| linux | pass | 22 s |
| bots | pass | 412 s |

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
| engine-configure | pass | 1 s |
| engine-build | pass | 60 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 12 s |
| move-probe-build | pass | 1 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 1 s |
| launcher-build | pass | 10 s |
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
e8f7a330a5143ed26da108e2f3fc519248a42086dc85c71716f44d678c6da0d8  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
3948d6179b1a12c9b53af90138365b929084e30d84f40c7ea2199860ab8326fe  game/engine/etl.exe
1592dbdbe044e160a9df1d6fffbcf51ccf4469056fe6f401b04bf90ff06daecf  game/engine/etlded.exe
45694601549640e664b38e802ee701e71ec87ffc466a59afa2e7335ef42c1bae  game/engine/renderer_dx12_x64.dll
cb4c2c197a6d015171580b48717aba2d83a3f6bd0afc82dd14c0578c6dfcc4d9  game/engine/renderer_opengl1_x64.dll
0f3dbe27673fe758d58eb07e80d081a5c648956da8ef01c28d564f915b48c372  game/tcetest/cgame_mp_x64.dll
375427d6058d147b370e3e029668b6629010e44c6edcf25f3d9a582090faf955  game/tcetest/qagame_mp_x64.dll
964bf6de990ddb1479e38f8b282accd2c636a15afdc1857669680ad98036935c  game/tcetest/ui_mp_x64.dll
ee6c9a843214ab4f3eca6d6a154f29ce0331eb805644f3a8484c0ed1efb8d842  probes/native-combat-probe.exe
02e541ca33afa7c2949d6c7ce05d6c2371025535d8a5287181e7940c9baa5111  probes/native-content-probe.exe
579d48166f4719932bfcc67813e89ef0ee3bbfb2e2e94244a5ced96aa3d642b1  probes/native-entity-lifecycle-probe.exe
4bae8aef6a771c3c91cc5f5f6f22f94d6d8bf425bfe60dd1d4003be2829a49a9  probes/native-move-probe.exe
6e6be9f77d61e42f4ae23614055085d178b60eacc040cd49d720ea11ea451d58  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T18:29:17Z

## Notes (kit owner)
- Patch 01-stance-smooth-0391.patch sha256 38c674309114bead647788803027c5ce1da2104bdb72091fae11fceeba41c666; cgame only (tcp_viewfx.h, tcp_player_models.h), no pak, no server change.
- Applies on the FINAL 0.39.0 source alone and after audit-0391 09-11, dx12-fixes 03, tacmap-title 01, launcher-patchnotes 01 and muzzle-flash 01 (checked 18:1xZ).
- Gate run with the container's host /usr/include/ogg, vorbis, AL headers moved aside (they leak into the Windows cross-build); no source change.
- Cloud OpenGL client 18:40Z (final 0.39.0 game code with and without the patch, same script): third person, the crouch now eases down over about 150 ms where 0.39.0 snapped in about 2-3 frames; first-person glide eased, same end height. Prone was not reached in this scripted run (the wall behind blocked the prone leg check); prone uses the same code path with 200 ms.
