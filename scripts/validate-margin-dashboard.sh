#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${SCRIPT_DIR}/common.sh" ]]; then
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/common.sh"
    BASE_URL="${BASE_URL:-$(default_base_url)}"
else
    BASE_URL="${BASE_URL:-http://localhost:8000}"
fi

ADMIN_TOKEN="${ADMIN_TOKEN:-admin-test-token}"

echo "[validate-margin-dashboard] Validando Margin Dashboard Endpoint..."

ARTIFACTS_DIR="${ROOT_DIR}/artifacts/margin-dashboard"
mkdir -p "${ARTIFACTS_DIR}"
RESP_FILE="${ARTIFACTS_DIR}/margin_resp.json"

HTTP_STATUS=$(curl -s -o "${RESP_FILE}" -w "%{http_code}" -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/financials/margin-dashboard")

if [[ "$HTTP_STATUS" != "200" ]]; then
    echo "[validate-margin-dashboard][error] Endpoint retornou HTTP $HTTP_STATUS"
    cat "${RESP_FILE}"
    exit 1
fi

echo "[validate-margin-dashboard] Validando Schema JSON..."
if ! jq -e '.generated_at_utc != null and .revenue_today_brl != null and .cost_today_brl != null and .gross_margin_today_brl != null and .gross_margin_percent_today != null and .requests_today != null and .cache_hit_rate_today != null and .estimated_cache_savings_brl != null and (.cost_by_provider | type == "array") and (.revenue_by_client | type == "array") and type == "object"' "${RESP_FILE}" > /dev/null; then
    echo "[validate-margin-dashboard][error] Validacao de JSON Schema falhou."
    cat "${RESP_FILE}"
    exit 1
fi

echo "[validate-margin-dashboard] Validando vazamento de secrets..."
if grep -iE 'api_key|sk-|password|secret|prompt|completion' "${RESP_FILE}" > /dev/null; then
    echo "[validate-margin-dashboard][error] Informacao sensivel detectada no payload!"
    exit 1
fi

echo "[validate-margin-dashboard] Validacao do Margin Dashboard concluida com sucesso."
exit 0
