#!/bin/sh
# Adds security and caching headers to truecombat.eu (run on the VPS with sudo rights).
#   sh install-headers.sh            install, validate, reload, smoke test
#   sh install-headers.sh --undo     restore the Caddyfile from before the install
# The site files need no change on the server: the next site sync brings the new links.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
CADDYFILE=/etc/caddy/Caddyfile
SNIPPET=/etc/caddy/security-headers.caddy
BACKUP=/etc/caddy/Caddyfile.before-headers
LINE="import $SNIPPET"

if [ "${1:-}" = "--undo" ]; then
	[ -f "$BACKUP" ] || { echo "no backup at $BACKUP"; exit 1; }
	sudo cp "$BACKUP" "$CADDYFILE"
	sudo caddy validate --config "$CADDYFILE" --adapter caddyfile
	sudo systemctl reload caddy
	echo "restored $CADDYFILE from $BACKUP"
	exit 0
fi

sudo install -m 0644 "$HERE/security-headers.caddy" "$SNIPPET"
if grep -qF "$LINE" "$CADDYFILE"; then
	echo "Caddyfile already imports $SNIPPET"
else
	[ -f "$BACKUP" ] || sudo cp "$CADDYFILE" "$BACKUP"
	# insert the import as the first line of the truecombat.eu site block (not www, not api)
	sudo python3 - "$CADDYFILE" "$LINE" <<'PY'
import re, sys
path, line = sys.argv[1], sys.argv[2]
text = open(path).read()
m = re.search(r'(?m)^(?:https://)?truecombat\.eu(?::443)?\s*\{[ \t]*\n', text)
if not m:
    sys.exit("no 'truecombat.eu {' site block found in %s; nothing changed" % path)
open(path, "w").write(text[:m.end()] + "\t" + line + "\n" + text[m.end():])
PY
fi

if ! sudo caddy validate --config "$CADDYFILE" --adapter caddyfile; then
	echo "validation failed, restoring the old Caddyfile"
	sudo cp "$BACKUP" "$CADDYFILE"
	exit 1
fi
sudo systemctl reload caddy
sleep 2

fail=0
check() { # url, expected status, expected Location (optional)
	got=$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' "$1")
	case "$got" in
		"$2 ${3:-}"*) echo "ok   $1 -> $got" ;;
		*) echo "FAIL $1 -> $got (wanted $2 ${3:-})"; fail=1 ;;
	esac
}
S=https://truecombat.eu
check "$S/" 200
check "$S/maps" 200
check "$S/de/" 200
check "$S/maps.html" 301 "$S/maps"
check "$S/style.css" 200
check "https://api.truecombat.eu/servers.json" 200
hdr() { # url, header name, expected text
	if curl -sI "$1" | tr -d '\r' | grep -i "^$2:" | grep -qF "$3"; then echo "ok   $1 has $2"; else echo "FAIL $1 lacks $2: $3"; fail=1; fi
}
hdr "$S/" Content-Security-Policy "frame-ancestors 'none'"
hdr "$S/" X-Frame-Options DENY
hdr "$S/" Permissions-Policy "camera=()"
F=$(curl -s "$S/style.css" | grep -o "fonts/[^)\"']*\.woff2" | head -1)
[ -n "$F" ] && hdr "$S/$F" Cache-Control "max-age=2592000"
[ "$fail" = 0 ] && echo "headers are live" || { echo "some checks failed: run 'sh $0 --undo' to go back"; exit 1; }
