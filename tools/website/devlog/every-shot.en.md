---
title: Every shot leaves a mark
date: 2026-11-08
summary: Bullet holes, impact sounds, the crack of a near miss and the original weapon animations. How the next update brings back the feel of a TC:E firefight.
image: img/devlog/impacts-warehouse.webp
tag: Gameplay
version: 0.33.0
---
Ask a TC:E veteran what a firefight felt like and you rarely hear about damage numbers. You hear about plaster bursting off a wall next to your head, the snap of a round that just missed, and the slide locking back on an empty pistol at the worst possible moment. Platinum already had the numbers right. The next update is about everything around them.

## Gunfire that stays in the world

Every surface now takes the original bullet holes for its material, where the round goes in and where it comes out. Every hit throws up dust, splinters, sparks or blood depending on what it strikes, and plays the original impact sound for that surface.

![A fresh bullet hole in a stack of crates in a warehouse, rendered in DirectX 12](img/devlog/impacts-warehouse.webp "A single round through a crate stack. The hole, the dust and the sound all come from the original material set.")

The near miss is back too. A round that passes close to your head makes the short, sharp crack TC:E players learned to react to long before they saw the shooter. It tells you that you have been found, and roughly from where.

Impacts are visual and audio only. They do not change damage, penetration or what a round can pass through. That all stays exactly as it is in the current release.

## The view model, rebuilt

We compared every player and weapon animation in Platinum with the original game, one by one, and listed every difference. The first-person set is now rebuilt from that list.

- Pistols lock their slide back on the last shot.
- Akimbo pistols fire from alternating hands.
- Reloads distinguish between a partial and an empty magazine, as they did in TC:E.
- Shotguns load shell by shell.
- Switching weapons lowers the old one before the new one comes up.

Every weapon also gets a new first-person muzzle flash, and scoped rifles show the sniper scope overlay when you aim.

## Ledges, not just ladders

Ledge climbing returns. Jump at a ledge within reach and you pull yourself up onto it, the way the original did. It opens up the same shortcuts and climbing spots veterans know, and nothing more.

![A soldier pulling himself up onto a crate in the Railhouse warehouse](img/devlog/ledge-railhouse.webp "Climbing a crate stack on Railhouse. The automated check runs the same climb on DirectX 12 and OpenGL.")

## How we tested it

Each piece has its own automated check that runs on DirectX 12 and on OpenGL. The impact check fires at walls and at a bot, then confirms that the server and the game agree on every single hit and its surface, and that a round passing close to a player registers as a near miss. The climbing check finds real ledges in the map and climbs them. All of it runs again in the full regression before the update ships.

## Still to come

Muzzle flashes and explosions do not cast shadows yet. That work is next, and it will arrive in a later update once it meets the same bar: faithful to the original, and fast enough that nobody has to turn it off.
