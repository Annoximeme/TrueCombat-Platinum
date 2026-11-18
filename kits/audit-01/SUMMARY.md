# Kit gate: kit

- Base: v0.38.1-sandbox35
- Kit checksum: 3c3c5022e9b35a73
- Started: 2026-11-18T00:32:33Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 7 s |
| scan | pass | 13 s |
| toolchain | pass | 0 s |
| windows | pass | 129 s |
| scan-built | pass | 1 s |
| linux | pass | 22 s |
| bots | pass | 412 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 214 | 51 | 3 % / 5 % |  |
| obj_snow | pass | 12 | 11x | 154 | 50 | 4 % / 8 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 11 s |
| openal-build | pass | 4 s |
| engine-configure | pass | 2 s |
| engine-build | pass | 73 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 10 s |
| move-probe-build | pass | 1 s |
| move-probe | pass | 3 s |
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
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=ON, probes run=1

```
8cd958ef3f8c0b3f7a444164f92031abcd20525a7301e83223ffef7b0fcd1e7a  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
8d47a2a1425b9f9ac9fc69a322294ccc817ef5cfd66cae84b6a99851ce332859  game/engine/etl.exe
43d558af0893b3fa49eeac16efdc5e176ac0f8344a1b4416422b11aa7a8b0ade  game/engine/etlded.exe
0542d793073cc13cfde8989980da7ee526a6d349f5e3d4b1c752dd75d274a8de  game/engine/renderer_dx12_x64.dll
28be67e6351d80be7d1c6023246d21be057c6be4e63bc8e9d07fd094be9a8c77  game/engine/renderer_opengl1_x64.dll
740ad8e5a5fbcd44e284904b0760e1e78b82e33f1e235fdf763a69e32847c24f  game/tcetest/cgame_mp_x64.dll
e63ef2288c6e9ff36bfcf5180303bcbd8e3545bd6d608260402c4b4095fb2caa  game/tcetest/qagame_mp_x64.dll
5df4ba1ac25480e281e207aac707011e11d166d8ef99f45142411e71c7ccff6e  game/tcetest/ui_mp_x64.dll
f4b501925454ffa3b63b28e5917c0c2542154f929f253b95c4ce5b7d6f85af00  probes/native-combat-probe.exe
57893bf394c3a6bbe9b7c5c62b11ffc9dd18d1e0ee3642b1f2b3e154f286af12  probes/native-content-probe.exe
c8623b8a71112390b924623679161c7b434355fa3ed129be4165c59ae5aeb357  probes/native-entity-lifecycle-probe.exe
a45cf338a3e76b543dc3d5997d4afaf0aff3aba5075905c1806c73b189bda8fa  probes/native-move-probe.exe
a25d14e1815a48c6b956698420a69220ec08832e8c10b4aaf6ff932c79d5b0de  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-18T00:42:17Z
