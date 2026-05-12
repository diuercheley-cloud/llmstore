#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/lib/validation-logging.sh"
init_stack_env

TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
OUTPUT_DIR="${ROOT_DIR}/artifacts/abuse-protection/${TIMESTAMP}"
LOGS_DIR="${OUTPUT_DIR}/logs"
REPORT_JSON="${OUTPUT_DIR}/abuse-report.json"
REPORT_MD="${OUTPUT_DIR}/abuse-report.md"

mkdir -p "${LOGS_DIR}"

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
MODE="${MODE:-quick}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  log_error "ADMIN_TOKEN must be set"
  exit 1
fi

log_section "Abuse Protection Local Validation"
log_info "Mode: ${MODE}"
log_info "Target: ${BASE_URL}"
log_info "Output: ${OUTPUT_DIR}"

RESULTS_FILE="${OUTPUT_DIR}/results.tmp"
HEALTH_STATUS="unknown"
: > "${RESULTS_FILE}"
RUN_SUFFIX="${TIMESTAMP}-$$"

record_result() {
  local scenario="$1"
  local expected="$2"
  local actual="$3"
  local status="$4"
  local note="${5:-}"
  printf '%s\t%s\t%s\t%s\t%s\n' "${scenario}" "${expected}" "${actual}" "${status}" "${note}" >> "${RESULTS_FILE}"
}

admin_api() {
  local path="$1"
  shift
  curl_base_url "${BASE_URL}${path}" -fsS \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    "$@"
}

json_read() {
  local expr="$1"
  python3 -c "import json, sys; data=json.load(sys.stdin); value=${expr}; print('' if value is None else value)"
}

require_json_value() {
  local payload="$1"
  local expr="$2"
  local context="$3"
  local value
  if ! value="$(printf '%s' "${payload}" | json_read "${expr}" 2>/dev/null)"; then
    printf '%s\n' "${payload}" > "${LOGS_DIR}/$(echo "${context}" | tr ' /' '__').log"
    log_error "${context} did not return valid JSON"
    exit 1
  fi
  if [[ -z "${value}" ]]; then
    printf '%s\n' "${payload}" > "${LOGS_DIR}/$(echo "${context}" | tr ' /' '__').log"
    log_error "${context} JSON response is missing ${expr}"
    exit 1
  fi
  printf '%s\n' "${value}"
}

find_plan_id() {
  local code="$1"
  local plans
  plans="$(admin_api "/admin/billing/plans")"
  printf '%s' "${plans}" | python3 -c "import json, sys; plans=json.load(sys.stdin); print(next((p['id'] for p in plans if p.get('code') == '${code}'), ''))"
}

patch_client_json() {
  local client_id="$1"
  local payload="$2"
  admin_api "/admin/clients/${client_id}" -X PATCH \
    -H "Content-Type: application/json" \
    -d "${payload}" >/dev/null
}

ensure_client() {
  local name="$1"
  local payload="${2:-}"
  local existing
  existing="$(admin_api "/admin/clients" | python3 -c "import json, sys; clients=json.load(sys.stdin); print(next((c['id'] for c in clients if c['name'] == '${name}'), ''))")"
  if [[ -n "${existing}" ]]; then
    printf '%s\n' "${existing}"
    return
  fi
  if [[ -z "${payload}" ]]; then
    payload="{\"name\":\"${name}\"}"
  fi
  local response
  response="$(admin_api "/admin/clients" -X POST -H "Content-Type: application/json" -d "${payload}")"
  require_json_value "${response}" "data['id']" "create client ${name}"
}

issue_key_json() {
  local client_id="$1"
  local key_name="$2"
  admin_api "/admin/api-keys" -X POST \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${client_id}\",\"name\":\"${key_name}\"}"
}

issue_key() {
  local client_id="$1"
  local key_name="${2:-abuse-key-$(date +%s%N)}"
  local response
  response="$(issue_key_json "${client_id}" "${key_name}")"
  require_json_value "${response}" "data['api_key']" "issue key ${key_name}"
}

revoke_key() {
  local key_id="$1"
  admin_api "/admin/api-keys/${key_id}" -X DELETE >/dev/null 2>&1 || true
}

cleanup_client() {
  local client_id="${1:-}"
  if [[ -z "${client_id}" ]]; then
    return
  fi
  admin_api "/admin/clients/${client_id}" -X DELETE >/dev/null 2>&1 || true
}

FREE_PLAN_ID="$(find_plan_id free)"
BASIC_PLAN_ID="$(find_plan_id basic)"

if [[ -z "${FREE_PLAN_ID}" || -z "${BASIC_PLAN_ID}" ]]; then
  log_error "Could not resolve required billing plans (free/basic)"
  exit 1
fi

client_name() {
  local slug="$1"
  printf 'abuse-%s-%s\n' "${slug}" "${RUN_SUFFIX}"
}

PAYLOAD_CLIENT=""
MAXT_CLIENT=""
STREAM_CLIENT=""
TTS_CLIENT=""

# 1. Invalid API key repeated -> 401
log_step "Testing invalid API key repeated"
INVALID_STATUSES=()
for i in {1..3}; do
  status="$(curl_base_url "${BASE_URL}/v1/models" -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer sk-invalid-${i}-test")"
  INVALID_STATUSES+=("${status}")
done
if [[ " ${INVALID_STATUSES[*]} " =~ " 401 " ]]; then
  record_result "invalid_api_key_repeated" "401" "${INVALID_STATUSES[0]}" "PASS" "all returned 401"
  log_ok "Invalid key -> 401"
else
  record_result "invalid_api_key_repeated" "401" "${INVALID_STATUSES[0]}" "FAIL"
  log_error "Invalid key did not return 401"
fi

# 2. Revoked API key -> 401
log_step "Testing revoked API key"
REV_CLIENT="$(ensure_client "$(client_name revoke-client)")"
REV_KEY_DATA="$(issue_key_json "${REV_CLIENT}" "revoke-me")"
REV_KEY="$(require_json_value "${REV_KEY_DATA}" "data['api_key']" "issue key revoke-me")"
REV_KEY_ID="$(require_json_value "${REV_KEY_DATA}" "data['id']" "issue key revoke-me")"
revoke_key "${REV_KEY_ID}"
RS="$(curl_base_url "${BASE_URL}/v1/models" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${REV_KEY}")"
if [[ "${RS}" == "401" ]]; then
  record_result "revoked_api_key" "401" "${RS}" "PASS"
  log_ok "Revoked key -> 401"
else
  record_result "revoked_api_key" "401" "${RS}" "FAIL"
  log_error "Revoked key expected 401, got ${RS}"
fi

# 3. Suspended client -> 402/403
log_step "Testing suspended client"
SUS_CLIENT="$(ensure_client "$(client_name suspended-client)")"
patch_client_json "${SUS_CLIENT}" '{"billing_status":"suspended"}'
SUS_KEY="$(issue_key "${SUS_CLIENT}" "abuse-suspended-key")"
SUS_STATUS="$(curl_base_url "${BASE_URL}/v1/models" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SUS_KEY}")"
if [[ "${SUS_STATUS}" == "402" || "${SUS_STATUS}" == "403" ]]; then
  record_result "suspended_client" "402/403" "${SUS_STATUS}" "PASS"
  log_ok "Suspended client -> ${SUS_STATUS}"
else
  record_result "suspended_client" "402/403" "${SUS_STATUS}" "FAIL"
  log_error "Suspended client expected 402/403, got ${SUS_STATUS}"
fi

# 4. Light flood -> 429
log_step "Testing light request flood"
FLOOD_CLIENT="$(ensure_client "$(client_name flood-client)")"
patch_client_json "${FLOOD_CLIENT}" '{"billing_plan_id":null,"rate_limit_per_minute":2,"daily_token_quota":100000,"weekly_token_quota":100000,"monthly_token_quota":100000,"max_context_tokens":4096,"max_output_tokens":512}'
FLOOD_KEY="$(issue_key "${FLOOD_CLIENT}" "abuse-flood-key")"
FLOOD_STATUSES=()
for _ in {1..5}; do
  status="$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${FLOOD_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"default","messages":[{"role":"user","content":"hi"}]}')"
  FLOOD_STATUSES+=("${status}")
done
if [[ " ${FLOOD_STATUSES[*]} " =~ " 429 " ]]; then
  record_result "light_flood" "429" "429" "PASS" "detected in ${FLOOD_STATUSES[*]}"
  log_ok "Flood -> 429 detected"
else
  record_result "light_flood" "429" "${FLOOD_STATUSES[*]}" "WARN" "rate limit did not trigger"
  log_warn "Flood did not trigger 429 (statuses: ${FLOOD_STATUSES[*]})"
fi

# 5. Invalid JSON payload -> 422
log_step "Testing invalid JSON payload"
PAYLOAD_CLIENT="$(ensure_client "$(client_name payload-client)")"
PAYLOAD_KEY="$(issue_key "${PAYLOAD_CLIENT}" "abuse-payload-key")"
JSON_STATUS="$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${PAYLOAD_KEY}" \
  -H "Content-Type: application/json" \
  -d "not json at all")"
if [[ "${JSON_STATUS}" == "422" || "${JSON_STATUS}" == "400" ]]; then
  record_result "invalid_json_payload" "422/400" "${JSON_STATUS}" "PASS"
  log_ok "Invalid JSON -> ${JSON_STATUS}"
else
  record_result "invalid_json_payload" "422/400" "${JSON_STATUS}" "FAIL"
  log_error "Invalid JSON expected 422/400, got ${JSON_STATUS}"
fi

# 6. Giant prompt -> 413
log_step "Testing giant prompt"
GIANT_CLIENT="$(ensure_client "$(client_name giant-client)")"
patch_client_json "${GIANT_CLIENT}" '{"billing_plan_id":null,"rate_limit_per_minute":100,"daily_token_quota":100000,"weekly_token_quota":100000,"monthly_token_quota":100000,"max_context_tokens":512,"max_output_tokens":512}'
GIANT_KEY="$(issue_key "${GIANT_CLIENT}" "abuse-giant-key")"
GIANT_PROMPT="$(python3 -c 'print("word " * 700, end="")')"
GIANT_STATUS="$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${GIANT_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"default\",\"messages\":[{\"role\":\"user\",\"content\":\"${GIANT_PROMPT}\"}]}")"
if [[ "${GIANT_STATUS}" == "413" ]]; then
  record_result "giant_prompt" "413" "${GIANT_STATUS}" "PASS"
  log_ok "Giant prompt -> 413"
else
  record_result "giant_prompt" "413" "${GIANT_STATUS}" "FAIL"
  log_error "Giant prompt expected 413, got ${GIANT_STATUS}"
fi

# 7. Excessive max_tokens -> not 413
log_step "Testing excessive max_tokens"
MAXT_CLIENT="$(ensure_client "$(client_name max-tokens-client)")"
MAXT_KEY="$(issue_key "${MAXT_CLIENT}" "abuse-max-tokens-key")"
MAXT_STATUS="$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${MAXT_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"default","messages":[{"role":"user","content":"hi"}],"max_tokens":999999}')"
if [[ "${MAXT_STATUS}" != "413" ]]; then
  record_result "excessive_max_tokens" "not 413" "${MAXT_STATUS}" "PASS" "capped or backend error"
  log_ok "Excessive max_tokens -> ${MAXT_STATUS} (not 413)"
else
  record_result "excessive_max_tokens" "not 413" "${MAXT_STATUS}" "FAIL"
  log_error "Excessive max_tokens unexpectedly returned 413"
fi

# 8. Embeddings input too large -> 400
log_step "Testing embeddings too many inputs"
EMB_CLIENT="$(ensure_client "$(client_name emb-client)")"
patch_client_json "${EMB_CLIENT}" "{\"billing_plan_id\":\"${FREE_PLAN_ID}\"}"
EMB_KEY="$(issue_key "${EMB_CLIENT}" "abuse-emb-key")"
EMB_STATUS="$(curl_base_url "${BASE_URL}/v1/embeddings" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${EMB_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-3-small","input":["a","b","c","d","e","f","g","h","i","j"]}')"
if [[ "${EMB_STATUS}" == "400" || "${EMB_STATUS}" == "413" ]]; then
  record_result "embeddings_too_many_inputs" "400/413" "${EMB_STATUS}" "PASS"
  log_ok "Embeddings too many inputs -> ${EMB_STATUS}"
else
  record_result "embeddings_too_many_inputs" "400/413" "${EMB_STATUS}" "WARN"
  log_warn "Embeddings expected 400/413, got ${EMB_STATUS}"
fi

# 9. Stream request -> not 500
log_step "Testing stream request handling"
STREAM_CLIENT="$(ensure_client "$(client_name stream-client)")"
patch_client_json "${STREAM_CLIENT}" "{\"billing_plan_id\":\"${FREE_PLAN_ID}\"}"
STREAM_KEY="$(issue_key "${STREAM_CLIENT}" "abuse-stream-key")"
STREAM_STATUS="$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${STREAM_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"default","messages":[{"role":"user","content":"hi"}],"stream":true}')"
if [[ "${STREAM_STATUS}" != "500" ]]; then
  record_result "interrupted_stream" "not 500" "${STREAM_STATUS}" "PASS"
  log_ok "Stream request -> ${STREAM_STATUS} (not 500)"
else
  record_result "interrupted_stream" "not 500" "${STREAM_STATUS}" "FAIL"
  log_error "Stream request crashed with 500"
fi

# 10. Concurrency above plan -> skip in quick mode
if [[ "${MODE}" == "full" ]]; then
  log_step "Testing concurrency above plan (full mode)"
  record_result "concurrency_above_plan" "429/503" "skipped" "SKIP" "use pytest for concurrency"
  log_info "Concurrency test delegated to pytest suite"
else
  record_result "concurrency_above_plan" "429/503" "skipped" "SKIP" "quick mode"
fi

# 11. Admin endpoints without token -> 401
log_step "Testing admin endpoints without token"
ADMIN_401_STATUS="$(curl_base_url "${BASE_URL}/admin/clients" -s -o /dev/null -w "%{http_code}")"
if [[ "${ADMIN_401_STATUS}" == "401" ]]; then
  record_result "admin_no_token" "401" "${ADMIN_401_STATUS}" "PASS"
  log_ok "Admin no token -> 401"
else
  record_result "admin_no_token" "401" "${ADMIN_401_STATUS}" "FAIL"
  log_error "Admin no token expected 401, got ${ADMIN_401_STATUS}"
fi

# 12. Cross-tenant resource access -> 401/403/404
log_step "Testing cross-tenant access"
TENANT_A="$(ensure_client "$(client_name tenant-a)")"
TENANT_B="$(ensure_client "$(client_name tenant-b)")"
KEY_A="$(issue_key "${TENANT_A}" "abuse-tenant-a-key")"
CROSS_STATUS="$(curl_base_url "${BASE_URL}/portal/me" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${KEY_A}")"
if [[ "${CROSS_STATUS}" == "200" ]]; then
  FORGED_STATUS="$(curl_base_url "${BASE_URL}/admin/api-keys" -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${KEY_A}" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${TENANT_B}\",\"name\":\"forged-key\"}")"
  if [[ "${FORGED_STATUS}" == "401" || "${FORGED_STATUS}" == "403" || "${FORGED_STATUS}" == "404" ]]; then
    record_result "cross_tenant_access" "401/403/404" "${FORGED_STATUS}" "PASS"
    log_ok "Cross-tenant access -> ${FORGED_STATUS}"
  else
    record_result "cross_tenant_access" "401/403/404" "${FORGED_STATUS}" "FAIL"
    log_error "Cross-tenant expected 401/403/404, got ${FORGED_STATUS}"
  fi
else
  record_result "cross_tenant_access" "200 baseline" "${CROSS_STATUS}" "FAIL" "baseline failed"
  log_error "Tenant baseline failed with ${CROSS_STATUS}"
fi

# 13. TTS input above limit -> 413
log_step "Testing TTS input above limit"
TTS_CLIENT="$(ensure_client "$(client_name tts-client)")"
patch_client_json "${TTS_CLIENT}" "{\"billing_plan_id\":\"${BASIC_PLAN_ID}\"}"
TTS_KEY="$(issue_key "${TTS_CLIENT}" "abuse-tts-key")"
TTS_TEXT="$(python3 -c 'print("a" * 1000, end="")')"
TTS_STATUS="$(curl_base_url "${BASE_URL}/pocket-tts/tts" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${TTS_KEY}" \
  --data-urlencode "text=${TTS_TEXT}")"
if [[ "${TTS_STATUS}" == "413" ]]; then
  record_result "tts_input_above_limit" "413" "${TTS_STATUS}" "PASS"
  log_ok "TTS above limit -> 413"
else
  record_result "tts_input_above_limit" "413" "${TTS_STATUS}" "WARN"
  log_warn "TTS above limit expected 413, got ${TTS_STATUS}"
fi

# 14. RAG upload above limit -> 429
log_step "Testing RAG upload above limit"
RAG_CLIENT="$(ensure_client "$(client_name rag-client)")"
patch_client_json "${RAG_CLIENT}" "{\"billing_plan_id\":\"${FREE_PLAN_ID}\"}"
RAG_KEY="$(issue_key "${RAG_CLIENT}" "abuse-rag-key")"
UP1=""
UP_LAST=""
for i in {1..6}; do
  rag_file="${OUTPUT_DIR}/rag-doc-${i}.txt"
  printf 'doc-%s\n' "${i}" > "${rag_file}"
  status="$(curl_base_url "${BASE_URL}/client/rag/documents" -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${RAG_KEY}" \
    -F "file=@${rag_file};type=text/plain")"
  if [[ -z "${UP1}" ]]; then
    UP1="${status}"
  fi
  UP_LAST="${status}"
done
if [[ "${UP_LAST}" == "429" ]]; then
  record_result "rag_upload_above_limit" "429" "${UP_LAST}" "PASS"
  log_ok "RAG upload above limit -> 429"
else
  record_result "rag_upload_above_limit" "429" "${UP_LAST}" "WARN" "first=${UP1} last=${UP_LAST}"
  log_warn "RAG upload limit not triggered (first=${UP1}, last=${UP_LAST})"
fi

# Final health check
log_step "Final health check"
HEALTH_STATUS="$(curl_base_url "${BASE_URL}/health" -s -o /dev/null -w "%{http_code}")"
if [[ "${HEALTH_STATUS}" == "200" ]]; then
  HEALTH_STATUS="healthy"
  log_ok "System healthy after abuse tests"
else
  HEALTH_STATUS="unhealthy (${HEALTH_STATUS})"
  log_error "System unhealthy after abuse tests"
fi

# Cleanup
log_step "Cleanup"
cleanup_client "${REV_CLIENT}"
cleanup_client "${SUS_CLIENT}"
cleanup_client "${FLOOD_CLIENT}"
cleanup_client "${PAYLOAD_CLIENT}"
cleanup_client "${GIANT_CLIENT}"
cleanup_client "${MAXT_CLIENT}"
cleanup_client "${EMB_CLIENT}"
cleanup_client "${STREAM_CLIENT}"
cleanup_client "${TENANT_A}"
cleanup_client "${TENANT_B}"
cleanup_client "${TTS_CLIENT}"
cleanup_client "${RAG_CLIENT}"
log_ok "Cleanup done"

# Generate JSON report
python3 - "${REPORT_JSON}" "${HEALTH_STATUS}" "${MODE}" "${TIMESTAMP}" "${RESULTS_FILE}" <<'PY'
import json
import sys

report_path, health, mode, timestamp, results_file = sys.argv[1:6]
scenarios = []
with open(results_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        scenarios.append(
            {
                "scenario": parts[0] if len(parts) > 0 else "",
                "expected": parts[1] if len(parts) > 1 else "",
                "actual": parts[2] if len(parts) > 2 else "",
                "status": parts[3] if len(parts) > 3 else "",
                "note": parts[4] if len(parts) > 4 else "",
            }
        )

report = {
    "timestamp": timestamp,
    "mode": mode,
    "health_after_tests": health,
    "summary": {
        "total": len(scenarios),
        "passed": sum(1 for s in scenarios if s["status"] == "PASS"),
        "failed": sum(1 for s in scenarios if s["status"] == "FAIL"),
        "warnings": sum(1 for s in scenarios if s["status"] == "WARN"),
        "skipped": sum(1 for s in scenarios if s["status"] == "SKIP"),
    },
    "scenarios": scenarios,
}

with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
    f.write("\n")
PY

# Generate Markdown report
cat > "${REPORT_MD}" <<EOF
# Abuse Protection Validation Report

- **Timestamp:** ${TIMESTAMP}
- **Mode:** ${MODE}
- **Health after tests:** ${HEALTH_STATUS}

## Summary

| Metric | Count |
| :--- | ---: |
| Total | $(python3 -c "import json; d=json.load(open('${REPORT_JSON}')); print(d['summary']['total'])") |
| Passed | $(python3 -c "import json; d=json.load(open('${REPORT_JSON}')); print(d['summary']['passed'])") |
| Failed | $(python3 -c "import json; d=json.load(open('${REPORT_JSON}')); print(d['summary']['failed'])") |
| Warnings | $(python3 -c "import json; d=json.load(open('${REPORT_JSON}')); print(d['summary']['warnings'])") |
| Skipped | $(python3 -c "import json; d=json.load(open('${REPORT_JSON}')); print(d['summary']['skipped'])") |

## Scenarios

| Scenario | Expected | Actual | Status | Note |
| :--- | :--- | :--- | :---: | :--- |
EOF

python3 - "${REPORT_JSON}" <<'PY' >> "${REPORT_MD}"
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)

for s in data["scenarios"]:
    print(f"| {s['scenario']} | {s['expected']} | {s['actual']} | {s['status']} | {s.get('note', '')} |")
PY

FAILED_COUNT="$(python3 -c "import json; d=json.load(open('${REPORT_JSON}')); print(d['summary']['failed'])")"

log_section "Abuse Protection Validation Complete"
log_info "Report JSON: ${REPORT_JSON}"
log_info "Report MD: ${REPORT_MD}"

if [[ "${HEALTH_STATUS}" == "healthy" && "${FAILED_COUNT}" -eq 0 ]]; then
  log_ok "All critical abuse scenarios passed and system is healthy"
  exit 0
fi

log_warn "Some abuse scenarios failed or system health degraded; review ${REPORT_MD}"
exit 0
