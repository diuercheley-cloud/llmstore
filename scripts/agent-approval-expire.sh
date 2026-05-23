#!/bin/bash
# Expire pending approvals
RUN_ID=$1
if [ -z "$RUN_ID" ]; then
    echo "Expiring ALL pending approvals older than threshold..."
else
    echo "Expiring approval for run $RUN_ID..."
fi
# Simulated expiry logic
echo "Approvals expired. Status updated to 'expired'."
