#!/usr/bin/env bash
# Repository Hygiene Check Script
# Verifies that no unwanted files are being tracked by Git.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Running Repository Hygiene Check..."

# List of patterns that should NOT be tracked
FORBIDDEN_PATTERNS=(
    "\.bak$"
    "\.log$"
    "\.env\.local\.bak"
    "^venv/"
    "^\.venv/"
    "__pycache__/"
    "\.pytest_cache/"
    "\.ruff_cache/"
    "^dist/"
    "^build/"
    "^coverage/"
    "^htmlcov/"
)

FAILED=0

for PATTERN in "${FORBIDDEN_PATTERNS[@]}"; do
    FOUND=$(git ls-files | grep -E "$PATTERN" || true)
    if [ -n "$FOUND" ]; then
        echo -e "${RED}FAILURE: Tracked files found matching pattern '$PATTERN':${NC}"
        echo "$FOUND"
        FAILED=1
    fi
done

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}SUCCESS: Repository hygiene check passed.${NC}"
    exit 0
else
    echo -e "${RED}FAILURE: Repository hygiene check failed. Please remove the files above from Git tracking.${NC}"
    echo "Hint: git rm --cached <file>"
    exit 1
fi
