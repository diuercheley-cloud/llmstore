#!/usr/bin/env bash
set -euo pipefail

# Script to validate that no misleading PIX/PSP terminology is used in public-facing files.

EXIT_CODE=0

echo "Checking for misleading billing terminology..."

# Files to check
FILES_TO_CHECK=(
    "README.md"
    "control_plane/app/static/www/index.html"
    "control_plane/app/static/admin-lab/index.html"
    "docs/LOCAL_DEMO_FAQ.md"
    "docs/LOCAL_DEMO_GUIDE.md"
    "docs/LOCAL_PRODUCTION_RUNBOOK.md"
)

# Patterns that should not appear without clarification
FORBIDDEN_PATTERNS=(
    "gerar PIX"
    "QR Code PIX"
    "PSP ativo"
    "pagamento PIX real"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if [ ! -f "$file" ]; then
        continue
    fi
    
    for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
        if grep -i "$pattern" "$file" > /dev/null; then
            # Check if it's in a clarification section
            if grep -i "$pattern" "$file" | grep -vEi "fora do escopo|simulação|manual|não há|preparado para futura|sem pix real" > /dev/null; then
                echo "FAIL: Found misleading terminology '$pattern' in $file"
                grep -in "$pattern" "$file"
                EXIT_CODE=1
            fi
        fi
    done
done

# Check specifically for "Manual PIX" as a visible UI label in Admin Lab
if [ -f "control_plane/app/static/admin-lab/index.html" ]; then
    if grep ">Manual PIX<" "control_plane/app/static/admin-lab/index.html" > /dev/null; then
        echo "FAIL: Found visible label 'Manual PIX' in Admin Lab UI. Should be 'Billing Local/Manual'."
        EXIT_CODE=1
    fi
fi

# Check for the old webhook endpoint in the code
if grep -rI "/public/webhooks/pix" control_plane/app/api/ > /dev/null; then
    echo "FAIL: Found old /public/webhooks/pix endpoint in API code. Should be /public/webhooks/local-payment."
    EXIT_CODE=1
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS: All billing terminology checks passed."
else
    echo "FAILURE: Misleading billing terminology found."
fi

exit $EXIT_CODE
