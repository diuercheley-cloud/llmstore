#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "== Retrieval Proofs validation =="

PYTEST_BIN="pytest"
if [[ -x "${ROOT_DIR}/venv/bin/pytest" ]]; then
  PYTEST_BIN="${ROOT_DIR}/venv/bin/pytest"
fi

"${PYTEST_BIN}" -q tests/test_retrieval_proofs.py

echo "Retrieval proofs validation completed."
