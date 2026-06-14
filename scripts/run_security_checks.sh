#!/bin/bash
set -euo pipefail

# =============================================================================
# LLM Inference Stack - Security Verification Suite
# =============================================================================
# Orchestrates all security checks: static analysis, existing tests, custom audit
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="$ROOT_DIR/artifacts/security-reports/$TIMESTAMP"
EXIT_CODE=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

mkdir -p "$REPORT_DIR"

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; EXIT_CODE=1; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "  ${CYAN}[INFO]${NC} $1"; }
header() {
    local border=$(printf '%*s' 70 '' | tr ' ' '=')
    echo -e "\n${border}"
    echo -e " ${BOLD}$1${NC}"
    echo -e "${border}"
}

cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
}
trap cleanup EXIT

cd "$ROOT_DIR"

# =============================================================================
# PHASE 1: Environment Verification
# =============================================================================
header "PHASE 1: Environment Verification"

if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    info "Virtual environment activated: $VENV_DIR"
else
    warn "Virtual environment not found at $VENV_DIR - trying system Python"
fi

PYTHON=$(command -v python3 || command -v python)
info "Using Python: $($PYTHON --version 2>&1)"

PYTEST=$(command -v pytest || command -v "$VENV_DIR/bin/pytest" || echo "")
if [ -z "$PYTEST" ]; then
    fail "pytest not found - install with: pip install pytest"
fi

UV=$(command -v uv || echo "")
RUFF=$(command -v ruff || command -v "$VENV_DIR/bin/ruff" || echo "")
MYPY=$(command -v mypy || command -v "$VENV_DIR/bin/mypy" || echo "")

# =============================================================================
# PHASE 2: Static Analysis
# =============================================================================
header "PHASE 2: Static Analysis"

if [ -n "$RUFF" ]; then
    info "Running Ruff linting..."
    "$RUFF" check control_plane/ scripts/ --output-format=concise \
        > "$REPORT_DIR/ruff_report.txt" 2>&1 || true
    RUFF_ISSUES=$(wc -l < "$REPORT_DIR/ruff_report.txt")
    echo "  Ruff output: $RUFF_ISSUES issues"
else
    warn "Ruff not available - skipping lint"
fi

if [ -n "$MYPY" ]; then
    info "Running Mypy type checking..."
    "$MYPY" control_plane/ --no-error-summary \
        > "$REPORT_DIR/mypy_report.txt" 2>&1 || true
    MYPY_ISSUES=$(wc -l < "$REPORT_DIR/mypy_report.txt")
    echo "  Mypy output: $MYPY_ISSUES lines"
else
    warn "Mypy not available - skipping type check"
fi

# =============================================================================
# PHASE 3: Internal Security Review
# =============================================================================
header "PHASE 3: Internal Security Review (Static Analysis)"

if [ -d "$ROOT_DIR/tests/integration/security" ]; then
    info "Running internal security review tests..."
    PYTHONPATH="$ROOT_DIR/control_plane:$PYTHONPATH" \
        $PYTHON -m pytest "$ROOT_DIR/tests/integration/security/test_internal_security_review.py" \
        -v --tb=short 2>&1 | tee "$REPORT_DIR/internal_security_review.txt" || EXIT_CODE=1
else
    warn "tests/integration/security/ not found"
fi

# =============================================================================
# PHASE 4: Existing Security Tests
# =============================================================================
header "PHASE 4: Security Tests"

SECURITY_TEST_DIRS=(
    "tests/security/"
    "tests/integration/security/"
    "tests/audit/"
)

for test_dir in "${SECURITY_TEST_DIRS[@]}"; do
    if [ -d "$ROOT_DIR/$test_dir" ]; then
        TEST_COUNT=$(find "$ROOT_DIR/$test_dir" -name "test_*.py" 2>/dev/null | wc -l)
        if [ "$TEST_COUNT" -gt 0 ]; then
            info "Running tests in $test_dir ($TEST_COUNT files)..."
            PYTHONPATH="$ROOT_DIR/control_plane:$PYTHONPATH" \
                $PYTHON -m pytest "$ROOT_DIR/$test_dir" \
                -v --tb=short --timeout=120 -q \
                -o "asyncio_mode=auto" \
                2>&1 | tee "$REPORT_DIR/$(echo $test_dir | tr '/' '_')_results.txt" || EXIT_CODE=1
        fi
    fi
done

# Additional security-specific test files
info "Running security-marked tests..."
PYTHONPATH="$ROOT_DIR/control_plane:$PYTHONPATH" \
    $PYTHON -m pytest "$ROOT_DIR/tests/" \
    -m "security" \
    --tb=short --timeout=120 -q \
    2>&1 | tee "$REPORT_DIR/security_marked_tests.txt" || EXIT_CODE=1

# =============================================================================
# PHASE 5: Auth & RBAC Tests
# =============================================================================
header "PHASE 5: Authentication & Authorization Tests"

AUTH_TEST_FILES=(
    "tests/integration/test_api_key_authentication.py"
    "tests/integration/test_auth_service.py"
    "tests/integration/test_admin_rbac.py"
    "tests/integration/test_abuse_protection_auth.py"
    "tests/integration/test_runtime_security.py"
    "tests/integration/test_cors_security_defaults.py"
)

for test_file in "${AUTH_TEST_FILES[@]}"; do
    if [ -f "$ROOT_DIR/$test_file" ]; then
        info "Running $test_file..."
        PYTHONPATH="$ROOT_DIR/control_plane:$PYTHONPATH" \
            $PYTHON -m pytest "$ROOT_DIR/$test_file" \
            -v --tb=short --timeout=60 -q \
            2>&1 | tee "$REPORT_DIR/$(basename $test_file .py)_results.txt" || EXIT_CODE=1
    else
        warn "Test file not found: $test_file"
    fi
done

# =============================================================================
# PHASE 6: Sandbox & Policy Tests
# =============================================================================
header "PHASE 6: Sandbox & Policy Tests"

SANDBOX_TEST_FILES=(
    "tests/integration/security/test_sandbox_privilege_escalation.py"
    "tests/integration/security/test_code_sandbox_jailbreak.py"
    "tests/integration/security/test_code_interpreter_hardening.py"
    "tests/integration/security/test_agent_sandbox_escape.py"
    "tests/integration/llm_harness/security/test_sandbox_escape.py"
    "tests/integration/llm_harness/security/test_policy_offensive.py"
)

for test_file in "${SANDBOX_TEST_FILES[@]}"; do
    if [ -f "$ROOT_DIR/$test_file" ]; then
        info "Running $test_file..."
        PYTHONPATH="$ROOT_DIR/control_plane:$PYTHONPATH" \
            $PYTHON -m pytest "$ROOT_DIR/$test_file" \
            -v --tb=short --timeout=60 -q \
            2>&1 | tee "$REPORT_DIR/$(basename $test_file .py)_results.txt" || EXIT_CODE=1
    else
        warn "Test file not found: $test_file"
    fi
done

# =============================================================================
# PHASE 7: Backup & Crypto Tests
# =============================================================================
header "PHASE 7: Backup & Cryptography Tests"

CRYPTO_TEST_FILES=(
    "tests/security/test_backup_crypto.py"
    "tests/security/test_backup_redaction.py"
    "tests/security/test_path_traversal.py"
    "tests/audit/test_backup_restore_audit.py"
)

for test_file in "${CRYPTO_TEST_FILES[@]}"; do
    if [ -f "$ROOT_DIR/$test_file" ]; then
        info "Running $test_file..."
        PYTHONPATH="$ROOT_DIR/control_plane:$PYTHONPATH" \
            BACKUP_RESTORE_ENABLED=true \
            $PYTHON -m pytest "$ROOT_DIR/$test_file" \
            -v --tb=short --timeout=60 -q \
            2>&1 | tee "$REPORT_DIR/$(basename $test_file .py)_results.txt" || EXIT_CODE=1
    else
        warn "Test file not found: $test_file"
    fi
done

# =============================================================================
# PHASE 8: Agent & LLM-Specific Security Tests
# =============================================================================
header "PHASE 8: Agent / LLM Security Tests"

LLM_SEC_TEST_FILES=(
    "tests/integration/llm_harness/test_security.py"
    "tests/integration/llm_harness/test_llm_harness_security.py"
    "tests/integration/llm_harness/security/test_prompt_injection.py"
    "tests/integration/test_cache_security.py"
    "tests/control_plane/test_agent_url_security.py"
)

for test_file in "${LLM_SEC_TEST_FILES[@]}"; do
    if [ -f "$ROOT_DIR/$test_file" ]; then
        info "Running $test_file..."
        PYTHONPATH="$ROOT_DIR/control_plane:$PYTHONPATH" \
            $PYTHON -m pytest "$ROOT_DIR/$test_file" \
            -v --tb=short --timeout=60 -q \
            2>&1 | tee "$REPORT_DIR/$(basename $test_file .py)_results.txt" || EXIT_CODE=1
    else
        warn "Test file not found: $test_file"
    fi
done

# =============================================================================
# PHASE 9: Custom Security Audit
# =============================================================================
header "PHASE 9: Custom Security Audit Script"

if [ -f "$SCRIPT_DIR/security_audit.py" ]; then
    info "Running comprehensive security audit..."
    PYTHONPATH="$ROOT_DIR/control_plane:$PYTHONPATH" \
        $PYTHON "$SCRIPT_DIR/security_audit.py" 2>&1 | tee "$REPORT_DIR/security_audit.txt"
else
    fail "security_audit.py not found"
fi

# =============================================================================
# PHASE 10: Check Secrets (git-secrets style)
# =============================================================================
header "PHASE 10: Secret Scanning"

if [ -x "$ROOT_DIR/scripts/validators/check-secrets.sh" ]; then
    info "Running check-secrets.sh..."
    "$ROOT_DIR/scripts/validators/check-secrets.sh" 2>&1 | tee "$REPORT_DIR/check_secrets.txt" || EXIT_CODE=1
else
    warn "check-secrets.sh not found - scanning with grep instead"
    info "Scanning for potential secret patterns..."
    grep -rn --include="*.py" --include="*.yaml" --include="*.yml" --include="*.toml" \
        -E "(sk-local-|sk-[a-z]+-)[A-Za-z0-9_-]{24,}" \
        control_plane/ scripts/ tests/ 2>/dev/null \
        > "$REPORT_DIR/secret_scan_results.txt" || true
    SECRET_COUNT=$(wc -l < "$REPORT_DIR/secret_scan_results.txt")
    echo "  Found $SECRET_COUNT potential secrets in source"
fi

# =============================================================================
# PHASE 11: Dependency Security
# =============================================================================
header "PHASE 11: Dependency Security Check"

if [ -f "$ROOT_DIR/uv.lock" ]; then
    echo "  uv.lock found - lockfile in use"
    pass "Lockfile management active (uv)"
fi

if [ -f "$ROOT_DIR/requirements.txt" ]; then
    REQ_COUNT=$(wc -l < "$ROOT_DIR/requirements.txt")
    echo "  requirements.txt with $REQ_COUNT dependencies"
fi

# Check for known-vulnerable patterns in dependencies
info "Checking pyproject.toml for security-related dependencies..."
if [ -f "$ROOT_DIR/pyproject.toml" ]; then
    for pkg in "bandit" "safety" "semgrep"; do
        grep -q "$pkg" "$ROOT_DIR/pyproject.toml" 2>/dev/null && \
            pass "Security tool configured: $pkg" || \
            warn "Security tool not configured: $pkg"
    done
fi

# =============================================================================
# SUMMARY
# =============================================================================
header "SECURITY VERIFICATION SUMMARY"

echo "  Report directory: $REPORT_DIR"
echo "  Timestamp: $(date)"

# Count test results
TOTAL_TESTS=$(find "$REPORT_DIR" -name "*_results.txt" -exec grep -cE "(PASSED|FAILED|ERROR)" {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')
PASSED_TESTS=$(find "$REPORT_DIR" -name "*_results.txt" -exec grep -c "PASSED" {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')
FAILED_TESTS=$(find "$REPORT_DIR" -name "*_results.txt" -exec grep -cE "FAILED" {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')

if [ -n "$TOTAL_TESTS" ]; then
    echo ""
    echo "  Test Results:"
    echo "    Total:  $TOTAL_TESTS"
    echo -e "    ${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "    ${RED}Failed: $FAILED_TESTS${NC}"
fi

echo ""
if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}All security checks passed.${NC}"
else
    echo -e "  ${RED}${BOLD}Some security checks failed. Review reports in:${NC}"
    echo "    $REPORT_DIR"
fi

echo ""
echo "  Reports:"
ls -1 "$REPORT_DIR"/

exit $EXIT_CODE
