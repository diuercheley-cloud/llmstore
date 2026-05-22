#!/bin/bash
set -e

SCENARIO=${1:-"worker_crash"}
echo "Executing Agentic Chaos Scenario: $SCENARIO"

case $SCENARIO in
    "worker_crash")
        echo "Simulating worker crash..."
        # Logic to kill worker process or container
        ;;
    "lease_expiry")
        echo "Simulating lease expiry..."
        # Logic to expire a lease in DB
        ;;
    "tool_timeout")
        echo "Simulating tool timeout..."
        # Logic to delay tool response
        ;;
    *)
        echo "Unknown scenario: $SCENARIO"
        exit 1
        ;;
esac

echo "Chaos scenario $SCENARIO executed."
