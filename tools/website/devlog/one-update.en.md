---
title: Ten pieces of work, one update
date: 2026-11-08
summary: The next update was built by ten separate efforts at the same time. How they came together into one build without stepping on each other, and what the final test gate looked like.
image: img/media-village-yard.webp
tag: Testing
version: 0.34.0
---
The update now in testing is the broadest one Platinum has had. A redesigned launcher, a Custom graphics preset, a new in-game Graphics page, weapon and view motion, voice commands, camouflage, climbing sounds, ultrawide support, Discord Rich Presence, a quality-of-life pass with votes, radio, demos and loadout presets, and server-side work for team balance, AFK handling and reports. Each of those came from its own line of work, developed and tested on its own copy of the game.

This post is about the less visible part: how ten separate pieces become a single build that we are willing to put on the download button.

## Why separate first

Working on everything in one shared tree sounds simpler, but it means every half-finished change can break every other test. Instead, each piece is developed against the current release, in this case 0.33.0, and tested there until it passes its own checks. Only then is it handed over as a patch: a precise description of every changed line, plus a checksum, a list of what it touches and the tests it passed.

That hand-over is where overlaps become visible. Three of the ten pieces change the same file that runs a match on the server. Four change the file that draws your view. Two change the in-game menus. None of them knew about the others while they were being written.

## Merging in a fixed order

The patches are applied in a fixed order, biggest and most invasive first, and each step is checked before the next one starts. When two pieces change the same lines, the merge is done by hand, line by line, and recorded. This time that happened eight times. The most delicate one was the first-person hand: the camouflage work gives it a new sleeve, and the animation work moves it with the weapon. The fix was to apply both, in the right sequence, and confirm the result compiles without a single warning and still passes the movement, combat, prediction and entity tests that every build runs.

The in-game menus were a special case. Two pieces rebuild the menu package, one for the new Graphics page and one for the new font, and the cheat detection on servers checks that package by checksum. So the menu sources from both are merged first, the package is generated once from the result, and the checksum is computed from that. Taking either piece's own package would have produced a client that every official server flags.

> Nothing in this update changes the network protocol. A 0.33 client can still see and join a 0.34 server. The upgrade only has to be installed to get the new features.

## What did not make it

Easy Anti-Cheat was planned for this update. The code builds and most of the checks pass, but the one that matters, a real client being reported as protected through the real anti-cheat bootstrapper, was not verified in time. It is held for the next update rather than shipped on partial evidence. The same rule applied to Discord Rich Presence for about an hour: its first full test failed at the Discord Join step, a fix was made and re-tested on both renderers, and only then did it go back in.

## The gate

Once everything is merged, the real candidate build is tested as a whole: seventeen automated match scenarios on DirectX 12 and OpenGL, with bots, on the official maps, covering combat, objectives, team play, settings changes and restarts, plus the launcher's own install and update tests and the graphics preset checks. A release only goes out when that run is green. If a single scenario fails, it is investigated, not re-run until it passes.

One scenario kept us busy today. A movement-speed check compares two speed settings and expects a ratio of at least 1.2. Three separate test runs measured 1.19. None of the changes in those runs touched movement, and the same check has flickered before, so the threshold is being reviewed rather than the game. It is a reminder that the test harness needs maintenance too.

If you play the update and something feels wrong, tell us on Discord with the map and the moment. Every piece of this update started as exactly that kind of note.
