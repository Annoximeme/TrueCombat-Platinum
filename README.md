# TrueCombat: Platinum

A native 64-bit Windows rebuild of TrueCombat: Elite, rendered with DirectX 12,
with an OpenGL Safe Start option and optional NVIDIA DLSS/DLAA.

Developed by RaziC* — Team Terminus.

**Website:** [truecombat.eu](https://truecombat.eu) · **Discord:** [discord.gg/7Dg4yhhvGF](https://discord.gg/7Dg4yhhvGF)

## Download

Get the latest version from [Releases](../../releases/latest). Download
`TrueCombat-Platinum-…-Windows-x64.zip`, extract the whole folder to a writable
location (for example Documents or Games) and run `TrueCombatPlatinum.exe`.

The launcher checks for new versions and updates itself from the update bar
above the PLAY button, downloading only the files that changed. Your settings,
profile and server data are kept.

## Status

Platinum is in active development. Version 0.31.0 brings the full TC:E weapon
roster with original recoil, spread and penetration, seven game modes, bots,
3D sound, the Deployment Menu, map voting, lag compensation, ranks and server
admin tools. Leaning, ladders, swimming and spectator mode are still to come,
and Easy Anti-Cheat is prepared but not switched on. Play between separate PCs
over the internet has not been fully verified yet. Everyone in a match must run
the same version.

The full patch notes for every release are on the
[news page](https://truecombat.eu/news.html) and the release pages.

## Built on

The Platinum Engine is built on [ET: Legacy](https://www.etlegacy.com) by the
ET: Legacy team, which continues the Wolfenstein: Enemy Territory engine source
code released by id Software. Wolfenstein: Enemy Territory is by Splash Damage
and id Software. TrueCombat: Elite, the game Platinum rebuilds, was created by
Team Terminator. The engine is released under the GNU GPL v3, like the code it
grew from.

## Source code

Each release includes its patch notes, a READ-ME and the matching game source
code (`source/native-sandbox-source.zip`), with the GNU GPL v3 and the third-party license
notices in the `licenses` folder. Original game data and
artwork keep their original terms.

## In this repository

| Path | What it is |
| --- | --- |
| `docs/` | The truecombat.eu website (English, with Dutch under `docs/nl/`). |
| `tools/website/` | Site builder: release sync, patch notes, roadmap (`roadmap.json`), weapons and the Dutch translation. |
| `tools/server-bridge/` | The web API behind the Servers and Leaderboards pages: server list bridge, player stats and ranks, and the server-side stats uploader. |
| `.github/workflows/website.yml` | Rebuilds the site whenever a release is published or edited, when the site tools change, and once a day. |

To rebuild the site locally (Python 3.12):

```
python tools/website/release_sync.py
python tools/website/build.py
```
