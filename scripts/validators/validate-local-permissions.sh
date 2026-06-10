#!/bin/bash

# scripts/validators/validate-local-permissions.sh
# Validates file permissions for security compliance.

set -e

FAILED=0

check_executable() {
    local file=$1
    if [ -e "$file" ]; then
        if [ ! -x "$file" ]; then
            echo "[FAIL] $file should be executable"
            FAILED=1
        else
            echo "[PASS] $file is executable"
        fi
    fi
}

check_not_executable() {
    local file=$1
    if [ -e "$file" ]; then
        if [ -x "$file" ]; then
            echo "[FAIL] $file should NOT be executable"
            FAILED=1
        else
            echo "[PASS] $file is not executable"
        fi
    fi
}

check_not_world_readable() {
    local file=$1
    if [ -e "$file" ]; then
        # Check if world has any permissions
        local perm=$(stat -c "%a" "$file")
        local world_perm=${perm: -1}
        if [ "$world_perm" -ne 0 ]; then
            echo "[FAIL] $file is world-readable (perms: $perm)"
            FAILED=1
        else
            echo "[PASS] $file is not world-readable (perms: $perm)"
        fi
    fi
}

is_allowed_fake_key_fixture() {
    local file=$1
    local normalized="${file#./}"

    if [[ ! "$normalized" =~ ^tests/fixtures/fake_.*\.(pem|key)$ ]]; then
        return 1
    fi

    if grep -qF "FAKE TEST KEY - DO NOT USE" "$file" 2>/dev/null; then
        return 0
    fi

    if grep -qF "FAKE SECRET FOR TESTS ONLY" "$file" 2>/dev/null; then
        return 0
    fi

    return 1
}

echo "Validating executable scripts..."
for f in scripts/*.sh; do check_executable "$f"; done
check_executable .githooks/pre-commit
if ls examples/curl/*.sh >/dev/null 2>&1; then
    for f in examples/curl/*.sh; do check_executable "$f"; done
fi

echo "Validating non-executable documents..."
for f in docs/*.md; do check_not_executable "$f"; done
for f in *.json *.yml *.yaml *.txt; do check_not_executable "$f"; done

echo "Validating sensitive files..."
if [ -f ".env.local" ]; then
    check_not_world_readable .env.local
fi

if [ -d ".local" ]; then
    # For directory, check world permissions
    perm=$(stat -c "%a" .local)
    world_perm=${perm: -1}
    if [ "$world_perm" -ne 0 ]; then
        echo "[FAIL] .local directory is world-accessible (perms: $perm)"
        FAILED=1
    else
        echo "[PASS] .local directory is restricted (perms: $perm)"
    fi
fi

# Check for .pem or .key files
echo "Checking for sensitive keys..."
# Use a temporary file to track failures across subshell
TEMP_FAIL=$(mktemp)
find . -not -path '*/.*' \( -name "*.pem" -o -name "*.key" \) | while read -r f; do
    if [ -e "$f" ]; then
        if is_allowed_fake_key_fixture "$f"; then
            echo "[PASS] $f is an authorized fake fixture"
            continue
        fi
        # Check if world has any permissions
        perm=$(stat -c "%a" "$f")
        world_perm=${perm: -1}
        if [ "$world_perm" -ne 0 ]; then
            echo "[FAIL] $f is world-readable (perms: $perm)"
            echo "1" > "$TEMP_FAIL"
        else
            echo "[PASS] $f is not world-readable (perms: $perm)"
        fi
    fi
done

if [ -s "$TEMP_FAIL" ]; then
    FAILED=1
fi
rm "$TEMP_FAIL"

if [ "$FAILED" -ne 0 ]; then
    echo "Validation FAILED."
    exit 1
else
    echo "Validation PASSED."
    exit 0
fi
