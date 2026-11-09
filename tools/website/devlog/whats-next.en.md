---
title: What we are working on next
date: 2026-11-09
summary: With 0.34.0 out, here is an open look at the work lined up behind it: better online play, Discord pickups, one-click joining, and a set of new features built on a shared match record. Plans, not promises.
image: img/media-map-vote.webp
tag: Roadmap
---
0.34.0 is out, and the official servers have moved to Linux. This is a good moment to show what is next. Everything below is either built and waiting for testing, or planned and not started. We say which is which, and none of it has a date. A feature ships when it passes the full test gate, not when a calendar says so.

## Online play

This work is furthest along. Most of it is already built and tested in isolation, and now has to be brought onto the 0.34.0 code and tested with real players on real connections.

- **Connection quality you can see.** The server measures loss, jitter and ping for every player and shares it, so the scoreboard can show a connection icon next to each name and you can open a network graph in-game. When something feels off, you will be able to tell whether it is your connection, someone else's or the server.
- **Fairer ranked matches.** A ping limit on Official #1 Ranked, so one very distant connection cannot spoil a match for everyone else. If you drop out and rejoin within a few minutes, you keep your team and your score. Leaving a team match you are losing on purpose will cost the full rating loss, and abandoned matches show on your profile.
- **One-click join.** Join links that open the launcher and drop you straight into a server, from the website or from Discord. If the server is full, the launcher waits for a free slot and joins on its own. A short connection check before you join warns you about a long route and turns on extra packet protection for lossy connections.
- **Pickup games on Discord.** A `/pickup` queue with a ready check, teams balanced by skill, and a server claimed for you with a join link for each player.
- **Better tools for admins.** Timed bans, a ban list shared across official servers, and player reports that link straight to the exact moment in the server's own recording of the match. Statistics that look implausible are flagged for staff to review. A person always makes the decision, never the system.
- **Community servers.** A ready-made container setup for hosting your own server, IPv6 support for players and servers, and a Verified tag for community servers that run the official build.

> Faster servers come last, on purpose. The tick rate only goes up after an internet hit-registration test shows hits register better, not just faster.

## New features

The second group is a set of plans we have chosen but not started. Most of them need the same thing first: a record of what happens in each match on the server, such as kills, objectives and where players move. We will build that record once and let several features read from it, instead of every feature collecting its own data.

- **2D replays and highlights.** Watch any match back from above on the map layout, round by round. Standout moments, such as an ace or a last-second defuse, are picked out automatically.
- **Location-aware pings.** Mark an enemy, a spot or an item for your team, with the area name where the map has one. On Ranked, you can only ping enemies you can actually see.
- **A post-match coach.** A few numbers from your last match and one practical tip, such as where you died most and from which direction. The tips are written by us, one by one.
- **Heatmaps and a balance view.** Where fights happen on each map, and how each weapon performs over time, so balance changes are based on data rather than guesswork.
- **Weekly contracts and seasons.** A few weekly challenges and an eight-week season with its own leaderboard. Nothing to buy and nothing that affects gameplay.
- **Friends and parties.** Add friends, see where they are playing and join them, or follow a party leader into the same server.
- **Smarter bots on Unranked.** Bots that adjust gently to how the humans on the server are doing, and later learn the routes real players take on each map.
- **Busiest times.** A chart of when the servers are usually full, and an optional notification when enough people are online.
- **In-game bug reports.** Type `/bug` with a short description, and the report reaches the team with a screenshot and the details needed to reproduce it.

## Also still open

Easy Anti-Cheat, held back from 0.34.0, is still waiting for its final check: a real client confirmed as protected through the real anti-cheat bootstrapper. It ships once that is verified, and not before.

## Your part in this

The order of all of this is not fixed. If one of these matters more to you than the rest, or if something you want is missing, say so on [Discord](https://discord.gg/8kcHdg2Hch). The [roadmap](index.html#roadmap) shows what has landed as we go, and every piece gets its own devlog post when it does.
