#!/usr/bin/env python3
# GPL-3.0-or-later. TrueCombat: Platinum 0.40.0 HD textures (engine visuals upgrade 1): height maps.
#
# Builds the optional HD pack's <texture>_rmaoh.dds maps: the roughness/metal/occlusion map of zzz_hd_materials.pk3
# with a height map in its alpha (1 = top), BC7 compressed with a full mip chain. The DX12 renderer (patch 11) loads
# <texture>_rmaoh.dds before <texture>_rmao.jpg and then uses the height for parallax on every world surface that has
# one, instead of the 0.39 guess from the albedo's brightness on brick and stone only.
#
# The height comes from the pack's own normal map (<texture>_n.jpg, tangent space, green up), integrated over the whole
# texture with an FFT (Frankot-Chellappa; textures tile, so the periodic solve is exact at the seams), then stretched
# to 0..1 between its 1st and 99th percentiles. No new art and no AI model: the shape is the one the normal map already
# shows, so the parallax agrees with the lighting.
#
# usage:
#   py build_hd2.py --materials <zzz_hd_materials.pk3> --out <dir> [--encoder hd2_bc7.exe] [--jobs 8] [--green-down]
#   py build_hd2.py --selftest --encoder <hd2_bc7>       (round trip on synthetic maps; no packs needed)
#   py build_hd2.py --from-albedo <pk3> [<pk3> ...] --out <dir>   (dry run: normals made from albedo; tests only)
# out: <dir>/zzz_hd2_heights.pk3 (stored), manifest.json, heights-sheet.jpg (contact sheet), report.md
import argparse, hashlib, io, json, math, os, re, struct, subprocess, sys, tempfile, zipfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
# No parallax for these: alpha-tested, see-through or not solid (the renderer skips them anyway: alphaTest, sky), and
# printed flat art (signs, posters, labels), where depth would only follow the print.
SKIP = re.compile(r'glass|window|water|liquid|leaf|leaves|foliage|tree|grass|bush|plant|ivy|sky|fence|net|wire|chain|'
                  r'decal|effect|fx/|flare|light|lamp|bulb|neon|sprite|gfx/|fog|cloud|smoke|blood|hair|'
                  r'sign|poster|logo|graffiti|label|calendar|pinup|letter|number|screen|monitor|map_', re.I)


FULL_RELIEF = 0.04  # relief of 4% of the texture width counts as full parallax depth


def png_like(data):
    return np.asarray(Image.open(io.BytesIO(data)).convert('RGB'), dtype=np.float32)


HIGHPASS = 0.0  # cycles per texture; 0.39.0 kit: 8 (keeps mortar and brick edges, drops the large blotches of the generated normal maps)


def height_from_normal(n_rgb, green_down=False):
    """n_rgb: HxWx3 float 0..255 tangent-space normal map. Returns HxW height in 0..1 (1 = top)."""
    n = n_rgb / 127.5 - 1.0
    nx, ny = n[..., 0], n[..., 1]
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 0.04, 1.0))
    gx = -nx / nz                      # dh/dx, x to the right
    gy = (-ny if green_down else ny) / nz  # dh/drow: green up means +y points to the top row, rows go down
    h, w = gx.shape
    wx = 2.0 * np.pi * np.fft.fftfreq(w)[None, :]
    wy = 2.0 * np.pi * np.fft.fftfreq(h)[:, None]
    den = wx * wx + wy * wy
    den[0, 0] = 1.0
    hf = (-1j * wx * np.fft.fft2(gx) - 1j * wy * np.fft.fft2(gy)) / den
    hf[0, 0] = 0.0
    if HIGHPASS > 0:
        cyc = np.sqrt((np.fft.fftfreq(w)[None, :] * w) ** 2 + (np.fft.fftfreq(h)[:, None] * h) ** 2)
        hf *= 1.0 - np.exp(-(cyc / HIGHPASS) ** 2)
    height = np.real(np.fft.ifft2(hf))
    lo, hi = np.percentile(height, 1.0), np.percentile(height, 99.0)
    # The relief is in texels. Full depth (0..1) needs at least FULL_RELIEF of the texture's width; a flatter texture
    # (a plank, a painted sign) keeps its small relief near the top instead of being stretched into deep noise.
    span = max(hi - lo, FULL_RELIEF * w, 1e-6)
    return np.clip(1.0 - (hi - height) / span, 0.0, 1.0)


def normal_from_height(height):
    """Test helper, same convention as height_from_normal (green up, central differences, periodic)."""
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    drow = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    n = np.stack([-dx, drow, np.ones_like(dx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n * 0.5 + 0.5) * 255.0


def box_resize(a, w, h):
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((w, h), Image.BOX), dtype=np.float32)


def pow2(v):
    return v >= 4 and (v & (v - 1)) == 0


def encode(encoder, rgba, out_path):
    h, w = rgba.shape[:2]
    with tempfile.NamedTemporaryFile(suffix='.rgba', delete=False) as f:
        f.write(np.clip(rgba + 0.5, 0, 255).astype(np.uint8).tobytes())
        raw = f.name
    try:
        subprocess.run([encoder, raw, str(w), str(h), out_path], check=True, capture_output=True)
    finally:
        os.unlink(raw)


# ---- BC7 mode 6 decoder (verification only) ----
W4 = [0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64]
W2 = [0, 21, 43, 64]


def decode_top(dds):
    assert dds[:4] == b'DDS ' and dds[84:88] == b'DX10' and struct.unpack_from('<I', dds, 128)[0] == 98
    h, w = struct.unpack_from('<II', dds, 12)
    out = np.zeros((h, w, 4), np.float32)
    pos = 148
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            v = int.from_bytes(dds[pos:pos + 16], 'little')
            pos += 16
            bit = 0

            def take(n):
                nonlocal bit
                r = (v >> bit) & ((1 << n) - 1)
                bit += n
                return r
            if v & 0x7F == 0x40:  # mode 6
                bit = 7
                e = [[0] * 4, [0] * 4]
                for c in range(4):
                    e[0][c] = take(7)
                    e[1][c] = take(7)
                p0, p1 = take(1), take(1)
                e0 = [x * 2 + p0 for x in e[0]]
                e1 = [x * 2 + p1 for x in e[1]]
                idx = [take(3)] + [take(4) for _ in range(15)]
                for i in range(16):
                    k = W4[idx[i]]
                    out[by + i // 4, bx + i % 4] = [((64 - k) * e0[c] + k * e1[c] + 32) >> 6 for c in range(4)]
            elif v & 0x3F == 0x20:  # mode 5
                bit = 6
                assert take(2) == 0, 'rotation'
                c0, c1 = [0] * 3, [0] * 3
                for c in range(3):
                    c0[c], c1[c] = take(7), take(7)
                c0 = [(q << 1) | (q >> 6) for q in c0]
                c1 = [(q << 1) | (q >> 6) for q in c1]
                a0, a1 = take(8), take(8)
                ci = [take(1)] + [take(2) for _ in range(15)]
                ai = [take(1)] + [take(2) for _ in range(15)]
                for i in range(16):
                    k, ka = W2[ci[i]], W2[ai[i]]
                    out[by + i // 4, bx + i % 4] = [((64 - k) * c0[c] + k * c1[c] + 32) >> 6 for c in range(3)] + \
                        [((64 - ka) * a0 + ka * a1 + 32) >> 6]
            else:
                raise AssertionError('unexpected BC7 mode')
    return out


def build_one(args):
    name, rmao_bytes, n_bytes, encoder, green_down, tmpdir, relief = args
    global FULL_RELIEF, HIGHPASS
    FULL_RELIEF, HIGHPASS = relief  # worker processes start with the default
    rmao = png_like(rmao_bytes)
    nrm = png_like(n_bytes)
    rh, rw = rmao.shape[:2]
    if not (pow2(rw) and pow2(rh)):
        return name, None, 'rmao not a power of two'
    height = height_from_normal(nrm, green_down) * 255.0
    if height.shape != (rh, rw):
        height = box_resize(height, rw, rh)
    rgba = np.dstack([rmao, height])
    out = os.path.join(tmpdir, hashlib.sha1(name.encode()).hexdigest() + '.dds')
    encode(encoder, rgba, out)
    return name, out, None


def contact_sheet(items, path, tile=128, cols=12):
    if not items:
        return
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new('L', (cols * tile, rows * tile), 0)
    for i, a in enumerate(items):
        sheet.paste(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((tile, tile)), ((i % cols) * tile, (i // cols) * tile))
    sheet.save(path, quality=90)


def selftest(encoder):
    rng = np.random.default_rng(7)
    # bricks: raised blocks with mortar joints, plus noise; periodic
    y, x = np.mgrid[0:128, 0:128]
    brick = (((y % 32) > 3) & (((x + (y // 32 % 2) * 32) % 64) > 3)).astype(np.float32)
    k = np.ones((5, 5)) / 25.0
    soft = np.real(np.fft.ifft2(np.fft.fft2(brick) * np.fft.fft2(np.pad(k, ((0, 123), (0, 123))))))
    hgt = soft * 0.8 + rng.normal(0, 0.02, soft.shape)
    nrm = normal_from_height(hgt * 6.0)
    back = height_from_normal(nrm)
    ref = (hgt - np.percentile(hgt, 1)) / (np.percentile(hgt, 99) - np.percentile(hgt, 1))
    corr = float(np.corrcoef(back.ravel(), np.clip(ref, 0, 1).ravel())[0, 1])
    flipped = float(np.corrcoef(height_from_normal(nrm, True).ravel(), ref.ravel())[0, 1])
    print(f'height round trip: correlation {corr:.3f} (green-down reading: {flipped:.3f})')
    ok = corr > 0.9 and flipped < corr
    # rmao like the pack's: rough concrete (roughness varies with its own grain), no metal, occlusion in the joints
    grain = box_resize(rng.uniform(0, 255, (128, 128, 1)).repeat(3, -1), 64, 64)[..., 0]
    rmao = np.dstack([150 + (grain - 128) * 0.5, np.zeros((64, 64)), box_resize(brick[..., None].repeat(3, -1) * 255, 64, 64)[..., 0] * 0.2 + 100])
    rgba = np.dstack([rmao, box_resize(back[..., None].repeat(3, -1) * 255.0, 64, 64)[..., 0]])
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, 't.dds')
        encode(encoder, rgba, out)
        dds = open(out, 'rb').read()
        levels = struct.unpack_from('<I', dds, 28)[0]
        dec = decode_top(dds)
        err = float(np.sqrt(np.mean((dec - np.clip(rgba + 0.5, 0, 255).astype(np.uint8)) ** 2)))
        err_a = float(np.sqrt(np.mean((dec[..., 3] - np.clip(rgba[..., 3] + 0.5, 0, 255).astype(np.uint8)) ** 2)))
        expect = 148 + sum(max(1, (64 >> l) // 4) ** 2 * 16 for l in range(levels))
        print(f'BC7: {levels} levels, {len(dds)} bytes (expected {expect}), RMS error {err:.2f}/255, height (alpha) {err_a:.2f}/255')
        ok = ok and len(dds) == expect and levels == 5 and err_a < 4.0 and err < 6.0
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def main():
    global FULL_RELIEF
    ap = argparse.ArgumentParser()
    ap.add_argument('--materials')
    ap.add_argument('--from-albedo', nargs='+')
    ap.add_argument('--out')
    ap.add_argument('--encoder', default=os.path.join(HERE, 'hd2_bc7.exe' if os.name == 'nt' else 'hd2_bc7'))
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument('--green-down', action='store_true', help='normal maps with green pointing down (DirectX style)')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--full-relief', type=float, default=FULL_RELIEF, help='relief (share of the texture width) that counts as full depth')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--highpass', type=float, default=0.0, help='drop relief coarser than this many cycles per texture (0 = keep all)')
    ap.add_argument('--only', help='text file of texture base names (textures/x/y, one per line): build these only')
    ap.add_argument('--pak-name', default='zzz_hd2_heights.pk3')
    a = ap.parse_args()
    FULL_RELIEF = a.full_relief
    if a.selftest:
        sys.exit(0 if selftest(a.encoder) else 1)
    if not a.out or not (a.materials or a.from_albedo):
        ap.error('--out and --materials (or --from-albedo) are needed')
    os.makedirs(a.out, exist_ok=True)
    jobs, skipped = [], []
    tmpdir = tempfile.mkdtemp(prefix='hd2-')
    only = None
    if a.only:
        only = {l.strip().lower() for l in open(a.only) if l.strip() and not l.startswith('#')}
    if a.materials:
        z = zipfile.ZipFile(a.materials)
        names = {n.lower(): n for n in z.namelist()}
        for low, real in sorted(names.items()):
            if not low.endswith('_rmao.jpg') or not low.startswith('textures/'):
                continue
            base = real[:-len('_rmao.jpg')]
            if only is not None and base.lower() not in only:
                continue
            if only is None and SKIP.search(base[len('textures/'):]):
                skipped.append((base, 'class'))
                continue
            n = names.get((base + '_n.jpg').lower())
            if not n:
                skipped.append((base, 'no normal map'))
                continue
            jobs.append((base, z.read(real), z.read(n), a.encoder, a.green_down, tmpdir, (a.full_relief, a.highpass)))
    else:  # dry run on stock albedo: a normal map from the luma, an rmao of mid roughness
        for pk in a.from_albedo:
            z = zipfile.ZipFile(pk)
            for real in sorted(z.namelist()):
                low = real.lower()
                if not low.startswith('textures/') or not low.endswith(('.jpg', '.tga')) or SKIP.search(low[9:]):
                    continue
                try:
                    alb = np.asarray(Image.open(io.BytesIO(z.read(real))).convert('L'), dtype=np.float32) / 255.0
                except Exception:
                    continue
                h, w = alb.shape
                if not (pow2(w) and pow2(h)) or w < 64 or h < 64:
                    continue
                nrm = normal_from_height(alb * 4.0)
                buf_n, buf_r = io.BytesIO(), io.BytesIO()
                Image.fromarray(nrm.astype(np.uint8)).save(buf_n, 'PNG')
                Image.new('RGB', (w // 2, h // 2), (160, 0, 128)).save(buf_r, 'PNG')
                jobs.append((os.path.splitext(real)[0], buf_r.getvalue(), buf_n.getvalue(), a.encoder, a.green_down, tmpdir, (a.full_relief, a.highpass)))
    if a.limit:
        jobs = jobs[:a.limit]
    print(f'{len(jobs)} textures to build, {len(skipped)} skipped', flush=True)
    results, sheet, manifest = [], [], {'textures': {}, 'skipped': dict(skipped), 'green_down': a.green_down, 'full_relief': a.full_relief, 'highpass': a.highpass}
    with ProcessPoolExecutor(a.jobs) as pool:
        for i, (name, path, err) in enumerate(pool.map(build_one, jobs, chunksize=4)):
            if err:
                manifest['skipped'][name] = err
                continue
            results.append((name, path))
            if (i + 1) % 50 == 0:
                print(f'  {i + 1}/{len(jobs)}', flush=True)
    pak = os.path.join(a.out, a.pak_name)
    with zipfile.ZipFile(pak, 'w', zipfile.ZIP_STORED) as out:
        for name, path in results:
            data = open(path, 'rb').read()
            out.writestr(name + '_rmaoh.dds', data)
            manifest['textures'][name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            if len(sheet) < 240:
                sheet.append(decode_top(data)[..., 3] if len(data) < 400000 else None)
            os.unlink(path)
    sheet = [s for s in sheet if s is not None]
    contact_sheet(sheet, os.path.join(a.out, 'heights-sheet.jpg'))
    digest = hashlib.sha256(open(pak, 'rb').read()).hexdigest()
    manifest['pak'] = {'name': os.path.basename(pak), 'bytes': os.path.getsize(pak), 'sha256': digest}
    json.dump(manifest, open(os.path.join(a.out, 'manifest.json'), 'w'), indent=1, sort_keys=True)
    with open(os.path.join(a.out, 'report.md'), 'w') as r:
        r.write(f'# HD height maps\n\n- Textures: {len(results)}\n- Skipped: {len(manifest["skipped"])}\n'
                f'- Pak: {os.path.basename(pak)}, {os.path.getsize(pak) / 1048576:.1f} MiB, sha256 {digest}\n'
                f'- Normal maps read as green {"down" if a.green_down else "up"}.\n'
                '- Check heights-sheet.jpg: mortar joints, cracks and gaps must be DARK (low). If they are bright, rerun with '
                '--green-down.\n')
    if only is not None:
        missing = sorted(only - {n.lower() for n, _ in results})
        manifest['missing'] = missing
        json.dump(manifest, open(os.path.join(a.out, 'manifest.json'), 'w'), indent=1, sort_keys=True)
        print(f'{len(missing)} listed textures have no material maps in the pack: {missing}')
    print(f'done: {len(results)} maps, {os.path.getsize(pak) / 1048576:.1f} MiB -> {pak}')


if __name__ == '__main__':
    main()
