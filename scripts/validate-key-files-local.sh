#!/bin/bash
# scripts/validate-key-files-local.sh
# Validates that no real .pem or .key files are present in the repo
# and that fixtures follow the security policy.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Starting Key File Policy Validation..."

# 1. List .pem and .key files (excluding .git and .venv)
echo "Checking for .pem and .key files..."
KEYS=$(find . -type f \( -name "*.pem" -o -name "*.key" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.cache/*")

EXIT_CODE=0

for KEY in $KEYS; do
    # Check if it's in the allowed location
    if [[ ! "$KEY" =~ ^\./tests/fixtures/fake_.*\.(pem|key)$ ]]; then
        echo -e "${RED}[FAIL] Unauthorized key file found: $KEY${NC}"
        EXIT_CODE=1
    else
        # Validate fixture content
        if ! grep -q "FAKE TEST KEY" "$KEY"; then
            echo -e "${RED}[FAIL] Fixture does not contain 'FAKE TEST KEY' marker: $KEY${NC}"
            EXIT_CODE=1
        else
            echo -e "${GREEN}[OK] Valid fixture: $KEY${NC}"
        fi
    fi
done

# 2. Validate .gitignore
echo "Validating .gitignore policy..."
if ! grep -q "\*.pem" .gitignore || ! grep -q "\*.key" .gitignore; then
    echo -e "${RED}[FAIL] .gitignore missing *.pem or *.key blocking patterns${NC}"
    EXIT_CODE=1
else
    echo -e "${GREEN}[OK] .gitignore contains blocking patterns${NC}"
fi

if ! grep -q "!tests/fixtures/fake_\*.pem" .gitignore || ! grep -q "!tests/fixtures/fake_\*.key" .gitignore; then
    echo -e "${RED}[FAIL] .gitignore missing exception for fake fixtures${NC}"
    EXIT_CODE=1
else
    echo -e "${GREEN}[OK] .gitignore contains fixture exceptions${NC}"
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All key file policy checks passed.${NC}"
else
    echo -e "${RED}Key file policy validation failed.${NC}"
fi

exit $EXIT_CODE
