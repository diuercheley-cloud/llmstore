#!/bin/bash
set -e

# Usage: ./load-test-agentic.sh <agent_id> <count>
AGENT_ID=$1
COUNT=${2:-100}

if [ -z "$AGENT_ID" ]; then
    echo "Usage: $0 <agent_id> [count]"
    exit 1
fi

echo "--- LLM Inference Stack Scale Validation ---"
echo "Target Agent: $AGENT_ID"
echo "Target Load: $COUNT runs"
echo "--------------------------------------------"

# Ensure dependencies
pip install httpx --silent

# Run Python load test
export PYTHONPATH=control_plane
python3 tests/integration/load/test_agentic_scale.py "$AGENT_ID" "$COUNT"
