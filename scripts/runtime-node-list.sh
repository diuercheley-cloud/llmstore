#!/bin/bash
# scripts/runtime-node-list.sh

curl -s "http://localhost:8000/runtime/nodes/" | jq .
