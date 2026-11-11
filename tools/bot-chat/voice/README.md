# Radio voice lines for bot chat

Bots can play one of the game's radio voice lines together with (or instead of) a typed line. This folder maps
chat situations to voice lines in two steps, because the real voice ids are only known from the game files.

| File | What it is |
|---|---|
| `voice_map.txt` | situation, TAB, concept. 146 of the 323 situations have a radio line, through 28 concepts such as `enemy_spotted`, `affirmative`, `need_backup` |
| `tools/voice_build.py` | Rebuilds `voice_map.txt` from `phrases.txt`. The rules and the concept list live here |
| `voice-ids.txt` | concept, TAB, real voice id, checked against the game and corrected by hand |
| `tools/voice_check.py` | Reads the game's `.voice` scripts (loose or inside `.pk3`) and ties each concept to a real voice id |

## Checked against the game (2026-11-11)

```
python tools/voice_check.py --dir "<game folder>" --only tcetest --out voice
```

`--only tcetest` matters: without it the stock engine voice scripts are read too and add ids and captions that
TrueCombat players never hear. The game's own scripts have 49 voice ids. `voice-ids.txt` in this folder is the
result, corrected by hand: 17 of the 28 concepts have a real radio line, 11 stay text only.

Hand corrections to the automatic picks, and why:

| Concept | Automatic pick | Decision |
|---|---|---|
| area_clear | ClearPath ("Clear the area.") | Empty. It is an order to clear, not a report that it is clear |
| on_my_way | Incoming ("Incoming.") | Empty. Players read it as enemies coming |
| sniper | FTProvideSniperCover ("How about some sniper fire?") | Empty. It asks for a friendly sniper |
| regroup | FTReviveTeamMate (stock script only) | Empty |
| cheer | GreatShot ("Nice shot.") | Cheer ("Alright!"), which fits round wins too |
| defusing | none | Empty. DisarmDynamite ("Diffuse the bomb!") is an order, usable later for `who_defuses` |

Captions differ from the stock ones: FireInTheHole is "Frag out.", TakingFire is "I'm taking fire.",
Negative is "Negative.". Unused lines that could get triggers later: DefendObjective, ReinforceDefense
("We need help on defense!"), Move ("Move it!"), CoverMe.

## Suggested runtime rules

- A voice line is extra, never required. Every situation works as text alone.
- Voice only for urgent calls by default: `enemy_spotted`, `need_backup`, `taking_fire`, `fire_in_hole`,
  `man_down`, `bomb_planted`, plus `affirmative` and `negative` as order replies.
- At most one voice line per team every 4 seconds and one per bot every 10 seconds, so the radio never
  becomes a wall of sound. Chat pacing stays as it is.
- When a voice line plays, prefer a short text line with the detail the voice cannot carry ("2 Tunnel").
- Dead bots never use voice.
- The same server setting that turns bot chat down should turn bot voice off first.
