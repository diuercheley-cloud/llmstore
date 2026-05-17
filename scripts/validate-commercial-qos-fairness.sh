#!/bin/bash
set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8080"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"admin-token-123"}

echo "--- Validating QoS Fairness & Chargeback (Phase 25) ---"

# 1. Trigger collection
echo "1. Triggering Fairness Metric Collection..."
curl -s -X POST "$API_URL/admin/routing/qos/fairness/collect" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "collected_count"
echo "OK"

# 2. Check Fairness Overview
echo "2. Checking Fairness Overview..."
curl -s "$API_URL/admin/routing/qos/fairness/overview" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "fairness_index"
echo "OK"

# 3. Check Starvation Report
echo "3. Checking Starvation Report..."
curl -s "$API_URL/admin/routing/qos/fairness/starvation" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "\["
echo "OK"

# 4. Trigger Chargeback Calculation
echo "4. Triggering Chargeback Calculation..."
curl -s -X POST "$API_URL/admin/routing/qos/chargeback/calculate" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "calculated_count"
echo "OK"

# 5. Check Chargeback Overview
echo "5. Checking Chargeback Overview..."
curl -s "$API_URL/admin/routing/qos/chargeback/overview" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "total_chargeback_brl"
echo "OK"

# 6. Test Export
echo "6. Testing CSV Export..."
curl -s "$API_URL/admin/routing/qos/chargeback/export?format=csv" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "Entity Type,Entity ID,Amount BRL"
echo "OK"

echo "--- QoS Fairness & Chargeback Validation Complete ---"
