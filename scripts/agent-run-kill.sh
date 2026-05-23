#!/bin/bash
# Kill a running agent process
RUN_ID=$1
if [ -z "$RUN_ID" ]; then
    echo "Usage: $0 <run_id>"
    exit 1
fi

echo "Killing agent run $RUN_ID..."
# Simulated kill logic
# This would send a signal to the worker or update status in DB to 'failed'
echo "Run $RUN_ID marked as failed (KILLED)."
