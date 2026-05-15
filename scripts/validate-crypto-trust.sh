#!/bin/bash
set -e

echo "============================================="
echo " Validating Cryptographic Trust Infrastructure "
echo "============================================="

# Ensure we are in the project root
if [ ! -d "control_plane" ]; then
  echo "Error: Must be run from the project root."
  exit 1
fi

echo "[1/4] Checking Models and Migrations..."
if grep -q "CommercialKMSProvider" control_plane/app/models/commercial_crypto_trust.py; then
  echo "  ✓ Models found."
else
  echo "  ✗ Models missing."
  exit 1
fi

MIGRATION_FILE=$(find control_plane/alembic/versions -name "*phase62_cryptographic_trust_*.py" | head -n 1)
if [ -n "$MIGRATION_FILE" ]; then
  echo "  ✓ Migration found: $MIGRATION_FILE"
else
  echo "  ✗ Migration missing."
  exit 1
fi

echo "[2/4] Checking Services..."
if [ -f "control_plane/app/services/security/kms_runtime.py" ] && \
   [ -f "control_plane/app/services/security/signing_service.py" ] && \
   [ -f "control_plane/app/services/security/key_rotation.py" ]; then
  echo "  ✓ Services found."
else
  echo "  ✗ Services missing."
  exit 1
fi

echo "[3/4] Running Python compilation check..."
python3 -m py_compile control_plane/app/services/security/*.py
python3 -m py_compile control_plane/app/api/commercial_crypto_admin.py
echo "  ✓ Compilation successful."

echo "[4/4] Running Unit Tests..."
cd control_plane && PYTHONPATH=. ../.venv/bin/pytest tests/test_kms_runtime.py tests/test_signing_service.py tests/test_key_rotation.py tests/test_crypto_trust_chain.py
cd ..
echo "  ✓ Unit tests passed."

echo "============================================="
echo " Cryptographic Trust Infrastructure Validated"
echo "============================================="
