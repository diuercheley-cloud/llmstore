#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

MODE="quick"
RUN_PYTEST="auto"
RUN_E2E="auto"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --quick)
      MODE="quick"
      shift
      ;;
    --full)
      MODE="full"
      shift
      ;;
    --with-pytest)
      RUN_PYTEST="yes"
      shift
      ;;
    --skip-pytest)
      RUN_PYTEST="no"
      shift
      ;;
    --with-e2e)
      RUN_E2E="yes"
      shift
      ;;
    --skip-e2e)
      RUN_E2E="no"
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso: ./scripts/validate-system-health.sh [opcoes]

Opcoes:
  --quick              Roda validacao operacional curta.
  --full               Roda validacao completa, incluindo pytest e validate-e2e.
  --mode quick|full    Define o modo explicitamente.
  --with-pytest        Forca execucao do pytest.
  --skip-pytest        Pula pytest.
  --with-e2e           Forca execucao do validate-e2e.
  --skip-e2e           Pula validate-e2e.
  -h, --help           Mostra esta ajuda.
EOF
      exit 0
      ;;
    *)
      printf '[health][error] opcao invalida: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

if [[ "${MODE}" != "quick" && "${MODE}" != "full" ]]; then
  printf '[health][error] modo invalido: %s\n' "${MODE}" >&2
  exit 2
fi

if [[ "${RUN_PYTEST}" == "auto" ]]; then
  [[ "${MODE}" == "full" ]] && RUN_PYTEST="yes" || RUN_PYTEST="no"
fi
if [[ "${RUN_E2E}" == "auto" ]]; then
  [[ "${MODE}" == "full" ]] && RUN_E2E="yes" || RUN_E2E="no"
fi

init_stack_env

ARTIFACTS_DIR="${ROOT_DIR}/artifacts/system-health/$(date +%Y%m%dT%H%M%S)"
mkdir -p "${ARTIFACTS_DIR}"
BASE_URL="${BASE_URL:-$(default_base_url)}"

log() {
  printf '[health] %s\n' "$*"
}

fail() {
  local message="$1"
  local service="${2:-}"
  printf '[health][error] %s\n' "${message}" >&2
  if [[ -n "${service}" ]]; then
    dc logs --tail=120 "${service}" >"${ARTIFACTS_DIR}/${service}.tail.log" 2>&1 || true
    printf '[health][error] service=%s log=%s\n' "${service}" "${ARTIFACTS_DIR}/${service}.tail.log" >&2
    if grep -q 'password authentication failed' "${ARTIFACTS_DIR}/${service}.tail.log" 2>/dev/null; then
      printf '[health][error] hint=postgres volume provavelmente foi inicializado com outra senha; alinhe %s com o volume atual ou recrie o volume de dados\n' "${STACK_ENV_FILE}" >&2
    fi
  fi
  exit 1
}

json_assert() {
  local file="$1"
  local expr="$2"
  local message="$3"
  python3 - "$file" "$expr" "$message" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expr = sys.argv[2]
message = sys.argv[3]
data = json.loads(path.read_text())
if not eval(expr, {"data": data}):
    raise SystemExit(message)
PY
}

wait_http_json() {
  local url="$1"
  local output="$2"
  local attempts="${3:-60}"
  local sleep_seconds="${4:-2}"
  local status_code
  for _ in $(seq 1 "${attempts}"); do
    status_code="$(curl_base_url "${url}" -sS -o "${output}" -w '%{http_code}' || true)"
    if [[ "${status_code}" == "200" ]]; then
      return 0
    fi
    sleep "${sleep_seconds}"
  done
  return 1
}

wait_compose_services() {
  local attempts="${1:-60}"
  local sleep_seconds="${2:-2}"
  shift 2 || true
  local expected_services=("$@")
  if [[ ${#expected_services[@]} -eq 0 ]]; then
    expected_services=(
      postgres
      redis
      data-plane-gemma
      control-plane
      control-plane-worker
    )
  fi
  if [[ "${STACK_MODE:-local}" == "prod" ]]; then
    expected_services+=(caddy)
  fi
  if [[ "${BONSAI_ENABLED:-false}" == "true" ]]; then
    expected_services+=(data-plane-bonsai)
  fi
  local snapshot_file
  snapshot_file="${ARTIFACTS_DIR}/compose-ps-wait.jsonl"

  for _ in $(seq 1 "${attempts}"); do
    dc ps --format json >"${snapshot_file}" 2>/dev/null || true
    if python3 - "${snapshot_file}" "${expected_services[@]}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected = sys.argv[2:]
rows = []
for line in path.read_text().splitlines():
    line = line.strip()
    if not line:
        continue
    rows.append(json.loads(line))

by_service = {row.get("Service"): row for row in rows}
ok = True
for service in expected:
    row = by_service.get(service)
    if row is None:
        ok = False
        continue
    state = (row.get("State") or "").lower()
    health = (row.get("Health") or "").lower()
    if state != "running":
        ok = False
        continue
    if service in {"postgres", "redis", "data-plane-gemma"} and health not in {"", "healthy"}:
        ok = False
        continue

raise SystemExit(0 if ok else 1)
PY
    then
      return 0
    fi
    sleep "${sleep_seconds}"
  done

  printf '[health][debug] compose status snapshot:\n' >&2
  cat "${snapshot_file}" >&2 || true
  return 1
}

check_postgres_auth() {
  local output_file="${ARTIFACTS_DIR}/postgres-auth.txt"
  if dc exec -T postgres sh -lc "PGPASSWORD='${POSTGRES_PASSWORD}' psql -U '${POSTGRES_USER}' -d '${POSTGRES_DB}' -c 'select 1'" >"${output_file}" 2>&1; then
    return 0
  fi
  printf '[health][error] falha de autenticacao no postgres com as credenciais atuais de %s\n' "${STACK_ENV_FILE}" >&2
  printf '[health][error] details=%s\n' "${output_file}" >&2
  if grep -qi 'password authentication failed' "${output_file}"; then
    printf '[health][error] hint=se o volume postgres_data e antigo, a senha gravada nele difere da senha atual do env; ajuste %s ou recrie o volume com: docker compose --env-file %s -f docker-compose.yml down -v\n' "${STACK_ENV_FILE}" "${STACK_ENV_FILE}" >&2
  fi
  return 1
}

ROOT_DIR_ESCAPED="${ROOT_DIR}"
cd "${ROOT_DIR_ESCAPED}"

log "modo=${MODE} base_url=${BASE_URL}"

log "checando docker e compose"
docker info >"${ARTIFACTS_DIR}/docker-info.txt" 2>&1 || true
dc ps >"${ARTIFACTS_DIR}/compose-ps.txt" 2>&1 || fail "docker compose ps falhou"

log "checando env e modelo"
[[ -f "${ROOT_DIR}/${STACK_ENV_FILE}" ]] || fail "env file ausente: ${STACK_ENV_FILE}"
env_model_file="$(awk -F= '/^MODEL_FILE=/{print $2}' "${ROOT_DIR}/${STACK_ENV_FILE}" | tail -n1)"
[[ -n "${env_model_file}" ]] || fail "MODEL_FILE ausente em ${STACK_ENV_FILE}"
[[ -f "${ROOT_DIR}/models/${env_model_file}" ]] || fail "model file nao encontrado: models/${env_model_file}"

log "subindo stack"
dc up -d --build >"${ARTIFACTS_DIR}/compose-up.log" 2>&1 || fail "docker compose up falhou"
dc ps >"${ARTIFACTS_DIR}/compose-ps-after-up.txt" 2>&1 || true
wait_compose_services 90 2 postgres redis data-plane-gemma || fail "infraestrutura base nao estabilizou apos o bootstrap" "postgres"
check_postgres_auth || exit 1
wait_compose_services 90 2 postgres redis data-plane-gemma control-plane control-plane-worker || fail "control-plane nao estabilizou apos a validacao do banco" "control-plane"

log "checando stack HTTP"
wait_http_json "${BASE_URL}/health" "${ARTIFACTS_DIR}/health.json" 60 2 || fail "/health nao respondeu 200" "control-plane"
wait_http_json "${BASE_URL}/ready" "${ARTIFACTS_DIR}/ready.json" 90 2 || fail "/ready nao respondeu 200" "control-plane"
curl_base_url "${BASE_URL}/metrics" -fsS >"${ARTIFACTS_DIR}/metrics.txt" || fail "/metrics falhou" "control-plane"
json_assert "${ARTIFACTS_DIR}/health.json" '"status" in data' "health sem campo status"
json_assert "${ARTIFACTS_DIR}/ready.json" '"status" in data' "ready sem campo status"

log "checando admin deep health"
curl_base_url "${BASE_URL}/admin/health/deep" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/admin-health-deep.json" || fail "admin deep health falhou" "control-plane"

log "emitindo API key de teste"
DEMO_CLIENT_ID="$(lookup_demo_client_id "${BASE_URL}" || true)"
[[ -n "${DEMO_CLIENT_ID}" ]] || fail "demo client nao encontrado" "control-plane"
API_KEY="${API_KEY:-$(issue_demo_api_key "${BASE_URL}" "system-health" || true)}"
[[ -n "${API_KEY}" ]] || fail "nao foi possivel emitir API key" "control-plane"
printf '%s\n' "${API_KEY}" >"${ARTIFACTS_DIR}/api-key.txt"

log "checando autenticacao e modelos"
curl_base_url "${BASE_URL}/v1/models" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  >"${ARTIFACTS_DIR}/models.json" || fail "models com API key falhou" "control-plane"
unauth_status="$(curl_base_url "${BASE_URL}/v1/models" -sS -o /dev/null -w '%{http_code}' || true)"
[[ "${unauth_status}" == "401" ]] || fail "models sem API key deveria retornar 401"
admin_unauth_status="$(curl_base_url "${BASE_URL}/admin/clients" -sS -o /dev/null -w '%{http_code}' || true)"
[[ "${admin_unauth_status}" == "401" ]] || fail "admin sem token deveria retornar 401"

log "limpando cache de respostas antes da validacao de inferencia"
curl_base_url "${BASE_URL}/admin/cache/responses" -fsS -X DELETE \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/cache-clear.json" || fail "cache clear falhou" "control-plane"

log "checando inferencia sincrona"
curl_base_url "${BASE_URL}/v1/chat/completions" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Responda com uma frase curta: o servidor esta funcional?"}],
    "max_tokens": 96,
    "stream": false,
    "include_reasoning": false
  }' >"${ARTIFACTS_DIR}/chat.json" || fail "chat sincrono falhou" "control-plane"
json_assert "${ARTIFACTS_DIR}/chat.json" 'bool(data["choices"][0]["message"]["content"].strip())' "chat retornou content vazio"

log "checando inferencia async"
curl_base_url "${BASE_URL}/v1/chat/completions/async" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Responda com uma frase curta: o worker async esta funcional?"}],
    "max_tokens": 96,
    "stream": false,
    "include_reasoning": false
  }' >"${ARTIFACTS_DIR}/async-create.json" || fail "async create falhou" "control-plane"
ASYNC_JOB_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "${ARTIFACTS_DIR}/async-create.json")"
ASYNC_STATUS=""
for _ in $(seq 1 45); do
  curl_base_url "${BASE_URL}/v1/jobs/${ASYNC_JOB_ID}" -fsS \
    -H "Authorization: Bearer ${API_KEY}" >"${ARTIFACTS_DIR}/async-status.json" || fail "async status falhou" "control-plane-worker"
  ASYNC_STATUS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "${ARTIFACTS_DIR}/async-status.json")"
  if [[ "${ASYNC_STATUS}" == "completed" ]]; then
    break
  fi
  if [[ "${ASYNC_STATUS}" == "failed" || "${ASYNC_STATUS}" == "cancelled" ]]; then
    fail "async terminou com status ${ASYNC_STATUS}" "control-plane-worker"
  fi
  sleep 2
done
[[ "${ASYNC_STATUS}" == "completed" ]] || fail "async nao completou a tempo" "control-plane-worker"

log "checando streaming"
curl_base_url "${BASE_URL}/v1/chat/completions" -N -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Conte de 1 a 5 em portugues."}],
    "max_tokens": 64,
    "stream": true,
    "include_reasoning": false
  }' >"${ARTIFACTS_DIR}/stream.txt" || fail "streaming falhou" "control-plane"
grep -q '^data:' "${ARTIFACTS_DIR}/stream.txt" || fail "streaming nao retornou eventos SSE"

log "checando billing e portal"
curl_base_url "${BASE_URL}/admin/billing/invoices" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/invoices.json" || fail "billing invoices falhou" "control-plane"
curl_base_url "${BASE_URL}/portal/me" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  >"${ARTIFACTS_DIR}/portal-me.json" || fail "portal me falhou" "control-plane"
json_assert "${ARTIFACTS_DIR}/portal-me.json" '"api_key" not in data and all("secret" not in k and "hash" not in k for k in data.keys())' "portal expos dados sensiveis"

if [[ "${RUN_PYTEST}" == "yes" ]]; then
  log "rodando pytest no container"
  dc exec -T control-plane pytest -q tests >"${ARTIFACTS_DIR}/pytest.txt" 2>&1 || fail "pytest falhou" "control-plane"
fi

if [[ "${RUN_E2E}" == "yes" ]]; then
  log "rodando validate-e2e"
  STACK_MODE="${STACK_MODE:-local}" ENV_FILE="${STACK_ENV_FILE}" BASE_URL="${BASE_URL}" \
    "${SCRIPT_DIR}/validate-e2e.sh" >"${ARTIFACTS_DIR}/validate-e2e.txt" 2>&1 || fail "validate-e2e falhou"
fi

printf '\n[health][summary] success\n'
printf '[health][summary] mode=%s\n' "${MODE}"
printf '[health][summary] artifacts=%s\n' "${ARTIFACTS_DIR}"
printf '[health][summary] endpoint=%s\n' "${BASE_URL}"
