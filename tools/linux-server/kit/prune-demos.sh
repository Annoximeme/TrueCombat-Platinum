#!/bin/sh
# Deletes server match recordings (svdemos/*.sv_84) older than DAYS (default 14).
#   prune-demos.sh <server home folder> [days]
# Daily from cron:  15 5 * * *  /opt/truecombat/current/prune-demos.sh /opt/truecombat/home
set -eu
HOME_DIR=${1:?usage: prune-demos.sh <server home folder> [days]}
DAYS=${2:-14}
[ -d "$HOME_DIR/tcetest/svdemos" ] || exit 0
find "$HOME_DIR/tcetest/svdemos" -type f -name '*.sv_84' -mtime +"$DAYS" -print -delete
