#!/bin/bash
set -e

echo "=== Running Production Agentic E2E Test Suite ==="

if [[ -f ".venv/bin/pytest" ]]; then
  PYTEST_EXE=".venv/bin/pytest"
elif [[ -f "venv/bin/pytest" ]]; then
  PYTEST_EXE="venv/bin/pytest"
else
  PYTEST_EXE="pytest"
fi

PYTHONPATH=.:control_plane $PYTEST_EXE tests/e2e/production_agentic/test_production_agentic_real_e2e.py -v

if [ $? -eq 0 ]; then
    echo "✅ E2E Test Suite Passed."
    exit 0
else
    echo "❌ E2E Test Suite Failed."
    exit 1
fi
