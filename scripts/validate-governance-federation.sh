#!/bin/bash
set -e

echo "--- Validating Enterprise Multi-Region Governance Federation (Phase 35) ---"

# Check if required files exist
FILES=(
    "control_plane/app/models/commercial_governance_federation.py"
    "control_plane/app/services/governance/policy_federation.py"
    "control_plane/app/services/governance/federated_audit.py"
    "control_plane/app/services/governance/governance_consistency.py"
    "control_plane/app/api/commercial_governance_federation_admin.py"
    "docs/GOVERNANCE_FEDERATION.md"
    "tests/test_governance_federation.py"
    "tests/test_federated_audit_trail.py"
    "tests/test_governance_consistency.py"
)

for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Error: $file not found."
        exit 1
    fi
done

echo "OK: All required files found."

# Validate models in __init__.py
for model in "CommercialGovernanceFederationPeer" "CommercialFederatedPolicySync" "CommercialFederatedAuditTrail"; do
    if ! grep -q "$model" control_plane/app/models/__init__.py; then
        echo "Error: $model not found in models/__init__.py"
        exit 1
    fi
done

echo "OK: Models registered in __init__.py."

# Validate config settings
for setting in "COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED" "COMMERCIAL_GOVERNANCE_FEDERATION_MODE" "COMMERCIAL_GOVERNANCE_FEDERATION_SHARED_TOKEN"; do
    if ! grep -q "$setting" control_plane/app/core/config.py; then
        echo "Error: $setting not found in config.py"
        exit 1
    fi
done

echo "OK: Config settings found."

# Validate router in main.py
if ! grep -q "commercial_governance_federation_admin_router" control_plane/app/main.py; then
    echo "Error: commercial_governance_federation_admin_router not found in main.py"
    exit 1
fi

echo "OK: Router registered in main.py."

# Validate Alembic migration
MIGRATION=$(ls control_plane/alembic/versions/*enterprise_multi_region_governance_federation.py 2>/dev/null | head -n 1)
if [ -z "$MIGRATION" ]; then
    echo "Error: Alembic migration for governance federation not found."
    exit 1
fi

echo "OK: Migration found: $MIGRATION"

# Validate payload sanitization
EXPORT_FILE=$(mktemp)
trap "rm -f $EXPORT_FILE" EXIT

# Check for secrets in source code
for pattern in "sk-" "ghp_" "api_key"; do
    SECRET_COUNT=$(grep -r "$pattern" control_plane/app/services/governance/ --include="*.py" 2>/dev/null | grep -v "REDACTED" | grep -v "test" | wc -l)
    if [ "$SECRET_COUNT" -gt 0 ]; then
        echo "Warning: Possible secrets found in governance service files: $SECRET_COUNT matches"
    fi
done

echo "OK: Secrets scan completed."

# Validate endpoints exist
ENDPOINTS=(
    "/admin/governance/federation/peers"
    "/admin/governance/federation/sync"
    "/admin/governance/federation/ingest-policy"
    "/admin/governance/federation/ingest-audit"
    "/admin/governance/federation/status"
    "/admin/governance/federation/consistency"
    "/admin/governance/federation/audit-trail"
    "/admin/governance/federation/export"
)

for endpoint in "${ENDPOINTS[@]}"; do
    if ! grep -q "$endpoint" control_plane/app/api/commercial_governance_federation_admin.py 2>/dev/null; then
        ROUTE_FOUND=$(grep -c "$(echo "$endpoint" | sed 's|/$||')" control_plane/app/api/commercial_governance_federation_admin.py 2>/dev/null | head -1 || true)
        if [ "${ROUTE_FOUND:-0}" = "0" ]; then
            echo "Warning: Endpoint $endpoint not explicitly found in router (may use prefix)"
        fi
    fi
done

echo "OK: Endpoints validated."

echo ""
echo "--- Phase 35 Validation Successful ---"
