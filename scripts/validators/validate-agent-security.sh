#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

python3 scripts/validators/validate_internal_security_review.py
python3 scripts/validators/validate_admin_route_auth.py
if command -v ruff >/dev/null 2>&1; then
  ruff check \
    control_plane/app/core/config.py \
    control_plane/app/bootstrap/routers.py \
    control_plane/app/services/agents/browser/browser_policy.py \
    control_plane/app/services/agents/tool_adapters/http_get_tool.py \
    scripts/validators/validate_admin_route_auth.py
else
  echo "ruff not installed; running compileall and AST security checks instead."
  python3 -m compileall -q control_plane/app scripts/validators/validate_admin_route_auth.py
fi
python3 -m pytest -q \
  tests/control_plane/test_admin_router_guard.py \
  tests/control_plane/test_agent_admin_security.py \
  tests/control_plane/test_agent_url_security.py \
  tests/control_plane/test_agent_sandboxed_tools.py
