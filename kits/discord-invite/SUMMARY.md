# Kit gate: discord-invite

- Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (sha256 65f45c7063c94df2; game data v0.39.1-sandbox38)
- Kit checksum: 1d05921746caf16e
- Started: 2026-11-18T20:23:03Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 11 s |
| toolchain | pass | 0 s |
| windows | pass | 132 s |
| scan-built | pass | 1 s |
| linux | pass | 20 s |
| bots | pass | 429 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1479 | 328 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1245 | 255 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 19 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 56 s |
| qagame-build | pass | 10 s |
| cgame-build | pass | 11 s |
| move-probe-build | pass | 1 s |
| move-probe | pass | 12 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 1 s |
| prediction-probe-build | pass | 0 s |
| prediction-probe | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| entity-lifecycle-probe | pass | 0 s |
| content-probe-build | pass | 1 s |
| content-probe | pass | 0 s |
| launcher-build | pass | 9 s |
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=ON, probes run=1

```
f6251a133f64abb22a6017861f1da07fa9403e43ed13d75f5744c007de66db4e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
7b00781cebbdcb59f52b72528c751328f133a684d30f64cb58af7cb83b750ec5  game/engine/etl.exe
28cf83abc5baeeec3066ad43e99823772ce60a11593e427ff1f1d18fe1294d72  game/engine/etlded.exe
6355fe4bbae6cc9082ebad78d2ec3e9e86b168ce73c7fb391748e4f92b119120  game/engine/renderer_dx12_x64.dll
28360eafd4620faef080f190cb25f465c4430be2ff1e98d987bd8769be52d643  game/engine/renderer_opengl1_x64.dll
89015e3a64bfbefa92b174890a25ccdafcb03502fc1c8865e43d044dbce34a3b  game/tcetest/cgame_mp_x64.dll
b54b1762196430f5841e0ecbe1b86158957eccfdb0959ce3880b827abb02a6c1  game/tcetest/qagame_mp_x64.dll
3bf49313d28a666b78a0253a982e893bac702b62f9d3eed5b577dac29561d1e1  game/tcetest/ui_mp_x64.dll
ca27cbc5a47909b7908d4e546a961103b8ee359862a0b267fc2826a4364e76cf  probes/native-combat-probe.exe
7d96ec0e95ef8ff51d41b31272f7a46f7ece982f62043410d024fe4117509d84  probes/native-content-probe.exe
ad39603f2e8ee743961c6efa0825460b8ca67b7f484f6cf46b679aa2f9787be6  probes/native-entity-lifecycle-probe.exe
be16da93deb812872e8c3942d755652886b696176a6d22e810b5d062322326cc  probes/native-move-probe.exe
9b0a441462222a995b1128b41255b1f72f1b3d1f9fd9074e8c84e903d0f78fbd  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T20:33:00Z
