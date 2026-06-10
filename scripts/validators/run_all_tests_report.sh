#!/usr/bin/env bash
# =============================================================================
# run_all_tests_report.sh
#
# Executa todos os arquivos de teste em tests/ individualmente e gera um
# relatório informando quais passaram e quais apresentaram erros.
#
# Uso:
#   ./scripts/validators/run_all_tests_report.sh [--html] [--quick]
#
# Opções:
#   --html   Gera também uma versão HTML do relatório
#   --quick  Executa com timeout reduzido (30s por arquivo)
# =============================================================================
set -euo pipefail

# ── Configuração ─────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Ativar virtualenv se existir ─────────────────────────────────────────────
if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.venv/bin/activate"
elif [ -f "${PROJECT_ROOT}/venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/venv/bin/activate"
fi

TESTS_DIR="${PROJECT_ROOT}/tests"
REPORT_DIR="${PROJECT_ROOT}/reports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="${REPORT_DIR}/test_report_${TIMESTAMP}.md"
LOG_DIR="${REPORT_DIR}/test_logs_${TIMESTAMP}"
TIMEOUT_SECONDS=120
GENERATE_HTML=false

# ── Parsing de argumentos ────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --html)  GENERATE_HTML=true ;;
        --quick) TIMEOUT_SECONDS=30 ;;
    esac
done

# ── Preparação de diretórios ─────────────────────────────────────────────────
mkdir -p "${REPORT_DIR}" "${LOG_DIR}"

# ── Cores para terminal ─────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # No Color

# ── Descoberta de arquivos de teste ──────────────────────────────────────────
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}   LLM Inference Stack — Relatório de Testes${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo ""

mapfile -t TEST_FILES < <(find "${TESTS_DIR}" -name 'test_*.py' -type f | sort)
TOTAL=${#TEST_FILES[@]}

echo -e "${BLUE}📁 Diretório de testes:${NC} ${TESTS_DIR}"
echo -e "${BLUE}📊 Total de arquivos:${NC}  ${TOTAL}"
echo -e "${BLUE}⏱️  Timeout por arquivo:${NC} ${TIMEOUT_SECONDS}s"
echo -e "${BLUE}📄 Relatório:${NC}          ${REPORT_FILE}"
echo ""

# ── Contadores ───────────────────────────────────────────────────────────────
PASSED=0
FAILED=0
ERRORS=0
TIMEOUTS=0
SKIPPED_FILES=0
CURRENT=0

# ── Arrays para resultados ───────────────────────────────────────────────────
declare -a PASSED_FILES=()
declare -a FAILED_FILES=()
declare -a ERROR_FILES=()
declare -a TIMEOUT_FILES=()
declare -a FAILED_DETAILS=()

START_TIME=$(date +%s)

# ── Execução dos testes ──────────────────────────────────────────────────────
for TEST_FILE in "${TEST_FILES[@]}"; do
    CURRENT=$((CURRENT + 1))
    REL_PATH="${TEST_FILE#${PROJECT_ROOT}/}"
    FILE_NAME="$(basename "${TEST_FILE}")"
    LOG_FILE="${LOG_DIR}/${FILE_NAME%.py}.log"

    # Progresso
    PERCENT=$(( (CURRENT * 100) / TOTAL ))
    printf "\r${BOLD}[%3d/%d] (%2d%%)${NC} Testando: %-60s" \
        "${CURRENT}" "${TOTAL}" "${PERCENT}" "${FILE_NAME}"

    # Executa pytest no arquivo individual
    FILE_START=$(date +%s)
    EXIT_CODE=0
    timeout "${TIMEOUT_SECONDS}" \
        python -m pytest "${TEST_FILE}" \
            --tb=short \
            --no-header \
            -q \
            --timeout=60 \
            2>&1 > "${LOG_FILE}" || EXIT_CODE=$?
    FILE_END=$(date +%s)
    FILE_DURATION=$((FILE_END - FILE_START))

    # Interpreta resultado
    if [ ${EXIT_CODE} -eq 124 ]; then
        # timeout
        TIMEOUTS=$((TIMEOUTS + 1))
        TIMEOUT_FILES+=("${REL_PATH}")
        printf "\r${BOLD}[%3d/%d]${NC} ${YELLOW}⏱ TIMEOUT${NC}  %-55s (%ds)\n" \
            "${CURRENT}" "${TOTAL}" "${FILE_NAME}" "${FILE_DURATION}"
    elif [ ${EXIT_CODE} -eq 0 ]; then
        # sucesso
        PASSED=$((PASSED + 1))
        PASSED_FILES+=("${REL_PATH}")
        printf "\r${BOLD}[%3d/%d]${NC} ${GREEN}✅ PASS${NC}     %-55s (%ds)\n" \
            "${CURRENT}" "${TOTAL}" "${FILE_NAME}" "${FILE_DURATION}"
    elif [ ${EXIT_CODE} -eq 1 ]; then
        # falhas de teste
        FAILED=$((FAILED + 1))
        FAILED_FILES+=("${REL_PATH}")
        # Captura resumo das falhas
        FAIL_SUMMARY=$(tail -20 "${LOG_FILE}" | grep -E "FAILED|ERROR|assert|Error" | head -5 || true)
        FAILED_DETAILS+=("### ${REL_PATH}\n\`\`\`\n${FAIL_SUMMARY}\n\`\`\`\n")
        printf "\r${BOLD}[%3d/%d]${NC} ${RED}❌ FAIL${NC}     %-55s (%ds)\n" \
            "${CURRENT}" "${TOTAL}" "${FILE_NAME}" "${FILE_DURATION}"
    elif [ ${EXIT_CODE} -eq 2 ]; then
        # erros de importação / coleta
        ERRORS=$((ERRORS + 1))
        ERROR_FILES+=("${REL_PATH}")
        FAIL_SUMMARY=$(tail -20 "${LOG_FILE}" | grep -E "ImportError|ModuleNotFoundError|SyntaxError|Error|ERROR" | head -5 || true)
        FAILED_DETAILS+=("### ${REL_PATH} (Erro de coleta)\n\`\`\`\n${FAIL_SUMMARY}\n\`\`\`\n")
        printf "\r${BOLD}[%3d/%d]${NC} ${RED}🔥 ERROR${NC}    %-55s (%ds)\n" \
            "${CURRENT}" "${TOTAL}" "${FILE_NAME}" "${FILE_DURATION}"
    elif [ ${EXIT_CODE} -eq 5 ]; then
        # nenhum teste coletado
        SKIPPED_FILES=$((SKIPPED_FILES + 1))
        printf "\r${BOLD}[%3d/%d]${NC} ${YELLOW}⚠ SKIP${NC}     %-55s (%ds)\n" \
            "${CURRENT}" "${TOTAL}" "${FILE_NAME}" "${FILE_DURATION}"
    else
        ERRORS=$((ERRORS + 1))
        ERROR_FILES+=("${REL_PATH}")
        FAIL_SUMMARY=$(tail -10 "${LOG_FILE}" || true)
        FAILED_DETAILS+=("### ${REL_PATH} (Exit code: ${EXIT_CODE})\n\`\`\`\n${FAIL_SUMMARY}\n\`\`\`\n")
        printf "\r${BOLD}[%3d/%d]${NC} ${RED}🔥 ERROR${NC}    %-55s (code=%d, %ds)\n" \
            "${CURRENT}" "${TOTAL}" "${FILE_NAME}" "${EXIT_CODE}" "${FILE_DURATION}"
    fi
done

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))
TOTAL_MINUTES=$((TOTAL_DURATION / 60))
TOTAL_SECONDS=$((TOTAL_DURATION % 60))

# ── Resumo no terminal ──────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}   RESUMO${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}✅ Passaram:${NC}     ${PASSED}"
echo -e "  ${RED}❌ Falharam:${NC}     ${FAILED}"
echo -e "  ${RED}🔥 Erros:${NC}        ${ERRORS}"
echo -e "  ${YELLOW}⏱  Timeout:${NC}      ${TIMEOUTS}"
echo -e "  ${YELLOW}⚠  Sem testes:${NC}   ${SKIPPED_FILES}"
echo -e "  ${BLUE}📊 Total:${NC}        ${TOTAL}"
echo -e "  ${BLUE}⏱  Duração:${NC}      ${TOTAL_MINUTES}m ${TOTAL_SECONDS}s"
echo ""

# ── Geração do relatório Markdown ────────────────────────────────────────────
{
    echo "# 📊 Relatório de Testes — LLM Inference Stack"
    echo ""
    echo "**Data:** $(date '+%d/%m/%Y %H:%M:%S')"
    echo "**Duração total:** ${TOTAL_MINUTES}m ${TOTAL_SECONDS}s"
    echo "**Timeout por arquivo:** ${TIMEOUT_SECONDS}s"
    echo ""
    echo "## Resumo"
    echo ""
    echo "| Métrica | Valor |"
    echo "|---------|-------|"
    echo "| ✅ Passaram | ${PASSED} |"
    echo "| ❌ Falharam | ${FAILED} |"
    echo "| 🔥 Erros de coleta | ${ERRORS} |"
    echo "| ⏱ Timeout | ${TIMEOUTS} |"
    echo "| ⚠ Sem testes | ${SKIPPED_FILES} |"
    echo "| **Total de arquivos** | **${TOTAL}** |"
    echo ""

    PROBLEM_COUNT=$((FAILED + ERRORS + TIMEOUTS))
    if [ ${PROBLEM_COUNT} -eq 0 ]; then
        echo "> [!TIP]"
        echo "> 🎉 **Todos os testes passaram com sucesso!**"
    else
        echo "> [!WARNING]"
        echo "> **${PROBLEM_COUNT} arquivo(s) apresentaram problemas.**"
    fi
    echo ""

    # Arquivos com falha
    if [ ${#FAILED_FILES[@]} -gt 0 ]; then
        echo "## ❌ Arquivos com Falhas de Teste (${FAILED})"
        echo ""
        echo "| # | Arquivo |"
        echo "|---|---------|"
        I=1
        for f in "${FAILED_FILES[@]}"; do
            echo "| ${I} | \`${f}\` |"
            I=$((I + 1))
        done
        echo ""
    fi

    # Arquivos com erros
    if [ ${#ERROR_FILES[@]} -gt 0 ]; then
        echo "## 🔥 Arquivos com Erros de Coleta/Importação (${ERRORS})"
        echo ""
        echo "| # | Arquivo |"
        echo "|---|---------|"
        I=1
        for f in "${ERROR_FILES[@]}"; do
            echo "| ${I} | \`${f}\` |"
            I=$((I + 1))
        done
        echo ""
    fi

    # Arquivos com timeout
    if [ ${#TIMEOUT_FILES[@]} -gt 0 ]; then
        echo "## ⏱ Arquivos com Timeout (${TIMEOUTS})"
        echo ""
        echo "| # | Arquivo |"
        echo "|---|---------|"
        I=1
        for f in "${TIMEOUT_FILES[@]}"; do
            echo "| ${I} | \`${f}\` |"
            I=$((I + 1))
        done
        echo ""
    fi

    # Detalhes dos erros
    if [ ${#FAILED_DETAILS[@]} -gt 0 ]; then
        echo "## 🔍 Detalhes dos Erros"
        echo ""
        for detail in "${FAILED_DETAILS[@]}"; do
            echo -e "${detail}"
        done
    fi

    # Arquivos que passaram
    if [ ${#PASSED_FILES[@]} -gt 0 ]; then
        echo "## ✅ Arquivos que Passaram (${PASSED})"
        echo ""
        echo "<details>"
        echo "<summary>Clique para expandir a lista completa</summary>"
        echo ""
        echo "| # | Arquivo |"
        echo "|---|---------|"
        I=1
        for f in "${PASSED_FILES[@]}"; do
            echo "| ${I} | \`${f}\` |"
            I=$((I + 1))
        done
        echo ""
        echo "</details>"
        echo ""
    fi

    echo "---"
    echo ""
    echo "*Logs individuais disponíveis em: \`${LOG_DIR}/\`*"

} > "${REPORT_FILE}"

echo -e "${GREEN}📄 Relatório gerado: ${REPORT_FILE}${NC}"
echo -e "${BLUE}📂 Logs individuais: ${LOG_DIR}/${NC}"

# ── Geração HTML (opcional) ──────────────────────────────────────────────────
if [ "${GENERATE_HTML}" = true ] && command -v python3 &> /dev/null; then
    HTML_FILE="${REPORT_DIR}/test_report_${TIMESTAMP}.html"
    python3 -c "
import sys
try:
    import markdown
    with open('${REPORT_FILE}', 'r') as f:
        md = f.read()
    html_body = markdown.markdown(md, extensions=['tables', 'fenced_code'])
    html = f'''<!DOCTYPE html>
<html><head>
<meta charset=\"utf-8\">
<title>Relatório de Testes</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; background: #0d1117; color: #c9d1d9; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #30363d; padding: 8px 12px; text-align: left; }}
th {{ background: #161b22; }}
code {{ background: #161b22; padding: 2px 6px; border-radius: 4px; }}
pre {{ background: #161b22; padding: 1rem; border-radius: 8px; overflow-x: auto; }}
h1, h2, h3 {{ color: #58a6ff; }}
</style>
</head><body>{html_body}</body></html>'''
    with open('${HTML_FILE}', 'w') as f:
        f.write(html)
    print('HTML gerado: ${HTML_FILE}')
except ImportError:
    print('Módulo markdown não encontrado. Instale com: pip install markdown', file=sys.stderr)
" 2>&1 && echo -e "${GREEN}🌐 Relatório HTML: ${HTML_FILE}${NC}" || true
fi

# ── Exit code baseado nos resultados ─────────────────────────────────────────
if [ $((FAILED + ERRORS + TIMEOUTS)) -gt 0 ]; then
    exit 1
fi
exit 0
