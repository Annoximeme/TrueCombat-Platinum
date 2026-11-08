---
title: Back to full speed
date: 2026-11-07
summary: For months Platinum felt a step slower than the game we remember. The cause turned out to be a single scaling factor, applied in the wrong place.
image: img/map-railhouse.webp
tag: Gameplay
version: 0.32.0
---
From the first public builds, veterans told us the same thing: Platinum looked right, sounded right, and felt a step too slow. Our own movement tests disagreed. Every speed we measured matched the values in the TC:E source data. Both sides were right, and finding out why took us back into the original game.

## One factor, two meanings

TrueCombat: Elite 0.49b scales player movement by `g_movespeed / 127`. The default server value is 76, so that factor slows players to roughly 60% of their base speed. What we had missed is where the original applies it: only in game types 0 and 1, the practice and free-for-all modes. The modes TC:E was really played in, such as Flag Capture and Bomb, run under other game type numbers and never touch the factor. They run at full speed.

Platinum runs all of its modes through game type 0 internally, so the practice slowdown applied everywhere. Our tests were measuring the slowed speed and finding it correct.

We confirmed it two ways: against the speed table in the original 0.49b changelog, and against the 1/127 constant in the original game code. Both pointed to the same answer.

## The numbers

With a rifle on default server settings, Platinum 0.32 moves at:

- **238** units per second sprinting
- **163** running
- **68** crouched
- **38** prone

Those are the original TC:E speeds. The [guide](guide.html) has the full breakdown.

## What full speed broke

Faster movement exposed things the slower speed had hidden. Other players switched between their walk and run animations at the wrong moment, so the threshold now sits at 150 units per second, as in the original.

The stamina system had a subtler problem. A recovery bonus was applied on every frame, even while running. At the old running speed that never showed, because running slowly enough counted as recovering anyway. At 163 units per second, players would have regained stamina while running flat out. Recovery now only happens when it should: standing still, walking, crouched or prone.

While we were in there, Elimination rounds went back to their original five minutes.

## Why it matters

TC:E is a game of timing. How long it takes to cross a street, reach a corner, or get back into cover is what every map is built around. Getting that wrong by 40% changes every fight on every map, and no screenshot shows it. That is why every speed in Platinum is now checked against the original data before a release ships.
