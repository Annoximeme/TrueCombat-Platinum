# Kit gate: audit-polish

- Base: TrueCombat-Platinum-0.39.0-sandbox37-source.zip (sha256 20e7673fd96f0b2c; game data v0.38.2-sandbox36)
- Kit checksum: e19fdc96b7721b42
- Started: 2026-11-18T14:00:03Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 7 s |
| scan | **FAIL** | 13 s |
| toolchain | pass | 0 s |
| windows | pass | 45 s |
| scan-built | pass | 1 s |
| linux | pass | 29 s |
| bots | pass | 373 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1304 | 283 | 4 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1205 | 265 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 1 s |
| openal-build | pass | 0 s |
| engine-configure | pass | 0 s |
| engine-build | pass | 0 s |
| qagame-build | pass | 12 s |
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
| launcher-build | pass | 11 s |
| installer-build | pass | 2 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
0943745925681de94444661623705300488a4cabc7fa899c9f56fc846a553d49  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
cb33652dc64a7a758ba7aad3191b359d39bdffc236cb13b46b8750bef2a320ee  game/engine/etl.exe
83240e3c030b95211ce7a9028db493894d9fe3f8f8a0b9adae318361051992a3  game/engine/etlded.exe
877d856b6c08efad2d794dd26e2fa8b514e035bbd741126c906278bebb0f3f40  game/engine/renderer_dx12_x64.dll
43f51f48d211add21b1df6003b8e5d0ee3ddbb8dff628c1fd475e3895eeabd46  game/engine/renderer_opengl1_x64.dll
124937ca5135f27446d4e73651516bc8bfe2b4a0b6c5478597ac24dbcd9fb613  game/tcetest/cgame_mp_x64.dll
ea547719147e55aadcd16abfd0fddd54f94aed9d1ab10b668a9ef92bc5c2c85b  game/tcetest/qagame_mp_x64.dll
8d8f3998cbc8569dfe3a7c6652752f8c900606cbcd6cc9ce1f9134c95b4819a6  game/tcetest/ui_mp_x64.dll
43dd617090b68bcb7a5d62b2e41c8f1e4a4beb63218bd89de3d52e469916215d  probes/native-combat-probe.exe
82698f04314126164543da7ea565d14cd16cff1093c5f4934d81705e8e9ac1af  probes/native-content-probe.exe
249445f533017171f8eb7fd7f155e2d88e721efa8d1f2e52f61b2d24608de9bb  probes/native-entity-lifecycle-probe.exe
c0483c8242b8954e0a2b9a144b4bf6edf175280d3f5d8c464683d2efdc6ba29b  probes/native-move-probe.exe
15c3ad51118ee9e1416e87cdaa91f9b0f4feb97e1a501186e84464c739dab58c  probes/native-prediction-probe.exe
```

**KIT GATE FAILED** 2026-11-18T14:07:51Z

## Note on the scan step (audit thread, 2026-11-18 14:09Z, second cut with patches 06-08)
The only failed step is `scan`, with exactly one hit, and it is in the unmodified base, not in this kit:
`analysis_scripts/x64/preflight_release.py: c2pa label` (the release checker's own comment in line 241 that names label
examples). The kit changes C sources of the client game module only. The release thread accepted this for kits gated on
this base zip (its option "c", 12:51Z: "a summary where scan is the only failed step with exactly that one hit counts
as passed for this rebuild"). Every other step passed: compose, toolchain, windows (with the native probes), scan-built
(the built Windows game folder is clean), linux, bots (Village and Snow).
First cut (patches 01a-05 only): checksum e6227a187e75a48b, gated 13:00:57Z, same result.
