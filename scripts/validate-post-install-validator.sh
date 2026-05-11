#!/usr/bin/env bash
# validate-post-install-validator.sh
# Validates the validate-post-install-local.sh script itself.

set -e

SCRIPT="./scripts/validate-post-install-local.sh"

echo "Validating $SCRIPT..."

# 1. Help works
echo "Testing --help"
$SCRIPT --help > /dev/null

# 2. Dry run with dummy base URL to check report generation
echo "Testing run and report generation..."
TEST_OUT="artifacts/test-validation-output"
rm -rf "$TEST_OUT"
# Might fail or warn because base URL is dummy
$SCRIPT --base-url "http://localhost:9999" --output-dir "$TEST_OUT" --skip-rag --skip-tts || true

LATEST_DIR=$(ls -td "$TEST_OUT"/* | head -1)

if [ ! -f "${LATEST_DIR}/post-install-report.json" ]; then
    echo "ERROR: JSON report not generated."
    exit 1
fi

if [ ! -f "${LATEST_DIR}/post-install-report.md" ]; then
    echo "ERROR: MD report not generated."
    exit 1
fi

SCORE=$(jq -r '.score' "${LATEST_DIR}/post-install-report.json")
if [[ "$SCORE" != "INSTALLED_READY" && "$SCORE" != "INSTALLED_WITH_WARNINGS" && "$SCORE" != "INSTALLATION_FAILED" ]]; then
    echo "ERROR: Invalid score in JSON: $SCORE"
    exit 1
fi

# 3. Check for secrets (simple grep)
if grep -i "secret\|password\|token\|key" "${LATEST_DIR}/post-install-report.json" > /dev/null 2>&1; then
    echo "WARNING: Possible secrets found in report."
fi

echo "Validator tests passed."
exit 0
