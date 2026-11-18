# Kit gate: kitfinal5

- Base: TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip (sha256 8032095307abdbfc; game data v0.39.0-sandbox37)
- Kit checksum: 3372edf7f0ba98fe
- Started: 2026-11-18T18:15:17Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 5 s |
| scan | pass | 14 s |
| toolchain | pass | 0 s |
| windows | pass | 139 s |
| scan-built | pass | 1 s |
| linux | pass | 29 s |
| bots | pass | 415 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1741 | 329 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1263 | 269 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 12 s |
| openal-build | pass | 6 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 69 s |
| qagame-build | pass | 13 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 0 s |
| move-probe | pass | 9 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 0 s |
| prediction-probe-build | pass | 1 s |
| prediction-probe | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| entity-lifecycle-probe | pass | 0 s |
| content-probe-build | pass | 0 s |
| content-probe | pass | 0 s |
| launcher-build | pass | 11 s |
| installer-build | pass | 1 s |
| master-build | pass | 1 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
e8f7a330a5143ed26da108e2f3fc519248a42086dc85c71716f44d678c6da0d8  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
e0cebc96f80a0285c408e9b335805a652edf404d18ba1c292bfa03281ccbc137  game/engine/etl.exe
64d9760eb8814f0eae429610466ff1bf4e5a575a282c0e322ed9741e6ea2c175  game/engine/etlded.exe
189172d7e4ea8546b2579c68cced0a6d0f0a584f9358f005fbb746f237c39e43  game/engine/renderer_dx12_x64.dll
84b95a9de5b39d616e4d98b6b17f6481d74fdbb995a4c0b47a54a9e33a62f966  game/engine/renderer_opengl1_x64.dll
54a7258bd4ee39a17fb749f9e5a59bc4caccc4b1881a98fbfef17a7e7e069045  game/tcetest/cgame_mp_x64.dll
5353cece110d9f0423c095aa273d1fe73c0319ff45fe276e476654779e26c283  game/tcetest/qagame_mp_x64.dll
7a66c1c45a65a1ca95d6973098be1d8a81e0afa5283140cabe8003d67ebce684  game/tcetest/ui_mp_x64.dll
a9ece54141473173c406ef79c3d490ae846f211f7c4268f468fd00bbf049db4d  probes/native-combat-probe.exe
bac4f380fabbc4c7680f441dee01b8a018c502884dfa9a4d7a33ba1969336389  probes/native-content-probe.exe
867d0d7d920cb1725905826d416ef78f2b2738f4cde177fb29df91449341475c  probes/native-entity-lifecycle-probe.exe
0a826c7f0e22b3cc56493ed7a9dad042159d6f9474a6f73704a900a79ff90f2f  probes/native-move-probe.exe
77bd9732023699d2b21d205a0b7252f0e1556705fcaede73dadda73e97b369ab  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T18:25:20Z
