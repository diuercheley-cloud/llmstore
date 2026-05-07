#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
cd "${ROOT_DIR}"

extract_summary_value() {
  local summary_file="$1"
  local key="$2"
  awk -F= -v key="${key}" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "${summary_file}"
}

free_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

latest_summary_file() {
  local report_root="${ROOT_DIR}/artifacts/dr-tests-local"
  local latest_dir
  latest_dir="$(ls -1 "${report_root}" 2>/dev/null | sort | tail -n1)"
  if [[ -n "${latest_dir}" && -f "${report_root}/${latest_dir}/summary.txt" ]]; then
    printf '%s\n' "${report_root}/${latest_dir}/summary.txt"
  fi
}

assert_summary_has() {
  local summary_file="$1"
  local key="$2"
  local expected="$3"
  local actual
  actual="$(extract_summary_value "${summary_file}" "${key}")"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "[test-dr-local-strict-rag][error] ${key} expected=${expected} actual=${actual}" >&2
    exit 1
  fi
}

run_and_check_default() {
  local output summary_dir summary_file
  local host_port
  host_port="$(free_port)"
  set +e
  output="$(HOST_PORT="${host_port}" RAG_INDEX_TIMEOUT_SECONDS=1 "${SCRIPT_DIR}/dr-test-local.sh" 2>&1)"
  local status=$?
  set -e
  printf '%s\n' "${output}"
  if [[ "${status}" -ne 0 ]]; then
    echo "[test-dr-local-strict-rag][error] default DR run failed unexpectedly" >&2
    exit 1
  fi
  summary_file="$(printf '%s\n' "${output}" | awk -F= '/^\[dr-test-local\] report=/{print $2}' | tail -n1)"
  if [[ -z "${summary_file}" || ! -f "${summary_file}" ]]; then
    echo "[test-dr-local-strict-rag][error] summary not found for default run" >&2
    exit 1
  fi
  summary_dir="$(dirname "${summary_file}")"
  assert_summary_has "${summary_file}" STARTED_AT "$(extract_summary_value "${summary_file}" STARTED_AT)"
  if [[ "$(extract_summary_value "${summary_file}" RAG_INDEXING_STATUS)" == "not_ready" ]]; then
    assert_summary_has "${summary_file}" RAG_VALIDATION_MODE persistence_only
    assert_summary_has "${summary_file}" DR_RESULT success_with_rag_warning
  else
    if [[ "$(extract_summary_value "${summary_file}" RAG_INDEXING_STATUS)" != "ready" ]]; then
      echo "[test-dr-local-strict-rag][error] unexpected default RAG_INDEXING_STATUS" >&2
      exit 1
    fi
    assert_summary_has "${summary_file}" RAG_VALIDATION_MODE semantic
    assert_summary_has "${summary_file}" DR_RESULT success
  fi
  printf '[test-dr-local-strict-rag] default_summary=%s\n' "${summary_file}"
  printf '[test-dr-local-strict-rag] default_report_dir=%s\n' "${summary_dir}"
}

run_and_check_strict() {
  local output summary_file status
  local host_port
  host_port="$(free_port)"
  set +e
  output="$(HOST_PORT="${host_port}" RAG_INDEX_TIMEOUT_SECONDS=1 "${SCRIPT_DIR}/dr-test-local.sh" --strict-rag 2>&1)"
  status=$?
  set -e
  printf '%s\n' "${output}"
  summary_file="$(printf '%s\n' "${output}" | awk -F= '/^\[dr-test-local\] report=/{print $2}' | tail -n1)"
  if [[ -z "${summary_file}" || ! -f "${summary_file}" ]]; then
    summary_file="$(latest_summary_file)"
  fi
  if [[ -z "${summary_file}" || ! -f "${summary_file}" ]]; then
    echo "[test-dr-local-strict-rag][error] summary not found for strict run" >&2
    exit 1
  fi
  if [[ "${status}" -eq 0 ]]; then
    assert_summary_has "${summary_file}" RAG_VALIDATION_MODE strict
    assert_summary_has "${summary_file}" DR_RESULT success
  else
    assert_summary_has "${summary_file}" RAG_INDEXING_STATUS failed_timeout
    assert_summary_has "${summary_file}" RAG_VALIDATION_MODE strict
    assert_summary_has "${summary_file}" DR_RESULT failed
  fi
  printf '[test-dr-local-strict-rag] strict_summary=%s\n' "${summary_file}"
  printf '[test-dr-local-strict-rag] strict_exit_code=%s\n' "${status}"
}

run_and_check_default
run_and_check_strict

printf '[test-dr-local-strict-rag] success\n'
