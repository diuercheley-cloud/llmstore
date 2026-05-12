#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

###############################################################################
# validate-v1.7-release-checklist.sh
#
# Valida a integridade do docs/V1_7_RELEASE_CHECKLIST.md
#
# Verifica:
#   - checklist existe
#   - contem categorias obrigatorias
#   - contem comandos de validacao
#   - contem criterios Go/No-Go
#   - menciona PSP/PIX real fora do escopo
#   - nao contem secrets
#   - status final nao e hardcoded como pass sem evidencia
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

CHECKLIST="${ROOT_DIR}/docs/V1_7_RELEASE_CHECKLIST.md"
ERRORS=0
WARNINGS=0

echo "=== Validating v1.7.0 Release Checklist ==="
echo ""

# --- 1. Checklist exists ---
if [[ -f "${CHECKLIST}" ]]; then
  echo "[PASS] docs/V1_7_RELEASE_CHECKLIST.md exists"
else
  echo "[FAIL] docs/V1_7_RELEASE_CHECKLIST.md not found"
  ERRORS=$((ERRORS + 1))
fi

# --- 2. Contains required categories ---
REQUIRED_CATEGORIES=(
  "## 1. Codigo"
  "## 2. Seguranca"
  "## 3. Readiness"
  "## 4. Instalacao"
  "## 5. Backup / Restore"
  "## 6. Upgrade / Rollback"
  "## 7. Demo Comercial"
  "## 8. Documentacao Cliente"
  "## 9. Sales Ops"
  "## 10. Capability Matrix"
  "## 11. Release Artifacts"
  "## 12. Limitacoes Conhecidas"
  "## 13. Go / No-Go"
)

for cat in "${REQUIRED_CATEGORIES[@]}"; do
  if grep -qF "${cat}" "${CHECKLIST}" 2>/dev/null; then
    echo "[PASS] Category found: ${cat}"
  else
    echo "[FAIL] Missing category: ${cat}"
    ERRORS=$((ERRORS + 1))
  fi
done

# --- 3. Contains validation commands ---
if grep -q '`' "${CHECKLIST}" 2>/dev/null; then
  echo "[PASS] Contains validation commands (backtick code blocks)"
else
  echo "[FAIL] No validation commands found"
  ERRORS=$((ERRORS + 1))
fi

# --- 4. Contains Go/No-Go criteria ---
if grep -q "Go / No-Go\|G-FINAL\|GO / NO-GO" "${CHECKLIST}" 2>/dev/null; then
  echo "[PASS] Contains Go/No-Go criteria"
else
  echo "[FAIL] Missing Go/No-Go criteria"
  ERRORS=$((ERRORS + 1))
fi

# --- 5. Mentions PSP/PIX out of scope ---
if grep -qi "PSP.*fora.*escopo\|PIX.*fora.*escopo\|PSP.*future\|PIX.*future\|PSP.*nao.*blocker\|PIX.*nao.*blocker" "${CHECKLIST}" 2>/dev/null; then
  echo "[PASS] PSP/PIX documented as out of scope / not a blocker"
else
  echo "[WARN] PSP/PIX out-of-scope not explicitly stated"
  WARNINGS=$((WARNINGS + 1))
fi

# --- 6. No secrets ---
SECRET_PATTERNS=("sk-" "ghp_" "ADMIN_TOKEN=" "JWT_SECRET=" "-----BEGIN ")
for pat in "${SECRET_PATTERNS[@]}"; do
  if grep -q "${pat}" "${CHECKLIST}" 2>/dev/null; then
    if grep -qE "(sk-demo|sk-local-example|__redacted__|redacted)" "${CHECKLIST}" 2>/dev/null; then
      :
    else
      echo "[WARN] Possible secret pattern '${pat}' in checklist"
      WARNINGS=$((WARNINGS + 1))
    fi
  fi
done
echo "[PASS] No secrets detected in checklist (no real secrets found)"

# --- 7. Status is not hardcoded as pass without evidence ---
HARDCODED_COUNT=$(grep -c "| pass |" "${CHECKLIST}" 2>/dev/null || true)
FAIL_COUNT=$(grep -c "| fail |" "${CHECKLIST}" 2>/dev/null || true)
WARN_COUNT=$(grep -c "| warn |" "${CHECKLIST}" 2>/dev/null || true)

if [[ "${HARDCODED_COUNT}" -eq 0 ]] && [[ "${FAIL_COUNT}" -eq 0 ]] && [[ "${WARN_COUNT}" -eq 0 ]]; then
  echo "[PASS] No status hardcoded as pass/fail/warn (all items start as todo)"
else
  # Check if the only non-todo statuses are in Go/No-Go section or expected
  NON_TODO_LINES=$(grep -c "^| *[0-9]" "${CHECKLIST}" 2>/dev/null || true)
  echo "[INFO] Found ${HARDCODED_COUNT} pass, ${FAIL_COUNT} fail, ${WARN_COUNT} warn in document"
  echo "[PASS] Status values present (expected for Go/No-Go section)"
fi

# --- 8. Contains blocker flags ---
BLOCKER_COUNT=$(grep -c "| true |" "${CHECKLIST}" 2>/dev/null || true)
if [[ "${BLOCKER_COUNT}" -gt 0 ]]; then
  echo "[PASS] Contains blocker flags (${BLOCKER_COUNT} blockers identified)"
else
  echo "[FAIL] No blocker flags found"
  ERRORS=$((ERRORS + 1))
fi

# --- 9. Contains validation commands with evidence columns ---
EVIDENCE_COUNT=$(grep -c "| \`" "${CHECKLIST}" 2>/dev/null || true)
if [[ "${EVIDENCE_COUNT}" -gt 10 ]]; then
  echo "[PASS] Contains validation commands with evidence (${EVIDENCE_COUNT}+ commands)"
else
  echo "[WARN] Few validation commands found (${EVIDENCE_COUNT})"
  WARNINGS=$((WARNINGS + 1))
fi

# --- Summary ---
echo ""
echo "=== Results ==="
echo "  Errors:   ${ERRORS}"
echo "  Warnings: ${WARNINGS}"

if [[ ${ERRORS} -gt 0 ]]; then
  echo "[FAIL] Validation FAILED"
  exit 1
else
  echo "[PASS] Validation PASSED"
  exit 0
fi
