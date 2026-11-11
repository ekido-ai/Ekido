#!/usr/bin/env bash
# Rebuilds both web apps from a source archive (src, next.config.ts, public). Used by gpuchain-autodeploy.sh and by hand.
#   gpuchain-web-deploy.sh /path/to/web-src.tgz
# The previous src, .next and next.config.ts are kept outside the app. A service is restarted only after its build
# succeeds; on a failed build the previous files are put back. Exits non-zero if any build failed.
set -u
TGZ="${1:?usage: gpuchain-web-deploy.sh <web-src.tgz>}"
STAMP=$(date +%Y%m%d-%H%M%S)
FAILED=0
deploy() {
  local dir=$1 svc=$2; shift 2
  echo "== $svc in $dir"
  cd "$dir" || { FAILED=1; return; }
  local bk="/opt/GPUchain-web-backups/$svc"
  mkdir -p "$bk" && chown gpuchain "$bk" /opt/GPUchain-web-backups
  for old in src.bak-* src.failed-* .next.bak-* .next.failed-* next.config.ts.bak-*; do [ -e "$old" ] && sudo -u gpuchain mv "$old" "$bk/"; done
  sudo -u gpuchain cp -a src "$bk/src.bak-$STAMP"
  sudo -u gpuchain cp -a .next "$bk/.next.bak-$STAMP"
  sudo -u gpuchain cp next.config.ts "$bk/next.config.ts.bak-$STAMP"
  sudo -u gpuchain mv src "$bk/src.replaced-$STAMP"
  sudo -u gpuchain tar -xzf "$TGZ" src next.config.ts public
  if sudo -u gpuchain env "$@" npx next build > "/tmp/build-$svc.log" 2>&1; then
    systemctl restart "$svc"
    sleep 4
    echo "built and restarted: $(systemctl is-active "$svc")"
  else
    FAILED=1
    echo "BUILD FAILED, restoring"; tail -20 "/tmp/build-$svc.log"
    sudo -u gpuchain mv src "$bk/src.failed-$STAMP"; sudo -u gpuchain cp -a "$bk/src.bak-$STAMP" src
    sudo -u gpuchain mv .next "$bk/.next.failed-$STAMP"; sudo -u gpuchain cp -a "$bk/.next.bak-$STAMP" .next
    sudo -u gpuchain cp "$bk/next.config.ts.bak-$STAMP" next.config.ts
  fi
}
deploy /opt/GPUchain/.cache/sepolia-release/apps/web-combined gpuchain-sepolia-web \
  NEXT_PUBLIC_COORDINATOR_URL=https://gpuchain.duckdns.org/sepolia \
  "NEXT_PUBLIC_COORDINATOR_WS=wss://gpuchain.duckdns.org/sepolia/ws/jobs/{job}" \
  NEXT_PUBLIC_EVENT_SOURCE=live NEXT_PUBLIC_CHAIN_ID=84532 NEXT_PUBLIC_SIGNED_JOBS=1 \
  NEXT_PUBLIC_ESCROW_ADDRESS=0x1BF65f755457a92850009c88AFb337Ec57745a22
deploy /opt/GPUchain/apps/web-combined gpuchain-web \
  NEXT_PUBLIC_COORDINATOR_URL=https://api.34-93-70-171.sslip.io \
  "NEXT_PUBLIC_COORDINATOR_WS=wss://api.34-93-70-171.sslip.io/ws/jobs/{job}" \
  NEXT_PUBLIC_EVENT_SOURCE=live NEXT_PUBLIC_CHAIN_ID=31337
for u in https://gpuchain.duckdns.org/ https://gpuchain.duckdns.org/chain https://34-93-70-171.sslip.io/; do
  echo "$u $(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$u")"
done
exit $FAILED
