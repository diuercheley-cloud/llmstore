#!/usr/bin/env bash
# Owner: agent-platform
# Status: beta

echo "Sending SIGUSR1 to agent workers to enter DRAIN mode..."
docker compose kill -s SIGUSR1 agent-worker
echo "Workers will finish current jobs and exit."
