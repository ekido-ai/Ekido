#!/usr/bin/env bash
# Pull-based continuous deployment for the hosted Base Sepolia network.
#
# Every few minutes (gpuchain-autodeploy.timer) this checks the newest commit on main. It deploys only when every
# required CI check on that commit has passed, and never holds a GitHub credential: the repository is public, so it
# reads the commit, its check runs and the source archive anonymously. Nothing in GitHub can reach into this server.
#
# Python services: refused while a job is unfinished (retried next run); the previous code is backed up and put back
# if /readyz isn't ready within a minute. Web apps: rebuilt with the previous build kept and restored on failure.
# Changes to dependencies (package.json, package-lock.json, pyproject.toml) are never deployed automatically.
set -euo pipefail

REPO="${GPUCHAIN_REPO:-piyushgargog/GPUChain}"
BRANCH="${GPUCHAIN_BRANCH:-main}"
STATE=/var/lib/gpuchain-autodeploy
PUBLIC="$STATE/public"
APP=/opt/gpuchain-sepolia
BACKUPS=/opt/gpuchain-sepolia-backups
WEB_DEPLOY=/opt/gpuchain-ops/gpuchain-web-deploy.sh
REQUIRED='["Python (core)","Python (runtime)","Python (agent)","Python (coordinator)","Python (verifier)","Web app","Contracts"]'
API="https://api.github.com/repos/$REPO"
CURL=(curl -fsS --max-time 30 -H "Accept: application/vnd.github+json" -H "User-Agent: gpuchain-autodeploy")

mkdir -p "$STATE" "$PUBLIC" "$BACKUPS"
chmod 755 "$STATE" "$PUBLIC"
log() { echo "$*"; }
DRY="${DRY_RUN:-0}"   # DRY_RUN=1: check CI and compare code, report what would happen, change nothing
fail() {
  echo "FAILED: $*"
  [ "$DRY" = 1 ] && exit 1
  logger -p err -t gpuchain-autodeploy "$*"; echo "$SHA" > "$STATE/failed"
  # Publish the failure next to the running version, so the GitHub deploy check can stop waiting and say why.
  if [ -f "$PUBLIC/version.json" ]; then
    jq --arg sha "$SHA" --arg why "$*" '. + {failed_sha: $sha, failed_reason: $why}' "$PUBLIC/version.json" > "$PUBLIC/version.json.tmp" \
      && chmod 644 "$PUBLIC/version.json.tmp" && mv "$PUBLIC/version.json.tmp" "$PUBLIC/version.json"
  fi
  exit 1
}

SHA=$(git ls-remote "https://github.com/$REPO" "refs/heads/$BRANCH" | cut -f1)
[ -n "$SHA" ] || { echo "could not read $BRANCH"; exit 1; }
LAST=$(cat "$STATE/deployed" 2>/dev/null || true)
[ "$SHA" = "$LAST" ] && { [ "$DRY" = 1 ] && echo "${SHA:0:7} is already deployed"; exit 0; }
[ "$DRY" != 1 ] && [ "$SHA" = "$(cat "$STATE/failed" 2>/dev/null || true)" ] && exit 0   # don't retry a commit that already failed

# ── 1. CI must be green ────────────────────────────────────────────────────
RUNS=$("${CURL[@]}" "$API/commits/$SHA/check-runs?per_page=100")
VERDICT=$(jq -r --argjson need "$REQUIRED" '
  [.check_runs[] | {name, status, conclusion}] as $runs
  | [$need[] as $n | ($runs | map(select(.name == $n)) | first)] as $mine
  | if any($mine[]; . == null or .status != "completed") then "wait"
    elif all($mine[]; .conclusion == "success") then "green"
    else "red" end' <<<"$RUNS")
case "$VERDICT" in
  wait) log "${SHA:0:7}: CI still running"; exit 0 ;;
  red) fail "${SHA:0:7}: CI failed, not deploying" ;;
esac
log "${SHA:0:7}: CI green"

# ── 2. What changed: compare the new source with what is running, file by file ──
SRC=$(mktemp -d); trap 'rm -rf "$SRC"' EXIT
curl -fsSL --max-time 120 "https://codeload.github.com/$REPO/tar.gz/$SHA" | tar -xz -C "$SRC" --strip-components=1
DIRS=(apps/coordinator/gpuchain_coordinator packages/gpuchain_core/gpuchain_core workers/agent/gpuchain_agent workers/runtime/gpuchain_runtime workers/verifier/gpuchain_verifier)
WEB_LIVE=/opt/GPUchain/.cache/sepolia-release/apps/web-combined
same() { diff -rq --strip-trailing-cr --exclude tests --exclude __pycache__ "$1" "$2" >/dev/null 2>&1; }

# Dependencies are never changed automatically: if the lockfile differs from the one installed, stop here.
for d in "$WEB_LIVE" /opt/GPUchain/apps/web-combined; do
  same "$SRC/apps/web-combined/package-lock.json" "$d/package-lock.json" || fail "${SHA:0:7}: web dependencies changed; deploy this one by hand (see RUNBOOK.md)"
done
if [ -f "$APP/apps/coordinator/pyproject.toml" ] && ! same "$SRC/apps/coordinator/pyproject.toml" "$APP/apps/coordinator/pyproject.toml"; then
  fail "${SHA:0:7}: coordinator dependencies changed; deploy this one by hand (see RUNBOOK.md)"
fi

PY=no; WEB=no
for d in "${DIRS[@]}"; do same "$SRC/$d" "$APP/$d" || PY=yes; done
same "$SRC/infra/gcp/sepolia_coordinator.py" "$APP/infra/gcp/sepolia_coordinator.py" || PY=yes
for p in src public next.config.ts; do same "$SRC/apps/web-combined/$p" "$WEB_LIVE/$p" || WEB=yes; done
log "${SHA:0:7}: python=$PY web=$WEB"
[ "$DRY" = 1 ] && { log "dry run: stopping before any change"; exit 0; }

# ── 3. Python services ──────────────────────────────────────────────────────
UNITS=(gpuchain-sepolia gpuchain-sepolia-verifier@1 gpuchain-sepolia-verifier@2 gpuchain-sepolia-smoke-provider)
ready() { for _ in $(seq 1 60); do [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8003/readyz)" = 200 ] && return 0; sleep 1; done; return 1; }
if [ "$PY" = yes ]; then
  BUSY=$(curl -s --max-time 10 'http://127.0.0.1:8003/jobs?limit=50' | jq '[.[] | select(.state as $s | ["SETTLED","REFUNDED","FAILED","CANCELLED"] | index($s) | not)] | length' 2>/dev/null || echo unknown)
  if [ "$BUSY" != 0 ]; then log "${SHA:0:7}: $BUSY job(s) unfinished or coordinator unreachable; will retry"; exit 0; fi
  K="$BACKUPS/auto-$(date -u +%Y%m%d-%H%M%S)-${LAST:0:7}"
  mkdir -p "$K"
  tar -czf "$K/code.tgz" -C "$APP" "${DIRS[@]}" infra/gcp/sepolia_coordinator.py
  for d in "${DIRS[@]}"; do
    rsync -a --delete --exclude tests --exclude __pycache__ "$SRC/$d/" "$APP/$d/"
  done
  install -m 0644 "$SRC/infra/gcp/sepolia_coordinator.py" "$APP/infra/gcp/sepolia_coordinator.py"
  if ! "$APP/venv/bin/python" -m compileall -q "${DIRS[@]/#/$APP/}" "$APP/infra/gcp/sepolia_coordinator.py" >/dev/null; then
    tar -xzf "$K/code.tgz" -C "$APP"; fail "${SHA:0:7}: code did not compile; previous code restored"
  fi
  systemctl restart "${UNITS[@]}"
  if ! ready; then
    tar -xzf "$K/code.tgz" -C "$APP"; systemctl restart "${UNITS[@]}"; ready || true
    fail "${SHA:0:7}: /readyz not ready after restart; previous code restored"
  fi
  log "${SHA:0:7}: python services deployed (backup $K)"
fi

# ── 4. Web apps ─────────────────────────────────────────────────────────────
if [ "$WEB" = yes ]; then
  TGZ="$STATE/web-src.tgz"
  tar -czf "$TGZ" -C "$SRC/apps/web-combined" src next.config.ts public
  bash "$WEB_DEPLOY" "$TGZ" || fail "${SHA:0:7}: web build failed; previous build kept"
  log "${SHA:0:7}: web apps deployed"
fi

# ── 5. Record it ────────────────────────────────────────────────────────────
echo "$SHA" > "$STATE/deployed"
rm -f "$STATE/failed"
jq -n --arg sha "$SHA" --arg at "$(date -u +%FT%TZ)" --arg py "$PY" --arg web "$WEB" \
  '{sha: $sha, deployed_at: $at, python: ($py == "yes"), web: ($web == "yes")}' > "$PUBLIC/version.json.tmp"
chmod 644 "$PUBLIC/version.json.tmp"; mv "$PUBLIC/version.json.tmp" "$PUBLIC/version.json"
log "${SHA:0:7}: deployed"
