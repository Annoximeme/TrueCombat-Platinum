"""Offline tests for cf_setup.plan(): python -m unittest tools/website/cloudflare/test_cf_setup.py"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cf_setup  # noqa: E402

Z = "truecombat.eu"
CFG = json.loads((Path(__file__).resolve().parent / "records.json").read_text(encoding="utf-8"))


def rec(i, t, name, content="", **kw):
    r = {"id": "r%d" % i, "type": t, "name": name, "content": content}
    r.update(kw)
    return r


class PlanTests(unittest.TestCase):
    def test_empty_zone_creates_everything(self):
        actions, extras = cf_setup.plan(CFG["records"], [], Z)
        self.assertEqual(len(actions), len(CFG["records"]))
        self.assertTrue(all(a[0] == "create" for a in actions))
        self.assertEqual(extras, [])

    def test_quick_scan_import_is_reconciled(self):
        # what Cloudflare's scan typically imports from Hostinger: all grey, TXT quoted
        existing = [
            rec(1, "A", Z, "2.24.59.195", proxied=False),
            rec(2, "CNAME", "www." + Z, "truecombat.eu", proxied=False),
            rec(3, "A", "api." + Z, "2.24.59.195", proxied=False),
            rec(4, "TXT", Z, '"zoho-verification=zb76464286.zmverify.zoho.eu"'),
            rec(5, "A", "ftp." + Z, "2.24.59.195", proxied=False),
        ]
        actions, extras = cf_setup.plan(CFG["records"], existing, Z)
        updates = {a[1]: a[3] for a in actions if a[0] == "update"}
        self.assertEqual(set(updates), {"r1", "r2"})               # website goes orange
        self.assertIn("proxied False -> True", updates["r1"])
        self.assertEqual([r["id"] for r in extras], ["r5"])        # unknown name reported, not touched
        created = [a[1] for a in actions if a[0] == "create"]
        self.assertFalse(any(b["type"] == "TXT" and "zoho-verification" in b["content"] for b in created))

    def test_everything_in_step(self):
        existing = []
        for i, w in enumerate(CFG["records"]):
            b = cf_setup.body_for(w, Z)
            r = {"id": "r%d" % i, "type": b["type"], "name": b["name"], "content": b.get("content", ""),
                 "proxied": b.get("proxied", False)}
            if "priority" in b:
                r["priority"] = b["priority"]
            if "data" in b:
                r["data"] = b["data"]
                r["content"] = '%d %s "%s"' % (b["data"]["flags"], b["data"]["tag"], b["data"]["value"])
            existing.append(r)
        self.assertEqual(cf_setup.plan(CFG["records"], existing, Z), ([], []))

    def test_changed_address_is_updated_in_place(self):
        existing = [rec(1, "A", "api." + Z, "1.2.3.4", proxied=False)]
        actions, extras = cf_setup.plan([w for w in CFG["records"] if w["name"] == "api"], existing, Z)
        self.assertEqual(actions[0][0], "update")
        self.assertEqual(actions[0][2]["content"], "2.24.59.195")
        self.assertEqual(extras, [])

    def test_caa_from_content_only(self):
        r = rec(1, "CAA", Z, '0 issue "letsencrypt.org"')
        self.assertEqual(cf_setup.norm_existing(r), ("CAA", Z, "0 issue letsencrypt.org"))

    def test_only_website_is_proxied(self):
        proxied = {(w["type"], w["name"]) for w in CFG["records"] if w.get("proxied")}
        self.assertEqual(proxied, {("A", "@"), ("CNAME", "www")})
        for w in CFG["records"]:
            if w["name"] in ("master", "api", "staff"):
                self.assertFalse(w.get("proxied"), w)

    def test_settings_keep_caddy_working(self):
        s = CFG["settings"]
        self.assertEqual(s["ssl"], "strict")
        self.assertEqual(s["always_use_https"], "off")
        for k in ("email_obfuscation", "rocket_loader", "server_side_exclude"):
            self.assertEqual(s[k], "off")


if __name__ == "__main__":
    unittest.main()
