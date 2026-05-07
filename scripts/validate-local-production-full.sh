#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
OUTPUT_DIR="${ROOT_DIR}/artifacts/local-production-validation/${TIMESTAMP}"
SUMMARY_JSON="${OUTPUT_DIR}/summary.json"
SUMMARY_MD="${OUTPUT_DIR}/summary.md"
RESULTS_FILE="$(mktemp)"
WARNINGS_FILE="$(mktemp)"
FAILURES_FILE="$(mktemp)"
START_EPOCH="$(date +%s)"

mkdir -p "${OUTPUT_DIR}"
printf '[]\n' >"${RESULTS_FILE}"
printf '[]\n' >"${WARNINGS_FILE}"
printf '[]\n' >"${FAILURES_FILE}"

cleanup() {
  rm -f "${RESULTS_FILE}" "${WARNINGS_FILE}" "${FAILURES_FILE}"
}
trap cleanup EXIT

VERSION="$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "unknown")"
GIT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo "not-a-git-repo")"
BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_BASE_URL="${ADMIN_BASE_URL:-${BASE_URL}/admin}"
LM_STUDIO_BASE_URL="${LM_STUDIO_BASE_URL:-http://192.168.101.1:1234/v1}"

SERVICES_TESTED=(
  "control-plane"
  "postgres"
  "redis"
  "admin-lab"
  "client-portal"
  "billing"
  "routing"
  "api-keys"
  "docs"
  "observability"
)

ENDPOINTS_TESTED=(
  "${BASE_URL}/"
  "${BASE_URL}/health"
  "${BASE_URL}/ready"
  "${BASE_URL}/status"
  "${BASE_URL}/v1/models"
  "${BASE_URL}/v1/chat/completions"
  "${BASE_URL}/pricing"
  "${BASE_URL}/signup"
  "${BASE_URL}/docs"
  "${BASE_URL}/developer-docs"
  "${BASE_URL}/admin/status"
  "${BASE_URL}/admin/health/deep"
  "${BASE_URL}/admin/clients"
  "${BASE_URL}/admin/api-keys"
  "${BASE_URL}/admin/backends"
  "${BASE_URL}/admin/backends/list-models"
  "${BASE_URL}/admin/billing/plans"
  "${BASE_URL}/admin/billing/invoices"
  "${BASE_URL}/admin/billing/run-cycle"
  "${BASE_URL}/admin/routing/explain"
  "${BASE_URL}/admin/usage/summary"
  "${BASE_URL}/admin/usage/by-client"
  "${BASE_URL}/admin/usage/by-model"
  "${BASE_URL}/admin-dashboard"
  "${BASE_URL}/portal/me"
  "${BASE_URL}/client/rag/documents"
  "${BASE_URL}/client/rag/query"
  "${BASE_URL}/admin/rag/usage"
  "${LM_STUDIO_BASE_URL}/models"
)

append_json_object() {
  local file="$1"
  local payload="$2"
  python3 - "${file}" "${payload}" <<'PY'
import json
import sys

path = sys.argv[1]
payload = json.loads(sys.argv[2])
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
data.append(payload)
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
PY
}

json_string_array() {
  python3 - "$@" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1:]))
PY
}

add_warning() {
  local message="$1"
  append_json_object "${WARNINGS_FILE}" "$(python3 - "${message}" <<'PY'
import json
import sys
print(json.dumps({"message": sys.argv[1]}))
PY
)"
}

add_failure() {
  local script_name="$1"
  local message="$2"
  append_json_object "${FAILURES_FILE}" "$(python3 - "${script_name}" "${message}" <<'PY'
import json
import sys
print(json.dumps({"script": sys.argv[1], "message": sys.argv[2]}))
PY
)"
}

record_result() {
  local script_name="$1"
  local status="$2"
  local exit_code="$3"
  local duration="$4"
  local critical="$5"
  local log_file="$6"
  local note="${7:-}"

  append_json_object "${RESULTS_FILE}" "$(python3 - \
    "${script_name}" "${status}" "${exit_code}" "${duration}" "${critical}" "${log_file}" "${note}" <<'PY'
import json
import sys

print(json.dumps({
    "script": sys.argv[1],
    "status": sys.argv[2],
    "exit_code": int(sys.argv[3]),
    "duration_seconds": int(sys.argv[4]),
    "critical": sys.argv[5] == "true",
    "log": sys.argv[6],
    "note": sys.argv[7],
}))
PY
)"
}

run_validation() {
  local script_name="$1"
  local critical="${2:-true}"
  local note="${3:-}"
  local script_path="${SCRIPT_DIR}/${script_name}"
  local log_file="${OUTPUT_DIR}/${script_name}.log"
  local start
  local end
  local duration
  local exit_code=0
  local status="success"

  printf '\n[%s] Running %s\n' "$(date +%H:%M:%S)" "${script_name}"
  start="$(date +%s)"

  if [[ ! -x "${script_path}" && ! -f "${script_path}" ]]; then
    printf 'Script not found: %s\n' "${script_path}" >"${log_file}"
    exit_code=127
  else
    (
      cd "${ROOT_DIR}" || exit 1
      BASE_URL="${BASE_URL}" \
      ADMIN_BASE_URL="${ADMIN_BASE_URL}" \
      CONTROL_PLANE_URL="${BASE_URL}" \
      LM_STUDIO_BASE_URL="${LM_STUDIO_BASE_URL}" \
      bash "${script_path}"
    ) >"${log_file}" 2>&1
    exit_code=$?
  fi

  end="$(date +%s)"
  duration=$((end - start))

  if [[ "${exit_code}" -ne 0 ]]; then
    if [[ "${critical}" == "true" ]]; then
      status="failed"
      add_failure "${script_name}" "exit code ${exit_code}; see ${log_file}"
      printf '[FAILED] %s (%ss)\n' "${script_name}" "${duration}"
    else
      status="warning"
      add_warning "${script_name} exited with ${exit_code}; see ${log_file}"
      printf '[WARNING] %s (%ss)\n' "${script_name}" "${duration}"
    fi
  else
    printf '[OK] %s (%ss)\n' "${script_name}" "${duration}"
  fi

  record_result "${script_name}" "${status}" "${exit_code}" "${duration}" "${critical}" "${log_file}" "${note}"
}

skip_validation() {
  local script_name="$1"
  local critical="$2"
  local note="$3"
  local log_file="${OUTPUT_DIR}/${script_name}.log"

  printf '%s\n' "${note}" >"${log_file}"
  record_result "${script_name}" "skipped" "0" "0" "${critical}" "${log_file}" "${note}"
  printf '[SKIPPED] %s: %s\n' "${script_name}" "${note}"
}

psp_configured="false"
if [[ -n "${PSP_PROVIDER:-}" || -n "${PAYMENT_PROVIDER:-}" || -n "${STRIPE_SECRET_KEY:-}" || -n "${MERCADOPAGO_ACCESS_TOKEN:-}" ]]; then
  psp_configured="true"
else
  add_warning "PSP is not configured. This is expected for local validation; real PSP integration is out of scope."
fi

printf '%s\n' "--- LOCAL PRODUCTION FULL VALIDATION ---"
printf 'Version: %s\n' "${VERSION}"
printf 'Commit: %s\n' "${GIT_COMMIT}"
printf 'Base URL: %s\n' "${BASE_URL}"
printf 'Timestamp: %s\n' "${TIMESTAMP}"
printf 'Output: %s\n' "${OUTPUT_DIR}"
printf '%s\n' "----------------------------------------"

run_validation "validate-localhost-mode.sh" "true"
run_validation "validate-status-local.sh" "true"
run_validation "validate-admin-lab-local.sh" "true"

if curl -fsS --connect-timeout 2 --max-time 5 "${LM_STUDIO_BASE_URL}/models" >/dev/null 2>&1; then
  run_validation "validate-lmstudio-backend.sh" "false" "LM Studio is online; integration validation executed."
else
  skip_validation "validate-lmstudio-backend.sh" "false" "LM Studio offline at ${LM_STUDIO_BASE_URL}; offline LM Studio is a warning, not a critical failure."
fi

run_validation "validate-routing-local.sh" "true"
run_validation "validate-plan-queues.sh" "true"
run_validation "validate-client-portal-local.sh" "true"
run_validation "validate-api-keys-local.sh" "true"

if [[ "${RAG_ENABLED:-true}" == "true" ]]; then
  run_validation "validate-rag-local-multiclient.sh" "true"
else
  skip_validation "validate-rag-local-multiclient.sh" "false" "RAG_ENABLED=${RAG_ENABLED}; RAG validation is conditional."
fi

run_validation "validate-local-billing.sh" "true" "Manual billing validation only; real PSP is not part of local scope."
run_validation "validate-local-docs.sh" "true"
run_validation "validate-observability-local.sh" "true"

TOTAL_DURATION=$(( $(date +%s) - START_EPOCH ))
SERVICES_JSON="$(json_string_array "${SERVICES_TESTED[@]}")"
ENDPOINTS_JSON="$(json_string_array "${ENDPOINTS_TESTED[@]}")"

python3 - \
  "${SUMMARY_JSON}" \
  "${SUMMARY_MD}" \
  "${RESULTS_FILE}" \
  "${WARNINGS_FILE}" \
  "${FAILURES_FILE}" \
  "${VERSION}" \
  "${GIT_COMMIT}" \
  "${TIMESTAMP}" \
  "${TOTAL_DURATION}" \
  "${BASE_URL}" \
  "${psp_configured}" \
  "${SERVICES_JSON}" \
  "${ENDPOINTS_JSON}" <<'PY'
import json
import sys

summary_json, summary_md, results_file, warnings_file, failures_file = sys.argv[1:6]
version, commit, timestamp = sys.argv[6:9]
duration = int(sys.argv[9])
base_url = sys.argv[10]
psp_configured = sys.argv[11] == "true"
services = json.loads(sys.argv[12])
endpoints = json.loads(sys.argv[13])

with open(results_file, "r", encoding="utf-8") as handle:
    results = json.load(handle)
with open(warnings_file, "r", encoding="utf-8") as handle:
    global_warnings = json.load(handle)
with open(failures_file, "r", encoding="utf-8") as handle:
    failures = json.load(handle)

warning_results = [
    {
        "script": item["script"],
        "message": item["note"] or f"status={item['status']}",
        "log": item["log"],
    }
    for item in results
    if item["status"] in {"warning", "skipped"}
]
warnings = global_warnings + warning_results
critical_failures = [item for item in results if item["critical"] and item["status"] == "failed"]
status = "failed" if critical_failures else "success"

next_steps = [
    "Inspect failed script logs and rerun make validate-local-production.",
    "Confirm local services with docker compose ps if health or readiness checks failed.",
] if critical_failures else [
    "Archive the generated artifact directory with the local release evidence.",
    "Use this report as the baseline before staging or production validation.",
]
if not psp_configured:
    next_steps.append("Keep PSP disabled for local validation unless a separate PSP integration task is opened.")

summary = {
    "version": version,
    "commit": commit,
    "timestamp": timestamp,
    "base_url": base_url,
    "status": status,
    "duration_seconds": duration,
    "services_tested": services,
    "endpoints_tested": endpoints,
    "scripts_executed": results,
    "failures": failures,
    "warnings": warnings,
    "psp_configured": psp_configured,
    "next_steps": next_steps,
}

with open(summary_json, "w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)
    handle.write("\n")

with open(summary_md, "w", encoding="utf-8") as handle:
    handle.write("# Local Production Validation Summary\n\n")
    handle.write(f"- Status: {status.upper()}\n")
    handle.write(f"- Version: {version}\n")
    handle.write(f"- Commit: {commit}\n")
    handle.write(f"- Base URL: {base_url}\n")
    handle.write(f"- Timestamp: {timestamp}\n")
    handle.write(f"- Duration: {duration}s\n")
    handle.write(f"- PSP configured: {'yes' if psp_configured else 'no'}\n\n")

    handle.write("## Services Tested\n\n")
    for service in services:
        handle.write(f"- {service}\n")

    handle.write("\n## Endpoints Tested\n\n")
    for endpoint in endpoints:
        handle.write(f"- `{endpoint}`\n")

    handle.write("\n## Scripts Executed\n\n")
    handle.write("| Script | Status | Critical | Duration | Log |\n")
    handle.write("| --- | --- | --- | ---: | --- |\n")
    for item in results:
        handle.write(
            f"| `{item['script']}` | {item['status']} | "
            f"{'yes' if item['critical'] else 'no'} | "
            f"{item['duration_seconds']}s | `{item['log']}` |\n"
        )

    handle.write("\n## Failures\n\n")
    if failures:
        for item in failures:
            handle.write(f"- `{item['script']}`: {item['message']}\n")
    else:
        handle.write("- None\n")

    handle.write("\n## Warnings\n\n")
    if warnings:
        for item in warnings:
            prefix = f"`{item['script']}`: " if "script" in item else ""
            handle.write(f"- {prefix}{item['message']}\n")
    else:
        handle.write("- None\n")

    handle.write("\n## Next Steps\n\n")
    for index, item in enumerate(next_steps, 1):
        handle.write(f"{index}. {item}\n")
PY

printf '%s\n' "----------------------------------------"
printf 'Summary JSON: %s\n' "${SUMMARY_JSON}"
printf 'Summary MD: %s\n' "${SUMMARY_MD}"

if python3 - "${SUMMARY_JSON}" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    sys.exit(0 if json.load(handle)["status"] == "success" else 1)
PY
then
  printf '%s\n' "VALIDATION SUCCESSFUL"
  exit 0
fi

printf '%s\n' "VALIDATION FAILED"
exit 1
