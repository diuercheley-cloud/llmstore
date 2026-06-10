#!/bin/bash
# scripts/dev/operational-readiness-pack.sh
# Validates system readiness for demo, pilot, or production.

OUTPUT_DIR="artifacts/operational-readiness/latest"
mkdir -p "$OUTPUT_DIR"

SUMMARY_FILE="$OUTPUT_DIR/summary.md"
CHECKS_FILE="$OUTPUT_DIR/checks.json"
RECS_FILE="$OUTPUT_DIR/recommendations.md"

# Load environment variables
ENV_FILE=".env"
if [ -f ".env.local" ]; then
    ENV_FILE=".env.local"
fi
if [ -n "$STACK_ENV_FILE" ] && [ -f "$STACK_ENV_FILE" ]; then
    ENV_FILE="$STACK_ENV_FILE"
fi

if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        # Ignore comments and empty lines
        if [[ ! "$line" =~ ^# ]] && [[ "$line" =~ = ]]; then
            key=$(echo "$line" | cut -d= -f1 | tr -d '[:space:]')
            val=$(echo "$line" | cut -d= -f2-)
            # strip leading/trailing spaces and quotes
            val=$(echo "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
            val="${val%\"}"
            val="${val#\"}"
            val="${val%\'}"
            val="${val#\'}"
            export "$key"="$val"
        fi
    done < "$ENV_FILE"
fi

# Determine host port
API_PORT="${HOST_PORT:-8080}"
TIMEOUT_LIMIT="${READINESS_TIMEOUT:-30}"

echo "{" > "$CHECKS_FILE"
STATUS="demo_ready"
WARNINGS=0
ERRORS=0

# 1. Infrastructure Checks
check_docker() {
    if docker compose ps > /dev/null 2>&1; then
        echo '"docker_compose": "ok",' >> "$CHECKS_FILE"
    else
        echo '"docker_compose": "failed",' >> "$CHECKS_FILE"
        ERRORS=$((ERRORS+1))
    fi
}

check_postgres() {
    if docker compose exec -T postgres pg_isready > /dev/null 2>&1; then
        echo '"postgres": "ok",' >> "$CHECKS_FILE"
    else
        echo '"postgres": "failed",' >> "$CHECKS_FILE"
        ERRORS=$((ERRORS+1))
    fi
}

check_redis() {
    if docker compose exec -T redis redis-cli ping | grep PONG > /dev/null 2>&1; then
        echo '"redis": "ok",' >> "$CHECKS_FILE"
    else
        echo '"redis": "failed",' >> "$CHECKS_FILE"
        ERRORS=$((ERRORS+1))
    fi
}

# Wait-for Control Plane API readiness
wait_for_api() {
    local start_time=$(date +%s)
    local delay=1
    local max_delay=8
    echo "Waiting for control plane API on port $API_PORT to be ready..."
    while true; do
        if curl -s -f "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
            echo "Control plane API is up and running."
            return 0
        fi
        
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        if [ $elapsed -ge $TIMEOUT_LIMIT ]; then
            echo "Timeout waiting for Control Plane API (elapsed: ${elapsed}s, limit: ${TIMEOUT_LIMIT}s)"
            return 1
        fi
        
        echo "API not ready yet, retrying in ${delay}s... (elapsed: ${elapsed}s)"
        sleep $delay
        delay=$((delay * 2))
        if [ $delay -gt $max_delay ]; then
            delay=$max_delay
        fi
    done
}

# 2. API Checks
check_api() {
    local endpoint=$1
    local name=$2
    if curl -s -f "http://localhost:$API_PORT$endpoint" > /dev/null 2>&1; then
        echo "\"$name\": \"ok\"," >> "$CHECKS_FILE"
    else
        echo "\"$name\": \"failed\"," >> "$CHECKS_FILE"
        ERRORS=$((ERRORS+1))
    fi
}

# 3. Environment & Security
check_env() {
    if [ -f .env ] || [ -f .env.local ]; then
        echo '"env_file": "exists",' >> "$CHECKS_FILE"
    else
        echo '"env_file": "missing",' >> "$CHECKS_FILE"
        ERRORS=$((ERRORS+1))
    fi
    
    if git check-ignore .env > /dev/null 2>&1 || git check-ignore .env.local > /dev/null 2>&1; then
        echo '"env_ignored": "ok",' >> "$CHECKS_FILE"
    else
        echo '"env_ignored": "failed",' >> "$CHECKS_FILE"
        WARNINGS=$((WARNINGS+1))
    fi
}

# 4. Hardware (Best effort)
check_gpu() {
    if command -v nvidia-smi > /dev/null 2>&1 && nvidia-smi > /dev/null 2>&1; then
        echo '"gpu_detected": "ok",' >> "$CHECKS_FILE"
    else
        echo '"gpu_detected": "warning",' >> "$CHECKS_FILE"
        WARNINGS=$((WARNINGS+1))
    fi
}

# 5. Agentic Section
check_agentic() {
    local runtime_enabled="${AGENT_RUNTIME_ENABLED:-false}"
    local worker_enabled="${AGENT_WORKER_ENABLED:-false}"
    echo "\"agentic_runtime_enabled\": \"$runtime_enabled\"," >> "$CHECKS_FILE"
    echo "\"agentic_worker_enabled\": \"$worker_enabled\"," >> "$CHECKS_FILE"
    
    # When runtime is disabled, agentic is explicitly opted out — never blocks
    if [ "$runtime_enabled" != "true" ]; then
        echo '"agentic_readiness_status": "disabled",' >> "$CHECKS_FILE"
        echo '"agentic_blockers": [],' >> "$CHECKS_FILE"
        echo '"agentic_warnings": [],' >> "$CHECKS_FILE"
        return
    fi
    
    if [ $API_READY -ne 0 ]; then
        echo '"agentic_readiness_status": "api_unreachable",' >> "$CHECKS_FILE"
        echo '"agentic_blockers": ["Control plane API unreachable for agentic readiness check"],' >> "$CHECKS_FILE"
        echo '"agentic_warnings": [],' >> "$CHECKS_FILE"
        return
    fi
    
    local AGENTIC_JSON
    AGENTIC_JSON=$(curl -s "http://localhost:$API_PORT/admin/agents/readiness" -H "X-Admin-Token: $ADMIN_TOKEN")
    local a_status
    a_status=$(echo "$AGENTIC_JSON" | jq -r '.status' 2>/dev/null || echo "unknown")
    echo "\"agentic_readiness_status\": \"$a_status\"," >> "$CHECKS_FILE"
    
    local blockers
    blockers=$(echo "$AGENTIC_JSON" | jq -c '.blockers // []' 2>/dev/null || echo "[]")
    echo "\"agentic_blockers\": $blockers," >> "$CHECKS_FILE"
    
    local warnings
    warnings=$(echo "$AGENTIC_JSON" | jq -c '.warnings // []' 2>/dev/null || echo "[]")
    echo "\"agentic_warnings\": $warnings," >> "$CHECKS_FILE"
    
    if [ "$a_status" == "blocked" ]; then
        ERRORS=$((ERRORS+1))
    elif [ "$a_status" == "degraded" ]; then
        WARNINGS=$((WARNINGS+1))
    fi
}

# Run infrastructure check
check_docker
check_postgres
check_redis

# Run environment check
check_env

# Run hardware check
check_gpu

# Wait for API to be ready before querying it
wait_for_api
API_READY=$?

if [ $API_READY -eq 0 ]; then
    # Run API Checks
    check_api "/health" "health_api"
    check_api "/ready" "ready_api"
    check_api "/metrics" "metrics_api"
    # Agentic health
    check_agentic
else
    echo '"health_api": "failed",' >> "$CHECKS_FILE"
    echo '"ready_api": "failed",' >> "$CHECKS_FILE"
    echo '"metrics_api": "failed",' >> "$CHECKS_FILE"
    ERRORS=$((ERRORS+3))
fi

# Finalizing JSON
echo "\"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"" >> "$CHECKS_FILE"
echo "}" >> "$CHECKS_FILE"

# Determine Overall Status
if [ $ERRORS -gt 0 ]; then
    STATUS="production_blocked"
else
    # Fetch `/ready` JSON response from API
    if [ $API_READY -eq 0 ]; then
        READY_JSON=$(curl -s "http://localhost:$API_PORT/ready")
        # Check if the API status is degraded or any opt-in components are disabled/unhealthy
        if echo "$READY_JSON" | grep -q '"status"[[:space:]]*:[[:space:]]*"degraded"' || [ $WARNINGS -gt 0 ]; then
            STATUS="demo_ready"
        else
            STATUS="pilot_ready"
        fi
    else
        STATUS="production_blocked"
    fi
fi

# Generate Summary
cat <<EOF > "$SUMMARY_FILE"
# Operational Readiness Summary
**Status**: $STATUS
**Errors**: $ERRORS
**Warnings**: $WARNINGS
**Generated at**: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Overview
This report validates the readiness of the llm-inference-stack for its intended use case.
EOF

# Generate Recommendations
cat <<EOF > "$RECS_FILE"
# Recommendations
EOF

if [ $ERRORS -gt 0 ]; then
    echo "- **CRITICAL**: Resolve all failed infrastructure checks before proceeding." >> "$RECS_FILE"
fi
if grep -q '"gpu_detected": "warning"' "$CHECKS_FILE"; then
    echo "- **WARNING**: No GPU detected. Performance will be severely limited to CPU-only inference." >> "$RECS_FILE"
fi
if grep -q '"env_ignored": "failed"' "$CHECKS_FILE"; then
    echo "- **SECURITY**: The environment files are not ignored by git. Add them to .gitignore immediately to prevent credential leaks." >> "$RECS_FILE"
fi

echo "Readiness check complete. Status: $STATUS"

if [ "$STATUS" = "production_blocked" ]; then
    exit 1
else
    exit 0
fi
