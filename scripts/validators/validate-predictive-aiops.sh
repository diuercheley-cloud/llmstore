#!/bin/bash
set -e

echo "Starting Validation: Phase 66 Predictive AIOps & Failure Forecasting"

# 1. Database Migrations
echo "Checking Alembic migrations..."
grep -r "phase66_predictive_aiops" control_plane/alembic/versions/

# 2. Model Integrity
echo "Checking SQLAlchemy models..."
ls control_plane/app/models/commercial_predictive_aiops.py

# 3. Service Layer
echo "Checking AIOps services..."
ls control_plane/app/services/runtime/predictive_aiops.py
ls control_plane/app/services/runtime/failure_forecasting.py
ls control_plane/app/services/runtime/anomaly_correlation.py
ls control_plane/app/services/runtime/runtime_risk_scoring.py

# 4. API Endpoints
echo "Checking API registration..."
grep "commercial_aiops_admin_router" control_plane/app/main.py

# 5. Dashboard Integration
echo "Checking Admin Dashboard..."
grep "Predictive AIOps" control_plane/app/static/admin/index.html

# 6. Run Tests
echo "Running pytest for Phase 66..."
.venv/bin/pytest tests/test_predictive_aiops.py \
       tests/test_failure_forecasting.py \
       tests/test_anomaly_correlation.py \
       tests/test_runtime_risk_scoring.py

echo "Phase 66 Validation COMPLETED SUCCESSFULY"
