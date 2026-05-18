#!/bin/bash
set -e

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <instance_id>"
  exit 1
fi

INSTANCE_ID=$1

# Load environment variables if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

ADMIN_TOKEN=${ADMIN_SUPER_TOKEN:-${ADMIN_TOKEN:-"test-admin-token"}}
BASE_URL=${CONTROL_PLANE_URL:-"http://localhost:8080"}

echo "Activating runtime instance $INSTANCE_ID..."
curl -s -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  "$BASE_URL/admin/models/runtime/activate/$INSTANCE_ID" | jq .
