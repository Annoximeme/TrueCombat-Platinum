#!/usr/bin/env python3
"""TrueCombat: Platinum stats upload agent, run next to a ranked game server.

The game server writes one tcp-match/1 report per finished match to
<fs_homepath>/tcetest/stats/. This agent signs each new report with the server's
key (HMAC-SHA256, from `tcp_stats.py add-server`) and posts it to the stats
service. Sent reports move to stats/sent/, refused ones to stats/rejected/ with
the reason next to them. Network errors are retried with a growing delay.
Python 3.8+ standard library only.

  python tcp_stats_agent.py --dir "<homepath>/tcetest/stats" --url https://api.truecombat.eu \
      --server 1a2b3c4d5e6f --key-file stats-key.txt
"""
import argparse
import hashlib
import hmac
import json
import pathlib
import time
import urllib.error
import urllib.request


def sign(key_hex, body, stamp=None):
    stamp = str(int(stamp if stamp is not None else time.time()))
    return stamp, hmac.new(bytes.fromhex(key_hex), stamp.encode() + b"\n" + body, hashlib.sha256).hexdigest()


def post(url, server, key, body, timeout=15):
    stamp, sig = sign(key, body)
    req = urllib.request.Request(url.rstrip("/") + "/api/v1/match", data=body, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "tcp-stats-agent/1",
        "X-TCP-Server": server, "X-TCP-Time": stamp, "X-TCP-Signature": sig})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def run_once(folder, url, server, key, log=print):
    """Uploads every pending report once. Returns (sent, rejected, retry)."""
    folder = pathlib.Path(folder)
    sent_dir, bad_dir = folder / "sent", folder / "rejected"
    counts = [0, 0, 0]
    for path in sorted(folder.glob("*.json")):
        if time.time() - path.stat().st_mtime < 2:      # still being written
            continue
        body = path.read_bytes()
        try:
            json.loads(body.decode("utf-8"))
        except ValueError:
            if time.time() - path.stat().st_mtime < 60:
                continue
            code, text = 400, '{"error":"not JSON"}'
        else:
            try:
                code, text = post(url, server, key, body)
            except (OSError, urllib.error.URLError) as exc:
                log("upload of %s failed: %s" % (path.name, exc))
                counts[2] += 1
                continue
        if code in (200, 409):
            sent_dir.mkdir(exist_ok=True)
            path.replace(sent_dir / path.name)
            counts[0] += 1
            log("%s %s" % ("sent" if code == 200 else "already stored", path.name))
        elif code in (400, 413, 422):
            bad_dir.mkdir(exist_ok=True)
            path.replace(bad_dir / path.name)
            (bad_dir / (path.stem + ".reason.txt")).write_text(text, encoding="utf-8")
            counts[1] += 1
            log("rejected %s: %s" % (path.name, text))
        else:                                             # 401/429/5xx: keep and retry
            counts[2] += 1
            log("will retry %s: HTTP %d %s" % (path.name, code, text))
    return tuple(counts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", required=True, help="the game server's stats folder")
    ap.add_argument("--url", required=True, help="stats service base URL")
    ap.add_argument("--server", required=True, help="server id from tcp_stats.py add-server")
    ap.add_argument("--key-file", required=True, help="file holding the server's secret key")
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args(argv)
    key = pathlib.Path(args.key_file).read_text(encoding="utf-8").strip()
    bytes.fromhex(key)
    delay = args.interval
    while True:
        sent, bad, retry = run_once(args.dir, args.url, args.server, key, lambda m: print(m, flush=True))
        if args.once:
            return 0 if not retry else 1
        delay = min(delay * 2, 600) if retry else args.interval
        time.sleep(delay)


if __name__ == "__main__":
    raise SystemExit(main())
