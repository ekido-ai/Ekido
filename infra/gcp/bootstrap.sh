#!/usr/bin/env bash
# Sets up GPUChain on a fresh Ubuntu 24.04 VM, behind HTTPS. Run as root:
#   sudo bash bootstrap.sh <host>        e.g. 34-93-70-171.sslip.io
# Expects the repo zip at /tmp/gpuchain.zip (top folder GPUchain/). It holds no wallet keys: the stack's
# local chain uses fixed public test keys. The operator token is made here and never leaves the VM.
set -euo pipefail
HOST="$1"
ROOT=/opt/GPUchain
export DEBIAN_FRONTEND=noninteractive

apt-get update -q
apt-get install -y -q python3-venv python3-pip unzip curl ca-certificates gnupg debian-keyring debian-archive-keyring apt-transport-https

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

id gpuchain >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin gpuchain
systemctl stop gpuchain-stack gpuchain-web 2>/dev/null || true
rm -rf "$ROOT"
unzip -q /tmp/gpuchain.zip -d /opt
chown -R gpuchain:gpuchain "$ROOT"

# Python: CPU torch and the services' packages, in the place demo_stack.py expects.
sudo -u gpuchain python3 -m venv "$ROOT/.cache/cpu-venv"
PIP="$ROOT/.cache/cpu-venv/bin/pip"
sudo -u gpuchain "$PIP" install -q --upgrade pip
sudo -u gpuchain "$PIP" install -q "torch==2.15.0" --index-url https://download.pytorch.org/whl/cpu
sudo -u gpuchain "$PIP" install -q safetensors numpy eth-account "sqlalchemy>=2" "fastapi>=0.115" "uvicorn>=0.30" pydantic-settings websockets web3 httpx

# Foundry 1.9.0 (anvil and forge), the version the contracts are tested with, through the official installer.
if [ ! -x "$ROOT/.cache/foundry/anvil" ]; then
  sudo -u gpuchain bash -c 'curl -fsSL https://foundry.paradigm.xyz | bash && ~/.foundry/bin/foundryup -i v1.9.0'
  mkdir -p "$ROOT/.cache/foundry"
  cp /home/gpuchain/.foundry/bin/anvil /home/gpuchain/.foundry/bin/forge "$ROOT/.cache/foundry/"
  chown -R gpuchain:gpuchain "$ROOT/.cache/foundry"
fi

# Operator token: lets someone with it use the operator API over HTTPS. Readable by root and the service only.
mkdir -p /etc/gpuchain
if [ ! -s /etc/gpuchain/stack.env ]; then
  printf 'API_TOKEN=%s\n' "$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')" > /etc/gpuchain/stack.env
fi
grep -q '^PUBLIC_READ=' /etc/gpuchain/stack.env || printf 'PUBLIC_READ=1\nCORS_ORIGINS=["https://%s"]\n' "$HOST" >> /etc/gpuchain/stack.env
chown root:gpuchain /etc/gpuchain/stack.env
chmod 640 /etc/gpuchain/stack.env

# Dashboard, built against the public coordinator address.
cd "$ROOT/apps/web-combined"
sudo -u gpuchain env NEXT_PUBLIC_COORDINATOR_URL="https://api.$HOST" NEXT_PUBLIC_COORDINATOR_WS="wss://api.$HOST/ws/jobs/{job}" \
  NEXT_PUBLIC_EVENT_SOURCE=live NEXT_PUBLIC_CHAIN_ID=31337 bash -c 'npm ci --no-audit --no-fund && npm run build'

install -m 644 "$ROOT/infra/gcp/gpuchain-stack.service" /etc/systemd/system/gpuchain-stack.service
install -m 644 "$ROOT/infra/gcp/gpuchain-web.service" /etc/systemd/system/gpuchain-web.service
sed "s/__HOST__/$HOST/g" "$ROOT/infra/gcp/Caddyfile" > /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now gpuchain-stack gpuchain-web
systemctl reload caddy || systemctl restart caddy
echo "Done. Dashboard: https://$HOST  Coordinator: https://api.$HOST"
