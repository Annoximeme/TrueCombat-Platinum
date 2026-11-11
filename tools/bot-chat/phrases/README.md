# Bot phrase bank 1.4.0

Offline chat lines for bot call-outs and chatter (bot brain design, idea 10, decision 1).
Written by hand, no language model at runtime, no running cost, no player data leaves the server.

- `phrases.json`: the bank, with metadata per situation. Source of truth for tools.
- `phrases.txt`: the same lines as tab-separated text, easy to parse in C at map load.
- `SITUATIONS.md`: every situation key with its trigger, channel, cooldown and placeholders. Start here when wiring triggers.
- `../chat/`: the C loader and picker (`tcp_bot_chat.h`), its tests and the chat simulator. `../roster/`: the 32 bot personalities.
- `tools/`: the source lists (`*.py` from 1.0.0, `*.bank` text files since 1.1.0) and `build.py`, which rebuilds and validates everything.

## Size

8,829 lines across 323 situations and 5 personalities (entry, anchor, lurker, support, marksman).
Every personality has at least four lines for every situation.

Counted honestly: that is 8,829 entries, with about 6,230 distinct wordings. Roughly a third of the entries
are short common calls ("gg", "Copy.", "one {area}") that several personalities share, because real players
share them too. Contact calls and follow-ups overlap least (about 22%), order replies most (about 52%).

| Group | Situations | What it covers |
|---|---|---|
| contact | 38 | Sightings, counts, sounds, snipers, flanks, height, pushes, fakes, numbers, what the enemy is doing |
| action | 68 | Kills of every kind, movement, utility, executes, trades, cover, ammo, misses |
| damage | 21 | Hits, low health, flashes, friendly fire, how the bot died and what it knew |
| objective | 50 | Bomb, flag and point play, sites, retakes, the clock, post-plant |
| clutch | 5 | Last one alive, and cheering a human clutch |
| round | 63 | Round and match results, score state, joins and leaves, votes, praise, mood |
| orders | 56 | Replies to orders, pings, questions and chat from humans |
| followup | 22 | Lines that refer back to an earlier call or round (see Follow-ups) |

History: 1.0.0 had 74 situations, 1.1.0 added 210, 1.2.0 added 22 follow-ups, filled every thin bucket and
added signature lines per personality. 1.3.0 added 9 situations and moved or removed 190 lines after reading
simulated rounds (see Checked claims). 1.4.0 added 8 situations for flag and deathmatch play and for the clock
(see Game modes) after defence, flag and deathmatch rounds were simulated. No key has ever been renamed.

## Placeholders

| Placeholder | Filled with |
|---|---|
| `{area}` | Area name from `target_location` or the map brain, cleaned first: strip colour codes and a leading "the", fix ALL CAPS (see `tools/area_check.py`, `normalise()`). Lines are written for bare names: "one Shed", "Holding Courtyard." |
| `{count}` | Number of enemies, plain digits. 2 or more in `contact_many`; can be 1 in `clutch_start` ("1v1"). |
| `{name}` | The teammate talked to or about. Trim long clan tags. |
| `{enemy}` | An enemy player's name. |

Each situation lists `always` (the game always has these when it fires) and `maybe` (sometimes known).
Lines do not have to use every placeholder: "lost him" and "lost him near {area}" are both valid for
`contact_lost`. **Rule:** when picking a line, skip any line that uses a placeholder you can't fill.

## Text format

```
@situation  group  channel  cooldown_s  placeholders_always  placeholders_maybe
situation   personality   text
```

Fields are separated by a single TAB. Lines starting with `#` are comments, blank lines are ignored.
`channel` is `team` (say_team) or `all` (say). `cooldown_s` is a suggested minimum gap per bot for that
situation; 0 means it fires on a one-off event and needs no cooldown.

## Runtime rules (suggested, for the team brain step C)

1. **Who talks.** One bot per event per team. Prefer the bot that saw it; for round events pick one at random,
   weighted by the personality's chattiness. Others stay quiet so chat doesn't flood.
2. **Chattiness.** entry 0.8, support 0.8, anchor 0.6, marksman 0.45, lurker 0.35 (chance to speak when chosen).
   Global cap: at most one bot line per team every 1.5 s, and at most 3 per bot in any 10 s.
3. **No repeats.** Keep the last 8 lines used per situation per team and skip them. Pick uniformly from the rest.
4. **Delay.** Wait 0.4 to 1.2 s before sending a call-out (people need time to type). Drop it if it's stale
   (enemy already dead, area already cleared).
5. **Typing style jitter.** 25% of the time lowercase the line and drop the final full stop. Never add typos
   to names or areas. Don't add emoji.
6. **Personality mix.** A bot uses its own personality's list; 10% of the time it may borrow from one other
   personality so voices overlap a little, like real people.
7. **Human pings and orders.** `order_*` and `ping_*` replies always come from the bot that received the order,
   and skip chattiness (an order must always get an answer).
8. **Honesty.** `reply_are_you_bot` always answers yes. Bots never deny being bots.
9. **Never hit back.** `reply_insult` and `reply_blame` are calm by design. Bots never taunt the enemy team by name
   except the friendly lines in `revenge`, `dominated_by` and `killed_by_good`. Make all-chat banter a server cvar
   (suggested `bot_chat 0/1/2`: off, team only, team and all).
10. **Specific beats generic.** When several situations match one event, fire the most specific one
   (`kill_sniper` over `kill_headshot` over `kill_confirm`; `died_to_sniper` over `dead_info`).
11. **Dead bots.** Only `dead_info`, `teammate_down`, `human_clutch_*`, round and match lines once dead.
   In a clutch (`clutch_start` fired), dead bots on that team say nothing except `human_clutch_cheer` once.

## Follow-ups

The `followup` group is what makes chat read like people who remember things: "still Courtyard", "make that 3",
"found him, Shed", "Courtyard again, same as last round", "told you". Each key's description in `SITUATIONS.md`
starts with **Needs:** and names the memory required. In total the game has to keep:

- per bot: its last 4 call-outs (situation, area, count, time), where it died in the last 2 rounds, whether it
  died first, and whether it recently said it missed;
- per team: the last call-out by anyone (for `fu_ack_teammate_call`), open help requests, and what each bot asked for;
- per team across rounds (the commander already has most of this): where the enemy hit in the last 3 rounds, the
  plan used last round and whether it won.

Rules: at most one follow-up per bot per 10 s; `fu_ack_teammate_call` fires for at most one in three calls and never
answers another acknowledgement; `fu_called_it` at most once per round per team. If the memory isn't there, never
fire the key: a wrong "told you" is worse than silence.

## Checked claims

A generic line must not claim something the game has not checked. "one Shed, back turned lol" is only true
if the enemy really is facing away, so that line lives in `contact_unaware`, not `contact_one`. Since 1.3.0:

- `contact_one` and `contact_many` only say where and how many. What the enemy is doing has its own keys:
  `contact_unaware`, `contact_running`, `contact_sneaking`, `contact_static`, `enemy_pushing`, `enemy_lone`.
- `enemy_heard` is footsteps only. Doors are `enemy_heard_door`, reloads are `enemy_reload_heard`.
- `kill_unaware` holds the "he never saw me" kills. `dead_enemy_low` holds "he's one shot" from a dying bot
  and needs 50 or more damage dealt to the killer.
- `round_won_bomb` is neutral. Use `round_won_detonated` or `round_won_defused` when you know which.
- Enemy actions (`enemy_planting`, `enemy_defusing`, `heard_plant`, `heard_defuse`) always say "he" or "they",
  so "Defusing." can never be read as the bot's own action.

The moves and removals are rules in `tools/edits.txt` (`move`, `drop`, `keep`), applied at build time, so the
reasoning stays visible and new lines that break a rule get caught by the same regex.
Since 1.4.0 no line names a map feature the game has not named (roof, window, upstairs, mid): `enemy_above`
only says "above".

## Game modes

The simulator now plays bomb defence, flag and deathmatch rounds too. What reading them changed:

| Rule | Why |
|---|---|
| `kill_carrier` is bomb only, `kill_flag_carrier` is new | "Bomb carrier's dead" was being said in flag matches |
| `time_60`, `time_30`, `time_10` are neutral | "30 sec go" is wrong for the side that wants the clock to run out |
| `time_low` = my side must act, `time_hold` (new) = the clock is on my side | Pick by mode and side: attackers before the plant and a team behind on score hurry, defenders and a team ahead hold |
| `save_call` only when the bomb can no longer be defused | Its lines say "no time, get out"; there is no economy to save for |
| `lead_lost` only if the team was ahead before | "Lead's gone" at 0-1 reads wrong |
| Use `map_start`, not `round_start_generic`, in modes without rounds | Round-start lines talk about "this round" |
| New flag keys: `flag_going`, `flag_defend`, `flag_standoff`, `flag_enemy_returned`, `flag_enemy_captured` | Common flag moments had no line |
| New `kills_to_win` ({count}) | Deathmatch endgame, fire at 5 or fewer |

Never fire these in respawn modes (flag, deathmatch): `last_enemy`, `enemies_left`, `kill_last`, every
`clutch_*`, `numbers_*`, `died_first`, `flawless_round`, `enemy_saving`, and do not fill `{count}` in
`dead_info`. They all assume dead players stay dead.

## Area names

Run `python tools/area_check.py --dir <game folder>` (or `--pk3`, `--bsp`, `--names file`) to read the real
location names from the maps, clean them, flag names that need a short alias and list which lines to skip.
Two runtime rules come out of it: skip a line when a word of the area name already appears in the line
("he's on the roof Roof"), and skip a line whose filled text is over 64 characters.
Not yet run on the six official maps (needs the game folder).

## Tone

Short, like people type mid-fight: "2 at Courtyard", "lost him near Shed", "planting, cover me".
Banter stays friendly; no slurs, no insults, no swearing. Each personality has habits a regular should
recognise after a few rounds (`tools/z4_voice.bank` holds the signature lines):

| Personality | Sounds like | Habits | Example |
|---|---|---|---|
| **entry** | fast, cocky, impatient | "on me", "trade me", "send it", hates waiting | "one Courtyard, send it" |
| **anchor** | calm, full stops, two short sentences | "They won't pass.", "Stay calm.", never chases | "One at Bridge. I'm not moving." |
| **lurker** | lowercase, dry, few words | "btw", "lol", "shh", "give me 5 sec", talks from behind the enemy | "3 Market btw, backs to me" |
| **support** | warm, team-first | "guys", offers smoke and flash, thanks people, apologises | "one at Gate, want a flash?" |
| **marksman** | clipped, precise | lines, angles, range, "Mine." | "One, Tower. Inside my range." |

## Rebuilding

```
python tools/build.py <outdir>
```

It also writes `SITUATIONS.md`. It fails on unknown placeholders, placeholders a situation can't fill, lines over 70 characters, tabs and
em or en dashes, drops duplicates within a situation and personality, and reports any personality with fewer than four lines.

## Adding lines

Add to any `tools/*.bank` file (or a new one) and rebuild:

```
@new_key | group | channel | cooldown | always placeholders | maybe placeholders | description
=e
entry line
=a
Anchor line.
```

`=e =a =l =s =m` start a personality block. A header with only `@existing_key` adds lines to that situation.
