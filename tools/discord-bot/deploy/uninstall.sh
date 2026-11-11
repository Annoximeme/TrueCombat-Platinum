#!/bin/sh
# Removes the Discord bot service and code. Config, token and state are kept
# unless --purge is given, so a reinstall picks up where it left off.
#   sudo ./deploy/uninstall.sh [--purge]
set -eu
[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }
systemctl disable --now tcp-discord-bot.service 2>/dev/null || true
rm -f /etc/systemd/system/tcp-discord-bot.service
systemctl daemon-reload
rm -rf /opt/tcp/discord-bot
if [ "${1:-}" = "--purge" ]; then
  rm -rf /etc/tcp-discord-bot /var/lib/tcp-discord-bot /var/lib/private/tcp-discord-bot
  userdel tcpbot 2>/dev/null || true
  echo "Removed everything, including the token and the bot's database."
else
  echo "Removed the service and code. Kept /etc/tcp-discord-bot (config, token) and /var/lib/tcp-discord-bot (links, events)."
fi
echo "The old webhook feed, if you retired it, can be turned back on with: systemctl enable --now tcp-status.timer"
