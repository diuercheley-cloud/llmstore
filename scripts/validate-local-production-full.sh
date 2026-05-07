#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/validation-logging.sh"
init_stack_env

TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
TIMESTAMP_START="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
OUTPUT_DIR="${ROOT_DIR}/artifacts/local-production-validation/${TIMESTAMP}"
LOGS_DIR="${OUTPUT_DIR}/logs"
SUMMARY_JSON="${OUTPUT_DIR}/summary.json"
SUMMARY_MD="${OUTPUT_DIR}/summary.md"
RESULTS_FILE="$(mktemp)"
WARNINGS_FILE="$(mktemp)"
FAILURES_FILE="$(mktemp)"
START_EPOCH="$(date +%s)"

mkdir -p "${LOGS_DIR}"
printf '[]\n' >"${RESULTS_FILE}"
printf '[]\n' >"${WARNINGS_FILE}"
printf '[]\n' >"${FAILURES_FILE}"

cleanup() {
  rm -f "${RESULTS_FILE}" "${WARNINGS_FILE}" "${FAILURES_FILE}"
}
trap cleanup EXIT

VERSION="$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "unknown")"
GIT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo "not-a-git-repo")"
GIT_BRANCH="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
GIT_TAG_BASE="$(git -C "${ROOT_DIR}" describe --tags --abbrev=0 2>/dev/null || echo "none")"

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_BASE_URL="${ADMIN_BASE_URL:-${BASE_URL}/admin}"
LM_STUDIO_BASE_URL="${LM_STUDIO_BASE_URL:-http://192.168.101.1:1234/v1}"

# Environment flags
LOCALHOST_MODE="${LOCALHOST_MODE:-false}"
LOCAL_BILLING_MODE="${LOCAL_BILLING_MODE:-false}"
RAG_ENABLED_FLAG="${RAG_ENABLED:-true}"
LM_STUDIO_CONFIGURED="false"
if [[ "${LM_STUDIO_BASE_URL}" != "http://192.168.101.1:1234/v1" ]]; then
  LM_STUDIO_CONFIGURED="true"
fi
LM_STUDIO_ONLINE="unknown"

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
  local started_at="$7"
  local finished_at="$8"
  local note="${9:-}"
  local error_summary="${10:-}"

  append_json_object "${RESULTS_FILE}" "$(python3 - \
    "${script_name}" "${status}" "${exit_code}" "${duration}" "${critical}" "${log_file}" "${started_at}" "${finished_at}" "${note}" "${error_summary}" <<'PY'
import json
import sys

print(json.dumps({
    "name": sys.argv[1],
    "path": f"scripts/{sys.argv[1]}",
    "status": sys.argv[2],
    "exit_code": int(sys.argv[3]),
    "duration_seconds": int(sys.argv[4]),
    "critical": sys.argv[5] == "true",
    "log_file": sys.argv[6],
    "started_at": sys.argv[7],
    "finished_at": sys.argv[8],
    "note": sys.argv[9],
    "error_summary": sys.argv[10],
}))
PY
)"
}

run_validation() {
  local script_name="$1"
  local critical="${2:-true}"
  local note="${3:-}"
  local script_path="${SCRIPT_DIR}/${script_name}"
  local log_file="logs/${script_name}.log"
  local full_log_path="${OUTPUT_DIR}/${log_file}"
  local start_time
  local started_at
  local finished_at
  local exit_code=0
  local status="ok"
  local error_summary=""

  log_step "Running ${script_name}"
  started_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  start_time=$(start_timer)

  if [[ ! -x "${script_path}" && ! -f "${script_path}" ]]; then
    log_error "Script not found: ${script_path}" >"${full_log_path}"
    exit_code=127
    error_summary="Script not found"
  else
    (
      cd "${ROOT_DIR}" || exit 1
      BASE_URL="${BASE_URL}" \
      ADMIN_BASE_URL="${ADMIN_BASE_URL}" \
      CONTROL_PLANE_URL="${BASE_URL}" \
      LM_STUDIO_BASE_URL="${LM_STUDIO_BASE_URL}" \
      bash "${script_path}"
    ) >"${full_log_path}" 2>&1
    exit_code=$?
  fi

  local duration
  duration=$(end_timer "${start_time}")
  finished_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  if [[ "${exit_code}" -ne 0 ]]; then
    if [[ "${critical}" == "true" ]]; then
      status="error"
      error_summary="exit code ${exit_code}"
      add_failure "${script_name}" "exit code ${exit_code}; see ${log_file}"
      log_error "${script_name} FAILED (${duration})"
    else
      status="warn"
      error_summary="exit code ${exit_code}"
      add_warning "${script_name} exited with ${exit_code}; see ${log_file}"
      log_warn "${script_name} WARNING (${duration})"
    fi
  else
    log_ok "${script_name} OK (${duration})"
  fi

  local duration_sec
  duration_sec=$(echo "${duration}" | sed 's/s//' | awk '{print int($1)}')
  record_result "${script_name}" "${status}" "${exit_code}" "${duration_sec}" "${critical}" "${log_file}" "${started_at}" "${finished_at}" "${note}" "${error_summary}"
}

skip_validation() {
  local script_name="$1"
  local critical="$2"
  local note="$3"
  local log_file="logs/${script_name}.log"
  local full_log_path="${OUTPUT_DIR}/${log_file}"
  local timestamp
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  printf '%s\n' "${note}" >"${full_log_path}"
  record_result "${script_name}" "skip" "0" "0" "${critical}" "${log_file}" "${timestamp}" "${timestamp}" "${note}" ""
  log_info "[SKIPPED] ${script_name}: ${note}"
}

log_section "Local Production Full Validation"
log_info "Version: ${VERSION}"
log_info "Commit: ${GIT_COMMIT}"
log_info "Branch: ${GIT_BRANCH}"
log_info "Base URL: ${BASE_URL}"
log_info "Timestamp: ${TIMESTAMP}"
log_info "Output: ${OUTPUT_DIR}"

run_validation "validate-localhost-mode.sh" "true"
run_validation "validate-status-local.sh" "true"
run_validation "validate-admin-lab-local.sh" "true"

if curl -fsS --connect-timeout 2 --max-time 5 "${LM_STUDIO_BASE_URL}/models" >/dev/null 2>&1; then
  LM_STUDIO_ONLINE="true"
  run_validation "validate-lmstudio-backend.sh" "false" "LM Studio is online; integration validation executed."
else
  LM_STUDIO_ONLINE="false"
  skip_validation "validate-lmstudio-backend.sh" "false" "LM Studio offline at ${LM_STUDIO_BASE_URL}"
fi

run_validation "validate-routing-local.sh" "true"
run_validation "validate-plan-queues.sh" "true"
run_validation "validate-client-portal-local.sh" "true"
run_validation "validate-api-keys-local.sh" "true"

if [[ "${RAG_ENABLED_FLAG}" == "true" ]]; then
  run_validation "validate-rag-local-multiclient.sh" "true"
else
  skip_validation "validate-rag-local-multiclient.sh" "false" "RAG_ENABLED=${RAG_ENABLED_FLAG}"
fi

run_validation "validate-local-billing.sh" "true" "Manual billing validation only"
run_validation "validate-local-docs.sh" "true"
run_validation "validate-observability-local.sh" "true"

TIMESTAMP_END="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
TOTAL_DURATION=$(( $(date +%s) - START_EPOCH ))

python3 - \
  "${SUMMARY_JSON}" \
  "${SUMMARY_MD}" \
  "${RESULTS_FILE}" \
  "${WARNINGS_FILE}" \
  "${FAILURES_FILE}" \
  "${VERSION}" \
  "${GIT_COMMIT}" \
  "${GIT_BRANCH}" \
  "${GIT_TAG_BASE}" \
  "${TIMESTAMP_START}" \
  "${TIMESTAMP_END}" \
  "${TOTAL_DURATION}" \
  "${BASE_URL}" \
  "${LOCALHOST_MODE}" \
  "${LOCAL_BILLING_MODE}" \
  "${RAG_ENABLED_FLAG}" \
  "${LM_STUDIO_CONFIGURED}" \
  "${LM_STUDIO_ONLINE}" \
  "${OUTPUT_DIR}" <<'PY'
import json
import sys
import os

(
    summary_json, summary_md, results_file, warnings_file, failures_file,
    version, git_commit, git_branch, git_tag_base,
    timestamp_start, timestamp_end, duration, base_url,
    localhost_mode, local_billing_mode, rag_enabled,
    lm_studio_configured, lm_studio_online, output_dir
) = sys.argv[1:20]

duration = int(duration)
localhost_mode = localhost_mode == "true"
local_billing_mode = local_billing_mode == "true"
rag_enabled = rag_enabled == "true"
lm_studio_configured = lm_studio_configured == "true"

with open(results_file, "r", encoding="utf-8") as handle:
    scripts = json.load(handle)
with open(warnings_file, "r", encoding="utf-8") as handle:
    global_warnings = json.load(handle)
with open(failures_file, "r", encoding="utf-8") as handle:
    failures = json.load(handle)

ok_count = sum(1 for s in scripts if s["status"] == "ok")
warn_count = sum(1 for s in scripts if s["status"] == "warn")
skip_count = sum(1 for s in scripts if s["status"] == "skip")
error_count = sum(1 for s in scripts if s["status"] == "error")

critical_failures = [s for s in scripts if s["critical"] and s["status"] == "error"]
success = len(critical_failures) == 0

summary = {
    "version": version,
    "git_commit": git_commit,
    "git_branch": git_branch,
    "git_tag_base": git_tag_base,
    "timestamp_start": timestamp_start,
    "timestamp_end": timestamp_end,
    "duration_seconds": duration,
    "base_url": base_url,
    "environment": {
        "LOCALHOST_MODE": localhost_mode,
        "LOCAL_BILLING_MODE": local_billing_mode,
        "RAG_ENABLED": rag_enabled,
        "LM_STUDIO_CONFIGURED": lm_studio_configured,
        "LM_STUDIO_ONLINE": lm_studio_online,
    },
    "scripts": scripts,
    "totals": {
        "ok": ok_count,
        "warn": warn_count,
        "skip": skip_count,
        "error": error_count,
    },
    "artifacts": {
        "summary_md": "summary.md",
        "summary_json": "summary.json",
        "logs_dir": "logs/",
    },
    "validation_result": {
        "success": success,
        "critical_failures": len(critical_failures),
        "warnings": warn_count + len(global_warnings),
    }
}

with open(summary_json, "w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)
    handle.write("\n")

with open(summary_md, "w", encoding="utf-8") as handle:
    handle.write("# Local Production Validation Summary\n\n")
    
    status_str = "SUCCESS" if success else "FAILED"
    handle.write(f"**Result: {status_str}**\n\n")

    handle.write("## Metadata\n\n")
    handle.write(f"- **Version:** {version}\n")
    handle.write(f"- **Branch:** {git_branch}\n")
    handle.write(f"- **Commit:** {git_commit}\n")
    handle.write(f"- **Base URL:** {base_url}\n")
    handle.write(f"- **Start Time:** {timestamp_start}\n")
    handle.write(f"- **End Time:** {timestamp_end}\n")
    handle.write(f"- **Total Duration:** {duration}s\n\n")

    handle.write("## Environment\n\n")
    handle.write(f"- LOCALHOST_MODE: `{localhost_mode}`\n")
    handle.write(f"- LOCAL_BILLING_MODE: `{local_billing_mode}`\n")
    handle.write(f"- RAG_ENABLED: `{rag_enabled}`\n")
    handle.write(f"- LM_STUDIO_CONFIGURED: `{lm_studio_configured}`\n")
    handle.write(f"- LM_STUDIO_ONLINE: `{lm_studio_online}`\n\n")

    handle.write("## Execution Summary\n\n")
    handle.write("| Script | Status | Critical | Duration | Log |\n")
    handle.write("| :--- | :--- | :---: | :---: | :--- |\n")
    for s in scripts:
        handle.write(
            f"| `{s['name']}` | {s['status'].upper()} | "
            f"{'Yes' if s['critical'] else 'No'} | "
            f"{s['duration_seconds']}s | [view]({s['log_file']}) |\n"
        )

    if warn_count > 0 or skip_count > 0 or global_warnings:
        handle.write("\n## Warnings & Skips\n\n")
        for s in scripts:
            if s["status"] in ["warn", "skip"]:
                handle.write(f"- **{s['name']}**: {s['note'] or s['error_summary']}\n")
        for w in global_warnings:
            handle.write(f"- {w['message']}\n")

    if error_count > 0:
        handle.write("\n## Failures\n\n")
        for s in scripts:
            if s["status"] == "error":
                handle.write(f"- **{s['name']}**: {s['error_summary']} (see `{s['log_file']}`)\n")

    handle.write("\n## How to reproduce\n\n")
    handle.write("```bash\n")
    handle.write("./scripts/validate-local-production-full.sh\n")
    handle.write("```\n\n")

    handle.write("## Useful commands\n\n")
    handle.write("- Check logs: `ls -R " + output_dir + "/logs/`\n")
    handle.write("- Tail all logs: `tail -f " + output_dir + "/logs/*.log`\n")
    handle.write("- Check services: `docker compose ps`\n\n")

    handle.write("## Out of scope\n\n")
    handle.write("- Real PSP (Stripe/MercadoPago) integration tests.\n")
    handle.write("- External DNS/SSL validation (handled by cloud provider).\n")
    handle.write("- GPU stress testing (requires dedicated environment).\n\n")

    handle.write("## Conclusion\n\n")
    if success:
        handle.write("The local production environment is healthy and ready for staging deployment.\n")
    else:
        handle.write("Critical failures were detected. Please resolve them before proceeding to deployment.\n")
PY

log_section "Validation Report"
log_info "Summary JSON: ${SUMMARY_JSON}"
log_info "Summary MD: ${SUMMARY_MD}"

if [[ "${critical_failures_count:-0}" -eq 0 ]]; then
    # We need to re-read the success status from the generated JSON to be sure
    if python3 - "${SUMMARY_JSON}" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    sys.exit(0 if json.load(handle)["validation_result"]["success"] else 1)
PY
    then
      log_ok "VALIDATION SUCCESSFUL"
      exit 0
    fi
fi

log_error "VALIDATION FAILED"
exit 1
