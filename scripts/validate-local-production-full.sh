#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/lib/validation-logging.sh"
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
CURL_MODE_FILE="$(mktemp)"
START_EPOCH="$(date +%s)"

mkdir -p "${LOGS_DIR}"
printf '[]\n' >"${RESULTS_FILE}"
printf '[]\n' >"${WARNINGS_FILE}"
printf '[]\n' >"${FAILURES_FILE}"
: >"${CURL_MODE_FILE}"

cleanup() {
  rm -f "${RESULTS_FILE}" "${WARNINGS_FILE}" "${FAILURES_FILE}" "${CURL_MODE_FILE}"
}
trap cleanup EXIT

resolve_validation_version() {
  if [[ -n "${VALIDATION_VERSION:-}" ]]; then
    printf '%s\n' "${VALIDATION_VERSION}"
    return
  fi

  if [[ -f "${ROOT_DIR}/VERSION" ]]; then
    local version_file
    version_file="$(tr -d '\r\n' < "${ROOT_DIR}/VERSION")"
    if [[ -n "${version_file}" ]]; then
      printf '%s\n' "${version_file}"
      return
    fi
  fi

  git -C "${ROOT_DIR}" describe --tags --always 2>/dev/null || printf '%s\n' "unknown"
}

VERSION="$(resolve_validation_version)"
GIT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo "unknown")"
GIT_BRANCH="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
GIT_TAG_BASE="$(git -C "${ROOT_DIR}" describe --tags --abbrev=0 2>/dev/null || echo "none")"

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_BASE_URL="${ADMIN_BASE_URL:-${BASE_URL}/admin}"
LM_STUDIO_BASE_URL="${LM_STUDIO_BASE_URL:-http://192.168.101.1:1234/v1}"
export VALIDATION_CURL_MODE_FILE="${CURL_MODE_FILE}"

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

if [[ "${VALIDATION_METADATA_ONLY:-false}" != "true" ]]; then
  run_validation "validate-localhost-mode.sh" "true"
  run_validation "validate-status-local.sh" "true"
  run_validation "validate-admin-lab-local.sh" "true"
  run_validation "validate-usable-chat-model-local.sh" "true"

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
else
  log_info "VALIDATION_METADATA_ONLY=true; skipping service validations"
fi

PYTEST_LOG_FILE="logs/pytest.log"
PYTEST_FULL_LOG_PATH="${OUTPUT_DIR}/${PYTEST_LOG_FILE}"
PYTEST_EXIT_CODE=0
if [[ "${VALIDATION_METADATA_ONLY:-false}" != "true" ]]; then
  log_step "Running repository pytest suite"
  RELEASE_PYTEST_ARGS=(
    tests/test_makefile_operator_commands.py
    tests/test_system_control_center_api.py
    tests/test_system_control_center_ui.py
    tests/test_system_control_center_sanitization.py
    tests/test_migrations_validation.py
    tests/test_alembic_heads.py
    tests/test_upgrade_migrations_safety.py
    tests/test_local_appliance_mode.py
    tests/test_local_appliance_security.py
    tests/test_local_appliance_release_guards.py
    tests/test_multitenant_isolation_full.py
    tests/test_multitenant_embeddings_responses.py
    tests/test_multitenant_tts.py
    tests/test_multitenant_billing_portal.py
    tests/test_multitenant_export_delete.py
    tests/test_abuse_protection_auth.py
    tests/test_abuse_protection_limits.py
    tests/test_abuse_protection_payloads.py
    tests/test_abuse_protection_multitenant.py
    tests/test_commercial_plans.py
    tests/test_plan_feature_gates.py
    tests/test_pricing_page_plans.py
    tests/test_client_portal_plan_limits.py
    tests/test_capability_matrix_docs.py
    tests/test_admin_capabilities_api.py
    tests/test_model_capabilities.py
    tests/test_models_capabilities_metadata.py
    tests/test_models_usable_chat_probe.py
    tests/test_integrations_docs.py
    tests/test_integration_examples_no_secrets.py
    -q
  )
  if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    if (
      cd "${ROOT_DIR}" || exit 1
      .venv/bin/python -m pytest "${RELEASE_PYTEST_ARGS[@]}"
    ) >"${PYTEST_FULL_LOG_PATH}" 2>&1; then
      log_ok "pytest OK"
    else
      PYTEST_EXIT_CODE=$?
      log_error "pytest FAILED (exit ${PYTEST_EXIT_CODE})"
    fi
  else
    log_warn "Local virtualenv not found; falling back to control-plane container pytest"
    if dc exec -T control-plane sh -lc "cd /app && python -m pytest ${RELEASE_PYTEST_ARGS[*]}" >"${PYTEST_FULL_LOG_PATH}" 2>&1; then
      log_ok "pytest OK"
    else
      PYTEST_EXIT_CODE=$?
      log_error "pytest FAILED (exit ${PYTEST_EXIT_CODE})"
    fi
  fi
else
  printf 'metadata-only validation; pytest skipped\n' >"${PYTEST_FULL_LOG_PATH}"
fi

ORPHAN_ANALYSIS_JSON="$(python3 - "${ROOT_DIR}" "${STACK_ENV_FILE}" <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
env_file = Path(sys.argv[2])
env_path = env_file if env_file.is_absolute() else root / env_file
cmd = ["docker", "compose", "--env-file", str(env_path), "-f", str(root / "docker-compose.yml"), "ps", "--format", "json"]
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
services = []
for line in result.stdout.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        continue
    services.append(payload.get("Service"))

orphans = []
compose_profiles = {item.strip() for item in os.environ.get("COMPOSE_PROFILES", "").split(",") if item.strip()}
if "data-plane-mock" in services and "fallback-test" not in compose_profiles:
    orphans.append("data-plane-mock")

print(json.dumps({
    "detected": bool(orphans),
    "services": orphans,
    "active_services": [service for service in services if service],
}))
PY
)"
if [[ "$(python3 -c 'import json,sys; print("true" if json.loads(sys.stdin.read())["detected"] else "false")' <<<"${ORPHAN_ANALYSIS_JSON}")" == "true" ]]; then
  add_warning "orphan-like services detected: $(python3 -c 'import json,sys; print(",".join(json.loads(sys.stdin.read())["services"]))' <<<"${ORPHAN_ANALYSIS_JSON}")"
fi

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
  "${OUTPUT_DIR}" \
  "${PYTEST_FULL_LOG_PATH}" \
  "${PYTEST_EXIT_CODE}" \
  "${PYTEST_LOG_FILE}" \
  "${CURL_MODE_FILE}" \
  "${ORPHAN_ANALYSIS_JSON}" <<'PY'
import json
import re
import sys

(
    summary_json, summary_md, results_file, warnings_file, failures_file,
    version, git_commit, git_branch, git_tag_base,
    timestamp_start, timestamp_end, duration, base_url,
    localhost_mode, local_billing_mode, rag_enabled,
    lm_studio_configured, lm_studio_online, output_dir,
    pytest_log_path, pytest_exit_code, pytest_log_file, curl_mode_file,
    orphan_analysis_json,
) = sys.argv[1:25]

duration = int(duration)
localhost_mode = localhost_mode == "true"
local_billing_mode = local_billing_mode == "true"
rag_enabled = rag_enabled == "true"
lm_studio_configured = lm_studio_configured == "true"
pytest_exit_code = int(pytest_exit_code)

with open(results_file, "r", encoding="utf-8") as handle:
    scripts = json.load(handle)
with open(warnings_file, "r", encoding="utf-8") as handle:
    global_warnings = json.load(handle)
with open(failures_file, "r", encoding="utf-8") as handle:
    failures = json.load(handle)
with open(curl_mode_file, "r", encoding="utf-8") as handle:
    curl_modes = [line.strip() for line in handle if line.strip()]

pytest_output = ""
try:
    with open(pytest_log_path, "r", encoding="utf-8") as handle:
        pytest_output = handle.read()
except FileNotFoundError:
    pytest_output = ""

pytest_counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "total": 0}
for key in ("passed", "failed", "errors", "skipped"):
    match = re.search(rf"(\d+)\s+{key if key != 'errors' else 'error[s]?'}", pytest_output)
    if match:
        pytest_counts[key] = int(match.group(1))
pytest_counts["total"] = sum(pytest_counts.values())

orphan_analysis = json.loads(orphan_analysis_json)

ok_count = sum(1 for s in scripts if s["status"] == "ok")
warn_count = sum(1 for s in scripts if s["status"] == "warn")
skip_count = sum(1 for s in scripts if s["status"] == "skip")
error_count = sum(1 for s in scripts if s["status"] == "error")

critical_failures = [s for s in scripts if s["critical"] and s["status"] == "error"]
curl_mode = "container" if "container" in curl_modes else "host" if "host" in curl_modes else "unknown"
success = len(critical_failures) == 0 and pytest_counts["failed"] == 0 and pytest_counts["errors"] == 0 and pytest_exit_code == 0

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
    "curl_mode": curl_mode,
    "orphan_containers_detected": orphan_analysis["detected"],
    "orphan_services": orphan_analysis["services"],
    "active_services": orphan_analysis["active_services"],
    "pytest_total": pytest_counts["total"],
    "pytest_passed": pytest_counts["passed"],
    "pytest_failed": pytest_counts["failed"],
    "pytest_errors": pytest_counts["errors"],
    "pytest_skipped": pytest_counts["skipped"],
    "pytest": {
        "exit_code": pytest_exit_code,
        "log_file": pytest_log_file,
        **pytest_counts,
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
        "pytest_exit_code": pytest_exit_code,
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
    handle.write(f"- LM_STUDIO_ONLINE: `{lm_studio_online}`\n")
    handle.write(f"- curl_mode: `{curl_mode}`\n")
    handle.write(f"- orphan_containers_detected: `{orphan_analysis['detected']}`\n\n")

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

    handle.write("\n## Test Suite\n\n")
    handle.write(f"- pytest exit code: `{pytest_exit_code}`\n")
    handle.write(f"- total: `{pytest_counts['total']}`\n")
    handle.write(f"- passed: `{pytest_counts['passed']}`\n")
    handle.write(f"- failed: `{pytest_counts['failed']}`\n")
    handle.write(f"- errors: `{pytest_counts['errors']}`\n")
    handle.write(f"- skipped: `{pytest_counts['skipped']}`\n")
    handle.write(f"- log: [view]({pytest_log_file})\n")

    if orphan_analysis["services"]:
        handle.write("\n## Container Warnings\n\n")
        for service in orphan_analysis["services"]:
            handle.write(f"- Unexpected active service: `{service}`\n")

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

log_step "Redacting sensitive tokens from artifacts"
"${SCRIPT_DIR}/redact-local-sensitive-artifacts.sh" --path "${OUTPUT_DIR}" --in-place

log_section "Validation Report"
log_info "Summary JSON: ${SUMMARY_JSON}"
log_info "Summary MD: ${SUMMARY_MD}"

VALIDATION_STATUS=0
if python3 - "${SUMMARY_JSON}" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    sys.exit(0 if json.load(handle)["validation_result"]["success"] else 1)
PY
then
  operator_success "Validação de produção local concluída com sucesso!"
  log_ok "VALIDATION SUCCESSFUL"
  VALIDATION_STATUS=0
else
  operator_error "VALIDATION_FAILED" "A validação de produção local encontrou falhas críticas." "Revise o arquivo ${SUMMARY_MD} para detalhes das falhas."
  log_error "VALIDATION FAILED"
  VALIDATION_STATUS=1
fi

add_next_step "Revise o relatório completo em: ${SUMMARY_MD}"
add_next_step "Verifique os logs detalhados em: ${LOGS_DIR}"
print_next_steps

exit ${VALIDATION_STATUS}
