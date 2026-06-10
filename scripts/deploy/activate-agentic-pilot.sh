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

echo "Activating agentic runtime in pilot mode..."

set_flag "DEPLOYMENT_MODE" "pilot"
set_flag "AGENT_RUNTIME_ENABLED" "true"
set_flag "AGENT_EXECUTION_ENABLED" "true"
set_flag "AGENT_ASYNC_EXECUTION_ENABLED" "true"
set_flag "AGENT_WORKER_ENABLED" "true"
set_flag "AGENT_STATEFUL_WORKFLOWS_ENABLED" "true"
set_flag "AGENT_SAAS_CONNECTORS_ENABLED" "true"
set_flag "AGENT_CONNECTOR_WRITE_ENABLED" "false"
set_flag "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED" "true"
set_flag "AGENT_HUMAN_APPROVAL_ENABLED" "true"
set_flag "AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK" "true"
set_flag "AGENT_STRICT_BUDGETS" "true"
set_flag "AGENT_EVALS_ENABLED" "false"
set_flag "AGENT_PROMOTION_REQUIRES_EVALS" "true"
set_flag "AGENT_SLO_ENFORCEMENT_ENABLED" "false"

echo "Pilot mode activation file updated: $CONFIG_FILE"
