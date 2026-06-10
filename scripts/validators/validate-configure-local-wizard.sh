#!/usr/bin/env bash
# LLM Inference Stack - Validation for Configuration Wizard

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
WIZARD="${SCRIPT_DIR}/../dev/configure-local-wizard.sh"

log() {
  echo "[VALIDATION] [INFO] $1"
}

error() {
  echo "[VALIDATION] [ERROR] $1"
  exit 1
}

chmod +x "$WIZARD"

# 1. Test --help
log "Testing --help..."
"$WIZARD" --help | grep -q "Usage:" || error "--help failed"

# 2. Test --dry-run
log "Testing --dry-run..."
DRY_RUN_OUT=$("$WIZARD" --non-interactive --dry-run --base-url "http://dry-run.local")
echo "$DRY_RUN_OUT" | grep -q "http://dry-run.local" || error "--dry-run output missing base-url"
echo "$DRY_RUN_OUT" | grep -q "No changes were made." || error "--dry-run did not report no changes"

# 3. Test non-interactive mode
log "Testing non-interactive mode..."
TEST_ENV="${ROOT_DIR}/.env.local.test"
# We need to simulate the ENV_FILE for the script, but the script uses a hardcoded ENV_FILE.
# I'll create a temporary directory and run it from there if I want to be safe, 
# or just rely on the script's backup mechanism and then restore.

# Let's use a temporary directory to avoid messing with the real .env.local during validation.
TEMP_DIR=$(mktemp -d)
cp "$WIZARD" "${TEMP_DIR}/wizard.sh"
echo "0.1.0" > "${TEMP_DIR}/VERSION"
mkdir -p "${TEMP_DIR}/scripts"
mkdir -p "${TEMP_DIR}/models"
touch "${TEMP_DIR}/.env.example"

# Run wizard in temp dir
# We need to fix ROOT_DIR in the script for it to work in temp dir, 
# but the script uses SCRIPT_DIR and ROOT_DIR based on its own location.
# So I'll put it in ${TEMP_DIR}/scripts/dev/configure-local-wizard.sh

mkdir -p "${TEMP_DIR}/scripts"
cp "$WIZARD" "${TEMP_DIR}/scripts/dev/configure-local-wizard.sh"
cd "$TEMP_DIR"

log "Running wizard in $TEMP_DIR..."
./scripts/dev/configure-local-wizard.sh --non-interactive --yes --base-url "http://test.local" --gpu --enable-demo

# Check results
grep -q "BASE_URL=http://test.local" .env.local || error "BASE_URL not updated in .env.local"
grep -q "LLAMA_N_GPU_LAYERS=20" .env.local || error "GPU mode not enabled in .env.local"
grep -q "DEMO_MODE=true" .env.local || error "DEMO_MODE not enabled in .env.local"

# Check backup
ls .local/backups/env/.env.local.*.bak >/dev/null 2>&1 || log "First run, no backup expected if .env.local didn't exist."

# Create .env.local and run again to check backup
echo "OLD=TRUE" >> .env.local
./scripts/dev/configure-local-wizard.sh --non-interactive --yes --base-url "http://test2.local"
ls .local/backups/env/.env.local.*.bak >/dev/null 2>&1 || error "Backup not created"

# Check secrets masking
log "Checking secrets masking..."
SUMMARY_MD=".local/install/configuration-summary.md"
if grep -q "ADMIN_TOKEN" "$SUMMARY_MD"; then
  # Ensure it doesn't contain a long hex string (typical of my generated token)
  if grep -E "[a-f0-8]{32,}" "$SUMMARY_MD"; then
    error "Unmasked token found in summary!"
  fi
fi

# Check PSP/PIX
log "Checking PSP/PIX disabling..."
grep -q "PUBLIC_EXPOSURE=false" .env.local || error "PUBLIC_EXPOSURE should be false"
grep -q "PUBLIC_SIGNUP_ENABLED=false" .env.local || error "PUBLIC_SIGNUP_ENABLED should be false"

log "All wizard validations passed!"
rm -rf "$TEMP_DIR"
exit 0
