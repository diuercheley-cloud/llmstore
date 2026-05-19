#!/bin/bash
# scripts/runtime-node-health.sh

NODE_ID=$1

if [ -z "$NODE_ID" ]; then
    echo "Usage: $0 <node_id>"
    exit 1
fi

curl -s "http://localhost:8000/runtime/nodes/$NODE_ID" | jq .status
