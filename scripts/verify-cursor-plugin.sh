#!/usr/bin/env bash
# Smoke test for the Cursor plugin manifest (https://github.com/cursor/plugins).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-cursor-plugin.cjs"

if [[ ! -f "$VALIDATOR" ]]; then
  echo "FAIL: validator not found at $VALIDATOR"
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "FAIL: node not found"
  exit 1
fi

node "$VALIDATOR" "$ROOT"

STAGING="$(mktemp -d)"
cleanup() {
  rm -rf "$STAGING"
}
trap cleanup EXIT

# A copy that looks like ~/.cursor/plugins/local/igerd must still validate.
LOCAL_PLUGIN="$STAGING/igerd"
mkdir -p "$LOCAL_PLUGIN/.cursor-plugin"
cp "$ROOT/.cursor-plugin/plugin.json" "$LOCAL_PLUGIN/.cursor-plugin/plugin.json"
cp -R "$ROOT/.agents" "$LOCAL_PLUGIN/.agents"
node "$VALIDATOR" "$LOCAL_PLUGIN"

# Broken name must fail (proves the validator is not a no-op).
BAD="$STAGING/bad-plugin"
mkdir -p "$BAD/.cursor-plugin"
node -e '
const fs = require("fs");
const src = process.argv[1];
const dest = process.argv[2];
const data = JSON.parse(fs.readFileSync(src, "utf8"));
data.name = "Not Valid";
fs.writeFileSync(dest, JSON.stringify(data, null, 2));
' "$LOCAL_PLUGIN/.cursor-plugin/plugin.json" "$BAD/.cursor-plugin/plugin.json"
cp -R "$LOCAL_PLUGIN/.agents" "$BAD/.agents"
if node "$VALIDATOR" "$BAD" >/dev/null 2>&1; then
  echo "FAIL: validator accepted an invalid plugin name"
  exit 1
fi

echo "OK: Cursor plugin validates, local-install layout works, invalid name is rejected"
