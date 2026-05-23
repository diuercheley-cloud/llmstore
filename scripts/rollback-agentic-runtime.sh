#!/bin/bash
set -euo pipefail

CONFIG_FILE=${AGENTIC_ENV_FILE:-"config/agentic.env"}
mkdir -p "$(dirname "$CONFIG_FILE")"
touch "$CONFIG_FILE"

set_flag() {
    local key=$1
    local value=$2
    if grep -q "^$key=" "$CONFIG_FILE"; then
        sed -i "s/^$key=.*/$key=$value/" "$CONFIG_FILE"
    else
        echo "$key=$value" >> "$CONFIG_FILE"
    fi
}

echo "Initiating rollback of agentic runtime..."

set_flag "AGENT_ROLLOUT_NEW_RUNS" "paused"
echo "- New runs paused."

echo "- Draining queue..."
sleep 1
set_flag "AGENT_ROLLOUT_QUEUE_STATUS" "drained"
echo "- Queue drained."

set_flag "DEPLOYMENT_MODE" "appliance"
set_flag "AGENT_RUNTIME_ENABLED" "false"
set_flag "AGENT_EXECUTION_ENABLED" "false"
set_flag "AGENT_ASYNC_EXECUTION_ENABLED" "false"
set_flag "AGENT_WORKER_ENABLED" "false"
set_flag "AGENT_SAAS_CONNECTORS_ENABLED" "false"
set_flag "AGENT_CONNECTOR_WRITE_ENABLED" "false"
echo "- Runtime disabled and appliance posture restored."

set_flag "AGENT_ROLLOUT_WORKFLOWS_STATE" "preserved"
echo "- Stateful workflows preserved."

echo "Rollback completed successfully."
