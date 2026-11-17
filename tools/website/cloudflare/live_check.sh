#!/bin/bash
# Live checks of truecombat.eu behind Cloudflare. Run from anywhere with dig and curl (the Cloudflare workflow, mode=verify).
D=truecombat.eu
fail=0
ok()  { echo "ok    $*"; }
bad() { echo "FAIL  $*"; fail=1; }
echo "== Nameservers"
ns=$(dig +short NS $D @1.1.1.1 | sort | tr '\n' ' '); echo "  $ns"
case "$ns" in *ns.cloudflare.com*) ok "Cloudflare nameservers";; *) bad "nameservers are not Cloudflare's yet";; esac
echo "== DNS (public resolvers 1.1.1.1 and 8.8.8.8)"
for r in 1.1.1.1 8.8.8.8; do
  for q in "$D A" "www.$D A" "api.$D A" "master.$D A" "master.$D AAAA" "staff.$D A" "staff.$D AAAA" "$D MX" "$D TXT" "_dmarc.$D TXT" "zmail._domainkey.$D TXT" "$D CAA"; do
    set -- $q; echo "  @$r $1 $2: $(dig +short $1 $2 @$r | tr '\n' ' ' | cut -c1-160)"
  done
done
echo "== Website through Cloudflare"
for u in https://$D/ https://$D/style.css https://$D/launcher-feed.txt https://$D/sitemap.xml https://www.$D/ http://$D/; do
  h=$(curl -sS -o /dev/null -D - --max-time 20 "$u")
  code=$(echo "$h" | head -1 | awk '{print $2}'); srv=$(echo "$h" | grep -i '^server:' | tr -d '\r'); ray=$(echo "$h" | grep -ci '^cf-ray:')
  loc=$(echo "$h" | grep -i '^location:' | tr -d '\r'); cache=$(echo "$h" | grep -i '^cf-cache-status:' | tr -d '\r')
  echo "  $u -> $code $srv ${loc} ${cache}"
  [ "$ray" -ge 1 ] && case "$code" in 2*|3*) ok "$u via Cloudflare";; *) bad "$u answered $code";; esac || bad "$u not via Cloudflare"
done
echo "== Certificate at the edge"
echo | openssl s_client -connect $D:443 -servername $D 2>/dev/null | openssl x509 -noout -issuer -enddate | sed 's/^/  /'
echo "== Let's Encrypt HTTP challenge path reaches Caddy (expect 404 from origin, not a Cloudflare redirect)"
curl -s -o /dev/null -w "  %{http_code} %{redirect_url}\n" --max-time 20 http://$D/.well-known/acme-challenge/cf-check
echo "== DNS-only names go straight to the VPS"
for u in https://api.$D/funding.json https://staff.$D/; do
  h=$(curl -sS -o /dev/null -D - --max-time 20 "$u"); code=$(echo "$h" | head -1 | awk '{print $2}')
  ip=$(curl -s -o /dev/null -w '%{remote_ip}' --max-time 20 "$u")
  echo "  $u -> $code from $ip"
  [ "$ip" = "2.24.59.195" ] || [ "$ip" = "2a02:4780:83:c9f9::1" ] && case "$code" in 2*|3*) ok "$u direct";; *) bad "$u answered $code";; esac || bad "$u not direct ($ip)"
done
echo "== Master server (UDP 27950, getservers)"
python3 - <<'PY' || true
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
try:
    s.sendto(b"\xff\xff\xff\xffgetservers 84 full empty", ("master.truecombat.eu", 27950))
    d, _ = s.recvfrom(4096); print("  ok    master answered %d bytes: %r" % (len(d), d[:40]))
except Exception as e:
    print("  note  master did not answer getservers (%s); protocol number may differ, check from the game" % e)
PY
[ $fail = 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
