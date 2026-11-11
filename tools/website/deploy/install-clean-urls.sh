#!/bin/sh
# Turns on addresses without .html for truecombat.eu (run on the VPS with sudo rights).
#   sh install-clean-urls.sh            install, validate, reload, smoke test
#   sh install-clean-urls.sh --undo     restore the Caddyfile from before the install
# The site files need no change on the server: the next site sync brings the new links.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
CADDYFILE=/etc/caddy/Caddyfile
SNIPPET=/etc/caddy/clean-urls.caddy
BACKUP=/etc/caddy/Caddyfile.before-clean-urls
LINE="import $SNIPPET"

if [ "${1:-}" = "--undo" ]; then
	[ -f "$BACKUP" ] || { echo "no backup at $BACKUP"; exit 1; }
	sudo cp "$BACKUP" "$CADDYFILE"
	sudo caddy validate --config "$CADDYFILE" --adapter caddyfile
	sudo systemctl reload caddy
	echo "restored $CADDYFILE from $BACKUP"
	exit 0
fi

sudo install -m 0644 "$HERE/clean-urls.caddy" "$SNIPPET"
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
		"$2 $3"*) echo "ok   $1 -> $got" ;;
		*) echo "FAIL $1 -> $got (wanted $2 $3)"; fail=1 ;;
	esac
}
S=https://truecombat.eu
check "$S/" 200
check "$S/maps" 200
check "$S/de/maps" 200
check "$S/de/" 200
check "$S/press" 200
check "$S/press/truecombat-platinum-press-kit.zip" 200
check "$S/style.css" 200
check "$S/maps.html" 301 "$S/maps"
check "$S/index.html" 301 "$S/"
check "$S/de/index.html" 301 "$S/de/"
check "$S/player.html?id=x" 301 "$S/player?id=x"
check "$S/no-such-page" 404
check "https://api.truecombat.eu/funding.json" 200
[ "$fail" = 0 ] && echo "clean URLs are live" || { echo "some checks failed: run 'sh $0 --undo' to go back"; exit 1; }
