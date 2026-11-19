#!/usr/bin/env python3
"""Compares two feel traces (tools/feelcheck) and reports the first frame where they differ.

    compare.py <expected.trace> <actual.trace> [--md out.md]

Exit 0 when the traces are identical, 1 when they differ, 2 on a bad or short trace.
"""
import sys

FIELDS = {'t': 'command time', 'pm': 'movement type', 'pf': 'movement flags', 'ef': 'entity flags',
          'o': 'position', 'v': 'velocity', 'a': 'view angles', 'w': 'weapon', 'ws': 'weapon state',
          'hp': 'health', 'clip': 'ammo in clip', 'ammo': 'ammo', 'ev': 'event count'}


def frames(path):
    """Yields (time, world hash, {client: (state hash, {field: value})})."""
    with open(path, encoding='ascii', errors='replace') as fh:
        head = fh.readline().split()
        if head[:2] != ['FEELTRACE', '1']:
            raise ValueError(f'{path}: not a feel trace')
        cur = None
        for line in fh:
            part = line.split()
            if not part:
                continue
            if part[0] == 'F':
                if cur:
                    yield cur
                cur = (int(part[1]), part[2], {})
            elif part[0] == 'P' and cur:
                cur[2][int(part[1])] = (part[2], dict(kv.split('=', 1) for kv in part[3:]))
        if cur:
            yield cur


def show(v):
    """Hex floats in the trace are exact; print them as plain numbers."""
    out = []
    for x in v.split(','):
        try:
            out.append(f'{float.fromhex(x):.3f}' if 'p' in x else x)
        except ValueError:
            out.append(x)
    return ' '.join(out)


def compare(a_path, b_path):
    lines, n, players = [], 0, 0
    a_it, b_it = frames(a_path), frames(b_path)
    while True:
        a, b = next(a_it, None), next(b_it, None)
        if a is None or b is None:
            if a is None and b is None:
                return 0, n, players, ['Identical: every traced frame matches.']
            short = 'expected' if a is None else 'actual'
            return 1, n, players, [f'The {short} trace ends after {n} frames while the other goes on.']
        n += 1
        players = max(players, len(a[2]))
        if a[0] != b[0]:
            return 1, n, players, [f'Frame {n}: server time {a[0]} ms expected, {b[0]} ms found.']
        if set(a[2]) != set(b[2]):
            return 1, n, players, [f'Frame {n} ({a[0]} ms): active clients {sorted(a[2])} expected, {sorted(b[2])} found.']
        for c in sorted(a[2]):
            (ha, fa), (hb, fb) = a[2][c], b[2][c]
            if ha == hb:
                continue
            lines.append(f'Frame {n} ({a[0]} ms), client {c}: first difference.')
            diff = [k for k in fa if fa.get(k) != fb.get(k)]
            for k in diff:
                lines.append(f'- {FIELDS.get(k, k)}: expected {show(fa[k])}, found {show(fb.get(k, "?"))}')
            if not diff:
                lines.append('- a player-state field outside the traced list differs (same position, health and weapon)')
            return 1, n, players, lines
        if a[1] != b[1]:
            return 1, n, players, [f'Frame {n} ({a[0]} ms): players identical, but other entities differ '
                                   '(projectiles, grenades, doors, dropped weapons or items).']


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    md = sys.argv[sys.argv.index('--md') + 1] if '--md' in sys.argv else None
    if md:
        args.remove(md)
    if len(args) != 2:
        print(__doc__)
        return 2
    try:
        code, n, players, lines = compare(*args)
    except (OSError, ValueError) as e:
        print(f'feel check: {e}')
        return 2
    if n < 128:
        lines.append(f'Trace too short ({n} frames): the server probably did not run.')
        code = 2
    text = '\n'.join(lines) + f'\n\nFrames compared: {n} ({n / 128:.1f} s of game time), up to {players} players.\n'
    print(text)
    if md:
        with open(md, 'w', encoding='utf-8') as fh:
            fh.write(text)
    return code


if __name__ == '__main__':
    sys.exit(main())
