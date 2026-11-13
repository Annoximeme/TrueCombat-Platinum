#!/usr/bin/env python3
"""TrueCombat: Platinum donation ledger for the Support page.

Ko-fi calls a webhook for every donation and membership payment. This small
service receives those calls, keeps them in SQLite and serves monthly totals
for the "Where the money goes" report on truecombat.eu/support.html:

  POST /kofi/webhook     Ko-fi webhook (form field "data", JSON; checked against
                         the verification token from Ko-fi > Settings > API)
  GET  /funding.json     monthly totals and the public supporters list
                         (schema tcp-funding/1)
  GET  /kofi/health

Privacy: e-mail addresses, Ko-fi URLs and messages are never stored. A name is
only published when the supporter left "make this public" on; everyone else
is listed as Anonymous.

Python 3.8+ standard library only. Run it behind the same HTTPS proxy as the
stats bridge, for example with Caddy on api.truecombat.eu:

  handle /kofi/* { reverse_proxy 127.0.0.1:8091 }
  handle /funding.json { reverse_proxy 127.0.0.1:8091 }

  python tcp_kofi.py --db /var/lib/tcp-kofi/kofi.db --token-file /etc/tcp-kofi/token

Backfill or corrections: `tcp_kofi.py --db ... add 2026-11-03 5.00 "Name"`
records a payment by hand (for example from Ko-fi's CSV export).
"""
import argparse
import datetime as dt
import hmac
import json
import pathlib
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SCHEMA = "tcp-funding/1"
MAX_BODY = 64 * 1024
COUNTED = {"Donation", "Subscription"}
TEST_ID = "00000000-1111-2222-3333-"  # transaction id of Ko-fi test webhooks  # shop orders and commissions are not donations


class Ledger:
    def __init__(self, path):
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path or ":memory:", check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY, ts TEXT NOT NULL, type TEXT NOT NULL, cents INTEGER NOT NULL,
            currency TEXT NOT NULL, public INTEGER NOT NULL, name TEXT NOT NULL, monthly INTEGER NOT NULL)""")
        self.db.commit()

    def add(self, pid, ts, kind, cents, currency, public, name, monthly):
        with self.lock:
            cur = self.db.execute("INSERT OR IGNORE INTO payments VALUES (?,?,?,?,?,?,?,?)",
                                  (pid, ts, kind, cents, currency.upper(), int(bool(public)), name, int(bool(monthly))))
            self.db.commit()
            return cur.rowcount == 1

    def report(self, goal=0):
        with self.lock:
            rows = self.db.execute("SELECT ts, cents, currency, public, name, monthly FROM payments ORDER BY ts").fetchall()
        months = {}
        for ts, cents, cur, public, name, monthly in rows:
            m = months.setdefault(ts[:7], {"month": ts[:7], "received": {}, "count": 0, "supporters": []})
            m["received"][cur] = m["received"].get(cur, 0) + cents
            m["count"] += 1
            m["supporters"].append({"name": name if public and name else None, "amount": cents / 100,
                                    "currency": cur, "monthly": bool(monthly), "date": ts[:10]})
        out = []
        for key in sorted(months, reverse=True):
            m = months[key]
            m["received"] = {c: v / 100 for c, v in m["received"].items()}
            m["supporters"].reverse()  # newest first
            out.append(m)
        return {"schema": SCHEMA, "goal": goal, "updated": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "months": out}


def clean_name(s):
    s = " ".join(str(s or "").split())
    return "".join(ch for ch in s if ch.isprintable())[:40]


def parse_kofi(body, token):
    """Returns (status, payment-tuple-or-None). Raises nothing."""
    try:
        form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        data = json.loads(form.get("data", [""])[0])
    except (UnicodeDecodeError, ValueError):
        return 400, None
    if not isinstance(data, dict):
        return 400, None
    if not token or not hmac.compare_digest(str(data.get("verification_token", "")), token):
        return 403, None
    if data.get("type") not in COUNTED:
        return 200, None  # acknowledged, not counted
    if str(data.get("kofi_transaction_id", "")).startswith(TEST_ID):
        return 200, None  # Ko-fi's "Send test" button
    try:
        cents = int(round(float(str(data.get("amount", "0")).replace(",", ".")) * 100))
        ts = dt.datetime.strptime(str(data.get("timestamp", ""))[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return 400, None
    pid = str(data.get("kofi_transaction_id") or data.get("message_id") or "")
    if not pid or cents <= 0:
        return 400, None
    return 200, (pid, ts.strftime("%Y-%m-%dT%H:%M:%SZ"), data["type"], cents, str(data.get("currency") or "EUR"),
                 bool(data.get("is_public")), clean_name(data.get("from_name")),
                 data["type"] == "Subscription" or bool(data.get("is_subscription_payment")))


def make_handler(ledger, token, goal, cors):
    class Handler(BaseHTTPRequestHandler):
        server_version = "tcp-kofi"
        timeout = 30                       # a client that stops sending frees its thread

        def log_message(self, fmt, *a):
            pass

        def send_json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            origin = self.headers.get("Origin", "")
            if "*" in cors:
                self.send_header("Access-Control-Allow-Origin", "*")
            elif origin in cors:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):
            p = urlparse(self.path).path
            if p == "/funding.json":
                return self.send_json(ledger.report(goal))
            if p == "/kofi/health":
                return self.send_json({"ok": True})
            self.send_json({"error": "not found"}, 404)

        do_HEAD = do_GET

        def do_POST(self):
            if urlparse(self.path).path != "/kofi/webhook":
                return self.send_json({"error": "not found"}, 404)
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if n <= 0 or n > MAX_BODY:
                return self.send_json({"error": "bad size"}, 413)
            code, pay = parse_kofi(self.rfile.read(n), token)
            if pay:
                new = ledger.add(*pay)
                print("kofi %s %s %.2f %s%s" % (pay[1], pay[2], pay[3] / 100, pay[4], "" if new else " (duplicate)"), flush=True)
            self.send_json({"ok": code == 200}, code)

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="", help="SQLite file (empty = in memory)")
    ap.add_argument("--listen", default="127.0.0.1:8091")
    ap.add_argument("--token-file", default="", help="file holding the Ko-fi verification token")
    ap.add_argument("--goal", type=int, default=150, help="monthly goal in euros")
    ap.add_argument("--cors", default="https://truecombat.eu,https://www.truecombat.eu")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="record a payment by hand")
    a.add_argument("date", help="YYYY-MM-DD")
    a.add_argument("amount", help="e.g. 5.00")
    a.add_argument("name", nargs="?", default="", help="leave empty for Anonymous")
    a.add_argument("--monthly", action="store_true")
    a.add_argument("--currency", default="EUR")
    sub.add_parser("report", help="print funding.json")
    args = ap.parse_args(argv)
    ledger = Ledger(args.db)

    if args.cmd == "add":
        day = dt.datetime.strptime(args.date, "%Y-%m-%d")
        cents = int(round(float(args.amount.replace(",", ".")) * 100))
        pid = "manual-%s-%d-%s" % (args.date, cents, clean_name(args.name) or "anon")
        ok = ledger.add(pid, day.strftime("%Y-%m-%dT12:00:00Z"), "Subscription" if args.monthly else "Donation",
                        cents, args.currency, bool(args.name), clean_name(args.name), args.monthly)
        print("added" if ok else "already recorded")
        return
    if args.cmd == "report":
        print(json.dumps(ledger.report(args.goal), indent=2, ensure_ascii=False))
        return

    token = pathlib.Path(args.token_file).read_text(encoding="utf-8").strip() if args.token_file else ""
    if not token:
        sys.exit("no --token-file given (Ko-fi > Settings > API > Verification Token)")
    host, _, port = args.listen.rpartition(":")
    cors = [c.strip() for c in args.cors.split(",") if c.strip()]
    print("tcp-kofi on http://%s:%s" % (host, port), flush=True)
    ThreadingHTTPServer.request_queue_size = 128   # the default 5 overflows under a burst behind Caddy
    httpd = ThreadingHTTPServer((host, int(port)), make_handler(ledger, token, args.goal, cors))
    httpd.daemon_threads = True
    httpd.serve_forever()


if __name__ == "__main__":
    main()
