#!/usr/bin/env python3
"""Puts the feel-check trace hook into a source tree's sv_main.c (feel-check builds only).

    feeltrace.py <source root>

Inserts feeltrace.c before SV_Frame_Ext, a call after the game frame, and the fixed 8 ms frame at the
top of SV_Frame. It finds those spots by their code, not by line numbers, so it still applies when a
kit has changed sv_main.c around them (an engine kit that adds profiler zones, for example).
"""
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
path = root / 'reference/etlegacy/src/server/sv_main.c'
text = path.read_bytes().decode('latin-1')
nl = '\r\n' if '\r\n' in text else '\n'
src = text.replace('\r\n', '\n')
block = (pathlib.Path(__file__).with_name('feeltrace.c').read_text()).rstrip('\n') + '\n\n'

if 'SV_FeelTraceFrame' in src:
    sys.exit('feeltrace.py: sv_main.c already has the trace hook')

m = re.search(r'(/\*\*[^/]*?\*/\s*)?static void SV_Frame_Ext\(', src)
if not m:
    sys.exit('feeltrace.py: SV_Frame_Ext not found')
src = src[:m.start()] + block + src[m.start():]

m = re.search(r'^([ \t]*)VM_Call\(gvm, GAME_RUN_FRAME, sv\.time\);[ \t]*\n', src, re.M)
if not m:
    sys.exit('feeltrace.py: GAME_RUN_FRAME call not found')
src = src[:m.end()] + m.group(1) + 'SV_FeelTraceFrame();\n' + src[m.end():]

m = re.search(r'^([ \t]*)svcls\.realtime \+= msec;', src, re.M)
if not m:
    sys.exit('feeltrace.py: start of SV_Frame not found')
src = src[:m.start()] + m.group(1) + 'msec = SV_FeelTraceMsec(msec);\n' + src[m.start():]

path.write_bytes(src.replace('\n', nl).encode('latin-1'))
print('feeltrace.py: trace hook added to', path)
