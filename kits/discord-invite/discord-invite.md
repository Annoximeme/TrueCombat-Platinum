# discord-invite (0.39.2)

Owner thread: Replace the expired Discord invite link.
Gianni 18 Nov 19:18Z: "Edit the Discord link everywhere. Apparently it's expired. This is the new one.
https://discord.gg/7Dg4yhhvGF"

Old invite discord.gg/8kcHdg2Hch is dead. Every game-side copy now points to https://discord.gg/7Dg4yhhvGF.
The 0.39.1 build is left alone; this goes into 0.39.2.

GATE PASSED 2026-11-18 ~20:33Z on the published 0.39.1 source zip (sha256 65f45c70; kit checksum 1d05921746caf16e; EAC on, probes run, Linux server, bots soak all pass). Patch 01 sha256 caba6c2c, ui-patches/02 sha256 2cb470bd. (Earlier gate on 0.39.0, c95f8716, superseded.)

## patches/01-discord-invite-launcher-0392.patch (gated, see SUMMARY.md)

Base: published 0.39.1 source zip (integ039/base, sha256 65f45c70...). Three one-line string changes plus the launcher bump:

- release_src/platinum_main.h: launcher Play page news card "Find a match on Discord" (fallback when the
  website feed is unreachable; the live feed already carries the new link since website PR #149).
- release_src/platinum_setup.c: installer HelpLink in Apps & features.
- release_src/platinum_shortcut.h: HelpLink rewritten by the shortcut care pass, so existing installs get the
  new link on the next launcher start.

The launcher's link allowlist (https://discord.gg/) is unchanged.
- release_src/platinum_launcher_version.h: launcher 3.0.3 -> 3.0.4 (launcher code changed).

## ui-patches/02-discord-invite-ui-0392.patch (PC UI pak rebuild, like voice-0391 ui-patches)

Not in the source zip: the UI menus are generated on the PC. Applies with `git apply` on the PC source
(checked against rel039-rebuild 424080c):

- analysis_scripts/platinum_errors.py: the "Report on Discord" button on the friendly error screens.
- release_src/platinum_ui/ui/popup_errormessage.menu and popup_errormessage_pb.menu: the generated output.

Rebuild the UI pak (build_platinum_ui.py / platinum_quick.py) and keep it in acReleasePaks as usual.

## PC look

Error screen (e.g. connect to a dead address) > "Report on Discord" opens discord.gg/7Dg4yhhvGF.
Launcher > Play page community card opens the same. Apps & features > TrueCombat: Platinum > support link.

## Heads-up for 0.40

The 0.40 UI kits (ui-overhaul k4, k7, k8, k15, k26, k27, k29, k31, k32, first-hour k4-bootcamp-delta) carry
their own copies of main.menu, the error menus, platinum_errors.py and platinum_front.py with the OLD link.
They were left untouched so their gate checksums stay valid; the UI thread was told to switch them before the
0.40 integration.
