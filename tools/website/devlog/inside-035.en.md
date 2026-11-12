---
title: Inside 0.35.0, our biggest update yet
date: 2026-11-12
time: 11:00
summary: Easy Anti-Cheat with no sign-up, a launcher rebuilt from scratch, player stats from every verified match and the bulk of the playtest fixes. This is the long version: what changed, why we built it the way we did, how it was tested, and what did not make it.
image: img/media-village-hd.webp
tag: Release
version: 0.35.0
---
Version 0.35.0 went live on the morning of 12 November, at 07:39 Belgian time. It is the largest update TrueCombat: Platinum has had so far, and it was shaped more by you than any update before it. Most of what is in it started as a line in [What the playtests told us](devlog-playtest-fixes.html), a message on Discord or a clip from a match.

The patch notes list every change. This post goes behind them. It explains the four big pieces of the update, the decisions behind them, and how we tested them, and it is honest about the items that did not make the cut. It is a long read, so use the contents list to jump to what interests you.

> Updating is the same as always: the launcher picks up 0.35.0 by itself. The first time anti-cheat is set up on your PC, Windows asks once for permission to install its service. That prompt is expected.

## Easy Anti-Cheat

From this update on, TrueCombat: Platinum ships with Easy Anti-Cheat. When you press PLAY, the launcher starts the game through the anti-cheat bootstrapper, and the anti-cheat service checks the game while it runs. The service is installed once, by the installer or on the first start, and that is the one administrator prompt you will see.

All four official servers, Ranked, Unranked and both pickup servers, now require it. They were switched over in the hours after the release went out, and a clean copy of the published game was confirmed connecting to them with protection active.

### No account, still

Anti-cheat for an online game needs to know who is playing, so that a ban sticks to a player and not to a single session. The usual answer is to make everyone sign in with an account from the anti-cheat provider. We did not want that. Platinum has never asked you to create an account, and an anti-cheat system was not going to be the reason to start.

Our first plan was to use an identity tied to your PC. It worked in testing right up to the last step, where Epic's service refused it: anti-cheat requires a proper sign-in, and an identity that only says which machine you are on is not accepted. So we built our own sign-in instead.

It works like this. The first time you play, the game creates a private identity key on your PC. When you start a protected session, the game proves to our sign-in service that it holds that key, without ever sending the key itself. Our service then hands Epic a short-lived token that says "this is the same player as last time". Epic accepts it, and the anti-cheat session starts. To you, all of this is invisible. There is no form, no password and no email address. The only thing that ever leaves your PC is a scrambled ID that cannot be traced back to you.

The launcher's new Profile page lets you back that identity up and restore it. Do that before you reinstall Windows or move to a new PC, and keep the backup file private: it is what carries your name on the leaderboards and your match history.

### What it checks

The anti-cheat service only runs while the protected game is running. It checks that the game's own files are the ones we shipped and watches the game process for tampering. In our final tests, a protected copy of the published build connected normally, a copy with one modified interface file was refused, and an unprotected client on a server that requires anti-cheat was removed within forty seconds.

One detail that matters for updates: the launcher itself is deliberately left out of the file check. The launcher updates itself between game releases, and we did not want a launcher update to lock you out of servers until the next full release.

### Where you see it

Servers that require anti-cheat show a green shield in the in-game server list and an EASY ANTI-CHEAT tag in the launcher. Servers that have it switched on but do not require it show ANTI-CHEAT ON. The connect screen tells you which kind of server you are joining. Community servers choose for themselves whether they use it.

## Launcher 2.0

The launcher is the first thing you see and the last thing anyone thinks about, until it gets in the way. The old one had grown page by page over many updates. Version 2.0 is a clean rebuild of the whole interface, with everything that had been added over time put where it belongs.

![The Play page of Launcher 2.0](img/devlog/launcher-2-play.webp "The new Play page: news, your servers and your next match, one click away.")

- **A new layout.** A navigation rail on the left and a full-screen Play page with the latest news, your servers and a practice match one click away.
- **A real server browser.** Every server in a sortable list with live player counts, ping and anti-cheat status. Quick filters hide full or empty servers, or show only ranked servers or servers without bots. Community servers that run the official build carry a Verified tag.
- **Profile, Replays and Host.** Your rank, rating and recent ranked matches, your recorded matches, and a page to host your own server.
- **Settings that are actually launcher settings.** Minimise to the tray, come back after a match, start with Windows, accent colour, interface size, a download speed limit and more.
- **Four languages.** English, German, French and Polish.
- **The small things.** Full keyboard control, sharp text on every monitor and scale, a Verify and Repair button for your game files, and a What's New page after each update.

Two long-standing annoyances are gone as well. A name you set in the game, colour codes included, is no longer overwritten by the launcher on the next start. And join links from the website and Discord now always open your installed copy of the game, not a second copy you may have lying around for testing.

### How it was tested

A launcher touches your files, your settings and your network, so it gets its own test gate before every release. For 2.0 that meant 54 screenshot checks across every page and language to catch layout breaks, 61 deliberately broken and malicious join links to make sure none of them can do anything they should not, and the full self-update cycle from older launchers, run fourteen times. The installer was tested separately with the anti-cheat service setup.

## Player stats from every verified match

Player profiles on truecombat.eu now record every verified match on the official servers, ranked and unranked, and they record a lot more of it: accuracy, hit locations, opening kills, clutches, multi-kills, rivals and per-map records. [Every fight on the record](devlog-every-fight-counts.html) explains what is tracked and the rules that keep it honest, so this is the short version.

The important change in 0.35.0 is that the rules are now enforced. A match only counts when the server had anti-cheat on from the first second to the last. Only fights between real players count: nothing you do to a bot, or a bot does to you, lands on your record. Warm-up and idle time are left out. Detailed stats went live on both official servers about forty minutes after the release, as soon as they were running with anti-cheat required.

Your skill rating still only moves on the Ranked server. Matches from before this update stay on your profile with the totals we recorded at the time.

## The playtest fixes

[What the playtests told us](devlog-playtest-fixes.html) listed every problem from our community playtests. Most of that list is fixed in 0.35.0. We have updated that post item by item, so here we want to explain how the work was done, because the most useful thing we learned was not what was broken, but how to tell.

### Measure first, then fix

Platinum's game code is a native rebuild, not the original TC:E code, and a rebuild can drift from the original in ways nobody notices until a room full of veterans plays it. So for every reported problem, the first step was not a fix. It was a measurement against original TC:E 0.49b.

That changed several fixes. Take jumping. Players told us jumps did not carry like the original. Our first suspect was a rule that shortens a moving jump. When we measured it against 0.49b, that rule turned out to be exactly right. The real differences were elsewhere: the original lets you take a full-power standing jump onto a low object such as a dumpster or the container on Delta, and it briefly limits how high you can jump right after a hard landing. Platinum had neither. Both are back, and the jump onto a low ledge went from falling short to clearing it.

Crouch-walking was the same story. It felt fast, loud and bouncy because footsteps and head bob ran at two and a half times the original rate while crouched. Rebuilding the timing for every stance from the original fixed all three complaints at once. Walking, aiming and leaning are now quiet, as they were in TC:E.

### Gunplay

- **Spread and damage.** We audited every weapon's spread and damage values against the original tables. They already matched. That told us to look elsewhere for the hits that did not land, and the next two fixes are what we found.
- **Hits on leaning players.** The game on your screen and the server disagreed slightly about where a leaning player's body was. Shots at a leaning target now land where you see them.
- **Your first shots after respawning.** Online, the first moves and shots after a respawn could be thrown away. In a simulated match on a bad connection, the number of lost inputs after a respawn dropped from up to fourteen to at most five, and nineteen of twenty-one test shots counted, with the misses at the very edge of the head and legs.
- **Bolt-action rifles.** The R93 and SR-8 now work the bolt after you release the trigger, with its own sound, before the next shot. The rifle has its deliberate rhythm back.
- **Grenades.** You can cook a grenade again: hold fire to prime it, release to throw it with the remaining fuse. Throwing your last grenade no longer fires your gun. Blasts check line of sight to several points on your body, so cover works, and explosions are no longer muffled by nearby walls.
- **No firing while sprinting.** As in the original, the weapon is ready a quarter of a second after you stop sprinting.
- **Aiming down sights** now slows you down as it should, and players and bots visibly shoulder their weapon while aiming.

### Maps

The invisible wall at the small house on the Delta bomb site turned out to be a capture-point post from the Flag Capture mode, left solid in every other mode. Every map has these, so we removed them in all modes outside Flag Capture rather than fixing Delta alone. We also went through every map, surface by surface, looking for missing textures, and found none. Separately, some weapon parts showed a placeholder texture, the AKS-74U charging handle among them, and those are fixed. If you still see a surface that looks wrong, press F12 while you look at it.

Doors now behave like the original: a use icon when you can open one, the original sounds, and a slow, quiet opening when you are walking or crouched.

### Menus, chat and match flow

- **Options in the pause menu.** A new MOUSE & VIEW page: sensitivity with exact typed values for high and low DPI mice, separate aim and scope sensitivity, field of view from 80 to 110, smoothing and acceleration.
- **Report a bug from the game.** Press F12, or REPORT A BUG in the pause menu, and describe what happened. The report is saved with a screenshot and your recent console log. Our next playtests will run through it.
- **Chat and voice commands.** T and Y open the chat box again, and V opens the voice command menu.
- **Team selection.** Bots no longer count against team limits, every switch is confirmed, and a team picked while the map loads is kept, including for the next map. Automatic balance only steps in when teams really are uneven, and moves bots before people.
- **Warm-up.** Warm-up is now a practice round. You spawn straight away, respawn a second after dying, can try every weapon and change your loadout, and the match starts after a 30-second countdown once two players are in. Nothing in warm-up counts.
- **Find Servers.** The in-game server browser is now in the main menu and the pause menu, so you can change servers without going back to the launcher.

### Online play

The third round of online play work arrived in this update too. Join buttons on the website and in Discord open the game straight into the server. If it is full, the launcher waits for a slot and joins by itself. A short connection check before joining turns on extra packet protection if your route is losing packets. The scoreboard shows connection bars next to every ping, and `cg_netGraph 1` or `2` shows ping, packet loss and jitter while you play.

If you drop out of a match, you can rejoin within five minutes and keep your team and score. On Ranked, leaving a match you are losing now costs the full rating change, and the server limits how far back in time it rewinds the world to check a hit: at most 200 milliseconds. Without that limit, a player on a very slow connection could hit you well after you had reached cover on your own screen.

Server hosts get a join password that is actually enforced, timed bans with the reason shown to the player, and a ping limit. Under the hood, the game, the server and the server list now handle IPv6, and our server list can be reached over IPv6. That matters more each year as providers run out of the older address type.

## How it was tested

Every release goes through the same gate: a full regression of the game and the dedicated server on both DirectX 12 and OpenGL, the launcher and the installer. 0.35.0 passed all seventeen game and server checks on the final build, plus the launcher, installer and anti-cheat checks above. Each movement and gunplay fix also got its own measurement against the original, as described above, so a fix for one thing cannot quietly undo another. The build was frozen in the early hours of 12 November, packaged, signed for the anti-cheat and published a few hours later.

## What did not make it

Not everything on the playtest list is in this update, and we would rather say so than let it go quiet.

- **Prone hits.** Our weapon-by-weapon aim audit continued after the release and found one more case: shots at players lying prone do not always register. The cause is known and the fix is being tested.
- **Red dot sight.** The dot in the red dot sight is too small and too dim. It needs a change to how the sight is drawn, not just a texture.
- **Instant replay.** The two small replay fixes from the last update, the short clip in warm-up and the wrong length in the confirmation, are not in 0.35.0.
- **Bots.** Bots now visibly shoulder their weapon when they aim, but teaching them when to aim, when to lean and how to vary their routes is a larger piece of work. It is described in [The road ahead, in full](devlog-the-road-ahead.html).
- **The staff badge refresh** is not in this update either.

All of these are being worked on. As always, they ship when they pass the same gate as everything above, and not before.

## Thank you

This update exists because people played, noticed and told us. Some of the most useful reports were a single sentence: "the jump onto the container on Delta doesn't work". That one sentence led to a measurement, the measurement to the real cause, and the cause to a fix that changed how the whole game moves.

If something in 0.35.0 feels wrong, press F12 in the game, or tell us on [Discord](https://discord.gg/8kcHdg2Hch). The [roadmap](index.html#roadmap) shows what comes next.
