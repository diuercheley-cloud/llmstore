#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env
cd "${ROOT_DIR}"

STRICT_RAG=false
usage() {
  cat <<'EOF'
Uso: ./scripts/dev/dr-test-local.sh [--strict-rag]

Variaveis:
  RAG_INDEX_TIMEOUT_SECONDS   Tempo maximo para aguardar indexacao RAG (padrao: 120)
  DR_HOST_PORT                Porta host manual para o control-plane temporario
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict-rag)
      STRICT_RAG=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[dr-test-local][error] argumento inesperado: $1" >&2
      exit 1
      ;;
  esac
  shift
done

BACKUP_ROOT="${ROOT_DIR}/artifacts/backups-local"
REPORT_ROOT="${ROOT_DIR}/artifacts/dr-tests"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
DR_PROJECT_NAME="llmstackdr$(printf '%s' "${TIMESTAMP}" | tr '[:upper:]' '[:lower:]')"
POSTGRES_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
REDIS_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
RAG_INDEX_TIMEOUT_SECONDS="${RAG_INDEX_TIMEOUT_SECONDS:-120}"
DR_HOST_PORT="${DR_HOST_PORT:-}"
PORT_SELECTION_MODE="auto"
PORT_VALIDATION_STATUS="not_run"
PORT_VALIDATION_ERROR=""
if [[ "${STACK_ENV_FILE}" = /* ]]; then
  STACK_ENV_PATH="${STACK_ENV_FILE}"
else
  STACK_ENV_PATH="${ROOT_DIR}/${STACK_ENV_FILE}"
fi

TEMP_ENV_FILE="$(mktemp "/tmp/llmstack-dr-local-${TIMESTAMP}-XXXXXX.env")"
TEMP_OVERRIDE_FILE="$(mktemp "/tmp/llmstack-dr-local-${TIMESTAMP}-XXXXXX.override.yml")"
REPORT_DIR="${REPORT_ROOT}/${TIMESTAMP}"
mkdir -p "${REPORT_DIR}"

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FINISHED_AT=""
BASE_URL=""
BACKUP_DIR=""
RESTORE_COMMAND=""
CLIENT_ID=""
API_KEY=""
API_KEY_MASKED=""
API_KEY_ID=""
MODEL_NAME=""
INVOICE_ID=""
RAG_DOC_ID=""
RAG_READY_BEFORE_BACKUP=false
RAG_READY_AFTER_RESTORE=false
RAG_INDEXING_STATUS="not_started"
RAG_VALIDATION_MODE="persistence_only"
RAG_FILE_RESTORE_STATUS="not_checked"
RAG_QUERY_VALIDATION_STATUS="not_checked"
CLIENT_VALIDATION_STATUS="not_run"
API_KEY_VALIDATION_STATUS="not_run"
INFERENCE_VALIDATION_STATUS="not_run"
INVOICE_VALIDATION_STATUS="not_run"
DR_RESULT="failed"

RAG_STORAGE_DIR_HOST=""
RAG_STORAGE_DIR_CONTAINER=""
RAG_UPLOAD_NAME="dr-rag.txt"
RAG_QUERY_PROBE="Qual e o numero de invoice no documento?"
RAG_QUERY_EXPECTED_TOKEN="DR-LOCAL-2026-0001"

cleanup() {
  local status=$?
  FINISHED_AT="${FINISHED_AT:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  write_summary || true
  docker compose -p "${DR_PROJECT_NAME}" \
    --env-file "${TEMP_ENV_FILE}" \
    -f "${ROOT_DIR}/docker-compose.yml" \
    -f "${TEMP_OVERRIDE_FILE}" \
    down -v >/dev/null 2>&1 || true
  rm -f "${TEMP_ENV_FILE}" "${TEMP_OVERRIDE_FILE}"
  exit "${status}"
}
trap cleanup EXIT

log() {
  printf '[dr-test-local] %s\n' "$*"
}

port_owner_diagnostics() {
  local port="$1"
  {
    printf '[dr-test-local][diagnostic] port=%s\n' "${port}"
    if command -v ss >/dev/null 2>&1; then
      ss -ltnp 2>/dev/null | grep -E ":${port}[[:space:]]" || true
    elif command -v lsof >/dev/null 2>&1; then
      lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
    elif command -v netstat >/dev/null 2>&1; then
      netstat -ltnp 2>/dev/null | grep -E ":${port}[[:space:]]" || true
    fi
    docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}' 2>/dev/null || true
    printf '[dr-test-local][diagnostic] investigate: docker ps --format '\''table {{.Names}}\\t{{.Ports}}\\t{{.Status}}'\''\n'
    printf '[dr-test-local][diagnostic] investigate: ss -ltnp | grep :%s\n' "${port}"
  } >&2
}

is_port_free() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ! ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "(:|\\])${port}$"
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    ! lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return
  fi
  if command -v netstat >/dev/null 2>&1; then
    ! netstat -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "(:|\\])${port}$"
    return
  fi
  python3 - "${port}" <<'PY'
import socket
import sys

port = int(sys.argv[1])
for host in ("127.0.0.1", "0.0.0.0"):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError:
        raise SystemExit(1)
    finally:
        sock.close()
raise SystemExit(0)
PY
}

find_free_port() {
  local start="${1:-18081}"
  local end="${2:-18199}"
  local port
  for port in $(seq "${start}" "${end}"); do
    if is_port_free "${port}"; then
      printf '%s\n' "${port}"
      return 0
    fi
  done
  return 1
}

assert_port_free() {
  local port="$1"
  if is_port_free "${port}"; then
    PORT_VALIDATION_STATUS="ok"
    PORT_VALIDATION_ERROR=""
    return 0
  fi
  PORT_VALIDATION_STATUS="failed"
  PORT_VALIDATION_ERROR="port_allocated"
  port_owner_diagnostics "${port}"
  echo "[dr-test-local][error] DR_HOST_PORT=${port} is already in use. Choose another port or stop the process using it." >&2
  return 1
}

fail() {
  echo "[dr-test-local][error] $*" >&2
  DR_RESULT="failed"
  exit 1
}

json_field() {
  local field="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('${field}', ''))"
}

json_required_field() {
  local field="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=data['${field}']; print(value)"
}

mask_api_key() {
  local key="$1"
  if [[ -z "${key}" ]]; then
    printf '%s' ""
    return
  fi
  if [[ "${#key}" -le 8 ]]; then
    printf '%s' "${key}"
    return
  fi
  printf '%s...%s' "${key:0:10}" "${key: -3}"
}

wait_url() {
  local url="$1"
  local attempts="${2:-90}"
  for _ in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 3
  done
  return 1
}

wait_for_rag_ready() {
  local doc_id="$1"
  local timeout_seconds="$2"
  local elapsed=0
  local status=""
  while [[ "${elapsed}" -lt "${timeout_seconds}" ]]; do
    local response=""
    response="$(curl -fsS "${BASE_URL}/client/rag/documents/${doc_id}" -H "Authorization: Bearer ${API_KEY}" 2>/dev/null || true)"
    if [[ -z "${response}" ]]; then
      sleep 3
      elapsed=$((elapsed + 3))
      continue
    fi
    status="$(printf '%s' "${response}" | json_required_field status)"
    if [[ "${status}" == "ready" ]]; then
      RAG_READY_BEFORE_BACKUP=true
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done
  RAG_READY_BEFORE_BACKUP=false
  return 1
}

query_rag_answer() {
  local output_file="$1"
  local http_code
  http_code="$(curl -sS -o "${output_file}" -w '%{http_code}' "${RAG_QUERY_ENDPOINT}" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"${RAG_QUERY_PROBE}\",\"top_k\":3}" || printf '000')"
  printf '%s' "${http_code}"
}

get_rag_db_row() {
  local doc_id="$1"
  dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc \
    "SELECT status || '|' || storage_path || '|' || COALESCE(processed_at::text, '') || '|' || COALESCE(chunk_count::text, '') FROM rag_documents WHERE id = '${doc_id}' LIMIT 1;"
}

rag_path_to_host() {
  local storage_path="$1"
  python3 - "${ROOT_DIR}" "${storage_path}" <<'PY'
from pathlib import Path
import sys

from local_dr_backup import host_path_for_data_dir

root = Path(sys.argv[1])
storage_path = sys.argv[2]
resolved = host_path_for_data_dir(root, storage_path)
print(resolved if resolved is not None else "")
PY
}

write_summary() {
  mkdir -p "${REPORT_DIR}"
  cat > "${REPORT_DIR}/summary.txt" <<EOF
STARTED_AT=${STARTED_AT}
FINISHED_AT=${FINISHED_AT}
PROJECT_NAME=${DR_PROJECT_NAME}
BACKUP_DIR=${BACKUP_DIR}
RESTORE_COMMAND=${RESTORE_COMMAND}
CLIENT_VALIDATION_STATUS=${CLIENT_VALIDATION_STATUS}
API_KEY_VALIDATION_STATUS=${API_KEY_VALIDATION_STATUS}
INFERENCE_VALIDATION_STATUS=${INFERENCE_VALIDATION_STATUS}
INVOICE_VALIDATION_STATUS=${INVOICE_VALIDATION_STATUS}
RAG_DOCUMENT_ID=${RAG_DOC_ID}
RAG_INDEXING_STATUS=${RAG_INDEXING_STATUS}
RAG_FILE_RESTORE_STATUS=${RAG_FILE_RESTORE_STATUS}
RAG_QUERY_VALIDATION_STATUS=${RAG_QUERY_VALIDATION_STATUS}
RAG_VALIDATION_MODE=${RAG_VALIDATION_MODE}
DR_RESULT=${DR_RESULT}
API_KEY_MASKED=${API_KEY_MASKED}
RAG_INDEX_TIMEOUT_SECONDS=${RAG_INDEX_TIMEOUT_SECONDS}
DR_HOST_PORT=${DR_HOST_PORT}
BASE_URL=${BASE_URL}
PORT_SELECTION_MODE=${PORT_SELECTION_MODE}
PORT_VALIDATION_STATUS=${PORT_VALIDATION_STATUS}
PORT_VALIDATION_ERROR=${PORT_VALIDATION_ERROR}
EOF
}

docker compose -p "${DR_PROJECT_NAME}" \
  --env-file "${STACK_ENV_PATH}" \
  -f "${ROOT_DIR}/docker-compose.yml" \
  down -v --remove-orphans >/dev/null 2>&1 || true

if [[ -n "${DR_HOST_PORT}" ]]; then
  PORT_SELECTION_MODE="manual"
  if [[ ! "${DR_HOST_PORT}" =~ ^[0-9]+$ ]]; then
    PORT_VALIDATION_STATUS="failed"
    PORT_VALIDATION_ERROR="invalid_port"
    echo "[dr-test-local][error] DR_HOST_PORT=${DR_HOST_PORT} is not a valid TCP port." >&2
    exit 1
  fi
  assert_port_free "${DR_HOST_PORT}" || exit 1
else
  PORT_SELECTION_MODE="auto"
  DR_HOST_PORT="$(find_free_port 18081 18199)" || {
    PORT_VALIDATION_STATUS="failed"
    PORT_VALIDATION_ERROR="no_free_port"
    echo "[dr-test-local][error] no free DR host port found in range 18081-18199" >&2
    exit 1
  }
  assert_port_free "${DR_HOST_PORT}" || exit 1
fi
BASE_URL="http://127.0.0.1:${DR_HOST_PORT}"
RAG_QUERY_ENDPOINT="${BASE_URL}/client/rag/query"

cp "${STACK_ENV_PATH}" "${TEMP_ENV_FILE}"
chmod 600 "${TEMP_ENV_FILE}"

python3 - "${TEMP_ENV_FILE}" "${DR_HOST_PORT}" "${POSTGRES_PORT}" "${REDIS_PORT}" "${TIMESTAMP}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
updates = {
    "HOST_PORT": sys.argv[2],
    "POSTGRES_PORT": sys.argv[3],
    "REDIS_PORT": sys.argv[4],
    "PUBLIC_EXPOSURE": "false",
    "LOCALHOST_MODE": "true",
    "RAG_STORAGE_DIR": f"/data/rag_uploads-drtest-{sys.argv[5]}",
}
lines = path.read_text(encoding="utf-8").splitlines()
result: list[str] = []
seen: set[str] = set()
for line in lines:
    if "=" in line and not line.startswith("#"):
        key, _, _value = line.partition("=")
        if key in updates:
            result.append(f"{key}={updates[key]}")
            seen.add(key)
            continue
    result.append(line)
for key, value in updates.items():
    if key not in seen:
        result.append(f"{key}={value}")
path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY

cat > "${TEMP_OVERRIDE_FILE}" <<'EOF'
services:
  postgres:
    ports: !reset []
  redis:
    ports: !reset []
  data-plane-gemma:
    ports: !reset []
EOF

export COMPOSE_PROJECT_NAME="${DR_PROJECT_NAME}"
export ENV_FILE="${TEMP_ENV_FILE}"
export EXTRA_COMPOSE_FILES="${TEMP_OVERRIDE_FILE}"
init_stack_env

RAG_STORAGE_DIR_CONTAINER="$(python3 -c 'import os; print(os.environ.get("RAG_STORAGE_DIR", ""))')"
RAG_STORAGE_DIR_HOST="$(python3 - "${ROOT_DIR}" "${RAG_STORAGE_DIR_CONTAINER}" <<'PY'
from pathlib import Path
import sys

from local_dr_backup import host_path_for_data_dir

root = Path(sys.argv[1])
storage_dir = sys.argv[2]
resolved = host_path_for_data_dir(root, storage_dir)
print(resolved if resolved is not None else "")
PY
)"

log "subindo ambiente temporario"
dc up -d --build --remove-orphans >/dev/null

log "aguardando health"
wait_url "${BASE_URL}/health" || fail "health failed"
wait_url "${BASE_URL}/ready" || fail "ready failed"

log "criando cliente"
CLIENT_RESPONSE="$(curl -fsS "${BASE_URL}/admin/clients" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name":"dr-local-client","description":"DR local test client","rate_limit_per_minute":10,"daily_token_quota":50000,"weekly_token_quota":150000,"monthly_token_quota":250000,"max_context_tokens":4096,"max_output_tokens":1024,"metadata_json":"{\"dr_test\":true}"}')"
CLIENT_ID="$(printf '%s' "${CLIENT_RESPONSE}" | json_required_field id)"

log "criando api key"
API_KEY_RESPONSE="$(curl -fsS "${BASE_URL}/admin/api-keys" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\",\"name\":\"dr-local-key\"}")"
API_KEY="$(printf '%s' "${API_KEY_RESPONSE}" | json_required_field api_key)"
API_KEY_ID="$(printf '%s' "${API_KEY_RESPONSE}" | json_required_field id)"
API_KEY_MASKED="$(mask_api_key "${API_KEY}")"

log "validando inferencia"
MODEL_NAME="$(curl -fsS "${BASE_URL}/v1/models" -H "Authorization: Bearer ${API_KEY}" | python3 -c 'import json,sys; data=json.load(sys.stdin)["data"]; print(data[0]["id"])')"
INFERENCE_BODY_FILE="${REPORT_DIR}/inference-before.json"
INFERENCE_HTTP_CODE="$(curl -sS -o "${INFERENCE_BODY_FILE}" -w '%{http_code}' "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL_NAME}\",\"messages\":[{\"role\":\"user\",\"content\":\"Responda apenas com a palavra OK.\"}],\"max_tokens\":16,\"stream\":false}")"
if [[ "${INFERENCE_HTTP_CODE}" != "200" ]]; then
  dc logs --tail 120 control-plane > "${REPORT_DIR}/control-plane-before-failure.log" 2>&1 || true
  dc logs --tail 120 data-plane-gemma > "${REPORT_DIR}/data-plane-before-failure.log" 2>&1 || true
  INFERENCE_VALIDATION_STATUS="failed_http_${INFERENCE_HTTP_CODE}"
  fail "inference failed with http ${INFERENCE_HTTP_CODE}"
fi
INFERENCE_VALIDATION_STATUS="success"

RAG_ENABLED="${RAG_ENABLED:-true}"
if [[ "${RAG_ENABLED}" == "true" || "${RAG_ENABLED}" == "True" ]]; then
  log "criando documento rag"
  RAG_FILE="${REPORT_DIR}/${RAG_UPLOAD_NAME}"
  cat > "${RAG_FILE}" <<'EOF'
Este documento de teste contem o numero de invoice DR-LOCAL-2026-0001.
EOF
  RAG_UPLOAD_RESPONSE="$(curl -fsS "${BASE_URL}/client/rag/documents" \
    -H "Authorization: Bearer ${API_KEY}" \
    -F "file=@${RAG_FILE}")"
  RAG_DOC_ID="$(printf '%s' "${RAG_UPLOAD_RESPONSE}" | json_required_field id)"
  if wait_for_rag_ready "${RAG_DOC_ID}" "${RAG_INDEX_TIMEOUT_SECONDS}"; then
    RAG_INDEXING_STATUS="ready"
    if [[ "${STRICT_RAG}" == "true" ]]; then
      RAG_VALIDATION_MODE="strict"
    else
      RAG_VALIDATION_MODE="semantic"
    fi
  else
    if [[ "${STRICT_RAG}" == "true" ]]; then
      RAG_INDEXING_STATUS="failed_timeout"
      RAG_VALIDATION_MODE="strict"
      RAG_QUERY_VALIDATION_STATUS="skipped_not_ready"
      DR_RESULT="failed"
      fail "rag document ${RAG_DOC_ID} did not become ready within ${RAG_INDEX_TIMEOUT_SECONDS}s"
    fi
    RAG_INDEXING_STATUS="not_ready"
    RAG_VALIDATION_MODE="persistence_only"
    RAG_QUERY_VALIDATION_STATUS="skipped_not_ready"
    DR_RESULT="success_with_rag_warning"
  fi
fi

log "gerando invoice local"
INVOICE_RESPONSE="$(curl -fsS "${BASE_URL}/admin/billing/invoices/generate" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\",\"due_in_days\":7,\"payment_method\":\"manual_pix\",\"payment_instructions\":\"dr-local\"}")"
INVOICE_ID="$(printf '%s' "${INVOICE_RESPONSE}" | python3 -c 'import json,sys; payload=json.load(sys.stdin); rows=payload.get("created") or payload.get("updated"); print(rows[0]["id"])')"
curl -fsS "${BASE_URL}/admin/billing/invoices/${INVOICE_ID}/mark-paid" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d '{"payment_method":"manual_pix","payment_reference":"dr-local","note":"dr-local payment"}' >/dev/null
INVOICE_VALIDATION_STATUS="success"

log "fazendo backup local"
BACKUP_OUTPUT="$("${SCRIPT_DIR}/../backup/backup-local.sh" --include-rag-files)"
printf '%s\n' "${BACKUP_OUTPUT}" > "${REPORT_DIR}/backup.log"
BACKUP_DIR="$(printf '%s\n' "${BACKUP_OUTPUT}" | awk -F= '/^\[backup-local\] dir=/{print $2}' | tail -n1)"
if [[ -z "${BACKUP_DIR}" || ! -d "${BACKUP_DIR}" ]]; then
  fail "backup directory not found in output"
fi

log "destruindo ambiente local de teste"
if [[ -n "${RAG_STORAGE_DIR_CONTAINER}" ]]; then
  dc exec -T control-plane sh -c "rm -rf '${RAG_STORAGE_DIR_CONTAINER}' && mkdir -p '${RAG_STORAGE_DIR_CONTAINER}'" >/dev/null 2>&1 || true
fi
dc down -v >/dev/null

RESTORE_COMMAND="${SCRIPT_DIR}/../backup/restore-local.sh --yes --force-rag-overwrite ${BACKUP_DIR}"
log "restaurando backup"
"${SCRIPT_DIR}/../backup/restore-local.sh" --yes --force-rag-overwrite "${BACKUP_DIR}" > "${REPORT_DIR}/restore.log"

log "subindo control plane para validacao"
dc up -d data-plane-gemma control-plane control-plane-worker rag-worker >/dev/null
wait_url "${BASE_URL}/health" || fail "health after restore failed"
wait_url "${BASE_URL}/ready" || fail "ready after restore failed"

log "validando cliente e api key apos restore"
if curl -fsS "${BASE_URL}/portal/me" -H "Authorization: Bearer ${API_KEY}" > "${REPORT_DIR}/portal-me-after.json"; then
  CLIENT_VALIDATION_STATUS="success"
  API_KEY_VALIDATION_STATUS="success"
else
  CLIENT_VALIDATION_STATUS="failed"
  API_KEY_VALIDATION_STATUS="failed"
  fail "client/api key validation failed after restore"
fi

if ! curl -fsS "${BASE_URL}/v1/models" -H "Authorization: Bearer ${API_KEY}" > "${REPORT_DIR}/models-after.json"; then
  fail "model list validation failed after restore"
fi
if ! curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL_NAME}\",\"messages\":[{\"role\":\"user\",\"content\":\"Responda apenas com a palavra RESTORED.\"}],\"max_tokens\":16,\"stream\":false}" > "${REPORT_DIR}/inference-after.json"; then
  fail "inference validation failed after restore"
fi
INFERENCE_VALIDATION_STATUS="success"

if [[ -n "${INVOICE_ID}" ]]; then
  log "validando invoice apos restore"
  curl -fsS "${BASE_URL}/portal/invoices" -H "Authorization: Bearer ${API_KEY}" > "${REPORT_DIR}/portal-invoices-after.json"
  curl -fsS "${BASE_URL}/admin/billing/invoices" -H "X-Admin-Token: ${ADMIN_TOKEN}" > "${REPORT_DIR}/admin-invoices-after.json"
  INVOICE_VALIDATION_STATUS="success"
else
  INVOICE_VALIDATION_STATUS="failed"
  fail "invoice id missing"
fi

if [[ -n "${RAG_DOC_ID}" ]]; then
  log "validando rag apos restore"
  RAG_DB_ROW="$(get_rag_db_row "${RAG_DOC_ID}")"
  if [[ -z "${RAG_DB_ROW}" ]]; then
    RAG_FILE_RESTORE_STATUS="missing_record"
    fail "rag document record missing after restore"
  fi

  RAG_DB_STATUS="${RAG_DB_ROW%%|*}"
  RAG_DB_REMAINDER="${RAG_DB_ROW#*|}"
  RAG_STORAGE_PATH="${RAG_DB_REMAINDER%%|*}"
  RAG_STORAGE_HOST_PATH="$(rag_path_to_host "${RAG_STORAGE_PATH}")"
  if [[ -z "${RAG_STORAGE_HOST_PATH}" || ! -f "${RAG_STORAGE_HOST_PATH}" ]]; then
    RAG_FILE_RESTORE_STATUS="missing_file"
    fail "rag file missing after restore: ${RAG_STORAGE_PATH}"
  fi
  RAG_FILE_RESTORE_STATUS="restored"

  if [[ "${RAG_INDEXING_STATUS}" == "ready" || "${RAG_READY_BEFORE_BACKUP}" == "true" ]]; then
    if [[ "${RAG_DB_STATUS}" != "ready" ]]; then
      fail "rag document was indexed before backup but is not ready after restore"
    fi
    RAG_READY_AFTER_RESTORE=true
  fi

  if [[ "${RAG_DB_STATUS}" == "ready" ]]; then
    RAG_READY_AFTER_RESTORE=true
  fi

  if [[ "${RAG_READY_AFTER_RESTORE}" == "true" ]]; then
    RAG_QUERY_HTTP_CODE="$(query_rag_answer "${REPORT_DIR}/rag-query-after.json")"
    if [[ "${RAG_QUERY_HTTP_CODE}" == "200" ]]; then
      if python3 - "${REPORT_DIR}/rag-query-after.json" "${RAG_QUERY_EXPECTED_TOKEN}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
needle = sys.argv[2]
answer = payload.get("answer", "")
sources = payload.get("sources", [])
if needle in answer:
    raise SystemExit(0)
for source in sources:
    if needle in str(source.get("text", "")):
        raise SystemExit(0)
raise SystemExit(1)
PY
      then
        RAG_QUERY_VALIDATION_STATUS="success"
      else
        RAG_QUERY_VALIDATION_STATUS="failed_content_mismatch"
        fail "rag query response did not contain expected content"
      fi
    elif [[ "${RAG_QUERY_HTTP_CODE}" == "404" || "${RAG_QUERY_HTTP_CODE}" == "405" || "${RAG_QUERY_HTTP_CODE}" == "501" ]]; then
      RAG_QUERY_VALIDATION_STATUS="skipped_no_endpoint"
    else
      RAG_QUERY_VALIDATION_STATUS="failed_http_${RAG_QUERY_HTTP_CODE}"
      fail "rag query failed with http ${RAG_QUERY_HTTP_CODE}"
    fi
  fi
else
  RAG_FILE_RESTORE_STATUS="skipped_no_document"
fi

if [[ "${RAG_INDEXING_STATUS}" == "not_ready" && "${STRICT_RAG}" != "true" ]]; then
  DR_RESULT="success_with_rag_warning"
elif [[ "${RAG_INDEXING_STATUS}" == "ready" ]]; then
  DR_RESULT="success"
elif [[ "${DR_RESULT}" == "failed" ]]; then
  DR_RESULT="failed"
else
  DR_RESULT="success"
fi

FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_summary

log "encerrando ambiente temporario"
dc down -v >/dev/null
trap - EXIT
rm -f "${TEMP_ENV_FILE}" "${TEMP_OVERRIDE_FILE}"

printf '[dr-test-local] success\n'
printf '[dr-test-local] backup_dir=%s\n' "${BACKUP_DIR}"
printf '[dr-test-local] restore_command=%s\n' "${RESTORE_COMMAND}"
printf '[dr-test-local] report=%s\n' "${REPORT_DIR}/summary.txt"
