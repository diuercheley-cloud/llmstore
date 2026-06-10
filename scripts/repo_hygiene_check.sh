#!/usr/bin/env bash
# Hygiene check for the repository
set -e

echo "--- Running Repo Hygiene Check ---"

# 1. Check for prohibited files
PROHIBITED_PATTERNS=("*.pem" "*.key" "*.sqlite" "*.sqlite3" "*.db" "*.log" "node_modules/" ".venv/")
for pattern in "${PROHIBITED_PATTERNS[@]}"; do
  files=$(git ls-files --others --exclude-standard --cached | grep -E "${pattern//\*/.*}$")
  
  # Filter out explicitly allowed files
  allowed_files="config/receipts_private_key.pem|config/receipts_private_key_test.pem|tests/fixtures/fake_.*"
  files=$(echo "$files" | grep -vE "$allowed_files" || true)
  
  if [ -n "$files" ]; then
    echo "[FAIL] Prohibited files found matching pattern: $pattern"
    echo "$files"
    exit 1
  fi
done

# 2. Check for large files (> 50MB)
LARGE_FILES=$(find . -type f -size +50M -not -path '*/.*')
if [ -n "$LARGE_FILES" ]; then
  echo "[FAIL] Large files detected (> 50MB):"
  echo "$LARGE_FILES"
  exit 1
fi

echo "[PASS] Repository hygiene check passed."
