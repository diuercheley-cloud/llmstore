#!/bin/bash
set -e

echo "Starting Stabilization Check..."

# 1. make test-smoke
echo "==> Running make test-smoke..."
make test-smoke

# 2. make validate-quick
echo "==> Running make validate-quick..."
make validate-quick

# 3. make security
echo "==> Running make security..."
make security

# 4. bash scripts/validators/check-secrets.sh --all
echo "==> Running check-secrets.sh..."
bash scripts/validators/check-secrets.sh --all

# 5. alembic heads check
echo "==> Checking Alembic heads..."
if [ -x "./scripts/validators/check-alembic-integrity.sh" ]; then
    ./scripts/validators/check-alembic-integrity.sh
else
    echo "Warning: check-alembic-integrity.sh not found or not executable."
fi

# 6. .env versioned check
echo "==> Checking for versioned .env files..."
VERSIONED_ENV=$(git ls-files | grep -E "^\.env$" || true)
if [ -z "$VERSIONED_ENV" ]; then
    echo "OK: No .env versioned."
else
    echo "ERROR: .env file is versioned! This is a security risk."
    exit 1
fi

# 7. data/pki versioned check
echo "==> Checking for versioned data/pki..."
VERSIONED_PKI=$(git ls-files | grep "^data/pki/" || true)
if [ -z "$VERSIONED_PKI" ]; then
    echo "OK: No data/pki versioned."
else
    echo "ERROR: Files in data/pki/ are versioned! These should be ignored."
    exit 1
fi

# 8. private certificates outside fixtures
echo "==> Checking for private certificates outside fake fixtures..."
# Common private key headers
PATTERN="BEGIN PRIV""ATE KEY"
PRIVATE_KEYS=$(git ls-files | grep -v "fixtures" | grep -v "tests" | xargs grep -l "${PATTERN}" 2>/dev/null || true)
if [ -z "$PRIVATE_KEYS" ]; then
    echo "OK: No private keys found outside tests/fixtures."
else
    echo "ERROR: Private keys found outside test fixtures: $PRIVATE_KEYS"
    exit 1
fi

echo "Stabilization Check PASSED successfully."
