#!/bin/bash
set -e

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <model_id> <backend_id>"
  exit 1
fi

MODEL_ID=$1
BACKEND_ID=$2

# Load environment variables if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

ADMIN_TOKEN=${ADMIN_SUPER_TOKEN:-${ADMIN_TOKEN:-"test-admin-token"}}
BASE_URL=${CONTROL_PLANE_URL:-"http://localhost:8080"}

echo "Rolling back to previous ready instance for model $MODEL_ID and backend $BACKEND_ID..."
curl -s -X POST -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d "{\"model_id\": \"$MODEL_ID\", \"backend_id\": \"$BACKEND_ID\"}" \
  "$BASE_URL/admin/models/runtime/rollback" | jq .
