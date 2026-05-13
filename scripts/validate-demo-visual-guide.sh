#!/bin/bash
# validate-demo-visual-guide.sh
# Valida a integridade, segurança e completude do guia visual de demo.
# Uso: ./scripts/validate-demo-visual-guide.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0
BASE_DIR="docs/demo-visual-guide"
SCRIPT_DIR="scripts"

echo "============================================"
echo " Validacao do Guia Visual de Demonstracao"
echo "============================================"
echo ""

# --- 1. Documentos existem ---
echo "--- [1/8] Documentos do guia visual ---"
required_docs=(
    "${BASE_DIR}/README.md"
    "${BASE_DIR}/SCREENSHOT_CHECKLIST.md"
    "${BASE_DIR}/DEMO_VISUAL_FLOW.md"
    "${BASE_DIR}/CAPTURE_COMMANDS.md"
    "${BASE_DIR}/DEMO_STORYBOARD.md"
    "${BASE_DIR}/placeholders/README.md"
)
for doc in "${required_docs[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "  ${GREEN}[OK]${NC} $doc"
    else
        echo -e "  ${RED}[FALTA]${NC} $doc"
        ERRORS=$((ERRORS + 1))
    fi
done

# --- 2. Telas principais documentadas ---
echo ""
echo "--- [2/8] Telas principais documentadas ---"
required_screens=(
    "Landing Page"
    "Capabilities"
    "Client Portal"
    "Admin Dashboard"
    "Admin Lab"
    "System Control Center"
    "Sales/Leads"
    "Pricing/Plans"
    "RAG demo"
    "TTS demo"
    "API examples"
    "Security Report"
    "Production Readiness"
    "Meeting Ready"
    "Proposal/Quote/SOW"
)
for screen in "${required_screens[@]}"; do
    if grep -qi "$screen" "${BASE_DIR}/DEMO_STORYBOARD.md" 2>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} $screen"
    else
        echo -e "  ${YELLOW}[AVISO]${NC} $screen nao encontrada em DEMO_STORYBOARD.md"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# --- 3. Limitacoes PSP/PIX real aparecem ---
echo ""
echo "--- [3/8] Limitacoes PSP/PIX real ---"
if grep -qiE "psp.*real|pix.*real|sem.*psp|sem.*pix|billing.*manual|nao.*psp" "${BASE_DIR}"/*.md 2>/dev/null; then
    echo -e "  ${GREEN}[OK]${NC} Limitacoes PSP/PIX documentadas"
else
    echo -e "  ${YELLOW}[AVISO]${NC} Limitacoes PSP/PIX podem nao estar explicitas"
    WARNINGS=$((WARNINGS + 1))
fi

# --- 4. Nao contem secrets ---
echo ""
echo "--- [4/8] Verificacao de secrets ---"
if command -v python3 &>/dev/null; then
    SECRET_FOUND=0
    # Check for potential secrets in the doc files
    for f in "${BASE_DIR}"/*.md "${BASE_DIR}"/placeholders/*.md; do
        [ -f "$f" ] || continue
        if grep -qE '(sk-[a-zA-Z0-9]{20,}|ADMIN_TOKEN=[a-zA-Z0-9]|ghp_[a-zA-Z0-9]{36})' "$f" 2>/dev/null; then
            echo -e "  ${RED}[SECRET]${NC} Possivel secret encontrado em $f"
            SECRET_FOUND=1
            ERRORS=$((ERRORS + 1))
        fi
    done
    if [ "$SECRET_FOUND" -eq 0 ]; then
        echo -e "  ${GREEN}[OK]${NC} Nenhum secret detectado"
    fi
else
    echo -e "  ${YELLOW}[SKIP]${NC} python3 nao disponivel para verificacao de secrets"
fi

# --- 5. Script prepare-demo-screenshots-local.sh --help funciona ---
echo ""
echo "--- [5/8] Script prepare-demo-screenshots-local.sh --help ---"
if [ -f "${SCRIPT_DIR}/prepare-demo-screenshots-local.sh" ]; then
    if bash "${SCRIPT_DIR}/prepare-demo-screenshots-local.sh" --help >/dev/null 2>&1; then
        echo -e "  ${GREEN}[OK]${NC} --help funciona"
    else
        echo -e "  ${RED}[FALHA]${NC} --help falhou"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "  ${RED}[FALTA]${NC} Script nao encontrado"
    ERRORS=$((ERRORS + 1))
fi

# --- 6. artifacts/demo-screenshots esta no .gitignore ---
echo ""
echo "--- [6/8] Gitignore para artifacts/demo-screenshots ---"
if [ -f ".gitignore" ]; then
    if grep -qE "artifacts/demo-screenshots" .gitignore 2>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} artifacts/demo-screenshots/ esta no .gitignore"
    else
        echo -e "  ${YELLOW}[AVISO]${NC} artifacts/demo-screenshots/ NAO esta no .gitignore"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "  ${YELLOW}[AVISO]${NC} .gitignore nao encontrado"
    WARNINGS=$((WARNINGS + 1))
fi

# --- 7. Placeholders nao contem dados sensiveis ---
echo ""
echo "--- [7/8] Placeholders sem dados sensiveis ---"
if [ -d "${BASE_DIR}/placeholders" ]; then
    SENSITIVE=0
    for f in "${BASE_DIR}"/placeholders/*; do
        [ -f "$f" ] || continue
        if grep -qiE '(real.client|patient_name|true.tax.id|secret_token|admin_token|sk-[a-zA-Z0-9]{20,})' "$f" 2>/dev/null; then
            echo -e "  ${RED}[SENSITIVE]${NC} Dado sensivel em $f"
            SENSITIVE=1
            ERRORS=$((ERRORS + 1))
        fi
    done
    if [ "$SENSITIVE" -eq 0 ]; then
        echo -e "  ${GREEN}[OK]${NC} Placeholders nao contem dados sensiveis"
    fi
else
    echo -e "  ${YELLOW}[AVISO]${NC} Diretorio de placeholders nao encontrado"
    WARNINGS=$((WARNINGS + 1))
fi

# --- 8. Script prepare-demo-screenshots-local.sh funciona com --help (duplicate check integrated above) ---
# (already checked in step 5)

echo ""
echo "============================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e " ${GREEN}RESULTADO: APROVADO (sem erros ou avisos)${NC}"
elif [ $ERRORS -eq 0 ] && [ $WARNINGS -gt 0 ]; then
    echo -e " ${YELLOW}RESULTADO: APROVADO COM AVISOS (${WARNINGS} avisos)${NC}"
else
    echo -e " ${RED}RESULTADO: REPROVADO (${ERRORS} erros, ${WARNINGS} avisos)${NC}"
fi
echo "============================================"
exit $ERRORS
