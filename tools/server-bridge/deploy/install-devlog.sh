#!/bin/sh
# Installs the devlog reads and ratings service next to the stats bridge on the VPS.
# Usage (from a checkout of the repo, on the VPS):
#   sudo sh tools/server-bridge/deploy/install-devlog.sh
# The first run creates the studio key for truecombat.eu/devlog-stats.html and prints it once.
# Then add the Caddy route printed at the end and reload Caddy.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/.."
[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }
id tcpsvc >/dev/null 2>&1 || { echo "user tcpsvc missing (stats bridge not installed?)"; exit 1; }
install -d -m 0755 /opt/tcp/server-bridge
install -m 0644 "$SRC/tcp_devlog.py" /opt/tcp/server-bridge/tcp_devlog.py
install -d -m 0750 -o root -g root /etc/tcp-devlog
if [ ! -s /etc/tcp-devlog/key ]; then
  umask 077
  python3 /opt/tcp/server-bridge/tcp_devlog.py new-key > /etc/tcp-devlog/key
  chmod 0600 /etc/tcp-devlog/key
  echo "Studio key for truecombat.eu/devlog-stats.html (keep it private):"
  cat /etc/tcp-devlog/key
fi
install -m 0644 "$HERE/tcp-devlog.service" /etc/systemd/system/tcp-devlog.service
systemctl daemon-reload
systemctl enable --now tcp-devlog.service
systemctl restart tcp-devlog.service
sleep 1
curl -fsS http://127.0.0.1:8092/devlog/health && echo
cat <<'TXT'

Add inside the api.truecombat.eu site block in /etc/caddy/Caddyfile, above the bridge proxy:

	handle /devlog/* {
		reverse_proxy 127.0.0.1:8092
	}

then: sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
TXT
