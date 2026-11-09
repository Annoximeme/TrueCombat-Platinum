import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import tcp_kofi

TOKEN = "test-token"


def body(**kw):
    d = {"verification_token": TOKEN, "message_id": "m1", "kofi_transaction_id": "t1", "timestamp": "2026-11-09T10:00:00Z",
         "type": "Donation", "is_public": True, "from_name": "RaziC*", "message": "gl", "amount": "5.00",
         "email": "someone@example.com", "currency": "EUR", "is_subscription_payment": False}
    d.update(kw)
    return urllib.parse.urlencode({"data": json.dumps(d)}).encode()


class KofiTest(unittest.TestCase):
    def setUp(self):
        self.ledger = tcp_kofi.Ledger("")
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), tcp_kofi.make_handler(self.ledger, TOKEN, 150, ["*"]))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()

    def post(self, data):
        try:
            return urllib.request.urlopen(self.base + "/kofi/webhook", data, timeout=5).status
        except urllib.error.HTTPError as e:
            return e.code

    def report(self):
        return json.load(urllib.request.urlopen(self.base + "/funding.json", timeout=5))

    def test_donation_counted_once(self):
        self.assertEqual(self.post(body()), 200)
        self.assertEqual(self.post(body()), 200)  # Ko-fi retry
        r = self.report()
        self.assertEqual(r["schema"], "tcp-funding/1")
        self.assertEqual(r["goal"], 150)
        m = r["months"][0]
        self.assertEqual((m["month"], m["received"], m["count"]), ("2026-11", {"EUR": 5.0}, 1))
        self.assertEqual(m["supporters"][0]["name"], "RaziC*")
        self.assertNotIn("someone@example.com", json.dumps(r))
        self.assertNotIn("gl", json.dumps(m["supporters"]))

    def test_private_is_anonymous_and_monthly(self):
        self.post(body(is_public=False, type="Subscription", kofi_transaction_id="t2", amount="3.00", is_subscription_payment=True))
        s = self.report()["months"][0]["supporters"][0]
        self.assertIsNone(s["name"])
        self.assertTrue(s["monthly"])

    def test_bad_token_and_shop_orders(self):
        self.assertEqual(self.post(body(verification_token="nope")), 403)
        self.assertEqual(self.post(body(type="Shop Order", kofi_transaction_id="t3")), 200)
        self.assertEqual(self.post(b"garbage"), 400)
        self.assertEqual(self.report()["months"], [])

    def test_months_newest_first(self):
        self.post(body(kofi_transaction_id="a", timestamp="2026-11-30T23:00:00Z"))
        self.post(body(kofi_transaction_id="b", timestamp="2026-12-01T08:00:00Z", amount="2.50"))
        self.assertEqual([m["month"] for m in self.report()["months"]], ["2026-12", "2026-11"])

    def test_manual_add(self):
        led = tcp_kofi.Ledger("")
        self.assertTrue(led.add("x", "2026-11-03T12:00:00Z", "Donation", 500, "EUR", False, "", False))
        self.assertFalse(led.add("x", "2026-11-03T12:00:00Z", "Donation", 500, "EUR", False, "", False))


if __name__ == "__main__":
    unittest.main()
