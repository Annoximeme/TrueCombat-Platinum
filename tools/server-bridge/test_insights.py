import gzip
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import tcp_insights

KEY = "studio-key"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/140.0"


class InsightsTest(unittest.TestCase):
    def setUp(self, limit=1000):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        for page in ("index", "download", "maps"):
            (root / (page + ".html")).write_text("x")
        (root / "nl").mkdir()
        (root / "nl" / "index.html").write_text("x")
        (root / "nl" / "maps.html").write_text("x")
        geo = root / "geo.csv.gz"
        with gzip.open(geo, "wt") as f:
            f.write("203.0.113.0,203.0.113.255,BE\n198.51.100.0,198.51.100.255,NL\n2001:db8::,2001:db8:ffff:ffff:ffff:ffff:ffff:ffff,DE\n")
        self.geo = tcp_insights.GeoIP(str(geo))
        self.store = tcp_insights.Store("")
        h = tcp_insights.make_handler(self.store, KEY, ["https://truecombat.eu"], self.tmp.name,
                                      tcp_insights.Limiter(60, limit), self.geo)
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), h)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def post(self, path, obj, ip="203.0.113.7", ua=UA, headers=None):
        hd = {"Content-Type": "text/plain", "X-Forwarded-For": ip, "User-Agent": ua}
        hd.update(headers or {})
        req = urllib.request.Request(self.base + path, json.dumps(obj).encode(), method="POST", headers=hd)
        try:
            r = urllib.request.urlopen(req, timeout=5)
            return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, None

    def hit(self, page, **kw):
        body = {"p": page, "l": kw.pop("l", "en"), "w": kw.pop("w", 1920)}
        for k in ("r", "s", "m", "c", "t", "d"):
            if k in kw:
                body[k] = kw.pop(k)
        return self.post("/insights/hit", body, **kw)

    def stats(self, key=KEY, days=30):
        req = urllib.request.Request(self.base + "/insights/stats.json?days=%d" % days, headers={"Authorization": "Bearer " + key} if key else {})
        try:
            return json.load(urllib.request.urlopen(req, timeout=5))
        except urllib.error.HTTPError as e:
            return e.code

    def by(self, rows):
        return {r["name"]: r for r in rows}

    def test_visitor_counted_once_per_day_views_every_time(self):
        self.hit("/")
        self.hit("/maps")
        self.hit("/maps")
        self.hit("/", ip="198.51.100.2")
        s = self.stats()
        self.assertEqual((s["totals"]["views"], s["totals"]["visitors"]), (4, 2))
        pages = self.by(s["pages"])
        self.assertEqual((pages["/maps"]["views"], pages["/maps"]["visitors"]), (2, 1))
        self.assertEqual(pages["/"]["visitors"], 2)

    def test_campaign_source_wins_and_download_is_credited(self):
        self.hit("/", s="reddit", m="social", c="launch", r="https://www.reddit.com/r/fps/")
        self.hit("/download")
        st, body = self.post("/insights/event", {"e": "download", "k": "installer", "p": "/download"})
        self.assertTrue(body["counted"])
        st, body = self.post("/insights/event", {"e": "download", "k": "installer", "p": "/download"})
        self.assertFalse(body["counted"])  # one download per visitor per day
        s = self.stats()
        src = self.by(s["sources"])["reddit"]
        self.assertEqual((src["visitors"], src["views"], src["downloads"]), (1, 2, 1))
        self.assertEqual(self.by(s["campaigns"])["reddit / social / launch"]["downloads"], 1)
        self.assertEqual(s["totals"]["downloads"], 1)
        self.assertEqual(self.by(s["download_kinds"])["installer"]["downloads"], 1)
        self.assertIn("reddit", s["source_series"])

    def test_referrer_maps_to_channel_and_own_site_is_direct(self):
        self.hit("/", r="https://old.reddit.com/r/oldschoolfps/comments/x")
        self.hit("/", r="https://www.moddb.com/mods/truecombat", ip="198.51.100.3")
        self.hit("/", r="https://truecombat.eu/maps", ip="198.51.100.4")
        self.hit("/", r="https://some-forum.example.org/thread?id=1", ip="198.51.100.5")
        s = self.by(self.stats()["sources"])
        for name in ("reddit", "moddb", "direct", "some-forum.example.org"):
            self.assertEqual(s[name]["visitors"], 1, name)
        refs = self.by(self.stats()["referrers"])
        self.assertNotIn("truecombat.eu", refs)
        self.assertIn("old.reddit.com", refs)  # host only, never the path

    def test_country_device_and_language(self):
        self.hit("/", w=390)
        self.hit("/nl/maps", ip="198.51.100.9", l="nl")
        self.hit("/", ip="2001:db8::5", w=800)
        s = self.stats()
        self.assertEqual(set(self.by(s["countries"])), {"BE", "NL", "DE"})
        self.assertEqual(set(self.by(s["devices"])), {"phone", "desktop", "tablet"})
        self.assertEqual(self.by(s["langs"])["nl"]["visitors"], 1)

    def test_privacy_signals_and_bots_are_not_counted(self):
        self.assertFalse(self.hit("/", headers={"Sec-GPC": "1"})[1]["counted"])
        self.assertFalse(self.hit("/", headers={"DNT": "1"})[1]["counted"])
        self.assertFalse(self.hit("/", ua="Googlebot/2.1")[1]["counted"])
        self.assertEqual(self.stats()["totals"]["views"], 0)

    def test_unknown_pages_and_bad_input_are_rejected(self):
        self.assertEqual(self.hit("/nope")[0], 404)
        self.assertEqual(self.hit("/../etc/passwd")[0], 404)
        self.assertEqual(self.post("/insights/event", {"e": "signup"})[0], 400)
        self.assertEqual(self.post("/insights/hit", ["x"])[0], 400)
        req = urllib.request.Request(self.base + "/insights/hit", b"x" * 5000, method="POST", headers={"User-Agent": UA})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(e.exception.code, 413)

    def test_bad_campaign_tags_are_dropped(self):
        self.hit("/", s="<script>", r="https://www.youtube.com/watch?v=1")
        self.assertIn("youtube", self.by(self.stats()["sources"]))

    def test_stats_need_the_key(self):
        self.assertEqual(self.stats(key=""), 401)
        self.assertEqual(self.stats(key="wrong"), 401)

    def test_nothing_identifying_is_stored(self):
        self.hit("/", r="https://www.reddit.com/r/fps/comments/hush", s="reddit")
        dump = "\n".join(self.store.db.iterdump())
        for needle in ("203.0.113.7", "Firefox", "hush", "/r/fps"):
            self.assertNotIn(needle, dump)

    def test_new_day_forgets_visitors(self):
        self.hit("/", s="reddit")
        self.store.day = "2000-01-01"
        self.store.db.execute("UPDATE secret SET day='2000-01-01'")
        self.store.roll()
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM visitor").fetchone()[0], 0)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM seen").fetchone()[0], 0)

    def test_value_cap_folds_into_other(self):
        old = tcp_insights.MAX_VALUES
        tcp_insights.MAX_VALUES = 3
        try:
            for i in range(6):
                self.hit("/", r="https://site%d.example.com/" % i, ip="198.51.100.%d" % (20 + i))
        finally:
            tcp_insights.MAX_VALUES = old
        names = set(self.by(self.stats()["sources"]))
        self.assertIn("(other)", names)
        self.assertLessEqual(len(names), 4)

    def test_rate_limit(self):
        self.tearDown()
        self.setUp(limit=3)
        codes = [self.hit("/")[0] for _ in range(5)]
        self.assertEqual(codes[-1], 429)

    def test_bare_host_referrer_and_device_class(self):
        self.hit("/", r="www.moddb.com", d="phone")
        s = self.stats()
        self.assertEqual(self.by(s["sources"])["moddb"]["visitors"], 1)
        self.assertEqual(self.by(s["devices"])["phone"]["visitors"], 1)

    def test_one_address_cannot_inflate_visitors_by_changing_browser(self):
        for i in range(tcp_insights.IP_VISITORS + 5):
            self.hit("/", ua=UA + " v%d" % i)
        self.assertEqual(self.stats()["totals"]["visitors"], tcp_insights.IP_VISITORS)
        self.assertTrue(self.hit("/", ip="198.51.100.77")[1]["counted"])  # other addresses still count

    def test_deleted_rows_are_zeroed(self):
        self.assertEqual(self.store.db.execute("PRAGMA secure_delete").fetchone()[0], 1)

    def test_github_counts(self):
        self.store.github({("v0.35.0-sandbox27", "TrueCombat-Platinum-Setup.exe"): 120})
        g = self.stats()["github"]
        self.assertEqual(g["releases"][0]["downloads"], 120)

    # ---- launcher reports ----
    REPORT = {"v": 1, "launcher": "2.6.0", "game": "0.38.0-sandbox34",
              "hw": {"os": "10.0.22631", "cpu": "AMD Ryzen 7 5800X3D 8-Core Processor", "threads": 16, "ram": 32,
                     "gpu": "NVIDIA GeForce RTX 4070", "vram": 12, "dx12": 1, "display": "2560x1440", "hz": 165, "lang": "nl"},
              "use": {"launches": 4, "safe": 1},
              "crashes": [{"program": "client", "kind": "unhandled exception", "code": "0xC0000005",
                           "at": "renderer_dx12_x64.dll+0x1A2B3", "frames": ["renderer_dx12_x64.dll+0x1a2b3", "platinum-engine.bin+0x4400"],
                           "up": 12, "game": "0.38.0-sandbox34"}]}

    def launcher(self, report=None, ip="203.0.113.7"):
        return self.post("/insights/launcher", report or self.REPORT, ip=ip, ua="TrueCombatPlatinumLauncher/2.6.0")

    def test_launcher_report_is_counted(self):
        code, body = self.launcher()
        self.assertEqual((code, body["counted"]), (200, True))
        lr = self.stats()["launcher"]
        self.assertEqual(lr["totals"]["launches"], 4)
        self.assertEqual(lr["totals"]["safe"], 1)
        self.assertEqual(lr["totals"]["crashes"], 1)
        v = lr["versions"][0]
        self.assertEqual((v["game"], v["crash_rate"]), ("0.38.0-sandbox34", 0.25))
        c = lr["crashes"][0]
        self.assertEqual((c["program"], c["code"], c["at"], c["count"]), ("client", "0xc0000005", "renderer_dx12_x64.dll+0x1a2b3", 1))
        self.assertEqual(c["gpuvendors"], {"NVIDIA": 1})
        hw = {d: {r["name"]: r["count"] for r in rows} for d, rows in lr["hardware"].items()}
        self.assertEqual(hw["cpu"], {"AMD Ryzen 7 5800X3D": 1})
        self.assertEqual(hw["os"], {"Windows 11 (22631)": 1})
        self.assertEqual(hw["ram"], {"32 GB or less": 1})
        self.assertEqual(hw["vram"], {"12 GB or less": 1})
        self.assertEqual(hw["country"], {"BE": 1})
        self.assertEqual(hw["display"], {"2560x1440": 1})
        self.assertEqual(lr["hardware_reports"], 1)

    def test_same_crash_twice_is_one_signature(self):
        self.launcher()
        self.launcher(ip="198.51.100.9")
        lr = self.stats()["launcher"]
        self.assertEqual(len(lr["crashes"]), 1)
        self.assertEqual(lr["crashes"][0]["count"], 2)

    def test_launcher_report_keeps_nothing_identifying(self):
        r = json.loads(json.dumps(self.REPORT))
        r["guid"] = "SECRETGUID"
        r["name"] = "RaziC"
        r["crashes"][0]["at"] = "C:\\Users\\gianni\\x.dll+0x10"
        self.launcher(r)
        dump = "\n".join(self.store.db.iterdump())
        for needle in ("203.0.113.7", "SECRETGUID", "RaziC", "Launcher/2.6.0"):
            self.assertNotIn(needle, dump)
        self.assertNotIn("Users", dump)   # a crash location that is a path is dropped, not stored

    def test_bad_launcher_reports_are_refused(self):
        self.assertEqual(self.launcher({"v": 2})[0], 400)
        self.assertEqual(self.launcher({"v": 1, "game": "0.38.0"})[0], 400)
        bad = {"v": 1, "game": "0.38.0", "crashes": [{"code": "boom", "at": "x"}]}
        self.assertEqual(self.launcher(bad)[0], 400)
        big = {"v": 1, "game": "0.38.0", "pad": "x" * 7000}
        self.assertEqual(self.launcher(big)[0], 413)

    def test_launcher_daily_cap_per_address(self):
        for _ in range(tcp_insights.LAUNCHER_PER_IP):
            self.assertTrue(self.launcher()[1]["counted"])
        self.assertFalse(self.launcher()[1]["counted"])
        self.assertTrue(self.launcher(ip="198.51.100.4")[1]["counted"])

    def test_launcher_retention(self):
        self.launcher()
        self.store.db.execute("UPDATE luse SET day='2000-01-01'")
        self.store.db.execute("UPDATE lcrashday SET day='2000-01-01'")
        self.store.db.execute("UPDATE lcrash SET last_day='2000-01-01'")
        self.store.db.execute("UPDATE lhw SET month='2000-01'")
        self.store.day = "2000-01-01"
        self.store.db.execute("UPDATE secret SET day='2000-01-01'")
        self.store.roll()
        for t in ("luse", "lcrashday", "lcrash", "lhw"):
            self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0], 0, t)

    def test_usage_only_report(self):
        code, body = self.launcher({"v": 1, "launcher": "2.6.0", "game": "0.38.0", "use": {"launches": 2, "safe": 0}, "gpu": "AMD Radeon RX 7800 XT"})
        self.assertEqual(code, 200)
        lr = self.stats()["launcher"]
        self.assertEqual(lr["totals"]["launches"], 2)
        self.assertEqual(lr["hardware"], {})


if __name__ == "__main__":
    unittest.main()
