---
title: Remodelled, on the road to 0.40
date: 2026-11-17
time: 21:30
summary: We are rebuilding TrueCombat: Platinum from the inside out, one model at a time. A first look at the new weapon models, the redesigned interface and the lighting work heading for 0.40, with every before and after we have so far.
image: img/devlog/models-teaser-clean.webp
tag: Graphics
kicker: Road to 0.40
---
![The Road to 0.40: Remodelled](img/devlog/models-teaser.webp "The new P19 sidearm, one of the first models rebuilt from scratch.")

Most of what you see in Platinum today still comes from 2006. The maps, the weapons and the player models were made for the hardware of their time, and for a long time our job was to keep them working on modern Windows. With the new renderer, HD textures and the Ultra preset in place, the limit is no longer the engine. It is the models themselves.

So we have started remodelling the game. Slowly, carefully, and one piece at a time.

This is the long version of where that work stands. It covers three things heading towards update 0.40: new 3D models, a redesigned interface, and a set of lighting and rendering upgrades. It has more pictures than anything we have posted before, and most of them are early.

> Everything in this post is **work in progress**. The model renders come from our studio scene, not from the game. The interface and lighting images are **concept art**: they show the direction, not final in-game output. 0.40 is currently planned for early February 2027, and that date is provisional.

## New models, built from the ground up

TC:E's weapons were good for their day, but many of the first-person guns are still built from somewhere between 500 and 1,600 triangles. Our HD textures made them sharper. They could not make them rounder. A trigger guard drawn with eight edges stays an octagon however good the texture is.

We went through every model the game loads, more than 600 files, and sorted them by how much a new version would improve what you actually look at. Fourteen first-person guns are still on their original meshes. Hands, grenades, the knife, the bomb and the objective items are next to them on the list.

Then we built three samples to prove the method: a sidearm, a fragmentation grenade and a combat knife. Each one is a new, original model, not a cleaned-up version of the old one. Below, each sample sits next to the model it would replace, under the same lights and the same camera.

### Sidearm

!compare(img/devlog/models-pistol-today.webp | In the game today | img/devlog/models-pistol-new.webp | New model | The current sidearm (698 triangles) against the new P19. Drag to compare.)

The current pistol uses 698 triangles. The new P19 is built at full detail and brought into the game at around 9,000 triangles with a 2048 pixel material set: colour, surface normals, roughness and metal. That is what lets the slide serrations, the grip texture and the worn edges catch the light the way metal and polymer really do.

The markings are our own. Every new weapon carries fictional names and serial numbers.

### Fragmentation grenade

!compare(img/devlog/models-grenade-today.webp | In the game today | img/devlog/models-grenade-new.webp | New model | The current grenade (612 triangles) against the new M67-pattern model.)

The grenade goes from 612 triangles to around 3,000, with a 1024 pixel material set. The spoon, pin and ring are separate parts now, which matters for the pin-pull animation, and the stencilled lettering is part of the texture instead of being painted on blurry.

### Combat knife

!compare(img/devlog/models-knife-today.webp | In the game today | img/devlog/models-knife-new.webp | New model | The current knife (172 triangles) against the new clip-point knife.)

The knife is the biggest jump of the three: 172 triangles today, around 2,500 for the new one. A stacked leather grip, a proper guard, and a blade that finally has an edge.

### What happens next

These are renders of the source models. Before any of them reach the game, each one is baked down to its in-game budget, exported to the game's model format and checked in the engine on the Ultra preset next to the current version. Only a model that looks better in the game, not just in a studio, replaces the old one.

The order of work follows the list: small items and the older guns first, then their third-person versions and attachments. First-person hands and the player characters come later, because organic shapes need their own test before we commit to them. Characters will keep the same skeleton and silhouette, so nothing about hit registration or how a player reads at a distance changes.

## Every gun, in the studio

While the new models are being built, the interface needs pictures of the guns we have today. We rendered all 41 weapons and throwables from the game's own models, placed exactly where the game holds them, and lit in one studio setup. They will appear on the loadout screen, the end-of-round MVP card and a new weapon turntable.

![All 41 weapon renders](img/devlog/render-arsenal.webp "All 41 weapons and throwables, rendered from the game's own models.")

![AK-47 studio render](img/devlog/render-ak47.webp "AK-47")

![SCAR studio render](img/devlog/render-scar.webp "SCAR")

![M4 SOPMOD studio render](img/devlog/render-m4sopmod.webp "M4 SOPMOD")

![MP5 studio render](img/devlog/render-mp5.webp "MP5")

![Desert Eagle studio render](img/devlog/render-deagle.webp "Desert Eagle")

As each new model lands, its render is made again from the new version.

## A new interface: Command

The interface is being redesigned from the main menu to the last line of the scoreboard. We call the direction Command: the same chrome wordmark and red accents as the website, dark glass panels with corner brackets, clear grouping, and information you can read at a glance in the middle of a round.

All of the images below are concept art, made at 4K over real game captures. Fonts, spacing and colours come from one shared design system, so the game, the launcher, the installer and the website finally speak the same visual language.

![Main menu concept](img/devlog/ui-main-menu.webp "Main menu: quick join, live player counts and the latest news on the first screen.")

![In-game menu concept](img/devlog/ui-esc.webp "The in-game menu opens as a side sheet, with the live score and your game version.")

![HUD concept](img/devlog/ui-hud.webp "HUD: cleaner, lighter, and readable on every map.")

![Scoreboard concept](img/devlog/ui-scoreboard.webp "Scoreboard")

![Deployment screen concept](img/devlog/ui-deploy.webp "Deployment: pick your team, kit and weapons in one place.")

![Options concept](img/devlog/ui-options.webp "Options, grouped the way you look for them, with a live preview.")

### The match, from loading screen to map vote

![Loading screen concept](img/devlog/ui-loading.webp "Loading screen with the map briefing.")

![Round banner concept](img/devlog/ui-round.webp "Round start banner.")

![Bomb alert concept](img/devlog/ui-bomb.webp "Bomb alert, team list and direction markers in a live round.")

![MVP card concept](img/devlog/ui-mvp.webp "End-of-round MVP card.")

![Map vote concept](img/devlog/ui-vote.webp "Map vote at the end of a match.")

![Player card concept](img/devlog/ui-player-card.webp "Your player card on the main menu.")

### Detail work

The smaller things matter as much as the screens. Every weapon gets a clean HD icon. The menus move with short, soft transitions instead of snapping in. Every control has proper hover, pressed and focus states, and the whole interface can be driven from the keyboard. A new server browser shows what is happening on each server before you join. Colour-blind presets and a text size setting are part of the plan too.

![HD weapon icons concept](img/devlog/ui-icons.webp "One clean icon set for every gun.")

![Weapon turntable concept](img/devlog/ui-turntable.webp "Weapon turntable on the loadout screen.")

![Server browser concept](img/devlog/ui-servers.webp "The new server browser.")

![Interface states concept](img/devlog/ui-states.webp "Cursor, hover and focus states.")

### Sharper scopes

The scope reticles were drawn at very low resolution, as small as 64 by 64 pixels, and you could see it every time you aimed. We redrew all of them at four times the resolution. Each reticle keeps exactly the same aim point, so nothing about how a scope shoots changes. It just looks like glass instead of pixels.

!compare(img/devlog/reticle-eotech-old.webp | Today | img/devlog/reticle-eotech-new.webp | Redrawn | The holographic sight reticle, today and redrawn at four times the resolution.)

![HD reticles concept](img/devlog/ui-reticles.webp "The new reticles in the scopes that use them.")

### Installer and studio splash

The installer gets the same treatment, so the first thing a new player sees already looks like the game they are about to play.

!compare(img/devlog/installer-old.webp | Today | img/devlog/installer-new.webp | New | The installer welcome page, today and in the new style.)

![Studio splash concept](img/devlog/ui-splash.webp "Studio splash and title sequence.")

![Key art](img/devlog/store-key-art.webp "New key art for store pages and press.")

## New light

The third part of the work is the renderer. TC:E's maps were lit once, years ago, and much of that light is baked into the textures. The upgrades below make the light behave: explosions that light the walls, lamps that cast shadows, haze that has depth.

Every image in this section is a painted impression over a real Ultra capture from today's build. The final result will look different in places, and we will show real in-game captures as each piece is finished.

> None of these upgrades changes what you can see in Ranked. Fog, haze and lighting keep the same visibility, so nobody gains an edge from a graphics setting.

### Dynamic lights

!compare(img/devlog/engine-m3-dynamic-lights-now.webp | Today | img/devlog/engine-m3-dynamic-lights-concept.webp | Concept | An explosion lights the wall, the floor and the player beside it.)

Today only a handful of lights can touch a surface at once. The new system lights the world and the players from every nearby source, with physically based materials, so muzzle flashes, explosions and flares light their surroundings properly.

### Sky and atmosphere

!compare(img/devlog/engine-m4-sky-now.webp | Today | img/devlog/engine-m4-sky-concept.webp | Concept | A physical sky with distance haze, at the same visibility.)

### Bullet holes with depth

!compare(img/devlog/engine-m5-decals-now.webp | Today | img/devlog/engine-m5-decals-concept.webp | Concept | Impacts with chipped edges, cracks and dust that follow the surface.)

### Particles

!compare(img/devlog/engine-m6-particles-now.webp | Today | img/devlog/engine-m6-particles-concept.webp | Concept | Explosions with ten times the particles: sparks, debris and dust.)

### HD world textures

!compare(img/devlog/engine-m1-hd-textures-now.webp | Today | img/devlog/engine-m1-hd-textures-concept.webp | Concept | Village brick, up close, with full material detail.)

New high-resolution textures with full material maps for the world. They will be an optional download of about 1 GB, offered on the Ultra preset, so nobody who plays on a smaller connection or an older PC has to take them.

### Re-baked lighting

!compare(img/devlog/engine-m2-lightmaps-now.webp | Today | img/devlog/engine-m2-lightmaps-concept.webp | Concept | Railhouse with re-baked lighting: bounce light, soft shadows and contact shadows.)

The core maps get their lighting calculated again, with light that bounces off surfaces and shadows that soften with distance. If a map cannot be matched closely to how it plays today, it keeps its current lighting.

### Bounce light

!compare(img/devlog/engine-m7-bounce-now.webp | Today | img/devlog/engine-m7-bounce-concept.webp | Concept | Light that bounces off walls and floors in real time, on Ultra.)

### Lit fog

!compare(img/devlog/engine-m8-lit-fog-now.webp | Today | img/devlog/engine-m8-lit-fog-concept.webp | Concept | Lamps that light the air around them, and respect the shadows of what stands in their way.)

### Lamp shadows

!compare(img/devlog/engine-m9-lamp-shadows-now.webp | Today | img/devlog/engine-m9-lamp-shadows-concept.webp | Concept | Indoor and street lamps that cast real shadows, on High and Ultra.)

The DirectX 12 renderer gets all of these. The OpenGL renderer gets the HD textures, the re-baked lighting, the new bullet holes and the new particles.

## How it gets tested

Nothing here ships because it looks good in a picture. Every new model is checked in the game next to the one it replaces. Every interface screen is captured at 1080p, 1440p, 4K and ultrawide and compared with its concept. Every lighting feature has a performance budget it must stay within, and the full regression run covers both renderers, the server and the launcher before a release is packaged.

If something misses the bar, it waits for the next update. We would rather ship a smaller 0.40 that works than a bigger one that does not.

## What to expect

0.40 is planned as the biggest update Platinum has had: the new interface, the lighting work, and the first wave of new models. It is currently planned for early February 2027. That date is provisional, and we will confirm it here once the final test run is behind us.

The remodelling does not stop at 0.40. It is a long project, and we will keep posting before and after shots as each new model reaches the game. Tell us what you think in the comments below, or on [Discord](https://discord.gg/8kcHdg2Hch). Which model should we rebuild next?
