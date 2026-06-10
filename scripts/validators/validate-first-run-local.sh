#!/usr/bin/env bash
# Validate First Run Local Setup Script
# Dry-runs and validates options for first-run-local.sh without affecting the system

set -euo pipefail

show_help() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --dry-run       Validate without affecting environment"
  echo "  --help          Show this help"
}

DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --help) show_help; exit 0 ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

echo "[TEST] Validating help output..."
./scripts/deploy/first-run-local.sh --help >/dev/null

echo "[TEST] Validating dry-run mode..."
DRY_RUN_OUT=$(./scripts/deploy/first-run-local.sh --dry-run)
if ! echo "$DRY_RUN_OUT" | grep -q "\[DRY-RUN\] Would execute"; then
  echo "Error: Dry run output is missing expected markers."
  exit 1
fi

echo "[TEST] Testing temporary directory safety..."
TEST_DIR=$(mktemp -d)
cp scripts/deploy/first-run-local.sh "$TEST_DIR/"
cp .env.example "$TEST_DIR/" 2>/dev/null || touch "$TEST_DIR/.env.example"
cd "$TEST_DIR"

echo "[TEST] Simulating environment..."
mkdir -p models
touch models/test_model.gguf
./first-run-local.sh --dry-run >/dev/null

echo "[TEST] Ensuring no secrets are leaked..."
# Since it's a bash script without a complex parser, we're relying on grep to ensure we don't accidentally print secrets
if grep -qi "secret\|token\|password" first-run-local.sh; then
  # The script itself might contain the word "token", so let's be more specific
  if grep -E 'echo ".*(ADMIN_TOKEN|\$ADMIN_TOKEN|SECRET).*"' first-run-local.sh; then
      echo "Error: Potential secret leak detected in script echo statements."
      exit 1
  fi
fi

echo "[TEST] All validation passed."
exit 0
