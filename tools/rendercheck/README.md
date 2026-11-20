# Render check

Shows what a change does to the picture, frame by frame. It is the visual counterpart of the
[feel check](../feelcheck/README.md): engine work on the renderer has to either leave the picture
exactly as it was, or change it only where it was meant to.

```
tools/rendercheck/render-check.sh <base> <kit folder | -> ["obj_village obj_railhouse"] ["opengl1 vulkan"]
```

- `<base>`: a release tag (`v0.39.5-sandbox42`), a source zip or a source folder, as `tools/ci/kit-gate.sh`.
- `<kit folder>`: `patches/*.patch` (applied in name order) and optionally `files/`, as a kit-gate kit.
  `-` checks the base against itself.
- `EXPECT=changes` for a kit that is meant to change the picture (a lighting or shader change): the
  differences are reported, with pictures, but do not fail the check.
- Result: `render-check/SUMMARY.md` and `render-check/report/<map>-<renderer>/`, exit 0 when every map
  is deterministic and (unless `EXPECT=changes`) unchanged.

Needs Xvfb, Mesa (llvmpipe for OpenGL, lavapipe for Vulkan), clang, cmake, python3 with numpy and
Pillow, and the Linux client build dependencies (`build-linux-client.sh` lists them). A run of two maps
on both renderers takes about 6 minutes on a 4-core machine after the first build.

## How it works

1. Both trees get the render check hook (`rendercheck_hook.py` adds `cl_renderCheck` to the client's
   frame code) and are built as Linux clients with the OpenGL 1 and Vulkan renderers
   (`build-linux-client.sh`). The Vulkan renderer shares its frontend with the DX12 renderer. The hook
   never goes into a release build.
2. Per map, the base build plays a seeded bot match and records a demo while the camera visits spawn
   points spread over the map (`scenes.py` reads them from the map's BSP and picks the ones farthest
   apart).
3. The demo is played back with `cl_renderCheck <fps>`: every frame advances exactly 1000/fps ms of
   demo time, whatever the machine's speed, and every N-th frame is saved as a screenshot.
4. The base plays the demo twice per renderer. If those runs differ, the map fails as "not
   deterministic", because the check could not be trusted there. Then the kit build plays it once.
5. `compare_images.py` compares every kit frame with the base: share of changed pixels, largest
   difference and PSNR, and a picture per changed frame (base, kit, and the changed pixels in magenta).

### Rasterizer noise

Mesa's software rasterizer can round a handful of pixels differently from one run to the next (seen:
1 to 34 pixels of a 1024 x 768 frame, off by 1 or 2 levels out of 255, at a shadow edge). Such
differences are counted as noise, not as a change (`--noise-level 2`, `--noise-share 0.02` percent),
and pixels that already differed between the two base runs are left out of the kit comparison. A real
change is far bigger: 2 % more ambient light changed 3.5 to 7.7 % of the pixels by up to 10 levels,
on every frame.

## Checked

| Run | Result |
|---|---|
| v0.39.5 against itself and against the phase 0 engine kit (profiler, dev build switch, job system) | pass: unchanged on Village and Railhouse, OpenGL and Vulkan |
| Test kit: ambient light x 1.02 | fail as it should: 17 of 17 frames changed on both renderers |
