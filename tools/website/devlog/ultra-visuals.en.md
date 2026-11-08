---
title: New light for old maps
date: 2026-11-08
summary: The Ultra preset brings modern lighting, real surface materials and sun shadows to every map on DirectX 12. Here is how we built it without changing how TC:E plays.
image: img/devlog/ultra-railhouse-ultra.webp
tag: Graphics
version: 0.33.0
---
Every map in Platinum was built for a renderer from 2003. The geometry, the sight lines and the dark corners are part of how the game plays, and players learned them over years. So when we set out to modernise the visuals, the first rule was simple: the new look can change how a map feels, never how it plays.

That rule shaped everything that follows. The work lives in a new preset, **Ultra**, on DirectX 12 only. Low, High and OpenGL render exactly as they did before, and we check that on every build.

## Phase one: the look

The first phase changed how light turns into colour on your screen. Ultra uses filmic tone mapping, which handles bright skies and deep shadow in the same frame without blowing out either, and automatic exposure, so stepping out of a dark corridor into daylight feels like it does in real life.

On top of that sits a colour grade. We kept it deliberately restrained. A heavy grade looks good in a trailer and terrible in a firefight, because it pulls players into the background. Every grading choice was tested against one question: can you still see the enemy?

## Phase two: real surfaces

In the original game a brick wall is a flat picture of bricks. Light hits every pixel of it the same way. Ultra gives every surface on the six maps a set of material maps: which parts stand out and which sink in, how rough or polished it is, and whether it is metal. The renderer uses them to light each surface the way the real material would behave.

!compare(img/devlog/ultra-railhouse-high.webp | High | img/devlog/ultra-railhouse-ultra.webp | Ultra | Railhouse, the same frame on High and on Ultra with surface materials. Captured before sun shadows were added.)

The material maps are generated from the HD textures with an offline tool, not painted by hand, so a few surfaces read a painted stain as relief. Those are the ones we will keep refining. The maps ship as one extra pack. The first time you load a map on Ultra, the game compresses its materials for your graphics card and keeps the result, so every load after that is quick.

!compare(img/devlog/ultra-village-high.webp | High | img/devlog/ultra-village-ultra.webp | Ultra | Village from the spawn. Notice the paving, the barrels and the fence.)

## Phase three: light and shadow

The last phase added what most players will notice first: real-time shadows from the sun. Players, props, weapons and the world itself now cast them, sharp up close and softer in the distance. Small contact shadows ground objects where they touch the floor, and light shafts through fog are available as an option.

That raised a real design question. On Ultra, other players cast sun shadows too, which means a shadow can give away someone standing just around a corner. We decided to keep it. It is how light works, it rewards awareness, and both sides get the same information. Server owners who want a strictly classic match can force the classic look for everyone with `sv_forceClassicVisuals 1`.

> Shadows from muzzle flashes and explosions are next on the list. They did not make this update, because we were not yet happy with how they perform.

## Fair by design

Every phase went through the same checks before it was allowed near a release:

- **Visibility.** Players placed in smoke and in the darkest spots of each map must stay as easy to see on Ultra as on High.
- **Performance.** Measured on every map. The materials pass added at most about half a millisecond per frame on our test machine.
- **Memory.** Ultra uses roughly 150 to 190 MB more video memory.
- **No regressions.** Low, High and OpenGL compared frame by frame against the previous release.

Anti-aliasing picks itself on Ultra: DLAA on RTX cards with 12 GB of video memory or more, and TAA everywhere else.

## What it means for you

If your PC handles High comfortably, give Ultra a try from the launcher's graphics presets. If you prefer the game exactly as it always looked, nothing changes for you. Either way, every player still sees the same map, the same sight lines and the same enemies.
