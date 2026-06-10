#!/bin/bash
# Validation script for Phase 53: Regulated RAG Vault

set -e

echo "Starting Confidential RAG Vault Validation..."

# 1. Check if models exist
if ! grep -q "CommercialRAGVault" control_plane/app/models/commercial_rag.py; then
    echo "FAILED: Models not found"
    exit 1
fi

# 2. Check if service exists
if [ ! -f "control_plane/app/services/rag/confidential_rag_vault.py" ]; then
    echo "FAILED: Service not found"
    exit 1
fi

# 3. Check if endpoints are registered
if ! grep -q "commercial_rag_admin_router" control_plane/app/main.py; then
    echo "FAILED: Admin router not registered"
    exit 1
fi

# 4. Run unit tests
echo "Running unit tests..."
docker exec llm-inference-stack-control-plane-1 pytest -q tests/test_confidential_rag_vault.py tests/test_retrieval_receipts.py tests/test_rag_lineage.py tests/test_rag_policy_enforcement.py

echo "Confidential RAG Vault Validation PASSED!"
