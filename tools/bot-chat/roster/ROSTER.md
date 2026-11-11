# Bot roster 1.0.0

The 32 existing bot names, each with a fixed personality that stays the same across matches, so regulars can learn them.
Numbers are 0 to 100. They multiply the utility weights of the bot brain (design idea 7); `chatty` and `lower` feed the chat picker.
Edit the table in `tools/roster_build.py` and rebuild.

## Entry

| Bot | Plays like | Sounds like | Weapon | Aggr. | Patience | Team | Chatty |
|---|---|---|---|---|---|---|---|
| **Viper** | Always first through the door. Re-peeks the same angle once too often. | Never waits; types fast and lower-case. | smg | 95 | 15 | 55 | 85 |
| **Blaze** | Sprints the first 10 seconds of every round. Chases kills too far. | Loudest bot on the team. Celebrates every kill. | rifle | 90 | 20 | 45 | 90 |
| **Havoc** | Loves close corners and tight rooms. Weak at range. | Short and blunt. | shotgun | 85 | 25 | 60 | 70 |
| **Cobra** | Jiggle-peeks before committing. The careful entry. | Calls his peek before he takes it. | rifle | 80 | 35 | 65 | 65 |
| **Jackal** | Takes the fight even when outnumbered. | Cocky. Says 'ez' more than he should. | smg | 88 | 20 | 40 | 75 |
| **Vandal** | Pushes through smoke. Throws his frag early. | Announces every grenade. | rifle | 82 | 30 | 50 | 60 |
| **Storm** | The entry who waits for the flash. Best paired with a support. | Asks for a flash, then goes. | rifle | 78 | 40 | 75 | 80 |

## Anchor

| Bot | Plays like | Sounds like | Weapon | Aggr. | Patience | Team | Chatty |
|---|---|---|---|---|---|---|---|
| **Warden** | Never leaves his site. Last to rotate. | Calm, full sentences, always a full stop. | rifle | 25 | 95 | 70 | 60 |
| **Rook** | Locks one lane with the machine gun and stays crouched. | Few words. Reports, never chats. | mg | 30 | 90 | 65 | 50 |
| **Bishop** | Holds the cross angle and covers the other anchor. | Gives the team instructions: 'Hold.', 'Don't peek.' | rifle | 35 | 85 | 80 | 65 |
| **Kodiak** | Sits close to the objective and makes you come to him. | Dry. Unbothered when he dies. | shotgun | 40 | 80 | 60 | 45 |
| **Sierra** | Rotates early on good information. Plays the retake well. | Clear rotate calls. Thanks people for info. | rifle | 30 | 88 | 85 | 70 |
| **Wolf** | The anchor who takes one early pick, then falls back. | Tells you when he gives up ground. | rifle | 45 | 75 | 70 | 55 |

## Lurker

| Bot | Plays like | Sounds like | Weapon | Aggr. | Patience | Team | Chatty |
|---|---|---|---|---|---|---|---|
| **Ghost** | Walks everywhere. Shows up behind you two minutes into the round. | Almost silent. When he talks, it matters. | smg | 50 | 90 | 25 | 25 |
| **Shadow** | Waits for the team's push, then hits the back. | 'give me 5 sec'. Timing talk. | rifle | 55 | 85 | 30 | 35 |
| **Lynx** | Fast lurker. Takes the long way round at a run, then goes quiet. | Dry humour. 'lol' after a backstab. | smg | 65 | 70 | 35 | 40 |
| **Mamba** | Sits in one off-angle per round and never the same one twice. | Tells you where he is hiding, once. | rifle | 60 | 80 | 30 | 30 |
| **Nomad** | Roams between lanes and feeds the team information. | More info calls than kills. Says 'btw' a lot. | rifle | 45 | 75 | 45 | 45 |
| **Onyx** | Hides close to the bomb after the plant. | Barely speaks. One-word answers. | shotgun | 70 | 65 | 25 | 20 |
| **Reaper** | Hunts the last enemy alive. Good in the clutch. | Quiet until the clutch, then asks for silence. | rifle | 75 | 60 | 30 | 35 |

## Support

| Bot | Plays like | Sounds like | Weapon | Aggr. | Patience | Team | Chatty |
|---|---|---|---|---|---|---|---|
| **Sparrow** | Always second in. Throws the flash for the entry. | Friendliest bot. Thanks and encourages. | smg | 40 | 60 | 95 | 90 |
| **Tango** | Smokes the crossing every round and re-smokes when it fades. | Counts down his utility. | rifle | 45 | 55 | 90 | 85 |
| **Yankee** | Trades the entry within a second or two. | 'I'll trade you'. Calls who he is behind. | rifle | 50 | 50 | 85 | 80 |
| **Frost** | Stays with the bomb carrier and covers the plant. | Calm helper. Offers to carry or defuse. | rifle | 35 | 70 | 90 | 70 |
| **Puma** | The aggressive support: flashes for himself when nobody goes. | Chatty. Apologises quickly. | smg | 55 | 45 | 80 | 85 |
| **Saber** | Suppresses a lane so others can cross. | 'Covering, cross now.' | mg | 45 | 65 | 88 | 65 |

## Marksman

| Bot | Plays like | Sounds like | Weapon | Aggr. | Patience | Team | Chatty |
|---|---|---|---|---|---|---|---|
| **Falcon** | Holds the longest line on the map. Relocates after every shot. | Clipped. 'Mine.' | sniper | 30 | 90 | 50 | 45 |
| **Raven** | Counter-sniper. Looks for the enemy scope first. | Calls the enemy sniper before anything else. | sniper | 35 | 85 | 55 | 40 |
| **Talon** | Aggressive scope. Peeks first, repositions late. | Admits his misses. | sniper | 50 | 70 | 45 | 50 |
| **Mako** | Rifle on single fire at range. Switches to the scope on long maps. | Talks range and lines. | rifle | 40 | 80 | 60 | 45 |
| **Hunter** | Covers the bomb from distance after the plant. | Tells the team which line he has. | sniper | 45 | 75 | 65 | 55 |
| **Ranger** | Overwatch for the entries. Shoots what they flush out. | 'Go. I have the angle.' | rifle | 35 | 88 | 70 | 50 |

## Team mix

When filling a team, pick one of each personality before repeating one: entry, support, anchor, lurker, marksman.
A five-bot team then has every voice in chat and every role on the map. On maps with no long lines, swap the marksman for a second support.
