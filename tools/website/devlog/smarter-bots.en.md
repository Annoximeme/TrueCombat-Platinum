---
title: Teaching bots to play like people
date: 2026-11-08
summary: Bots that never miss are no fun, and bots that ignore the objective are worse. This is how we test every change to Platinum's bots before it reaches a server.
image: img/media-village-yard.webp
tag: Bots
version: 0.33.0
---
TC:E never had bots. Platinum does, because a tactical shooter is only fun when there are enough people to play against, and an empty server stays empty. Our second official server runs with ten bots for exactly that reason. That puts a lot of weight on them: a bad bot teaches new players the wrong habits, and a perfect bot is simply frustrating.

## Starting from nothing

The original maps contain no data for bots at all. There is no information about where a player can walk, jump or climb. So the first job was a navigation system that reads each map's geometry when it loads and works out the routes by itself: floors, stairs, ledges, doors, ladders and water. On our maps that takes between half a second and a second and a half.

With that in place, version 0.31 gave bots the basics: move, shoot, throw grenades, go prone and peek around corners. Version 0.32 taught them the objective. Bots now plant and defuse the bomb, carry the flag home and take the capture point, and they call out what they are doing in team chat.

## Making them human

The pass now in testing is about *how* bots fight. A few of the changes:

- **Reaction time** depends on the situation. An enemy straight ahead is spotted faster than one at the edge of the screen.
- **Aim** no longer snaps. A bot flicks towards a target, slightly overshoots or undershoots, and settles. Tracking a moving player lags just enough to feel fair.
- **Movement.** Bots stop to take an accurate shot, strafe at close range, crouch while spraying, reload behind cover and keep their distance from teammates.
- **Teamwork.** Bots share what they see, send support to a teammate under fire, trade a fallen teammate and move in pairs in Team Deathmatch and Elimination.
- **Discipline.** A bot holds its fire when a teammate stands in the line of fire.

## Measured, not guessed

Every change to the bots is tested the same way. We run bots-only matches on all six maps, in every mode, once with the current release and once with the new version, and compare the results: kills, accuracy, bomb plants, flag captures, rounds played and how often a bot gets stuck.

That process caught a problem we would never have spotted by playing a few rounds. In the first test round, the new bots were so much better at spotting and shooting that flag carriers barely survived. Flag captures across the test matches dropped from eight to one. Better individual bots had made Flag Capture worse.

> The fix was to keep the new combat behaviour for bots that hunt and defend, and let bots running an objective move the way they did before. Captures went back to the same level as the current release, within the normal variation between runs.

Five test rounds and dozens of matches later, the numbers look like this: no crashes, twice as many kills in Elimination, noticeably sharper aim in Team Deathmatch, and bomb and flag play at the same level as before.

## What comes next

Bots are a long project. Flag carrier routes on Village and Railhouse can still be smarter, and every new mode or map will need its own test round. If you play against them on the official unranked server and something looks wrong, tell us on Discord. A clear description of the map and the moment helps more than you might think.
