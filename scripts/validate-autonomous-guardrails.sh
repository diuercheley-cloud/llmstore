#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m py_compile \
  control_plane/app/models/commercial_autonomous_guardrails.py \
  control_plane/app/services/governance/autonomous_guardrails.py \
  control_plane/app/services/governance/autonomous_execution_limits.py \
  control_plane/app/services/governance/blast_radius_analysis.py \
  control_plane/app/services/governance/human_checkpointing.py \
  control_plane/app/api/commercial_autonomous_guardrails_admin.py \
  control_plane/app/services/security/trust_graph.py

test -f docs/AUTONOMOUS_GUARDRAILS.md
test -f tests/test_autonomous_guardrails.py
test -f tests/test_blast_radius_analysis.py
test -f tests/test_human_checkpointing.py
test -f tests/test_autonomous_execution_limits.py

if [[ -x "./venv/bin/pytest" ]]; then
  ./venv/bin/pytest \
    tests/test_autonomous_guardrails.py \
    tests/test_blast_radius_analysis.py \
    tests/test_human_checkpointing.py \
    tests/test_autonomous_execution_limits.py
else
  pytest \
    tests/test_autonomous_guardrails.py \
    tests/test_blast_radius_analysis.py \
    tests/test_human_checkpointing.py \
    tests/test_autonomous_execution_limits.py
fi
