---
title: What keeps the official servers running
date: 2026-11-08
summary: Two official servers, a master list, live leaderboards and this website all run around the clock. Here is what happens behind the scenes when nobody is watching.
image: img/map-northport.webp
tag: Servers
---
When you join an official Platinum server, you see a map, a scoreboard and other players. Behind that sits a small set of services that has to keep running day and night, whether or not anyone from the team is awake. This post walks through what they are and how we look after them.

## What runs where

Everything public runs on a single server in a European data centre:

- **Official #1 Ranked.** Every match counts towards the [leaderboards](leaderboards.html).
- **Official #2 Unranked.** Ten bots keep the server alive, so there is always someone to play against. Matches here never touch your rating.
- **The master server**, which tells the in-game browser and the launcher which servers exist.
- **The stats service** behind the leaderboards, player profiles and the live scoreboards on the [servers page](servers.html).
- **This website**, which updates itself from our code repository every two minutes and serves every page over HTTPS.

The two game servers run separately, each with its own settings and its own folder, so a problem on one cannot take down the other.

## A watchdog that never sleeps

Every minute, a watchdog asks each game server for its status, just like the server browser does. If a server misses three answers in a row, it is restarted automatically and the team gets an alert on Discord. A crash brings the same alert. In testing, a server that was killed outright was back online in eleven seconds.

The same check keeps an eye on the rest: that the servers are listed on the master server, that the website and the stats service answer, and that disk space and memory are healthy. If a server keeps failing, the watchdog stops restarting it after four attempts in an hour and waits for a person to look, so a deeper problem never turns into an endless restart loop.

## The nightly round

Every night the system does a short round of its own. It checks that every map in the rotation is actually installed, posts a short health report to the team, and restarts a game server for a clean start, but only when no human players are on it. Nobody gets kicked out of a match for maintenance.

## Backups that leave the building

A backup on the same machine is not a backup. Every night, the server configuration, the match records and the statistics database are copied to a private, off-site repository. Anything sensitive, such as passwords and signing keys, is encrypted before it leaves the server. A copy is only made when something actually changed, so the history stays readable.

> A backup only counts once you know you can get it back. We tested decrypting the off-site copy before calling the job done.

## Why it matters

Ranks, ratings and match history are yours. You earned them, and they should not disappear because a disk failed or a setting went wrong. And an official server that is down at nine in the evening is a clan night that does not happen. None of this is glamorous, but it is the part of the game that has to work every single day.
