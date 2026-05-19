#!/bin/bash
set -e

echo "Starting Stabilization Check..."

# 1. make test
echo "==> Running make test..."
make test

# 2. make validate
echo "==> Running make validate..."
make validate

# 3. make security
echo "==> Running make security..."
make security

# 4. bash scripts/check-secrets.sh --all
echo "==> Running check-secrets.sh..."
bash scripts/check-secrets.sh --all

# 5. alembic heads check
echo "==> Checking Alembic heads..."
if [ -d "control_plane/alembic" ]; then
    cd control_plane
    HEADS=$(../.venv/bin/alembic heads | wc -l)
    if [ "$HEADS" -gt 1 ]; then
        echo "ERROR: Multiple Alembic heads detected. Please merge migrations."
        exit 1
    fi
    cd ..
else
    echo "Warning: control_plane/alembic not found, skipping alembic check."
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
PRIVATE_KEYS=$(git ls-files | grep -v "fixtures" | grep -v "tests" | xargs grep -l "BEGIN PRIVATE KEY" 2>/dev/null || true)
if [ -z "$PRIVATE_KEYS" ]; then
    echo "OK: No private keys found outside tests/fixtures."
else
    echo "ERROR: Private keys found outside test fixtures: $PRIVATE_KEYS"
    exit 1
fi

echo "Stabilization Check PASSED successfully."
