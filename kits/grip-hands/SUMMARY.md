# Kit gate: grip-hands

- Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (sha256 65f45c7063c94df2; game data v0.39.1-sandbox38)
- Kit checksum: 28b8dbe9dc45d889
- Started: 2026-11-18T20:23:00Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 5 s |
| scan | pass | 13 s |
| toolchain | pass | 0 s |
| windows | pass | 109 s |
| scan-built | pass | 2 s |
| linux | pass | 22 s |
| bots | pass | 422 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1480 | 329 | 4 % / 5 % |  |
| obj_snow | pass | 12 | 11x | 1246 | 255 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 10 s |
| openal-build | pass | 4 s |
| engine-configure | pass | 2 s |
| engine-build | pass | 58 s |
| qagame-build | pass | 10 s |
| cgame-build | pass | 11 s |
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
f74933bb1089f89a64899120e8cae61150b465850c6c4d0a4a9d2292851e8826  game/engine/etl.exe
3407df849732721b2293263680873865ebb23ec5ea00be7c6eabb853ba58f794  game/engine/etlded.exe
c5774cf184b88ea5ee95973db0ebc1a49ba86c759345c17569fc68736b657f24  game/engine/renderer_dx12_x64.dll
30a48b48bda638d4976fda9b290b2292a6d28461981ea46a9a03838cdcd628c7  game/engine/renderer_opengl1_x64.dll
169342ab10592449f6ce4b890fe69c65c7c97c9dba9f7e2a8ee7354ef17979a9  game/tcetest/cgame_mp_x64.dll
e7c14656aee56e210c9be52d92a887b2d7d3560d320149c6bb447a75e3ee1eac  game/tcetest/qagame_mp_x64.dll
fae95cf3d1aa50cf953c7be43bcdfa7797c1aac8d8ca5f29a9447af1174593bb  game/tcetest/ui_mp_x64.dll
1e65518796749b98ca5fbd214bd541098418d5def6f90e3f7c48d48cbd38e7e9  probes/native-combat-probe.exe
bdbc6711e51a160be71135035365eff93f16df58f468eb0a5e4bfae38227c41e  probes/native-content-probe.exe
94e72aa298bea5e04dfe4da4fe4f0d82aa94f4fe0bf99ff9a84761472b3b5222  probes/native-entity-lifecycle-probe.exe
674a2f00cbdec966ac38760db77a83ef1a69806a62fb1fd48f04c4b6a864c718  probes/native-move-probe.exe
52730e99bebe46bcf744dffe2710aba2b42276e55303838171124b9ba9a15070  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T20:32:33Z

Earlier gate: PASSED 2026-11-18T19:31:29Z on TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (data v0.39.0-sandbox37), same kit checksum 28b8dbe9dc45d889.
