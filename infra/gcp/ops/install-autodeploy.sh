#!/usr/bin/env bash
# One-time setup of pull-based auto-deploy on the VM. Run as root from a folder holding the ops files.
#   sudo bash install-autodeploy.sh <current-main-sha>
# The SHA marks what is already running, so the first deploy only ships what changed after it.
set -euo pipefail
cd "$(dirname "$0")"
BASE="${1:?pass the commit that is already deployed}"
sed -i 's/\r$//' gpuchain-autodeploy.sh gpuchain-web-deploy.sh gpuchain-autodeploy.service gpuchain-autodeploy.timer
bash -n gpuchain-autodeploy.sh && bash -n gpuchain-web-deploy.sh
install -m 0755 gpuchain-autodeploy.sh gpuchain-web-deploy.sh /opt/gpuchain-ops/
install -m 0644 gpuchain-autodeploy.service gpuchain-autodeploy.timer /etc/systemd/system/
mkdir -p /var/lib/gpuchain-autodeploy/public && chmod 755 /var/lib/gpuchain-autodeploy /var/lib/gpuchain-autodeploy/public
[ -f /var/lib/gpuchain-autodeploy/deployed ] || echo "$BASE" > /var/lib/gpuchain-autodeploy/deployed
[ -f /var/lib/gpuchain-autodeploy/public/version.json ] || printf '{"sha":"%s","deployed_at":"%s","python":false,"web":false}\n' "$BASE" "$(date -u +%FT%TZ)" > /var/lib/gpuchain-autodeploy/public/version.json
chmod 644 /var/lib/gpuchain-autodeploy/public/version.json

# Serve the deployed version at https://gpuchain.duckdns.org/deploy/version.json (nothing else from that folder).
# The anchor matches the site block in infra/gcp/Caddyfile, which answers both domain names.
CF=/etc/caddy/Caddyfile
if ! grep -q 'handle_path /deploy/\*' "$CF"; then
  cp -a "$CF" "$CF.before-autodeploy-$(date -u +%Y%m%d-%H%M%S)"
  python3 - "$CF" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
anchor = "gpuchain.duckdns.org, ekido.duckdns.org {\n\timport secure\n\tencode gzip\n"
block = ("\thandle_path /deploy/* {\n\t\t@version path /version.json\n\t\thandle @version {\n"
         "\t\t\theader Cache-Control \"no-store\"\n\t\t\troot * /var/lib/gpuchain-autodeploy/public\n\t\t\tfile_server\n\t\t}\n"
         "\t\trespond 404\n\t}\n")
assert s.count(anchor) == 1, "site block not found"
open(p, "w").write(s.replace(anchor, anchor + block))
PY
  caddy validate --config "$CF" --adapter caddyfile
  systemctl reload caddy
fi
systemctl daemon-reload
systemctl enable --now gpuchain-autodeploy.timer
echo "auto-deploy timer: $(systemctl is-active gpuchain-autodeploy.timer); base ${BASE:0:7}"
