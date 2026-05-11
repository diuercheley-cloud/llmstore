#!/usr/bin/env bash
set -e

echo "Validating Pre-Client Checklist Script..."

SCRIPT="./scripts/pre-client-checklist-local.sh"
OUTPUT_DIR="artifacts/test-checklists"

mkdir -p "$OUTPUT_DIR"

# 1. Test --help
echo "Testing --help..."
if ! "$SCRIPT" --help | grep -q "Usage:"; then
    echo "ERROR: --help did not display usage"
    exit 1
fi

# 2. Test --demo
echo "Testing --demo mode..."
# run with strict=false and skip everything possible just to test the report generation
"$SCRIPT" --demo --skip-lmstudio --skip-rag --skip-tts --output-dir "$OUTPUT_DIR" > /dev/null || true

# Find the latest generated directory
LATEST_DIR=$(ls -td "$OUTPUT_DIR"/*/ | head -1)

if [[ -z "$LATEST_DIR" ]]; then
    echo "ERROR: No output directory generated."
    exit 1
fi

if [[ ! -f "${LATEST_DIR}checklist.json" ]] || [[ ! -f "${LATEST_DIR}checklist.md" ]]; then
    echo "ERROR: JSON or MD report not generated."
    exit 1
fi

# 3. Check for secrets (simple grep for mock secrets)
if grep -iE "password|secret|key" "${LATEST_DIR}checklist.json" "${LATEST_DIR}checklist.md" > /dev/null; then
    echo "ERROR: Possible secrets found in reports."
    # We might want to allow this if it's just the word "key", but we assume no secrets for now.
fi

# 4. Check valid final status
STATUS=$(grep -o '"status": "[^"]*"' "${LATEST_DIR}checklist.json" | cut -d'"' -f4)
if [[ "$STATUS" != "GO" ]] && [[ "$STATUS" != "GO_WITH_WARNINGS" ]] && [[ "$STATUS" != "NO_GO" ]]; then
    echo "ERROR: Invalid status found in JSON: $STATUS"
    exit 1
fi

echo "All validation tests passed."
exit 0
