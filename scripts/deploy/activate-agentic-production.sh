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

get_flag() {
    local key=$1
    grep "^$key=" "$CONFIG_FILE" | tail -n1 | cut -d'=' -f2- || true
}

echo "Activating agentic runtime in production mode..."

READINESS=$(get_flag "AGENTIC_READINESS_STATUS")
if [ "$READINESS" != "passed" ] && [ "${AGENTIC_FORCE_READINESS:-false}" != "true" ]; then
    echo "ERROR: Readiness check not passed. Exiting."
    exit 1
fi

SLOS=$(get_flag "AGENTIC_SLO_STATUS")
if [ "$SLOS" != "passed" ] && [ "${AGENTIC_FORCE_SLOS:-false}" != "true" ]; then
    echo "ERROR: SLO check not passed. Exiting."
    exit 1
fi

BUDGETS=$(get_flag "AGENTIC_BUDGET_STATUS")
if [ "$BUDGETS" != "passed" ] && [ "${AGENTIC_FORCE_BUDGETS:-false}" != "true" ]; then
    echo "ERROR: Budgets check not passed. Exiting."
    exit 1
fi

set_flag "DEPLOYMENT_MODE" "production"
set_flag "AGENT_RUNTIME_ENABLED" "true"
set_flag "AGENT_EXECUTION_ENABLED" "true"
set_flag "AGENT_ASYNC_EXECUTION_ENABLED" "true"
set_flag "AGENT_WORKER_ENABLED" "true"
set_flag "AGENT_STATEFUL_WORKFLOWS_ENABLED" "true"
set_flag "AGENT_SAAS_CONNECTORS_ENABLED" "true"
set_flag "AGENT_CONNECTOR_WRITE_ENABLED" "true"
set_flag "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED" "true"
set_flag "AGENT_EVALS_ENABLED" "true"
set_flag "AGENT_PROMOTION_REQUIRES_EVALS" "true"
set_flag "AGENT_EVAL_REGRESSION_GATE_ENABLED" "true"
set_flag "AGENT_WORKER_AUTOSCALING_ENABLED" "true"
set_flag "AGENT_SLO_ENFORCEMENT_ENABLED" "true"
set_flag "AGENT_STRICT_BUDGETS" "false"

echo "Production mode activation file updated: $CONFIG_FILE"
