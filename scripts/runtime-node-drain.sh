#!/bin/bash
# scripts/runtime-node-drain.sh

NODE_ID=$1
ADMIN_TOKEN=$2

if [ -z "$NODE_ID" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo "Usage: $0 <node_id> <admin_token>"
    exit 1
fi

curl -X POST "http://localhost:8000/runtime/nodes/$NODE_ID/drain" \
     -H "X-Admin-Token: $ADMIN_TOKEN"
