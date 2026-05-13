#!/usr/bin/env bash
# validate-customer-demo-local.sh
# Valida o script customer-demo-local.sh e seus artefatos.
# Uso: ./scripts/validate-customer-demo-local.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo "============================================"
echo " Validacao do Customer Demo Script"
echo "============================================"
echo ""

# 1. Script existe e --help funciona
echo "--- [1] Script --help ---"
if [ -f "scripts/customer-demo-local.sh" ] && [ -x "scripts/customer-demo-local.sh" ]; then
    if bash scripts/customer-demo-local.sh --help >/dev/null 2>&1; then
        echo -e "  ${GREEN}[OK]${NC} --help funciona"
    else
        echo -e "  ${RED}[FALHA]${NC} --help falhou"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "  ${RED}[FALTA]${NC} scripts/customer-demo-local.sh nao encontrado ou sem permissao"
    ERRORS=$((ERRORS + 1))
fi

# 2. Modo --quick gera relatorio
echo ""
echo "--- [2] Modo --quick gera relatorio ---"
OUTPUT=$(bash scripts/customer-demo-local.sh --quick --no-build 2>&1 || true)
if echo "${OUTPUT}" | grep -qi "Relatorio"; then
    echo -e "  ${GREEN}[OK]${NC} Modo --quick gerou relatorio"
else
    echo -e "  ${YELLOW}[AVISO]${NC} Modo --quick pode nao ter gerado relatorio"
    WARNINGS=$((WARNINGS + 1))
fi
# Find latest report
LATEST_REPORT=$(ls -t artifacts/customer-demo/*/customer-demo-report.json 2>/dev/null | head -1)
if [ -n "${LATEST_REPORT}" ]; then
    echo -e "  ${GREEN}[OK]${NC} Relatorio JSON encontrado: ${LATEST_REPORT}"
else
    echo -e "  ${YELLOW}[AVISO]${NC} Nenhum relatorio JSON encontrado"
    WARNINGS=$((WARNINGS + 1))
fi

# 3. Status valido
echo ""
echo "--- [3] Status reportado ---"
if echo "${OUTPUT}" | grep -qE "CUSTOMER_DEMO_READY|CUSTOMER_DEMO_READY_WITH_WARNINGS|CUSTOMER_DEMO_FAILED"; then
    echo -e "  ${GREEN}[OK]${NC} Status valido encontrado"
else
    echo -e "  ${YELLOW}[AVISO]${NC} Status nao reconhecido na saida"
    WARNINGS=$((WARNINGS + 1))
fi

# 4. Relatorio nao contem secrets
echo ""
echo "--- [4] Relatorio sem secrets ---"
if [ -n "${LATEST_REPORT}" ] && [ -f "${LATEST_REPORT}" ]; then
    if grep -qE '(sk-[a-zA-Z0-9]{20,}|ADMIN_TOKEN=[a-zA-Z0-9]|ghp_[a-zA-Z0-9]{36})' "${LATEST_REPORT}" 2>/dev/null; then
        echo -e "  ${RED}[SECRET]${NC} Possivel secret encontrado no relatorio"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "  ${GREEN}[OK]${NC} Nenhum secret detectado"
    fi
else
    echo -e "  ${YELLOW}[AVISO]${NC} Nenhum relatorio para verificar"
    WARNINGS=$((WARNINGS + 1))
fi

# 5. Reset demo sem --yes nao apaga
echo ""
echo "--- [5] Reset demo sem --yes (dry-run) ---"
OUTPUT_DRY=$(bash scripts/customer-demo-local.sh --quick --no-build --reset-demo 2>&1 || true)
if echo "${OUTPUT_DRY}" | grep -qi "dry-run\|simulado\|Skipped"; then
    echo -e "  ${GREEN}[OK]${NC} Reset demo seguro (dry-run)"
else
    echo -e "  ${YELLOW}[AVISO]${NC} Reset demo pode nao estar em modo seguro"
    WARNINGS=$((WARNINGS + 1))
fi

# 6. Makefile tem target customer-demo
echo ""
echo "--- [6] Makefile targets ---"
if [ -f "Makefile" ]; then
    if grep -qE "^customer-demo:" Makefile; then
        echo -e "  ${GREEN}[OK]${NC} Target 'customer-demo' no Makefile"
    else
        echo -e "  ${RED}[FALTA]${NC} Target 'customer-demo' nao encontrado no Makefile"
        ERRORS=$((ERRORS + 1))
    fi
    if grep -qE "^customer-demo-full:" Makefile; then
        echo -e "  ${GREEN}[OK]${NC} Target 'customer-demo-full' no Makefile"
    else
        echo -e "  ${RED}[FALTA]${NC} Target 'customer-demo-full' nao encontrado no Makefile"
        ERRORS=$((ERRORS + 1))
    fi
    if grep -qE "^validate-customer-demo:" Makefile; then
        echo -e "  ${GREEN}[OK]${NC} Target 'validate-customer-demo' no Makefile"
    else
        echo -e "  ${RED}[FALTA]${NC} Target 'validate-customer-demo' nao encontrado no Makefile"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "  ${RED}[FALTA]${NC} Makefile nao encontrado"
    ERRORS=$((ERRORS + 1))
fi

# 7. artifacts/customer-demo esta no .gitignore
echo ""
echo "--- [7] .gitignore ---"
if grep -qE "artifacts/customer-demo|artifacts/" .gitignore 2>/dev/null; then
    echo -e "  ${GREEN}[OK]${NC} artifacts/customer-demo coberto pelo .gitignore"
else
    echo -e "  ${YELLOW}[AVISO]${NC} artifacts/customer-demo pode nao estar no .gitignore"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "============================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e " ${GREEN}RESULTADO: APROVADO${NC}"
elif [ $ERRORS -eq 0 ] && [ $WARNINGS -gt 0 ]; then
    echo -e " ${YELLOW}RESULTADO: APROVADO COM AVISOS (${WARNINGS})${NC}"
else
    echo -e " ${RED}RESULTADO: REPROVADO (${ERRORS} erros, ${WARNINGS} avisos)${NC}"
fi
echo "============================================"
exit $ERRORS
