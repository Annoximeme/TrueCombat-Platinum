# launcher-patchnotes: Launcher 3.0.3 (fix only, for 0.39.1)

Developer: Gianni. Base: the published 0.39.0 source (`integ039/base/TrueCombat-Platinum-0.39.0-sandbox37-FINAL-source.zip`).
One patch, `patches/01-launcher-303-release-cards-story-dip.patch`, launcher only (`release_src/platinum_*.h`). No game,
server or pak change.

## What it fixes

1. **Patch notes cards all read the same.** Every GitHub release name starts "TrueCombat: Platinum", so the three
   Patch notes cards on the Play page all showed `TRUECOMBAT: PLATINUM V...` once cut to the card width. A release
   post is now named by its version: `UPDATE 0.39.0`, `UPDATE 0.38.2`, ... (`ui_release_heading` in
   `platinum_home.h`; the version comes from the release tag URL, as the reader already did). A name in brackets that
   is not the build tag goes on the line under it: `Front Lines · today`. The News page grid uses the same heading; its
   large card, the in-launcher reader and the Play page "What's new" panel read `UPDATE 0.39.0 · FRONT LINES`. A release whose name
   holds no version keeps its name, minus a leading "TrueCombat: Platinum". Translations reuse the existing
   `Update %ls` string (DE, FR, PL, NL).
2. **Ghost text when the featured story changes.** The 600 ms whole-page cross-fade laid the old story's headline and
   copy over the new one half-way through. A story change is now a dip: for the first half the page is drawn without
   the story's words and the old frame fades out over it; for the second half the new words fade in out of that bare
   frame. The words never overlap. Background art still cross-fades. Clicking a story dot does the same in 360 ms.
   Page changes keep the plain 140 ms cross-fade. Reduced motion is unchanged (no fade).
3. Launcher version 3.0.2 -> **3.0.3** (`platinum_launcher_version.h`).

## Files

| file | what |
|---|---|
| patches/01-launcher-303-release-cards-story-dip.patch | the change (`git apply` on the 0.39.0 source) |
| evidence/launcher-303-evidence.zip | 3.0.2 / 3.0.3 renders under Wine (README.txt inside): Play cards, What's new, News grid, reader, and a frame every 50 ms through a story change and a story dot click |
| preview.zip | one pair: the Play page 250 ms into the Devlog -> Ranked change on 3.0.2 (both headlines, three identical cut cards) and 400 ms into it on 3.0.3 (only CLIMB THE LADDER., cards UPDATE 0.39.0 / 0.38.2 / 0.38.1) |
| SUMMARY.md | kit gate result |

Images are stripped (`tools/strip_image_metadata.py`) and scanned clean (`tools/ci/scan_metadata.py`); they stay in zips
because the share stamps loose images.

## Checked on screen (Wine, 1408 x 880, 110 %)

With the four public releases of the feed repository (0.39.0 "Front Lines", 0.38.2, 0.38.1, 0.38.0) and the site feed
as the cached Play feed, 3.0.2 against 3.0.3:

- Play cards: 3.0.2 `TRUECOMBAT: PLATINUM O...` / `TRUECOMBAT: PLATINUM V...` x 2 (the report); 3.0.3 `UPDATE 0.39.0`
  with `Front Lines · today`, `UPDATE 0.38.2 / today`, `UPDATE 0.38.1 / yesterday`.
- News grid, reader and What's new: `UPDATE 0.39.0 · FRONT LINES` (reader was `TRUECOMBAT: PLATINUM 0.39.0 (FRONT...`).
  The first build of this kit named the large News card `UPDATE 0.39.0` only, dropping "Front Lines" that 3.0.2 still
  showed there; it now carries the name (one line in `ui_paint_news_grid`).
- Story change (auto, 600 ms): 3.0.2 shows both headlines from about 100 to 350 ms (the ghost over CLIMB THE LADDER.);
  3.0.3: old words fade out, about 100 ms of bare art, new words fade in; never two headlines. Dot click (360 ms): same.
- Not changed by this kit, seen in both: the What's new panel is translucent, so the Live card's text under it shows
  faintly through its top half.

## Carry into 0.40

Launcher 3.2.0 (UI overhaul K10) is built on 3.0.1 + 3.1.0 and needs the same two changes; the UI overhaul thread
ports them into K10 after this kit is gated.

## PC check

Play page: the three cards read UPDATE 0.39.0 / UPDATE 0.38.2 / UPDATE 0.38.1 with "Front Lines · today" under the
first; let the stories rotate (8 s) and click the dots: no two headlines on screen at once; News page and reader
headings; DE/NL language.
