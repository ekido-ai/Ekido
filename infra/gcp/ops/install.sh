#!/usr/bin/env bash
# Installs the backup and monitor timers, runs each once, and prints their results.
set -euo pipefail
sudo mkdir -p /opt/gpuchain-ops
cd "$(dirname "$0")"
sudo install -m 755 gpuchain-backup.sh gpuchain-monitor.sh /opt/gpuchain-ops/
sudo install -m 644 gpuchain-backup.service gpuchain-backup.timer gpuchain-monitor.service gpuchain-monitor.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gpuchain-backup.timer gpuchain-monitor.timer
sudo systemctl start gpuchain-backup.service gpuchain-monitor.service
sudo journalctl -u gpuchain-backup.service -n 3 --no-pager -o cat
sudo cat /var/lib/gpuchain-monitor/last.json
systemctl list-timers 'gpuchain-*' --no-pager | head -5
