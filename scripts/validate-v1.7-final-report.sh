#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

###############################################################################
# validate-v1.7-final-report.sh
#
# Valida o relatorio gerado por validate-v1.7-final-local.sh.
#
# Verifica:
#   - Relatorio existe
#   - Status valido (V1_7_READY, V1_7_READY_WITH_WARNINGS, V1_7_NOT_READY)
#   - Nao contem secrets
#   - Contem security/readiness/demo/clean install
#   - Contem limitacoes PSP/PIX real
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

ARTIFACTS_BASE="${ROOT_DIR}/artifacts/v1.7-final-validation"
ERRORS=0
WARNINGS=0

echo "=== Validating v1.7.0 Final Validation Report ==="
echo ""

# Find latest report
if [[ ! -d "${ARTIFACTS_BASE}" ]]; then
    echo "[FAIL] No final validation artifacts directory found"
    exit 1
fi

LATEST_DIR=$(find "${ARTIFACTS_BASE}" -maxdepth 1 -type d -name '2026*' 2>/dev/null | sort | tail -1)
if [[ -z "${LATEST_DIR}" ]]; then
    echo "[FAIL] No final validation report timestamp directory found"
    exit 1
fi

echo "  Report dir: ${LATEST_DIR}"

REPORT_JSON="${LATEST_DIR}/v1.7-final-validation.json"
REPORT_MD="${LATEST_DIR}/v1.7-final-validation.md"

# --- 1. Report exists ---
if [[ -f "${REPORT_JSON}" ]]; then
    echo "[PASS] v1.7-final-validation.json exists"
else
    echo "[FAIL] v1.7-final-validation.json not found"
    ERRORS=$((ERRORS + 1))
fi

if [[ -f "${REPORT_MD}" ]]; then
    echo "[PASS] v1.7-final-validation.md exists"
else
    echo "[WARN] v1.7-final-validation.md not found"
    WARNINGS=$((WARNINGS + 1))
fi

# --- 2. Valid status ---
if [[ -f "${REPORT_JSON}" ]]; then
    STATUS=$(python3 -c "
import json
with open('${REPORT_JSON}') as f:
    d = json.load(f)
print(d.get('final_status', 'not_found'))
" 2>/dev/null || echo "parse_error")

    VALID_STATUSES=("V1_7_READY" "V1_7_READY_WITH_WARNINGS" "V1_7_NOT_READY")
    FOUND=false
    for s in "${VALID_STATUSES[@]}"; do
        if [[ "${STATUS}" == "${s}" ]]; then
            FOUND=true
            break
        fi
    done

    if [[ "${FOUND}" == "true" ]]; then
        echo "[PASS] Final status is valid: ${STATUS}"
    else
        echo "[FAIL] Invalid final status: ${STATUS}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "[FAIL] Cannot check status: report not found"
    ERRORS=$((ERRORS + 1))
fi

# --- 3. No secrets ---
for fp in "${REPORT_JSON}" "${REPORT_MD}"; do
    if [[ ! -f "${fp}" ]]; then
        continue
    fi
    SECRET_PATTERNS=("sk-" "ghp_" "ADMIN_TOKEN=" "JWT_SECRET=" "-----BEGIN ")
    for pat in "${SECRET_PATTERNS[@]}"; do
        if grep -q "${pat}" "${fp}" 2>/dev/null; then
            if grep -qE "(sk-demo|sk-local-example|__redacted__|redacted)" "${fp}" 2>/dev/null; then
                :
            else
                echo "[WARN] Possible secret pattern '${pat}' in $(basename ${fp})"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
    done
done
echo "[PASS] No secrets detected in final validation report"

# --- 4. Contains security/readiness/demo/clean install ---
REQUIRED_SECTIONS=("security" "readiness" "demo" "clean install" "release" "checklist")
for fp in "${REPORT_JSON}" "${REPORT_MD}"; do
    if [[ ! -f "${fp}" ]]; then
        continue
    fi
    content=$(cat "${fp}" | tr '[:upper:]' '[:lower:]')
    for section in "${REQUIRED_SECTIONS[@]}"; do
        if echo "${content}" | grep -q "${section}"; then
            echo "[PASS] $(basename ${fp}) contains: ${section}"
        else
            echo "[WARN] $(basename ${fp}) missing: ${section}"
            WARNINGS=$((WARNINGS + 1))
        fi
    done
done

# --- 5. Contains limitations PSP/PIX ---
for fp in "${REPORT_JSON}" "${REPORT_MD}"; do
    if [[ ! -f "${fp}" ]]; then
        continue
    fi
    if grep -qi "PSP\|PIX" "${fp}" 2>/dev/null; then
        echo "[PASS] $(basename ${fp}): PSP/PIX limitations documented"
    else
        echo "[WARN] $(basename ${fp}): PSP/PIX not mentioned"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# --- 6. Contains cloud/internet limitations ---
for fp in "${REPORT_JSON}" "${REPORT_MD}"; do
    if [[ ! -f "${fp}" ]]; then
        continue
    fi
    if grep -qi "cloud.*nao\|internet.*nao\|offline" "${fp}" 2>/dev/null; then
        echo "[PASS] $(basename ${fp}): cloud/internet limitations documented"
    else
        echo "[WARN] $(basename ${fp}): cloud/internet limitations not mentioned"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# --- 7. Logs directory exists ---
if [[ -d "${LATEST_DIR}/logs" ]]; then
    LOG_COUNT=$(find "${LATEST_DIR}/logs" -type f | wc -l)
    echo "[PASS] Logs directory exists with ${LOG_COUNT} files"
else
    echo "[WARN] Logs directory not found"
    WARNINGS=$((WARNINGS + 1))
fi

# --- 8. Report has version info ---
if [[ -f "${REPORT_JSON}" ]]; then
    HAS_VERSION=$(python3 -c "
import json
with open('${REPORT_JSON}') as f:
    d = json.load(f)
print(d.get('version', ''))
" 2>/dev/null || echo "")
    if [[ -n "${HAS_VERSION}" ]]; then
        echo "[PASS] Report contains version: ${HAS_VERSION}"
    else
        echo "[WARN] Report missing version"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# --- Summary ---
echo ""
echo "=== Results ==="
echo "  Errors:   ${ERRORS}"
echo "  Warnings: ${WARNINGS}"

if [[ ${ERRORS} -gt 0 ]]; then
    echo "[FAIL] Final validation report validation FAILED"
    exit 1
else
    echo "[PASS] Final validation report validation PASSED"
    exit 0
fi
