#!/bin/bash
# Throttle agent queue
LIMIT=$1
if [ -z "$LIMIT" ]; then
    echo "Usage: $0 <max_parallel_runs>"
    exit 1
fi

echo "Setting queue throttle limit to $LIMIT..."
# Simulated throttle logic (e.g. updating Redis or Config)
echo "Throttle applied. Current capacity: $LIMIT concurrent runs."
