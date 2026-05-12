#!/usr/bin/env bash
# Audit shell library layout in the repository.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  printf "[PASS] %s\n" "$1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  printf "[FAIL] %s\n" "$1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

section() {
  printf "\n=== %s ===\n" "$1"
}

section "1. Checking existence of lib/*.sh in root"
if [[ -d "${PROJECT_ROOT}/lib" ]]; then
  ROOT_LIB_FILES=$(find "${PROJECT_ROOT}/lib" -maxdepth 1 -name '*.sh' 2>/dev/null)
  if [[ -n "${ROOT_LIB_FILES}" ]]; then
    fail "lib/ in root still exists with files: $(echo "${ROOT_LIB_FILES}" | xargs -I{} basename {} | tr '\n' ' ')"
  else
    if [[ -d "${PROJECT_ROOT}/lib" ]]; then
      rmdir "${PROJECT_ROOT}/lib" 2>/dev/null && pass "Empty lib/ directory removed" || fail "lib/ is empty but could not be removed"
    fi
  fi
else
  pass "No lib/ directory in root"
fi

section "2. Checking existence of scripts/lib/*.sh"
EXPECTED_LIBS=("operator-errors.sh" "redaction.sh" "validation-logging.sh" "project-root.sh")
for lib in "${EXPECTED_LIBS[@]}"; do
  if [[ -f "${PROJECT_ROOT}/scripts/lib/${lib}" ]]; then
    pass "scripts/lib/${lib} exists"
  else
    fail "scripts/lib/${lib} is missing"
  fi
done

section "3. Checking scripts that source lib/ in root directly"
USING_ROOT_LIB=0
while IFS= read -r -d '' script; do
  if grep -qP 'source\s+.*ROOT_DIR\}/lib/' "${script}" 2>/dev/null; then
    fail "${script} references ROOT_DIR/lib/ (should be ROOT_DIR/scripts/lib/)"
    USING_ROOT_LIB=$((USING_ROOT_LIB + 1))
  fi
done < <(find "${PROJECT_ROOT}/scripts" -maxdepth 2 -name '*.sh' -type f -print0 2>/dev/null)

if [[ "${USING_ROOT_LIB}" -eq 0 ]]; then
  pass "No scripts reference lib/ in root directly"
fi

section "4. Checking scripts with fragile relative paths"
FRAGILE_COUNT=0
while IFS= read -r -d '' script; do
  if grep -qP 'source\s+\$\(dirname\s+\$0\)' "${script}" 2>/dev/null; then
    fail "${script} (uses \$(dirname \$0) instead of BASH_SOURCE)"
    FRAGILE_COUNT=$((FRAGILE_COUNT + 1))
  fi
done < <(find "${PROJECT_ROOT}/scripts" -maxdepth 2 -name '*.sh' -type f -print0 2>/dev/null)

if [[ "${FRAGILE_COUNT}" -eq 0 ]]; then
  pass "No scripts use fragile relative paths"
fi

section "5. Checking that scripts/lib/project-root.sh defines resolve_project_root"
if [[ -f "${PROJECT_ROOT}/scripts/lib/project-root.sh" ]]; then
  if grep -q 'resolve_project_root' "${PROJECT_ROOT}/scripts/lib/project-root.sh"; then
    pass "scripts/lib/project-root.sh defines resolve_project_root"
  else
    fail "scripts/lib/project-root.sh is missing resolve_project_root function"
  fi
else
  fail "scripts/lib/project-root.sh is missing"
fi

section "6. Checking for duplicate libraries"
if [[ -d "${PROJECT_ROOT}/lib" ]] && [[ -d "${PROJECT_ROOT}/scripts/lib" ]]; then
  for f in operator-errors.sh redaction.sh validation-logging.sh; do
    if [[ -f "${PROJECT_ROOT}/lib/${f}" ]] && [[ -f "${PROJECT_ROOT}/scripts/lib/${f}" ]]; then
      fail "DUPLICATE: ${f} exists in both lib/ and scripts/lib/"
    fi
  done
fi
pass "No duplicate libraries found"

section "Summary"
printf "\n%d PASS, %d FAIL out of %d checks\n" "${PASS_COUNT}" "${FAIL_COUNT}" "$((PASS_COUNT + FAIL_COUNT))"

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
  exit 1
fi
