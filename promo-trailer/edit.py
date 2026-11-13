"""Assemble the TrueCombat: Platinum trailer from an edit list (EDL).

Usage: python edit.py EDL.json OUT.mp4 [--clips DIR] [--music FILE] [--vertical] [--draft]

EDL format (JSON):
{
  "music": "buckley_venom.mp3",        # relative to --music dir or absolute; optional
  "music_start": 0.0,                   # seconds into the track where the edit starts
  "game_audio_db": -16,                 # level of clip audio under the music (null = mute)
  "fade_out": 0.6,                      # video+audio fade at the very end
  "segments": [
    {"brand": "intro", "dur": 4.5},                           # branding.intro_frame
    {"clip": "delta_plant_b.mp4", "in": 2.0, "dur": 1.8,
     "card": {"text": "ONE LIFE", "sub": "PER ROUND", "at": 0.2, "dur": 2.2},
     "speed": 1.0, "flash": false},
    {"black": 0.3},
    {"brand": "end", "dur": 7.0}
  ]
}
Clips are scaled to 1920x1080 (16:9) or centre-cropped to 1080x1920 with --vertical.
Requires ffmpeg on PATH (or FFMPEG env var) and branding.py next to this file.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import branding as B  # noqa: E402

FF = os.environ.get("FFMPEG", "ffmpeg")
FPS = B.FPS


def read_frames(path, t_in, dur, speed, w, h, vertical):
    """Yield PIL RGB frames of size (w,h) from a clip segment at 60 fps."""
    n = int(round(dur * FPS))
    if vertical:
        vf = f"setpts=PTS/{speed},fps={FPS},scale=-2:{h}:flags=lanczos,crop={w}:{h}"
    else:
        vf = f"setpts=PTS/{speed},fps={FPS},scale={w}:{h}:flags=lanczos"
    cmd = [FF, "-loglevel", "error", "-ss", f"{t_in:.3f}", "-i", str(path), "-t", f"{dur * speed + 0.5:.3f}",
           "-vf", vf, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = w * h * 3
    last = None
    for _ in range(n):
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        last = Image.frombuffer("RGB", (w, h), buf, "raw", "RGB", 0, 1)
        yield last
    p.stdout.close()
    p.wait()


def brand_frames(kind, dur, w, h, vertical):
    fn = B.intro_frame if kind == "intro" else B.end_frame
    for i in range(int(round(dur * FPS))):
        im = fn(i).convert("RGB")
        if vertical:  # fit the 16:9 card into the 9:16 frame, centred on black
            s = w / im.width
            im2 = Image.new("RGB", (w, h))
            r = im.resize((w, int(im.height * s)), Image.LANCZOS)
            im2.paste(r, (0, (h - r.height) // 2))
            im = im2
        yield im


def card_overlay(im, t, card, vertical):
    if not card:
        return im
    ct = t - card.get("at", 0.0)
    if ct < 0 or ct > card.get("dur", 2.2):
        return im
    if vertical:  # draw on a 1920x1080 canvas centred, then paste the middle back
        canvas = Image.new("RGB", (B.W, B.H))
        x0 = (B.W - im.width) // 2
        y0 = (im.height - B.H) // 2
        canvas.paste(im.crop((0, y0, im.width, y0 + B.H)), (x0, 0))
        out = B.title_card(canvas, ct, card["text"], card.get("sub"), card.get("dur", 2.2))
        im = im.copy()
        im.paste(out.crop((x0, 0, x0 + im.width, B.H)), (0, y0))
        return im
    return B.title_card(im, ct, card["text"], card.get("sub"), card.get("dur", 2.2))


def flash(im, t, seg):
    if not seg.get("flash"):
        return im
    a = max(0.0, 1 - t / 0.12) * 0.6
    if a <= 0:
        return im
    arr = np.asarray(im).astype(np.float32)
    return Image.fromarray(np.clip(arr + 255 * a, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("out")
    ap.add_argument("--clips", default=".")
    ap.add_argument("--music", default=str(HERE))
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--draft", action="store_true", help="fast preview encode")
    a = ap.parse_args()
    edl = json.loads(Path(a.edl).read_text())
    w, h = (1080, 1920) if a.vertical else (B.W, B.H)
    clips = Path(a.clips)
    segs = edl["segments"]
    total = sum(s.get("dur", s.get("black", 0)) for s in segs)
    nframes_total = int(round(total * FPS))
    fade = edl.get("fade_out", 0.6)

    vtmp = Path(a.out).with_suffix(".video.mp4")
    enc = [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast" if a.draft else "slow",
           "-crf", "23" if a.draft else "16", "-pix_fmt", "yuv420p", str(vtmp)]
    p = subprocess.Popen(enc, stdin=subprocess.PIPE)
    fi = 0
    audio_parts = []  # (clip path, in, dur*speed, speed, start time in edit)
    t_edit = 0.0
    for seg in segs:
        if "black" in seg:
            n = int(round(seg["black"] * FPS))
            blk = Image.new("RGB", (w, h)).tobytes()
            for _ in range(n):
                p.stdin.write(blk)
            fi += n
            t_edit += seg["black"]
            continue
        dur = seg["dur"]
        n = int(round(dur * FPS))
        if "brand" in seg:
            src = brand_frames(seg["brand"], dur, w, h, a.vertical)
        else:
            path = clips / seg["clip"]
            sp = seg.get("speed", 1.0)
            src = read_frames(path, seg.get("in", 0.0), dur, sp, w, h, a.vertical)
            if sp == 1.0 and not seg.get("mute"):
                audio_parts.append((path, seg.get("in", 0.0), dur, t_edit))
        k = 0
        last = Image.new("RGB", (w, h))
        for im in src:
            last = im
            t = k / FPS
            im = flash(card_overlay(im, t, seg.get("card"), a.vertical), t, seg)
            g = (nframes_total - fi) / (fade * FPS)
            if g < 1:
                im = Image.fromarray((np.asarray(im).astype(np.float32) * max(g, 0)).astype(np.uint8))
            p.stdin.write(im.convert("RGB").tobytes())
            k += 1
            fi += 1
        while k < n:  # pad short clips with their last frame
            p.stdin.write(last.tobytes())
            k += 1
            fi += 1
        t_edit += dur
    p.stdin.close()
    p.wait()

    # audio: music bed + ducked clip audio
    inputs, filters, mix = [], [], []
    music = edl.get("music")
    if music:
        mp = Path(music) if Path(music).is_absolute() else Path(a.music) / music
        inputs += ["-ss", str(edl.get("music_start", 0.0)), "-i", str(mp)]
        filters.append(f"[1:a]atrim=0:{total:.3f},afade=t=out:st={total - fade:.3f}:d={fade}[m]")
        mix.append("[m]")
    gdb = edl.get("game_audio_db", -16)
    if gdb is not None:
        for j, (path, tin, dur, at) in enumerate(audio_parts):
            idx = 1 + inputs.count("-i")
            inputs += ["-ss", f"{tin:.3f}", "-t", f"{dur:.3f}", "-i", str(path)]
            d = int(at * 1000)
            filters.append(f"[{idx}:a]aresample=48000,afade=t=in:d=0.04,afade=t=out:st={max(dur - 0.06, 0):.3f}:d=0.06,"
                           f"volume={gdb}dB,adelay={d}|{d}[g{j}]")
            mix.append(f"[g{j}]")
    if mix:
        filters.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0,alimiter=limit=0.95[aout]")
        cmd = [FF, "-y", "-loglevel", "error", "-i", str(vtmp)] + inputs + [
            "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k", "-t", f"{total:.3f}", "-movflags", "+faststart", a.out]
        r = subprocess.run(cmd)
        if r.returncode == 0:
            vtmp.unlink()
    else:
        vtmp.replace(a.out)
    print("done", a.out, f"{total:.2f}s")


if __name__ == "__main__":
    main()
