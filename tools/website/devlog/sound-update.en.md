---
title: Hear the fight
date: 2026-11-19
time: 03:20
summary: Every gun gets its own voice, impacts get twelve variations per surface, and the sound engine learns about rooms, doorways and distance. Plus free aim and two-handed AKs. The full story of update 0.39.3.
image: img/devlog/front-lines-blast-courtyard.webp
tag: Update
kicker: Update 0.39.3
version: 0.39.3
---
In TrueCombat you hear most fights before you see them. A burst behind a wall tells you where the enemy is, how many there are and whether they're inside or out, and a good player turns that into a decision in half a second. That only works if the sound is honest. For 0.39.3 we went through everything a gun does to your ears, from the moment the trigger breaks to the last echo off a building three streets away.

Two things drove the work. A lot of the original guns shared the same sound or sounded thin next to everything else we've upgraded, and the engine treated every sound as if it happened in the room you're standing in. 0.39.3 fixes both.

![A shot fired into a courtyard on the Ultra preset](img/devlog/front-lines-blast-courtyard.webp "Every shot now has its own voice and an echo that matches where it was fired. Ultra preset, DirectX 12.")

## Every gun its own voice

We started by listening to every weapon file in the game, one by one. Too many pistols and SMGs were nearly the same sound, and most rifles were missing the low punch that makes a shot feel like a shot.

The new set gives every in-game weapon its own source:

- **35 weapons use a real recording** of that gun or its closest relative. No two guns share a recording, apart from twins like akimbo pairs and iron-sight versions of the same rifle.
- **12 weapons keep their original TrueCombat:Elite sound, remastered**, where there was no recording that was clearly that gun. They're re-cut, given a kick and spread over four slightly different takes, so full auto doesn't sound like a loop.
- **Every shot has a kick**: a short low thump tuned to the calibre, under a darker body. Your own gun gets more of it than other players' guns, because that's how it sounds when it's against your shoulder.
- **It's louder**, but not unfairly so. Other players' guns are about 3 dB up on the original, and your own about 7 dB, both capped before they turn into distortion. How far a shot carries and how it falls off with distance haven't changed, so nobody hears further than before.

Not everyone wants a new sound for a game they've played for twenty years. Options > Audio now has **Weapon sounds: Remastered / Original**. Original plays exactly what 0.39.2 played. Both sets load with the map, so switching is instant, even mid-round.

## An echo that knows where you are

A rifle in a small room, a long hall, an open street and a snowfield should not have the same tail. Each shot now gets a rendered room tail for the space it's in (room, hall, outdoors or snow) and for its weapon class (pistol and SMG, rifle, or DMR, sniper and shotgun), with two takes of each so repeated shots don't sound copied.

![A harbour alley on the Ultra preset](img/devlog/front-lines-harbour-cqb-alley.webp "Alleys and courtyards now slap shots back off their walls. Harbour, Ultra preset.")

## Impacts that sit with the originals

Bullet impacts were a different problem. The original TC:E impacts are short and dry, and players know them by heart. Replacing them would make the game feel foreign, so we kept them and added more around them.

- Every surface (flesh, metal, sheet metal, fences, wood, glass, stone and foliage) keeps its five original sounds and gets **seven new ones**, so it now picks from twelve. The same sound never plays twice in a row.
- Every new variation was matched to the originals of its set: the same tonal balance, the same level within 1.5 dB, the same length. Long-ringing sets like metal carry a bit of the original ring under the new hit. Some are real recorded hits, some are blends of an original's first few milliseconds with a recorded body, and some are the originals re-voiced.
- **Dirt, sand, snow and grass were silent** in TC:E. They now get twelve quiet hits of their own.
- **Ricochets** whine off hard surfaces.
- **Near-miss cracks and whizzes** go from four variations to twelve.

## A sound engine that understands rooms

The bigger change is under the hood. Seven upgrades to the sound engine change how every sound reaches you, not just gunfire.

![Stacked crates in the Snow warehouse](img/devlog/front-lines-snow-warehouse.webp "A firefight inside a warehouse now booms in that warehouse, even when you're outside. Snow, Ultra preset.")

### The shooter's room

Until now every sound used one reverb: the one for the room you're in. A rifle fired in a big barn while you stood in the street sounded like it was fired in the street. Now gunfire and blasts further than a few metres away also ring in **the room they were fired in**. The engine probes the space around the shooter, tunes a reverb to it and sends the shot into it, muffled by the same walls the shot travels through. A fight in a warehouse booms like a warehouse, and you can tell it apart from a fight in the open.

### Through the doorway

When a wall stands between you and a sound, the engine used to muffle it heavily and leave it where it was. Now it looks for the opening the sound would really travel through, testing 32 points around you and the source for a clear path. When it finds one, you hear the sound **from the doorway or window**, at the length of that path and only lightly muffled. Stand in a house with one door and a shot outside comes in through the door, not through the wall.

### The loudest shot stays clear

A big firefight used to turn into a wall of noise. Now the loudest fresh gunshot or blast leads the mix for a moment, and other gunfire, impacts, debris and casings more than 12 dB under it step back by up to 4 dB. Footsteps, near-miss snaps, voice chat and menus are never touched, so nothing you rely on to find an enemy gets quieter.

### Distance takes time

Sound travels at about 343 metres per second, and now it does in the game too. Gunfire and blasts further away start a moment later: about 0.3 seconds for a shot 100 metres away. **It's the same for every player** and can't be switched off for an advantage. Up close, shots near walls get one or two short **wall slaps**, the hard reflection you hear firing in an alley. In an open field there are none.

![The harbour waterfront on the Ultra preset](img/devlog/front-lines-harbour-water-fire.webp "Out in the open there are no wall slaps, and distant shots arrive a moment after the flash. Harbour, Ultra preset.")

### More voices, finer sound

The engine can now play **240 sounds at once** instead of 192, and it mixes at 48 kHz. When every voice is busy, it drops the sound you hear least right now instead of the oldest one, so a big fight doesn't cut off the shot next to you.

### Your ears react

An unsuppressed shot fired close to you by someone else briefly dulls your hearing with a faint ring, which comes back over about two seconds. Your own shots never count. It's milder than a nearby blast, and the existing options for blast muffle and tinnitus turn it off.

### Footsteps in their room

Footsteps further away now echo in the room the walker is in, like gunfire. Only the echo is new. How loud footsteps are, how far they carry and how walls block them are exactly as before, so nobody gets louder or quieter steps than in 0.39.2.

## Free aim, finally done properly

Free aim was already hidden in the game: a copy of TC:E's aimed free aim from 0.38.0, off and only active while aiming. 0.39.3 turns it into a real option under **Options > Mouse & View > Free aim**, **off by default**:

- **Deadzone**: at the hip your mouse moves the gun inside a small box (about 4 degrees left and right, 2.5 up and down) before the view turns.
- **Wide deadzone**: the same with a bigger box.
- **Classic (aim only)**: TC:E's original free aim, unchanged.

When you aim down the sights in a deadzone mode, the sights glide to where the gun points in about a tenth of a second while the view turns with them, so you never lose your target. Shots always leave along the gun, the server agrees with your screen, and there's no added input lag. We tested it with 320,000 random mouse movements at four different frame rates to make sure the gun always points exactly where you moved it.

## Two hands on the AK again

For a while, other players' AK-47s and G3s were held with one hand in third person. One line in the animation script was too long and got cut off, so those rifles fell back to a one-handed pose. That line is fixed, and both hands are back on the gun.

![An AK-47 on Railhouse](img/devlog/cqb-ak47-railhouse-ultra.webp "The AK-47 on Railhouse. Ultra preset.")

## How we tested it

Sound is hard to test with a machine. The parts that can be measured were measured. Every new impact was checked against its originals for level and tonal balance. The engine reports how many rooms it tuned, how many doorway paths it found and how often it stepped sounds back, and we checked those counts with eight bots fighting on Village. Each upgrade has its own switch, so we compared the game with each one on and off. On top of that came the full 19-case release test, bot matches on six maps, and a CPU and frame-time comparison against 0.39.2, because 240 voices and extra reverb aren't free.

What a machine can't tell us is whether it sounds right. That part is up to you. If a gun sounds wrong, a room echoes strangely or a doorway sends a sound the wrong way, tell us on [Discord](https://discord.gg/7Dg4yhhvGF) with the map and where you were standing.

> Prefer the old sound? Options > Audio > Weapon sounds > Original brings back the TC:E gunfire. The other sound engine upgrades stay on and apply to everyone the same way.

## What's next

Next up is the light. Darker maps with real light and shadow are being tested now, and they'll come in a following update once we're happy with how every map looks. After that, the 0.40.0 interface overhaul is on its way. As always, thanks for playing, and for listening.
