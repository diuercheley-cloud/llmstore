#!/bin/bash
# scripts/validators/check-runtime-prerequisites.sh
# Validates Python and system prerequisites for the agentic runtime

set -e

echo "Checking Agentic Runtime Prerequisites..."

# Use the project venv if it exists
if [ -f "venv/bin/python3" ]; then
    PYTHON_CMD="./venv/bin/python3"
elif [ -f ".venv/bin/python3" ]; then
    PYTHON_CMD="./.venv/bin/python3"
else
    PYTHON_CMD="python3"
fi

# 1. Python version check
MIN_PYTHON="3.10"
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

if [ "$(printf '%s\n' "$MIN_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$MIN_PYTHON" ]; then
    echo "❌ FAIL: Python $MIN_PYTHON+ required. Found $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION: PASS"

# 2. Virtual environment check
if [[ "$VIRTUAL_ENV" == "" && "$CONDA_PREFIX" == "" && "$PYTHON_CMD" == "python3" ]]; then
    echo "⚠️  WARNING: No active virtual environment detected and no local venv found."
else
    echo "✅ Runtime Environment ($PYTHON_CMD): PASS"
fi

# 3. Required Python Packages
REQUIRED_PKGS=("fastapi" "sqlalchemy" "pydantic" "alembic")
for pkg in "${REQUIRED_PKGS[@]}"; do
    if ! $PYTHON_CMD -c "import $pkg" &> /dev/null; then
        echo "❌ FAIL: Python package '$pkg' is not installed in $PYTHON_CMD."
        exit 1
    fi
done
echo "✅ Essential Python Packages: PASS"

# 4. Binary check for platform freeze
if [[ ! -x "scripts/validators/platform-freeze-check.sh" ]]; then
    echo "❌ FAIL: scripts/validators/platform-freeze-check.sh is not executable."
    exit 1
fi

echo "=========================================================="
echo "    Runtime Prerequisites: ALL PASS"
echo "=========================================================="
exit 0
