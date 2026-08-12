#!/usr/bin/env bash
# Smoke test for install.sh (local plugin install path used in dev/CI).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="$ROOT/install.sh"
DEST="$(mktemp -d)"

cleanup() {
  rm -rf "$DEST"
}
trap cleanup EXIT

if [[ ! -f "$INSTALLER" ]]; then
  echo "FAIL: install.sh not found at $INSTALLER"
  exit 1
fi

for shell in sh bash; do
  if ! "$shell" -n "$INSTALLER"; then
    echo "FAIL: $shell -n install.sh"
    exit 1
  fi
done

LIST_OUT="$(sh "$INSTALLER" --local "$ROOT" --list)"
if ! grep -q "brainstorming" <<<"$LIST_OUT"; then
  echo "FAIL: --list did not mention brainstorming"
  echo "$LIST_OUT"
  exit 1
fi
if ! grep -q "using-superpowers" <<<"$LIST_OUT"; then
  echo "FAIL: --list did not mention using-superpowers"
  echo "$LIST_OUT"
  exit 1
fi

sh "$INSTALLER" --local "$ROOT" --dry-run --dir "$DEST" >/dev/null

sh "$INSTALLER" --local "$ROOT" --dir "$DEST" --quiet

for skill in brainstorming using-superpowers; do
  if [[ ! -f "$DEST/$skill/SKILL.md" ]]; then
    echo "FAIL: expected $DEST/$skill/SKILL.md after install"
    exit 1
  fi
done

if [[ ! -f "$DEST/brainstorming/scripts/server.cjs" ]]; then
  echo "FAIL: brainstorming companion scripts not installed"
  exit 1
fi

sh "$INSTALLER" --local "$ROOT" --dir "$DEST" --uninstall --quiet

for skill in brainstorming using-superpowers; do
  if [[ -d "$DEST/$skill" ]]; then
    echo "FAIL: $skill still present after uninstall"
    exit 1
  fi
done

echo "OK: install.sh local install, list, dry-run, and uninstall passed"
