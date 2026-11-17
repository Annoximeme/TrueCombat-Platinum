#!/usr/bin/env python3
"""Removes the hashed connection address from match reports older than 90 days (privacy retention).

A tcp-match/2 report gives every player an "ip" field: a short hash of their connection address. The stats
service only uses it inside one match, to treat two clients behind one address as one person. After the
retention period this script swaps each hash for a small per-match label ("1", "2", ...): players who shared
an address in that match still share a label, so a rebuild gives exactly the same stats, but nothing links a
label to an address or to the same player in another match.

It rewrites both copies: the report files in each --dir, and the reports stored in the stats database.
Idempotent; run it nightly (deploy/tcp-strip-ips.timer).

  python3 tcp_strip_ips.py --db /var/lib/tcp-stats/stats.db --dir /var/lib/tcpgame/home-unranked/tcetest/stats
  add --dry-run to only count
"""
import argparse
import calendar
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import time

DAYS = 90


def parse_time(s):
    try:
        return calendar.timegm(time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def done(ip):
    return len(ip) <= 3  # labels are "1".."ff"; real hashes are 12 hex digits


def relabel(report):
    """Returns True when the report changed."""
    players = report.get("players") if isinstance(report, dict) else None
    if not isinstance(players, list):
        return False
    labels, changed = {}, False
    for p in players:
        ip = str(p.get("ip") or "") if isinstance(p, dict) else ""
        if not ip or done(ip):
            continue
        if ip not in labels:
            labels[ip] = "%x" % (len(labels) + 1)
        p["ip"] = labels[ip]
        changed = True
    return changed


def write_atomic(path, text):
    st = path.stat()
    fd, tmp = tempfile.mkstemp(prefix=".strip-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, st.st_mode & 0o7777)
        if os.geteuid() == 0:
            os.chown(tmp, st.st_uid, st.st_gid)
        os.utime(tmp, (st.st_atime, st.st_mtime))
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def strip_dir(folder, cutoff, dry):
    n = 0
    for path in sorted(pathlib.Path(folder).glob("*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ended = parse_time(report.get("ended")) if isinstance(report, dict) else None
        if ended is None:
            ended = path.stat().st_mtime
        if ended >= cutoff or not relabel(report):
            continue
        n += 1
        if not dry:
            write_atomic(path, json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return n


def strip_db(db_path, cutoff, dry):
    db = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    db.execute("PRAGMA busy_timeout=30000")
    cut = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(cutoff))
    rows = db.execute("SELECT server, id, report FROM matches WHERE ended < ? AND report LIKE '%\"ip\"%'", (cut,)).fetchall()
    n = 0
    for server, mid, text in rows:
        try:
            report = json.loads(text)
        except (TypeError, ValueError):
            continue
        if not relabel(report):
            continue
        n += 1
        if not dry:
            db.execute("UPDATE matches SET report=? WHERE server=? AND id=?",
                       (json.dumps(report, ensure_ascii=False, separators=(",", ":")), server, mid))
    db.close()
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", help="stats database (tcp_stats.py)")
    ap.add_argument("--dir", action="append", default=[], help="folder of tcp-match report files (repeatable)")
    ap.add_argument("--days", type=int, default=DAYS)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.days < 1:
        sys.exit("--days must be at least 1")
    cutoff = time.time() - a.days * 86400
    files = sum(strip_dir(d, cutoff, a.dry_run) for d in a.dir)
    rows = strip_db(a.db, cutoff, a.dry_run) if a.db else 0
    print("%s: %d report files, %d stored reports older than %d days" %
          ("would strip" if a.dry_run else "stripped", files, rows, a.days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
