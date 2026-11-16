#!/usr/bin/env python3
"""Watches the staff portal from outside and tells the staff channel when it stops answering.

The portal raises its own alerts, so it cannot report that it is down itself. This runs every two minutes from
tcp-staff-watch.timer: two failed checks in a row post "Staff portal is down" to the staff webhook, and the next
good check posts that it is back. It also warns once a day when the nightly database snapshot is missing or old.

    python3 tcp_staff_watch.py [--url http://127.0.0.1:8097/healthz] [--state DIR] [--webhook FILE]

Standard library only. The webhook URL arrives as the systemd credential "staff-webhook" (an empty file: no posts).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WEBHOOK = re.compile(r"^https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+$")


def check(url: str) -> str:
    """'' when the portal answers {"ok": true}, otherwise what went wrong."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "TCPStaffWatch"}), timeout=10) as r:
            body = json.loads(r.read().decode() or "{}")
        return "" if body.get("ok") else "answered without ok"
    except urllib.error.HTTPError as e:
        return "HTTP %d" % e.code
    except (urllib.error.URLError, OSError, ValueError) as e:
        return str(getattr(e, "reason", e))[:200] or "no answer"


def post(webhook: str, title: str, text: str, colour: int) -> bool:
    if not webhook:
        return False
    if not WEBHOOK.match(webhook) and not (os.environ.get("TCP_STAFF_DEV") == "1" and webhook.startswith("http://127.0.0.1:")):
        print("webhook ignored: not a Discord webhook URL", file=sys.stderr)
        return False
    payload = {"username": "Staff Portal", "allowed_mentions": {"parse": []},
               "embeds": [{"title": title, "description": text, "color": colour,
                           "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}]}
    req = urllib.request.Request(webhook, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "TCPStaffWatch"})
    try:
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except (urllib.error.URLError, OSError) as e:
        print("webhook post failed: %s" % e, file=sys.stderr)
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default="http://127.0.0.1:8097/healthz")
    ap.add_argument("--state", default=os.environ.get("STATE_DIRECTORY", "/var/lib/tcp-staff-watch"))
    ap.add_argument("--webhook", help="file with the webhook URL (default: the systemd credential staff-webhook)")
    ap.add_argument("--snapshot", default="/var/lib/tcp-staff-portal/backups/portal-snapshot.db",
                    help="the portal's nightly database snapshot; warns when it is older than --snapshot-hours")
    ap.add_argument("--snapshot-hours", type=float, default=30)
    a = ap.parse_args(argv)
    hook_file = a.webhook or (Path(os.environ["CREDENTIALS_DIRECTORY"]) / "staff-webhook" if os.environ.get("CREDENTIALS_DIRECTORY") else None)
    try:
        webhook = Path(hook_file).read_text(encoding="utf-8").strip() if hook_file else ""
    except OSError:
        webhook = ""
    state_file = Path(a.state) / "state.json"
    try:
        st = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    problem = check(a.url)
    t = int(time.time())
    if problem:
        st["fails"] = int(st.get("fails", 0)) + 1
        st.setdefault("down_since", t)
        if st["fails"] >= 2 and not st.get("alerted"):
            st["alerted"] = post(webhook, "Staff portal is down", "staff.truecombat.eu has not answered for %d minutes: %s.\n"
                                 "Check `systemctl status tcp-staff-portal` on the VPS." % (max(1, (t - st["down_since"]) // 60) + 1, problem),
                                 0xD63B3B) or not webhook
        print("portal check failed (%d in a row): %s" % (st["fails"], problem))
    else:
        if st.get("alerted"):
            post(webhook, "Staff portal is back", "Answering again after %d minutes." % max(1, (t - int(st.get("down_since", t))) // 60), 0x4FBF7A)
        st = {"last_ok": t, "snapshot_warned": st.get("snapshot_warned", 0)}
        try:
            age = t - Path(a.snapshot).stat().st_mtime
        except OSError:
            age = None
        if (age is None or age > a.snapshot_hours * 3600) and t - int(st.get("snapshot_warned", 0)) > 86400:
            st["snapshot_warned"] = t
            post(webhook, "Staff portal snapshot is missing", "The nightly database snapshot %s. The off-site backup has no fresh copy "
                 "of the portal." % ("does not exist" if age is None else "is %d hours old" % (age // 3600)), 0xE7A73C)
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(st), encoding="utf-8")
    except OSError as e:
        print("state not saved: %s" % e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
