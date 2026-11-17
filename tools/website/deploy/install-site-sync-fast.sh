#!/bin/sh
# Makes the VPS pick up website changes from GitHub every 30 seconds instead of every 2 minutes.
#   sh install-site-sync-fast.sh          install the timer override and show the next runs
#   sh install-site-sync-fast.sh --undo   remove the override (back to the original timer)
# A sync with nothing new is one small git fetch, so the extra runs cost next to nothing.
# Together with the "purge" job in .github/workflows/cloudflare.yml a merged site change is
# live for visitors about a minute later.
set -eu
DROPIN=/etc/systemd/system/tcp-site-sync.timer.d/10-fast.conf
if [ "${1:-}" = "--undo" ]; then
	sudo rm -f "$DROPIN"
	sudo systemctl daemon-reload
	sudo systemctl restart tcp-site-sync.timer
	systemctl list-timers tcp-site-sync.timer --no-pager
	exit 0
fi
systemctl cat tcp-site-sync.timer >/dev/null || { echo "tcp-site-sync.timer not found; nothing changed"; exit 1; }
sudo mkdir -p "$(dirname "$DROPIN")"
printf '%s\n' '[Timer]' '# empty lines clear the original schedule' 'OnCalendar=' 'OnUnitActiveSec=' \
	'OnActiveSec=5s' 'OnBootSec=1min' 'OnUnitActiveSec=30s' 'AccuracySec=1s' | sudo tee "$DROPIN" >/dev/null
sudo systemctl daemon-reload
sudo systemctl restart tcp-site-sync.timer
sleep 1
systemctl list-timers tcp-site-sync.timer --no-pager
