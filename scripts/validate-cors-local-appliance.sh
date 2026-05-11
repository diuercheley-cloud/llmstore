#!/usr/bin/env bash
# LLM Inference Stack - CORS Validation for Local Appliance
# Validates that CORS is explicitly and securely configured.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-http://localhost:18080}"
echo "Validating CORS for: ${BASE_URL}"

# 1. Check if CORS_ALLOW_ORIGINS is not empty (warning if empty but has defaults)
CORS_VAL=$(grep "^CORS_ALLOW_ORIGINS=" .env.local 2>/dev/null | cut -d'=' -f2 || echo "")
if [[ -z "${CORS_VAL}" ]]; then
    echo "[WARN] CORS_ALLOW_ORIGINS is empty in .env.local. System will use secure defaults."
else
    echo "[INFO] CORS_ALLOW_ORIGINS configured: ${CORS_VAL}"
fi

# 2. Check for wildcard '*'
if [[ "${CORS_VAL}" == "*" ]]; then
    echo "[ERROR] Wildcard '*' CORS detected. This is INSECURE for appliance mode."
    exit 1
fi

# 3. Test OPTIONS preflight for localhost
echo "[TEST] Testing preflight for http://localhost:18080..."
resp_localhost=$(curl -s -I -X OPTIONS "${BASE_URL}/health" \
  -H "Origin: http://localhost:18080" \
  -H "Access-Control-Request-Method: GET")

if echo "${resp_localhost}" | grep -qi "access-control-allow-origin: http://localhost:18080" || \
   echo "${resp_localhost}" | grep -qi "access-control-allow-origin: \*"; then
    echo "[PASS] localhost:18080 is allowed."
else
    echo "[FAIL] localhost:18080 is NOT allowed."
    echo "${resp_localhost}"
    exit 1
fi

# 4. Test OPTIONS preflight for 127.0.0.1
echo "[TEST] Testing preflight for http://127.0.0.1:18080..."
resp_127=$(curl -s -I -X OPTIONS "${BASE_URL}/health" \
  -H "Origin: http://127.0.0.1:18080" \
  -H "Access-Control-Request-Method: GET")

if echo "${resp_127}" | grep -qi "access-control-allow-origin: http://127.0.0.1:18080" || \
   echo "${resp_127}" | grep -qi "access-control-allow-origin: \*"; then
    echo "[PASS] 127.0.0.1:18080 is allowed."
else
    echo "[FAIL] 127.0.0.1:18080 is NOT allowed."
    exit 1
fi

# 5. Test status endpoint for cors_configured
echo "[TEST] Checking /status for cors_configured..."
status_json=$(curl -s "${BASE_URL}/status")
if echo "${status_json}" | grep -q '"cors_configured":true'; then
    echo "[PASS] /status reports cors_configured: true"
else
    echo "[FAIL] /status reports cors_configured: false or missing"
    echo "${status_json}"
    exit 1
fi

echo "[SUCCESS] CORS validation passed for local appliance mode."
exit 0
