#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Phase 59: Offline Sovereign Model Lifecycle Validation ==="

echo ""
echo "1. Syntax checking Python files..."
python3 -m py_compile "$PROJECT_ROOT/control_plane/app/models/commercial_model_lifecycle.py" && echo "  OK: models" || echo "  FAIL: models"
python3 -m py_compile "$PROJECT_ROOT/control_plane/app/services/models/model_lifecycle_manager.py" && echo "  OK: model_lifecycle_manager" || echo "  FAIL: model_lifecycle_manager"
python3 -m py_compile "$PROJECT_ROOT/control_plane/app/services/models/model_promotion.py" && echo "  OK: model_promotion" || echo "  FAIL: model_promotion"
python3 -m py_compile "$PROJECT_ROOT/control_plane/app/services/models/model_lineage.py" && echo "  OK: model_lineage" || echo "  FAIL: model_lineage"
python3 -m py_compile "$PROJECT_ROOT/control_plane/app/services/models/model_quarantine.py" && echo "  OK: model_quarantine" || echo "  FAIL: model_quarantine"
python3 -m py_compile "$PROJECT_ROOT/control_plane/app/api/commercial_model_lifecycle_admin.py" && echo "  OK: api" || echo "  FAIL: api"
python3 -m py_compile "$PROJECT_ROOT/control_plane/alembic/archive/20260515_phase59_offline_model_lifecycle.py" && echo "  OK: migration" || echo "  FAIL: migration"

echo ""
echo "2. Running unit tests..."
cd "$PROJECT_ROOT"
python3 -m pytest tests/test_model_lifecycle.py tests/test_model_promotion.py tests/test_model_lineage.py tests/test_model_quarantine.py -v --tb=short 2>&1 | tail -30

echo ""
echo "=== Validation complete ==="
