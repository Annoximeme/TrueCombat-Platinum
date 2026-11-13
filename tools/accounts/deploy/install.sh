#!/bin/sh
# Installs or updates the player account service on the VPS. Run as root from the unpacked tools/accounts folder.
#
#   sudo ./deploy/install.sh inspect       read-only: what is there, what would change, is the port free
#   sudo ./deploy/install.sh install       code, user, service, credentials (not Caddy, not the stats link)
#   sudo ./deploy/install.sh stats-link    token + tcp-bridge drop-in so linked PCs merge in the stats (restarts tcp-bridge)
#   sudo ./deploy/install.sh caddy         adds /api/account/* and /u/<name> to the truecombat.eu block (backup + validate + reload)
#   sudo ./deploy/install.sh uninstall     stops and removes the service (keeps data and config)
#
# Before install: the Discord OAuth client secret goes in /etc/tcp-accounts/client-secret (one line). It is the
# same TrueCombat Discord app the staff portal uses; install copies the portal's secret when that file is missing.
# The stats service must already carry the accounts change (tcp_stats.py: learned keys, aliases, the
# /staff/accounts/aliases route). The VPS stats code is NOT a main checkout: patch those hunks, never copy main over it.
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
APP=/opt/tcp/accounts
ETC=/etc/tcp-accounts
DATA=/var/lib/tcp-accounts
UNIT=tcp-accounts.service
PORT=8095
HOMES="/var/lib/tcpgame/home /var/lib/tcpgame/home-unranked /var/lib/tcpgame/home-pickup1 /var/lib/tcpgame/home-pickup2"
MODE=${1:-inspect}

say() { printf '%s\n' "$*"; }
filled() { [ -f "$1" ] && grep -q '[^[:space:]]' "$1"; }
need_root() { [ "$(id -u)" = 0 ] || { say "run as root (sudo)"; exit 1; }; }
port_user() { ss -ltnpH "sport = :$PORT" 2>/dev/null | sed -n 's/.*users:((\("[^"]*"\).*/\1/p' | head -n 1; }

inspect() {
  say "== player accounts: inspect (read-only)"
  say "code:    $APP $( [ -f $APP/tcp_accounts.py ] && sed -n 's/^VERSION = "\(.*\)"/version \1/p' $APP/tcp_accounts.py || echo '(not installed)')"
  say "new:     $(sed -n 's/^VERSION = "\(.*\)"/version \1/p' "$HERE/tcp_accounts.py")"
  say "user:    $(id tcpaccounts 2>/dev/null || echo 'tcpaccounts (will be created)')"
  say "config:  $( [ -f $ETC/config.json ] && echo present || echo 'missing (created from the example)')"
  say "secret:  $( filled $ETC/client-secret && echo present || (filled /etc/tcp-staff-portal/client-secret && echo 'missing: will copy the staff portal secret' || echo 'MISSING: Discord client secret'))"
  say "stats:   $( filled $ETC/stats-token && echo 'token present' || echo 'not linked (install.sh stats-link)')"
  say "         $( grep -q 'accounts/aliases' /opt/tcp/server-bridge/tcp_stats.py 2>/dev/null && echo 'stats code has the alias route' || echo 'STATS CODE LACKS THE ALIAS ROUTE: patch tcp_stats.py first')"
  user=$(port_user)
  if [ -z "$user" ]; then say "port:    127.0.0.1:$PORT free"
  elif echo "$user" | grep -q python3 && systemctl is-active -q $UNIT 2>/dev/null; then say "port:    127.0.0.1:$PORT in use by $UNIT"
  else say "port:    127.0.0.1:$PORT TAKEN by $user: pick another port in config.json, the unit and the Caddy snippet"; fi
  say "caddy:   $( grep -q '/api/account/' /etc/caddy/Caddyfile 2>/dev/null && echo 'route present' || echo 'no route yet (install.sh caddy)')"
  say "unit:    $(systemctl is-active $UNIT 2>/dev/null || true)"
  say "group:   $(getent group tcpgame >/dev/null && echo 'tcpgame present' || echo 'NO tcpgame GROUP: the reserved-name list cannot be written')"
  for h in $HOMES; do say "server:  $h $( [ -d "$h/tcetest" ] && echo "names list -> $h/tcetest/accounts/names.txt" || echo '(no such server)')"; done
}

install_all() {
  need_root
  user=$(port_user)
  if [ -n "$user" ] && ! systemctl is-active -q $UNIT 2>/dev/null; then say "port $PORT is taken by $user; stop"; exit 1; fi
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { say "needs Python 3.10+"; exit 1; }
  ( cd "$HERE" && python3 -m py_compile tcp_accounts.py )
  getent group tcpaccounts >/dev/null || groupadd --system tcpaccounts
  id tcpaccounts >/dev/null 2>&1 || useradd --system --gid tcpaccounts --home-dir $DATA --shell /usr/sbin/nologin tcpaccounts
  install -d -m 0755 /opt/tcp "$APP"
  if [ -f $APP/tcp_accounts.py ]; then cp -p $APP/tcp_accounts.py "$APP/tcp_accounts.py.bak-$(date -u +%Y%m%d-%H%M%S)"; fi
  install -m 0644 "$HERE/tcp_accounts.py" $APP/tcp_accounts.py
  install -d -m 0750 -o root -g tcpaccounts $ETC
  [ -f $ETC/config.json ] || install -m 0640 -o root -g tcpaccounts "$HERE/deploy/config.example.json" $ETC/config.json
  if ! filled $ETC/client-secret && filled /etc/tcp-staff-portal/client-secret; then
    install -m 0600 -o root -g root /etc/tcp-staff-portal/client-secret $ETC/client-secret
  fi
  filled $ETC/client-secret || { say "put the Discord client secret in $ETC/client-secret first"; exit 1; }
  [ -f $ETC/stats-token ] || install -m 0600 -o root -g root /dev/null $ETC/stats-token
  filled $ETC/internal-token || { umask 077; head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > $ETC/internal-token; }
  chmod 0600 $ETC/client-secret $ETC/stats-token $ETC/internal-token
  for h in $HOMES; do
    [ -d "$h/tcetest" ] || continue
    # setgid: names.txt keeps the tcpgame group whoever writes it
    install -d -m 2775 -o "$(stat -c %U "$h/tcetest")" -g tcpgame "$h/tcetest/accounts"
  done
  install -m 0644 "$HERE/deploy/$UNIT" /etc/systemd/system/$UNIT
  systemctl daemon-reload
  systemctl enable $UNIT >/dev/null
  systemctl restart $UNIT
  sleep 2
  curl -fsS "http://127.0.0.1:$PORT/api/account/health" && say "" && say "installed: $UNIT on 127.0.0.1:$PORT"
}

stats_link() {
  need_root
  grep -q 'accounts/aliases' /opt/tcp/server-bridge/tcp_stats.py || { say "patch the stats service first (tcp_stats.py alias route)"; exit 1; }
  filled $ETC/stats-token || { umask 077; head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > $ETC/stats-token; }
  install -d -m 0755 /etc/systemd/system/tcp-bridge.service.d
  install -m 0644 "$HERE/deploy/70-accounts.conf" /etc/systemd/system/tcp-bridge.service.d/70-accounts.conf
  systemctl daemon-reload
  systemctl restart tcp-bridge.service
  systemctl restart $UNIT
  say "linked: rollback = rm /etc/systemd/system/tcp-bridge.service.d/70-accounts.conf; systemctl daemon-reload; systemctl restart tcp-bridge"
}

caddy() {
  need_root
  F=/etc/caddy/Caddyfile
  if grep -q '/api/account/' $F; then say "route already present"; return 0; fi
  B="$F.bak-$(date -u +%Y%m%d-%H%M%S)-pre-accounts"
  cp -p $F "$B"
  # insert the snippet right after the line that opens the truecombat.eu block
  python3 - "$F" "$HERE/deploy/Caddyfile.snippet" <<'PY'
import re, sys
path, snip = sys.argv[1], open(sys.argv[2]).read()
text = open(path).read()
m = re.search(r'(?m)^truecombat\.eu(\s*,[^{]*)?\s*\{\s*$', text)
if not m:
    sys.exit("no 'truecombat.eu {' block found")
open(path, "w").write(text[:m.end()] + "\n" + snip + text[m.end():])
PY
  if caddy validate --config $F --adapter caddyfile >/dev/null 2>&1; then
    systemctl reload caddy
    say "caddy: route added (backup $B)"
  else
    cp -p "$B" $F
    say "caddy validate FAILED: restored $B, nothing changed"; exit 1
  fi
}

case "$MODE" in
  inspect) inspect ;;
  install) install_all ;;
  stats-link) stats_link ;;
  caddy) caddy ;;
  uninstall) need_root; systemctl disable --now $UNIT || true; rm -f /etc/systemd/system/$UNIT; systemctl daemon-reload; say "removed (data in $DATA, config in $ETC kept)" ;;
  *) say "usage: install.sh inspect|install|stats-link|caddy|uninstall"; exit 2 ;;
esac
