# Kit gate: ak-twohand

- Base: TrueCombat-Platinum-0.39.2-sandbox39-source.zip (sha256 2a53f0894fbc5913; game data v0.39.2-sandbox39)
- Kit checksum: 0f65acfbea25f47b
- Started: 2026-11-19T01:24:49Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 5 s |
| scan | pass | 13 s |
| toolchain | pass | 0 s |
| windows | pass | 126 s |
| scan-built | pass | 1 s |
| linux | pass | 22 s |
| bots | pass | 420 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1398 | 308 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1065 | 259 | 4 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 20 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 60 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 0 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 1 s |
| launcher-build | pass | 9 s |
| installer-build | pass | 2 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
f6251a133f64abb22a6017861f1da07fa9403e43ed13d75f5744c007de66db4e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
216a50196d0295f1ab27f19287d50158b35fb294498840cac8307ce2fe055295  game/engine/etl.exe
e5eae3c0555c9e67fdd77305d01b76dd135c1bbfb69f3119266d60f6965e6fc3  game/engine/etlded.exe
886c499917e708be4e09247622ff01c2566290b6769e781849ca35d109884e9e  game/engine/renderer_dx12_x64.dll
ec1dc135a8d95d4c0743f9c586dabfb1536d7fe381bfcec31699fd52539c3b5f  game/engine/renderer_opengl1_x64.dll
2b532b8ea33ff190bad43a76fc327aae635927122640e5829043f33f94c6e12c  game/tcetest/cgame_mp_x64.dll
97ae4c943cb32dbdb6e5a944d60ff5da453da9cd5c6454c17d9c46aef00bfab6  game/tcetest/qagame_mp_x64.dll
b1ca002a97d73bb40b61c6e0cb193c94b1cf055ae5d700b0e20984d3ba695770  game/tcetest/ui_mp_x64.dll
41ab08cf500e29479e03b9606fc26a3d68d65ed3686ccbc71190f14a0500c673  probes/native-combat-probe.exe
d7655ff4a24caf3df5ea8e045e1c3b4867d9f0e6b59a2223595763b58f2612e1  probes/native-content-probe.exe
46d3c8d29a283784a5ce8bfc0bad3616598b2dafa766fb34a113bffac3694893  probes/native-entity-lifecycle-probe.exe
5cd2743ae0cb9b79415843624a86fcd044fc9884360346208572478687f2cc8d  probes/native-move-probe.exe
cf9c2727790a2bcf0508e814258891dfc7e9e74652ed2b81e593d947f6f1841d  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-19T01:34:36Z
