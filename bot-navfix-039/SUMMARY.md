# Kit gate: kit039s

- Base: base-0390-botflags.zip (sha256 85ffb30b3d49d30c; game data v0.38.1-sandbox35)
- Kit checksum: c25917caca6739b5
- Started: 2026-11-18T13:37:09Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 5 s |
| scan | **FAIL** | 12 s |
| toolchain | pass | 0 s |
| windows | pass | 34 s |
| scan-built | pass | 1 s |
| linux | pass | 19 s |
| bots | pass | 558 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1741 | 329 | 3 % / 3 % |  |
| obj_snow | pass | 12 | 11x | 1262 | 269 | 3 % / 4 % |  |
| obj_railhouse | pass | 12 | 11x | 1709 | 347 | 1 % / 2 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 0 s |
| openal-build | pass | 0 s |
| engine-configure | pass | 0 s |
| engine-build | pass | 1 s |
| qagame-build | pass | 9 s |
| cgame-build | pass | 11 s |
| move-probe-build | pass | 0 s |
| combat-probe-build | pass | 2 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| content-probe-build | pass | 1 s |
| launcher-build | pass | 9 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
0943745925681de94444661623705300488a4cabc7fa899c9f56fc846a553d49  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
1a4108379010d48c68a64c63c180382cbcbab0cbc154a5d3ca2e65e70b44af95  game/engine/etl.exe
b60d63ed08d22e4720232a0319b744ed597fe0c073793a44b87dd3f06ac9c5b1  game/engine/etlded.exe
f4bfdadeeb397a4b4a208dfb5158c41700dbbfc24f2116f5a0ffe7980b53a586  game/engine/renderer_dx12_x64.dll
60167c934177903132fa73c9b83867963f82124907a7420ddc28446a799b8e45  game/engine/renderer_opengl1_x64.dll
25b54dd13f66a5f5f4054f18605e48e8d410097dc9f50a3206256dd44e72eaa7  game/tcetest/cgame_mp_x64.dll
d2253dfe6b0c18b0e5260ba47fec083fc26737f29f05dcb4b45ffc25a9bc3f71  game/tcetest/qagame_mp_x64.dll
2d6198a292c80b009856ba8b34b25b873d2bc7d57c4e2002baf663bc6624468d  game/tcetest/ui_mp_x64.dll
704580110e1e23cfdd16ea8cf084c5463fd6fc73cca948479052e354a07f3902  probes/native-combat-probe.exe
786abaf6a9f6f6cd6151568081f613afdcdf33d742c14fb3a1ed698ee7e0500d  probes/native-content-probe.exe
b124325fc3c54a4d8d1c2e15f66e630b3faec152f489bdfc50067dbf2cbf855f  probes/native-entity-lifecycle-probe.exe
cb055fcd98d6686379045fefa768f34dd4bf3ee007ab5c567a76e10833c4c932  probes/native-move-probe.exe
880450253193d454a0f9016a14e0c97afddab6241d84c90615d350c6739c3ea1  probes/native-prediction-probe.exe
```

**KIT GATE FAILED** 2026-11-18T13:47:38Z

## Notes (kit owner)
- Round 2 (13:37Z): patch 03-bot-snipe-ads.patch added (sniper bots scope at every skill). Replaces the 13:05Z gate (checksum 777294561bd2ef1c).
- scan FAIL is the single known hit in the unmodified 0.39.0 base (analysis_scripts/x64/preflight_release.py, "c2pa label" read from a comment); the release thread said to count this as passed for the rebuild. The kit adds no files the scan flags (scan-built pass).
- Windows probes were built but NOT run: wine in this cloud container crashes since a container restart. The kit only touches qagame bot code; run the native probes on the PC build as usual.
- Base = TrueCombat-Platinum-0.39.0-sandbox37-source.zip (sha256 20e7673f...) + community-maps botflags 01-bot-flagstands.patch (f1969535), packed as one zip.
- Patches: 01-bot-navfix.patch d15cf6164efb69f5fe21673eb1f26fd3e0d4865b71f1d20b3c04ef6cd6f5adf1, 02-bot-lof-free.patch 05b7c0115d43ae7bb3016a4e67a1a7913d4a1122e1158088b838a7cb7a8785d4, 03-bot-snipe-ads.patch b8e31e697d68a963f51132f48b70a9337372acee6417f1c9f1447d97f3a3102a.
