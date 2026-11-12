#!/bin/sh
# Installs the website insights service next to the stats bridge on the VPS.
# Usage (from a checkout of the repo, on the VPS):
#   sudo sh tools/server-bridge/deploy/install-insights.sh            install or update
#   sudo sh tools/server-bridge/deploy/install-insights.sh --undo     stop and remove it (keeps the data)
# The first run creates the studio key for the staff portal's Insights page and stores it in
# /etc/tcp-insights/key (root only). Then add the Caddy route printed at the end and reload Caddy.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/.."
[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }
if [ "${1:-}" = "--undo" ]; then
  systemctl disable --now tcp-insights.service tcp-insights-geoip.timer 2>/dev/null || true
  rm -f /etc/systemd/system/tcp-insights.service /etc/systemd/system/tcp-insights-geoip.service /etc/systemd/system/tcp-insights-geoip.timer
  systemctl daemon-reload
  echo "tcp-insights removed. Data kept in /var/lib/tcp-insights. Remove the handle /insights/* block from the Caddyfile and reload Caddy."
  exit 0
fi
id tcpsvc >/dev/null 2>&1 || { echo "user tcpsvc missing (stats bridge not installed?)"; exit 1; }
install -d -m 0755 /opt/tcp/server-bridge
install -m 0644 "$SRC/tcp_insights.py" /opt/tcp/server-bridge/tcp_insights.py
install -m 0755 "$HERE/insights-geoip.sh" /opt/tcp/server-bridge/insights-geoip.sh
install -d -m 0750 -o root -g root /etc/tcp-insights
if [ ! -s /etc/tcp-insights/key ]; then
  umask 077
  python3 /opt/tcp/server-bridge/tcp_insights.py new-key > /etc/tcp-insights/key
  chmod 0600 /etc/tcp-insights/key
  echo "Created the studio key in /etc/tcp-insights/key (the staff portal reads it from there)."
fi
for u in tcp-insights.service tcp-insights-geoip.service tcp-insights-geoip.timer; do
  install -m 0644 "$HERE/$u" /etc/systemd/system/$u
done
systemctl daemon-reload
install -d -m 0750 -o tcpsvc -g tcpsvc /var/lib/tcp-insights
[ -s /var/lib/tcp-insights/geo.csv.gz ] || systemctl start tcp-insights-geoip.service || echo "country list not loaded yet; countries show as ?? until it is"
systemctl enable --now tcp-insights.service tcp-insights-geoip.timer
systemctl restart tcp-insights.service
sleep 1
curl -fsS http://127.0.0.1:8093/insights/health && echo
cat <<'TXT'

Add inside the api.truecombat.eu site block in /etc/caddy/Caddyfile, above the bridge proxy:

	handle /insights/* {
		reverse_proxy 127.0.0.1:8093
	}

then: sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
TXT
