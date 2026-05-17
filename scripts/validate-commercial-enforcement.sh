#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "[validate-commercial-enforcement] Executando suite de enforcement local/offline..."
./venv/bin/pytest -q tests/test_commercial_guardrails_enforcement.py

echo "[validate-commercial-enforcement] Enforcement validado sem chamadas cloud reais."
