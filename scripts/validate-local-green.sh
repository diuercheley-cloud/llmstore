#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/lib/validation-logging.sh"
init_stack_env

STACK_ENV_PATH="${STACK_ENV_FILE}"
if [[ "${STACK_ENV_PATH}" != /* ]]; then
  STACK_ENV_PATH="${ROOT_DIR}/${STACK_ENV_PATH}"
fi

TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
OUTPUT_DIR="${ROOT_DIR}/artifacts/local-green-validation/${TIMESTAMP}"
LOGS_DIR="${OUTPUT_DIR}/logs"
SUMMARY_JSON="${OUTPUT_DIR}/summary.json"
SUMMARY_MD="${OUTPUT_DIR}/summary.md"
mkdir -p "${LOGS_DIR}"
OVERALL_EXIT_CODE=0

RESULTS_FILE="$(mktemp)"
printf '[]\n' > "${RESULTS_FILE}"
trap 'rm -f "${RESULTS_FILE}"' EXIT

append_result() {
  python3 - "$RESULTS_FILE" "$1" "$2" "$3" "$4" <<'PY'
import json
import sys

path, name, status, exit_code, log_file = sys.argv[1:6]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
data.append({
    "name": name,
    "status": status,
    "exit_code": int(exit_code),
    "log_file": log_file,
})
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
PY
}

run_step() {
  local name="$1"
  local log_file="logs/${name}.log"
  shift

  log_step "Running ${name}"
  if (
    cd "${ROOT_DIR}" || exit 1
    "$@"
  ) > "${OUTPUT_DIR}/${log_file}" 2>&1; then
    append_result "${name}" "ok" "0" "${log_file}"
    log_ok "${name} OK"
  else
    local exit_code=$?
    append_result "${name}" "error" "${exit_code}" "${log_file}"
    log_error "${name} FAILED (exit ${exit_code})"
    OVERALL_EXIT_CODE=1
  fi
}

log_section "Local Green Validation"
log_info "Output: ${OUTPUT_DIR}"

run_step "check-secrets" ./scripts/check-secrets.sh --all
run_step "docker-compose-ps" docker compose --env-file "${STACK_ENV_PATH}" -f "${ROOT_DIR}/docker-compose.yml" ps
run_step "validate-local-production-full" ./scripts/validate-local-production-full.sh
run_step "pytest-control-plane" docker compose --env-file "${STACK_ENV_PATH}" -f "${ROOT_DIR}/docker-compose.yml" exec -T control-plane python -m pytest -q

if [[ -f "${ROOT_DIR}/scripts/dr-test-local.sh" ]]; then
  run_step "dr-test-local" ./scripts/dr-test-local.sh
else
  append_result "dr-test-local" "skip" "0" "not_available"
  log_warn "dr-test-local skipped: script not found"
fi

python3 - "${RESULTS_FILE}" "${SUMMARY_JSON}" "${SUMMARY_MD}" "${OUTPUT_DIR}" <<'PY'
import json
import sys

results_file, summary_json, summary_md, output_dir = sys.argv[1:5]
with open(results_file, "r", encoding="utf-8") as handle:
    results = json.load(handle)

success = all(item["status"] == "ok" or item["status"] == "skip" for item in results)
summary = {
    "validation_result": {"success": success},
    "results": results,
    "artifacts_dir": output_dir,
}

with open(summary_json, "w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)
    handle.write("\n")

with open(summary_md, "w", encoding="utf-8") as handle:
    handle.write("# Local Green Validation Summary\n\n")
    handle.write(f"**Result: {'SUCCESS' if success else 'FAILED'}**\n\n")
    handle.write("| Step | Status | Exit Code | Log |\n")
    handle.write("| :--- | :--- | :---: | :--- |\n")
    for item in results:
        handle.write(f"| `{item['name']}` | {item['status'].upper()} | {item['exit_code']} | `{item['log_file']}` |\n")
PY

if python3 - "${SUMMARY_JSON}" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    sys.exit(0 if json.load(handle)["validation_result"]["success"] else 1)
PY
then
  log_ok "LOCAL GREEN VALIDATION SUCCESSFUL"
  exit 0
fi

log_error "LOCAL GREEN VALIDATION FAILED"
exit "${OVERALL_EXIT_CODE}"
