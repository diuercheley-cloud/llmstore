#!/bin/bash
# Validation script for Phase 50: Confidential Multi-Agent Governance

set -e

echo "Starting Confidential Multi-Agent Governance Validation..."

# 1. Check if models exist
if ! grep -q "CommercialAgentProfile" control_plane/app/models/commercial_agents.py; then
    echo "FAILED: Models not found"
    exit 1
fi

# 2. Check if service exists
if [ ! -f "control_plane/app/services/inference/agent_governance.py" ]; then
    echo "FAILED: Service not found"
    exit 1
fi

# 3. Check if endpoints are registered
if ! grep -q "commercial_agents_admin_router" control_plane/app/main.py; then
    echo "FAILED: Admin router not registered"
    exit 1
fi

# 4. Run unit tests
echo "Running unit tests..."
docker exec llm-inference-stack-control-plane-1 pytest -q tests/test_agent_governance.py

echo "Confidential Multi-Agent Governance Validation PASSED!"
