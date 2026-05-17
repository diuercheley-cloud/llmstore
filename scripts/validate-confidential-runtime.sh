#!/bin/bash
# Validation script for Phase 47: Confidential Inference Runtime

set -e

echo "Starting Confidential Runtime Validation..."

# 1. Check if models exist
if ! grep -q "CommercialConfidentialRuntimeProfile" control_plane/app/models/commercial_confidential_runtime.py; then
    echo "FAILED: Models not found"
    exit 1
fi

# 2. Check if service exists
if [ ! -f "control_plane/app/services/inference/confidential_runtime.py" ]; then
    echo "FAILED: Service not found"
    exit 1
fi

# 3. Check if endpoints are registered
if ! grep -q "commercial_confidential_runtime_admin_router" control_plane/app/main.py; then
    echo "FAILED: Admin router not registered"
    exit 1
fi

# 4. Run unit tests
echo "Running unit tests..."
docker exec llm-inference-stack-control-plane-1 pytest -q \
    tests/test_confidential_runtime.py \
    tests/test_confidential_logging_controls.py \
    tests/test_confidential_runtime_enforcement.py

echo "Confidential Runtime Validation PASSED!"
