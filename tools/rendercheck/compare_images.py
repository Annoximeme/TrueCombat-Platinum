#!/usr/bin/env python3
"""Compares the render check frames of two or three runs and prints one SUMMARY.md table row.

  compare_images.py <shots dir> <base run> <base repeat run> <kit run> <report dir> --row <map> <renderer> [--expect-changes]

<shots dir>/<run>/rc-NNNNN.png per run. The base and its repeat must match (else "not deterministic").
Software rasterizers (Mesa llvmpipe) can round a handful of pixels differently from run to run (seen: 1 to 34
pixels, off by 1 or 2 levels, at the edge of a crate shadow). When the base and its repeat differ by at most
--noise-level levels on at most --noise-share percent of the pixels, those pixels (grown by 2) are marked
unstable: the runs still count as deterministic, and kit differences inside the unstable pixels are not counted.
Kit differences elsewhere that stay within the same noise limits are listed, not counted.
A real change is far bigger: 2 % more ambient light changed 3.5 to 7.7 % of the pixels by up to 10 levels.
Then every kit frame is compared with the base: changed pixels, largest channel difference and PSNR. Each
changed frame gets <report dir>/rc-NNNNN.png: base, kit and the difference (changed pixels in magenta over a
dimmed base). Exit 0 when deterministic and identical (or, with --expect-changes, deterministic); else 1.
"""
import argparse, math, sys
from pathlib import Path
import numpy as np
from PIL import Image

p = argparse.ArgumentParser()
p.add_argument('shots', type=Path); p.add_argument('base'); p.add_argument('repeat'); p.add_argument('kit')
p.add_argument('report', type=Path); p.add_argument('--row', nargs=2, required=True); p.add_argument('--expect-changes', action='store_true')
p.add_argument('--noise-level', type=int, default=2); p.add_argument('--noise-share', type=float, default=0.02)
a = p.parse_args()

def load(run, name):
    f = a.shots/run/name
    return np.asarray(Image.open(f).convert('RGB'), dtype=np.int16) if f.exists() else None

names = sorted(f.name for f in (a.shots/a.base).glob('rc-*.png'))
mapname, renderer = a.row
def grow(mask, by=2):
    out = mask.copy()
    for dy in range(-by, by + 1):
        for dx in range(-by, by + 1):
            out |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return out

def repeat_diff(x, y):
    """None when equal, an unstable-pixel mask when within the noise limits, else 'differs'."""
    if x is None or y is None or x.shape != y.shape:
        return 'differs'
    d = np.abs(x - y); mask = d.max(axis=2) > 0
    if not mask.any():
        return None
    if int(d.max()) <= a.noise_level and 100 * mask.mean() <= a.noise_share:
        return grow(mask)
    return 'differs'

repeat = {n: repeat_diff(load(a.base, n), load(a.repeat, n)) for n in names}
nondet = [n for n in names if isinstance(repeat[n], str)]
noisy = [n for n in names if isinstance(repeat[n], np.ndarray)]
same = 'identical' if not noisy else f'matches ({len(noisy)} frames with rasterizer noise)'
if nondet:
    print(f'| {mapname} | {renderer} | {len(names)} | **differs** ({len(nondet)} frames, first {nondet[0]}) | **FAIL** | not deterministic, check not trustworthy |')
    sys.exit(1)
if a.kit == a.repeat:
    print(f'| {mapname} | {renderer} | {len(names)} | {same} | pass | none (base against itself) |')
    sys.exit(0)
changed, lines, kitnoise = [], [], []
missing = [n for n in names if not (a.shots/a.kit/n).exists()]
extra = sorted(f.name for f in (a.shots/a.kit).glob('rc-*.png') if f.name not in names)
for n in names:
    b, k = load(a.base, n), load(a.kit, n)
    if k is None or b.shape != k.shape:
        continue
    d = np.abs(b - k); mask = d.max(axis=2) > 0
    if isinstance(repeat[n], np.ndarray) and mask.any():
        if not (mask & ~repeat[n]).any():
            kitnoise.append(n); continue
        mask &= ~repeat[n]; d = d * mask[..., None]
    if not mask.any():
        continue
    if int(d.max()) <= a.noise_level and 100 * mask.mean() <= a.noise_share:
        kitnoise.append(n); continue
    mse = float((d.astype(np.float64) ** 2).mean())
    psnr = 10 * math.log10(255 ** 2 / mse) if mse else float('inf')
    changed.append(n)
    lines.append(f'| {n} | {100 * mask.mean():.3f} % | {int(d.max())} | {psnr:.1f} dB |')
    a.report.mkdir(parents=True, exist_ok=True)
    over = (b * 0.35).astype(np.uint8); over[mask] = (255, 0, 255)
    h, w = b.shape[:2]
    sheet = Image.new('RGB', (w * 3, h))
    for i, img in enumerate((b.astype(np.uint8), k.astype(np.uint8), over)):
        sheet.paste(Image.fromarray(img), (i * w, 0))
    sheet.save(a.report/n)
if lines or missing or extra:
    a.report.mkdir(parents=True, exist_ok=True)
    with open(a.report/'report.md', 'w') as f:
        f.write(f'# {mapname} {renderer}: frames that differ from the base\n\nEach picture: base | kit | difference (magenta).\n\n')
        f.write('| Frame | Changed pixels | Largest difference (0-255) | PSNR |\n|---|---|---|---|\n' + '\n'.join(lines) + '\n')
        if missing: f.write(f'\nMissing in the kit run: {", ".join(missing)}\n')
        if extra: f.write(f'\nOnly in the kit run: {", ".join(extra)}\n')
        if kitnoise: f.write(f'\nRasterizer noise only (unstable pixels between the two base runs, or within the noise limits), not counted: {", ".join(kitnoise)}\n')
ok = not changed and not missing and not extra
detail = 'none' if ok else f'{len(changed)} of {len(names)} frames differ' + (f', {len(missing)} missing' if missing else '') + (f', {len(extra)} extra' if extra else '') + f' (report/{a.report.name})'
result = 'pass' if ok else ('changed (expected)' if a.expect_changes else '**FAIL**')
print(f'| {mapname} | {renderer} | {len(names)} | {same} | {result} | {detail} |')
sys.exit(0 if ok or a.expect_changes else 1)
