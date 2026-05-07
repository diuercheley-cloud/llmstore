#!/usr/bin/env bash
set -euo pipefail

# demo-full-local.sh
# Script único para preparar e validar uma demonstração local completa.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

# Default values
BUILD=true
SKIP_RAG=false
SKIP_LMSTUDIO=false
RESET_FIRST=false
KEEP_DATA=false
BASE_URL=""
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
ARTIFACTS_ROOT="${ROOT_DIR}/artifacts/local-demo"
ARTIFACTS_DIR="${ARTIFACTS_ROOT}/${TIMESTAMP}"

show_help() {
    echo "Uso: $0 [opções]"
    echo ""
    echo "Opções:"
    echo "  --no-build       Pula o build das imagens docker"
    echo "  --skip-rag       Pula validações de RAG"
    echo "  --skip-lmstudio  Pula validações de LMStudio"
    echo "  --reset-first    Executa down e limpa volumes antes de subir"
    echo "  --keep-data      Não limpa dados locais ao iniciar (se não usar --reset-first)"
    echo "  --base-url URL   Define a URL base da stack (padrão: detectada de .env)"
    echo "  --help           Mostra esta ajuda"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-build) BUILD=false; shift ;;
        --skip-rag) SKIP_RAG=true; shift ;;
        --skip-lmstudio) SKIP_LMSTUDIO=true; shift ;;
        --reset-first) RESET_FIRST=true; shift ;;
        --keep-data) KEEP_DATA=true; shift ;;
        --base-url) BASE_URL="$2"; shift 2 ;;
        --help) show_help; exit 0 ;;
        *) echo "Opção desconhecida: $1"; show_help; exit 1 ;;
    esac
done

mkdir -p "${ARTIFACTS_DIR}"

# Initialize environment
init_stack_env
BASE_URL="${BASE_URL:-$(default_base_url)}"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

# Status tracking
declare -A STEPS_STATUS
declare -A STEPS_LOGS

run_step() {
    local name="$1"
    local cmd="$2"
    local log_file="${ARTIFACTS_DIR}/${name}.log"
    STEPS_LOGS[$name]="${name}.log"
    
    echo ">>> Etapa: ${name}"
    # Use || true to prevent set -e from exiting the script
    if eval "${cmd}" > "${log_file}" 2>&1; then
        echo "OK"
        STEPS_STATUS[$name]="OK"
        return 0
    else
        echo "FALHA (ver ${log_file})"
        STEPS_STATUS[$name]="ERROR"
        return 0 # Return 0 to continue with next steps
    fi
}

skip_step() {
    local name="$1"
    echo ">>> Etapa: ${name} (PULADA)"
    STEPS_STATUS[$name]="SKIP"
}

# 1. Reset (opcional)
if [[ "${RESET_FIRST}" == "true" ]]; then
    run_step "reset" "${SCRIPT_DIR}/down.sh --volumes"
else
    skip_step "reset"
fi

# 2. Docker Compose Up
UP_CMD="${SCRIPT_DIR}/up.sh"
if [[ "${BUILD}" == "false" ]]; then
    export SKIP_BUILD=true
fi
run_step "docker-up" "${UP_CMD}"

# 3. Aguardar Health/Ready
echo ">>> Aguardando Stack ficar pronta em ${BASE_URL}..."
MAX_RETRIES=30
COUNT=0
while ! curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; do
    sleep 2
    COUNT=$((COUNT+1))
    if [[ $COUNT -ge $MAX_RETRIES ]]; then
        echo "ERRO: Stack não ficou pronta após $(($MAX_RETRIES*2)) segundos."
        STEPS_STATUS["wait-ready"]="ERROR"
        # Não saímos aqui para tentar gerar o relatório mesmo com falha
        break
    fi
done
if [[ "${STEPS_STATUS[wait-ready]:-}" != "ERROR" ]]; then
    STEPS_STATUS["wait-ready"]="OK"
    echo "OK"
fi

# 4. Seed Demo
run_step "seed-demo" "${SCRIPT_DIR}/seed-demo-local.sh"

# 5. Validações
run_step "validate-demo-local" "${SCRIPT_DIR}/validate-demo-local.sh"
run_step "validate-demo-client-portal" "${SCRIPT_DIR}/validate-demo-client-portal.sh"
run_step "validate-demo-admin-dashboard" "${SCRIPT_DIR}/validate-demo-admin-dashboard.sh"
run_step "validate-examples" "${SCRIPT_DIR}/validate-examples-local.sh"

if [[ "${SKIP_LMSTUDIO}" == "false" ]]; then
    run_step "validate-lmstudio" "CONTROL_PLANE_URL=\"${BASE_URL}\" ${SCRIPT_DIR}/validate-lmstudio-backend.sh"
else
    skip_step "validate-lmstudio"
fi

run_step "validate-full" "${SCRIPT_DIR}/validate-local-production-full.sh"

# Generate Reports
SUMMARY_JSON="${ARTIFACTS_DIR}/demo-summary.json"
SUMMARY_MD="${ARTIFACTS_DIR}/demo-summary.md"

# JSON Report
cat <<EOF > "${SUMMARY_JSON}"
{
  "timestamp": "${TIMESTAMP}",
  "branch": "${BRANCH}",
  "commit": "${COMMIT}",
  "base_url": "${BASE_URL}",
  "demo_client": "Cliente Demo Local",
  "steps": {
$(for key in "${!STEPS_STATUS[@]}"; do
    echo "    \"${key}\": \"${STEPS_STATUS[$key]}\","
done | sed '$s/,$//')
  },
  "safety": {
    "no_real_psp": true,
    "no_real_pix": true
  },
  "urls": {
    "api": "${BASE_URL}",
    "admin": "${BASE_URL}/admin",
    "portal": "${BASE_URL}/portal",
    "docs": "${BASE_URL}/docs"
  }
}
EOF

# Markdown Report
cat <<EOF > "${SUMMARY_MD}"
# Relatório de Demonstração Local - ${TIMESTAMP}

- **Branch:** \`${BRANCH}\`
- **Commit:** \`${COMMIT}\`
- **Base URL:** ${BASE_URL}
- **Data/Hora:** $(date)

## Status das Etapas

| Etapa | Status | Log |
|-------|--------|-----|
$(for key in "reset" "docker-up" "wait-ready" "seed-demo" "validate-demo-local" "validate-demo-client-portal" "validate-demo-admin-dashboard" "validate-examples" "validate-lmstudio" "validate-full"; do
    status="${STEPS_STATUS[$key]:-UNKNOWN}"
    log="${STEPS_LOGS[$key]:-N/A}"
    echo "| ${key} | ${status} | [${log}](${log}) |"
done)

## URLs de Acesso

- **API:** [${BASE_URL}](${BASE_URL})
- **Admin Dashboard:** [${BASE_URL}/admin](${BASE_URL}/admin)
- **Client Portal:** [${BASE_URL}/portal](${BASE_URL}/portal)
- **Documentação API:** [${BASE_URL}/docs](${BASE_URL}/docs)

## Comandos Úteis

- Abrir Portal: \`xdg-open ${BASE_URL}/portal\` (ou abra no navegador)
- Abrir Admin: \`xdg-open ${BASE_URL}/admin\`
- Ver Logs: \`make logs\`

## Segurança e Limitações

- [x] Confirmação: **Nenhum gateway de pagamento real (PSP/PIX) foi utilizado.** Tudo opera em modo mock/demo.
- Limitação: Ambiente local utiliza recursos reduzidos. Performance pode variar conforme hardware.
- Limitação: Dados são voláteis a menos que volumes persistentes sejam mantidos.

---
Gerado por \`scripts/demo-full-local.sh\`
EOF

echo "################################################"
echo "Demonstração Local Finalizada!"
echo "Relatório Gerado em: ${ARTIFACTS_DIR}"
echo "Resumo: ${SUMMARY_MD}"
echo "URLs Principais:"
echo "  - API: ${BASE_URL}"
echo "  - Portal: ${BASE_URL}/portal"
echo "  - Admin: ${BASE_URL}/admin"
echo "################################################"

# Final exit code based on ERROR presence
if [[ " ${STEPS_STATUS[*]} " =~ " ERROR " ]]; then
    exit 1
fi
exit 0
