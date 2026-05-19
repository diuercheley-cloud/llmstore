#!/bin/bash
# scripts/runtime-node-register.sh

NAME=$1
URL=$2
TYPE=${3:-remote}

if [ -z "$NAME" ] || [ -z "$URL" ]; then
    echo "Usage: $0 <name> <url> [type]"
    exit 1
fi

curl -X POST "http://localhost:8000/runtime/nodes/register" \
     -H "Content-Type: application/json" \
     -d "{
       \"name\": \"$NAME\",
       \"base_url\": \"$URL\",
       \"node_type\": \"$TYPE\",
       \"gpu_count\": 1,
       \"gpu_memory_total_mb\": 8192,
       \"cpu_count\": 8,
       \"memory_total_mb\": 16384
     }"
