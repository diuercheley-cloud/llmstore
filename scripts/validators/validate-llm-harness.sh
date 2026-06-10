#!/bin/bash
# scripts/validators/validate-llm-harness.sh
# CI/CD validation script for the LLM Harness module.

set -e

PYTHON=".venv/bin/python3"
PYTEST=".venv/bin/pytest"
RUFF=".venv/bin/ruff"
MYPY=".venv/bin/mypy"

echo "--- Validating LLM Harness ---"

# 0. Check prerequisites
if [ ! -f "$PYTEST" ]; then
    echo "ERROR: pytest not found at $PYTEST. Create and activate the .venv first."
    echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -e .[dev]"
    exit 1
fi

# 0b. Verify dependencies declared in pyproject.toml
echo "Checking pyproject.toml..."
if [ ! -f pyproject.toml ]; then
    echo "ERROR: pyproject.toml not found at project root"
    exit 1
fi

# 0c. Verify httpx is available (mandatory runtime dep)
echo "Checking httpx availability..."
"$PYTHON" -c "import httpx; print(f'httpx {httpx.__version__} OK')" 2>/dev/null || {
    echo "ERROR: httpx not found. Run: pip install -e ."
    exit 1
}

# 1. Check syntax
echo "Checking syntax..."
PYTHONPATH=. "$PYTHON" -m py_compile scripts/llm_harness/*.py
PYTHONPATH=. "$PYTHON" -m py_compile scripts/llm_harness/agent_harness.py

# 2. Lint with ruff (if available)
if [ -f "$RUFF" ]; then
    echo "Running ruff lint..."
    RUFF_CACHE_DIR="/tmp/ruff-cache" "$RUFF" check scripts/llm_harness/ scripts/llm_harness/agent_harness.py
else
    echo "Skipping ruff lint (not found at $RUFF)"
fi

# 2b. Type checking with mypy (if available)
if [ -f "$MYPY" ]; then
    echo "Running mypy type check..."
    "$MYPY" --config-file pyproject.toml scripts/llm_harness
else
    echo "Skipping mypy type check (not found at $MYPY)"
fi

# 3. Fix imports
echo "Fixing PYTHONPATH imports..."
PYTHONPATH=. "$PYTHON" scripts/dev/fix_imports.py

# 4. Run unit tests
echo "Running unit tests..."
PYTHONPATH=.:scripts "$PYTEST" tests/integration/llm_harness/ -v --tb=short --cov=scripts/llm_harness --cov-report=term --cov-report=xml:coverage.xml --cov-fail-under=75

# 5. Check health (local mode)
echo "Running health check..."
PYTHONPATH=. "$PYTHON" -m scripts.llm_harness.cli health --local-only

# 6. Security scan (mock)
echo "Running security scan..."
PYTHONPATH=. "$PYTHON" -m scripts.llm_harness.cli security --check-only

echo "--- LLM Harness Validation Passed ---"
