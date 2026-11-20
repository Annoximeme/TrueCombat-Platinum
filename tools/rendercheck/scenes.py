#!/usr/bin/env python3
"""Camera spots for the render check, from the map itself.

  scenes.py <game data folder> <map> <count> > scenes.cfg

Reads the map's spawn points (info_player_deathmatch, team spawns, intermission) from its BSP inside the pk3s and
picks <count> of them spread over the map (farthest point first). Writes a console script for the recording
client: start a demo, put the player on each spot for a while (tcp_place, devmap only), stop, quit.
"""
import re, struct, sys, zipfile
from pathlib import Path

data, mapname, count = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
FRAMES_PER_SPOT = 90   # recording client frames on each spot
bsp = None
for pk3 in sorted((data/'etmain').glob('*.pk3')) + sorted((data/'tcetest').glob('*.pk3')):   # later paks win, as in the game
    with zipfile.ZipFile(pk3) as z:
        for n in z.namelist():
            if n.lower() == f'maps/{mapname.lower()}.bsp':
                bsp = z.read(n)
if bsp is None:
    sys.exit(f'scenes.py: maps/{mapname}.bsp not found under {data}')
offset, length = struct.unpack_from('<ii', bsp, 8)   # lump 0: entities
ents = bsp[offset:offset + length].decode('latin1')
spots = []
for block in re.findall(r'\{([^{}]*)\}', ents):
    kv = dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', block))
    if kv.get('classname') in ('info_player_deathmatch', 'team_CTF_redspawn', 'team_CTF_bluespawn', 'info_player_intermission') and 'origin' in kv:
        x, y, z = (float(v) for v in kv['origin'].split()[:3])
        spots.append((x, y, z, float(kv.get('angle', kv.get('angles', '0 0 0').split()[1] if 'angles' in kv else 0))))
if not spots:
    sys.exit('scenes.py: no spawn points in the map')
chosen = [min(spots)]   # deterministic start: lowest x
while len(chosen) < min(count, len(spots)):
    far = max((s for s in spots if s not in chosen), key=lambda s: min((s[0]-c[0])**2 + (s[1]-c[1])**2 + (s[2]-c[2])**2 for c in chosen))
    chosen.append(far)
print('wait 200')
print('record rc')
for x, y, z, yaw in chosen:
    print(f'wait 5; tcp_place 0 at {x:.0f} {y:.0f} {z + 24:.0f} {yaw:.0f}; wait {FRAMES_PER_SPOT}')
print('stoprecord')
print('wait 10')
print('quit')
