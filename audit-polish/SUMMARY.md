# Kit gate: audit-polish

- Base: TrueCombat-Platinum-0.39.0-sandbox37-source.zip (sha256 20e7673fd96f0b2c; game data v0.38.2-sandbox36)
- Kit checksum: e6227a187e75a48b
- Started: 2026-11-18T12:50:40Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 9 s |
| scan | **FAIL** | 14 s |
| toolchain | pass | 0 s |
| windows | pass | 153 s |
| scan-built | pass | 2 s |
| linux | pass | 28 s |
| bots | pass | 411 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1304 | 283 | 4 % / 5 % |  |
| obj_snow | pass | 12 | 11x | 1205 | 265 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 13 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 2 s |
| engine-build | pass | 74 s |
| qagame-build | pass | 13 s |
| cgame-build | pass | 13 s |
| move-probe-build | pass | 1 s |
| move-probe | pass | 16 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 1 s |
| prediction-probe-build | pass | 0 s |
| prediction-probe | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| entity-lifecycle-probe | pass | 1 s |
| content-probe-build | pass | 0 s |
| content-probe | pass | 0 s |
| launcher-build | pass | 11 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
0943745925681de94444661623705300488a4cabc7fa899c9f56fc846a553d49  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
2457a7cad70e8edf834876d97dcfa46b02f7b79b0d5aa830b05e5d84eeae16e2  game/engine/etl.exe
88c04a5f6282721f7a1011c8610f52aa1cee04ce5417451766ac650989f27516  game/engine/etlded.exe
877d856b6c08efad2d794dd26e2fa8b514e035bbd741126c906278bebb0f3f40  game/engine/renderer_dx12_x64.dll
43f51f48d211add21b1df6003b8e5d0ee3ddbb8dff628c1fd475e3895eeabd46  game/engine/renderer_opengl1_x64.dll
2cb3ff6496cfac852a80a121f4df5319a01416d1a75cdb1f090dc9cc3f776d1c  game/tcetest/cgame_mp_x64.dll
0e479546352e737c3de1042efe41561430c59293562693f7505f7d197d7e545f  game/tcetest/qagame_mp_x64.dll
b5a449a81e9e3ef41ca15cfa129068b11869995ec7a85fdcba5fa69e2d864f72  game/tcetest/ui_mp_x64.dll
1173f66e5013572b84051e17c69ce78a264f07e9f9b9dccbef23461a5ccd1e8d  probes/native-combat-probe.exe
ad75bb49cb30a4814c3cf8d4edf059636f0bebebbe2fc03c3a038c0b8255f058  probes/native-content-probe.exe
209e3be3eff36a2c927194d2b2a5f4095c00654f13bc58d9241dbea5d6e17e29  probes/native-entity-lifecycle-probe.exe
c2e0489700f3646e3cce14e809c8df3798c1503e89af0eaac3cbeadfc39cea27  probes/native-move-probe.exe
c03a142115ced31d647091a360e90f34e4d4cf2a7c0652796033742766ffa418  probes/native-prediction-probe.exe
```

**KIT GATE FAILED** 2026-11-18T13:00:57Z

## Note on the scan step (audit thread, 2026-11-18 13:02Z)
The only failed step is `scan`, with exactly one hit, and it is in the unmodified base, not in this kit:
`analysis_scripts/x64/preflight_release.py: c2pa label` (the release checker's own comment in line 241 that names label
examples). The kit changes C sources of the client game module only. The release thread accepted this for kits gated on
this base zip (its option "c", 12:51Z: "a summary where scan is the only failed step with exactly that one hit counts
as passed for this rebuild"). Every other step passed: compose, toolchain, windows (with the native probes), scan-built
(the built Windows game folder is clean), linux, bots (Village and Snow).
