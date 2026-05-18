#!/bin/bash
set -e

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <model_id> <backend_id> <model_path> [runtime_config_json]"
  exit 1
fi

MODEL_ID=$1
BACKEND_ID=$2
MODEL_PATH=$3
CONFIG=${4:-"{}"}

# Load environment variables if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

ADMIN_TOKEN=${ADMIN_SUPER_TOKEN:-${ADMIN_TOKEN:-"test-admin-token"}}
BASE_URL=${CONTROL_PLANE_URL:-"http://localhost:8080"}

echo "Loading model $MODEL_ID on backend $BACKEND_ID..."
curl -s -X POST -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d "{\"model_id\": \"$MODEL_ID\", \"backend_id\": \"$BACKEND_ID\", \"model_path\": \"$MODEL_PATH\", \"runtime_config\": $CONFIG}" \
  "$BASE_URL/admin/models/runtime/load" | jq .
