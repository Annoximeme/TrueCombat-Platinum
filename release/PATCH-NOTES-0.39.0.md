# TrueCombat: Platinum 0.39.0 patch notes (REBUILD v0390f: + launcher 3.0.2, height maps, audit polish, community polish, bot navfix; verify claims after the gate)

Discord markup, 6 posts, each under 2,000 characters.

```
# TrueCombat: Platinum 0.39.0
Smarter opponents, four classic community maps, a rebuilt launcher and a deeper layer of atmosphere on every map.

## Smarter bots
- Bots now listen. Footsteps and gunfire give away your position, and they remember where they last saw you.
- Bomb mode plays like a real match: attackers agree on a plan and can cover their entry with smoke, defenders hold sites and regroup to retake together.
- Bots choose when to hold, push or fall back, and vary their peeks instead of rushing in one line.
- Teams learn which round plans work on each map and adapt over a session.
- The end of a round no longer causes a brief hitch on servers with bots.
- Bots with sniper rifles now use the scope on every difficulty.
- Bots no longer freeze in front of you while you aim down a scope. If they can't get out of your line of fire, they crouch and keep moving.
- Bots no longer climb the same ledge over and over, and the bomb carrier no longer keeps switching between sites.
- Bots that got stuck at the start of their route, or somewhere with no route (a roof, a pit by a ladder), now find their way out.
- One bot keeps the defuse or bomb pickup job, and bots no longer stand inside you when you stop.
- Bots walk quietly when they know an enemy is close, and round starts with many bots are smoother.
```

```
## Community maps
- Four of the most played TrueCombat:Elite community maps return: Villa 2.1, Shozen, Snowtown and Chlite, playable on Unranked servers.
- Several of their original sounds have been cleaned up and levelled to sit alongside our own ambience.
- Stadtrand gets its second bomb site back: site A now works on every server, Ranked included.
- Community maps have minimaps, tactical maps and loading screens with a map plan, picture and description.
- Bots pick up the flag on Villa 2.1 in Flag Capture.
- The site A crate on Villa 2.1 breaks when the bomb goes off.

## Interface and match screens
- Clearer match screens: map names read properly on the scoreboard and tactical map, round results name the teams ("Terrorists win the round"), and Bomb, Flag and Capture Point objective cards say what to do next.
- Capture Point: the point is marked on the tactical map and the minimap.
- Team Deathmatch and Flag: waiting players see "Deploying in N" instead of "No more deployments this round".
- Spectators of team matches get the team scoreboard and the right status texts.
- The firing range panel no longer overlaps the minimap and says how many targets are up. The FPS counter no longer sits on the minimap.
- Small in-game UI sizes keep all text readable.
- Match end: the podium is lit the same on every map, and the game view dims behind the map vote.
- Kill feed, chat box, vote menu, weapon pickup prompt and first-launch tips no longer overlap or cut off text.
- Flash grenades also blind the minimap, compass and objective card.
- The final-kill replay camera no longer ends up inside the shooter or behind a fence.
```

```
## Graphics
- Smoother baked lighting, with soft shadow edges on walls and floors.
- Trees, bushes, grass and canvas sway gently in the wind.
- Sun shafts and soft glare when looking toward the sun (DX12).
- Wet patches on the ground that reflect the world around them (DX12, Ultra).
- Water ripples from players and gunfire.
- Higher-detail fire and explosions, and smoke lit briefly by blasts and muzzle flashes.
- Brick, cobblestone, gravel and rock gain real depth up close, from height maps that match their lighting (DX12, Ultra).
- Aiming down sights softens the rear of your own weapon while the sights stay sharp (DX12).
- Frost forms at the edges of your view in the cold on Snow and fades indoors.
- Each map gets its own subtle colour mood.
Ranked servers and clan matches keep sun shafts, glare, colour mood, lens frost and lit smoke off, so every player sees the same picture.
```

```
## Combat feel and immersion
- **Focus zoom.** While aiming, hold the right mouse button to steady your view with a slight extra zoom. Release to return to your normal sight picture. With hold-to-aim, the sprint key focuses instead.
- Gear rustles and magazines rattle as you move, and the last round in the magazine ends with a dry click.
- At low health you hear a slow heartbeat that quickens as you near death, sound dulls and colour drains from the world.
- After a long sprint you catch your breath.
- Fallen soldiers settle naturally: bodies fall away from walls, keep a little of their momentum and come to rest along slopes and stairs.

## Player models
- Your sidearm now rides on your right thigh, your knife on your left hip and your grenades on your belt, so everyone can see what you carry.
- The support hand now sits on the handguard on every two-handed weapon in third person.
- When spectating another player, their weapon now moves with them: sprint, aim, sway and bob are all visible.
```

```
## Launcher 3.0.2
- A completely rebuilt launcher: live server cards on the Play page, a new server browser with favourites, recent servers and search, and news with full articles.
- **Friends.** Add friends by code, see who is playing, and join or invite in one click. Optional and off until you turn it on.
- Downloads panel with pause and resume, a dark tray menu with quick play, and update notifications.
- New Accessibility settings: high contrast, larger text, colour-blind friendly markers and reduced motion.
- The launcher is now also available in Dutch.
- Includes the repair improvements from launcher 2.6.2: missing or damaged files are downloaded again automatically, and errors now say what went wrong.

## CQB (experimental)
- CQB spawn rules now apply only in the CQB Rules playlist. Every other mode keeps standard spawns.
- Official #2 (Unranked) now runs with experimental content on: the new CQB weapons are in every match, and Harbour joins the rotation as Team Deathmatch.
- CQB Rules: health regeneration and the Protected and Tank perks are no longer undone by the next hit.
```

```
## Fixes
- Fixed game sound fading away or turning into thumps a few seconds into a match on audio devices set to high sample rates (96 kHz and above).
- Bomb rounds are no longer scored twice when the explosion takes someone with it.
- The bomb's explosion now hurts everyone nearby and counts for the player who planted it.
- SpecOps can no longer plant a bomb they picked up.
- Blocked rotating doors no longer swing backwards on servers.
- Grenades and smoke from the previous round are cleared when a new round starts.
- Players no longer slide down slopes while standing still, and stay planted when running downhill.
- Pulling the pin on a grenade is now audible to you and nearby players.
- Northport's harbour ambience plays again. It had been silent since the original release.
- Smoother movement along the glass fronts on Railhouse, and fewer small freezes the first time a sound or effect is used.
- A "Connection interrupted" notice appears when the server stops answering.
- Recorded demos play back without menus opening over them.
- The M4 SOPMOD sight shows a single red dot at 1440p and 4K.
- Bug reports (F12) at high resolutions no longer say the screenshot is too large to upload.
- The Deployment menu closes when the match ends.
- Replaced an unused system sound that shipped with the original game files.
- We've tightened and expanded our security measures.
```
