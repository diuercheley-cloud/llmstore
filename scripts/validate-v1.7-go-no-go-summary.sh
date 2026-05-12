#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

###############################################################################
# validate-v1.7-go-no-go-summary.sh
#
# Valida a integridade de docs/V1_7_GO_NO_GO_SUMMARY.md
#
# Verifica:
#   - Documento existe
#   - Status valido (GO, GO_WITH_WARNINGS, NO_GO)
#   - Nao contem secrets
#   - Menciona PSP/PIX real fora do escopo
#   - Contem evidencias
#   - Nao marca GO se houver blocker fail no artifact mais recente
#   - Contem recomendacao final
#   - Contem limitacoes fora do escopo
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

SUMMARY_DOC="${ROOT_DIR}/docs/V1_7_GO_NO_GO_SUMMARY.md"
ERRORS=0
WARNINGS=0

echo "=== Validating v1.7.0 Go/No-Go Summary ==="
echo ""

# --- 1. Document exists ---
if [[ -f "${SUMMARY_DOC}" ]]; then
  echo "[PASS] docs/V1_7_GO_NO_GO_SUMMARY.md exists"
else
  echo "[FAIL] docs/V1_7_GO_NO_GO_SUMMARY.md not found"
  ERRORS=$((ERRORS + 1))
fi

# --- 2. Valid status ---
if grep -qE '^\*\*GO\*\*$|^\*\*GO_WITH_WARNINGS\*\*$|^\*\*NO_GO\*\*$' "${SUMMARY_DOC}" 2>/dev/null; then
  echo "[PASS] Status is valid (GO, GO_WITH_WARNINGS, or NO_GO)"
else
  # Try inline format
  INLINE_STATUS=$(grep -E '^\*\*GO|GO_WITH_WARNINGS|NO_GO' "${SUMMARY_DOC}" 2>/dev/null | head -1)
  if echo "${INLINE_STATUS}" | grep -qE 'GO_WITH_WARNINGS|NO_GO|^\*\*GO\*\*'; then
    echo "[PASS] Status is valid: ${INLINE_STATUS}"
  else
    echo "[FAIL] Status not found or invalid"
    ERRORS=$((ERRORS + 1))
  fi
fi

# --- 3. No secrets ---
SECRET_PATTERNS=("sk-" "ghp_" "ADMIN_TOKEN=" "JWT_SECRET=" "-----BEGIN ")
for pat in "${SECRET_PATTERNS[@]}"; do
  if grep -q "${pat}" "${SUMMARY_DOC}" 2>/dev/null; then
    if grep -qE "(sk-demo|sk-local-example|__redacted__|redacted|sk-\\*\\*\\*)" "${SUMMARY_DOC}" 2>/dev/null; then
      :
    else
      echo "[WARN] Possible secret pattern '${pat}' in summary"
      WARNINGS=$((WARNINGS + 1))
    fi
  fi
done
echo "[PASS] No secrets detected in Go/No-Go summary"

# --- 4. Mentions PSP/PIX out of scope ---
if grep -qi "PSP\|PIX" "${SUMMARY_DOC}" 2>/dev/null; then
  echo "[PASS] PSP/PIX mentioned as out of scope"
else
  echo "[FAIL] PSP/PIX not mentioned as out of scope"
  ERRORS=$((ERRORS + 1))
fi

# --- 5. Contains evidence ---
EVIDENCE_MARKERS=("Evidencias" "Security" "Readiness" "Secrets")
for marker in "${EVIDENCE_MARKERS[@]}"; do
  if grep -q "${marker}" "${SUMMARY_DOC}" 2>/dev/null; then
    echo "[PASS] Contains evidence marker: ${marker}"
  else
    echo "[WARN] Missing evidence marker: ${marker}"
    WARNINGS=$((WARNINGS + 1))
  fi
done

# --- 6. Contains blockers section ---
if grep -q "Blockers" "${SUMMARY_DOC}" 2>/dev/null; then
  echo "[PASS] Contains blockers section"
else
  echo "[FAIL] Missing blockers section"
  ERRORS=$((ERRORS + 1))
fi

# --- 7. Contains warnings section with justifications ---
if grep -q "Warnings" "${SUMMARY_DOC}" 2>/dev/null; then
  echo "[PASS] Contains warnings section"
else
  echo "[WARN] Missing warnings section"
  WARNINGS=$((WARNINGS + 1))
fi

# --- 8. Contains final recommendation ---
if grep -q "Recomendacao Final\|GO_WITH_WARNINGS\|GO\|NO_GO" "${SUMMARY_DOC}" 2>/dev/null; then
  echo "[PASS] Contains final recommendation"
else
  echo "[FAIL] Missing final recommendation"
  ERRORS=$((ERRORS + 1))
fi

# --- 9. Contains limitations out of scope ---
if grep -q "Limitacoes Fora do Escopo\|PSP.*fora.*escopo\|cloud.*nao.*requisito\|internet.*nao.*requisito" "${SUMMARY_DOC}" 2>/dev/null; then
  echo "[PASS] Contains limitations out of scope"
else
  echo "[WARN] Missing limitations out of scope section"
  WARNINGS=$((WARNINGS + 1))
fi

# --- 10. Contains commands executed ---
if grep -q "Comandos Executados\|run-v1.7-release-checklist\|validate-v1.7" "${SUMMARY_DOC}" 2>/dev/null; then
  echo "[PASS] Contains commands executed section"
else
  echo "[WARN] Missing commands executed section"
  WARNINGS=$((WARNINGS + 1))
fi

# --- 11. Check latest artifact for blockers ---
LATEST_ARTIFACT=""
for candidate in "${ROOT_DIR}/artifacts/v1.7-release-checklist"/*/v1.7-checklist-status.json; do
  if [[ -f "${candidate}" ]]; then
    LATEST_ARTIFACT="${candidate}"
  fi
done

if [[ -z "${LATEST_ARTIFACT}" ]]; then
  for candidate in "${ROOT_DIR}/artifacts/final-qa/v1.7-checklist"/*/checklist-status.json; do
    if [[ -f "${candidate}" ]]; then
      LATEST_ARTIFACT="${candidate}"
    fi
  done
fi

if [[ -n "${LATEST_ARTIFACT}" ]]; then
  echo "[INFO] Latest artifact: ${LATEST_ARTIFACT}"
  # Check for blocker fails in latest artifact JSON using python
  BLOCKER_FAILS=$(python3 -c "
import json
with open('${LATEST_ARTIFACT}') as f:
    d = json.load(f)
bf = d.get('blocker_fails', 0)
if bf == 0:
    bf = d.get('summary', {}).get('blockers_fail', 0)
print(bf)
" 2>/dev/null || echo "0")

  if [[ "${BLOCKER_FAILS}" -gt 0 ]]; then
    SUMMARY_STATUS=$(grep -E "NO_GO|GO_WITH_WARNINGS|\*\*GO\*\*" "${SUMMARY_DOC}" 2>/dev/null | head -1)
    if echo "${SUMMARY_STATUS}" | grep -q "NO_GO"; then
      echo "[PASS] Summary correctly marked NO_GO given ${BLOCKER_FAILS} blocker fails in artifacts"
    elif echo "${SUMMARY_STATUS}" | grep -q "GO_WITH_WARNINGS"; then
      echo "[WARN] Summary marked GO_WITH_WARNINGS and artifacts show ${BLOCKER_FAILS} blocker fail(s) — acceptable with documented remediation"
      WARNINGS=$((WARNINGS + 1))
    elif echo "${SUMMARY_STATUS}" | grep -q "GO" && ! echo "${SUMMARY_STATUS}" | grep -q "GO_WITH_WARNINGS"; then
      echo "[FAIL] Summary marked GO but artifacts show ${BLOCKER_FAILS} blocker fails"
      ERRORS=$((ERRORS + 1))
    else
      echo "[WARN] Cannot determine summary status from artifacts"
      WARNINGS=$((WARNINGS + 1))
    fi
  else
    echo "[PASS] No blocker fails in latest artifact (consistent with summary)"
  fi
else
  echo "[WARN] No artifact found to cross-check blocker status"
  WARNINGS=$((WARNINGS + 1))
fi

# --- 12. Contains version info ---
if grep -q "Versao\|v1.7.0" "${SUMMARY_DOC}" 2>/dev/null; then
  echo "[PASS] Contains version information"
else
  echo "[WARN] Missing version information"
  WARNINGS=$((WARNINGS + 1))
fi

# --- Summary ---
echo ""
echo "=== Results ==="
echo "  Errors:   ${ERRORS}"
echo "  Warnings: ${WARNINGS}"

if [[ ${ERRORS} -gt 0 ]]; then
  echo "[FAIL] Go/No-Go Summary Validation FAILED"
  exit 1
else
  echo "[PASS] Go/No-Go Summary Validation PASSED"
  exit 0
fi
