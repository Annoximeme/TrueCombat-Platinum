---
title: Inside 0.37.0, our biggest update yet
date: 2026-11-14
time: 09:00
summary: A rebuilt interface, a tactical map, photo mode, optional player accounts, bots that respect your line of fire, one-life Bomb rounds and a long list of fixes from your reports. Here is what changed, why, and how we tested it.
image: img/devlog/a-new-look.webp
tag: Release
version: 0.37.0
---
Version 0.37.0 is out, a day after the 0.36.1 hotfix. It is the largest update TrueCombat: Platinum has had. Six separate pieces of work that had been built and tested on their own were brought together into one release: a new interface, a set of visual and quality-of-life features, optional player accounts, a studio refresh, smarter bots and a batch of fixes from your playtest reports.

Putting that much into one update is a risk, so we treated it as one. Every piece arrived with its own tests. They were merged one at a time, each in a way that could be taken back out cleanly, and then the whole game was tested again as a single build before it was allowed anywhere near the launcher.

> The launcher picks up 0.37.0 by itself and your settings carry over. This first update from 0.36 is a larger one-time download, because we changed how game files are stored so that future updates can be smaller.

## A new interface

Every menu and the in-game HUD have been rebuilt in the new Platinum style. The goal was not decoration. It was to make the information you need easier to read at a glance: clearer type, consistent spacing and controls that behave the same way on every page.

Not everyone wants change, and the old HUD has been part of TrueCombat for a long time. So the classic HUD is still there, one switch away in the options. You can also scale the menus to 100, 90 or 80 percent under **Options > HUD & Effects > Menu size**, and the HUD now keeps its layout on screens narrower than 16:9.

We tested the new menus at eight resolutions, from 1280x720 to 3840x2160 and from 4:3 to ultrawide, in both renderers, and checked that keyboard focus lands on the right control at every menu size.

## Seeing more of the fight

We wrote about these features in detail in [A new look, from the loading screen to the kill feed](devlog-a-new-look.html). The short version:

- Every map has its own **loading screen**.
- Hold **M** for a **tactical map** of the battlefield and your squad.
- A **podium** at the end of every match celebrates the top players.
- **Photo mode** and camera paths for screenshots and videos.
- **HDR10 output** for HDR displays, and optional per-map colour grading.
- The Graphics menu shows an estimated GPU cost and a preview for each setting.
- Kill feed icons are drawn from the real weapon models.
- Prompts show your actual key bindings, and error screens explain what went wrong.

## Optional player accounts

You still do not need an account to play. Your identity in TrueCombat comes from a key on your own PC, exactly as before. What 0.37.0 adds is the option to link that PC to an account, or to link in seconds with your phone. With an account you can switch between profiles in the launcher, reserve your name, and show a clean-record tick on your profile. There is also a new "Looking for a squad" option on the Servers page.

## Gameplay and fixes

Most of the fixes in this update come straight from your playtest reports after 0.36.0. 0.36.1 already shipped the most urgent movement and control fixes. 0.37.0 includes those and adds:

- **Bomb is now one life per round.** Players who join mid-round wait for the next round. In our bot matches this took respawns in a Bomb round from 26 to zero.
- Blood effects are back.
- Fixed missing textures on the hands and pliers while defusing.
- The SIG 552 and SPAS-12 sights are correctly aligned.
- The shotgun pumps after every shot.
- Aiming down sights now has a subtle weapon sway that grows while you move and after you sprint. You asked for this, and it is adjustable.
- Legs no longer flicker into the wrong animation when you run on slopes.
- Bullets hitting windows show glass impacts.
- Every option in the settings menus was checked to make sure it actually changes, applies and saves what it says it does. Several that did not now do.

## Bots

Two bot changes in this release. Bots now step clear of your line of fire as soon as you raise your sights or fire, and they pick the open side if a wall is in the way. And bots stay on the objective in Bomb and CTF instead of chasing every sound they hear.

We tested the bot changes in matched matches against 0.36.0 on all six Bomb maps, with the same random seeds on both sides, to make sure nothing else changed. Plants, stalls, crashes and stuck bots all came out the same.

## Servers and voting

Map votes now only offer maps from the server's own rotation, and a vote no longer breaks a server's mode rotation. The number of votes each player can call now also survives a map restart.

We have also tightened and expanded our security measures.

## The launcher

Launcher 2.4 adds a tray panel and full controller navigation. Fresh installs now start on the graphics preset recommended for your card, even if you skip the welcome page. Most importantly for the future, updates can now download individual files rather than one large package, so they are smaller and recover better from a bad connection.

## How we tested it

Before 0.37.0 was packaged, the final build went through the same release suite as every version before it, plus checks written for each new piece:

- the full regression suite, covering movement, combat, network feel, graphics, settings and restarts;
- hit registration under simulated lag;
- 128 updates per second;
- voice chat on teams and in practice;
- the new menus and their options, in both renderers;
- the account flow;
- the launcher's update path, including what happens when a file fails to download.

A few things can only be checked by a person: the HDR output, controller navigation and a handful of key-binding screens. Those were checked by hand.

## What did not make it

A fix for sound dropping out and the mouse unlocking in borderless windowed mode is written, but we could not reproduce the original problem reliably enough to prove the fix works. Rather than ship a guess, it moves to 0.37.1. So do a new weapon-switch animation, a new frag explosion and more character choices per class, which are built but not yet tested in game.

As always, if something feels wrong, press **F12** in game to send us a report. Thank you for playing, and for telling us what to fix.
