# Kit free-aim (0.39.3): free aim with a deadzone

Thread "Add free aim to the game", 2026-11-18. Gianni 23:42Z: "Let's get the free aim feature in as well." / "Get this in asap as well."
Kit folder: integ0393/kits/free-aim/ (patches/01-free-aim-0393.patch, ui-patches/02-free-aim-ui-0393.patch). Gate summary: integ0393/kits/free-aim-SUMMARY.md.

Base: TrueCombat-Platinum-0.39.1-sandbox38-source.zip (integ039/base). Also checked: applies cleanly on top of every 0.39.2 kit
(tracers, grip-hands, chlite-shutters, stairs-curbs, discord-invite). Re-gate on the 0.39.2 source once it is published.

## What it does
`cg_freeAim` already existed (0.38.0 aim-feel kit, TC:E 0.49b free aim) but was off, hidden, and only worked while aimed
down the sights. This kit turns it into a real option with two new modes:

| cg_freeAim | Behaviour |
|---|---|
| 0 Off (default) | as before |
| 2 Deadzone | at the hip the mouse moves the weapon inside a box of 2.5 deg up/down, 4 deg left/right; past the edge the view turns |
| 3 Wide deadzone | same, 4 deg up/down, 7 deg left/right |
| 1 Classic (aim only) | the TC:E 0.49b aimed free aim, unchanged |

Aiming down the sights in the deadzone modes brings the sights to the weapon: the offset eases back to the centre
(90 % in ~100 ms) while the view turns by the same amount, so the weapon never jumps off target. While aimed the mouse turns the view 1:1.
Shots leave along the weapon (view + offset), server-authoritative; the client predicts it (no added input lag), and the
view model points where the shot goes, at the hip and aimed.

## Files
- tcp_aim.c / tcp_native_combat.h: TCP_FreeAimFrame(mode, msec, ...) with the deadzone in whole angle units (server and
  client replay match exactly, no drift); TCP_WeaponAngles adds the offsets at the hip in deadzone modes; tcp_aim_state.free_mode.
- tcp_lagpredict.c/.h: mode 0-3 rides the snapshot (new flag bit TCP_LAG_FREEAIM2 0x800, free).
- tcp_lagclient.h: predicted offsets written into the predicted playerState for the view model (the snapshot copy is a round trip late).
- tcp_viewfx.h: gun turns by the full offsets in deadzone modes.
- tcp_game.c: userinfo cg_freeAim 0-3 (bots stay 0).
- tests/freeaim_deadzone_probe.c (new, added to build_candidate.py probes), tests/combat_feel_probe.c (new signature).
- ui-patches/02 (PC UI pak rebuild, generator only, like discord-invite): Options > MOUSE & VIEW gets "Free aim: Off / Deadzone /
  Wide deadzone / Classic (aim only)" under "Aim speed" (y 372), and RESET MOUSE & VIEW sets cg_freeAim 0. Checked against rel0392.

## Evidence (cloud)
- freeaim_deadzone_probe PASS: 320,000 random commands at 1/2/4/8 ms frames, weapon direction == mouse input exactly, view still
  while inside the box; aimed ease 90 % at 100/98/100/104 ms (frame-rate independent); pack/unpack + replay == server for modes 0-3;
  hip M4 mean shot moves by exactly the offset.
- combat_feel_probe PASS (TC:E classic mode unchanged against the recovered reference).

## PC look (in the 0.39.3 candidate)
Options > Mouse & View > Free aim = Deadzone. With bots on any map: small mouse moves swing the gun, the view stays; push past the
edge and the view turns; hip-fire lands where the barrel points; right mouse brings the sights in smoothly with no snap; try
Wide deadzone and Classic; DX12 and OpenGL. Third person: other players' gun model still follows their view (offset not shown), cosmetic.

## Patch notes line
- New option: Free aim (Options > Mouse & View). Your weapon moves within a small deadzone before the view turns, the way a real
  rifle swings ahead of your head. Aiming down the sights brings the sights to the weapon. Off by default.
