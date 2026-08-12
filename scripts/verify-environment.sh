#!/usr/bin/env bash
# Smoke test for the development environment (zero-dependency Node companion server).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_SCRIPT="$ROOT/.agents/skills/brainstorming/scripts/server.cjs"
PORT="${VERIFY_PORT:-59999}"
HOST="${VERIFY_HOST:-127.0.0.1}"
SESSION_DIR="$(mktemp -d)"
CONTENT_DIR="$SESSION_DIR/content"
STATE_DIR="$SESSION_DIR/state"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$SESSION_DIR"
}
trap cleanup EXIT

if ! command -v node >/dev/null 2>&1; then
  echo "FAIL: node not found"
  exit 1
fi

if [[ ! -f "$SERVER_SCRIPT" ]]; then
  echo "FAIL: server script not found at $SERVER_SCRIPT"
  exit 1
fi

mkdir -p "$CONTENT_DIR" "$STATE_DIR"

BRAINSTORM_DIR="$SESSION_DIR" \
  BRAINSTORM_PORT="$PORT" \
  BRAINSTORM_HOST="$HOST" \
  node "$SERVER_SCRIPT" &
SERVER_PID=$!

for _ in $(seq 1 50); do
  if [[ -f "$STATE_DIR/server-info" ]]; then
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "FAIL: server exited before startup"
    exit 1
  fi
  sleep 0.1
done

if [[ ! -f "$STATE_DIR/server-info" ]]; then
  echo "FAIL: server did not write server-info within 5s"
  exit 1
fi

cat >"$CONTENT_DIR/smoke.html" <<'EOF'
<h2>Environment smoke test</h2>
<p class="subtitle">If you see this, HTTP serving works.</p>
EOF

sleep 0.2
BODY="$(curl -fsS "http://${HOST}:${PORT}/")"

if ! grep -q "Environment smoke test" <<<"$BODY"; then
  echo "FAIL: expected screen content not found in HTTP response"
  exit 1
fi

if ! grep -q "new WebSocket" <<<"$BODY"; then
  echo "FAIL: helper script not injected"
  exit 1
fi

STATUS="$(curl -s -o /dev/null -w '%{http_code}' "http://${HOST}:${PORT}/missing")"
if [[ "$STATUS" != "404" ]]; then
  echo "FAIL: expected 404 for unknown path, got $STATUS"
  exit 1
fi

echo "OK: node $(node --version), companion server HTTP smoke test passed on ${HOST}:${PORT}"
