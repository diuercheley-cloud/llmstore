#!/bin/bash
set -e

echo "----------------------------------------------------------------"
echo "  AGENT WORKER STATUS"
echo "----------------------------------------------------------------"

BASE_URL=${KLEBER_BASE_URL:-"http://localhost:18080"}
API_KEY=${KLEBER_API_KEY}

# Check readiness which contains worker info
RESPONSE=$(curl -s -H "X-Admin-Token: $API_KEY" -X GET "$BASE_URL/admin/agents/readiness")

STATUS=$(echo "$RESPONSE" | jq -r '.status')
WORKERS=$(echo "$RESPONSE" | jq -r '.checks[] | select(.id=="worker_heartbeat") | .value')

echo "Global Status: $STATUS"
echo "Active Workers: $WORKERS"
echo ""
echo "Worker Details (Heartbeats):"
# In a real scenario, we might have a dedicated endpoint for listing workers
# For now, let's assume we can see them in readiness or via a quick SQL query if possible
# But as a CLI tool, we prefer API.

echo "Queue Metrics:"
echo "$RESPONSE" | jq -r '.checks[] | select(.id=="queue_depth" or .id=="dead_letter_queue" or .id=="stuck_runs") | "[\(.status | ascii_upcase)] \(.name): \(.value)"'

echo "----------------------------------------------------------------"
