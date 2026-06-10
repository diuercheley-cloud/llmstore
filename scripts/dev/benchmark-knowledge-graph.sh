#!/usr/bin/env bash
set -euo pipefail

echo "Running Knowledge Graph 10k entities performance benchmark..."
PYTHONPATH=.venv:control_plane .venv/bin/pytest -v tests/integration/performance/test_kg_10k_entities.py

echo "Benchmark completed successfully. Summary generated at artifacts/benchmarks/kg-10k-summary.md"
