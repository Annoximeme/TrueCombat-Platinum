---
title: Match mode, built for clan nights
date: 2026-11-07
summary: Clan matches are where TC:E lived. Platinum 0.32 brings a full match flow to every server, with a pause that freezes the whole world.
image: img/media-deployment.webp
tag: Competitive
version: 0.32.0
---
Ask anyone who played TC:E seriously what they remember, and it is rarely a public server. It is a clan match: two tags, a booked server, and a round decided by one well-held corner. Platinum 0.32 brings that format back as a built-in match mode, ready on every server with a single command.

## The flow

A match starts in **warmup**: free play with respawns, and no automatic team balancing, so clans can line up however they like, four against five included. Players type `ready` when they are set, and the match begins the moment every player on both teams is ready. Bots never hold it up.

Next comes the **knife round**. One round, knives only, no respawns in any mode, two minutes on the clock. The bomb and the flags stay out of play. The winners choose their side with `stay` or `swap`.

Then the match goes **live**: twelve rounds in the round modes, or two 20-minute halves in Team Deathmatch and Flag Capture. Teams lock, and every warmup and knife round kill is wiped from the scoreboard and from the leaderboard report. At **half-time** the teams swap sides, and scores, clan names and remaining timeouts move with them. A team that can no longer be caught wins on the spot.

## A pause that really pauses

The hardest part to get right was the timeout. A tactical timeout is only fair if nothing moves while it runs, so in Platinum the whole match freezes. Players stand still, grenades hang in the air with their fuse held, and the round clock, the bomb timer, dropped backpacks, reloads and respawn waves all keep exactly the time they had left. Play resumes after a five-second countdown.

Each team gets two timeouts of 60 seconds by default. Admins can pause without a time limit.

## Built to be tested

Match mode went through thirteen scripted test steps with two real game clients, on both DirectX 12 and OpenGL. Among them: a knife round that really is knives only, a side pick only the winners can make, a round clock that held through ten seconds of pause, a smoke grenade whose fuse only burned while the game was running, and a half-time swap that carried scores and names across.

## Run your own

Host a server in a team mode, type `match on` in the server console, name the teams, and let both sides ready up. The [competitive page](competitive.html) lists every command and setting. Match nights and scrims are organised on our Discord.
