# Trailer tools (temporary branch)

- `branding.py OUTDIR`: renders intro_ident.mp4 and end_card.mp4 (1920x1080, 60 fps).
- `edit.py EDL.json OUT.mp4 --clips DIR --music DIR [--vertical] [--draft]`: assembles the trailer from an edit list.

Needs Python 3 with numpy and Pillow, and ffmpeg on PATH (or the FFMPEG environment variable).
