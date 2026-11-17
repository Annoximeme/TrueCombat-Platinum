# Cloudflare in front of truecombat.eu

Cloudflare (free plan) holds the DNS for truecombat.eu and serves the website through its network.

## What goes through Cloudflare

| Name | Proxied | Why |
|---|---|---|
| truecombat.eu, www | yes (orange) | the website: cached worldwide, DDoS and bot shielding, faster TLS |
| api | no (grey) | game servers, launcher, EOS login and webhooks are not browsers; no gain, real risk of challenges |
| master | no | UDP master server; Cloudflare's free proxy only carries web traffic |
| staff | no | small, logged-in audience; can be switched on later |
| mail (MX, SPF, DKIM, DMARC) | always DNS only | Zoho Mail |

The VPS address stays public through the grey names, so Cloudflare does not hide it. The gain is caching,
speed and shielding for the website itself.

The full desired zone is `records.json`. `cf_setup.py` makes Cloudflare match it.

## Workflow

`.github/workflows/cloudflare.yml`, needs the repository secret `CLOUDFLARE_API_TOKEN`:

- Run it by hand with mode `check` (report only), `apply` (make Cloudflare match `records.json`), or `purge`.
- It purges Cloudflare's cache by itself after every site change: it waits until the VPS serves the new
  files (asking the VPS directly), then empties the cache. HTML is never cached by Cloudflare anyway; this
  covers images, fonts, feeds and downloads that keep their name.

Token: Cloudflare > My Profile > API Tokens > Create Token > Custom token, zone `truecombat.eu` only,
permissions Zone Read, DNS Edit, Zone Settings Edit, Cache Purge, Bot Management Edit.

## Settings and why

See `_settings_why` in `records.json`. The important ones: SSL **Full (strict)**; **Always Use HTTPS off**
(Caddy redirects and sends HSTS itself, and the setting would stop Let's Encrypt renewals over port 80);
Email Obfuscation, Rocket Loader and Server-side Excludes **off** (they rewrite HTML and break the
per-page CSP); Browser Integrity Check and Bot Fight Mode **off** (they challenge non-browser clients
such as the launcher).

## Caching, DNSSEC and rules (also in records.json)

- **Page cache**: a cache rule caches every page of truecombat.eu at Cloudflare for 4 hours (errors never),
  except `/api/`, `/u/` and `/.well-known/`. The purge job empties the cache after every site change, so
  pages are fast everywhere and still current within about a minute.
- **Rate limit** (the free plan's one rule): more than 30 requests in 10 seconds from one address to
  `/api/account/` is blocked for 10 seconds.
- **Smart Tiered Cache** on; **DNSSEC** on (the DS record lives at Hostinger).
- Token also needs Zone Cache Rules Edit, Zone WAF Edit (rate limit) and DNS Settings for DNSSEC.

## VPS side

- `tools/website/deploy/install-cloudflare.sh`: Caddy trusts Cloudflare's ranges and passes the real visitor
  address on as X-Forwarded-For, so rate limits, insights and accounts see real visitors and not Cloudflare.
  Run `--ranges` now and then to refresh the list.
- `install-cloudflare.sh --lock-origin`: the website only serves Cloudflare (and the box itself); a direct
  visitor gets a redirect instead of content, so Cloudflare's shielding can't be bypassed. api, staff and the
  game servers are untouched. `--unlock-origin` undoes it.
- `tools/website/deploy/install-site-sync-fast.sh`: the VPS checks GitHub for site changes every 30 seconds.

## Rolling back

Point the nameservers at Hostinger again (aster.dns-parking.com, helios.dns-parking.com) after re-entering
the records there, or in Cloudflare switch the two orange records to grey: the site is then served
straight from the VPS again within minutes.
