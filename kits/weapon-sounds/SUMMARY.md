# Kit gate: weapon-sounds-0393

- Base: base0391.zip (sha256 65f45c7063c94df2; game data v0.39.1-sandbox38)
- Kit checksum: 5750e6f91f3d81d8
- Started: 2026-11-19T00:21:09Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 12 s |
| toolchain | pass | 0 s |
| windows | pass | 99 s |
| scan-built | pass | 1 s |
| linux | pass | 20 s |
| bots | pass | 422 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1479 | 328 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1245 | 255 | 3 % / 4 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 9 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 52 s |
| qagame-build | pass | 9 s |
| cgame-build | pass | 11 s |
| move-probe-build | pass | 0 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 0 s |
| launcher-build | pass | 9 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=ON, probes run=0

```
fe48bfc0db8c07b8b8c224b5dd8f9954cf364657922489d878ed2dfad5acc60e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
e4d66d218e7d242b8d5924a20f1362160b29e6190adc62732e4f14e8192cedcb  game/engine/etl.exe
932941655d429ef8fba0a0416006b6e4caed17610a4ddb7703d9c6ebb43eff9c  game/engine/etlded.exe
f835542638cc0a78cc062a45cf6e407baca3da5aadd5e6d1e0f559bea0de584d  game/engine/renderer_dx12_x64.dll
79c8c9b7fe4ca3cbf5908bd45feecf070807accaaf392e33b5f6f547a81bb196  game/engine/renderer_opengl1_x64.dll
b782867687f27eaa86e7afab4c49a2f94e65b965f5359b4cc611c7c6ea80ca69  game/tcetest/cgame_mp_x64.dll
841a2c92dd48b1a045e8895640129142871cdbf88ad619e89436506633664a5d  game/tcetest/qagame_mp_x64.dll
d01f803ec8a219ba00d7e953c4113129730de19725830fb8e5053520d715ee00  game/tcetest/ui_mp_x64.dll
8fb40e0cfdb25b917b579a0dbd8d4a0ff36155a0525327a03de52fda80467039  probes/native-combat-probe.exe
0929bc243d7451fbf7f75badbb790085695e7e095a086912c5826b601d09e7dd  probes/native-content-probe.exe
3773acbcb9bc4309c5140e3b30915af12b531f0896455b1d803ea685dab6efb4  probes/native-entity-lifecycle-probe.exe
d473b200984d3b22839dc36bb794619163bc93efbca1c75285e249aa8b53cbae  probes/native-move-probe.exe
39dc83fa6b153c2d9f46f75da007d5eca1a8cbc9c559f74657a00dbf8bf03377  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-19T00:30:27Z
