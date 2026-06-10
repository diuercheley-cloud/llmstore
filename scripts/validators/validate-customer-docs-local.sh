#!/usr/bin/env bash
set -e

echo "=> Validating Customer Local Documentation..."

# 1. Docs existem
DOCS=("docs/CUSTOMER_INSTALL_GUIDE.md" "docs/CUSTOMER_QUICKSTART.md" "docs/CUSTOMER_TROUBLESHOOTING.md" "docs/CUSTOMER_REQUIREMENTS.md")

for doc in "${DOCS[@]}"; do
    if [ ! -f "$doc" ]; then
        echo "ERROR: Document $doc missing."
        exit 1
    fi
done

# 2. Docs mencionam install-local-appliance.sh
if ! grep -q "install-local-appliance.sh" docs/CUSTOMER_INSTALL_GUIDE.md; then
    echo "ERROR: CUSTOMER_INSTALL_GUIDE.md does not mention install-local-appliance.sh"
    exit 1
fi

# 3. Docs mencionam LOCAL_APPLIANCE_MODE
if ! grep -q "LOCAL_APPLIANCE_MODE" docs/CUSTOMER_INSTALL_GUIDE.md; then
    echo "ERROR: CUSTOMER_INSTALL_GUIDE.md does not mention LOCAL_APPLIANCE_MODE"
    exit 1
fi

# 4. Docs deixam claro sem PSP/PIX real
if ! grep -qi "PIX" docs/CUSTOMER_INSTALL_GUIDE.md || ! grep -qi "PSP" docs/CUSTOMER_INSTALL_GUIDE.md; then
    echo "ERROR: CUSTOMER_INSTALL_GUIDE.md missing PSP/PIX real disclaimer."
    exit 1
fi

# 5. Docs não contêm secrets (verificação básica aqui)
if grep -q "sk-[a-zA-Z0-9]\{32,\}" docs/CUSTOMER_*.md; then
    echo "ERROR: Found potential secrets in customer docs."
    exit 1
fi

# 6. README linka os docs
if ! grep -q "CUSTOMER_INSTALL_GUIDE.md" README.md; then
    echo "ERROR: README.md does not link to CUSTOMER_INSTALL_GUIDE.md"
    exit 1
fi

echo "=> All customer local docs validated successfully."
