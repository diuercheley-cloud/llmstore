#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

RELEASE_TAG="${1:-${GA_RELEASE_TAG:-v2.0.1-agentic-operational-maturity}}"
PYTHON_EXEC="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_EXEC}" ]]; then
  PYTHON_EXEC="python3"
fi

export PYTHONPATH="${ROOT_DIR}/control_plane:${PYTHONPATH:-}"

"${PYTHON_EXEC}" - "${RELEASE_TAG}" <<'PY'
import json
import sys

from app.services.platform.ga_readiness import GAReadinessService

release_tag = sys.argv[1]
service = GAReadinessService(config_path="config/ga-readiness-rules.yaml")
state = service.collect_current_state()

platform_result = service.generate_report(state, filepath="artifacts/platform/ga-readiness.md")
service.generate_report(
    state,
    filepath=f"artifacts/releases/{release_tag}/ga-readiness.md",
)

print(json.dumps({
    "release_tag": release_tag,
    "status": platform_result["maturity_level"],
    "score": platform_result["score"],
    "total_possible": platform_result["total_possible"],
    "failed_criteria": platform_result["failed_criteria"],
}, indent=2))

if platform_result["score"] != platform_result["total_possible"]:
    sys.exit(1)
PY
