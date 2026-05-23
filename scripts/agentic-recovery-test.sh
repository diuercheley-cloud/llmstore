#!/bin/bash
set -e

echo "Running Agentic Recovery Tests..."

# 1. Run chaos
./scripts/agentic-chaos-run.sh worker_crash

# 2. Wait for recovery
echo "Waiting for recovery..."
sleep 10

# 3. Check readiness
./scripts/agentic-readiness.sh

echo "Recovery test complete."
