# Kit gate: free-aim

- Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (sha256 65f45c7063c94df2; game data v0.39.1-sandbox38)
- Kit checksum: fb12a6fe61dd3912
- Started: 2026-11-18T23:51:06Z

| Step | Result | Time |
|---|---|---|
| compose | pass | 4 s |
| scan | pass | 14 s |
| toolchain | pass | 21 s |
| windows | pass | 120 s |
| scan-built | pass | 1 s |
| linux | pass | 24 s |
| bots | pass | 411 s |

## Bots soak

| Map | Result | Bots seen | Answered | Hits | Spawns | Server CPU avg / max 15 s | Notes |
|---|---|---|---|---|---|---|---|
| obj_village | pass | 12 | 11x | 1480 | 329 | 4 % / 5 % |  |
| obj_snow | pass | 12 | 11x | 1246 | 255 | 4 % / 5 % |  |

## Windows build

| Step | Result | Time |
|---|---|---|
| openal-configure | pass | 11 s |
| openal-build | pass | 5 s |
| engine-configure | pass | 2 s |
| engine-build | pass | 59 s |
| qagame-build | pass | 11 s |
| cgame-build | pass | 12 s |
| move-probe-build | pass | 1 s |
| move-probe | pass | 4 s |
| combat-probe-build | pass | 2 s |
| combat-probe | pass | 0 s |
| prediction-probe-build | pass | 0 s |
| prediction-probe | pass | 0 s |
| entity-lifecycle-probe-build | pass | 0 s |
| entity-lifecycle-probe | pass | 0 s |
| content-probe-build | pass | 1 s |
| content-probe | pass | 0 s |
| launcher-build | pass | 10 s |
| installer-build | pass | 1 s |
| master-build | pass | 0 s |

Options: DLSS=ON, EAC=OFF, probes run=1

```
fe48bfc0db8c07b8b8c224b5dd8f9954cf364657922489d878ed2dfad5acc60e  game/TrueCombatPlatinum.exe
95b71bda48d846eb6fa5b05cf6c4b0ac5ee69b7108be184af9b537940f587240  game/engine/OpenAL64.dll
e0094f93717c459f363b954f1042799534daa19ee7e9640607adfb545143a1ff  game/engine/etl.exe
d9f0b7cb070718cf459d48cf5937cb14b67bfd1baafee39f26b2665156d92c8a  game/engine/etlded.exe
7efa8763b19a7f3d6e48a08b2bf2efd124fd7b54f0636cb995e95c1c5273fc35  game/engine/renderer_dx12_x64.dll
58eebd15591bfd45c37be6e3c8fe4000e9d7a1628cfb6d3bc83171841f374ef2  game/engine/renderer_opengl1_x64.dll
f9c4b04867e6196c0428acbeb0eb6092bf0d82c1b1e991643f83cde079c1b88a  game/tcetest/cgame_mp_x64.dll
45f6600f3f64fcf3271eae016671fa107532078da48407f3acd936629e8ff049  game/tcetest/qagame_mp_x64.dll
d04ebbf68ca1e9e19b900bbba0fb9624c5e11d6e427542be475ec47595dfd194  game/tcetest/ui_mp_x64.dll
8920a349440dbced971815a425d72e77bb6134161ee547de3923390ef2aa16bb  probes/native-combat-probe.exe
d59cd9a18b323f6b92dad1673a660f73db208cd5b237ebe6241d09218b113bd1  probes/native-content-probe.exe
1471f60d3c6e0cddfa0e5c499ec58881db7af85ce7c647dbb40460d1cdfdc127  probes/native-entity-lifecycle-probe.exe
6dd3349969762de1595ab2870c868f6ada13cfda100bb0a334367ef9a76f2e59  probes/native-move-probe.exe
c461640e32d03d2ceae3bae2f630933b9f8e5170a49eb8c96c88558d4431c2ac  probes/native-prediction-probe.exe
```

**KIT GATE PASSED** 2026-11-19T00:01:01Z
