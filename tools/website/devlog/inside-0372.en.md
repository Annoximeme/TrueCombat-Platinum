---
title: Inside 0.37.2, eyes up
date: 2026-11-16
time: 03:30
summary: A live minimap, hits you can feel, friendly fire, and a game that looks like Platinum from the taskbar to the first frame. Here is what changed in 0.37.2, and why.
image: img/hero-snow-warehouse.webp
tag: Release
version: 0.37.2
---
0.37.1 was about fixing what you told us felt wrong. 0.37.2 is about awareness: knowing where your team is, knowing when you are under fire, and knowing that every round you fire counts, including the ones that hit a teammate.

> The launcher installs 0.37.2 by itself and your settings carry over.

## A live minimap

The tactical map has always been one key away, but holding a key to see where your team is means taking your hands off the fight. 0.37.2 adds a **live minimap** in the top-right corner.

It turns with your view, so up is always the way you are facing. It shows the layout of the map, the bomb sites, north and your own team. Enemies never appear on it: the minimap only shows what your side already knows. The objective panel and the network readout move down to make room, and go back to their usual place if you switch the minimap off under **Options > HUD & Effects**.

**M** opens the full tactical map again. Older profiles had the key bound to something else after an earlier change, and they are corrected automatically. If you had deliberately put another action on M, it stays where you put it. Servers that turn the tactical map off hide the minimap too.

## Hits you can feel

Until now, the first sign that you were being shot was often your health bar. That is too late. In 0.37.2, taking a hit kicks your view, flashes the screen red and leaves a blood mark on the side the shot came from, so you know where to turn before you have read a single number.

Being shot at matters too. Rounds that crack past you now desaturate the edges of your screen and shake your view. Pinning someone down is a real tactic again, and you will know when it is happening to you.

Both effects work with the Platinum and Classic HUDs, in DirectX 12 and OpenGL.

## Friendly fire is on

Teamwork means trusting your teammates with your back, and that trust only means something if a careless shot has a cost. **Friendly fire is now on.** Bullets, knives and grenades hurt teammates. Team kills are counted as team kills and no longer add to your score.

Check your target, and think twice before you throw a grenade into a room your team is clearing.

## A HUD that stays out of the way

When the Platinum HUD shows its kill card, the "You were killed by" line in the middle of the screen is gone. It said the same thing twice, in the spot where you were looking. The Classic HUD keeps the original line.

Coloured player names now show every colour on the Platinum HUD. Several colours from the launcher's name colour picker used to show up without their colour in chat, in the Deployment Menu and on HUD cards. They now appear the way you picked them.

## Throwing grenades properly

Grenades now play their pin-pull and throwing animations in first person, and leave from your throwing hand instead of the centre of the screen. Where a grenade lands has not changed: the throw is exactly as strong and as accurate as before. It just looks like a throw now.

## Names

If a name is reserved by its owner and someone else joins with it, they play as "Player####". Until now they were never told why. The game now explains it once, in plain words. Names that imitate staff tags are also cleaned up more thoroughly.

## A game that looks like Platinum

Until now, the game window, the taskbar and Task Manager still showed the old engine's icon and name. They now show the Platinum badge and **TrueCombat: Platinum**.

The Team Terminus and Platinum intro had a problem of its own: when you pressed Play, Join or Practice in the launcher, the game skipped straight to loading, and you only saw the intro if the game opened to the main menu. The intro now plays first, and the game starts the moment it ends. Launcher 2.5.1 makes this change.

## Behind the scenes

Bots are ready faster when a server rotates between game modes on the same map. Windows dedicated servers are lighter and run more smoothly. The in-game What's New card has been updated for this release.

## How we tested it

0.37.2 went through the full release suite: movement, combat, network feel, graphics, settings and restarts, in both DirectX 12 and OpenGL, plus the launcher, the installer and the update path. Every new feature in this update was also tested on its own, on both renderers and with both HUD styles, before it went into the release.

## Still on our list

Two things are not finished yet. The kill feed and the scoreboard still show team colours rather than each player's own name colours. And some players still lose all sound after alt-tabbing or after a change to their audio device. Both are in progress for a future update. Until the sound fix lands, restarting the game brings the sound back.

As always, if something feels wrong, press **F12** in game to send us a report. Thank you for playing.
