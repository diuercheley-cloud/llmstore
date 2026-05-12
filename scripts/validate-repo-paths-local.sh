#!/usr/bin/env bash
# Validate repository path integrity.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="${PROJECT_ROOT}/artifacts/repo-cleanup/${TIMESTAMP}"
REPORT_JSON="${REPORT_DIR}/repo-paths-report.json"
REPORT_MD="${REPORT_DIR}/repo-paths-report.md"

PASS_COUNT=0
FAIL_COUNT=0
ERRORS=()
WARNINGS=()

mkdir -p "${REPORT_DIR}"

pass()  { PASS_COUNT=$((PASS_COUNT + 1)); }
fail()  { FAIL_COUNT=$((FAIL_COUNT + 1)); ERRORS+=("$1"); }
warn()  { WARNINGS+=("$1"); }

section() { printf "\n=== %s ===\n" "$1"; }
check() {
  if "$@" &>/dev/null; then
    printf "[PASS] %s\n" "$2"
    pass
  else
    printf "[FAIL] %s\n" "$2"
    fail "$2"
  fi
}

# ---- 1. Shebang validation ----
section "1. Shebang validation"
ALL_SHELL_SCRIPTS=()
while IFS= read -r -d '' f; do ALL_SHELL_SCRIPTS+=("$f"); done < <(
  find "${PROJECT_ROOT}/scripts" -maxdepth 2 -name '*.sh' -type f -print0 2>/dev/null
)
for sh in "${ALL_SHELL_SCRIPTS[@]}"; do
  shebang=$(head -1 "$sh" 2>/dev/null)
  case "$shebang" in
    "#!/usr/bin/env bash"|"#!/bin/bash"|"#!/bin/sh")
      ;;
    "")
      warn "${sh}: empty file"
      ;;
    *)
      warn "${sh}: unusual shebang: ${shebang}"
      ;;
  esac
done
pass "Shebang validation done"

# ---- 2. Executable check ----
section "2. Executable permissions"
for sh in "${ALL_SHELL_SCRIPTS[@]}"; do
  if [[ ! -x "$sh" ]]; then
    warn "${sh} is NOT executable"
  fi
done
pass "Executable check done"

# ---- 3. source targets exist ----
section "3. Source target validation"
SOURCE_MISSING=0
for sh in "${ALL_SHELL_SCRIPTS[@]}"; do
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    # Skip lines with command substitution (dynamic paths resolved at runtime)
    [[ "$line" == *\$\(* ]] && continue
    # Skip lines sourcing bare variables (LIB_PATH, METADATA_FILE, etc.)
    if [[ "$line" =~ source[[:space:]]+\$\{ ]]; then
      local varname
      varname=$(echo "$line" | sed -n 's/.*source[[:space:]]*${\([^}]*\)}.*/\1/p')
      [[ "$varname" != "ROOT_DIR" && "$varname" != "SCRIPT_DIR" && "$varname" != "PROJECT_ROOT" && "$varname" != "script_dir" ]] && continue
    fi
    if [[ "$line" =~ source[[:space:]]+\"([^\"]+)\" ]]; then
      raw="${BASH_REMATCH[1]}"
      # Skip if raw path still has unresolvable variable at start
      [[ "$raw" == \$* && "$raw" != '${ROOT_DIR}'* && "$raw" != '${SCRIPT_DIR}'* && "$raw" != '${PROJECT_ROOT}'* && "$raw" != '${script_dir}'* ]] && continue
      resolved="$raw"
      resolved="${resolved//\$\{ROOT_DIR\}/${PROJECT_ROOT}}"
      resolved="${resolved//\$\{SCRIPT_DIR\}/${PROJECT_ROOT}/scripts}"
      resolved="${resolved//\$\{PROJECT_ROOT\}/${PROJECT_ROOT}}"
      resolved="${resolved//\$\{script_dir\}/${PROJECT_ROOT}/scripts}"
      # Remove any ../.. prefix relative to PROJECT_ROOT
      if [[ "$resolved" != /* ]]; then
        resolved="${PROJECT_ROOT}/${resolved}"
      fi
      if [[ ! -f "$resolved" ]] && [[ ! -d "$resolved" ]]; then
        # Only fail if target is in a version-controlled area
        if [[ "$resolved" == "${PROJECT_ROOT}/scripts"* ]] || [[ "$resolved" == "${PROJECT_ROOT}/lib"* ]] || [[ "$resolved" == "${PROJECT_ROOT}/control_plane"* ]]; then
          fail "source target not found: $raw (resolved: $resolved) in $sh"
          SOURCE_MISSING=$((SOURCE_MISSING + 1))
        else
          warn "optional source target not found: $raw (resolved: $resolved) in $sh"
        fi
      fi
    fi
  done < "$sh"
done
if [[ "$SOURCE_MISSING" -eq 0 ]]; then
  pass "All source targets exist"
fi

# ---- 4. Python scripts referenced in shell scripts exist ----
section "4. Python script references"
for sh in "${ALL_SHELL_SCRIPTS[@]}"; do
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ "$line" =~ python3[[:space:]]+[\"']?([a-zA-Z0-9_./-]+\.py)[\"']? ]]; then
      py_path="${BASH_REMATCH[1]}"
      if [[ "$py_path" != /* ]]; then
        full="${PROJECT_ROOT}/${py_path}"
      else
        full="$py_path"
      fi
      full="${full/#\~/${HOME}}"
      if [[ ! -f "$full" ]]; then
        fail "Python script not found: $py_path (ref in $sh)"
      fi
    fi
  done < "$sh"
done
if [[ ${#ERRORS[@]} -eq 0 || "$(printf '%s\n' "${ERRORS[@]}" | grep -c 'Python script not found')" -eq 0 ]]; then
  pass "Python script references OK"
fi

# ---- 5. Makefile references exist ----
section "5. Makefile script references"
if [[ -f "${PROJECT_ROOT}/Makefile" ]]; then
  while IFS= read -r line; do
    if [[ "$line" =~ \./scripts/([a-zA-Z0-9_.-]+\.sh) ]]; then
      sh_ref="${BASH_REMATCH[1]}"
      if [[ ! -f "${PROJECT_ROOT}/scripts/${sh_ref}" ]]; then
        fail "Makefile references missing script: scripts/${sh_ref}"
      fi
    fi
  done < "${PROJECT_ROOT}/Makefile"
fi
if [[ ${#ERRORS[@]} -eq 0 || "$(printf '%s\n' "${ERRORS[@]}" | grep -c 'Makefile')" -eq 0 ]]; then
  pass "Makefile references OK"
fi

# ---- 6. bash -n syntax check ----
section "6. Shell syntax (bash -n)"
SYNTAX_ERRORS=0
for sh in "${ALL_SHELL_SCRIPTS[@]}"; do
  if ! bash -n "$sh" 2>/dev/null; then
    fail "bash -n failed: $sh"
    SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
  fi
done
if [[ "$SYNTAX_ERRORS" -eq 0 ]]; then
  pass "All scripts pass bash -n"
fi

# ---- 7. Python compile check ----
section "7. Python compile check"
PY_FILES=$(find "${PROJECT_ROOT}/scripts" -maxdepth 1 -name '*.py' -type f 2>/dev/null)
PY_COMPILE_FAIL=0
for pyf in $PY_FILES; do
  if ! python3 -m py_compile "$pyf" 2>/dev/null; then
    fail "py_compile failed: $pyf"
    PY_COMPILE_FAIL=$((PY_COMPILE_FAIL + 1))
  fi
done
if [[ "$PY_COMPILE_FAIL" -eq 0 ]]; then
  pass "All Python files pass py_compile"
fi

# ---- 8. Examples references exist ----
section "8. Examples references"
EXAMPLES_README="${PROJECT_ROOT}/examples/README.md"
if [[ -f "$EXAMPLES_README" ]]; then
  while IFS= read -r line; do
    if [[ "$line" =~ \.\/(examples\/[a-zA-Z0-9_./-]+) ]]; then
      ref="${BASH_REMATCH[1]}"
      if [[ ! -f "${PROJECT_ROOT}/${ref}" ]]; then
        fail "examples/README.md references missing: ${ref}"
      fi
    fi
  done < "$EXAMPLES_README"
fi
pass "Examples references check done"

# ---- 9. Release bundle includes ----
section "9. Release bundle paths"
if [[ -f "${PROJECT_ROOT}/scripts/create-release-bundle.sh" ]]; then
  pass "Release bundle script exists"
fi

# ---- Summary ----
section "Summary"
TOTAL=$((PASS_COUNT + FAIL_COUNT))
printf "\n%d PASS, %d FAIL out of %d checks\n" "${PASS_COUNT}" "${FAIL_COUNT}" "${TOTAL}"

# Generate JSON report
cat > "$REPORT_JSON" <<JSONEOF
{
  "timestamp": "${TIMESTAMP}",
  "pass_count": ${PASS_COUNT},
  "fail_count": ${FAIL_COUNT},
  "total_checks": ${TOTAL},
  "errors": [$(printf '"%s",' "${ERRORS[@]}" | sed 's/,$//')],
  "warnings": [$(printf '"%s",' "${WARNINGS[@]}" | sed 's/,$//')]
}
JSONEOF

# Generate Markdown report
{
  echo "# Repo Paths Validation Report"
  echo "**Timestamp:** ${TIMESTAMP}"
  echo ""
  echo "## Summary"
  echo "- **PASS:** ${PASS_COUNT}"
  echo "- **FAIL:** ${FAIL_COUNT}"
  echo "- **Total:** ${TOTAL}"
  echo ""
  if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo "## Errors"
    for e in "${ERRORS[@]}"; do echo "- ${e}"; done
    echo ""
  fi
  if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    echo "## Warnings"
    for w in "${WARNINGS[@]}"; do echo "- ${w}"; done
    echo ""
  fi
} > "$REPORT_MD"

echo ""
echo "Report: ${REPORT_MD}"
echo "JSON:   ${REPORT_JSON}"

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
  exit 1
fi
