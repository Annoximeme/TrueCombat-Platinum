#!/bin/sh
# Prepares Caddy on the VPS for Cloudflare in front of truecombat.eu (run with sudo rights).
#   sh install-cloudflare.sh            install, validate, reload, smoke test
#   sh install-cloudflare.sh --ranges   only refresh Cloudflare's address list (safe to run from a timer)
#   sh install-cloudflare.sh --undo     restore the Caddyfile from before the install
#   sh install-cloudflare.sh --lock-origin     the website (truecombat.eu, www) serves only Cloudflare and this box;
#                                              anyone else who connects straight to the VPS gets a redirect, no content
#   sh install-cloudflare.sh --unlock-origin   undo --lock-origin
#
# What it changes, and why:
#  1. /etc/caddy/cloudflare-ips.caddy: Cloudflare's published address ranges as trusted proxies, and
#     CF-Connecting-IP as the client address header. Only requests that really come from those ranges
#     are believed; anyone talking to the VPS directly keeps their own address.
#  2. every reverse_proxy passes the real visitor address to the services as X-Forwarded-For
#     ({client_ip}). The services (accounts, insights, devlog, staff portal) rate-limit and count by
#     that address; without this they would see a handful of Cloudflare addresses for everyone.
# Safe before the nameserver move: with no Cloudflare traffic nothing behaves differently.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
CADDYFILE=/etc/caddy/Caddyfile
SNIPPET=/etc/caddy/cloudflare-ips.caddy
LOCK=/etc/caddy/cloudflare-only.caddy
LOCKLINE="import $LOCK"
BACKUP=/etc/caddy/Caddyfile.before-cloudflare
LINE="import $SNIPPET"

reload() {
	if ! sudo caddy validate --config "$CADDYFILE" --adapter caddyfile >/dev/null; then
		return 1
	fi
	sudo systemctl reload caddy
}

write_ranges() {
	tmp=$(mktemp)
	v4=$(curl -fsS --max-time 20 https://www.cloudflare.com/ips-v4 || true)
	v6=$(curl -fsS --max-time 20 https://www.cloudflare.com/ips-v6 || true)
	if echo "$v4" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$' && echo "$v6" | grep -qE '^[0-9a-f:]+/[0-9]+$'; then
		ranges=$(printf '%s\n%s\n' "$v4" "$v6" | grep -E '^[0-9a-f.:]+/[0-9]+$' | tr '\n' ' ')
		src="cloudflare.com/ips-v4 + ips-v6, fetched $(date -u +%Y-%m-%dT%H:%MZ)"
	else
		ranges=$(grep -E '^[0-9a-f.:]+/[0-9]+$' "$HERE/cloudflare-ips.txt" | tr '\n' ' ')
		src="fallback list in the repo (cloudflare.com could not be reached)"
	fi
	# the origin lock snippet always follows the same list (harmless while no site block imports it)
	{
		echo "# Website answers only Cloudflare ($src) and this box. Written by install-cloudflare.sh --lock-origin."
		echo "@tcp_not_cloudflare not remote_ip $ranges 127.0.0.1/8 ::1"
		# redir, not abort: Caddy runs redir before handle and file_server, while abort would come after handle
		# (so /api/account/* would slip past it). A direct visitor is sent to the real address, via Cloudflare.
		echo "redir @tcp_not_cloudflare https://truecombat.eu{uri} 308"
	} | sudo tee "$LOCK.new" >/dev/null
	sudo mv "$LOCK.new" "$LOCK"
	{
		echo "# Cloudflare address ranges ($src). Written by install-cloudflare.sh; imported in the global servers block."
		echo "trusted_proxies static $ranges"
		echo "client_ip_headers CF-Connecting-IP"
	} >"$tmp"
	if [ -f "$SNIPPET" ] && cmp -s "$tmp" "$SNIPPET"; then rm -f "$tmp"; echo "ranges unchanged"; return 1; fi
	if [ -f "$SNIPPET" ] && [ "$(sed 1d "$tmp")" = "$(sed 1d "$SNIPPET")" ]; then rm -f "$tmp"; echo "ranges unchanged"; return 1; fi
	sudo install -m 0644 "$tmp" "$SNIPPET.new"
	rm -f "$tmp"
	[ -f "$SNIPPET" ] && sudo cp "$SNIPPET" "$SNIPPET.old"
	sudo mv "$SNIPPET.new" "$SNIPPET"
	echo "wrote $SNIPPET from $src"
	return 0
}

if [ "${1:-}" = "--undo" ]; then
	[ -f "$BACKUP" ] || { echo "no backup at $BACKUP"; exit 1; }
	sudo cp "$BACKUP" "$CADDYFILE"
	reload
	echo "restored $CADDYFILE from $BACKUP ($SNIPPET left in place, unused)"
	exit 0
fi

if [ "${1:-}" = "--lock-origin" ] || [ "${1:-}" = "--unlock-origin" ]; then
	write_ranges || true
	LBACKUP=/etc/caddy/Caddyfile.before-origin-lock
	[ "$1" = "--lock-origin" ] && sudo cp "$CADDYFILE" "$LBACKUP"
	sudo python3 - "$CADDYFILE" "$LOCKLINE" "$1" <<'PY'
import re, sys
path, line, mode = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path).read()
if mode == "--unlock-origin":
    text, n = re.subn(r'(?m)^[ \t]*' + re.escape(line) + r'[ \t]*\n', "", text)
    open(path, "w").write(text); print("removed %d import line(s)" % n); sys.exit(0)
n = 0
for host in (r"truecombat\.eu", r"www\.truecombat\.eu"):
    m = re.search(r'(?m)^(?:https://)?' + host + r'(?::443)?\s*\{[ \t]*\n', text)
    if not m:
        sys.exit("no site block for %s; nothing changed" % host)
    block_start = m.end()
    if line in text[block_start:block_start + 200]:
        continue
    text = text[:block_start] + "\t" + line + "\n" + text[block_start:]
    n += 1
open(path, "w").write(text); print("origin lock added to %d site block(s)" % n)
PY
	if ! reload; then
		echo "validation failed, restoring the old Caddyfile"
		[ "$1" = "--lock-origin" ] && sudo cp "$LBACKUP" "$CADDYFILE"
		exit 1
	fi
	sleep 2
	echo "from this box (allowed): $(curl -s -o /dev/null -w '%{http_code}' --resolve truecombat.eu:443:127.0.0.1 https://truecombat.eu/)"
	pub=$(curl -s -4 --max-time 10 https://api.ipify.org || echo 2.24.59.195)
	echo "via the public address (308 = locked, 200 = open): $(curl -s -o /dev/null -w '%{http_code}' --max-time 10 --resolve truecombat.eu:443:$pub https://truecombat.eu/ || true)"
	echo "api still direct: $(curl -s -o /dev/null -w '%{http_code}' --max-time 10 --resolve api.truecombat.eu:443:$pub https://api.truecombat.eu/funding.json)"
	exit 0
fi

if [ "${1:-}" = "--ranges" ]; then
	if write_ranges; then
		if ! reload; then
			echo "validation failed, restoring the old ranges"
			[ -f "$SNIPPET.old" ] && sudo cp "$SNIPPET.old" "$SNIPPET"
			exit 1
		fi
		echo "Caddy reloaded with the new ranges"
	fi
	exit 0
fi

write_ranges || true
[ -f "$BACKUP" ] || sudo cp "$CADDYFILE" "$BACKUP"
sudo python3 - "$CADDYFILE" "$LINE" <<'PY'
import re, sys
path, line = sys.argv[1], sys.argv[2]
text = open(path).read()
changed = False
if line not in text:
    m = re.search(r'(?m)^([ \t]*)strict_sni_host on[ \t]*\n', text)
    if not m:
        sys.exit("no 'strict_sni_host on' line in the global servers block of %s; nothing changed" % path)
    text = text[:m.end()] + m.group(1) + line + "\n" + text[m.end():]
    changed = True
# one-line "reverse_proxy <upstream>" -> block that passes the real visitor address
def block(m):
    ind, up = m.group(1), m.group(2)
    return "%sreverse_proxy %s {\n%s\theader_up X-Forwarded-For {client_ip}\n%s}\n" % (ind, up, ind, ind)
text, n = re.subn(r'(?m)^([ \t]*)reverse_proxy[ \t]+(\S+)[ \t]*\n', block, text)
left = re.findall(r'(?m)^[ \t]*reverse_proxy\b.*\{[ \t]*$', text)
missing = [l for l in left if "header_up X-Forwarded-For" not in text[text.index(l):text.index(l) + 300]]
if missing:
    sys.exit("reverse_proxy blocks that need a header_up line by hand: %r; nothing changed" % missing)
if changed or n:
    open(path, "w").write(text)
print("import line %s, %d reverse_proxy line(s) converted" % ("added" if changed else "already there", n))
PY

if ! reload; then
	echo "validation failed, restoring the old Caddyfile"
	sudo cp "$BACKUP" "$CADDYFILE"
	exit 1
fi
sleep 2

fail=0
check() { # resolve-spec, url: any 2xx/3xx answer counts (no 5xx, no connection error)
	got=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 --resolve "$1" "$2" 2>/dev/null || true)
	case "$got" in
		2??|3??) echo "ok   $2 -> $got" ;;
		*) echo "FAIL $2 -> $got"; fail=1 ;;
	esac
}
# straight to this box, past any DNS or Cloudflare
check truecombat.eu:443:127.0.0.1 https://truecombat.eu/
check truecombat.eu:443:127.0.0.1 https://truecombat.eu/style.css
check www.truecombat.eu:443:127.0.0.1 https://www.truecombat.eu/
check api.truecombat.eu:443:127.0.0.1 https://api.truecombat.eu/funding.json
check staff.truecombat.eu:443:127.0.0.1 https://staff.truecombat.eu/
[ "$fail" = 0 ] && echo "All checks passed." || { echo "Some checks failed: look before anything else (undo: sh $0 --undo)"; exit 1; }
