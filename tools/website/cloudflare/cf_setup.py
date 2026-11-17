#!/usr/bin/env python3
"""Keep the truecombat.eu zone on Cloudflare in step with records.json.

  python cf_setup.py check            # show what differs, change nothing
  python cf_setup.py apply            # create/update records and settings
  python cf_setup.py apply --delete-extras   # also remove records not in records.json
  python cf_setup.py purge            # purge the whole Cloudflare cache

Needs CLOUDFLARE_API_TOKEN in the environment, a token limited to the truecombat.eu zone with:
Zone Read, DNS Edit, Zone Settings Edit, Cache Purge, Bot Management Edit.
Standard library only. Exit code 0 = in step (or applied), 1 = differences left, 2 = error.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.cloudflare.com/client/v4"
HERE = Path(__file__).resolve().parent
ADDRESS_TYPES = ("A", "AAAA", "CNAME")


class CfError(Exception):
    pass


def call(token, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": "tcp-site-tools"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            out = json.load(e)
        except ValueError:
            raise CfError("%s %s -> HTTP %d" % (method, path, e.code)) from None
    if not out.get("success"):
        raise CfError("%s %s -> %s" % (method, path, "; ".join(m.get("message", "?") for m in out.get("errors", [])) or "failed"))
    return out


def fqdn(name, zone):
    return zone if name in ("@", "", zone) else (name if name.endswith("." + zone) else name + "." + zone)


def unquote(s):
    s = (s or "").strip()
    # Cloudflare may hand back TXT content in quotes (and split long strings as "a" "b")
    if s.startswith('"') and s.endswith('"'):
        s = "".join(part for part in s[1:-1].split('" "'))
    return s


def norm_existing(r):
    t = r["type"]
    if t == "CAA":
        d = r.get("data") or {}
        if not d:
            f, tag, val = (r.get("content", "") + "  ").split(" ", 2)
            d = {"flags": int(f or 0), "tag": tag, "value": unquote(val.strip())}
        return (t, r["name"].lower(), "%d %s %s" % (int(d.get("flags", 0)), d.get("tag"), unquote(d.get("value"))))
    if t == "MX":
        return (t, r["name"].lower(), "%d %s" % (int(r.get("priority", 0)), r["content"].rstrip(".").lower()))
    if t == "TXT":
        return (t, r["name"].lower(), unquote(r["content"]))
    return (t, r["name"].lower(), r["content"].rstrip(".").lower())


def norm_wanted(w, zone):
    t, name = w["type"], fqdn(w["name"], zone)
    if t == "CAA":
        return (t, name, "%d %s %s" % (int(w.get("flags", 0)), w["tag"], w["value"]))
    if t == "MX":
        return (t, name, "%d %s" % (int(w["priority"]), w["content"].lower()))
    if t == "TXT":
        return (t, name, w["content"])
    return (t, name, w["content"].lower())


def body_for(w, zone):
    b = {"type": w["type"], "name": fqdn(w["name"], zone), "ttl": 1}
    if w["type"] == "CAA":
        b["data"] = {"flags": int(w.get("flags", 0)), "tag": w["tag"], "value": w["value"]}
    else:
        b["content"] = w["content"]
    if w["type"] == "MX":
        b["priority"] = int(w["priority"])
    if w["type"] in ADDRESS_TYPES:
        b["proxied"] = bool(w.get("proxied"))
    if w.get("why"):
        b["comment"] = w["why"][:100]
    return b


def plan(wanted, existing, zone):
    """Return (actions, extras). actions: ('create', body) | ('update', id, body, reason)."""
    left = list(existing)
    actions = []
    for w in wanted:
        key = norm_wanted(w, zone)
        hit = next((r for r in left if norm_existing(r) == key), None)
        if hit is None and w["type"] in ADDRESS_TYPES:
            # same name and type but another address: change it in place
            hit = next((r for r in left if r["type"] == w["type"] and r["name"].lower() == key[1]), None)
            if hit is not None:
                left.remove(hit)
                actions.append(("update", hit["id"], body_for(w, zone), "content %s -> %s" % (hit["content"], w["content"])))
                continue
        if hit is None:
            actions.append(("create", body_for(w, zone)))
            continue
        left.remove(hit)
        if w["type"] in ADDRESS_TYPES and bool(hit.get("proxied")) != bool(w.get("proxied")):
            actions.append(("update", hit["id"], body_for(w, zone),
                            "proxied %s -> %s" % (bool(hit.get("proxied")), bool(w.get("proxied")))))
    return actions, left


def describe(b):
    if b["type"] == "CAA":
        val = "%d %s %s" % (b["data"]["flags"], b["data"]["tag"], b["data"]["value"])
    elif b["type"] == "MX":
        val = "%d %s" % (b["priority"], b["content"])
    else:
        val = b["content"]
    px = "" if b["type"] not in ADDRESS_TYPES else ("  [proxied]" if b.get("proxied") else "  [DNS only]")
    return "%-5s %-24s %s%s" % (b["type"], b["name"], val, px)


def describe_existing(r):
    return "%-5s %-24s %s%s" % (r["type"], r["name"], norm_existing(r)[2],
                                ("  [proxied]" if r.get("proxied") else "  [DNS only]") if r["type"] in ADDRESS_TYPES else "")


def get_zone(token, name):
    zones = call(token, "GET", "/zones?name=" + name)["result"]
    if not zones:
        raise CfError("zone %s not found for this token (add the site in Cloudflare first)" % name)
    return zones[0]


def list_records(token, zid):
    out, page = [], 1
    while True:
        r = call(token, "GET", "/zones/%s/dns_records?per_page=500&page=%d" % (zid, page))
        out += r["result"]
        info = r.get("result_info") or {}
        if page >= int(info.get("total_pages") or 1):
            return out
        page += 1


def run(args):
    cfg = json.loads((HERE / "records.json").read_text(encoding="utf-8"))
    zone = cfg["zone"]
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        print("CLOUDFLARE_API_TOKEN is not set.")
        return 2
    z = get_zone(token, zone)
    zid = z["id"]
    print("Zone %s: status %s, plan %s" % (zone, z.get("status"), (z.get("plan") or {}).get("name")))
    print("Cloudflare nameservers: %s" % ", ".join(z.get("name_servers") or []))
    if z.get("original_name_servers"):
        print("Nameservers at the registrar when the site was added: %s" % ", ".join(z["original_name_servers"]))

    # what this token may do: report every missing permission at once instead of failing on the first
    probes = [("DNS (Zone > DNS > Edit)", "/zones/%s/dns_records?per_page=1" % zid),
              ("Zone Settings (Zone > Zone Settings > Edit)", "/zones/%s/settings/ssl" % zid),
              ("Bot Management (Zone > Bot Management > Edit)", "/zones/%s/bot_management" % zid)]
    missing = []
    for label, path in probes:
        try:
            call(token, "GET", path)
        except CfError as e:
            missing.append("%s: %s" % (label, str(e).split("-> ")[-1]))
    if missing:
        print("\nThe token cannot read:")
        for m in missing:
            print("  " + m)
        if args.cmd != "purge":
            print("Edit the token in Cloudflare (My Profile > API Tokens) and add these permissions for truecombat.eu.")
            return 2

    if args.cmd == "purge":
        call(token, "POST", "/zones/%s/purge_cache" % zid, {"purge_everything": True})
        print("Cache purged.")
        return 0

    apply = args.cmd == "apply"
    pending = 0
    actions, extras = plan(cfg["records"], list_records(token, zid), zone)
    print("\nDNS records")
    if apply and args.delete_extras:
        for r in extras:
            print("  deleting  %s" % describe_existing(r))
            call(token, "DELETE", "/zones/%s/dns_records/%s" % (zid, r["id"]))
    elif not apply:
        for r in extras:
            print("  extra     %s   (not in records.json)" % describe_existing(r))
            pending += 1
    else:
        for r in extras:
            print("  kept extra  %s   (not in records.json; use --delete-extras to remove)" % describe_existing(r))
    for a in actions:
        if a[0] == "create":
            print("  %s  %s" % ("creating" if apply else "missing ", describe(a[1])))
            if apply:
                call(token, "POST", "/zones/%s/dns_records" % zid, a[1])
        else:
            print("  %s  %s  (%s)" % ("updating" if apply else "differs ", describe(a[2]), a[3]))
            if apply:
                call(token, "PATCH", "/zones/%s/dns_records/%s" % (zid, a[1]), a[2])
        pending += 0 if apply else 1
    if not actions and not extras:
        print("  all %d records match" % len(cfg["records"]))

    print("\nSettings")
    if apply:
        try:   # new zones may start in automatic SSL mode, which would override our choice
            call(token, "PATCH", "/zones/%s/settings/ssl_automatic_mode" % zid, {"value": "custom"})
        except CfError as e:
            print("  note: ssl_automatic_mode: %s" % e)
    for key, want in cfg["settings"].items():
        try:
            have = call(token, "GET", "/zones/%s/settings/%s" % (zid, key))["result"].get("value")
        except CfError as e:
            print("  %-20s could not read (%s)" % (key, e))
            continue
        if have == want:
            print("  %-20s %s" % (key, have))
            continue
        if apply:
            try:
                call(token, "PATCH", "/zones/%s/settings/%s" % (zid, key), {"value": want})
                print("  %-20s %s -> %s" % (key, have, want))
            except CfError as e:
                print("  %-20s FAILED to set %s (%s)" % (key, want, e))
                pending += 1
        else:
            print("  %-20s %s (want %s)" % (key, have, want))
            pending += 1
    if "bot_fight_mode" in cfg:
        want = bool(cfg["bot_fight_mode"])
        try:
            have = bool(call(token, "GET", "/zones/%s/bot_management" % zid)["result"].get("fight_mode"))
            if have != want and apply:
                call(token, "PUT", "/zones/%s/bot_management" % zid, {"fight_mode": want})
                print("  %-20s %s -> %s" % ("bot_fight_mode", have, want))
            else:
                print("  %-20s %s%s" % ("bot_fight_mode", have, "" if have == want else " (want %s)" % want))
                pending += 0 if have == want else 1
        except CfError as e:
            print("  %-20s could not check (%s); set it off by hand: Security > Bots" % ("bot_fight_mode", e))
    pending += extras_section(token, zid, cfg, apply)
    print("\n%s" % ("Applied." if apply and not pending else "%d difference(s)." % pending if pending else "In step."))
    return 1 if pending else 0


def rule_key(r):
    keep = ("expression", "action", "action_parameters", "ratelimit", "enabled", "description")
    return json.dumps({k: r.get(k) for k in keep if r.get(k) is not None}, sort_keys=True)


def extras_section(token, zid, cfg, apply):
    """Smart Tiered Cache, DNSSEC and the rulesets (cache rules, rate limiting). Returns differences left."""
    pending = 0
    print("\nCaching, DNSSEC and rules")
    if "smart_tiered_cache" in cfg:
        want = "on" if cfg["smart_tiered_cache"] else "off"
        path = "/zones/%s/cache/tiered_cache_smart_topology_enable" % zid
        try:
            have = call(token, "GET", path)["result"].get("value")
            if have != want and apply:
                call(token, "PATCH", path, {"value": want})
                print("  %-20s %s -> %s" % ("smart_tiered_cache", have, want))
            else:
                print("  %-20s %s%s" % ("smart_tiered_cache", have, "" if have == want else " (want %s)" % want))
                pending += 0 if have == want else 1
        except CfError as e:
            print("  %-20s FAILED (%s)" % ("smart_tiered_cache", e))
            pending += 1
    if cfg.get("dnssec"):
        path = "/zones/%s/dnssec" % zid
        try:
            d = call(token, "GET", path)["result"]
            if d.get("status") in ("disabled", None) and apply:
                d = call(token, "PATCH", path, {"status": "active"})["result"]
                print("  %-20s disabled -> %s" % ("dnssec", d.get("status")))
            else:
                print("  %-20s %s" % ("dnssec", d.get("status")))
                pending += 1 if d.get("status") in ("disabled", None) else 0
            if d.get("ds"):
                print("  DS record for the registrar (Hostinger): %s" % d["ds"])
                print("    key tag %s, algorithm %s, digest type %s, digest %s" % (
                    d.get("key_tag"), d.get("algorithm"), d.get("digest_type"), d.get("digest")))
        except CfError as e:
            print("  %-20s FAILED (%s)" % ("dnssec", e))
            pending += 1
    for phase, rules in (cfg.get("rulesets") or {}).items():
        path = "/zones/%s/rulesets/phases/%s/entrypoint" % (zid, phase)
        try:
            have = call(token, "GET", path)["result"].get("rules") or []
        except CfError:
            have = []                       # no entrypoint yet
        same = sorted(rule_key(r) for r in have) == sorted(rule_key(r) for r in rules)
        if same:
            print("  %-20s %d rule(s) in step" % (phase, len(rules)))
            continue
        if not apply:
            print("  %-20s differs (%d rule(s) now, %d wanted)" % (phase, len(have), len(rules)))
            pending += 1
            continue
        try:
            call(token, "PUT", path, {"rules": rules})
            print("  %-20s set %d rule(s)" % (phase, len(rules)))
        except CfError as e:
            print("  %-20s FAILED (%s)" % (phase, e))
            pending += 1
    return pending


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("check", "apply", "purge"))
    ap.add_argument("--delete-extras", action="store_true")
    args = ap.parse_args()
    try:
        return run(args)
    except CfError as e:
        print("Cloudflare API error: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
