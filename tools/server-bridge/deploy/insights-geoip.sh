#!/bin/sh
# Downloads this month's DB-IP "IP to Country Lite" list (CC BY 4.0, https://db-ip.com) to $1.
# Keeps the previous file when the download fails or looks wrong.
set -eu
OUT=${1:-/var/lib/tcp-insights/geo.csv.gz}
TMP="$OUT.new"
M=$(date -u +%Y-%m)
P=$(date -u -d "$(date -u +%Y-%m-01) -1 day" +%Y-%m)
for month in "$M" "$P"; do
  if curl -fsSL --max-time 300 -o "$TMP" "https://download.db-ip.com/free/dbip-country-lite-$month.csv.gz" \
     && gzip -t "$TMP" && [ "$(zcat "$TMP" | head -n 1000 | wc -l)" -ge 1000 ]; then
    mv -f "$TMP" "$OUT"
    echo "country list $month installed"
    exit 0
  fi
done
rm -f "$TMP"
echo "country list download failed; keeping the old one" >&2
exit 1
