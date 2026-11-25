"""TrueCombat: Platinum Engine phase 0 benchmark (Windows, the release PC).

Every map x renderer x preset x resolution, each repeated, on a local server full of seeded bots. The client
stays in spectator free-fly and turns slowly for the whole window, so every run sees the same kind of scene.
Loopback only. Every process runs with its own fs_homepath under --home, so the game folder is never written.

    python bench.py run    --game <install> [options]     client matrix (and the server CPU run)
    python bench.py server --game <install> [options]     dedicated server CPU at 0 / 16 / 32 players only

Options
    --maps obj_village,obj_snow,...   default: the six official maps
    --renderers dx12,opengl           default both
    --presets low,high,ultra          the launcher's own preset files (platinum-preset-0/1/2.cfg)
    --preset-dir <dir>                where those files are (a profile's tcetest folder or a harness copy)
    --sizes 1920x1080,2560x1440       default both
    --dlss                            also Ultra with DLSS Quality at the largest size (DX12 only)
    --seconds 60 --repeats 3          measured seconds per run, runs per case (the median is reported)
    --uncapped                        lift the 500 fps cap: needs a build with com_benchUncapped
                                      (platinum-engine kit phase0-profiler); the server then runs as devmap
    --profile                         also capture 'profile 1200' (development build with FEATURE_PROFILER)
    --home <dir> --out <dir>          private profiles and results (default under the current folder)
    --ports 28310                     server UDP port; the client uses the next one
    --tools <project root>            folder with analysis_scripts/integration/candidate_common.py
                                      (required, or set TCP_PROJECT_ROOT)

Output: <out>/results.csv (one row per case, median of the repeats), <out>/runs/*.json (every run),
<out>/SUMMARY.md. Run it through the PC job queue under suite.lock, like every other game test.
"""
from pathlib import Path
import argparse, csv, ctypes, ctypes.wintypes as wt, json, os, re, shutil, statistics, subprocess, sys, time

OFFICIAL = 'obj_village,obj_snow,obj_northport,obj_railhouse,obj_delta,obj_stadtrand'
PRESETS = {'low': 0, 'high': 1, 'ultra': 2}

ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=['run', 'server'])
ap.add_argument('--game', required=True, type=Path)
ap.add_argument('--maps', default=OFFICIAL)
ap.add_argument('--renderers', default='dx12,opengl')
ap.add_argument('--presets', default='low,high,ultra')
ap.add_argument('--preset-dir', type=Path)
ap.add_argument('--sizes', default='1920x1080,2560x1440')
ap.add_argument('--dlss', action='store_true')
ap.add_argument('--seconds', type=int, default=60)
ap.add_argument('--repeats', type=int, default=3)
ap.add_argument('--bots', type=int, default=16)
ap.add_argument('--seed', type=int, default=1)
ap.add_argument('--uncapped', action='store_true')
ap.add_argument('--profile', action='store_true')
ap.add_argument('--home', type=Path, default=Path('bench-home'))
ap.add_argument('--out', type=Path, default=Path('bench-results'))
ap.add_argument('--ports', type=int, default=28310)
ap.add_argument('--tools', type=Path, default=Path(os.environ['TCP_PROJECT_ROOT']) if os.environ.get('TCP_PROJECT_ROOT') else None)
A = ap.parse_args()
if A.tools is None:
    ap.error('pass --tools <project root> or set TCP_PROJECT_ROOT')
GAME, HOME, OUT = A.game.resolve(), A.home.resolve(), A.out.resolve()
SERVER_PORT, CLIENT_PORT = A.ports, A.ports + 1
sys.path.insert(0, str(A.tools / 'analysis_scripts/integration'))
from candidate_common import protocol_for_module  # noqa: E402

# ---- process CPU / memory via Win32 (psutil is not installed on the PC) ----
k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi


class PMC(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('PageFaultCount', wt.DWORD)] + [(n, ctypes.c_size_t) for n in (
        'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
        'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]


def _h(pid):
    return k32.OpenProcess(0x1000 | 0x0400 | 0x0010, False, pid)


def cpu_seconds(pid):
    h = _h(pid)
    c, e, kt, ut = (wt.FILETIME() for _ in range(4))
    k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut))
    k32.CloseHandle(h)
    f = lambda t: ((t.dwHighDateTime << 32) | t.dwLowDateTime) / 1e7
    return f(kt) + f(ut)


def mem(pid):
    h = _h(pid)
    p = PMC(); p.cb = ctypes.sizeof(p)
    psapi.GetProcessMemoryInfo(h, ctypes.byref(p), p.cb)
    k32.CloseHandle(h)
    return {'private_mb': round(p.PrivateUsage / 2**20, 1), 'working_set_mb': round(p.WorkingSetSize / 2**20, 1)}


def cpu_window(pid, seconds):
    c0, t0 = cpu_seconds(pid), time.perf_counter()
    time.sleep(seconds)
    return round(100 * (cpu_seconds(pid) - c0) / (time.perf_counter() - t0), 1)


# ---- launching ----
def launch(home, server, commands, renderer='dx12'):
    (home / 'tcetest').mkdir(parents=True, exist_ok=True)
    (home / 'tcetest/bench.cfg').write_text(commands)
    if not server and A.preset_dir:
        for f in A.preset_dir.glob('platinum-preset-*.cfg'):
            shutil.copy(f, home / 'tcetest' / f.name)
    cmd = [str(GAME / ('server/platinum-server.bin' if server else 'engine/platinum-engine.bin'))]
    opts = {'fs_basepath': GAME, 'fs_homepath': home, 'fs_game': 'tcetest', 'net_ip': '127.0.0.1',
            'net_port': SERVER_PORT if server else CLIENT_PORT, 'net_port6': 0, 'logfile': 2}
    if server:
        opts.update({'dedicated': 1, 'sv_maxclients': 34, 'sv_pure': 0, 'sv_fps': 128, 'tcp_native_host_control': 1,
                     'sv_master1': '', 'sv_master2': '', 'sv_master3': '', 'sv_master4': '', 'sv_master5': '',
                     'bot_seed': A.seed, 'g_weather': 'clear'})
    else:
        opts.update({'com_introplayed': 1, 'com_recommendedSet': 1, 'cl_renderer': renderer, 's_initsound': 1,
                     'r_dx12Debug': 0, 'r_fullscreen': 0})
    for k, v in opts.items():
        cmd += ['+set', k, str(v)]
    if not server:
        cmd += ['+setu', 'tcp_native_protocol', protocol_for_module(GAME / 'tcetest/qagame_mp_x64.dll')]
    cmd += ['+exec', 'bench.cfg']
    log = (home / 'process.log').open('w')
    si = subprocess.STARTUPINFO(); si.dwFlags = subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = 0 if server else 4
    return subprocess.Popen(cmd, cwd=GAME, startupinfo=si, creationflags=subprocess.CREATE_NEW_CONSOLE, stdout=log,
                            stderr=subprocess.STDOUT), log


def console(home):
    f = home / 'tcetest/etconsole.log'
    return f.read_text(encoding='utf-8', errors='replace') if f.exists() else ''


def wait_for(home, marker, proc, seconds=120, step=0.02):
    end = time.time() + seconds
    while time.time() < end:
        if marker in console(home):
            return time.perf_counter()
        if proc.poll() is not None:
            return None
        time.sleep(step)
    return None


def start_server(mapname, bots, tag):
    sh = HOME / f'server-{tag}'
    shutil.rmtree(sh, ignore_errors=True)
    load = 'devmap' if A.uncapped else 'map'   # devmap = sv_cheats 1, which com_benchUncapped needs on the client
    srv, log = launch(sh, True, f'set tcp_native_targets 0\nset bot_minplayers {bots}\nset bot_skill 3\n{load} {mapname}\n')
    if not wait_for(sh, 'TCP_NATIVE_STATUS', srv):
        srv.kill(); raise SystemExit('server did not load ' + mapname)
    return srv, log, sh


STATS = re.compile(r'FRAMESTATS(?: STOPPED)?: (\d+) frames, avg ([\d.]+) ms \(([\d.]+) fps\), 1% low ([\d.]+) fps \(([\d.]+) ms\), '
                   r'p99 ([\d.]+), p99\.9 ([\d.]+), max ([\d.]+), spikes (\d+)')
GPU = re.compile(r'DX12 GPU: frame ([\d.]+) ms')
PROFILE = re.compile(r'PROFILE (.+?)\s+avg\s+([\d.]+) ms\s+p99\s+([\d.]+) ms\s+max\s+([\d.]+) ms\s+([\d.]+)% of frame')


def combine(text):
    ws = [dict(zip(('frames', 'avg_ms', 'fps', 'low1_fps', 'low1_ms', 'p99', 'p999', 'max', 'spikes'), m.groups()))
          for m in STATS.finditer(text)]
    if not ws:
        return {}
    frames = sum(int(w['frames']) for w in ws)
    total = sum(int(w['frames']) * float(w['avg_ms']) for w in ws)
    return {'frames': frames, 'avg_fps': round(1000 * frames / total, 1), 'avg_ms': round(total / frames, 3),
            'low1_fps': round(1000 / (sum(int(w['frames']) * float(w['low1_ms']) for w in ws) / frames), 1),
            'p99_ms': max(float(w['p99']) for w in ws), 'worst_ms': max(float(w['max']) for w in ws),
            'frames_over_33ms': sum(int(w['spikes']) for w in ws)}


def client_cfg(cvars, body):
    lines = [f'set {k} {v}' for k, v in cvars.items()] + ['vid_restart', 'wait 200', 'set cl_frameStats 100000',
                                                       'echo BENCH_CONNECT', f'connect 127.0.0.1:{SERVER_PORT}']
    return '\n'.join(lines + body) + '\n'


def run_client(home, renderer, size, preset, dlss):
    w, h = size.split('x')
    cv = {'r_fullscreen': 0, 'r_mode': -1, 'r_customwidth': w, 'r_customheight': h, 'r_swapInterval': 0,
          'com_maxfps': 500, 'com_maxfpsUnfocused': 500, 'cl_frameSpikeMs': 33, 'r_dx12HitchMs': 33,
          'cg_popupLimboMenu': 0, 'cg_tips': 0, 'r_dx12GpuTimes': 1000 if renderer == 'dx12' else 0}
    pre = [f'exec platinum-preset-{PRESETS[preset]}.cfg'] if A.preset_dir else []
    if dlss:
        pre.append('set r_dx12Dlss 2')
    measure = ['wait 400', 'set cl_frameStats 0', 'wait 2', 'echo BENCH_MEASURE', 'set cl_frameStats 2000',
               'set cl_yawspeed 30', '+right']
    if A.uncapped:
        measure.insert(0, 'set com_benchUncapped 1')
    if A.profile:
        measure += ['wait 2000', 'profile 1200']
    proc, log = launch(home, False, '\n'.join(pre) + '\n' + client_cfg(cv, measure + ['wait 10000000']), renderer)
    t0 = wait_for(home, 'BENCH_CONNECT', proc, 60)
    t1 = wait_for(home, 'state 8', proc, 180)
    if not wait_for(home, 'BENCH_MEASURE', proc, 60):
        proc.kill(); log.close()
        return {'error': 'client never reached the measured window'}
    m0 = len(console(home))
    c0, w0 = cpu_seconds(proc.pid), time.perf_counter()
    time.sleep(A.seconds)
    cpu = round(100 * (cpu_seconds(proc.pid) - c0) / (time.perf_counter() - w0), 1)
    text = console(home)[m0:]
    memo = mem(proc.pid)
    proc.kill(); log.close(); time.sleep(1)
    full = console(home)
    gpu = [float(x) for x in GPU.findall(text)]
    return {'load_s': round(t1 - t0, 2) if t0 and t1 else None, **combine(text), 'client_cpu_pct': cpu, **memo,
            'gpu_ms': round(statistics.median(gpu), 3) if gpu else None,
            'profile': {m.group(1).strip(): {'avg_ms': float(m.group(2)), 'p99_ms': float(m.group(3)), 'share_pct': float(m.group(5))}
                        for m in PROFILE.finditer(full)},
            'errors': [l.strip() for l in full.splitlines() if re.search(r'ERROR|WARNING: .*fail|Exception', l)][:8]}


def save(name, data):
    (OUT / 'runs').mkdir(parents=True, exist_ok=True)
    (OUT / 'runs' / f'{name}.json').write_text(json.dumps(data, indent=2))


def server_cpu():
    rows = []
    for bots in (0, 16, 32):
        srv, log, sh = start_server('obj_railhouse', bots, f'cpu-{bots}')
        time.sleep(10 if bots else 3)
        r = {'players': bots, 'cpu_pct': cpu_window(srv.pid, 60), **mem(srv.pid)}
        srv.kill(); log.close(); time.sleep(1)
        rows.append(r); save(f'server-{bots}', r)
    return rows


def cases():
    sizes = A.sizes.split(',')
    for mapname in A.maps.split(','):
        for renderer in A.renderers.split(','):
            for preset in A.presets.split(','):
                for size in sizes:
                    yield mapname, renderer, preset, size, False
            if A.dlss and renderer == 'dx12':
                yield mapname, renderer, 'ultra', sizes[-1], True


METRICS = ['avg_fps', 'low1_fps', 'avg_ms', 'p99_ms', 'worst_ms', 'frames_over_33ms', 'gpu_ms', 'client_cpu_pct', 'private_mb', 'load_s']

OUT.mkdir(parents=True, exist_ok=True)
summary = ['# Platinum Engine benchmark', '', f'- Game: {GAME}', f'- Started: {time.strftime("%Y-%m-%d %H:%M:%S")}',
           f'- {A.seconds} s per run, {A.repeats} runs per case (median), {A.bots} bots, seed {A.seed}, '
           f'{"uncapped" if A.uncapped else "500 fps cap"}', '']
srows = server_cpu()
summary += ['## Dedicated server CPU (obj_railhouse, 128 Hz)', '', '| Players | CPU % of one core | Private MB |', '|---|---|---|']
summary += [f'| {r["players"]} | {r["cpu_pct"]} | {r["private_mb"]} |' for r in srows] + ['']
if A.mode == 'run':
    with (OUT / 'results.csv').open('w', newline='') as fh:
        out = csv.writer(fh)
        out.writerow(['map', 'renderer', 'preset', 'size', 'dlss'] + METRICS)
        summary += ['## Client', '', '| Map | Renderer | Preset | Size | Avg fps | 1% low | p99 ms | GPU ms | Load s |', '|---|---|---|---|---|---|---|---|---|']
        for mapname, renderer, preset, size, dlss in cases():
            srv, slog, sh = start_server(mapname, A.bots, mapname)
            time.sleep(10)
            runs = []
            for i in range(A.repeats):
                tag = f'{mapname}-{renderer}-{preset}-{size}{"-dlss" if dlss else ""}-{i + 1}'
                home = HOME / f'client-{tag}'
                shutil.rmtree(home, ignore_errors=True)
                r = run_client(home, renderer, size, preset, dlss)
                save(tag, r); runs.append(r)
            srv.kill(); slog.close(); time.sleep(1)
            med = {m: (statistics.median([r[m] for r in runs if r.get(m) is not None]) if any(r.get(m) is not None for r in runs) else '')
                   for m in METRICS}
            out.writerow([mapname, renderer, preset, size, int(dlss)] + [med[m] for m in METRICS]); fh.flush()
            summary.append(f'| {mapname} | {renderer} | {preset}{" + DLSS Q" if dlss else ""} | {size} | {med["avg_fps"]} | '
                           f'{med["low1_fps"]} | {med["p99_ms"]} | {med["gpu_ms"]} | {med["load_s"]} |')
(OUT / 'SUMMARY.md').write_text('\n'.join(summary) + '\n')
print('\n'.join(summary))
