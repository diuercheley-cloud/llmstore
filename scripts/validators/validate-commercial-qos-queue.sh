#!/bin/bash
set -e

# Validation script for Phase 24: QoS Priority Queue & Rate Limiting

echo "--- Validating QoS Priority Queue & Rate Limiting ---"

# Check if admin token is set
if [ -z "$ADMIN_TOKEN" ]; then
    echo "Error: ADMIN_TOKEN environment variable not set."
    exit 1
fi

BASE_URL=${BASE_URL:-"http://localhost:8080"}

# 1. Check Queue Overview
echo "Checking QoS Queue Overview..."
curl -s -X GET "$BASE_URL/admin/routing/qos/queue/overview" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | jq .

# 2. Check Rate Limits Overview
echo "Checking QoS Rate Limits Overview..."
curl -s -X GET "$BASE_URL/admin/routing/qos/rate-limits/overview" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | jq .

# 3. Simulate Rate Limit (Free tier)
DUMMY_CLIENT="00000000-0000-0000-0000-000000000001"
echo "Simulating Rate Limit Check for Client $DUMMY_CLIENT (Free)..."
curl -s -X POST "$BASE_URL/admin/routing/qos/rate-limits/simulate?client_id=$DUMMY_CLIENT&qos_tier=Free" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | jq .

# 4. Check Queue Jobs
echo "Listing Priority Queue Jobs..."
curl -s -X GET "$BASE_URL/admin/routing/qos/queue/jobs?limit=5" \
     -H "X-Admin-Token: $ADMIN_TOKEN" | jq .

echo "--- QoS Validation Complete ---"
