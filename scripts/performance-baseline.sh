#!/usr/bin/env bash
set -euo pipefail

# scripts/performance-baseline.sh
# Measures key performance metrics of the LLM Inference Stack.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

init_stack_env

RESULTS_DIR="${ROOT_DIR}/artifacts/performance/latest"
mkdir -p "${RESULTS_DIR}"
BASELINE_FILE="${RESULTS_DIR}/baseline.md"

echo "# Performance Baseline - $(date)" > "${BASELINE_FILE}"
echo "" >> "${BASELINE_FILE}"

measure_startup() {
    echo "--- Measuring FastAPI Startup Time ---"
    # Measure time to reach 'Application startup complete' in logs
    local start_time=$(date +%s.%N)
    
    # We'll use a temporary log file to watch for the startup message
    local tmp_log=$(mktemp)
    
    # Start control plane in background using the virtualenv
    PYTHONPATH="${ROOT_DIR}/control_plane" "${ROOT_DIR}/.venv/bin/python3" "${ROOT_DIR}/control_plane/app/main.py" > "${tmp_log}" 2>&1 &
    local server_pid=$!
    
    local startup_complete=false
    local timeout=30
    local elapsed=0
    
    while [ "${elapsed}" -lt "${timeout}" ]; do
        if grep -q "Application startup complete" "${tmp_log}"; then
            startup_complete=true
            break
        fi
        sleep 0.1
        elapsed=$((elapsed + 1))
    done
    
    local end_time=$(date +%s.%N)
    kill "${server_pid}" || true
    
    if [ "${startup_complete}" = true ]; then
        local duration=$(echo "${end_time} - ${start_time}" | bc)
        echo "Startup Time: ${duration}s"
        echo "- **FastAPI Startup Time**: ${duration}s" >> "${BASELINE_FILE}"
    else
        echo "Startup Failed or Timed Out"
        echo "- **FastAPI Startup Time**: FAILED" >> "${BASELINE_FILE}"
    fi
    rm "${tmp_log}"
}

measure_imports() {
    echo "--- Measuring Import Time ---"
    local import_time=$(PYTHONPATH="${ROOT_DIR}/control_plane" "${ROOT_DIR}/.venv/bin/python3" -X importtime -c "import app.main" 2>&1 | tail -n 1 | awk '{print $NF}')
    # Note: simple measure, we'll just use total time for now
    local total_import=$(PYTHONPATH="${ROOT_DIR}/control_plane" time -p "${ROOT_DIR}/.venv/bin/python3" -c "import app.main" 2>&1 | grep real | awk '{print $2}')
    echo "Import Time (total real): ${total_import}s"
    echo "- **Import Time (app.main)**: ${total_import}s" >> "${BASELINE_FILE}"
}

measure_latency() {
    echo "--- Measuring Endpoint Latency ---"
    local base_url=$(default_base_url)
    
    # Ensure server is running (we'll use the already running one if available or start one)
    # For baseline, we assume the environment is ready (local-production-up.sh or similar)
    
    echo "Endpoint | Latency (ms)" >> "${BASELINE_FILE}"
    echo "--- | ---" >> "${BASELINE_FILE}"
    
    for endpoint in "/health" "/ready" "/metrics"; do
        local latency=$(curl -o /dev/null -s -w "%{time_total}\n" "${base_url}${endpoint}")
        local latency_ms=$(echo "${latency} * 1000" | bc)
        echo "${endpoint}: ${latency_ms}ms"
        echo "${endpoint} | ${latency_ms}ms" >> "${BASELINE_FILE}"
    done
}

measure_pytest() {
    echo "--- Measuring Pytest Duration ---"
    local start_time=$(date +%s.%N)
    export PYTHONPATH="${ROOT_DIR}/control_plane"
    "${ROOT_DIR}/.venv/bin/pytest" control_plane/tests/api/test_support_admin.py > /dev/null 2>&1
    local end_time=$(date +%s.%N)
    local duration=$(echo "${end_time} - ${start_time}" | bc)
    echo "Pytest Duration (support_admin): ${duration}s"
    echo "- **Pytest Duration (Support Admin)**: ${duration}s" >> "${BASELINE_FILE}"
}

measure_startup
measure_imports
measure_latency
measure_pytest

echo "" >> "${BASELINE_FILE}"
echo "Measurements completed. Results in ${BASELINE_FILE}"
