---
title: The official servers now run on Linux
date: 2026-11-09
summary: Both official servers have moved to a native Linux build of the 0.34.0 server. What that means for your matches, why we did it, and how we made sure we could undo it in seconds.
image: img/shot-hosted.webp
tag: Servers
version: 0.34.0
---
Until this week, the official servers ran the Windows version of the game server on a Linux machine, through a compatibility layer that translates every Windows call as it happens. It worked, and it carried us through every update so far. But it was never the long-term plan. Since the early hours of 9 November, both Official #1 Ranked and Official #2 Unranked run a native Linux build of the 0.34.0 server.

## What you will notice

Ideally, nothing. The maps, rules, rotation, ranks and match history are exactly where they were. Your rating carried over untouched, because the servers kept their settings and statistics folders and only the program that runs them was swapped. The 0.34.0 client and the 0.33 client both join as before.

What changes is underneath. A native server no longer pays for translation on every frame, so it uses less of the machine and has more headroom when a match gets busy. In testing, a full ten-bot match running at twice today's tick rate used about seven percent of a single processor core.

## Why it matters

Headroom is what lets us raise the tick rate later. The servers currently send updates twenty times per second. Forty would make movement and hits feel tighter, especially in close fights, but only if the server can keep up comfortably and the hit registration still agrees with what you saw on your screen. Doubling the rate is not something we will switch on and hope for the best.

> The tick rate on the official servers has not changed yet. It will only go up after a dedicated internet hit-registration test shows that it is better, not just faster.

The Linux build is also the version community hosts get. Since 0.34.0, every release ships a ready-made Linux server package next to the Windows download, built from the same source code as the official servers. If you rent a small server somewhere, you can now run exactly what we run.

## How the move was done

The switch happened late at night, in a quiet window, one server at a time. Before anything was touched, the Linux build was checked against the release: the same game files, the same checksums, the same maps. The old setup was left in place next to the new one. Going back is a single change and a restart, which takes seconds, and that path was ready before the first server was switched.

The watchdog described in [What keeps the official servers running](devlog-official-servers.html) kept an eye on both servers throughout, as it does every minute of every day.

## What comes next

Two things follow directly from this move. First, the hit-registration test over a real internet connection, at both tick rates and with extra delay added on purpose, so we can see how the game behaves for players further away. Second, automatic server updates: new releases are already published with the Linux package, and the official servers will pick them up on their own once the update script has been adapted to their setup.

If a match on an official server feels different since the move, in a good way or a bad way, tell us on Discord with the server, the map and the time. That is exactly the feedback this change needs.
