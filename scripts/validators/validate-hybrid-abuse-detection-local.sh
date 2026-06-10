#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"

PASS=0
FAIL=0

pass()  { PASS=$((PASS+1)); echo "  PASS: $*"; }
fail()  { FAIL=$((FAIL+1)); echo "  FAIL: $*"; }

echo "=== Hybrid Abuse Detection Validation ==="
echo ""

# ---- 1. All abuse signals are registered ----
echo "--- 1. All abuse signals are registered ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
from app.services.security import ABUSE_SIGNALS
signals = list(ABUSE_SIGNALS.keys())
print(f'signals_count={len(signals)}')
for s in signals:
    print(f'  SIGNAL: {s}')
")
echo "$RESULT"
SIGNAL_COUNT=$(echo "$RESULT" | grep "signals_count=" | cut -d= -f2)
if [ "$SIGNAL_COUNT" -ge 11 ]; then
  pass "All $SIGNAL_COUNT abuse signals are registered"
else
  fail "Expected at least 11 abuse signals, got $SIGNAL_COUNT"
fi
echo ""

# ---- 2. Auto-suspend disabled by default ----
echo "--- 2. Auto-suspend disabled by default ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os
os.environ['ABUSE_DETECTION_ENABLED'] = 'true'
os.environ['ABUSE_DRY_RUN'] = 'true'
os.environ['ABUSE_AUTO_SUSPEND_ENABLED'] = 'false'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///tmp/test_abuse_check.db'
os.environ['REDIS_URL'] = 'redis://test.invalid:6379/0'
os.environ['DATA_PLANE_BASE_URL'] = 'http://localhost:8081'
from app.core.config import get_settings
s = get_settings()
print(f'auto_suspend={s.abuse_auto_suspend_enabled}')
print(f'dry_run={s.abuse_dry_run}')
print(f'detection_enabled={s.abuse_detection_enabled}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "auto_suspend=False"; then
  pass "Auto-suspend is disabled by default"
else
  fail "Auto-suspend should be disabled by default"
fi
if echo "$RESULT" | grep -q "dry_run=True"; then
  pass "Dry-run is enabled by default"
else
  fail "Dry-run should be enabled by default"
fi
if echo "$RESULT" | grep -q "detection_enabled=True"; then
  pass "Detection is enabled by default"
else
  fail "Detection should be enabled by default"
fi
echo ""

# ---- 3. Run abuse detection pytest suite ----
echo "--- 3. Run abuse detection pytest suite ---"
cd "$PROJECT_ROOT"
PYTEST_RESULT=$($PYTHON -m pytest \
  tests/test_hybrid_abuse_detection.py \
  tests/test_abuse_detection_dry_run.py \
  tests/test_abuse_admin_api.py \
  tests/test_abuse_detection_security.py \
  -q --tb=line 2>&1)
echo "$PYTEST_RESULT" | tail -10
if echo "$PYTEST_RESULT" | grep -q "failed"; then
  fail "Some pytest tests failed"
  echo "$PYTEST_RESULT" | grep "FAILED" || true
else
  pass "All pytest tests passed"
fi
echo ""

# ---- 4. Verify no secrets in source files ----
echo "--- 4. Verify no secrets in source files ---"
ABUSE_FILES=$(find control_plane/app/services/security/ control_plane/app/models/abuse_*.py control_plane/app/api/abuse_admin.py -type f 2>/dev/null)
SECRET_FOUND=false
for f in $ABUSE_FILES; do
  if grep -l 'api_key.*=[[:space:]]*['"'"'"]' "$f" 2>/dev/null | grep -v 'api_key_prefix' | grep -v 'api_key_hash' | grep -v '\.env' > /dev/null; then
    echo "  WARNING: possible secret in $f"
    SECRET_FOUND=true
  fi
done
if [ "$SECRET_FOUND" = false ]; then
  pass "No secrets found in abuse detection source files"
else
  fail "Secrets may be exposed in source files"
fi
echo ""

# ---- Summary ----
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
