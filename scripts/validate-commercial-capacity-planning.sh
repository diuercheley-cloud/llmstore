#!/bin/bash
set -e

# Validation script for Phase 21: Capacity Planning + Predictive Autoscaling Commercial

echo "--- Validating Capacity Planning (Phase 21) ---"

# 1. Check if endpoints are registered (dry run/mock check)
echo "Checking API endpoints..."
# In a real environment we would use curl, but here we'll check the main.py or similar
grep -q "commercial_capacity_admin" control_plane/app/main.py && echo "✅ API router registered" || echo "❌ API router missing"

# 2. Check Models
echo "Checking Models..."
ls control_plane/app/models/commercial_capacity.py > /dev/null && echo "✅ Models created"

# 3. Check Services
echo "Checking Services..."
ls control_plane/app/services/routing/commercial_capacity_monitor.py > /dev/null && echo "✅ Monitor service created"
ls control_plane/app/services/routing/commercial_capacity_forecasting.py > /dev/null && echo "✅ Forecasting service created"
ls control_plane/app/services/routing/commercial_autoscaling.py > /dev/null && echo "✅ Autoscaling service created"

# 4. Check Migrations
echo "Checking Migrations..."
ls control_plane/alembic/versions/*capacity_planning.py > /dev/null && echo "✅ Migration created"

# 5. Run Tests
echo "Running tests..."
if [ -f ".venv/bin/pytest" ]; then
  PYTHONPATH=control_plane .venv/bin/pytest -q tests/test_commercial_capacity_planning.py
  echo "✅ Tests passed"
else
  echo "⚠️ pytest not found in .venv, skipping execution but files exist."
fi

# 6. Check Documentation
echo "Checking Documentation..."
[ -f "docs/COMMERCIAL_CAPACITY_PLANNING.md" ] && echo "✅ Documentation exists" || echo "⚠️ Documentation missing"

echo "--- Validation Complete ---"
