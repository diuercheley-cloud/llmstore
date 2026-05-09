#!/usr/bin/env bash
set -euo pipefail

# scripts/validate-artifact-redaction-local.sh
# Validates the artifact redaction system.
# FAKE SECRET FOR TESTS ONLY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo "Creating temporary artifacts with fake tokens..."

# Create a fake JSON artifact
cat <<EOF > "${TEMP_DIR}/summary.json"
{
  "validation_result": {
    "success": true,
    "token": "sk-abc123def456ghi789jkl012mno345pqr678",
    "details": "Connected with Bearer abc123def456ghi789jkl012mno345pqr678"
  },
  "safe_value": "sk-local-example"
}
EOF

# Create a fake MD artifact
cat <<EOF > "${TEMP_DIR}/summary.md"
# Validation Summary
- Status: Success
- Token used: sk-abc123def456ghi789jkl012mno345pqr678
- Auth: Bearer abc123def456ghi789jkl012mno345pqr678
- Safe: sk-local-example
EOF

# Create a fake log
cat <<EOF > "${TEMP_DIR}/test.log"
[INFO] Starting validation
[DEBUG] ADMIN_TOKEN=admin-token-super-secret-123
[DEBUG] X-Admin-Token: admin-token-super-secret-123
EOF

echo "Running redaction in dry-run mode..."
"${SCRIPT_DIR}/redact-local-sensitive-artifacts.sh" --path "${TEMP_DIR}" --dry-run

echo "Running redaction in-place..."
"${SCRIPT_DIR}/redact-local-sensitive-artifacts.sh" --path "${TEMP_DIR}" --in-place

echo "Validating results..."

# Check JSON
if grep -q "sk-abc123def456" "${TEMP_DIR}/summary.json"; then
    echo "FAIL: Token still present in summary.json"
    exit 1
fi
if ! grep -q "\[REDACTED\]" "${TEMP_DIR}/summary.json"; then
    echo "FAIL: [REDACTED] placeholder missing in summary.json"
    exit 1
fi
if ! grep -q "sk-local-example" "${TEMP_DIR}/summary.json"; then
    echo "FAIL: Safe pattern removed from summary.json"
    exit 1
fi

# Check MD
if grep -q "sk-abc123def456" "${TEMP_DIR}/summary.md"; then
    echo "FAIL: Token still present in summary.md"
    exit 1
fi
if ! grep -q "sk-local-example" "${TEMP_DIR}/summary.md"; then
    echo "FAIL: Safe pattern removed from summary.md"
    exit 1
fi

# Check Log
if grep -q "admin-token-super-secret" "${TEMP_DIR}/test.log"; then
    echo "FAIL: ADMIN_TOKEN still present in test.log"
    exit 1
fi

# Verify JSON is still valid
python3 -c "import json; json.load(open('${TEMP_DIR}/summary.json'))" || { echo "FAIL: Invalid JSON after redaction"; exit 1; }

echo "Running check-secrets on redacted directory..."
"${SCRIPT_DIR}/check-secrets.sh" --path "${TEMP_DIR}" || { echo "FAIL: check-secrets failed on redacted artifacts"; exit 1; }

echo "--------------------------------------------------"
echo "Artifact redaction validation SUCCESSFUL"
echo "--------------------------------------------------"
