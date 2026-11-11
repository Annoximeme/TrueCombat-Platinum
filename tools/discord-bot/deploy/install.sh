#!/bin/sh
# Installs or updates the TrueCombat: Platinum Discord bot on the VPS.
#
#   sudo ./deploy/install.sh                     install or update the code, keep config and token
#   sudo ./deploy/install.sh --token-stdin       also store a new bot token, read from stdin:
#        read -rs T && printf '%s' "$T" | sudo ./deploy/install.sh --token-stdin; unset T
#   sudo ./deploy/install.sh --retire-webhook    also stop the old webhook status feed (tcp-status timers)
#   sudo ./deploy/install.sh --rcon-from-cfg rcon-official1=/var/lib/tcpgame/home/tcetest/official-private.cfg
#        copy a game server's rcon password (set rconpassword "...") into a bot credential, for /admin and pickups
#   sudo ./deploy/install.sh --secret-stdin github-token
#        store another secret from stdin (the GitHub token for "File on GitHub" on bug reports)
#
# The token is only ever read from stdin, so it never appears in argv, shell
# history, sudo logs or the process list.
set -eu

APP=/opt/tcp/discord-bot
ETC=/etc/tcp-discord-bot
UNIT=/etc/systemd/system/tcp-discord-bot.service
SRC=$(cd "$(dirname "$0")/.." && pwd)
TOKEN_STDIN=0
RETIRE=0
RCON_FROM=""
SECRET_NAME=""

for arg in "$@"; do
  case "$arg" in
    --token-stdin) TOKEN_STDIN=1 ;;
    --retire-webhook) RETIRE=1 ;;
    --rcon-from-cfg) RCON_NEXT=1; continue ;;
    --secret-stdin) SECRET_NEXT=1; continue ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) if [ "${RCON_NEXT:-0}" -eq 1 ]; then RCON_FROM="$RCON_FROM $arg"; RCON_NEXT=0; continue; fi
       if [ "${SECRET_NEXT:-0}" -eq 1 ]; then SECRET_NAME="$arg"; SECRET_NEXT=0; continue; fi
       echo "unknown option: $arg" >&2; exit 2 ;;
  esac
  RCON_NEXT=0
done

[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
need_pkg() { apt-get install -y -q "$1" >/dev/null 2>&1 || { apt-get update -q >/dev/null && apt-get install -y -q "$1" >/dev/null; }; }

# ---------------------------------------------------------------- python
PY=$(command -v python3 || true)
[ -n "$PY" ] || { echo "python3 is not installed" >&2; exit 1; }
"$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "Python 3.10 or newer is needed" >&2; exit 1; }
if ! "$PY" -c 'import ensurepip, venv' 2>/dev/null; then
  say "installing python3-venv"
  need_pkg python3-venv
fi

# ---------------------------------------------------------------- user
if ! id tcpbot >/dev/null 2>&1; then
  say "creating system user tcpbot"
  # the group may already exist (the pickup servers' rcon files are root:tcpbot)
  if getent group tcpbot >/dev/null 2>&1; then
    useradd --system -g tcpbot --home-dir /nonexistent --shell /usr/sbin/nologin tcpbot
  else
    useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin tcpbot
  fi
fi

# ---------------------------------------------------------------- code
say "installing the bot to $APP"
install -d -m 0755 "$APP"
rm -rf "$APP/tcpbot.new"
cp -r "$SRC/tcpbot" "$APP/tcpbot.new"
find "$APP/tcpbot.new" -name '__pycache__' -prune -exec rm -rf {} +
rm -rf "$APP/tcpbot.old"
[ -d "$APP/tcpbot" ] && mv "$APP/tcpbot" "$APP/tcpbot.old"
mv "$APP/tcpbot.new" "$APP/tcpbot"
rm -rf "$APP/assets.new"
cp -r "$SRC/assets" "$APP/assets.new"          # avatar, fonts and the game's icons for the bot emoji
find "$APP/assets.new" -type d -exec chmod 0755 {} + && find "$APP/assets.new" -type f -exec chmod 0644 {} +
rm -rf "$APP/assets" && mv "$APP/assets.new" "$APP/assets"
install -m 0644 "$SRC/requirements.lock" "$SRC/README.md" "$APP/"
install -d -m 0755 "$APP/deploy"
install -m 0755 "$SRC/deploy/install.sh" "$SRC/deploy/uninstall.sh" "$APP/deploy/"
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" rev-parse --short HEAD > "$APP/DEPLOYED_COMMIT" 2>/dev/null || true
fi
"$PY" -c "import sys; sys.path.insert(0, '$APP'); import tcpbot; print(tcpbot.__version__)" > "$APP/VERSION"

if [ ! -x "$APP/venv/bin/python" ]; then
  say "creating the virtual environment"
  "$PY" -m venv "$APP/venv"
fi
say "installing pinned dependencies (hash-checked)"
"$APP/venv/bin/pip" install -q --disable-pip-version-check --require-hashes -r "$APP/requirements.lock"
chown -R root:root "$APP"

# ---------------------------------------------------------------- config and token
install -d -m 0750 -o root -g tcpbot "$ETC"
if [ ! -f "$ETC/config.json" ]; then
  say "writing a starter config to $ETC/config.json (fill in the ids)"
  install -m 0640 -o root -g tcpbot "$SRC/deploy/config.example.json" "$ETC/config.json"
fi
if [ "$TOKEN_STDIN" -eq 1 ]; then
  say "storing the bot token"
  umask 077
  IFS= read -r TOKEN || true
  [ -n "${TOKEN:-}" ] || { echo "no token on stdin" >&2; exit 1; }
  printf '%s\n' "$TOKEN" > "$ETC/token.new"
  unset TOKEN
  chown root:root "$ETC/token.new"; chmod 0600 "$ETC/token.new"
  mv "$ETC/token.new" "$ETC/token"
fi
if [ -n "$SECRET_NAME" ]; then
  [ "$TOKEN_STDIN" -eq 0 ] || { echo "store the token and other secrets in separate runs" >&2; exit 2; }
  case "$SECRET_NAME" in github-token) ;; *) echo "known secrets: github-token" >&2; exit 2 ;; esac
  say "storing $SECRET_NAME"
  umask 077
  IFS= read -r SECRET || true
  [ -n "${SECRET:-}" ] || { echo "nothing on stdin" >&2; exit 1; }
  printf '%s\n' "$SECRET" > "$ETC/$SECRET_NAME.new"
  unset SECRET
  chown root:root "$ETC/$SECRET_NAME.new"; chmod 0600 "$ETC/$SECRET_NAME.new"
  mv "$ETC/$SECRET_NAME.new" "$ETC/$SECRET_NAME"
fi
[ -f "$ETC/token" ] || echo "note: no token yet. Store it with --token-stdin before starting the bot."

# rcon passwords: copied from the game server's own cfg, root-only, handed over as credentials
for pair in $RCON_FROM; do
  name=${pair%%=*}; cfgfile=${pair#*=}
  case "$name" in rcon-[a-z0-9_-]*) ;; *) echo "credential names look like rcon-official1" >&2; exit 2 ;; esac
  pw=$(sed -n 's/^[[:space:]]*set[[:space:]]\{1,\}rconpassword[[:space:]]\{1,\}"\{0,1\}\([^"[:space:]]*\).*/\1/p' "$cfgfile" | tail -n 1)
  [ -n "$pw" ] || { echo "no rconpassword in $cfgfile" >&2; exit 1; }
  umask 077; printf '%s\n' "$pw" > "$ETC/$name"; unset pw
  chown root:root "$ETC/$name"; chmod 0600 "$ETC/$name"
  say "stored $name"
done
CREDS=""
for f in "$ETC"/rcon-* "$ETC"/github-token; do
  [ -f "$f" ] && CREDS="${CREDS}LoadCredential=$(basename "$f"):$f
"
done

# ---------------------------------------------------------------- link folders
# The game server (user tcpgame) writes link requests and player reports; the bot reads and clears them.
LINK_DIRS=$("$PY" - "$ETC/config.json" <<'PYEOF'
import json, sys
cfg = json.load(open(sys.argv[1]))
home = "/var/lib/tcpgame/home/tcetest"
dirs = cfg.get("linking", {}).get("dirs", [home + "/links"]) + cfg.get("reports", {}).get("dirs", [home + "/reports"])
print("\n".join(dict.fromkeys(dirs)))
PYEOF
)
RW=""
for d in $LINK_DIRS; do
  parent=$(dirname "$d")
  if [ ! -d "$parent" ]; then
    echo "note: $parent does not exist, skipping $d"
    continue
  fi
  owner=$(stat -c %U "$parent")
  install -d -m 2770 -o "$owner" -g tcpbot "$d"
  # tcpbot may need to pass through the game's home folders to reach it
  p="$parent"
  while [ "$p" != "/" ]; do
    if ! runuser -u tcpbot -- test -x "$p" 2>/dev/null; then
      command -v setfacl >/dev/null 2>&1 || need_pkg acl
      setfacl -m u:tcpbot:x "$p"    # traverse only: tcpbot can't list or read anything else there
    fi
    p=$(dirname "$p")
  done
  RW="${RW}ReadWritePaths=-$d
"
  say "game folder ready: $d"
done

# Server demos next to the report folders: read-only, so reports can point at the right moment
for d in $("$PY" - "$ETC/config.json" <<'PYEOF'
import json, os, sys
cfg = json.load(open(sys.argv[1]))
for r in cfg.get("reports", {}).get("dirs", ["/var/lib/tcpgame/home/tcetest/reports"]):
    print(os.path.join(os.path.dirname(r.rstrip("/")), "svdemos"))
PYEOF
); do
  if [ -d "$d" ]; then
    command -v setfacl >/dev/null 2>&1 || need_pkg acl
    setfacl -m u:tcpbot:rx "$d" && setfacl -d -m u:tcpbot:r "$d" 2>/dev/null || true
    say "demo folder readable: $d"
  fi
done

# Chat bridge: read access to each bridged server's console log, or to the journal for "unit" entries
EXTRA=""
BRIDGE=$("$PY" - "$ETC/config.json" <<'PYEOF'
import json, sys
cb = json.load(open(sys.argv[1])).get("chat_bridge", {})
for s in cb.get("servers", []) if cb.get("enabled") else []:
    print("log " + s["log"] if s.get("log") else "unit " + str(s.get("unit", "")))
PYEOF
)
if printf '%s\n' "$BRIDGE" | grep -q '^unit '; then
  EXTRA="SupplementaryGroups=systemd-journal
"
  say "chat bridge: journal access added"
fi
printf '%s\n' "$BRIDGE" | sed -n 's/^log //p' | while IFS= read -r f; do
  [ -f "$f" ] || { echo "note: chat log $f does not exist yet"; continue; }
  command -v setfacl >/dev/null 2>&1 || need_pkg acl
  setfacl -m u:tcpbot:r "$f"
  p=$(dirname "$f")
  while [ "$p" != "/" ]; do
    runuser -u tcpbot -- test -x "$p" 2>/dev/null || setfacl -m u:tcpbot:x "$p"
    p=$(dirname "$p")
  done
  say "chat log readable: $f"
done

# ---------------------------------------------------------------- service
say "installing the systemd service"
install -m 0644 "$SRC/deploy/systemd/tcp-discord-bot.service" "$UNIT"
printf '%s%s%s' "$RW" "$CREDS" "$EXTRA" >> "$UNIT"
printf '\n[Install]\nWantedBy=multi-user.target\n' >> "$UNIT"
systemctl daemon-reload

if ! TCPBOT_CONFIG="$ETC/config.json" "$APP/venv/bin/python" -c "import sys; sys.path.insert(0, '$APP'); from tcpbot.__main__ import main; sys.exit(main(['check']))"; then
  echo "The config needs attention ($ETC/config.json). The service was installed but not started." >&2
  exit 1
fi

if [ "$RETIRE" -eq 1 ]; then
  for t in tcp-status.timer tcp-status-unranked.timer; do
    if systemctl list-unit-files "$t" >/dev/null 2>&1 && systemctl is-enabled "$t" >/dev/null 2>&1; then
      say "retiring the webhook feed: $t"
      systemctl disable --now "$t"
    fi
  done
fi

if [ -f "$ETC/token" ]; then
  systemctl enable tcp-discord-bot.service >/dev/null 2>&1
  systemctl restart tcp-discord-bot.service
  sleep 5
  systemctl --no-pager --lines=15 status tcp-discord-bot.service || true
  rm -rf "$APP/tcpbot.old"
  say "done. Logs: journalctl -u tcp-discord-bot -f"
fi
