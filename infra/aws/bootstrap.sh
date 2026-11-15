#!/usr/bin/env bash
# Builds the Ekido Base Sepolia server on a fresh Ubuntu 24.04 EC2 instance from one commit of the public repo.
# Run as root, for example through SSM Run Command (no SSH):
#   bash bootstrap.sh <commit-sha>
#
# It lays out the same paths and systemd units as the earlier GCP server, so the ops scripts in infra/gcp/ops work
# unchanged: the coordinator, two verifiers and the smoke provider under /opt/gpuchain-sepolia, the dashboard under
# /opt/GPUchain/.cache/sepolia-release, Caddy in front, and the auto-deploy, backup and monitor timers.
# The hackathon demo stack (local chain on sslip.io) is not installed.
#
# Not done here, on purpose:
#   - secrets: /etc/gpuchain/sepolia.env, sepolia-verifier-{1,2}.env and backup.env are placed separately;
#   - data: /var/lib/gpuchain-sepolia (jobs.db, artifacts) is restored separately;
#   - the escrow ABI under /opt/gpuchain-sepolia/contracts/out is copied from the build that deployed the contract;
#   - starting services: done once the secrets and data are in place.
# Safe to run again: it installs what's missing and refreshes code, units and scripts.
set -euo pipefail
SHA="${1:?usage: bootstrap.sh <commit-sha>}"
REPO="${EKIDO_REPO:-ekido-ai/Ekido}"
APP=/opt/gpuchain-sepolia
WEB=/opt/GPUchain/.cache/sepolia-release/apps/web-combined
OPS=/opt/gpuchain-ops
export DEBIAN_FRONTEND=noninteractive

echo "== packages"
apt-get update -q
apt-get install -y -q python3-venv python3-pip jq curl ca-certificates gnupg rsync sqlite3 unzip \
  debian-keyring debian-archive-keyring apt-transport-https
if ! command -v node >/dev/null || ! node --version | grep -q '^v22'; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y -q nodejs
fi
if ! command -v caddy >/dev/null; then
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -q
  apt-get install -y -q caddy
fi
command -v aws >/dev/null || snap install aws-cli --classic   # used by gpuchain-backup.sh for S3

echo "== source $REPO@${SHA:0:7}"
SRC=$(mktemp -d); trap 'rm -rf "$SRC"' EXIT
curl -fsSL --max-time 180 "https://codeload.github.com/$REPO/tar.gz/$SHA" | tar -xz -C "$SRC" --strip-components=1
id gpuchain >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin gpuchain

echo "== services' code and Python"
mkdir -p "$APP/infra/gcp" "$APP/contracts"
for d in apps/coordinator packages/ekido_core workers/agent workers/runtime workers/verifier; do
  mkdir -p "$APP/$d"
  rsync -a --delete --exclude tests --exclude __pycache__ "$SRC/$d/" "$APP/$d/"
done
install -m 0644 "$SRC/infra/gcp/sepolia_coordinator.py" "$APP/infra/gcp/sepolia_coordinator.py"
[ -x "$APP/venv/bin/python" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q --upgrade pip
"$APP/venv/bin/pip" install -q -r "$SRC/infra/aws/requirements-server.txt"
"$APP/venv/bin/python" -m compileall -q "$APP/apps" "$APP/packages" "$APP/workers" "$APP/infra/gcp/sepolia_coordinator.py" >/dev/null
[ -f "$APP/contracts/out/GPUChainEscrow.sol/GPUChainEscrow.json" ] || echo "NOTE: escrow ABI missing at $APP/contracts/out; copy it before starting the coordinator"

echo "== dashboard"
mkdir -p "$WEB"
rsync -a --delete --exclude node_modules --exclude .next "$SRC/apps/web-combined/" "$WEB/"
chown -R gpuchain:gpuchain /opt/GPUchain
sudo -u gpuchain bash -c "cd '$WEB' && npm ci --no-audit --no-fund >/tmp/ekido-npm-ci.log 2>&1"
sudo -u gpuchain env -C "$WEB" \
  NEXT_PUBLIC_COORDINATOR_URL=https://gpuchain.duckdns.org/sepolia \
  "NEXT_PUBLIC_COORDINATOR_WS=wss://gpuchain.duckdns.org/sepolia/ws/jobs/{job}" \
  NEXT_PUBLIC_EVENT_SOURCE=live NEXT_PUBLIC_CHAIN_ID=84532 NEXT_PUBLIC_SIGNED_JOBS=1 \
  NEXT_PUBLIC_ESCROW_ADDRESS=0x1BF65f755457a92850009c88AFb337Ec57745a22 \
  npx next build >/tmp/ekido-next-build.log 2>&1 || { tail -30 /tmp/ekido-next-build.log; exit 1; }

echo "== units and ops scripts"
install -m 0644 "$SRC/infra/gcp/gpuchain-sepolia.service" "$SRC/infra/gcp/gpuchain-sepolia-verifier@.service" \
  "$SRC/infra/gcp/gpuchain-sepolia-web.service" /etc/systemd/system/
install -m 0644 "$SRC"/infra/gcp/ops/gpuchain-sepolia-smoke-provider.service \
  "$SRC"/infra/gcp/ops/gpuchain-{autodeploy,backup,monitor}.{service,timer} /etc/systemd/system/
mkdir -p "$OPS"
for f in gpuchain-autodeploy.sh gpuchain-web-deploy.sh gpuchain-backup.sh gpuchain-monitor.sh; do
  sed 's/\r$//' "$SRC/infra/gcp/ops/$f" > "$OPS/$f"; chmod 0755 "$OPS/$f"; bash -n "$OPS/$f"
done
sed -i 's/\r$//' /etc/systemd/system/gpuchain-*.service /etc/systemd/system/gpuchain-*.timer

echo "== auto-deploy state"
mkdir -p /var/lib/gpuchain-autodeploy/public && chmod 755 /var/lib/gpuchain-autodeploy /var/lib/gpuchain-autodeploy/public
echo "$SHA" > /var/lib/gpuchain-autodeploy/deployed
printf '{"sha":"%s","deployed_at":"%s","python":true,"web":true}\n' "$SHA" "$(date -u +%FT%TZ)" > /var/lib/gpuchain-autodeploy/public/version.json
chmod 644 /var/lib/gpuchain-autodeploy/public/version.json

echo "== caddy"
install -m 0644 "$SRC/infra/aws/Caddyfile" /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null
systemctl reload caddy || systemctl restart caddy

systemctl daemon-reload
systemctl enable gpuchain-sepolia gpuchain-sepolia-verifier@1 gpuchain-sepolia-verifier@2 gpuchain-sepolia-web \
  gpuchain-sepolia-smoke-provider gpuchain-autodeploy.timer gpuchain-backup.timer gpuchain-monitor.timer >/dev/null 2>&1
echo "Bootstrap done for ${SHA:0:7}. Next: secrets, data, escrow ABI, then start the services."
