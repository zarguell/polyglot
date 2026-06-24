#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# check_config.sh — Guard rail: ban os.getenv outside app/core/config.py
#
# Usage:
#   bash scripts/check_config.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# Only flag actual os.getenv() calls (with opening paren), not docstring references.
VIOLATIONS=$(grep -rn "os\.getenv(" app/ --include="*.py" \
  | grep -v "app/core/config.py" \
  | grep -v "noqa: config" \
  || true)

if [ -n "$VIOLATIONS" ]; then
  echo "❌ os.getenv/os.environ used outside app/core/config.py:"
  echo "$VIOLATIONS"
  echo ""
  echo "Fix: Add the setting to app/core/config.py and use settings.xxx instead."
  exit 1
else
  echo "✅ No os.getenv outside core/config"
fi
