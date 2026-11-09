import json
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import tcp_devlog

KEY = "studio-key"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/140.0"


class DevlogTest(unittest.TestCase):
    def setUp(self, public_reads=False, limit=1000):
        self.tmp = tempfile.TemporaryDirectory()
        for slug in ("every-shot", "installer"):
            (pathlib.Path(self.tmp.name) / ("devlog-%s.html" % slug)).write_text("x")
        self.store = tcp_devlog.Store("")
        h = tcp_devlog.make_handler(self.store, KEY, ["https://truecombat.eu"], self.tmp.name, 5, public_reads,
                                    tcp_devlog.Limiter(60, limit))
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), h)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def post(self, path, obj, ip="203.0.113.7", ua=UA):
        req = urllib.request.Request(self.base + path, json.dumps(obj).encode(), method="POST",
                                     headers={"Content-Type": "text/plain", "X-Forwarded-For": ip, "User-Agent": ua})
        try:
            r = urllib.request.urlopen(req, timeout=5)
            return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, None

    def get(self, path, key=None):
        req = urllib.request.Request(self.base + path, headers={"Authorization": "Bearer " + key} if key else {})
        try:
            return json.load(urllib.request.urlopen(req, timeout=5))
        except urllib.error.HTTPError as e:
            return e.code

    def test_reads_count_once_per_reader_per_day(self):
        self.post("/devlog/read", {"slug": "every-shot"})
        self.post("/devlog/read", {"slug": "every-shot"})
        self.post("/devlog/read", {"slug": "every-shot"}, ip="198.51.100.2")
        p = self.get("/devlog/stats.json", KEY)["posts"]["every-shot"]
        self.assertEqual((p["reads"], p["readers"], p["last30"][-1]), (3, 2, 2))

    def test_nothing_identifying_is_stored(self):
        self.post("/devlog/read", {"slug": "every-shot"})
        self.post("/devlog/rate", {"slug": "every-shot", "stars": 4})
        dump = "\n".join(self.store.db.iterdump())
        self.assertNotIn("203.0.113.7", dump)
        self.assertNotIn("Firefox", dump)

    def test_new_day_forgets_hashes(self):
        self.post("/devlog/read", {"slug": "every-shot"})
        self.store.day = "2000-01-01"  # pretend the stored secret belongs to yesterday
        self.store.db.execute("UPDATE secret SET day='2000-01-01'")
        self.post("/devlog/read", {"slug": "every-shot"})
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM secret").fetchone()[0], 1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM seen").fetchone()[0], 1)

    def test_unknown_posts_and_bad_input_are_refused(self):
        self.assertEqual(self.post("/devlog/read", {"slug": "nope"})[0], 404)
        self.assertEqual(self.post("/devlog/read", {"slug": "../etc/passwd"})[0], 404)
        self.assertEqual(self.post("/devlog/rate", {"slug": "installer", "stars": 6})[0], 400)
        self.assertEqual(self.post("/devlog/rate", {"slug": "installer", "stars": True})[0], 400)
        self.assertEqual(self.post("/devlog/rate", {"slug": "installer", "stars": "5"})[0], 400)

    def test_crawlers_are_ignored(self):
        _, r = self.post("/devlog/read", {"slug": "installer"}, ua="Googlebot/2.1")
        self.assertFalse(r["counted"])
        self.assertNotIn("installer", self.get("/devlog/stats.json", KEY)["posts"])

    def test_one_vote_per_reader_and_threshold(self):
        self.post("/devlog/rate", {"slug": "installer", "stars": 1})
        self.post("/devlog/rate", {"slug": "installer", "stars": 5})  # changes the vote, does not add one
        r = self.get("/devlog/stats.json", KEY)["posts"]["installer"]["rating"]
        self.assertEqual((r["n"], r["split"]), (1, [0, 0, 0, 0, 1]))
        self.assertNotIn("installer", self.get("/devlog/public.json")["posts"])
        for i in range(4):
            self.post("/devlog/rate", {"slug": "installer", "stars": 4}, ip="10.0.0.%d" % i)
        pub = self.get("/devlog/public.json")["posts"]["installer"]
        self.assertEqual(pub, {"rating": 4.2, "ratings": 5})  # no read counts while they are private

    def test_stats_need_the_key(self):
        self.assertEqual(self.get("/devlog/stats.json"), 401)
        self.assertEqual(self.get("/devlog/stats.json", "wrong"), 401)

    def test_rate_limit(self):
        self.tearDown()
        self.setUp(limit=3)
        codes = [self.post("/devlog/read", {"slug": "installer"})[0] for _ in range(5)]
        self.assertEqual(codes, [200, 200, 200, 429, 429])

    def test_public_reads_switch(self):
        self.tearDown()
        self.setUp(public_reads=True)
        self.post("/devlog/read", {"slug": "installer"})
        self.assertEqual(self.get("/devlog/public.json")["posts"]["installer"], {"reads": 1})


if __name__ == "__main__":
    unittest.main()
