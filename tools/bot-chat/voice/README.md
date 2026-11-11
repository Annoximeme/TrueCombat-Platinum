# Radio voice lines for bot chat

Bots can play one of the game's radio voice lines together with (or instead of) a typed line. This folder maps
chat situations to voice lines in two steps, because the real voice ids are only known from the game files.

| File | What it is |
|---|---|
| `voice_map.txt` | situation, TAB, concept. 146 of the 323 situations have a radio line, through 28 concepts such as `enemy_spotted`, `affirmative`, `need_backup` |
| `tools/voice_build.py` | Rebuilds `voice_map.txt` from `phrases.txt`. The rules and the concept list live here |
| `tools/voice_check.py` | Reads the game's `.voice` scripts (loose or inside `.pk3`) and ties each concept to a real voice id |

## The check that still has to run

```
python tools/voice_check.py --dir "<game folder>" --out voice
```

It writes `voice-report.txt` (what was matched, other candidates, voice lines in the game that no situation
uses yet) and `voice-ids.txt` (concept, TAB, voice id). Read the report, correct `voice-ids.txt` by hand where
the automatic pick is wrong, and leave the id empty where the game has no such line: those situations stay
text only. The exit code is 1 while a concept has no voice id. Tested only on a made-up script so far; it has
not seen the real game files.

## Suggested runtime rules

- A voice line is extra, never required. Every situation works as text alone.
- Voice only for urgent calls by default: `enemy_spotted`, `need_backup`, `taking_fire`, `fire_in_hole`,
  `man_down`, `bomb_planted`, plus `affirmative` and `negative` as order replies.
- At most one voice line per team every 4 seconds and one per bot every 10 seconds, so the radio never
  becomes a wall of sound. Chat pacing stays as it is.
- When a voice line plays, prefer a short text line with the detail the voice cannot carry ("2 Tunnel").
- Dead bots never use voice.
- The same server setting that turns bot chat down should turn bot voice off first.
