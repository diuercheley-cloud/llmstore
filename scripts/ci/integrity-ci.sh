#!/bin/bash
set -e

# LLM Inference Stack - Integrity CI
# Source of truth: docs/CI_DECISION.md

echo "==> Integrity CI: Alembic Check"
bash scripts/validators/check-alembic-integrity.sh

echo "==> Integrity CI: Working Tree Clean Check"
if [ -f scripts/validators/check-working-tree-clean.sh ]; then 
    bash scripts/validators/check-working-tree-clean.sh
fi

echo "==> Integrity CI: Platform Freeze Check"
make platform-freeze-check
