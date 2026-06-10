#!/bin/bash
set -euo pipefail

echo "=== Validating Commercial Report Export ==="

test -f "control_plane/app/services/routing/commercial_report_export.py"
test -f "docs/COMMERCIAL_REPORT_EXPORT.md"

grep -q "/executive-dashboard/export" control_plane/app/api/commercial_routing_admin.py
grep -q "/executive-dashboard/export/preview" control_plane/app/api/commercial_routing_admin.py
grep -q "/executive-dashboard/report-schedules" control_plane/app/api/commercial_routing_admin.py
grep -q "sanitize_report_payload" control_plane/app/services/routing/commercial_report_export.py
grep -q "API keys" docs/COMMERCIAL_REPORT_EXPORT.md

if [ -f ".venv/bin/pytest" ]; then
  ./.venv/bin/pytest -q tests/test_commercial_report_export.py
else
  pytest -q tests/test_commercial_report_export.py
fi

echo "=== Commercial Report Export Validation Successful ==="
