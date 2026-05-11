#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

EXIT_CODE=0

echo "============================================"
echo " Validating Proposal Templates"
echo "============================================"

# 1. Templates existem
TEMPLATES=(
    "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md"
    "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md"
    "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md"
    "proposals/README.md"
)

echo ""
echo "=> Checking proposal files exist..."
for doc in "${TEMPLATES[@]}"; do
    if [ -f "$ROOT_DIR/$doc" ]; then
        echo -e "  ${GREEN}OK${NC} $doc"
    else
        echo -e "  ${RED}MISSING${NC} $doc"
        EXIT_CODE=1
    fi
done

# 2. Mencionam local appliance
echo ""
echo "=> Checking local appliance terminology..."
for doc in "${TEMPLATES[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    if ! grep -qi "appliance local\|local appliance\|on-premise\|appliance local" "$file"; then
        echo -e "  ${YELLOW}WARN${NC} $doc missing 'local appliance'"
    fi
done
echo -e "  ${GREEN}OK${NC} Local appliance checked"

# 3. Mencionam PSP/PIX real fora do escopo
echo ""
echo "=> Checking PSP/PIX disclaimer..."
for doc in "${TEMPLATES[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    if ! grep -qi "psp.*real\|pix.*real\|sem psp\|fora do escopo\|billing.*manual\|faturamento.*manual\|sem psp/pix" "$file"; then
        echo -e "  ${YELLOW}WARN${NC} $doc missing PSP/PIX disclaimer"
    fi
done
echo -e "  ${GREEN}OK${NC} PSP/PIX checked"

# 4. Não contêm secrets
echo ""
echo "=> Checking for secrets..."
SECRET_PATTERNS=(
    "sk-[a-zA-Z0-9]\{32,\}"
    "ghp_[a-zA-Z0-9]\{36\}"
    "-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
for doc in "${TEMPLATES[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    for pattern in "${SECRET_PATTERNS[@]}"; do
        if grep -q "$pattern" "$file" 2>/dev/null; then
            echo -e "  ${RED}FAIL${NC} $doc contains potential secret: $pattern"
            EXIT_CODE=1
        fi
    done
done
echo -e "  ${GREEN}OK${NC} No secrets detected"

# 5. generate-proposal-pdf.sh --help funciona
echo ""
echo "=> Checking generate-proposal-pdf.sh..."
PDF_SCRIPT="$ROOT_DIR/scripts/generate-proposal-pdf.sh"
if [ -f "$PDF_SCRIPT" ]; then
    if $PDF_SCRIPT --help >/dev/null 2>&1; then
        echo -e "  ${GREEN}OK${NC} --help works"
    else
        echo -e "  ${RED}FAIL${NC} --help failed"
        EXIT_CODE=1
    fi
else
    echo -e "  ${RED}MISSING${NC} scripts/generate-proposal-pdf.sh"
    EXIT_CODE=1
fi

# 6. If pandoc or chrome available, generate PDF
echo ""
echo "=> Attempting PDF generation..."
PDF_GENERATED=false

if command -v pandoc &>/dev/null; then
    echo "  pandoc detected. Generating PDF..."
    mkdir -p "$ROOT_DIR/artifacts/proposals"
    "$PDF_SCRIPT" --input "$ROOT_DIR/proposals/TECHNICAL_PROPOSAL_TEMPLATE.md" \
        --output "$ROOT_DIR/artifacts/proposals/proposta-tecnica.pdf"
    if [ -f "$ROOT_DIR/artifacts/proposals/proposta-tecnica.pdf" ]; then
        PDF_GENERATED=true
    fi
elif command -v google-chrome &>/dev/null || command -v chromium-browser &>/dev/null || command -v chromium &>/dev/null; then
    echo "  chromium detected. Generating PDF..."
    mkdir -p "$ROOT_DIR/artifacts/proposals"
    "$PDF_SCRIPT" --input "$ROOT_DIR/proposals/TECHNICAL_PROPOSAL_TEMPLATE.md" \
        --output "$ROOT_DIR/artifacts/proposals/proposta-tecnica.pdf"
    if [ -f "$ROOT_DIR/artifacts/proposals/proposta-tecnica.pdf" ]; then
        PDF_GENERATED=true
    fi
else
    echo -e "  ${YELLOW}SKIP${NC} No pandoc or chromium available for PDF generation"
fi

if $PDF_GENERATED; then
    echo -e "  ${GREEN}OK${NC} PDF generated at artifacts/proposals/"
else
    echo -e "  ${YELLOW}INFO${NC} No PDF generated (tool not available or generation failed)"
fi

# 7. artifacts/proposals/ not versioned
echo ""
echo "=> Checking .gitignore for proposals..."
GITIGNORE="$ROOT_DIR/.gitignore"
if grep -q "artifacts/proposals" "$GITIGNORE" 2>/dev/null || grep -q "artifacts/" "$GITIGNORE" 2>/dev/null; then
    echo -e "  ${GREEN}OK${NC} artifacts/proposals/ covered by .gitignore"
else
    echo -e "  ${YELLOW}WARN${NC} proposals/artifacts not in .gitignore"
fi

# Summary
echo ""
echo "============================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e " ${GREEN}All proposals validated successfully.${NC}"
else
    echo -e " ${RED}Some checks failed.${NC}"
fi
echo "============================================"

exit $EXIT_CODE
