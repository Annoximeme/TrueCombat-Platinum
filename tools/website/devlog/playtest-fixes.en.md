---
title: What the playtests told us
date: 2026-11-09
summary: Our latest community playtests turned up a clear list of problems, led by gunplay. A large batch of fixes is lined up for the next patch. Here is everything we found, the order we will fix it in, and how it fits with the rest of the work coming up.
image: img/media-grenade.webp
tag: Roadmap
updated: 2026-11-12
---
The best test of a shooter is a full server of people who know how it is supposed to feel. Our most recent community playtests gave us exactly that, and the verdict was honest: the foundations are there, but too many small things still feel wrong next to the original. This post lists every issue that came out of those sessions, the order we will tackle them in, and where they sit next to the work we described in [What we are working on next](devlog-whats-next.html).

The result is a long list of fixes, and they are lined up for the next patch. It will not have a date until it is ready: each fix ships once it passes the full test gate, and we will update this post as items land. Every update brings Platinum a step closer to the enhanced, better game we set out to make.

> Update, 12 November: most of this list shipped in 0.35.0. Each item below now says where it stands. [Inside 0.35.0](devlog-inside-035.html) explains how the fixes were made and what did not make it.

> Gunplay comes first. Until every shot lands where you aim and does what it should, nothing else on this list matters as much.

## Gunplay

This is the most important group, and the one we hear about most.

- **Hits at range.** Shots at longer distances do not always register on a target that was clearly under the crosshair. We will check every hitbox against the player model at range, with and without lag compensation, on a real internet connection. *Update, 12 November: 0.35.0 fixes hits on leaning players and lost shots right after a respawn. One remaining case, shots at prone players, was found after the release and is being fixed.*
- **Bullets not landing at the aim point.** Some weapons, the SIG among them, put rounds slightly off from where the crosshair sits. We will not stop at the weapons that were reported: every gun in the roster gets the same check, so the fix is complete rather than case by case. *Update: the weapon-by-weapon audit is under way. The causes found so far are the leaning and respawn fixes in 0.35.0.*
- **Spread and aim per weapon.** Each weapon's spread, its growth while firing and how it behaves aimed down sights will be compared against the original values, weapon by weapon. *Update: checked. Every weapon's spread matches the original values, and aiming down sights now slows you down as in the original.*
- **Damage.** The damage model for rifles, SMGs, pistols and sniper rifles gets a full review, including how damage falls off with distance and body part. *Update: checked. The damage values match the original tables. Fall damage now hits the legs instead of the body.*
- **Bolt-action rhythm.** The bolt-action sniper rifle cycles too quickly between shots. It will get back the original pace, which is a large part of what makes the rifle feel deliberate. *Fixed in 0.35.0.*
- **Grenade throw firing the gun.** Throwing a grenade can fire your weapon at the same moment. This is a plain bug and will be fixed as part of the first batch. *Fixed in 0.35.0, together with grenade cooking.*

Every weapon change will be verified with an automated test that fires each gun at fixed targets and distances and compares the result with the original game, so a fix for one weapon cannot quietly break another.

## Maps

- **Invisible walls.** Players found invisible collision in places where nothing should block you, most noticeably around the small house at the bomb site on Delta. *Fixed in 0.35.0 on every map: they were capture-point posts from Flag Capture, left solid in the other modes.*
- **Textures.** Some surfaces show the wrong texture. Rather than patch the spots that were reported, we will walk through every map, surface by surface, and correct whatever does not match. *Update: every map was checked surface by surface and no missing textures were found. Placeholder textures on weapon parts are fixed in 0.35.0.*

## Movement and sound

- **Jump distance.** Jumps do not carry as far as they did in the original. Movement is something TC:E players feel instantly, so this gets measured against the original rather than tuned by eye. *Fixed in 0.35.0. Standing jumps onto low objects and the landing recovery now match the original.*
- **Crouch-walking.** Moving while crouched is too fast and too loud, and the view bobs too much. All three will be brought back in line. *Fixed in 0.35.0.*
- **Your own footsteps.** Your own footsteps are sometimes missing altogether. We will find out why and fix it. *Update: footstep timing was rebuilt from the original in 0.35.0. One more cause, linked to the sprint and walk toggles, is found and being tested.*
- **Weapon sounds.** Some weapons play the wrong sound. Every weapon's firing and handling sounds will be checked against the original set. *Update: explosions are no longer muffled by nearby walls in 0.35.0. If a weapon still sounds wrong to you, press F12 in the game and tell us which one.*
- **Sound while spectating.** Gunfire sounds wrong when you watch another player. Spectating should sound exactly like playing. *Fixed in 0.35.0.*

## Menus and match flow

- **Options in the pause menu.** The Esc menu has no settings yet. You will be able to change mouse sensitivity and other options in the middle of a match, without leaving the game. *Fixed in 0.35.0 with the new MOUSE & VIEW page.*
- **Warm-up.** The warm-up phase before a match is meant for picking your loadout and talking with the players who are joining. Right now it does not work the way it should, and we will rework it. *Fixed in 0.35.0. Warm-up is now a practice round.*
- **Instant replay.** Two small fixes from the last update: a clip saved during warm-up can come out shorter than expected, and the confirmation always says 30 seconds whatever the actual length. *Not in 0.35.0. Being worked on.*

## Bots

- **Aiming down sights and leaning.** Bots never aim down sights and never lean, which makes them easy to read. They will learn both. *Update: since 0.35.0, bots visibly shoulder their weapon when they aim. When to aim and lean is part of the bot work in progress.*
- **Routes.** Bots take the same routes too often. They will vary them more, and later learn from the routes real players take on each map. *In progress, as part of the bot work described in [The road ahead, in full](devlog-the-road-ahead.html).*

## Smaller items

- **In-game bug reports.** A `/bug` command and a "Report a bug" entry in the Esc menu. Your report reaches the team with a screenshot, your position on the map and the technical details needed to reproduce it. After this round of testing, that is a tool we clearly want ourselves. *Shipped in 0.35.0: press F12, or REPORT A BUG in the pause menu.*
- **Staff badge.** The badge that marks team members in game will get a more refined look. *Not in 0.35.0.*

## Alongside this

The playtest fixes come first, but the rest of the plan has not gone anywhere. Most of the online play work is built and waiting for its real-world test: connection quality on the scoreboard, a ping limit and rejoin protection on Ranked, one-click join from the website and Discord, pickup games on Discord, better admin tools, and IPv6 support for players and servers.

After that come the larger features: 2D match replays with automatic highlights, location-aware pings, a post-match coach, heatmaps and a public balance view, weekly contracts and seasons, friends and party join, and bots that adapt to the players on the server. [What we are working on next](devlog-whats-next.html) covers all of them in more detail. Easy Anti-Cheat is still waiting for its final verification and will ship once that is complete. *Update: Easy Anti-Cheat shipped in 0.35.0 and the official servers now require it. The game side of the online play work above shipped in the same update.*

## Thank you

Every item above came from players who took the time to play, notice and tell us. That is exactly the kind of testing we cannot do on our own, and it is why the next patch carries as many fixes as it does. If you spot something else, or if one of these issues matters more to you than the rest, tell us on [Discord](https://discord.gg/8kcHdg2Hch). The [roadmap](index.html#roadmap) shows what has landed as we go.
