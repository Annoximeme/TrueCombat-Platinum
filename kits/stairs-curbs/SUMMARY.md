# Kit gate: stairs-curbs

- Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (sha256 65f45c7063c94df2; game data v0.37.3-sandbox33)
- Kit checksum: 8a2eb691263a576f
- Started: 2026-11-18T22:57:31Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 6 s |
| scan | pass | 13 s |
| toolchain | pass | 23 s |
| windows | pass | 112 s |
| scan-built | pass | 2 s |
| linux | pass | 22 s |
| bots | pass | 414 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1398 | 308 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1065 | 259 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 9 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 59 s |
| qagame-build | pass | 10 s |
| cgame-build | pass | 12 s |
| move-probe-build | pass | 1 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 0 s |
| launcher-build | pass | 10 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
fe48bfc0db8c07b8b8c224b5dd8f9954cf364657922489d878ed2dfad5acc60e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
dbcb53de7db307a340c53c852cc8e34b165d03167440332f3abba61a919d79ff  game/engine/etl.exe
02703df3d029c84a51fce5506eace35081772464b6ebc281a8fe7a1d59e54a76  game/engine/etlded.exe
00cb76b4419daa68eb4d6601dc56889ca46229292b217ed6ef35bfa43308c4e3  game/engine/renderer_dx12_x64.dll
1fd57bab5e34eb08dc9c0460304cf878148846373d475c4771bdff42bb4581b0  game/engine/renderer_opengl1_x64.dll
1476d4d9ca1c26985d2f84ddd0f40b8891416b249db1422e2273e432f9ff6210  game/tcetest/cgame_mp_x64.dll
f23c72a8523058be76e02dfd1c24ea36108a48e4dae4574574fd2bc9d675c395  game/tcetest/qagame_mp_x64.dll
649777714fdfe94bab8f79936e8d9cf52d71a92979114050ed2f94e9a85b0091  game/tcetest/ui_mp_x64.dll
5fac9aa577d7b49452d8850430eaebace683e8974f49933709d7dccd9524d967  probes/native-combat-probe.exe
09c3c7e728f9602f9fae1716fb7211580b75ce6026a93fd3718f2a67bd32c3f1  probes/native-content-probe.exe
0ebd342b0a81d6f9bc618c8dfe80c856a68e3250717987547e54db937c284901  probes/native-entity-lifecycle-probe.exe
ea95cb1aabb29b36a5c7a93eb4267f19bcabdc9bbd51cb5c7b3f66bee6839c2e  probes/native-move-probe.exe
8cafe2ddcefbadc3b08bab50972ddf690acba4370c5c0ee8b46f085aba356bae  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T23:07:23Z
