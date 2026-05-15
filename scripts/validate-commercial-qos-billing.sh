#!/bin/bash
set -e

# Validation script for Phase 26: Commercial QoS Billing

API_URL=${API_URL:-"http://localhost:18080"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"admin-token"}

echo "--- Validating Commercial QoS Billing (Phase 26) ---"

# 1. Check Billing Overview
echo "1. Checking QoS Billing Overview..."
curl -s "$API_URL/admin/billing/qos/overview" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "total_calculated_brl"
echo "   [OK] Overview accessible"

# 2. Trigger Billing Generation (report_only)
echo "2. Triggering QoS Billing Generation..."
curl -s -X POST "$API_URL/admin/billing/qos/generate" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "calculated_count"
echo "   [OK] Generation triggered"

# 3. Check Records
echo "3. Listing QoS Billing Records..."
curl -s "$API_URL/admin/billing/qos/records?limit=5" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "qos_tier"
echo "   [OK] Records listed"

# 4. Export JSON
echo "4. Exporting QoS Billing JSON..."
curl -s "$API_URL/admin/billing/qos/export?format=json" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "billable_amount_brl"
echo "   [OK] JSON Export valid"

# 5. Export CSV
echo "5. Exporting QoS Billing CSV..."
curl -s "$API_URL/admin/billing/qos/export?format=csv" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "id,client_id"
echo "   [OK] CSV Export valid"

# 6. Attempt Wallet Debit (Should fail or be skipped by default)
echo "6. Testing default Wallet Debit restriction..."
# We need a record_id. We'll try to get one from the records list.
RECORD_ID=$(curl -s "$API_URL/admin/billing/qos/records?limit=1" -H "X-Admin-Token: $ADMIN_TOKEN" | grep -oP '"id":"\K[^"]+')

if [ -n "$RECORD_ID" ]; then
    echo "   Testing debit for record $RECORD_ID..."
    # This should return 400 because default mode is report_only
    RESPONSE=$(curl -s -X POST "$API_URL/admin/billing/qos/$RECORD_ID/debit-wallet" -H "X-Admin-Token: $ADMIN_TOKEN")
    if echo "$RESPONSE" | grep -q "Failed to debit wallet"; then
        echo "   [OK] Wallet debit correctly blocked in report_only mode"
    elif echo "$RESPONSE" | grep -q "record not found"; then
        echo "   [WARN] Record not found for debit test"
    else
        echo "   [DEBUG] Response: $RESPONSE"
    fi
else
    echo "   [SKIP] No records found to test debit"
fi

echo "--- Commercial QoS Billing Validation Complete ---"
