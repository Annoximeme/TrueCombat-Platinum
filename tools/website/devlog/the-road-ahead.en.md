---
title: The road ahead, in full
date: 2026-11-11
summary: The next two updates are planned, and so is the work behind them. A rebuilt movement core, a match record that powers replays and coaching, bots that have to look and listen like you do, pickup games on Discord and more. This is the long version, with how each piece works and why we are building it this way.
image: img/map-delta.webp
tag: Roadmap
---
Two days ago we published [What we are working on next](devlog-whats-next.html) and [What the playtests told us](devlog-playtest-fixes.html). Since then the plan has gone from a list to an order of work: we know what goes into the next update, what goes into the one after it, and what the larger projects behind them look like.

This post is the long version. It does not repeat the two earlier lists. It explains how the main pieces work, because several of them are things a game of this age was never designed to do, and a bullet point does not do them justice. It is a long read, so use the contents list to jump to what interests you.

> Nothing in this post has a date. An update ships when every part of it passes the full test run on the game, the server, both renderers and the launcher. Where something depends on a party outside our team, we say so.

## How the work is organised

There are two updates in the plan, and they are deliberately different in character.

**Update 0.35** is about how the game plays. It carries the core fixes from the playtests, and the first of the new features that do not need any collected data to work.

**Update 0.36** is about bots, maps and the warm-up, plus the features that read from recorded matches. Those features need real matches to exist first, which is why they come second: the recording starts with 0.35, and 0.36 builds on what it has gathered.

Inside 0.35 the fixes are built first. If the update has to be cut smaller to get the fixes out sooner, it is the new features that move, never the fixes.

## Update 0.35: what the investigation found

When we went through the playtest reports line by line in the source, one finding explained more than any other.

Platinum's game code is not the original TC:E code with changes on top. It is a new, native implementation, written to behave like the original. That is what makes the DirectX 12 renderer, the lag compensation and the bots possible at all. It also means that some things players reported as bugs are not broken features. They are features that have not been rebuilt yet, or that were rebuilt as a first approximation and never replaced.

### Movement has one root cause

Jump distance, crouch speed, ladder speed, footsteps and head bob were reported as separate problems. They are one problem. The part of the code that moves a player through the world each frame, applying friction, acceleration, steps and slopes, is still the provisional version from early development. Everything that depends on your speed inherits its small errors: when a footstep plays, how much the view bobs, how far a jump carries.

We also found a specific fault in the jump itself. A jump taken while moving loses a large part of its height compared with a standing jump, which is the reason the container jump on Delta is currently impossible.

So we are not going to tune these numbers one by one. The provisional movement core is being replaced with a faithful one, and then each value is measured against the original game: jump height, jump length while running and sprinting, crouch and crouch-walk speeds, ladder speed, how high a ledge you can climb. We have a test rig that runs the same inputs through the original and through Platinum and compares the results, so "feels right" becomes a number we can check after every change.

Weapon accuracy depends on this too. The accuracy penalty for moving is calculated from your speed, so every weapon gets re-checked once the new movement is in.

### Gunplay, measured

For hits at range and shots landing off the aim point, we are building a firing range that runs by itself: fixed targets at 10, 25, 50 and 100 metres, every weapon in the roster, aimed and from the hip, on a perfect connection and on a delayed one. It records where each round lands relative to the crosshair and compares it with the original. Whatever that data shows is what gets fixed, across the whole roster and not only the weapons that were named in reports.

The same pass covers damage per body region for every weapon, the pace of the bolt-action rifle, and weapon sounds, including the sounds you hear while spectating.

### Causes we have already confirmed

- **A grenade throw firing your gun.** After your last grenade the game switched straight back to your weapon without the normal switch delay, so a mouse button that was still held down fired immediately. The fix adds the delay and requires a fresh trigger pull.
- **Suppressors.** A suppressor can be selected in the Deployment Menu, but nothing in the firing or sound code reads it yet. It will get a suppressed sound, no muzzle flash, and a shorter distance at which bots can hear it.
- **Grenade cooking.** Grenades are currently thrown the moment you press the button. The original behaviour returns: hold to prime, release to throw, with the fuse running while you hold.
- **Your team between maps.** The game did not remember which team you were on when the map changed. It will, and it will also keep your team and score if you drop out and rejoin within a few minutes.

### Everything else in the 0.35 fix batch

- Chat and team chat input, with history.
- Team selection that registers on the first click.
- A server browser inside the game, in the Esc menu, so you can change server without going back to the launcher.
- The voice command menu.
- Coloured player names that survive a restart and display the same everywhere.
- Key binding for extra mouse buttons, and toggle options for walk and sprint.
- An Options page in the Esc menu: mouse and aim sensitivity with typed values, field of view, audio volumes and HUD options, all applied live.
- A hit marker setting. It is a player choice on Unranked and always off on Ranked.
- A longer, adjustable kill feed with names in team colour.
- Doors that follow each map's own settings as in the original, with an on-screen prompt.
- Flashbangs that blind and deafen bots for as long as they would a player.
- Fall damage applied to the legs, as in the original.
- Missing weapons in the Deployment Menu, dark red dot sights and wrongly coloured weapon parts.

### A bug reporter built into the game

Press F12, or pick "Report a bug" in the Esc menu, and a text box opens. No console, no command to remember. The report is sent with what we need to reproduce it: the map, your position, the server, the build, the renderer, a screenshot and the last lines of the game log. Details about your hardware are included only if you leave the tick box on, and you can see exactly what is sent.

We want this in 0.35 for a selfish reason: the next round of playtest feedback should arrive through it, with a position and a screenshot attached to every report.

## The match record

This is the piece most of the new features stand on, so it is worth explaining properly.

From 0.35, the official servers write down what happens in each match: every kill, every point of damage, every objective, the start and end of each round, and where each player is, sampled several times a second. It is a compact log of gameplay, a few hundred kilobytes per match, kept for a limited time and then deleted. It records what happens in the match and nothing about you outside it.

Older games treated a match as something that is over when the scoreboard closes. With a record like this, a match becomes something you can study afterwards. One recording feeds many features:

- **2D replays.** Watch any match from above on the map layout, round by round, with a timeline and the kill feed.
- **Automatic highlights.** The server recognises an ace, a clutch, several kills within seconds or a defuse with almost no time left, and picks out the best moments.
- **Heatmaps.** Where fights happen and where players die on each map, per team and mode.
- **A public balance view.** How each weapon performs over time: time to kill, headshot rate, how often it is picked. Balance changes can then be argued from data everyone can see.
- **A post-match coach.** A few numbers from your last match and one practical tip, such as the area where you died most and whether it was from the front or the flank. The tips are written by us, one by one. No generated text.
- **Weekly contracts and seasons.** Small weekly challenges and an eight-week season with its own leaderboard. Nothing to buy and nothing that affects gameplay.
- **Bots that learn.** More on that below.

We build the record once and let every feature read from it, instead of each feature collecting its own data in its own way. The recording arrives in 0.35. The features that read from it follow in 0.36, when there are enough matches to make them meaningful.

## Also new in 0.35

Three features that need no collected data come with the first update.

### Location pings

Aim at something, press the ping key, and your team sees a marker in the world and a line in chat with the area name, such as "[Market] Enemy spotted". A double tap means "enemy here", and a small wheel offers the rest: need help, going here, defending, bomb or flag.

Two details matter. First, the server checks that you can actually see an enemy before it accepts an enemy ping, so pings can never be used to reveal someone through a wall, on Ranked or anywhere else. Second, most of the original maps carry no area names at all, so we work them out from the map's layout and name them by hand, starting with Village.

### Bots that adapt to the server

On Unranked, the server compares every minute how the human players are doing against the bots, and nudges the bots' aim and reaction time slightly up or down. The steps are small and smoothed, so you should never notice it happening. You should only notice that a server of newcomers is not being farmed and a server of veterans is not bored. Ranked has no bots, so none of this applies there.

### When people play

The servers already know how many players are online. They will start keeping that history and turn it into a "busiest times" chart on the website. The launcher and Discord get an optional notification: tell it a number, and it lets you know when that many players are on. For a small community, knowing when to show up is half of having a full server.

## Bots, rebuilt from the senses up

Platinum's bots can move, shoot, play the objective and work in pairs. The playtests were clear about what they cannot do: they take the same routes, they rarely aim down sights, they lean at the wrong moments, and their reactions swing between slow and instant. We could patch those four things. Instead we have designed a new bot brain in four layers, and the first layer is being built now for 0.36.

### 1. A bot that understands the map

The original maps contain no information for bots. Platinum already works out where a bot can walk. The next step is working out what a place *means*.

When a map loads, the game divides it into a few hundred small areas and calculates which areas can see which. From that one table a great deal follows without anyone marking up a map by hand:

- **Exposure.** An area that many others can see is dangerous to stand in. An area few can see is a place to hold.
- **Cover.** For each spot, which directions are protected, and whether you have to crouch for it.
- **Chokepoints.** The areas every route between a spawn and an objective has to pass through.
- **Corners.** The places where one step sideways suddenly reveals a lot of the map. These are where a player slows down, raises the sights and leans, so that is where bots will do it too: aiming at head height at the edge before they come round it, and leaning out toward the open side when they hold it.
- **Lanes.** Up to four clearly different routes between each spawn and each objective. Bots are spread over the lanes at the start of a round, with a limit per lane, so they stop arriving at the same door in one group. Narrow doorways get a queue instead of a traffic jam.

Because it is calculated from the geometry, it works on every map, including community maps we have never seen.

### 2. A bot that has to look and listen

This is the layer that changes how bots feel most.

Today, a bot becomes aware of you the moment nothing stands between you. That is why their reactions feel unfair one moment and blind the next. In the new design a bot perceives the world roughly the way you do:

- **Noticing takes time.** Awareness builds up. Fast if you are close, in front of the bot and in the open. Slowly if you are far away, at the edge of its view, standing still or in shadow. A bot can fail to notice you, and you can see it happen.
- **Hearing.** Footsteps, reloads and doors tell a bot roughly where something is, not exactly where. Walking quietly becomes a real tactic against bots, as it is against people.
- **Belief, not knowledge.** Each team of bots keeps a shared picture of where the enemy *might* be, built only from what its members have seen and heard. It fades and spreads with time. A bot checks the corner where it last saw you, not the corner where you really are.
- **Decisions by weighing options.** Instead of a fixed script, a bot scores a small set of actions, such as push, hold, flank, fall back, support a teammate or go for the objective, against the situation it believes it is in.
- **Personalities.** Each bot name gets its own temperament: patient or aggressive, a preferred range, how readily it takes a risk. The same name will play recognisably the same way from match to match.
- **Nerves.** A bot left alone against three plays differently from a bot on a winning team, and bots make the occasional believable mistake.

### 3. A team that makes a plan

At the start of a round a team of bots picks a plan from a small playbook: which lanes to take, who holds and who pushes. The team keeps track of which plans have worked on this map against these opponents and gradually favours them, while still trying the others now and then so it does not become predictable.

Bots will call out what they see through the same voice commands and pings players use, with area names, and react to calls from teammates. That works in both directions: you will be able to give a bot a simple order, such as follow me or hold here.

### 4. Bots that learn from real matches

This is where the match record comes back in. Once enough matches have been recorded on a map, bots can start to use them:

- **Routes.** Bots favour the paths real players actually take on each map, mixed with their own lane, so they flank and hold where people do.
- **Positions and timing.** Where players tend to hold, and how long after the start of a round fights usually break out in each area.
- **Aim.** How a human hand really moves a crosshair onto a target: the speed, the overshoot, the settling. Bot aim is shaped to follow those curves instead of an invented formula.

We are also designing an optional mode for later in which a bot can play in the style of a specific player who has agreed to it.

There is no chatbot inside any of this. A bot's decisions are made by game logic that runs on the server and can be tested and measured, not by a language model.

### How we will know it worked

Every bot change is already tested by running full matches on all six maps, old version against new, and comparing the numbers. For this work we are adding a measure of how human the bots look: how often they use the sights, how many different routes a team takes per round, how their reaction times are distributed.

And once the later layers are in, we want to run an announced test night on the official servers where players guess who in the match was a bot. If you cannot tell, we are done.

The first layer, map understanding with corners and lanes, is in development for 0.36. The other three follow one at a time, each after the one before it has proven itself.

## Online play and launcher 1.5.0

This work is built and has been brought up to date with the current version. What it still needs is its test with real players on real connections, and it joins an update once it has passed.

- **A connection you can read.** Four-bar connection icons next to every ping on the scoreboard, coloured by quality, and a network graph you can switch on under the round clock: ping, packet loss and jitter, or a rolling six-second graph with loss spikes in red. When a fight feels wrong you can see whether it was your connection, theirs or the server.
- **One-click join.** A join link on the website or in Discord opens the launcher and puts you in the server, on the right team if the link says so. If the server is full, the launcher waits for a slot and joins by itself. Before connecting it runs a short connection check and turns on extra packet protection if your route is losing packets.
- **IPv6.** The launcher, the game, the server list and the dedicated server all handle IPv6 addresses. For players whose provider no longer gives them a full IPv4 address, that can be the difference between being able to host and not.
- **A Verified tag.** Community servers that run the official build are marked in the server browser and on the website.
- **Hover tips.** The launcher explains its own options: hold the pointer over a graphics setting and it tells you what it does and what it costs.
- **Fairer Ranked.** A ping limit on Official #1, timed bans that apply across the official servers, and a full rating loss for quitting a team match you are losing.

## Discord: pickup games and reports

Our own Discord bot is built and tested. It is not switched on yet, because that step involves the live servers and waits for its own go-ahead.

- **Pickup games.** Press Join queue. When two full teams are waiting, everyone gets a 60-second ready check. The bot then balances the teams on skill rating by trying every possible split, claims a free match server, sets a fresh password, turns on competitive match mode and sends each player a join link that lands them on the right team. When the match ends it posts the result with each player's rating change and starts the next group. For a community our size, this is matchmaking that works with twelve people online.
- **Reports with evidence.** An in-game `/report` reaches the staff channel with the reported player's stats for that map and a pointer to the exact minute in the server's own recording of the match. A person always makes the decision.
- **Your account, linked.** One code typed in game connects your Discord account to your player profile. No password and no sign-up. From then on `/profile` shows your rank, rating and last matches, and Discord roles follow your rank.
- **Live server cards, events and playtests.** A card per official server that updates every minute, and event sign-ups with reminders in your own time zone.

## Easy Anti-Cheat

The Easy Anti-Cheat integration is in the engine and switched off. One check remains: a real client confirmed as protected when it is started through the real anti-cheat launcher. We will not announce it on the strength of a build that only looks right. It ships when that check passes, and it will get its own post explaining what it does and does not see on your PC.

## DLSS 5

We get asked about this, so here is the honest state of it.

Platinum already supports DLSS upscaling, DLAA, Frame Generation and Reflex. DLSS 5 is a different kind of technology: instead of sharpening or adding frames, it uses a neural network to re-light and refine the finished image. On a game with lighting from this era, that is potentially the largest visual step available.

Our plan is to build it into the DirectX 12 renderer as a proper, native feature. The renderer already produces the motion and depth information this kind of technique needs, so nothing has to be bolted on from outside the game.

Three things are decided:

- It will be **optional and off by default**.
- It will be **off on Ranked**, and enemy players are excluded from the effect everywhere. A technique that repaints the image must never change how visible an opponent is.
- It will only ship with **software NVIDIA has released for developers to distribute**. That is not yet available for a project like ours, and the timing is not in our hands.

So: planned, researched, and not available. It also needs a graphics card that supports it. We will not put a date on something that depends on a release we do not control.

## After that

Further out, each with its own decision still to be made: more maps from TC:E's history, additional weapons and player skins from other TrueCombat releases, custom maps on community servers with a safe way to download them, and friends and parties in the launcher.

## What you can do

The order above came directly from what players told us after the playtests, and it can change the same way. If something here matters more to you than the rest, or something is missing, tell us on [Discord](https://discord.gg/8kcHdg2Hch). The [roadmap](index.html#roadmap) follows this plan, and each piece gets its own devlog post when it lands.
