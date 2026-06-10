#!/bin/bash
# Validation script for Phase 46: Public Attestation Gateway

set -e

echo "Starting Public Attestation Gateway Validation..."

# 1. Check if models exist
if ! grep -q "CommercialPublicAttestationRequest" control_plane/app/models/commercial_attestation.py; then
    echo "FAILED: Models not found"
    exit 1
fi

# 2. Check if service exists
if [ ! -f "control_plane/app/services/inference/public_attestation_gateway.py" ]; then
    echo "FAILED: Service not found"
    exit 1
fi

# 3. Check if endpoints are registered
if ! grep -q "commercial_attestation_public_router" control_plane/app/main.py; then
    echo "FAILED: Public router not registered"
    exit 1
fi

# 4. Run unit tests
echo "Running unit tests..."
docker exec llm-inference-stack-control-plane-1 pytest -q tests/test_public_attestation_gateway.py

# 5. Check verifier CLI update
if ! grep -q "verify-online" tools/public_verifier/verifier_cli.py; then
    echo "FAILED: Verifier CLI not updated"
    exit 1
fi

echo "Public Attestation Gateway Validation PASSED!"
