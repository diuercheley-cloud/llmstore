#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"

cd "${ROOT_DIR}"

BUILD=true
SKIP_RAG=false
SKIP_LMSTUDIO=false
RESET_FIRST=false
KEEP_DATA=false
BASE_URL=""
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
ARTIFACT_DIR="${ROOT_DIR}/artifacts/local-demo/${TIMESTAMP}"

show_help() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --no-build       Skip docker image build"
    echo "  --skip-rag       Skip RAG validation"
    echo "  --skip-lmstudio  Skip LM Studio validation"
    echo "  --reset-first    Reset demo data before starting"
    echo "  --keep-data      Keep existing local data when not resetting first"
    echo "  --base-url URL   Override default base URL"
    echo "  --help           Show this help"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-build) BUILD=false; shift ;;
        --skip-rag) SKIP_RAG=true; shift ;;
        --skip-lmstudio) SKIP_LMSTUDIO=true; shift ;;
        --reset-first) RESET_FIRST=true; shift ;;
        --keep-data) KEEP_DATA=true; shift ;;
        --base-url)
            [[ $# -ge 2 ]] || { echo "Missing value for --base-url"; exit 1; }
            BASE_URL="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            show_help
            exit 1
            ;;
    esac
done

mkdir -p "${ARTIFACT_DIR}"

STACK_ENV_FILE="$(resolve_stack_env_file)"
if [[ "${STACK_ENV_FILE}" = /* ]]; then
    STACK_ENV_PATH="${STACK_ENV_FILE}"
else
    STACK_ENV_PATH="${ROOT_DIR}/${STACK_ENV_FILE}"
fi

if [[ ! -f "${STACK_ENV_PATH}" ]]; then
    cp "${ROOT_DIR}/.env.example" "${STACK_ENV_PATH}"
    echo "${STACK_ENV_FILE} created from .env.example; review tokens, passwords and ports before use."
fi

ensure_env_value() {
    local key="$1"
    local value="$2"
    local env_path="$3"

    if grep -qE "^${key}=" "${env_path}"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "${env_path}"
    else
        printf '\n%s=%s\n' "${key}" "${value}" >>"${env_path}"
    fi
}

ensure_env_value "DEMO_MODE" "true" "${STACK_ENV_PATH}"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"

declare -A STEPS_STATUS

run_step() {
    local name="$1"
    local cmd="$2"
    local log_file="${ARTIFACT_DIR}/${name}.log"

    echo "Running step: ${name}..."
    echo "Command: ${cmd}" >"${log_file}"
    if eval "${cmd}" >>"${log_file}" 2>&1; then
        echo "OK"
        STEPS_STATUS["${name}"]="OK"
        return 0
    fi

    echo "FAILED (see ${log_file})"
    STEPS_STATUS["${name}"]="ERROR"
    return 1
}

skip_step() {
    local name="$1"
    local reason="$2"
    local log_file="${ARTIFACT_DIR}/${name}.log"

    printf 'Skipped: %s\n' "${reason}" >"${log_file}"
    echo "Skipping step: ${name} (${reason})"
    STEPS_STATUS["${name}"]="SKIP"
}

run_health_check_attempt() {
    local name="$1"
    local log_file="${ARTIFACT_DIR}/${name}.log"

    echo "Running step: ${name}..."
    echo "Command: ./scripts/dev/test-health.sh" >"${log_file}"
    if ./scripts/dev/test-health.sh >>"${log_file}" 2>&1; then
        echo "OK"
        STEPS_STATUS["${name}"]="OK"
        return 0
    fi

    echo "Not ready yet (see ${log_file})"
    STEPS_STATUS["${name}"]="RETRY"
    return 1
}

echo "--- Local Demo Full Preparation and Validation ---"
echo "Artifacts will be saved in: ${ARTIFACT_DIR}"

if [[ "${RESET_FIRST}" == "true" ]]; then
    run_step "reset" "./scripts/dev/reset-demo-local.sh --yes" || true
elif [[ "${KEEP_DATA}" == "true" ]]; then
    skip_step "reset" "--keep-data requested"
else
    skip_step "reset" "no reset requested"
fi

COMPOSE_ARGS=(up -d --remove-orphans)
if [[ "${BUILD}" == "true" ]]; then
    COMPOSE_ARGS+=(--build)
else
    COMPOSE_ARGS+=(--no-build)
fi
run_step "docker-up" "dc ${COMPOSE_ARGS[*]}"

echo "Waiting for services to be healthy (timeout 60s)..."
MAX_RETRIES=12
RETRY_COUNT=0
HEALTHY=false
while [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; do
    if run_health_check_attempt "health-check-try-${RETRY_COUNT}"; then
        HEALTHY=true
        cp "${ARTIFACT_DIR}/health-check-try-${RETRY_COUNT}.log" "${ARTIFACT_DIR}/health-check.log"
        STEPS_STATUS["health-check"]="OK"
        break
    fi
    echo "Services not ready yet, retrying in 5s..."
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [[ "${HEALTHY}" == "false" ]]; then
    STEPS_STATUS["health-check"]="ERROR"
    echo "ERROR: Services failed to become healthy within 60s."
    exit 1
fi

run_step "seed-data" "./scripts/dev/seed-demo-local.sh"

run_step "validate-local" "./scripts/validators/validate-demo-local.sh" || true
run_step "validate-portal" "./scripts/validators/validate-demo-client-portal.sh" || true
run_step "validate-admin" "./scripts/validators/validate-demo-admin-dashboard.sh" || true
run_step "validate-examples" "./scripts/validators/validate-examples-local.sh" || true

if [[ "${SKIP_LMSTUDIO}" == "true" ]]; then
    skip_step "validate-lmstudio" "--skip-lmstudio requested"
else
    run_step "validate-lmstudio" "CONTROL_PLANE_URL=\"${BASE_URL}\" ./scripts/validators/validate-lmstudio-backend.sh" || true
fi

if [[ "${SKIP_RAG}" == "true" ]]; then
    skip_step "validate-rag" "--skip-rag requested"
else
    run_step "validate-rag" "RAG_ENABLED=true ./scripts/validators/validate-rag-local-multiclient.sh" || true
fi

run_step "validate-prod-full" "./scripts/validators/validate-local-production-full.sh" || true

cat >"${ARTIFACT_DIR}/demo-summary.json" <<EOF
{
  "timestamp": "${TIMESTAMP}",
  "branch": "${BRANCH}",
  "commit": "${COMMIT}",
  "base_url": "${BASE_URL}",
  "config": {
    "no_build": $([[ "${BUILD}" == "true" ]] && echo false || echo true),
    "skip_rag": ${SKIP_RAG},
    "skip_lmstudio": ${SKIP_LMSTUDIO},
    "reset_first": ${RESET_FIRST},
    "keep_data": ${KEEP_DATA}
  },
  "results": {
    "reset": "${STEPS_STATUS[reset]:-SKIP}",
    "docker_up": "${STEPS_STATUS[docker-up]:-UNKNOWN}",
    "health_check": "${STEPS_STATUS[health-check]:-UNKNOWN}",
    "seed_data": "${STEPS_STATUS[seed-data]:-UNKNOWN}",
    "validate_local": "${STEPS_STATUS[validate-local]:-UNKNOWN}",
    "validate_portal": "${STEPS_STATUS[validate-portal]:-UNKNOWN}",
    "validate_admin": "${STEPS_STATUS[validate-admin]:-UNKNOWN}",
    "validate_examples": "${STEPS_STATUS[validate-examples]:-UNKNOWN}",
    "validate_lmstudio": "${STEPS_STATUS[validate-lmstudio]:-UNKNOWN}",
    "validate_rag": "${STEPS_STATUS[validate-rag]:-UNKNOWN}",
    "validate_prod_full": "${STEPS_STATUS[validate-prod-full]:-UNKNOWN}"
  }
}
EOF

cat >"${ARTIFACT_DIR}/demo-summary.md" <<EOF
# Relatório de Demonstração Local - ${TIMESTAMP}

- **Data**: $(date)
- **Branch**: \`${BRANCH}\`
- **Commit**: \`${COMMIT}\`
- **Base URL**: ${BASE_URL}

## Status das Etapas
- **Reset**: ${STEPS_STATUS[reset]:-SKIP}
- **Docker Up**: ${STEPS_STATUS[docker-up]:-UNKNOWN}
- **Health Check**: ${STEPS_STATUS[health-check]:-UNKNOWN}
- **Seed Demo Data**: ${STEPS_STATUS[seed-data]:-UNKNOWN}
- **Validação Local**: ${STEPS_STATUS[validate-local]:-UNKNOWN}
- **Portal do Cliente**: ${STEPS_STATUS[validate-portal]:-UNKNOWN}
- **Admin Dashboard**: ${STEPS_STATUS[validate-admin]:-UNKNOWN}
- **Exemplos de API**: ${STEPS_STATUS[validate-examples]:-UNKNOWN}
- **LM Studio**: ${STEPS_STATUS[validate-lmstudio]:-UNKNOWN}
- **RAG**: ${STEPS_STATUS[validate-rag]:-UNKNOWN}
- **Produção Completa**: ${STEPS_STATUS[validate-prod-full]:-UNKNOWN}

## URLs Principais
- **Landing Page**: ${BASE_URL}/
- **Portal do Cliente**: ${BASE_URL}/client-portal
- **Admin Dashboard**: ${BASE_URL}/admin-dashboard
- **Admin Lab**: ${BASE_URL}/admin-lab

## Comandos Úteis
- Ver documentação: \`cat docs/LOCAL_DEMO_GUIDE.md\`
- Testar exemplos: \`./scripts/validators/validate-examples-local.sh\`
- Resetar ambiente: \`./scripts/dev/reset-demo-local.sh\`

## Limitações
- PSP Real: Não utilizado (faturamento manual/local).
- PIX Real: Não utilizado.
- HTTPS: Opcional em localhost.

---
Gerado automaticamente por \`scripts/dev/demo-full-local.sh\`
EOF

echo "Redacting demo artifacts..."
"${SCRIPT_DIR}/../backup/redact-local-sensitive-artifacts.sh" --path "${ARTIFACT_DIR}" --in-place

echo
echo "--- Relatório Gerado ---"
cat "${ARTIFACT_DIR}/demo-summary.md"

if [[ "${KEEP_DATA}" == "false" && "${STEPS_STATUS[validate-local]:-ERROR}" == "OK" ]]; then
    echo
    echo "Validation passed. Run ./scripts/dev/reset-demo-local.sh if you want to clean up."
fi

for step in "${!STEPS_STATUS[@]}"; do
    if [[ "${step}" == health-check-try-* && "${STEPS_STATUS[health-check]:-ERROR}" == "OK" ]]; then
        continue
    fi
    if [[ "${STEPS_STATUS[${step}]}" == "ERROR" ]]; then
        exit 1
    fi
done

exit 0
