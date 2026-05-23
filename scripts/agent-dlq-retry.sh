#!/bin/bash
set -e

DLQ_ID=$1

if [ -z "$DLQ_ID" ]; then
    echo "Usage: $0 <dlq_item_id>"
    exit 1
fi

BASE_URL=${KLEBER_BASE_URL:-"http://localhost:18080"}
API_KEY=${KLEBER_API_KEY}

echo "Retrying DLQ item $DLQ_ID..."

curl -s -H "X-Admin-Token: $API_KEY" \
     -X POST "$BASE_URL/admin/agents/worker/dlq/$DLQ_ID/retry" | jq .
