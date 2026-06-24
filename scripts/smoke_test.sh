#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# smoke_test.sh — Pre-commit / CI guard rail
#
# Verifies the application actually boots and serves content.
# Run AFTER ``make up`` (all containers running) or ``make dev`` (local).
#
# Usage:
#   bash scripts/smoke_test.sh [base_url]
#
# Default base_url: http://localhost:8000
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE="${1:-http://localhost:8000}"
PASS=0
FAIL=0

green()  { printf "  ✓ %s\n" "$1"; }
red()    { printf "  ✗ %s\n" "$1"; ((FAIL++)); }
check()  { local label="$1"; shift; if "$@" &>/dev/null; then green "$label"; ((PASS++)); else red "$label"; return 1; fi }

echo ""
echo "── Smoke Tests ──────────────────────────────────────────────"
echo ""

# 1. Health endpoint
check "Health endpoint returns 200" \
  curl -sSf "${BASE}/healthz" -o /dev/null

# 2. Home page
check "Home page renders" \
  curl -s "${BASE}/" | grep -q "Sign in"

# 3. Login page
check "Login page renders" \
  curl -s "${BASE}/login" | grep -q "Sign in\|Login"

# 4. Static assets served
check "Static CSS served" \
  curl -sSf "${BASE}/static/app.css" -o /dev/null

# 5. CSP security header present
check "CSP header on responses" \
  curl -sI "${BASE}/" | grep -qi "content-security-policy"

# 6. CSRF protection active (POST without token -> 403)
check "CSRF rejects unauthenticated POST" \
  [ "$(curl -s -o /dev/null -w '%{http_code}' -X POST "${BASE}/logout")" = "403" ]

# 7. G10: Form data persists through full middleware stack
# POST /login/dev with form data, following redirect, verify display_name renders.
# Verifies BodyCacheMiddleware replays the body correctly — if the body is consumed
# by CSRF middleware and not replayed, the route handler gets empty form data and
# the display_name defaults to "Dev User" instead of our test value.
check "Form POST data persists through middleware stack" \
  bash -c '
    COOKIE_JAR=$(mktemp)
    # Step 1: GET /login to seed CSRF token in session
    curl -s -L -c "$COOKIE_JAR" "${BASE}/login" > /dev/null 2>&1
    # Step 2: POST dev login with test data (dev login is CSRF-exempt in dev mode)
    RESP=$(curl -s -L -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      -X POST "${BASE}/login/dev" \
      -d "email=smoke-test-body-cache@polyglot.dev" \
      -d "display_name=SmokeBodyCacheTest")
    rm -f "$COOKIE_JAR"
    # Step 3: Verify the display_name appears in the response
    echo "$RESP" | grep -q "SmokeBodyCacheTest"
  '

echo ""
echo "── Results ──────────────────────────────────────────────────"
echo "  Passed: ${PASS}"
echo "  Failed: ${FAIL}"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "❌ Smoke tests FAILED — do not ship."
  exit 1
else
  echo "✅ All smoke tests passed."
fi
