---
title: Storm over Northport
date: 2026-11-19
time: 04:30
summary: Rain, thunderstorms, soaked streets after the rain, snow and wind. Every map now rolls its own weather when it loads, the same for every player on the server, and the loading screen tells you what's coming.
image: img/devlog/weather-northport-storm.webp
tag: Graphics
version: 0.39.4
---
Northport has always looked like it was about to rain. Grey water, red sheds, puddles on the quays that never dry. For twenty years the rain never came. In 0.39.4 it does.

Every map now rolls its own weather when it loads: clear, overcast, rain, a full thunderstorm, the soaked hour after the rain, snow or a windy day. It isn't a setting and it isn't decoration that only some players see. The server picks the weather, every player on that server gets exactly the same sky, and the loading screen tells you what you're walking into before you spawn.

![A thunderstorm over Northport on the Ultra preset](img/devlog/weather-northport-storm.webp "Heavy rain and a black sky over the Northport yard. Ultra preset, DirectX 12.")

## Why weather, and why for everyone

A map you've played a thousand times stops looking like a place. Weather is the cheapest way to make it a place again. The same yard reads differently when the light goes flat, the ground turns dark and every surface hisses with rain. You move differently, you listen differently, and the round you remember is "the one in the storm".

We thought hard about making it an option. We decided against it. If one player turns rain off and another leaves it on, they're not playing the same round anymore: one of them sees a cleaner screen, the other hears a footstep through the rain. So there is no switch. The weather belongs to the round, like the map does. That also forced us to build every weather type so that it never makes another player harder to see. More on that below.

## How a round gets its weather

When a map loads, the server rolls the weather from a table made for that map. The roll gives three things: the kind of weather, how strong it is, and a seed. Those go to every player, and everything else is built from them on each machine: where the rain falls, how the gusts swell, when and where lightning strikes. Two players on opposite sides of the map see the same bolt at the same moment, and both hear its thunder arrive when it should.

The weather stays for the whole map. Going from warmup into the match doesn't re-roll it, so what the loading screen promised is what you play.

Every map has its own odds:

- **Northport** is the rain map. About half its rounds bring rain or a thunderstorm, and another one in six is the hour after rain, with the quays soaked and dripping. The rest are overcast, clear or windy.
- **Harbour** is close behind, with a little less storm.
- **Snow, Snowtown and the villa** snow on most rounds, from a few flakes to a blizzard. The rest are grey or windy.
- **Delta, Village, Railhouse, Stadtrand and the others** get a mix that leans towards clear skies, with Delta the windiest.

![The loading screen showing the weather for the round](img/devlog/weather-loading-screen.webp "The loading screen shows the weather next to the map plan, so you know what you're walking into.")

## On the loading screen

You see the weather before you see the map. A small badge sits in the corner of the map preview on the loading screen: **CLEAR**, **OVERCAST**, **LIGHT RAIN**, **HEAVY RAIN**, **THUNDERSTORM**, **AFTER THE RAIN**, **SNOW**, **HEAVY SNOW**, **WINDY**. It's a small thing, but it sets the mood while the map loads, and on a storm round the yellow stripe tells you to expect lightning.

## Rain

Rain is the heart of this update, and it took the most work.

A rain drop in TrueCombat is a thin streak that falls along its own speed and the wind's, so a gust visibly leans the rain. Up to 2,600 of them are alive at once in a wide circle around you, more close up where you can see them and fewer far away where they'd only be noise. Streaks very close to your eyes fade out, so the rain never puts a bright bar across your sights. Far streaks stay about a pixel wide, so a downpour looks dense without turning into a grey wall.

The hard part is knowing where rain can fall. Rain that falls through a roof is the fastest way to ruin the effect. The game checks the sky above every patch of ground around you. Under a roof, a canopy or an overhang, nothing falls. Out in the open, every drop lands on the real ground height, so it doesn't vanish in mid-air or fall through a crate. The check is cached per patch of ground and spread over several frames, so it costs almost nothing once you've looked around.

When a drop lands, it splashes:

- **On water and puddles**, a ring spreads out across the surface. Northport's harbour basin dances in a storm.
- **On hard ground**, a tiny crown of spray jumps up and a small ring spreads.

Rain also changes the ground itself. On DirectX 12 with Ultra materials, the wet patches we introduced in 0.39.0 now follow the weather. Light rain darkens part of the ground, heavy rain soaks almost all of it, and puddles shine. This works on every map, not only the ones that had wet patches before.

![Rain splashing on the Northport quays](img/devlog/weather-northport-rain.webp "Rain on the quays: every drop lands on the real ground and splashes, and puddles ring. Ultra preset.")

## Thunderstorm

A thunderstorm is rain turned all the way up: the heaviest downpour, strong gusts that lean the rain sideways, a dark overcast sky and lightning.

We spent a lot of time on where the lightning should strike. Our first version struck inside the map. It looked great in a screenshot and terrible in a fight: a white line across the middle of the screen while you're aiming down a street is a distraction, not an atmosphere. So lightning now strikes **out past the edge of the map**, from high in the clouds down behind the rooftops. You see it over the buildings, the sky flickers, and a moment later the thunder rolls in. It never lands between you and the player you're aiming at.

Each strike has a shape of its own, a jagged bolt with a soft glow around a white core, and it flickers like the real thing: one bright stroke, then two or three weaker return strokes over about half a second. The screen gets a short, faint flash at the same moment, much weaker when you're indoors.

The thunder comes from the new weather sounds in the same update. It travels at the speed of sound, so a strike 3,000 units away is heard more than a fifth of a second after you see it. Close strikes crack and boom; distant ones roll low; indoors they're muffled. Since every player gets the same strikes at the same moments, everyone hears the same storm.

![Lightning over the Northport rooftops](img/devlog/weather-northport-lightning.webp "Lightning strikes beyond the map, over the rooftops: you see it, and a moment later you hear it. Ultra preset.")

## After the rain

Our favourite one is the quietest. After the rain, the storm has passed but the world hasn't dried: the ground is soaked, puddles shine, a few last drops fall, water drips around you, and your footsteps sound wet. The sun comes back at less than half strength through the thinning clouds.

It's the round where the map looks most different and plays exactly the same. There's nothing in the air and nothing to see through, just a wetter, colder version of a place you know.

![Northport after the rain](img/devlog/weather-northport-afterrain.webp "After the rain: soaked ground, shining puddles and a cold light. Ultra preset.")

## Snow

The snow maps always had a little snowfall. Now it comes and goes with the weather, from a few lazy flakes to a heavy fall that drifts on the wind. Each flake sways on its own path, and like the rain it only falls where the sky is open. When the weather snows, it replaces the map's own snowfall, so the two never stack.

![Heavy snow on Snow](img/devlog/weather-snow.webp "A heavy snowfall drifting on the wind. Ultra preset.")

## Wind and overcast

A windy round blows harder: the gusts that already moved snow and leaves are stronger and faster, grit skims along the ground on the gusts, and leaves blow across every map, not only the green ones. The wind loop you hear follows the same gusts.

Overcast is the simplest weather and changes the map more than you'd think. The sky turns to low grey cloud, the sun shafts and glare go away, and the colour cools down a touch.

## Fair in Ranked

Weather in a competitive shooter is only fun if it's fair. Every rule here comes from one question: does this make another player harder to see or hear?

- **Everyone gets the same weather.** The server picks it and every player sees it. There is no option to turn rain off for a cleaner screen.
- **The colour change never touches brightness.** Rain and storms shift the colour a little colder and less saturated, but brightness and contrast stay exactly where they were, so a player in a doorway is as visible in a storm as on a clear day.
- **On Ranked and clan matches the heavy end is capped.** Every kind of weather can still roll, but rain, storms and snow are held at a moderate strength, and the lightning flash is half as bright.
- **Rain never hides footsteps.** The rain sounds sit well under the quietest footstep, and they dip for a moment when another player steps near you.
- **Fog and golden hour aren't in this update.** Both are on our list, but fog is exactly the kind of weather that hides players, and we want to get it right before it can roll in a match.

## Performance

Weather is drawn on your graphics card, with no new files to download and the same look on DirectX 12 and OpenGL, Remastered and Classic. The wet ground and colour change need DirectX 12 with Ultra materials. Everything else shows on every preset. Rain is the heaviest weather, and it's built to stay cheap:

- drops behind you aren't drawn at all,
- the sky check is cached and spread over frames,
- the number of drops rises and falls with the strength of the rain, and on an ordinary clear round nothing runs at all.

## For server owners

Weather is on by default and rolls by itself. For events you can force a weather on your server, for example a storm at a set strength. Ranked servers keep the caps above whatever you choose.

## Tested

We tested the weather on every map, in every weather, with bots fighting on Northport and Snow for long rounds in random weather, and with the server and both game builds checked on Windows and Linux. The strike timing, the sky and the loading screen were checked side by side to make sure every player sees the same round.

Some things only show on a real screen, so the last pass is on our own PCs before 0.39.4 ships: rain density against each map's sky, the splashes on DirectX 12, and the frame rate in the heaviest storm.

> The next time you load into Northport and the badge says THUNDERSTORM, stand on the quay for a second before you run. Listen for the thunder.

See you in the rain.
