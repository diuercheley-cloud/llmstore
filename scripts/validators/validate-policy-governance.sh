#!/bin/bash
set -e

echo "--- Validating Enterprise Policy Governance (Phase 34) ---"

# Check if required files exist
FILES=(
    "control_plane/app/models/commercial_governance.py"
    "control_plane/app/services/governance/policy_registry.py"
    "control_plane/app/services/governance/policy_engine.py"
    "control_plane/app/api/commercial_policy_governance_admin.py"
    "docs/POLICY_GOVERNANCE.md"
)

for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Error: $file not found."
        exit 1
    fi
done

echo "OK: All required files found."

# Validate models in __init__.py
if ! grep -q "CommercialPolicyBundle" control_plane/app/models/__init__.py; then
    echo "Error: CommercialPolicyBundle not found in models/__init__.py"
    exit 1
fi

echo "OK: Models registered."

# Validate router in main.py
if ! grep -q "commercial_policy_governance_admin_router" control_plane/app/main.py; then
    echo "Error: commercial_policy_governance_admin_router not found in main.py"
    exit 1
fi

echo "OK: Router registered."

# Validate Alembic migration
MIGRATION=$(ls control_plane/alembic/versions/*enterprise_policy_governance.py | head -n 1)
if [ -z "$MIGRATION" ]; then
    echo "Error: Alembic migration for enterprise_policy_governance not found."
    exit 1
fi

echo "OK: Migration found: $MIGRATION"

echo "--- Phase 34 Validation Successful ---"
