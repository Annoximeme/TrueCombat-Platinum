# Chlite site B shutters open (sliding doors), for 0.39.2 (kit chlite-shutters)

Thread "Make bots smarter in matches". This is a bug fix, so it goes in a 0.39.x patch release (Gianni wants all bug fixes in the patch releases). It missed the 0.39.1 cut-off, which closed early, so it's queued for 0.39.2 (coordinator, 18:41Z). Re-gated on the published 0.39.1 source. It is the game-code part of 0.40 bot kit patch 02 (integ040/kits/bot-ideas-040/patches/02-bot-maps-040.patch). That patch still applies on top: its tcp_game.c hunks are identical, so drop those hunks there, or apply 02 with `git apply --exclude=game_src/native/tcp_game.c` after this kit.

## 1. Kit
| file | sha256 | use |
|---|---|---|
| patches/01-sliding-doors.patch | 1b9fb0add71ab7b75abb48f6b79060116d48b0fdbed2a28611a3ca38d3b9aa09 | `git apply -p1` at the repo root, on the published 0.39.1 source. Changes one file: game_src/native/tcp_game.c (qagame, server). CRLF is kept. |

**KIT GATE PASSED 2026-11-18 20:34Z on the published 0.39.1 source** (TrueCombat-Platinum-0.39.1-sandbox38-source.zip, sha256 65f45c70…), kit checksum a811fae42ca08227, every step pass (probes built, not run: wine in the cloud container): [SUMMARY.md](SUMMARY.md). Rebased from the 0.39.0 version: one hunk that changed nothing (a line rewritten with identical text) was dropped; the code is the same. The 0.39.0 version and its gate (18:50Z, d04a38d696c86bcb) are in old-0.39.0/.

## 2. Extra build steps
None. Server game module only: no cgame, UI, paks, engine or protocol change. The client already draws moving brush entities (the door uses the same entity state as the map's moving platforms).

New server cvar: `g_slidedoors 1` (archived, latched). 0 = every sliding door is a fixed wall, as in 0.39.0 and 0.39.1.

## 3. What it fixes
- **The bug:** the game spawned every `func_door` (sliding door) as a fixed wall. Only rotating doors (`func_door_rotating`) worked.
- **Where it shows:** only Chlite uses sliding doors; no stock map and no other community map has one. Chlite's bomb site B sits behind two roll-up shutters, so in 0.39.0 nobody, players or bots, can get into site B. A third shutter (the west hall) was shut too.
- **The fix:** sliding doors now work like the rotating ones.
  - Press use and they slide in the map's "angle" direction (-1 = up) by their size less "lip", at "speed" (400 units/s by default). On Chlite that's about 0.25 s.
  - They close after "wait" seconds (2 by default); toggle doors stay open until used again.
  - They stop rather than close on a player.
  - They use the map's door sounds ("type" key).
- **What stays shut:** doors that a map script unlocks (a "key" lock or a targetname, such as Chlite's lockpick fire door near site A) stay shut as before, because map scripts are not rebuilt.
- **Bots:** they already open doors on their route and plan through them, so they use the shutters too.
- **Server log:** a `TCP_NATIVE_SLIDEDOOR` line per door at map load.
- **Still for 0.40:** the other Chlite bot problems (attackers circling on their spawn balcony, site A only reachable with a vault) are fixed in the 0.40 bot kit, not here. Until then, keep Chlite off Bomb in the rotation for bot-filled servers.

## 4. Test checklist (in-game pass)
Columns: `map | renderer | cvars/commands | look at | pass rule | shot`

- obj_chlite | either | bomb mode, walk to bomb site B and press use on a roll-up shutter | the shutter | it slides up quickly with a door sound, you can walk in, and it comes down after about 2 s (or stays up, for the toggle one) | y
- obj_chlite | either | stand under an open shutter until it closes | the shutter | it stops on you instead of closing through you | n
- obj_chlite | either | `g_slidedoors 0` + map_restart | the shutters | fixed walls again, as in 0.39.0 | n
- any stock map | either | normal play | doors | no change (stock maps have no sliding doors) | n

## 5. Cloud evidence
Linux server from the FINAL 0.39.0 source with this patch, Chlite, 12 bots, 3 minutes per mode:
- All 3 shutters load as doors (TCP_NATIVE_SLIDEDOOR, 102-116 units up, 0.26-0.29 s).
- Bots opened them 5 times in a Bomb run; Bomb 78 kills and TDM 35 kills in 3 minutes.
- No errors.

## 6. Public patch notes line (suggested)
- Chlite: the roll-up shutters at bomb site B now open, so site B can be attacked again.
