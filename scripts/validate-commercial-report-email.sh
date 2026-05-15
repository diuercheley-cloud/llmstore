#!/bin/bash
set -euo pipefail

echo "=== Validating Commercial Report Email ==="

test -f "control_plane/app/services/routing/commercial_report_email.py"
test -f "control_plane/app/models/commercial_report_delivery_log.py"
test -f "control_plane/alembic/versions/20260514_0035_commercial_report_delivery_logs.py"
test -f "docs/COMMERCIAL_REPORT_EMAIL.md"
test -f "tests/test_commercial_report_email.py"

grep -q "COMMERCIAL_REPORT_SMTP_HOST" control_plane/app/core/config.py
grep -q "send-test-email" control_plane/app/api/commercial_routing_admin.py
grep -q "report-deliveries" control_plane/app/api/commercial_routing_admin.py
grep -q "validate_recipient_allowlist" control_plane/app/services/routing/commercial_report_email.py
grep -q "retry_send_with_backoff" control_plane/app/services/routing/commercial_report_email.py
grep -q "COMMERCIAL_REPORT_EMAIL_ALLOWLIST" docs/COMMERCIAL_REPORT_EMAIL.md

if [ -x ".venv/bin/pytest" ]; then
  ./.venv/bin/pytest -q tests/test_commercial_report_email.py
elif [ -x "venv/bin/pytest" ]; then
  ./venv/bin/pytest -q tests/test_commercial_report_email.py
else
  pytest -q tests/test_commercial_report_email.py
fi

echo "=== Commercial Report Email Validation Successful ==="
