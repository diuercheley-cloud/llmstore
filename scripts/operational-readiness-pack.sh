#!/bin/bash
# scripts/operational-readiness-pack.sh
# Validates system readiness for demo, pilot, or production.

OUTPUT_DIR="artifacts/operational-readiness/latest"
mkdir -p "$OUTPUT_DIR"

SUMMARY_FILE="$OUTPUT_DIR/summary.md"
CHECKS_FILE="$OUTPUT_DIR/checks.json"
RECS_FILE="$OUTPUT_DIR/recommendations.md"

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

# 2. API Checks
check_api() {
    local endpoint=$1
    local name=$2
    if curl -s -f "http://localhost:8000$endpoint" > /dev/null 2>&1; then
        echo "\"$name\": \"ok\"," >> "$CHECKS_FILE"
    else
        echo "\"$name\": \"failed\"," >> "$CHECKS_FILE"
        ERRORS=$((ERRORS+1))
    fi
}

# 3. Environment & Security
check_env() {
    if [ -f .env ]; then
        echo '"env_file": "exists",' >> "$CHECKS_FILE"
    else
        echo '"env_file": "missing",' >> "$CHECKS_FILE"
        ERRORS=$((ERRORS+1))
    fi
    
    if git check-ignore .env > /dev/null 2>&1; then
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

# Run checks
check_docker
check_postgres
check_redis
check_api "/health" "health_api"
check_api "/ready" "ready_api"
check_api "/metrics" "metrics_api"
check_env
check_gpu

# Finalizing JSON (removing last comma is tricky in bash, but let's just add a final dummy)
echo '"timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"' >> "$CHECKS_FILE"
echo "}" >> "$CHECKS_FILE"

# Determine Overall Status
if [ $ERRORS -gt 0 ]; then
    STATUS="production_blocked"
elif [ $WARNINGS -gt 0 ]; then
    STATUS="needs_attention"
else
    # Check if specifically demo ready or pilot ready
    # For now, if no errors and no warnings, it's pilot_ready
    STATUS="pilot_ready"
fi

# Generate Summary
cat <<EOF > "$SUMMARY_FILE"
# Operational Readiness Summary
**Status**: $STATUS
**Errors**: $ERRORS
**Warnings**: $WARNINGS
**Generated at**: $(date)

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
    echo "- **SECURITY**: The .env file is not ignored by git. Add it to .gitignore immediately to prevent credential leaks." >> "$RECS_FILE"
fi

echo "Readiness check complete. Status: $STATUS"
