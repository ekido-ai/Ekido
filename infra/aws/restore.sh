#!/usr/bin/env bash
# Puts secrets, data and the escrow ABI on a server built by bootstrap.sh, then starts the services.
# Run as root (for example through SSM Run Command):
#   bash restore.sh <bucket>            # data from s3://<bucket>/migration/data.tgz
#
# Inputs, all private:
#   s3://<bucket>/migration/contracts-out.tgz   the escrow build output (contracts/out) the deployed contract came from
#   s3://<bucket>/migration/data.tgz            ekido-data/jobs.db and ekido-data/artifacts/ (a consistent copy)
#   SSM SecureString parameters /ekido/server/{sepolia.env,sepolia-verifier-1.env,sepolia-verifier-2.env}
# Secrets are written straight to /etc/gpuchain with mode 600 and never printed.
# The smoke provider is not started here: it dials wss://gpuchain.duckdns.org, so it starts once DNS points here.
set -euo pipefail
BUCKET="${1:?usage: restore.sh <bucket>}"
APP=/opt/gpuchain-sepolia
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-ap-south-1}"

echo "== escrow ABI"
aws s3 cp "s3://$BUCKET/migration/contracts-out.tgz" "$WORK/contracts-out.tgz" --only-show-errors
tar -xzf "$WORK/contracts-out.tgz" -C "$APP"
test -f "$APP/contracts/out/GPUChainEscrow.sol/GPUChainEscrow.json"

echo "== secrets"
install -d -m 0755 /etc/gpuchain
for name in sepolia.env sepolia-verifier-1.env sepolia-verifier-2.env; do
  # Create the file with mode 600 first, then fill it through a pipe. The snap-packaged AWS CLI writes nothing when
  # its output is redirected straight to a file, and still exits 0, which left empty secret files once.
  install -m 600 /dev/null "/etc/gpuchain/$name"
  aws ssm get-parameter --name "/ekido/server/$name" --with-decryption --query Parameter.Value --output text | cat > "/etc/gpuchain/$name"
  keys=$(grep -c '=' "/etc/gpuchain/$name" || true)
  [ "$keys" -gt 0 ] || { echo "$name came back empty; stopping"; exit 1; }
  echo "$name: $keys keys"
done
printf 'BACKUP_S3_BUCKET=%s\n' "$BUCKET" > /etc/gpuchain/backup.env
chmod 644 /etc/gpuchain/backup.env

echo "== data"
systemctl stop gpuchain-sepolia gpuchain-sepolia-verifier@1 gpuchain-sepolia-verifier@2 2>/dev/null || true
aws s3 cp "s3://$BUCKET/migration/data.tgz" "$WORK/data.tgz" --only-show-errors
tar -xzf "$WORK/data.tgz" -C "$WORK"
python3 - "$WORK/ekido-data/jobs.db" <<'PY'
import sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
print("jobs:", c.execute("select count(*) from jobs").fetchone()[0])
PY
# DynamicUser units keep their state in /var/lib/private/<name>; systemd fixes ownership when the unit starts.
STATE=/var/lib/private/gpuchain-sepolia
install -d -m 0700 /var/lib/private
install -d -m 0755 "$STATE"
if [ -e "$STATE/jobs.db" ]; then
  mv "$STATE/jobs.db" "$STATE/jobs.db.before-restore-$(date -u +%Y%m%d-%H%M%S)"
fi
cp "$WORK/ekido-data/jobs.db" "$STATE/jobs.db"
mkdir -p "$STATE/artifacts"
cp -r --update=none "$WORK/ekido-data/artifacts/." "$STATE/artifacts/"
echo "artifacts: $(find "$STATE/artifacts" -type f | wc -l) files"

echo "== start"
systemctl start gpuchain-sepolia
for _ in $(seq 1 90); do [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8003/readyz)" = 200 ] && break; sleep 2; done
echo "coordinator readyz: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8003/readyz)"
systemctl start gpuchain-sepolia-verifier@1 gpuchain-sepolia-verifier@2 gpuchain-sepolia-web
sleep 8
systemctl is-active gpuchain-sepolia gpuchain-sepolia-verifier@1 gpuchain-sepolia-verifier@2 gpuchain-sepolia-web caddy | tr '\n' ' '; echo
echo "web: $(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:3101/)"
systemctl start gpuchain-backup.timer gpuchain-monitor.timer
echo "Restore done. Next: point DNS here, then start gpuchain-sepolia-smoke-provider and gpuchain-autodeploy.timer."
