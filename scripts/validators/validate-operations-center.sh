#!/usr/bin/env bash
set -euo pipefail

echo "[operations-center] validating source files"
python3 -m py_compile \
  control_plane/app/models/commercial_trust_graph.py \
  control_plane/app/models/commercial_operations_center.py \
  control_plane/app/models/commercial_trust_violation.py \
  control_plane/app/services/security/trust_graph.py \
  control_plane/app/services/security/cryptographic_topology.py \
  control_plane/app/services/security/trust_snapshotting.py \
  control_plane/app/services/security/trust_violation_detection.py \
  control_plane/app/api/commercial_operations_center.py

echo "[operations-center] validating docs and tests"
test -f docs/OPERATIONS_CENTER.md
test -f tests/test_trust_graph.py
test -f tests/test_operations_center.py
test -f tests/test_trust_snapshotting.py
test -f tests/test_trust_violation_detection.py

PYTEST_BIN="pytest"
if [[ -x "./venv/bin/pytest" ]]; then
  PYTEST_BIN="./venv/bin/pytest"
fi

echo "[operations-center] running focused pytest"
"${PYTEST_BIN}" -q \
  tests/test_trust_graph.py \
  tests/test_operations_center.py \
  tests/test_trust_snapshotting.py \
  tests/test_trust_violation_detection.py

echo "[operations-center] validation completed"
