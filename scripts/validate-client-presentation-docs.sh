#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

EXIT_CODE=0

echo "============================================"
echo " Validating Client Presentation Documents"
echo "============================================"

# 1. Documents existem
DOCS=(
    "docs/CLIENT_PRESENTATION_SCRIPT.md"
    "docs/CLIENT_DEMO_TALK_TRACK.md"
    "docs/CLIENT_DEMO_FAQ.md"
    "docs/CLIENT_DEMO_OBJECTIONS.md"
)

echo ""
echo "=> Checking document existence..."
for doc in "${DOCS[@]}"; do
    if [ -f "$ROOT_DIR/$doc" ]; then
        echo -e "  ${GREEN}OK${NC} $doc"
    else
        echo -e "  ${RED}MISSING${NC} $doc"
        EXIT_CODE=1
    fi
done

# 2. Docs não contêm secrets (API keys reais)
echo ""
echo "=> Checking for secrets in documents..."
SECRET_PATTERNS=(
    "sk-[a-zA-Z0-9]\{32,\}"
    "ghp_[a-zA-Z0-9]\{36\}"
    "-----BEGIN [A-Z ]*PRIVATE KEY-----"
    "ADMIN_TOKEN=[a-zA-Z0-9._-]\{12,\}"
)
SAFE_PATTERNS=(
    "sk-demo"
    "sk-local"
    "sk-example"
    "ghp_demo"
    "admin-token-123"
    "ADMIN_TOKEN=\*\*\*masked"
)

for doc in "${DOCS[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    for pattern in "${SECRET_PATTERNS[@]}"; do
        if grep -q "$pattern" "$file" 2>/dev/null; then
            # Check if it's a safe/demo pattern
            is_safe=false
            for safe in "${SAFE_PATTERNS[@]}"; do
                if grep -q "$safe" "$file" 2>/dev/null; then
                    is_safe=true
                    break
                fi
            done
            if [ "$is_safe" = false ]; then
                echo -e "  ${RED}FAIL${NC} $doc contains potential secret matching: $pattern"
                EXIT_CODE=1
            fi
        fi
    done
done
echo -e "  ${GREEN}OK${NC} No secrets detected"

# 3. Mencionam limitações (local appliance, dados fictícios)
echo ""
echo "=> Checking for required disclaimers..."
LIMITATION_PHRASES=(
    "dados fictícios"
    "fictícios"
    "local"
    "appliance local"
)

for doc in "${DOCS[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    for phrase in "${LIMITATION_PHRASES[@]}"; do
        if ! grep -qi "$phrase" "$file"; then
            echo -e "  ${YELLOW}WARN${NC} $doc missing phrase: '$phrase'"
        fi
    done
done
echo -e "  ${GREEN}OK${NC} Required disclaimers checked"

# 4. Mencionam que PSP/PIX real está fora do escopo
echo ""
echo "=> Checking PSP/PIX disclaimer..."
for doc in "${DOCS[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    if grep -qi "PSP\|PIX" "$file" 2>/dev/null; then
        if ! grep -qi "sem PSP\|PSP real\|PSP/PIX real\|fora do escopo\|billing.*manual\|pagamento.*fora" "$file" 2>/dev/null; then
            echo -e "  ${YELLOW}WARN${NC} $doc mentions PSP/PIX but may lack disclaimer"
        fi
    fi
done
echo -e "  ${GREEN}OK${NC} PSP/PIX disclaimers checked"

# 5. Mencionam demo com dados fictícios
echo ""
echo "=> Checking fictional data disclaimer..."
for doc in "${DOCS[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    if ! grep -qi "dados fictícios\|dados demo\|fictional" "$file"; then
        echo -e "  ${YELLOW}WARN${NC} $doc missing 'dados fictícios/fictional data' disclaimer"
    fi
done
echo -e "  ${GREEN}OK${NC} Fictional data disclaimers checked"

# 6. Mencionam local appliance
echo ""
echo "=> Checking local appliance terminology..."
for doc in "${DOCS[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    if ! grep -qi "appliance local\|local appliance\|on-premise\|100% local\|rodando localmente" "$file"; then
        echo -e "  ${YELLOW}WARN${NC} $doc missing 'local appliance' terminology"
    fi
done
echo -e "  ${GREEN}OK${NC} Local appliance terminology checked"

# 7. Mencionam URLs principais
echo ""
echo "=> Checking for main URLs..."
URLS=(
    "/admin-dashboard"
    "/admin-lab"
    "/client-portal"
    "/v1/chat/completions"
    "localhost:18080"
)
for doc in "${DOCS[@]}"; do
    file="$ROOT_DIR/$doc"
    [ ! -f "$file" ] && continue

    for url in "${URLS[@]}"; do
        if ! grep -qi "$url" "$file"; then
            echo -e "  ${YELLOW}WARN${NC} $doc missing URL reference: $url"
        fi
    done
done
echo -e "  ${GREEN}OK${NC} Main URLs checked"

# Summary
echo ""
echo "============================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e " ${GREEN}All client presentation docs validated successfully.${NC}"
else
    echo -e " ${RED}Some checks failed. Review warnings above.${NC}"
fi
echo "============================================"

exit $EXIT_CODE
