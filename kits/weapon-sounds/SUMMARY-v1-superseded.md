# Kit gate: weapon-sounds-0393

- Base: base0391.zip (sha256 65f45c7063c94df2; game data v0.37.3-sandbox33)
- Kit checksum: d528108056c41407
- Started: 2026-11-18T23:42:01Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 13 s |
| toolchain | pass | 0 s |
| windows | pass | 108 s |
| scan-built | pass | 1 s |
| linux | pass | 21 s |
| bots | pass | 403 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1480 | 329 | 4 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1246 | 255 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 10 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 55 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 11 s |
| move-probe-build | pass | 1 s |
| combat-probe-build | pass | 1 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 1 s |
| launcher-build | pass | 9 s |
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=ON, probes run=0

```
fe48bfc0db8c07b8b8c224b5dd8f9954cf364657922489d878ed2dfad5acc60e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
4993b2038a20240421006fb62e1a31b7eb68c29a61dd972f6f2242ebc7bd9ed9  game/engine/etl.exe
ba0f47e2e5b8843b8c4b7b7f335e0ffc0bddcc5af53071f3971ace8d0005b9ce  game/engine/etlded.exe
434d163017f79c631ef3f1fa4b2b12afee330a08bfb135a68ae99ba85f024832  game/engine/renderer_dx12_x64.dll
b29ee4afd9d006f67425bc854439c63570d9a9debb3c79c0ba3ffbe1ea7e00bc  game/engine/renderer_opengl1_x64.dll
3b4887c2d9bf06735be71f58addf9cf1d7bd984713533c5b46a232c082306649  game/tcetest/cgame_mp_x64.dll
96e429f5ff6cb0c3f8f8dbbe875be621ea3d03c91ff6c97dfea168a0e8c40e60  game/tcetest/qagame_mp_x64.dll
c3762f4e3d546216e8b74d11f8bae1915583ea0a4123f8039a1af744bea0f0e3  game/tcetest/ui_mp_x64.dll
f3e2b288d29e4cd30f075ff449a69105052d24917c613ee732a29e84150586f3  probes/native-combat-probe.exe
6b8dea2c0dc329719817cfee86a25e45a05803f3bf9aa8f1d68efdacbca77d19  probes/native-content-probe.exe
da4458eb5873404ae316585ef1d358847aadd321e5efe2a0d38c92fcaacd538f  probes/native-entity-lifecycle-probe.exe
0ce720f7eda00440d652323be728345d82d228cca592fc9f3c0d5a6f98c243a6  probes/native-move-probe.exe
8afb1ff59912823efaf34e29a2c29e72d032319158cb767586b09315e410e3b1  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T23:51:11Z
