# Preset comparison captures

Low, High and Ultra graphics presets, captured from one frame of the Railhouse backyard.

## Build and setup

- Build: 0.36.0 (sandbox28 release package with the HD texture, material and interface packs)
- Renderer: DX12, 1920x1080 borderless window, vsync on
- GPU: NVIDIA GeForce RTX 4080 SUPER
- Map: obj_railhouse, listen server, no master heartbeat

## Camera

- Position: 224 5536 25 (blue spawn, Backyard). Yaw 280, pitch 0, cg_fov 90.
- I recorded the camera once as a demo (presetcam) on a 1920x1080 client. Each preset then played the same demo in a fresh engine launch and captured at the same demo time. Edge alignment between the three frames is exact, with a 0,0 px shift.
- Hidden for capture: weapon (cg_gunX/cg_gunZ -200), limbo menu (cg_popupLimboMenu 0, closelimbomenu), objective hint (toggleobjectivedesc), bug-report hint, tips.

## Crop

- The source frames are lossless 1920x1080 TGA.
- Each preset is cropped to the box x 24-1656, y 50-917, which gives 1632x867. That's the 1280:680 slider aspect.
- No scaling, saved as PNG.
- The crop removes the remaining HUD: compass, location label and warmup text at top right, stance icons at bottom left, fire mode and ammo at bottom right.
- brick-crop-low-high-ultra.png is the source box x 176-876, y 200-700, shown at 100% for each preset side by side (Low, High, Ultra).

## Preset cvars

These are the exact values the 0.36.0 launcher writes. The ui_gfx* menu mirrors are omitted. Nothing beyond the preset was enabled. Ultra ships r_dx12Materials, r_dx12Specular and r_dx12Probes on, and the log confirms 247 material textures loaded.

### Low (platinum-preset-0.cfg)

```
set r_picmip 1
set r_textureMode GL_LINEAR_MIPMAP_NEAREST
set r_ext_texture_filter_anisotropic 0
set r_ext_max_anisotropy 2
set r_ext_multisample 0
set r_dx12Msaa 0
set r_dx12Hdr 0
set r_dx12Ssao 0
set r_dx12Tonemap 0
set r_dx12Bloom 0
set r_dx12BloomIntensity 0.00
set r_dx12Sharpen 0.00
set r_dx12Fxaa 0
set r_dx12AlphaToCoverage 0
set r_dx12Dlss 0
set r_dx12BloomThreshold 0.75
set r_dx12Taa 0
set r_dx12AutoExposure 0
set r_dx12Grade 0
set r_dx12Materials 0
set r_dx12Specular 0
set r_dx12Probes 0
set r_dx12Reflex 0
set r_dx12FrameGen 0
set r_dx12Shadows 0
set r_dx12ContactShadows 0
set r_dx12Volumetrics 0
set r_dynamiclight 1
set r_flares 1
set r_detailtextures 1
seta cg_impactEffects 1
seta ui_platinumPreset 0
```

### High (platinum-preset-1.cfg)

```
set r_picmip 0
set r_textureMode GL_LINEAR_MIPMAP_LINEAR
set r_ext_texture_filter_anisotropic 8
set r_ext_max_anisotropy 8
set r_ext_multisample 4
set r_dx12Msaa 4
set r_dx12Hdr 1
set r_dx12Ssao 1
set r_dx12Tonemap 1
set r_dx12Bloom 1
set r_dx12BloomIntensity 0.25
set r_dx12Sharpen 0.30
set r_dx12Fxaa 0
set r_dx12AlphaToCoverage 1
set r_dx12Dlss 0
set r_dx12BloomThreshold 0.75
set r_dx12Taa 0
set r_dx12AutoExposure 0
set r_dx12Grade 0
set r_dx12Materials 0
set r_dx12Specular 0
set r_dx12Probes 0
set r_dx12Reflex 0
set r_dx12FrameGen 0
set r_dx12Shadows 0
set r_dx12ContactShadows 0
set r_dx12Volumetrics 0
set r_dynamiclight 1
set r_flares 1
set r_detailtextures 1
seta cg_impactEffects 1
seta ui_platinumPreset 1
```

### Ultra (platinum-preset-2.cfg)

```
set r_picmip 0
set r_textureMode GL_LINEAR_MIPMAP_LINEAR
set r_ext_texture_filter_anisotropic 16
set r_ext_max_anisotropy 16
set r_ext_multisample 0
set r_dx12Msaa 0
set r_dx12Hdr 1
set r_dx12Ssao 3
set r_dx12Tonemap 3
set r_dx12Bloom 1
set r_dx12BloomIntensity 0.20
set r_dx12Sharpen 0.30
set r_dx12Fxaa 0
set r_dx12AlphaToCoverage 1
set r_dx12Dlss 1
set r_dx12BloomThreshold 0.80
set r_dx12Taa 1
set r_dx12AutoExposure 1
set r_dx12Grade 1
set r_dx12Materials 1
set r_dx12Specular 1
set r_dx12Probes 1
set r_dx12Reflex 1
set r_dx12FrameGen 0
set r_dx12Shadows 2
set r_dx12ContactShadows 1
set r_dx12Volumetrics 0
set r_dynamiclight 1
set r_flares 1
set r_detailtextures 1
seta cg_impactEffects 1
seta ui_platinumPreset 2
```
