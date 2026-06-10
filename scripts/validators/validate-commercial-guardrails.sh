#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

if [[ -f "${SCRIPT_DIR}/../dev/common.sh" ]]; then
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/../dev/common.sh"
    BASE_URL="${BASE_URL:-$(default_base_url)}"
else
    BASE_URL="${BASE_URL:-http://localhost:8000}"
fi

ADMIN_TOKEN="${ADMIN_TOKEN:-admin-test-token}"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts/commercial-guardrails"
mkdir -p "${ARTIFACTS_DIR}"

OVERVIEW_FILE="${ARTIFACTS_DIR}/overview.json"
SIMULATE_FILE="${ARTIFACTS_DIR}/simulate.json"
RUNTIME_FILE="${ARTIFACTS_DIR}/runtime-status.json"

echo "[validate-commercial-guardrails] Validando overview..."
HTTP_STATUS=$(curl -s -o "${OVERVIEW_FILE}" -w "%{http_code}" -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/commercial-guardrails/overview")
if [[ "${HTTP_STATUS}" != "200" ]]; then
    echo "[validate-commercial-guardrails][error] Overview retornou HTTP ${HTTP_STATUS}"
    cat "${OVERVIEW_FILE}"
    exit 1
fi

if ! jq -e '.generated_at_utc != null and .mode != null and (.global_limits | type == "object") and (.global_usage_today | type == "object") and (.providers | type == "array") and (.clients | type == "array") and (.warnings | type == "array") and (.would_block | type == "array") and (.recommendations | type == "array")' "${OVERVIEW_FILE}" > /dev/null; then
    echo "[validate-commercial-guardrails][error] Schema do overview invalido."
    cat "${OVERVIEW_FILE}"
    exit 1
fi

echo "[validate-commercial-guardrails] Validando simulate..."
SIMULATE_PAYLOAD='{"client_id":"00000000-0000-0000-0000-000000000001","provider":"openai","model":"gpt-4o-mini","estimated_cost_brl":1.25,"estimated_revenue_brl":2.00}'
HTTP_STATUS=$(curl -s -o "${SIMULATE_FILE}" -w "%{http_code}" -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" -d "${SIMULATE_PAYLOAD}" "${BASE_URL}/admin/commercial-guardrails/simulate")
if [[ "${HTTP_STATUS}" != "200" ]]; then
    echo "[validate-commercial-guardrails][error] Simulate retornou HTTP ${HTTP_STATUS}"
    cat "${SIMULATE_FILE}"
    exit 1
fi

echo "[validate-commercial-guardrails] Validando runtime-status..."
HTTP_STATUS=$(curl -s -o "${RUNTIME_FILE}" -w "%{http_code}" -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/commercial-guardrails/runtime-status")
if [[ "${HTTP_STATUS}" != "200" ]]; then
    echo "[validate-commercial-guardrails][error] Runtime status retornou HTTP ${HTTP_STATUS}"
    cat "${RUNTIME_FILE}"
    exit 1
fi

if ! jq -e '.enforcement_mode != null and .cloud_kill_switch != null and .local_fallback_enabled != null and .blocked_cloud_requests_today != null and .successful_local_fallbacks_today != null and .report_only_events_today != null' "${RUNTIME_FILE}" > /dev/null; then
    echo "[validate-commercial-guardrails][error] Schema do runtime-status invalido."
    cat "${RUNTIME_FILE}"
    exit 1
fi

if ! jq -e '.allowed_in_report_only != null and .would_allow_if_enforced != null and .estimated_margin_brl != null and .estimated_margin_percent != null and (.reasons | type == "array") and (.recommendations | type == "array")' "${SIMULATE_FILE}" > /dev/null; then
    echo "[validate-commercial-guardrails][error] Schema do simulate invalido."
    cat "${SIMULATE_FILE}"
    exit 1
fi

echo "[validate-commercial-guardrails] Validando sanitizacao..."
if grep -iE 'api_key|provider_api_key|authorization|sk-|password|secret|prompt|completion|response\":\"' "${OVERVIEW_FILE}" "${SIMULATE_FILE}" "${RUNTIME_FILE}" > /dev/null; then
    echo "[validate-commercial-guardrails][error] Informacao sensivel detectada no payload!"
    exit 1
fi

echo "[validate-commercial-guardrails] Validando modo cloud-disabled/read-only..."
if ! jq -e '.mode == "disabled" or .mode == "report_only" or .mode == "enforce_cloud_only"' "${OVERVIEW_FILE}" > /dev/null; then
    echo "[validate-commercial-guardrails][error] Modo inesperado no overview."
    cat "${OVERVIEW_FILE}"
    exit 1
fi

echo "[validate-commercial-guardrails] Validacao concluida com sucesso."
exit 0
