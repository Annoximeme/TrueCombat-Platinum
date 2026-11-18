# Kit gate: muzzle-flash

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.39.0-sandbox37)
- Kit checksum: 14c034eabe51b264
- Started: 2026-11-18T18:15:52Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 7 s |
| scan | pass | 14 s |
| toolchain | pass | 0 s |
| windows | pass | 117 s |
| scan-built | pass | 1 s |
| linux | pass | 23 s |
| bots | pass | 418 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1745 | 329 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1263 | 269 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 10 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 61 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 0 s |
| combat-probe-build | pass | 3 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 0 s |
| launcher-build | pass | 11 s |
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
e8f7a330a5143ed26da108e2f3fc519248a42086dc85c71716f44d678c6da0d8  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
65467c49df11f5a0d1d324cea9a66da1dd25711b9f54f4b4c5a95732fe1fd78c  game/engine/etl.exe
5a70381fe1797e1ae9e17cf2fe6ab642ce27d086124bedc5b56ac80489878d5c  game/engine/etlded.exe
4b09c1c09f6e221f52458121af6c5bde90d56092a46b620070554da27b87ab59  game/engine/renderer_dx12_x64.dll
bb97189b59e2edb65fddc5c81fa8a4ad402462972c718bbbcd719e633acf13a5  game/engine/renderer_opengl1_x64.dll
bf9b485b51d5372f5b7d5399322157a4583350839f5f28b14eeb9d956f7c7f60  game/tcetest/cgame_mp_x64.dll
b6dfb10c3a6cd19e6a7151480cdf110c8fabb9bdfc0bb0768cd19630b707dec6  game/tcetest/qagame_mp_x64.dll
bd13801a0024f6c04e71142e84c9ddbeb68c0aa38eb4e7a5eed7afc4ed19a338  game/tcetest/ui_mp_x64.dll
ef3b61782b9e966971f4a939ee59a94189371b7c5c48bdf84dc8246f29dbedeb  probes/native-combat-probe.exe
1ae08e8c83928f74615e1ac32dca3230f96ea977ae5fe7977a3fee55cd7c5e73  probes/native-content-probe.exe
df829051339da0219478d1a164df1f821f9352f2c520fb19b37c2dbe9888e0ce  probes/native-entity-lifecycle-probe.exe
f2af1f08aceb8a469801a00e85eee4534aa8ec87e579fee3ec42ea4c5f985df8  probes/native-move-probe.exe
920cdf616299a9b4bd4e6e1699726cae7ae0b0261c3fe3bfa7e16eb7f63fe780  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T18:25:32Z
