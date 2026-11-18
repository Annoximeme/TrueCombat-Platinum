---
title: Front lines
date: 2026-11-18
summary: Bots that listen, plan and retake together, four classic community maps, a rebuilt launcher with friends, and a new layer of light, weather, sound and body language across every map. The full story of update 0.39.0.
image: img/devlog/front-lines-teaser-clean.webp
tag: Update
kicker: Update 0.39.0
version: 0.39.0
---
![Update 0.39.0 key art: Front Lines](img/devlog/front-lines-teaser.webp "Update 0.39.0: Front Lines. Stadtrand, Ultra preset, DirectX 12.")

Most updates add things you can point at. 0.39.0 is mostly about the moments between shots: the scrape of someone repositioning behind a wall, light breaking through a doorway on Snow, a defending team that waits for each other before it retakes a site instead of dying one at a time. Those are the moments that made TrueCombat:Elite feel tense twenty years ago, and they are the moments we wanted to deepen.

It is also one of our largest updates so far. Thirteen separate pieces of work went into this release, from the way bots think to the way a fallen soldier comes to rest on a staircase, alongside a launcher rebuilt from the ground up and four community maps that many of you have asked about since Platinum began. This is the long version of the story, with everything we changed and why.

## Opponents that think

Bots have been part of Platinum since the start, and for a long time their job was simple: find an enemy, shoot it, find the next one. That works for warming up. It does not feel like a match. For 0.39.0 we rebuilt how bots perceive the round, how they decide what to do and how they work as a team.

### They listen now

Footsteps and gunfire now carry information. A bot that hears you running on the other side of a wall knows roughly where you are, even without seeing you, and acts on it: it turns to face the sound, holds an angle or moves to cut you off. When a bot loses sight of you, it no longer forgets you exist. It remembers where you were last seen and plays around that position, checking the corner you disappeared behind instead of walking past it.

Walking, crouching and choosing when to make noise therefore matter against bots in the same way they matter against people. Sprint across an open courtyard on Village and the defenders will know about it.

### Bomb rounds that play like a match

Bomb mode got the most attention. At the start of each round the attacking team agrees on a plan: which site to hit, which route to take and who goes first. Attackers move as a group, can cover their way in with smoke and spread out around the charge once it is planted, so a single defender can no longer collect them one by one as they walk through the same doorway.

Defenders hold their sites instead of wandering. When they are outnumbered they fall back, and when the bomb goes down they gather and retake together. That one change made the biggest difference in our test matches. Attacking bots used to win almost three rounds out of four, mostly because defenders arrived one at a time. With defenders that regroup, bomb rounds against bots are now close to even.

![Bots pushing onto a bomb site on Snow](img/devlog/front-lines-bots-snow-push.webp "Attackers move onto a site together on Snow.")

![Defenders moving in to retake a site on Snow](img/devlog/front-lines-bots-snow-retake.webp "Defenders gather and move in to retake the site.")

### Decisions, not reflexes

In a fight, bots now weigh whether to hold, push or fall back, based on their health, how many teammates are nearby and how the round is going. They vary their peeks instead of swinging out of the same corner at the same height every time, and they will sometimes wait for you to make the first move.

Each team also keeps track of which round plans have worked on each map and adapts over a session. If a route keeps failing on Stadtrand, the bots try something else in the next rounds. Play a long session against them and you will notice they stop falling for the same trick.

![A bot rushing through a Village side street](img/devlog/front-lines-bots-village.webp "The final kill of a round on Village, seen in the round replay.")

### Smoother rounds

Some of you noticed a short hitch at the end of rounds on servers with bots. We tracked it down to the moment bots recalculate their routes for the next round, and that work is now spread out so the server no longer stalls. Servers that run bots should feel smoother from round to round.

### Out of your way

Bots also got a round of navigation fixes. They no longer climb the same ledge over and over, and a bomb carrier sticks to one site instead of switching back and forth. A bot that gets stuck at the start of its route, or ends up somewhere with no route at all, like a roof or the pit by the Railhouse ladder, now finds its way out. One bot keeps the defuse or bomb pickup job instead of two bots swapping it, and bots no longer stand inside you when you stop on the spot they were heading for. Close to a known enemy they walk quietly, and round starts with a full server of bots are smoother.

One fix many of you will feel straight away: bots no longer freeze in front of you while you aim down a scope. If they can't get out of your line of fire, they crouch and keep moving. And bots with sniper rifles now use the scope on every difficulty.

## Four classics return

Villa 2.1, Shozen, Snowtown and Chlite were among the most played community maps in the TrueCombat:Elite years, and they are the maps we were asked about most when Platinum began. All four now ship with the game, so any server can run them and you can play them against bots offline.

We left the maps exactly as their authors made them: the same layouts, the same textures and the same spots you remember. What we did change is sound. Several of the original sounds were recorded at low quality or played far too loud next to Platinum's own ambience. We cleaned them up, levelled them to sit alongside the rest of the game and left out a few we had no right to ship. Both bomb sites on Villa and Chlite now work as their authors intended, and the site A crate on Villa 2.1 now breaks when the bomb goes off.

The four maps also get everything the core maps have: a minimap, a tactical map and a loading screen with a map plan, picture and description. On Villa 2.1 and Shozen, bots now pick up the flag in Flag Capture.

![Villa 2.1](img/devlog/front-lines-villa.webp "Villa 2.1 in the evening, Ultra preset, DirectX 12.")

![Snowtown](img/devlog/front-lines-snowtown.webp "Snowtown, Ultra preset, DirectX 12.")

![Shozen](img/devlog/front-lines-shozen.webp "Shozen, Ultra preset, DirectX 12.")

![Chlite](img/devlog/front-lines-chlite.webp "Chlite, Ultra preset, DirectX 12.")

The four community maps play on Unranked servers. Ranked stays on the core map pool for now, so every ranked match is played on maps that have been balanced for it.

### Stadtrand gets its second site back

While we were fixing bomb sites on the community maps, we found that the same problem had quietly disabled site A on Stadtrand. From 0.39.0 both sites work again, on every server, Ranked included. Stadtrand plays like a two-site map for the first time in a very long time.

![Stadtrand with both bomb sites on the HUD](img/devlog/front-lines-stadtrand-bomb-hud.webp "Stadtrand: sites A and B both on the HUD again.")

## Light, weather and water

The second big theme of 0.39.0 is atmosphere. None of these changes alter how a gunfight plays out, but together they make the maps feel like real places at a real time of day.

### Softer light

Baked lighting is smoother, with soft edges where shadows fall across walls and floors instead of the hard stepped lines of the original lightmaps. The difference is easiest to see on flat walls in the afternoon sun.

![Lighting before](img/devlog/front-lines-lightmap-before.webp "Before: the original baked shadows on Village.")

![Lighting after](img/devlog/front-lines-lightmap-after.webp "After: the same corner with smoothed lighting in 0.39.0.")

### Wind, sun and wet ground

Trees, bushes, grass and canvas tarps now sway gently in the wind, with trunks and walls staying still. On DirectX 12, sunlight breaks through gaps in the scenery as soft shafts, and looking toward the sun gives a gentle glare. Wet patches on the ground pick up reflections of the world around them on the Ultra preset, and brick, cobblestone and rubble gain real depth up close: mortar lines and joints sink into the surface when you look along a wall.

![Wet ground reflecting the harbour on Harbour](img/devlog/front-lines-harbour-wet.webp "Wet patches pick up reflections on Harbour, DirectX 12 Ultra.")

Each map also gets its own subtle colour mood. Snow is a little colder, Delta a little warmer. It is deliberately understated: the goal is a sense of place, not a filter.

### Water, fire and smoke

Water now ripples when players wade through it and when rounds hit the surface. Surface after a swim and drops run down the edges of your view for a few seconds. Fire and explosions are far more detailed, and smoke lights up briefly with every blast and muzzle flash, so a firefight inside a smoke screen now glows orange from within.

### Frost on Snow

On Snow, frost slowly gathers at the edges of your view while you are outside and melts away when you step indoors. It stays at the edges of the screen, never in the middle where you aim.

![Frost at the edges of the view on Snow](img/devlog/front-lines-lens-frost.webp "Frost gathers at the edges of your view outdoors on Snow.")

### A level field on Ranked

Atmosphere should never decide a ranked match. On Ranked servers and in clan matches, sun shafts, glare, colour mood, lens frost and lit smoke are switched off, so every player sees the same picture regardless of their settings. Wind, softer light, ripples and the detail improvements stay on everywhere because they do not affect what you can see.

## Closer to the soldier

The third theme is the soldier you play and the soldiers you see. TrueCombat has always been about deliberate, grounded combat, and a lot of small things were missing that make a body feel real.

### Sound you carry

Your gear now makes noise as you move: a quiet rustle with every step, louder when you run, and a magazine rattle when you sprint. The last round in a magazine ends with a dry click, so you know you are empty before you look at the counter. All of these sounds are built from recordings the game already ships, so they sit naturally next to the original weapons.

### Low health and fatigue

Drop below a quarter of your health and a slow heartbeat sets in. It quickens as you get closer to death, sound dulls and the colour drains from the world. After a long sprint you catch your breath for a few seconds. None of this changes your aim or movement: it tells you how you are doing without another number on the screen.

### Gear you can see

What you carry is now on your body for everyone to see. Your sidearm rides on your right thigh, your knife lies flat on your left hip and your grenades hang from your belt. Together with the rifle on your back, which arrived in 0.34.0, an enemy can now read your loadout at a glance.

![Rifle on the back and grenades on the belt](img/devlog/front-lines-holster-rifle-back.webp "Rifle on the back, grenades on the belt, sidearm on the thigh.")

![Pistol holstered on the thigh with a rifle in hand](img/devlog/front-lines-holster-pistol-thigh.webp "With a rifle in hand, the pistol rides on the right thigh.")

### Hands where they belong

This one goes back to the original game. In TrueCombat:Elite's third-person animations, the support hand never actually held the rifle: it hovered beside the barrel or below it, in every stance, on every two-handed weapon. We rebuilt the arm in eleven sets of rifle animations, from standing to crouch-walking and firing, so the left hand now rests on the handguard, with a small per-weapon adjustment for each gun. The Shorty shotgun is now held one-handed, as it should be. First person is unchanged.

![Third-person grip before](img/devlog/front-lines-grip-before.webp "Before: the support hand floats beside the AK-47.")

![Third-person grip after](img/devlog/front-lines-grip-after.webp "After: the support hand holds the handguard.")

### How soldiers fall

Fallen soldiers now come to rest naturally. A body that dies against a wall falls away from it instead of through it. A soldier shot while running keeps a little of their momentum and slides a short way before stopping. On slopes and stairs, bodies lie along the ground instead of floating above it, and arms, legs and heads settle onto whatever is beneath them. It is a small thing until you see a body draped down a staircase in Railhouse for the first time.

### Watching a teammate

When you spectate a teammate after dying, their weapon now moves the way it does in their own view. You see them sprint with the gun lowered, raise their sights, sway and bob as they move. Following a good player is now far more readable.

## Focus zoom

For riflemen there is a new layer to aiming. While aiming down your sights, hold the right mouse button to steady your view with a slight extra zoom, and release it to return to your normal sight picture. If you use hold-to-aim, the sprint key focuses instead while you are aimed in.

Focus zoom is purely a zoom: weapon sway, spread, recoil and movement are exactly the same as without it. It works on every server running 0.39.0, Ranked included.

## Sound that holds

On audio devices set to high sample rates, 96 kHz and above, game sound could fade away or turn into dull thumps a few seconds into a match. 0.39.0 ships a newer version of the audio library the game uses, and we tested it on every common rate up to 384 kHz. If you had switched your headset to 48 kHz just to play Platinum, you can switch it back.

Northport's harbour ambience plays again. The map has always asked for it, but the sound itself was missing from the original release, so the harbour has been silent for almost twenty years. We also replaced an unused system sound that shipped with the original game files.

## Launcher 3.0

The launcher has been rebuilt from the ground up, and it is the first thing everyone sees, so we took our time.

The Play page now shows live server cards with the current map, players and ping, and Play always tells you where it is going to take you. The server browser gains tabs for favourites, recent servers, friends and LAN, a search bar, player bars and a side drawer with the full roster, and it can join a full server the moment a slot opens. News opens as full articles with images.

![The new Play page in Launcher 3.0](img/devlog/front-lines-launcher-play.webp "The new Play page: live servers, news and quick play in one place.")

### Friends

Friends lets you add each other with a friend code, see who is playing and on which server, invite each other and join in one click. It is entirely optional: it stays off until you turn it on, you choose what others can see, and turning it off removes your friends data.

![Friends in Launcher 3.0](img/devlog/front-lines-launcher-friends.webp "Friends: add each other by code, see who is playing, join in one click.")

### The details

The tray icon has a dark menu with quick play, the firing range and settings, and notifications now carry the game icon. A downloads panel shows progress and speed and lets you pause and resume, and a resumed update never downloads finished files again. Settings gain a search box, a graphics preview you can drag to compare presets and a new Accessibility tab with high contrast, larger text, colour-blind friendly markers and reduced motion. Screen readers can now read the launcher's pages, rows and buttons. The launcher is also available in Dutch, alongside English, German, French and Polish.

Launcher 3.0 also includes the repair work from launcher 2.6.2: missing or damaged game files are downloaded again automatically, and when something goes wrong, the error now tells you what happened.

## A clearer HUD

We went through every game mode screen by screen and fixed what got in the way. Map names now read properly on the scoreboard and the tactical map, round results name the teams ("Terrorists win the round"), and the Bomb, Flag and Capture Point objective cards tell you what to do next. In Capture Point the point is marked on the tactical map and the minimap, and in Team Deathmatch and Flag a player waiting for the next wave sees when they deploy instead of being told there are no more deployments.

Smaller things add up too: spectators of team matches get the team scoreboard, the firing range panel and the FPS counter no longer sit on the minimap, small UI sizes keep all text readable, the match end podium is lit the same on every map, and the kill feed, chat box, vote menu and weapon pickup prompt no longer overlap or cut off text. Flash grenades now also blind the minimap, compass and objective card, and the final-kill replay camera no longer ends up inside the shooter or behind a fence.

## Close quarters

CQB remains experimental while we bring it up to the standard of the core game. In 0.39.0, CQB's spawn rules apply only in the CQB Rules playlist, so every other mode keeps standard spawns even with experimental content enabled. In CQB Rules, health regeneration and the Protected and Tank perks are no longer undone by the next hit.

From this update, Official #2 (Unranked) runs with experimental content on: the new CQB weapons are in every match there, and Harbour joins the rotation as Team Deathmatch.

## Fixes

- Bomb rounds are no longer scored twice when the explosion takes someone with it.
- The bomb's explosion now hurts everyone nearby and counts for the player who planted it.
- SpecOps can no longer plant a bomb they picked up.
- Blocked rotating doors no longer swing backwards on servers.
- Grenades and smoke from the previous round are cleared when a new round starts.
- Players no longer slide down slopes while standing still, and stay planted when running downhill.
- Pulling the pin on a grenade is now audible to you and to players nearby.
- Smoother movement along the glass fronts on Railhouse, and fewer small freezes the first time a sound or effect is used.
- A "Connection interrupted" notice appears when the server stops answering.
- Recorded demos play back without menus opening over them.
- The M4 SOPMOD sight shows a single red dot at 1440p and 4K.
- Bug reports (F12) at high resolutions no longer say the screenshot is too large to upload.
- The Deployment menu closes when the match ends.
- We've tightened and expanded our security measures.

## How we tested it

Every candidate build of 0.39.0 went through our full regression: nineteen automated scenarios covering matches with bots, network play, server settings, restarts and prediction, on both DirectX 12 and OpenGL. On top of that we played it ourselves, checked the anti-cheat end to end and ran the new launcher through a full update and repair from 0.38.2. A few issues turned up along the way, from a bomb round scoring twice to doors swinging the wrong way, and all of them are fixed in the build that ships.

## What comes next

0.39.0 is the last large update before 0.40, our biggest milestone so far. We have already shown some of what is coming in [Remodelled, on the road to 0.40](devlog-remodelled.html), and there is a lot more we have not shown yet.

0.39.0 is in its final round of checks as you read this and arrives through the launcher very soon. The full patch notes go up on the release page the moment it ships. When it does, load up Snow and listen. See you on the front line.
