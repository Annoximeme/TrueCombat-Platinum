# Kit gate: csh391

- Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (sha256 65f45c7063c94df2; game data v0.38.1-sandbox35)
- Kit checksum: a811fae42ca08227
- Started: 2026-11-18T20:22:58Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 6 s |
| scan | pass | 12 s |
| toolchain | pass | 0 s |
| windows | pass | 59 s |
| scan-built | pass | 2 s |
| linux | pass | 19 s |
| bots | pass | 584 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1475 | 327 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1246 | 255 | 3 % / 4 % |  |
| obj_railhouse | pass | 12 | 11x | 1709 | 346 | 1 % / 2 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 6 s |
| openal-build | pass | 0 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 17 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 10 s |
| move-probe-build | pass | 1 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 0 s |
| launcher-build | pass | 9 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
fe48bfc0db8c07b8b8c224b5dd8f9954cf364657922489d878ed2dfad5acc60e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
72e7b2d8ad01e4f666e015c0e45b826cab2083fdf83bad8bc15c1c8ca9812175  game/engine/etl.exe
8ebc638eef3f64910416a781b4575e555aa4facd3aadc8853b083886e45d6d4f  game/engine/etlded.exe
16bea0dcca1d9335f56aafe4beb954458dda00bc67594cdd7776add9e6b9e8bc  game/engine/renderer_dx12_x64.dll
7adfbb24861be1e7d52fc798b630f94df96c2409f871bcc22faf6c258f5f8c1f  game/engine/renderer_opengl1_x64.dll
70a38475611cb0b8a483af938f79d3eed21721a820947e11b766f239dcbdf7c5  game/tcetest/cgame_mp_x64.dll
c544e4f865046150e1507005438c9fbe2686b6b92ca03d1abcae397791ecdfb4  game/tcetest/qagame_mp_x64.dll
12ccf4a76c66774196dcae1381e7f197cdd74787c82989165169cfb28c3e27d0  game/tcetest/ui_mp_x64.dll
c003dc96e028d23574c1673e523db6815be4762bc493e535fd2b9f2a209adb55  probes/native-combat-probe.exe
629d377a39dd240d28acf63af385d30c961ef1239f12df31bd491f990dcead36  probes/native-content-probe.exe
4c5703648b7e8d7aa02cad3fb633d2e8c622ffb34ff832194ffeae31b4f6beef  probes/native-entity-lifecycle-probe.exe
b7de385c689a4b3ccfd8a156234ee5bb402da9e24e9dd4327e62a4367e9a2c00  probes/native-move-probe.exe
ae2056a9c685d3fcd77c5042f68dd7ce72a790bad6a89c98150b5a483735b829  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T20:34:20Z
