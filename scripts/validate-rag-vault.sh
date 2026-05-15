#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "== Regulated RAG Vault validation =="

PYTEST_BIN="pytest"
if [[ -x "${ROOT_DIR}/venv/bin/pytest" ]]; then
  PYTEST_BIN="${ROOT_DIR}/venv/bin/pytest"
fi

"${PYTEST_BIN}" -q \
  tests/test_rag_vault.py \
  tests/test_rag_access_control.py \
  tests/test_rag_poison_detection.py \
  tests/test_rag_retrieval_audit.py

echo "Validation completed."
