#!/bin/sh
# Installs or updates the staff portal on the VPS. Run as root from the unpacked tools/staff-portal folder.
#
#   sudo ./deploy/install.sh inspect             read-only: what is there, what would change
#   sudo ./deploy/install.sh install             code, user, service, credentials, polkit rule (not Caddy)
#   sudo ./deploy/install.sh caddy               adds staff.truecombat.eu to Caddy (backup + validate + reload)
#   sudo ./deploy/install.sh stats-link          lets the portal use the stats service's review queue (token + drop-in, restarts tcp-bridge)
#   sudo ./deploy/install.sh uninstall           stops and removes the service (keeps data and config)
#
# Before install: put the Discord OAuth client secret in /etc/tcp-staff-portal/client-secret (one line),
# and fill /etc/tcp-staff-portal/config.json (created from config.example.json on the first run).
# rcon passwords are copied from each game server's own cfg into root-only credential files.
# Optional: the staff channel's Discord webhook URL in /etc/tcp-staff-portal/staff-webhook (one line).
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
APP=/opt/tcp/staff-portal
ETC=/etc/tcp-staff-portal
DATA=/var/lib/tcp-staff-portal
UNIT=tcp-staff-portal.service
MODE=${1:-inspect}

# server key : game home (the folder that holds tcetest/)
SERVERS="official1:/var/lib/tcpgame/home official2:/var/lib/tcpgame/home-unranked pickup1:/var/lib/tcpgame/home-pickup1 pickup2:/var/lib/tcpgame/home-pickup2"
BOTDB=/var/lib/tcp-discord-bot

say() { printf '%s\n' "$*"; }
# a file counts as filled only when it holds something other than white space (an empty line is not a secret)
filled() { [ -f "$1" ] && grep -q '[^[:space:]]' "$1"; }
need_root() { [ "$(id -u)" = 0 ] || { say "run as root (sudo)"; exit 1; }; }

# The last 'set rconpassword "..."' in the server's cfg files (official-private.cfg first).
rcon_password_of() {
  home=$1
  for f in "$home"/tcetest/official-private.cfg "$home"/tcetest/*private*.cfg "$home"/tcetest/*.cfg; do
    [ -f "$f" ] || continue
    pw=$(sed -n 's/^[[:space:]]*set[[:space:]]\{1,\}rconpassword[[:space:]]\{1,\}"\{0,1\}\([^"[:space:]]*\).*/\1/p' "$f" | tail -n 1)
    if [ -n "$pw" ]; then printf '%s' "$pw"; return 0; fi
  done
  return 1
}

inspect() {
  say "== staff portal: inspect (read-only)"
  say "code:    $APP $( [ -f $APP/tcp_staff_portal.py ] && sed -n 's/^VERSION = "\(.*\)"/version \1/p' $APP/tcp_staff_portal.py || echo '(not installed)')"
  say "new:     $(sed -n 's/^VERSION = "\(.*\)"/version \1/p' "$HERE/tcp_staff_portal.py")"
  say "user:    $(id tcpstaff 2>/dev/null || echo 'tcpstaff (will be created)')"
  say "config:  $( [ -f $ETC/config.json ] && echo present || echo 'missing (created from the example)')"
  say "secret:  $( filled $ETC/client-secret && echo present || echo 'MISSING: Discord client secret')"
  say "webhook: $( filled $ETC/staff-webhook && echo present || echo 'none (alerts stay in the portal)')"
  say "stats:   $( filled $ETC/stats-token && echo 'review queue linked' || echo 'review queue not linked (install.sh stats-link)')"
  say "botdb:   $( [ -f $BOTDB/bot.db ] && echo "$BOTDB/bot.db (linked Discord accounts)" || echo 'no Discord bot database')"
  for entry in $SERVERS; do
    key=${entry%%:*}; home=${entry#*:}
    if rcon_password_of "$home" >/dev/null 2>&1; then pw=found; else pw='NOT FOUND'; fi
    unit_state=$(systemctl is-active "tcp-$( [ "$key" = official1 ] && echo official || echo "$key").service" 2>/dev/null || true)
    say "server:  $key home=$home rcon=$pw reports=$( [ -d "$home/tcetest/reports" ] && echo yes || echo 'not yet') demos=$( [ -d "$home/tcetest/svdemos" ] && echo yes || echo 'none yet') unit=$unit_state"
  done
  say "port:    $(ss -ltn 2>/dev/null | grep -q '127.0.0.1:8097 ' && echo '8097 in use' || echo '8097 free')"
  say "polkit:  $( [ -d /etc/polkit-1/rules.d ] && echo 'rules.d present' || echo 'NO polkit rules.d (restart button will not work)')"
  say "acl:     $(command -v setfacl >/dev/null && echo setfacl || echo 'setfacl missing (apt install acl)')"
  say "caddy:   $(grep -q '^staff.truecombat.eu' /etc/caddy/Caddyfile 2>/dev/null && echo 'site block present' || echo 'no staff.truecombat.eu block yet')"
  say "dns:     $(getent hosts staff.truecombat.eu || echo 'staff.truecombat.eu does not resolve yet')"
  say "service: $(systemctl is-active $UNIT 2>/dev/null || true)"
}

install_portal() {
  need_root
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || { say "python 3.10+ needed"; exit 1; }
  command -v setfacl >/dev/null || { say "setfacl missing: apt-get install -y acl"; exit 1; }
  id tcpstaff >/dev/null 2>&1 || useradd --system --home-dir "$DATA" --no-create-home --shell /usr/sbin/nologin tcpstaff
  install -d -m 0755 /opt/tcp
  if [ -d "$APP" ]; then rm -rf "$APP.previous"; cp -a "$APP" "$APP.previous"; fi
  install -d -m 0755 "$APP" "$APP/static" "$APP/static/fonts" "$APP/static/maps"
  install -m 0644 "$HERE/tcp_staff_portal.py" "$APP/"
  install -m 0644 "$HERE"/static/*.html "$HERE"/static/*.css "$HERE"/static/*.js "$HERE"/static/*.png "$APP/static/"
  install -m 0644 "$HERE"/static/fonts/*.woff2 "$APP/static/fonts/"
  install -m 0644 "$HERE"/static/maps/*.json "$HERE"/static/maps/*.webp "$APP/static/maps/"
  git -C "$HERE" rev-parse HEAD > "$APP/DEPLOYED_COMMIT" 2>/dev/null || date -u +%FT%TZ > "$APP/DEPLOYED_COMMIT"

  install -d -m 0750 -o root -g tcpstaff "$ETC"
  [ -f "$ETC/config.json" ] || install -m 0640 -o root -g tcpstaff "$HERE/deploy/config.example.json" "$ETC/config.json"
  filled "$ETC/client-secret" || { say "put the Discord client secret in $ETC/client-secret first"; exit 1; }
  chown root:root "$ETC/client-secret"; chmod 0600 "$ETC/client-secret"
  if grep -q 'DISCORD_' "$ETC/config.json"; then say "fill owners, client_id and guild_id in $ETC/config.json first"; exit 1; fi
  # optional credentials: an empty file switches the feature off
  for f in staff-webhook stats-token; do
    [ -f "$ETC/$f" ] || : > "$ETC/$f"
    chown root:root "$ETC/$f"; chmod 0600 "$ETC/$f"
  done

  # rcon passwords -> root-only credential files (systemd hands them to the service)
  for entry in $SERVERS; do
    key=${entry%%:*}; home=${entry#*:}
    if pw=$(rcon_password_of "$home"); then
      umask 077; printf '%s\n' "$pw" > "$ETC/rcon-$key"; umask 022
    else
      say "warning: no rconpassword for $key in $home/tcetest; that server stays read-only in the portal"
      : > "$ETC/rcon-$key"
    fi
    chown root:root "$ETC/rcon-$key"; chmod 0600 "$ETC/rcon-$key"
    # the portal reads player reports; the game and the Discord bot keep writing them as before
    for d in "$home/tcetest/reports" "$home/tcetest/reports/sent"; do
      [ -d "$d" ] || install -d -m 0775 -o tcpgame -g tcpgame "$d"
    done
    for d in "$home" "$home/tcetest"; do setfacl -m u:tcpstaff:x "$d"; done
    for d in "$home/tcetest/reports" "$home/tcetest/reports/sent"; do
      setfacl -m u:tcpstaff:rx "$d"; setfacl -d -m u:tcpstaff:r "$d"
      find "$d" -maxdepth 1 -type f -name '*.json' -exec setfacl -m u:tcpstaff:r {} +
    done
    # server demos (only written while sv_autoDemo is on): staff download the one that covers a report
    d="$home/tcetest/svdemos"
    [ -d "$d" ] || install -d -m 0775 -o tcpgame -g tcpgame "$d"
    setfacl -m u:tcpstaff:rx "$d"; setfacl -d -m u:tcpstaff:r "$d"
    find "$d" -maxdepth 1 -type f -exec setfacl -m u:tcpstaff:r {} +
  done

  # linked Discord accounts: read-only access to the Discord bot's database
  if [ -f "$BOTDB/bot.db" ]; then
    setfacl -m u:tcpstaff:rx "$BOTDB"; setfacl -d -m u:tcpstaff:r "$BOTDB"
    find "$BOTDB" -maxdepth 1 -type f -name 'bot.db*' -exec setfacl -m u:tcpstaff:r {} +
  fi

  if [ -d /etc/polkit-1/rules.d ]; then
    install -m 0644 "$HERE/deploy/50-tcp-staff-portal.rules" /etc/polkit-1/rules.d/50-tcp-staff-portal.rules
  fi
  install -m 0644 "$HERE/deploy/tcp-staff-portal.service" /etc/systemd/system/$UNIT
  systemctl daemon-reload
  systemctl enable $UNIT >/dev/null
  systemctl restart $UNIT
  sleep 3
  if curl -fsS http://127.0.0.1:8097/healthz >/dev/null; then
    say "portal is up: $(curl -fsS http://127.0.0.1:8097/healthz)"
  else
    say "portal did not come up; rolling back"; journalctl -u $UNIT -n 30 --no-pager || true
    if [ -d "$APP.previous" ]; then rm -rf "$APP"; mv "$APP.previous" "$APP"; systemctl restart $UNIT || true
    else systemctl disable --now $UNIT || true; fi
    exit 1
  fi
}

add_caddy() {
  need_root
  F=/etc/caddy/Caddyfile
  if grep -q '^staff.truecombat.eu' "$F"; then say "Caddy already has the staff.truecombat.eu block"; return 0; fi
  getent hosts staff.truecombat.eu >/dev/null || { say "staff.truecombat.eu does not resolve yet: add the DNS record first"; exit 1; }
  B="$F.bak-$(date -u +%Y%m%d-%H%M%S)-pre-staff"
  cp -a "$F" "$B"
  printf '\n' >> "$F"; cat "$HERE/deploy/Caddyfile.snippet" >> "$F"
  if caddy validate --config "$F" --adapter caddyfile >/dev/null 2>&1; then
    systemctl reload caddy && say "Caddy reloaded; backup $B"
  else
    cp -a "$B" "$F"; say "Caddy rejected the new block; restored $B"; exit 1
  fi
}

# The stats service answers /staff/review.json and /staff/void only from this machine and only with this token.
# It reads it as the systemd credential 'staff-token', so the drop-in leaves the bridge's command line alone.
stats_link() {
  need_root
  install -d -m 0750 -o root -g tcpstaff "$ETC"
  if ! filled "$ETC/stats-token"; then
    umask 077; head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$ETC/stats-token"; umask 022
  fi
  chown root:root "$ETC/stats-token"; chmod 0600 "$ETC/stats-token"
  install -d -m 0755 /etc/systemd/system/tcp-bridge.service.d
  printf '[Service]\nLoadCredential=staff-token:%s/stats-token\n' "$ETC" > /etc/systemd/system/tcp-bridge.service.d/staff-portal.conf
  systemctl daemon-reload
  systemctl restart tcp-bridge.service
  sleep 2
  # the token goes in a header file, not on the command line where any user could see it in ps
  H=$(mktemp); chmod 0600 "$H"; printf 'X-Staff-Token: %s\n' "$(cat "$ETC/stats-token")" > "$H"
  if curl -fsS -H @"$H" http://127.0.0.1:8090/staff/review.json >/dev/null; then
    rm -f "$H"
    say "stats service linked: review queue answers"
  else
    rm -f "$H"
    say "the stats service did not answer /staff/review.json; is the new tcp_stats.py deployed? Removing the drop-in."
    rm -f /etc/systemd/system/tcp-bridge.service.d/staff-portal.conf; systemctl daemon-reload; systemctl restart tcp-bridge.service
    exit 1
  fi
  systemctl restart $UNIT 2>/dev/null || true
}

uninstall() {
  need_root
  systemctl disable --now $UNIT 2>/dev/null || true
  rm -f /etc/systemd/system/$UNIT /etc/polkit-1/rules.d/50-tcp-staff-portal.rules
  systemctl daemon-reload
  say "stopped and removed; $DATA, $ETC and $APP are kept"
}

case "$MODE" in
  inspect) inspect ;;
  install) install_portal ;;
  caddy) add_caddy ;;
  stats-link) stats_link ;;
  uninstall) uninstall ;;
  *) say "usage: $0 inspect|install|caddy|stats-link|uninstall"; exit 2 ;;
esac
