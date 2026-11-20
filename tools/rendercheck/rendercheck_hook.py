#!/usr/bin/env python3
"""Adds the render check hook to a composed source tree (client only; never in a release build).

  rendercheck_hook.py <source tree>

cl_renderCheck <fps> (set on the command line) makes demo playback deterministic: from the first frame of the
demo every client frame advances exactly 1000/fps ms of demo time, whatever the real frame time. While the demo
is in game, every cl_renderCheckEvery-th frame is saved as screenshots/rc-<frame>.png, and after
cl_renderCheckFrames frames, or when the demo ends, the client quits. So two builds that render alike write identical images.
Inserted by anchor (like feeltrace.py), so it applies on top of engine kits. Line endings are preserved.
"""
import re, sys
from pathlib import Path

path = Path(sys.argv[1]) / 'reference/etlegacy/src/client/cl_main.c'
text = path.read_bytes().decode('utf-8')
nl = '\r\n' if '\r\n' in text else '\n'
if 'cl_renderCheck' in text:
    sys.exit('rendercheck_hook.py: hook already present in ' + str(path))
anchor = re.search(r'static void CL_FrameHandleVideo\(int \*msec\)\s*\{\s*\n', text)
if not anchor:
    sys.exit('rendercheck_hook.py: CL_FrameHandleVideo not found in ' + str(path))
hook = '''	{	// render check (tools/rendercheck): fixed demo time step, numbered screenshots, quit at the end
		static cvar_t *rcFps, *rcEvery, *rcFrames;
		static int    rcFrame;

		if (!rcFps)
		{
			rcFps    = Cvar_Get("cl_renderCheck", "0", CVAR_INIT);
			rcEvery  = Cvar_Get("cl_renderCheckEvery", "10", CVAR_INIT);
			rcFrames = Cvar_Get("cl_renderCheckFrames", "300", CVAR_INIT);
		}
		if (rcFps->integer > 0 && clc.demo.playing)
		{
			*msec = 1000 / rcFps->integer;
			if (cls.state == CA_ACTIVE)
			{
				rcFrame++;
				if (rcFrame % (rcEvery->integer > 0 ? rcEvery->integer : 1) == 0)
				{
					Cbuf_ExecuteText(EXEC_NOW, va("screenshot rc-%05d\\n", rcFrame));
				}
				if (rcFrame >= rcFrames->integer)
				{
					Cvar_Set("cl_renderCheck", "0");
					Cbuf_AddText("quit\\n");
				}
			}
			return;
		}
		if (rcFps->integer > 0 && rcFrame > 0)
		{
			Cvar_Set("cl_renderCheck", "0");   // the demo ended: done
			Cbuf_AddText("quit\\n");
		}
	}
'''.replace('\n', nl)
text = text[:anchor.end()] + hook + text[anchor.end():]
path.write_bytes(text.encode('utf-8'))
print('rendercheck_hook.py: hook added to', path)
