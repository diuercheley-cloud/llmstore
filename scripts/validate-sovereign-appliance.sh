#!/bin/bash
# Validation script for Phase 52: Sovereign Offline AI Appliance Mode

set -e

echo "Starting Sovereign Appliance Validation..."

# 1. Check if models exist
if ! grep -q "CommercialApplianceProfile" control_plane/app/models/commercial_appliance.py; then
    echo "FAILED: Models not found"
    exit 1
fi

# 2. Check if service exists
if [ ! -f "control_plane/app/services/inference/sovereign_appliance.py" ]; then
    echo "FAILED: Service not found"
    exit 1
fi

# 3. Check if endpoints are registered
if ! grep -q "commercial_appliance_admin_router" control_plane/app/main.py; then
    echo "FAILED: Admin router not registered"
    exit 1
fi

# 4. Run unit tests
echo "Running unit tests..."
docker exec llm-inference-stack-control-plane-1 pytest -q tests/test_sovereign_appliance.py

echo "Sovereign Appliance Validation PASSED!"
