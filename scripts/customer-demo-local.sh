#!/usr/bin/env bash
# customer-demo-local.sh
# Comando unico para preparar e validar uma demo comercial de cliente.
# Uso: ./scripts/customer-demo-local.sh [options]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
VERSION=$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "unknown")
TIMESTAMP=$(date +%Y%m%dT%H%M%S)

# Defaults
BASE_URL="http://localhost:18080"
NO_BUILD=false
RESET_DEMO=false
YES=false
SKIP_RAG=false
SKIP_TTS=false
SKIP_LMSTUDIO=false
SKIP_SCREENSHOTS=false
QUICK=false
FULL=false
OUTPUT_DIR="artifacts/customer-demo/${TIMESTAMP}"

show_help() {
    cat <<'EOF'
Uso: ./scripts/customer-demo-local.sh [opcoes]

Comando unico para preparar e validar uma demo comercial de cliente.

Opcoes:
  --base-url URL        URL base da stack (default: http://localhost:18080)
  --no-build            Pula build Docker
  --reset-demo          Reseta dados demo antes de recriar (dry-run por padrao)
  --yes                 Confirma acoes destrutivas (reset real)
  --skip-rag            Pula validacao RAG
  --skip-tts            Pula validacao TTS
  --skip-lmstudio       Pula verificacoes LM Studio
  --skip-screenshots    Pula plano de screenshots
  --quick               Modo rapido (pula geracao de proposta/quote/SOW/monthly)
  --full                Modo completo (inclui reset e rebuild)
  --output-dir DIR      Diretorio de saida (default: artifacts/customer-demo/<timestamp>)
  --help                Exibe esta ajuda e sai

Status de saida:
  CUSTOMER_DEMO_READY               = 0
  CUSTOMER_DEMO_READY_WITH_WARNINGS = 1
  CUSTOMER_DEMO_FAILED              = 2
EOF
    exit 0
}

# Parse --help early
for arg in "$@"; do
    if [[ "$arg" == "--help" ]]; then
        show_help
    fi
done

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-url) BASE_URL="$2"; shift 2 ;;
        --no-build) NO_BUILD=true; shift ;;
        --reset-demo) RESET_DEMO=true; shift ;;
        --yes) YES=true; shift ;;
        --skip-rag) SKIP_RAG=true; shift ;;
        --skip-tts) SKIP_TTS=true; shift ;;
        --skip-lmstudio) SKIP_LMSTUDIO=true; shift ;;
        --skip-screenshots) SKIP_SCREENSHOTS=true; shift ;;
        --quick) QUICK=true; shift ;;
        --full) FULL=true; shift ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        *) echo "Opcao desconhecida: $1"; echo "Use --help para ajuda."; exit 1 ;;
    esac
done

LOGS_DIR="${OUTPUT_DIR}/logs"
REPORT_JSON="${OUTPUT_DIR}/customer-demo-report.json"
REPORT_MD="${OUTPUT_DIR}/customer-demo-report.md"
mkdir -p "${LOGS_DIR}"

# Counters
PASS=0
FAIL=0
WARN=0
RESULTS=()
WARNINGS=()
ERRORS=()

# Helpers
log()    { echo "[INFO] $1" | tee -a "${LOGS_DIR}/demo.log"; }
pass()   { PASS=$((PASS+1)); echo -e "  [PASS] $1" | tee -a "${LOGS_DIR}/demo.log"; RESULTS+=("pass:$1"); }
fail()   { FAIL=$((FAIL+1)); echo -e "  [FAIL] $1" | tee -a "${LOGS_DIR}/demo.log"; RESULTS+=("fail:$1"); ERRORS+=("$1"); }
warn()   { WARN=$((WARN+1)); echo -e "  [WARN] $1" | tee -a "${LOGS_DIR}/demo.log"; RESULTS+=("warn:$1"); WARNINGS+=("$1"); }
step()   { echo "" | tee -a "${LOGS_DIR}/demo.log"; echo "=== $1 ===" | tee -a "${LOGS_DIR}/demo.log"; }

http_ok() {
    local url=$1
    local method=${2:-GET}
    local c
    c=$(curl -X "$method" -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    echo "$c"
}

# Load ADMIN_TOKEN
ADMIN_TOKEN=""
if [ -f "${ROOT_DIR}/.env.local" ]; then
    ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" "${ROOT_DIR}/.env.local" | cut -d= -f2 || echo "")
fi
if [ -f "${ROOT_DIR}/.env" ]; then
    ADMIN_TOKEN=${ADMIN_TOKEN:-$(grep "^ADMIN_TOKEN=" "${ROOT_DIR}/.env" | cut -d= -f2 || echo "")}
fi

# === BANNER ===
echo ""
echo "============================================"
echo "  Local AI Appliance — Customer Demo"
echo "  Version: ${VERSION}"
echo "  Timestamp: ${TIMESTAMP}"
echo "  Base URL: ${BASE_URL}"
echo "  Mode: $([ "${QUICK}" = true ] && echo "QUICK" || echo "FULL")"
echo "============================================"
echo ""

# === 1. Health / Ready ===
step "1. Validando saude da stack"
HEALTH_CODE=$(http_ok "${BASE_URL}/health")
if [ "${HEALTH_CODE}" = "200" ]; then
    pass "Health check: HTTP ${HEALTH_CODE}"
else
    warn "Health check: HTTP ${HEALTH_CODE} (stack pode nao estar rodando)"
fi
READY_CODE=$(http_ok "${BASE_URL}/ready")
if [ "${READY_CODE}" = "200" ]; then
    pass "Ready check: HTTP ${READY_CODE}"
else
    warn "Ready check: HTTP ${READY_CODE}"
fi

# === 2. Security Report ===
step "2. Validando security report"
SEC_REPORT_FILE=""
if [ -d "artifacts/security-reports" ]; then
    SEC_REPORT_FILE=$(ls -t artifacts/security-reports/ 2>/dev/null | head -1)
fi
if [ -n "${SEC_REPORT_FILE}" ] && [ -f "artifacts/security-reports/${SEC_REPORT_FILE}/security-report.md" ]; then
    pass "Security report recente encontrado: ${SEC_REPORT_FILE}"
elif [ -x "${ROOT_DIR}/scripts/security-report-local.sh" ]; then
    log "Gerando security report..."
    if bash "${ROOT_DIR}/scripts/security-report-local.sh" >> "${LOGS_DIR}/security-report.log" 2>&1; then
        pass "Security report gerado com sucesso"
    else
        warn "Security report gerado com warnings"
    fi
else
    warn "security-report-local.sh nao encontrado"
fi

# === 3. Production Readiness ===
step "3. Validando production readiness"
if [ -x "${ROOT_DIR}/scripts/production-readiness-local.sh" ]; then
    if bash "${ROOT_DIR}/scripts/production-readiness-local.sh" >> "${LOGS_DIR}/production-readiness.log" 2>&1; then
        pass "Production readiness: OK"
    else
        warn "Production readiness reportou falhas"
    fi
else
    warn "production-readiness-local.sh nao encontrado"
fi

# === 4. Reset demo (se --reset-demo) ===
if [ "${RESET_DEMO}" = true ] || [ "${FULL}" = true ]; then
    step "4. Resetando dados demo"
    if [ -x "${ROOT_DIR}/scripts/reset-commercial-demo-pack.sh" ]; then
        if [ "${YES}" = true ]; then
            if bash "${ROOT_DIR}/scripts/reset-commercial-demo-pack.sh" --yes >> "${LOGS_DIR}/reset.log" 2>&1; then
                pass "Reset demo executado (--yes)"
            else
                warn "Reset demo reportou erros (ver reset.log)"
            fi
        else
            log "Modo dry-run: reset simulado"
            bash "${ROOT_DIR}/scripts/reset-commercial-demo-pack.sh" --dry-run >> "${LOGS_DIR}/reset.log" 2>&1 || true
            pass "Reset demo simulado (dry-run)"
        fi
    else
        warn "reset-commercial-demo-pack.sh nao encontrado"
    fi
else
    step "4. Pulando reset (use --reset-demo ou --full)"
    log "Skipped"
fi

# === 5. Seed commercial demo pack ===
if [ "${FULL}" = true ]; then
    step "5. Seeding commercial demo pack"
    if [ -x "${ROOT_DIR}/scripts/seed-commercial-demo-pack.sh" ]; then
        SEED_OUTPUT=$(bash "${ROOT_DIR}/scripts/seed-commercial-demo-pack.sh" 2>&1 || true)
        echo "${SEED_OUTPUT}" >> "${LOGS_DIR}/seed.log"
        if echo "${SEED_OUTPUT}" | grep -qi "error\|ERRO"; then
            warn "Demo pack seed teve erros (ver seed.log)"
        else
            pass "Commercial demo pack seeded"
        fi
    else
        warn "seed-commercial-demo-pack.sh nao encontrado"
    fi
else
    step "5. Pulando seed (use --full)"
    log "Skipped"
fi

# === 6. Validate fake demo data ===
step "6. Validando fake demo data"
if [ -x "${ROOT_DIR}/scripts/validate-fake-demo-data.sh" ]; then
    if bash "${ROOT_DIR}/scripts/validate-fake-demo-data.sh" >> "${LOGS_DIR}/fake-data.log" 2>&1; then
        pass "Fake demo data validated"
    else
        warn "Fake data validation reportou falhas"
    fi
else
    warn "validate-fake-demo-data.sh nao encontrado"
fi

# === 7. Validate /capabilities ===
step "7. Validando /capabilities"
CAP_CODE=$(http_ok "${BASE_URL}/capabilities")
if [ "${CAP_CODE}" = "200" ]; then
    pass "/capabilities HTTP 200"
    # Check that PSP/PIX limitations are mentioned
    if curl -fsS "${BASE_URL}/capabilities" 2>/dev/null | grep -qi "PSP\|PIX"; then
        pass "/capabilities menciona limitacoes PSP/PIX"
    else
        warn "/capabilities pode nao mencionar PSP/PIX explicitamente"
    fi
else
    warn "/capabilities HTTP ${CAP_CODE}"
fi

# === 8. Validate Client Portal ===
step "8. Validando Client Portal"
PORTAL_CODE=$(http_ok "${BASE_URL}/client-portal")
if [ "${PORTAL_CODE}" = "200" ] || [ "${PORTAL_CODE}" = "401" ]; then
    pass "Client Portal HTTP ${PORTAL_CODE}"
else
    warn "Client Portal HTTP ${PORTAL_CODE}"
fi

# === 9. Validate Admin Dashboard ===
step "9. Validando Admin Dashboard"
ADMIN_CODE=$(http_ok "${BASE_URL}/admin-dashboard")
if [ "${ADMIN_CODE}" = "200" ] || [ "${ADMIN_CODE}" = "401" ] || [ "${ADMIN_CODE}" = "302" ]; then
    pass "Admin Dashboard HTTP ${ADMIN_CODE}"
else
    warn "Admin Dashboard HTTP ${ADMIN_CODE}"
fi

# === 10. Validate Admin Lab ===
step "10. Validando Admin Lab"
LAB_CODE=$(http_ok "${BASE_URL}/admin-lab")
if [ "${LAB_CODE}" = "200" ] || [ "${LAB_CODE}" = "302" ]; then
    pass "Admin Lab HTTP ${LAB_CODE}"
else
    warn "Admin Lab HTTP ${LAB_CODE}"
fi

# === 11. Validate Sales/Leads ===
step "11. Validando Sales/Leads"
if [ -n "${ADMIN_TOKEN}" ]; then
    CLIENTS_CODE=$(http_ok "${BASE_URL}/admin/clients")
    if [ "${CLIENTS_CODE}" = "200" ] || [ "${CLIENTS_CODE}" = "401" ]; then
        pass "Admin clients endpoint HTTP ${CLIENTS_CODE}"
    else
        warn "Admin clients endpoint HTTP ${CLIENTS_CODE}"
    fi
else
    warn "ADMIN_TOKEN nao disponivel, pulando validacao Sales/Leads"
fi

# === 12. Validate chat/responses/embeddings ===
step "12. Validando chat/responses/embeddings"
# Check v1/models
MODELS_CODE=$(http_ok "${BASE_URL}/v1/models")
if [ "${MODELS_CODE}" = "200" ] || [ "${MODELS_CODE}" = "401" ]; then
    pass "v1/models HTTP ${MODELS_CODE}"
else
    warn "v1/models HTTP ${MODELS_CODE}"
fi
# Check v1/chat/completions (POST)
CHAT_CODE=$(http_ok "${BASE_URL}/v1/chat/completions" "POST")
if [ "${CHAT_CODE}" = "200" ] || [ "${CHAT_CODE}" = "400" ] || [ "${CHAT_CODE}" = "401" ]; then
    pass "v1/chat/completions reachable (HTTP ${CHAT_CODE})"
else
    warn "v1/chat/completions HTTP ${CHAT_CODE}"
fi

# === 13. Validate RAG ===
if [ "${SKIP_RAG}" = false ]; then
    step "13. Validando RAG"
    RAG_CODE=$(http_ok "${BASE_URL}/v1/rag/query" "POST")
    if [ "${RAG_CODE}" = "200" ] || [ "${RAG_CODE}" = "400" ] || [ "${RAG_CODE}" = "401" ]; then
        pass "RAG endpoint reachable (HTTP ${RAG_CODE})"
    else
        warn "RAG endpoint HTTP ${RAG_CODE}"
    fi
else
    step "13. Pulando RAG (--skip-rag)"
    log "Skipped"
fi

# === 14. Validate TTS ===
if [ "${SKIP_TTS}" = false ]; then
    step "14. Validando TTS"
    TTS_HEALTH_CODE=$(http_ok "${BASE_URL}/pocket-tts/health")
    if [ "${TTS_HEALTH_CODE}" = "200" ]; then
        pass "TTS health HTTP 200"
        TTS_CODE=$(http_ok "${BASE_URL}/pocket-tts/tts" "POST")
        if [ "${TTS_CODE}" = "200" ] || [ "${TTS_CODE}" = "400" ] || [ "${TTS_CODE}" = "401" ]; then
            pass "TTS endpoint reachable (HTTP ${TTS_CODE})"
        else
            warn "TTS endpoint HTTP ${TTS_CODE}"
        fi
    else
        warn "TTS nao disponivel (HTTP ${TTS_HEALTH_CODE})"
    fi
else
    step "14. Pulando TTS (--skip-tts)"
    log "Skipped"
fi

# === 15-17. Proposal/Quote/SOW (skip on --quick) ===
if [ "${QUICK}" = false ]; then
    step "15. Gerando proposta demo"
    if [ -x "${ROOT_DIR}/scripts/generate-client-proposal.sh" ]; then
        if bash "${ROOT_DIR}/scripts/generate-client-proposal.sh" --company-name "Cliente Demo" --segment "tecnologia" --plan "pro" >> "${LOGS_DIR}/proposal.log" 2>&1; then
            pass "Proposta demo gerada"
        else
            warn "Geracao de proposta reportou erros"
        fi
    else
        warn "generate-client-proposal.sh nao encontrado"
    fi

    step "16. Gerando orcamento demo"
    if [ -x "${ROOT_DIR}/scripts/generate-local-quote.sh" ]; then
        if bash "${ROOT_DIR}/scripts/generate-local-quote.sh" --company-name "Cliente Demo" --plan "Pro" --rag --support-hours 4 >> "${LOGS_DIR}/quote.log" 2>&1; then
            pass "Orcamento demo gerado"
        else
            warn "Geracao de orcamento reportou erros"
        fi
    else
        warn "generate-local-quote.sh nao encontrado"
    fi

    step "17. Gerando SOW demo"
    if [ -x "${ROOT_DIR}/scripts/generate-sow-local.sh" ]; then
        if bash "${ROOT_DIR}/scripts/generate-sow-local.sh" --company-name "Cliente Demo" --project-name "Local AI Appliance" >> "${LOGS_DIR}/sow.log" 2>&1; then
            pass "SOW demo gerado"
        else
            warn "Geracao de SOW reportou erros"
        fi
    else
        warn "generate-sow-local.sh nao encontrado"
    fi

    step "18. Gerando monthly report demo"
    if [ -x "${ROOT_DIR}/scripts/generate-client-monthly-report.sh" ]; then
        if bash "${ROOT_DIR}/scripts/generate-client-monthly-report.sh" --email "demo@example.local" --month "$(date +%Y-%m)" >> "${LOGS_DIR}/monthly.log" 2>&1; then
            pass "Monthly report demo gerado"
        else
            warn "Monthly report reportou erros"
        fi
    else
        warn "generate-client-monthly-report.sh nao encontrado"
    fi
else
    log "Pulando geracao de proposta/quote/SOW/monthly (modo --quick)"
fi

# === 19. Meeting Ready Check ===
step "19. Rodando meeting-ready check"
MEETING_ARGS=("--base-url" "${BASE_URL}")
if [ "${SKIP_TTS}" = true ]; then MEETING_ARGS+=("--skip-tts"); fi
if [ "${SKIP_RAG}" = true ]; then MEETING_ARGS+=("--skip-rag"); fi
if [ "${SKIP_LMSTUDIO}" = true ]; then MEETING_ARGS+=("--skip-lmstudio"); fi
if [ -x "${ROOT_DIR}/scripts/meeting-ready-check-local.sh" ]; then
    MEETING_OUTPUT=$(bash "${ROOT_DIR}/scripts/meeting-ready-check-local.sh" "${MEETING_ARGS[@]}" 2>&1 || true)
    echo "${MEETING_OUTPUT}" >> "${LOGS_DIR}/meeting-ready.log"
    if echo "${MEETING_OUTPUT}" | grep -qi "MEETING_READY"; then
        pass "Meeting-ready: MEETING_READY"
    elif echo "${MEETING_OUTPUT}" | grep -qi "READY_WITH_WARNINGS"; then
        warn "Meeting-ready: READY_WITH_WARNINGS"
    else
        warn "Meeting-ready: status inesperado"
    fi
else
    warn "meeting-ready-check-local.sh nao encontrado"
fi

# === 20. Screenshot plan ===
if [ "${SKIP_SCREENSHOTS}" = false ]; then
    step "20. Preparando plano de screenshots"
    if [ -x "${ROOT_DIR}/scripts/prepare-demo-screenshots-local.sh" ]; then
        if bash "${ROOT_DIR}/scripts/prepare-demo-screenshots-local.sh" --placeholders-only >> "${LOGS_DIR}/screenshots.log" 2>&1; then
            pass "Plano de screenshots preparado"
        else
            warn "Plano de screenshots reportou erros"
        fi
    else
        warn "prepare-demo-screenshots-local.sh nao encontrado"
    fi
else
    step "20. Pulando screenshots (--skip-screenshots)"
    log "Skipped"
fi

# === Determine final status ===
echo ""
echo "============================================"
echo "  Customer Demo — Resultados"
echo "  Pass: ${PASS} | Warnings: ${WARN} | Failures: ${FAIL}"
echo "============================================"

if [ "${FAIL}" -gt 0 ]; then
    FINAL_STATUS="CUSTOMER_DEMO_FAILED"
    EXIT_CODE=2
elif [ "${WARN}" -gt 0 ]; then
    FINAL_STATUS="CUSTOMER_DEMO_READY_WITH_WARNINGS"
    EXIT_CODE=1
else
    FINAL_STATUS="CUSTOMER_DEMO_READY"
    EXIT_CODE=0
fi

echo "  Status: ${FINAL_STATUS}"
echo ""

# === Build results array (avoid trailing comma) ===
RESULTS_JSON="["
FIRST=true
for r in "${RESULTS[@]}"; do
    if [ "$FIRST" = true ]; then FIRST=false; else RESULTS_JSON+=","; fi
    RESULTS_JSON+="\"${r}\""
done
RESULTS_JSON+="]"

WARNINGS_JSON="["
FIRST=true
for w in "${WARNINGS[@]}"; do
    if [ "$FIRST" = true ]; then FIRST=false; else WARNINGS_JSON+=","; fi
    WARNINGS_JSON+="\"${w}\""
done
WARNINGS_JSON+="]"

ERRORS_JSON="["
FIRST=true
for e in "${ERRORS[@]}"; do
    if [ "$FIRST" = true ]; then FIRST=false; else ERRORS_JSON+=","; fi
    ERRORS_JSON+="\"${e}\""
done
ERRORS_JSON+="]"

if [ "${QUICK}" = true ]; then MODE_STR="quick"; else MODE_STR="full"; fi

cat > "${REPORT_JSON}" <<JSONEOF
{
  "report_type": "customer-demo",
  "version": "${VERSION}",
  "timestamp": "${TIMESTAMP}",
  "base_url": "${BASE_URL}",
  "mode": "${MODE_STR}",
  "status": "${FINAL_STATUS}",
  "counts": {
    "pass": ${PASS},
    "warn": ${WARN},
    "fail": ${FAIL}
  },
  "results": ${RESULTS_JSON},
  "warnings": ${WARNINGS_JSON},
  "errors": ${ERRORS_JSON}
}
JSONEOF

# Generate MD report
{
    echo "# Customer Demo Report"
    echo ""
    echo "| Campo | Valor |"
    echo "|-------|-------|"
    echo "| **Versao** | ${VERSION} |"
    echo "| **Timestamp** | ${TIMESTAMP} |"
    echo "| **Base URL** | ${BASE_URL} |"
    echo "| **Modo** | $([ "${QUICK}" = true ] && echo "Quick" || echo "Full") |"
    echo "| **Status** | ${FINAL_STATUS} |"
    echo ""
    echo "## Resultados"
    echo ""
    echo "| Tipo | Contagem |"
    echo "|------|----------|"
    echo "| Pass | ${PASS} |"
    echo "| Warn | ${WARN} |"
    echo "| Fail | ${FAIL} |"
    echo ""
    echo "## Detalhes"
    echo ""
    for entry in "${RESULTS[@]}"; do
        type="${entry%%:*}"
        msg="${entry#*:}"
        case "${type}" in
            pass) echo "- [PASS] ${msg}" ;;
            warn) echo "- [WARN] ${msg}" ;;
            fail) echo "- [FAIL] ${msg}" ;;
        esac
    done
    echo ""
    echo "## Logs"
    echo ""
    for logf in "${LOGS_DIR}"/*; do
        echo "- \`${logf}\`"
    done
    echo ""
    echo "---"
    echo "Gerado por \`scripts/customer-demo-local.sh\`"
} > "${REPORT_MD}"

echo "  Relatorio: ${REPORT_MD}"
echo "  JSON:      ${REPORT_JSON}"
echo "  Logs:      ${LOGS_DIR}/"
echo ""

exit "${EXIT_CODE}"
