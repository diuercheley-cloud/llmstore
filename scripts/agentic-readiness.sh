#!/bin/bash
set -e

BASE_URL=${KLEBER_BASE_URL:-"http://localhost:18080"}
API_KEY=${KLEBER_API_KEY}

echo "Running Agentic Runtime Readiness Checks..."

curl -s -H "X-Admin-Token: $API_KEY" \
     -X GET "$BASE_URL/admin/agents/observability/readiness" | jq .

echo "Readiness check complete."
