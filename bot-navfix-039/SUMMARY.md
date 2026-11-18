# Kit gate: kit

- Base: base-0390-botflags.zip (sha256 85ffb30b3d49d30c; game data v0.38.1-sandbox35)
- Kit checksum: 777294561bd2ef1c
- Started: 2026-11-18T12:53:01Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 8 s |
| scan | **FAIL** | 11 s |
| toolchain | pass | 0 s |
| windows | pass | 102 s |
| scan-built | pass | 1 s |
| linux | pass | 21 s |
| bots | pass | 599 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1432 | 310 | 3 % / 4 % |  |
| obj_snow | pass | 12 | 11x | 1230 | 264 | 3 % / 4 % |  |
| obj_railhouse | pass | 12 | 11x | 1777 | 347 | 1 % / 2 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 9 s |
| openal-build | pass | 4 s |
| engine-configure | pass | 1 s |
| engine-build | pass | 54 s |
| qagame-build | pass | 10 s |
| cgame-build | pass | 11 s |
| move-probe-build | pass | 1 s |
| combat-probe-build | pass | 1 s |
| prediction-probe-build | pass | 0 s |
| entity-lifecycle-probe-build | pass | 1 s |
| content-probe-build | pass | 0 s |
| launcher-build | pass | 9 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=0

```
0943745925681de94444661623705300488a4cabc7fa899c9f56fc846a553d49  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
bf3394fb543f977e186a145b4f3448c00a8edba9f3f18b70fcb30fa023a41a7e  game/engine/etl.exe
9d1e5e26ea7553a2de69d13f3d92cff26a6084d4ce808caf428a1e47cadc1da2  game/engine/etlded.exe
35ebc19ad347e3e4c98e8c165566f6843123444a44e2c293461fdcdbe94634a4  game/engine/renderer_dx12_x64.dll
76767b57e0b4ad53dce13fbfe8df8df68a9cb484b6e07e289ff981a9142175d2  game/engine/renderer_opengl1_x64.dll
6502b140ee8455991e725539427200a5e7159e1a1be14595f856bcfa0c0dbf71  game/tcetest/cgame_mp_x64.dll
1ca54d76bc0b997fe9c8750b732832889b03295a52b79b11e81e384b993e672b  game/tcetest/qagame_mp_x64.dll
3c72f8fbc200f5987e2935f04537ce31aa829afa8828dec636c231d7941788db  game/tcetest/ui_mp_x64.dll
8c6016e162e0c4cb31a5e935e0be4c96b900e8a89802c94d337c4a46457b8243  probes/native-combat-probe.exe
853c8cdc328524212f3049cea98f1278b440bc2c85e001e2f465ff368dcb0bc5  probes/native-content-probe.exe
801de9ca190de6cd49626936fa0274e59c6229dc37a751f0ec1842d9097e3beb  probes/native-entity-lifecycle-probe.exe
a5fe160f3a368c258bd0e84e0cff3d00bad9a7214be75f6b5acb616c576a645b  probes/native-move-probe.exe
175642073f2b2676cfc12109b2a86a9086d5f4b9119e6dcebb646ea44a78075a  probes/native-prediction-probe.exe
```

**KIT GATE FAILED** 2026-11-18T13:05:23Z

## Notes (kit owner)
- scan FAIL is the single known hit in the unmodified 0.39.0 base (analysis_scripts/x64/preflight_release.py, "c2pa label" read from a comment); the release thread said to count this as passed for the rebuild. The kit adds no files the scan flags (scan-built pass).
- Windows probes were built but NOT run: wine in this cloud container crashes since a container restart (wine cmd itself aborts; probe binaries that passed earlier today crash the same way). The kit only touches qagame bot code; run the native probes on the PC build as usual.
- Base = TrueCombat-Platinum-0.39.0-sandbox37-source.zip (sha256 20e7673f...) + community-maps botflags 01-bot-flagstands.patch (f1969535), packed as one zip.
- Patches: 01-bot-navfix.patch sha256 d15cf6164efb69f5fe21673eb1f26fd3e0d4865b71f1d20b3c04ef6cd6f5adf1, 02-bot-lof-free.patch sha256 05b7c0115d43ae7bb3016a4e67a1a7913d4a1122e1158088b838a7cb7a8785d4.
