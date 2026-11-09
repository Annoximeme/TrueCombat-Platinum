#!/bin/sh
# Installs the Ko-fi donation ledger next to the stats bridge on the VPS.
# Usage (from a checkout of the repo, on the VPS):
#   printf '%s' 'KOFI-VERIFICATION-TOKEN' | sudo sh tools/server-bridge/deploy/install-kofi.sh --token-stdin
# Then add the two Caddy routes printed at the end and reload Caddy.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/.."
[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }
id tcpsvc >/dev/null 2>&1 || { echo "user tcpsvc missing (stats bridge not installed?)"; exit 1; }
install -d -m 0755 /opt/tcp/server-bridge
install -m 0644 "$SRC/tcp_kofi.py" /opt/tcp/server-bridge/tcp_kofi.py
install -d -m 0750 -o root -g root /etc/tcp-kofi
if [ "${1:-}" = "--token-stdin" ]; then
  umask 077; cat > /etc/tcp-kofi/token; chmod 0600 /etc/tcp-kofi/token
fi
[ -s /etc/tcp-kofi/token ] || { echo "no token yet: pipe it in with --token-stdin"; exit 1; }
install -m 0644 "$HERE/tcp-kofi.service" /etc/systemd/system/tcp-kofi.service
systemctl daemon-reload
systemctl enable --now tcp-kofi.service
sleep 1
curl -fsS http://127.0.0.1:8091/kofi/health && echo
cat <<'TXT'

Add inside the api.truecombat.eu site block in /etc/caddy/Caddyfile, above the bridge proxy:

	handle /kofi/* {
		reverse_proxy 127.0.0.1:8091
	}
	handle /funding.json {
		reverse_proxy 127.0.0.1:8091
	}

then: sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
Ko-fi > Settings > API > Webhook URL: https://api.truecombat.eu/kofi/webhook
TXT
