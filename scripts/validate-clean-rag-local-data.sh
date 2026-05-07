#!/usr/bin/env bash
# scripts/validate-clean-rag-local-data.sh - Validate RAG cleanup script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"
MODELS_DIR="${PROJECT_ROOT}/models"

echo "--- Starting Validation of clean-rag-local-data.sh ---"

# 1. Setup fake test data
TEST_CLIENT_ID="test-clean-$(date +%s)"
TEST_RAG_DIR="${DATA_DIR}/rag_uploads/${TEST_CLIENT_ID}"
mkdir -p "${TEST_RAG_DIR}"
echo "fake RAG content" > "${TEST_RAG_DIR}/doc1.txt"

DR_TEST_RAG_DIR="${DATA_DIR}/rag_uploads-drtest-fake-validation"
mkdir -p "${DR_TEST_RAG_DIR}"
echo "fake DR RAG content" > "${DR_TEST_RAG_DIR}/dr-doc.txt"

# Ensure models directory exists and has a fake .gguf for protection test
mkdir -p "${MODELS_DIR}"
touch "${MODELS_DIR}/protect-me-validation.gguf"

echo "Setup complete."

# 2. Test --dry-run
echo "Testing --dry-run..."
DRY_RUN_OUTPUT=$("${SCRIPT_DIR}/clean-rag-local-data.sh" --dry-run --client-id "${TEST_CLIENT_ID}")
echo "${DRY_RUN_OUTPUT}" | grep -q "${TEST_CLIENT_ID}" || (echo "FAIL: Dry run should list test client ID"; exit 1)

if [[ ! -d "${TEST_RAG_DIR}" ]]; then
  echo "FAIL: Dry run should NOT delete files."
  exit 1
fi
echo "PASS: Dry run safety confirmed."

# 3. Test --yes for specific client
echo "Testing --yes --client-id..."
"${SCRIPT_DIR}/clean-rag-local-data.sh" --yes --client-id "${TEST_CLIENT_ID}"

if [[ -d "${TEST_RAG_DIR}" ]]; then
  echo "FAIL: File should be deleted with --yes."
  exit 1
fi
echo "PASS: Targeted deletion confirmed."

# 4. Test protection of models/
echo "Verifying protection of models/..."
if [[ ! -f "${MODELS_DIR}/protect-me-validation.gguf" ]]; then
  echo "FAIL: models/ files were deleted!"
  exit 1
fi
# Cleanup our fake gguf
rm "${MODELS_DIR}/protect-me-validation.gguf"
echo "PASS: models/ protection confirmed."

# 5. Cleanup the rest of test data
echo "Cleaning up remaining test data..."
# The script targets rag_uploads-* automatically
"${SCRIPT_DIR}/clean-rag-local-data.sh" --yes

if [[ -d "${DR_TEST_RAG_DIR}" ]]; then
  echo "FAIL: DR test RAG dir should be deleted."
  exit 1
fi

echo "--- Validation SUCCESSFUL ---"
