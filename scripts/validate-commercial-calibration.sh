#!/bin/bash
set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8080"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"dev-admin-token"}

echo "--- Validating Commercial Calibration (Phase 6) ---"

# 1. Check calibration report endpoint
echo "Checking Calibration Report..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/admin/routing/calibration/report?days=1" \
  -H "X-Admin-Token: $ADMIN_TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "✅ Calibration Report: SUCCESS"
  # Check if body contains expected fields
  if echo "$BODY" | grep -q "global_error_summary" && echo "$BODY" | grep -q "recommended_cost_multipliers"; then
    echo "✅ Calibration Report Schema: VALID"
  else
    echo "❌ Calibration Report Schema: INVALID"
    echo "$BODY"
    exit 1
  fi
else
  echo "❌ Calibration Report: FAILED (HTTP $HTTP_CODE)"
  echo "$BODY"
  exit 1
fi

# 2. Check calibration simulate endpoint
echo "Checking Calibration Simulation..."
SIM_PAYLOAD='{
  "provider": "openai",
  "model": "gpt-4",
  "current_estimated_cost_brl": 1.0,
  "actual_cost_history_days": 7
}'

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/admin/routing/calibration/simulate" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$SIM_PAYLOAD")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "✅ Calibration Simulation: SUCCESS"
  if echo "$BODY" | grep -q "recommended_multiplier" && echo "$BODY" | grep -q "adjusted_estimated_cost_brl"; then
    echo "✅ Calibration Simulation Schema: VALID"
  else
    echo "❌ Calibration Simulation Schema: INVALID"
    echo "$BODY"
    exit 1
  fi
else
  echo "❌ Calibration Simulation: FAILED (HTTP $HTTP_CODE)"
  echo "$BODY"
  exit 1
fi

# 3. Check for secrets in payload (best effort)
echo "Checking for secrets in payloads..."
if echo "$BODY" | grep -E "key|secret|token|password" | grep -v "X-Admin-Token" | grep -v "recommended_multiplier"; then
  echo "❌ Potential SECRETS EXPOSED in payload!"
  exit 1
else
  echo "✅ No secrets detected in payloads."
fi

echo "--- Commercial Calibration Validation COMPLETE ---"
