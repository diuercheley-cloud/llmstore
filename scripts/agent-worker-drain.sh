#!/bin/bash
set -e

WORKER_ID=$1

if [ -z "$WORKER_ID" ]; then
    echo "Usage: $0 <worker_id_or_pod_name>"
    exit 1
fi

echo "Gracefully draining worker $WORKER_ID..."

# Check if we are in Kubernetes
if command -v kubectl &> /dev/null && kubectl get pod "$WORKER_ID" &> /dev/null; then
    echo "Detected Kubernetes environment."
    kubectl exec "$WORKER_ID" -- kill -SIGUSR1 1
    echo "SIGUSR1 sent to Pod $WORKER_ID (PID 1)."
elif docker ps --format '{{.Names}}' | grep -q "$WORKER_ID"; then
    echo "Detected Docker environment."
    docker exec "$WORKER_ID" kill -SIGUSR1 1
    echo "SIGUSR1 sent to Container $WORKER_ID (PID 1)."
else
    # Try local process
    PID=$(ps aux | grep "$WORKER_ID" | grep -v grep | awk '{print $2}')
    if [ -n "$PID" ]; then
        kill -SIGUSR1 "$PID"
        echo "SIGUSR1 sent to local PID $PID."
    else
        echo "Error: Could not find worker $WORKER_ID in k8s, docker, or local processes."
        exit 1
    fi
fi

echo "Worker is now in DRAIN mode. It will finish its current job and stop picking up new ones."
