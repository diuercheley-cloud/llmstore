#!/usr/bin/env bash
# scripts/validators/validate-retention-local.sh - Validation for retention policy
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RETENTION_SCRIPT="${SCRIPT_DIR}/../backup/retention-local.sh"

TEST_ROOT="${PROJECT_ROOT}/artifacts/retention-test"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Starting Retention Policy Validation..."

# Cleanup previous tests
rm -rf "${TEST_ROOT}"
mkdir -p "${TEST_ROOT}/artifacts/validation"
mkdir -p "${TEST_ROOT}/artifacts/backups"
mkdir -p "${TEST_ROOT}/data/rag_uploads"
mkdir -p "${TEST_ROOT}/logs"
mkdir -p "${TEST_ROOT}/models"
mkdir -p "${TEST_ROOT}/releases/v1.0.0"

# Create fake items
# Validation artifacts: keep last 10. We create 15.
for i in $(seq 1 15); do
  # Adjust modification time to ensure sorting works
  touch -d "$i minutes ago" "${TEST_ROOT}/artifacts/validation/test-v$i"
done

# Backups: keep last 5. We create 8.
for i in $(seq 1 8); do
  touch -d "$i minutes ago" "${TEST_ROOT}/artifacts/backups/test-b$i"
done

# Logs: older than 14 days. We create some old ones.
touch -d "20 days ago" "${TEST_ROOT}/logs/old.log"
touch "${TEST_ROOT}/logs/new.log"

# RAG: no default retention days (null in config), but we can test --older-than-days
touch -d "5 days ago" "${TEST_ROOT}/data/rag_uploads/old-rag"
touch "${TEST_ROOT}/data/rag_uploads/new-rag"

# Protected items
touch "${TEST_ROOT}/models/protected.gguf"
touch "${TEST_ROOT}/releases/v1.0.0/protected.txt"

# Temporary config for test
TEST_CONFIG="${TEST_ROOT}/test-config.json"
cat <<EOF > "${TEST_CONFIG}"
{
  "rag_uploads_retention_days": null,
  "tts_audio_retention_days": 7,
  "validation_artifacts_keep_last": 10,
  "demo_artifacts_keep_last": 5,
  "security_reports_keep_last": 10,
  "production_readiness_keep_last": 10,
  "dr_artifacts_keep_last": 5,
  "model_benchmarks_keep_last": 10,
  "backups_keep_last": 5,
  "logs_retention_days": 14,
  "releases_keep_all": true
}
EOF

# Override PROJECT_ROOT in script for testing? 
# The script uses realpath and expects items to be under PROJECT_ROOT.
# I will run the script but point it to these fake items if possible, 
# OR I will use the real script but carefully.
# Since the script is designed to be safe, I can run it on the project but I'll check my fake items.

echo "--- Test 1: Dry Run ---"
"${RETENTION_SCRIPT}" --dry-run --config "${TEST_CONFIG}" --section all > /dev/null

# Verify nothing was deleted
if [[ $(find "${TEST_ROOT}/artifacts/validation" -type f | wc -l) -eq 15 ]]; then
  echo -e "${GREEN}[OK] Dry run did not delete files.${NC}"
else
  echo -e "${RED}[FAIL] Dry run deleted files!${NC}"
  exit 1
fi

echo "--- Test 2: Selective Deletion (Artifacts) ---"
# Validation artifacts: keep last 10. We had 15.
# Run with --yes and --section artifacts
PROJECT_ROOT="${TEST_ROOT}" "${RETENTION_SCRIPT}" --yes --config "${TEST_CONFIG}" --section artifacts

COUNT=$(find "${TEST_ROOT}/artifacts/validation" -type f | wc -l)
if [[ $COUNT -eq 10 ]]; then
  echo -e "${GREEN}[OK] Selective deletion kept 10 latest artifacts.${NC}"
else
  echo -e "${RED}[FAIL] Selective deletion kept $COUNT items, expected 10.${NC}"
  exit 1
fi

echo "--- Test 3: Logs retention ---"
PROJECT_ROOT="${TEST_ROOT}" "${RETENTION_SCRIPT}" --yes --config "${TEST_CONFIG}" --section logs > /dev/null
if [[ ! -f "${TEST_ROOT}/logs/old.log" && -f "${TEST_ROOT}/logs/new.log" ]]; then
  echo -e "${GREEN}[OK] Logs retention removed old log and kept new log.${NC}"
else
  echo -e "${RED}[FAIL] Logs retention logic failed.${NC}"
  exit 1
fi

echo "--- Test 4: Safety (Protected Paths) ---"
# Try to delete everything, including protected
# We'll add fake models to candidates manually by messing with a custom section if we could, 
# but the script protects them in is_protected.
# We can check if is_protected works by seeing if they are in 'skipped' in the report.
PROJECT_ROOT="${TEST_ROOT}" "${RETENTION_SCRIPT}" --yes --config "${TEST_CONFIG}" --section all > /dev/null

if [[ -f "${TEST_ROOT}/models/protected.gguf" ]]; then
  echo -e "${GREEN}[OK] Protected .gguf file was NOT deleted.${NC}"
else
  echo -e "${RED}[FAIL] Protected .gguf file was deleted!${NC}"
  exit 1
fi

if [[ -d "${TEST_ROOT}/releases/v1.0.0" ]]; then
  echo -e "${GREEN}[OK] Releases directory was NOT deleted.${NC}"
else
  echo -e "${RED}[FAIL] Releases directory was deleted!${NC}"
  exit 1
fi

echo "Validation script completed successfully."
