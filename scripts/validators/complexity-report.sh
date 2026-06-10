#!/bin/bash
# scripts/validators/complexity-report.sh
# Entrypoint for running the platform complexity analyzer and generating markdown reports.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "=========================================================="
echo "      LLM Inference Stack - System Complexity Report      "
echo "=========================================================="

# Check for virtualenv Python
PYTHON_EXEC="python3"
if [ -f ".venv/bin/python3" ]; then
    PYTHON_EXEC=".venv/bin/python3"
elif [ -f "venv/bin/python3" ]; then
    PYTHON_EXEC="venv/bin/python3"
fi

# Run the python analyzer
PYTHONPATH="${ROOT_DIR}/control_plane" ${PYTHON_EXEC} scripts/dev/lib/complexity_analyzer.py

echo ""
echo "Relatórios gerados com sucesso sob artifacts/complexity/latest/:"
echo " - summary.md        (Métricas Gerais)"
echo " - api-surface.md    (Routers & Endpoints)"
echo " - services.md       (Services & Cobertura de Testes)"
echo " - models.md         (SQLAlchemy Models)"
echo " - scripts.md        (Scripts & Duplicações)"
echo " - feature-flags.md  (Feature Flags Governance)"
echo " - recommendations.md (Recomendações de Refatoração)"
echo "=========================================================="
