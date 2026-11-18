# Kit gate: launcher-patchnotes

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.39.0-sandbox37)
- Kit checksum: d5fb4f94e62ce116
- Started: 2026-11-18T17:55:20Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 14 s |
| toolchain | pass | 0 s |
| windows | pass | 131 s |
| scan-built | pass | 2 s |
| linux | pass | 29 s |
| bots | pass | 431 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1741 | 329 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1262 | 269 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 10 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 71 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 1 s |
| move-probe | pass | 0 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 1 s |
| prediction-probe-build | pass | 0 s |
| prediction-probe | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| entity-lifecycle-probe | pass | 0 s |
| content-probe-build | pass | 1 s |
| content-probe | pass | 0 s |
| launcher-build | pass | 12 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
fe48bfc0db8c07b8b8c224b5dd8f9954cf364657922489d878ed2dfad5acc60e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
204c7ea69450c58d1b49e7533f077eda186a89ae9b83592aafeea0df31b552db  game/engine/etl.exe
8a881f797ff2de24e79324878819bbc8cd53c96a528c221bf55c991a2193172b  game/engine/etlded.exe
ebdb59e3adc9c85cf26b040733444abeaf9d80c8bf2fa5d964c8c9879db20f5b  game/engine/renderer_dx12_x64.dll
6428eb3db7a3b3f1c80c64b6bdcfb1f65ea38d50b9f7752e0c4d6b7ff800036a  game/engine/renderer_opengl1_x64.dll
051dedbe5a1a669054f4f1d13a21197ee9497846a3ad49706334f17b54a5433e  game/tcetest/cgame_mp_x64.dll
1f972a547c2b2db19a826444db11fba8f3d1b1acadff915b4779dea4d127b78d  game/tcetest/qagame_mp_x64.dll
fe5c2d81075dd9268ce1a9ca7eaac6107127565ec21a1e67626c2d47dd3a6431  game/tcetest/ui_mp_x64.dll
d8cb4d6b5d03c0864dedc77134540d16492b1be88f4000d5f7b2a487497df7cb  probes/native-combat-probe.exe
f8fcb4625faff1f27537f5bf013a667bcf1179ed30e0afa9909a289fba062412  probes/native-content-probe.exe
f4fc0284a9e511eadf2a489f8686c2d94cd1f4d932da4dafd16f1d40fdb1d7d0  probes/native-entity-lifecycle-probe.exe
27f2ff7d67c3b6fd00f0119f4aa5b23363adc796f637247472a725aa7f3d0728  probes/native-move-probe.exe
16d0522de457f86a6bb82910717b04bf889dc0acd876513bcb1035128ef07fa5  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T18:05:31Z
