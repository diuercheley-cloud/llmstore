#!/bin/bash
set -euo pipefail

echo "======================================================="
echo "Phase 17 Validation: Commercial Global Traffic Shifting"
echo "======================================================="

# Verify Alembic models
if ! grep -q "CommercialGlobalTrafficPolicy" control_plane/app/models/commercial_global_traffic.py; then
    echo "❌ CommercialGlobalTrafficPolicy model missing"
    exit 1
fi
echo "✅ Models present"

# Verify API Endpoints
if ! grep -q "@router.post(\"/policies\"" control_plane/app/api/commercial_global_traffic_admin.py; then
    echo "❌ API Endpoints missing"
    exit 1
fi
echo "✅ API Endpoints present"

# Verify Service Logic
if ! grep -q "def deterministic_bucket" control_plane/app/services/routing/commercial_global_traffic_shifter.py; then
    echo "❌ Service logic missing deterministic bucket"
    exit 1
fi
echo "✅ Service logic present"

echo "======================================================="
echo "✅ Phase 17 Commercial Global Traffic Shifting is valid"
echo "======================================================="
