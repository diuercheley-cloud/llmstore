#!/usr/bin/env bash
# Owner: agent-platform
# Status: beta

echo "Simulating worker crash (SIGKILL)..."
docker compose kill -s SIGKILL agent-worker
echo "Worker crashed."
echo "Waiting for recovery loop in another worker (or restarting worker) to pick up orphan leases..."
sleep 2
docker compose up -d agent-worker
echo "New worker started. Orphans should be recovered within 60 seconds."
