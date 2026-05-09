#!/usr/bin/env bash
# scripts/validate-clean-sensitive-artifacts-local.sh
# Validates the clean-sensitive-artifacts-local.sh script.
# FAKE SECRET FOR TESTS ONLY

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
CLEAN_SCRIPT="${SCRIPT_DIR}/clean-sensitive-artifacts-local.sh"

chmod +x "${CLEAN_SCRIPT}"

# Temporary test directory
TEST_DIR="${PROJECT_ROOT}/artifacts/tmp-validation-clean"
mkdir -p "${TEST_DIR}"

echo "--- STEP 1: Creating temporary artifacts ---"
FAKE_TOKEN="sk-abc123def456ghi789jkl012mno345pqr678"
FAKE_ADMIN="ADMIN_TOKEN=abc123def456ghi789jkl012mno345"

cat <<EOF > "${TEST_DIR}/test_artifact.json"
{
  "id": "test-1",
  "secret": "${FAKE_TOKEN}",
  "config": {
    "admin": "${FAKE_ADMIN}"
  }
}
EOF

cat <<EOF > "${TEST_DIR}/test_artifact.md"
# Test Artifact
This is a test artifact with a secret: ${FAKE_TOKEN}
And an admin token: ${FAKE_ADMIN}
EOF

cat <<EOF > "${TEST_DIR}/test_artifact.log"
2026-05-09 10:00:00 INFO Processing request
2026-05-09 10:00:01 DEBUG Token used: ${FAKE_TOKEN}
2026-05-09 10:00:02 ERROR Unauthorized access with ${FAKE_ADMIN}
EOF

# Create a tracked file to ensure it's NOT touched
TRACKED_FILE="${PROJECT_ROOT}/scripts/__init__.py"
if [[ ! -f "${TRACKED_FILE}" ]]; then
    touch "${TRACKED_FILE}"
fi

echo "--- STEP 2: Dry-run validation ---"
# We need to make sure our TEST_DIR is considered by the script. 
# The script currently looks at specific sections or artifacts/*
# Our TEST_DIR is in artifacts/, so it should be picked up by 'all' section if we don't use keep-last/older-than-days or if we use them loosely.

# To be sure it's picked up, let's use a subfolder name that matches a section pattern if needed, 
# or just rely on 'all' with no filters (but I added logic to avoid that if no filters are present).
# Let's use --section all --older-than-days -1 (to include everything)
"${CLEAN_SCRIPT}" --dry-run --section all --older-than-days -1 > /dev/null

if grep -q "${FAKE_TOKEN}" "${TEST_DIR}/test_artifact.json"; then
    echo "SUCCESS: Dry-run did not modify files."
else
    echo "FAILURE: Dry-run modified files!"
    exit 1
fi

echo "--- STEP 3: Redaction validation ---"
"${CLEAN_SCRIPT}" --yes --redact-instead-of-delete --section all --older-than-days -1 > /dev/null

if grep -q "\[REDACTED\]" "${TEST_DIR}/test_artifact.json" && ! grep -q "${FAKE_TOKEN}" "${TEST_DIR}/test_artifact.json"; then
    echo "SUCCESS: Redaction masked tokens."
else
    echo "FAILURE: Redaction failed to mask tokens in JSON!"
    cat "${TEST_DIR}/test_artifact.json"
    exit 1
fi

if grep -q "\[REDACTED\]" "${TEST_DIR}/test_artifact.md"; then
    echo "SUCCESS: Redaction masked tokens in MD."
else
    echo "FAILURE: Redaction failed in MD!"
    exit 1
fi

echo "--- STEP 4: Cleanup validation ---"
"${CLEAN_SCRIPT}" --yes --section all --older-than-days -1 > /dev/null

if [[ ! -f "${TEST_DIR}/test_artifact.json" ]]; then
    echo "SUCCESS: Cleanup removed artifacts."
else
    echo "FAILURE: Cleanup failed to remove artifacts!"
    ls -l "${TEST_DIR}"
    exit 1
fi

echo "--- STEP 5: Tracked file protection validation ---"
if [[ -f "${TRACKED_FILE}" ]]; then
    echo "SUCCESS: Tracked file was NOT removed."
else
    echo "FAILURE: Tracked file WAS removed!"
    exit 1
fi

# Cleanup test dir
rm -rf "${TEST_DIR}"

echo "--- ALL VALIDATIONS PASSED ---"
