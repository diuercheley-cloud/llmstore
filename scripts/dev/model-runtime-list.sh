#!/bin/bash
set -e

# Load environment variables if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

ADMIN_TOKEN=${ADMIN_SUPER_TOKEN:-${ADMIN_TOKEN:-"test-admin-token"}}
BASE_URL=${CONTROL_PLANE_URL:-"http://localhost:8080"}

echo "Listing active model runtimes..."
curl -s -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/models/runtime" | jq .
