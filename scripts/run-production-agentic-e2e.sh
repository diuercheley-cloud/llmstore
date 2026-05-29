#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="${ROOT_DIR}/artifacts/e2e/production-agentic"
PYTEST_BIN="${ROOT_DIR}/.venv/bin/pytest"

if [[ ! -x "${PYTEST_BIN}" ]]; then
  PYTEST_BIN="pytest"
fi

mkdir -p "${ARTIFACT_DIR}"

echo "Starting Agentic Production E2E Suite..."
export PLATFORM_PROFILE=agentic-production
export AGENT_RUNTIME_ENABLED=true
export AGENT_WORKER_ENABLED=true
export PYTHONPATH="${ROOT_DIR}:${ROOT_DIR}/control_plane:${PYTHONPATH:-}"

cat > "${ARTIFACT_DIR}/summary.md" <<'EOF'
# Agentic Production E2E Summary

This suite is allowed to certify only non-mock production claims.
EOF

if rg -n "MockAgentLLMProvider|allow_mocks:\\s*true|# Service exists|# In a real E2E" "${ROOT_DIR}/tests/e2e/production_agentic" --glob '*.py' >/dev/null; then
  cat >> "${ARTIFACT_DIR}/summary.md" <<'EOF'

Status: BLOCKED
Reason: mock-backed or initialization-only tests are still present in tests/e2e/production_agentic.
EOF
  echo "Production E2E suite blocked: mock-backed or initialization-only tests detected." >&2
  exit 1
fi

"${PYTEST_BIN}" "${ROOT_DIR}/tests/e2e/production_agentic/"

echo "Status: PASS" >> "${ARTIFACT_DIR}/summary.md"
echo "E2E Suite Completed. Artifacts generated in ${ARTIFACT_DIR}/"
