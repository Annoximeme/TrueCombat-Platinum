---
title: Inside 0.37.1, tuned to your reports
date: 2026-11-15
time: 11:30
summary: A HUD you can size to your screen, a magazine and health readout in the spirit of the original, weapons back at their true fire rates, smoother map loads and optional HD textures. Here is what changed in 0.37.1, and why.
image: img/hero-snow-warehouse.webp
tag: Release
version: 0.37.1
---
0.37.0 was the biggest update Platinum has had, and it put a lot of new things in front of a lot of players at once. You told us quickly what felt right and what did not. Version 0.37.1 is our answer to those reports. It is a follow-up rather than a new feature drop, but it is not a small one: it touches the HUD, the gunplay, the bots, performance and the launcher.

> The launcher installs 0.37.1 by itself and your settings carry over. If you want a smaller install, you can now switch off HD textures in the launcher.

## A HUD that fits your screen

The new interface in 0.37.0 came with three fixed menu sizes. That was not enough. Players on large monitors wanted a smaller HUD, players on laptops wanted a bigger one, and almost everyone wanted the chat less in the way.

So the sizes are now sliders. **Menu size** runs from 50 to 100 percent and **In-game UI size** from 50 to 150 percent, both in 5 percent steps. Opacity is split three ways, so you can fade the HUD panels without losing the text and icons on them, and set the chat separately. The round timer and the team scores can each be shown or hidden on their own.

A few things also got out of the way. The "You killed" notice in the middle of the screen is gone, because it covered exactly the spot you were aiming at. The death card now sits in the bottom-right corner and fades out after about two and a half seconds. Map loading screens are back, and the FPS counter option finally does what it says.

Key bindings had two problems of their own. **Default Settings** now restores the proper Platinum layout, and the launcher no longer overwrites keys you changed in game. New players also get **F3** for Call a vote out of the box.

## Ammo and health, the way they used to read

The original TrueCombat never showed you a round count. You saw a magazine and how many spares you had, and you learned to count your shots. 0.37.1 brings that back. The ammo panel shows a magazine icon with an exact count of spare magazines, along with the icon of the weapon in your hands. When you need to know how full the current magazine is, the new **Check Magazine** key tells you.

The reload prompt has been removed for the same reason. Instead, the click of an empty gun is louder, so you know you are dry the moment it happens.

Health works in the same spirit. A body silhouette shows where you have been hit, and warns you when you are limping or close to death. In ranked matches the silhouette is all you get, so every player reads the same information. In unranked play you can turn exact health numbers on in the options if you prefer them.

## Weapons back at their true speed

Fire rates were one of the most consistent pieces of feedback after 0.37.0. We measured every weapon against the original TrueCombat:Elite and corrected the ones that had drifted:

- Automatic weapons fire at exactly their original rates.
- Bolt-action rifles cycle at their original speed again.
- Pump shotguns now need a full pump between shots, which brings them back to the correct rate. The reload sound is fixed too: one shell, one sound, instead of a doubled and delayed effect.

Sprinting got a deliberate change. In the original you could keep sprinting while aiming down sights, and even with an empty stamina bar. Those are faithful details, but in practice they made fights feel wrong, and it was one of the clearest complaints from playtests. In 0.37.1, raising your sights ends a sprint, and an empty stamina bar means you stop sprinting. The original cost of jumping while sprinting is unchanged.

Several visual details are back where they belong. Switching weapons plays its proper animation, frag grenade explosions have their original look again in both DirectX 12 and OpenGL, each class uses its own character model, and a thrown frag grenade no longer looks like a smoke grenade in flight. Bullet holes and blood are cleared at the start of each round, and in borderless window mode the mouse stays on the game's monitor.

## Bots

Bots find their way around the maps better. Improved pathfinding means they get stuck less often and choose better routes, and they are better at keeping out of your line of fire.

## Smoother map loads

Some of you reported a stutter every time a new map started. The cause was a graphics cache that was meant to be built once per map, but was being rebuilt on every load. It is now built once, saved in the background and reused, so the first seconds of a map play as smoothly as the rest.

We also fixed several cases where the game could hang during startup or while connecting. Frame Generation now pauses while the game is minimised or in the background. Nine sounds that had gone missing are back. And the console log from your previous session is now kept, which makes your crash reports far more useful to us.

## Graphics

More world textures now have specular detail on the Ultra preset for a richer, more detailed look up close. HDR reflections have been tuned to look more natural.

## Names, accounts and reports

Orange is now available to everyone in the name colour picker. Account holders whose account took a moment to verify sometimes joined as "Player####". That no longer happens: your name is restored as soon as the check completes. Bug reports sent with **F12** now keep your draft until it has actually been sent, so a lost connection no longer costs you what you wrote.

We have also tightened and expanded our security measures.

## Launcher 2.5

The biggest launcher change is choice. **HD textures are now optional.** Switch them off under **Settings > Updates** to save disk space and download time. You can still join any server without downloading them first, and if you switch them back on, the launcher fetches whatever is missing.

The rest is polish. The News page and patch notes load again. "What's New" no longer overlaps the Support button, and the layout holds up in maximised and larger windows. Only one launcher runs per install, so duplicate tray icons are gone. Your desktop shortcut survives updates. Download progress reads more cleanly, and the German, French and Polish translations have been improved.

## A new intro

The game now opens with a Team Terminus card followed by the Platinum logo, replacing the old intro movies and exit screens. The intro music is "Venom" by Scott Buckley, licensed under CC BY 4.0.

## How we tested it

0.37.1 went through the same release suite as every version before it: the full regression across movement, combat, network feel, graphics, settings and restarts, in both DirectX 12 and OpenGL, plus the launcher's update path. Each fix in this release was also tested on its own before it was merged, and the weapon timings were checked against the original game.

## Still on our list

One report from 0.37.0 is not fixed in this release. Some players lose all sound after alt-tabbing or after a change to their audio device, and it stays silent until they restart the game. We now know why it happens and a fix is in testing for a future update. Until then, restarting the game brings the sound back.

As always, if something feels wrong, press **F12** in game to send us a report. This update exists because you did. Thank you for playing.
