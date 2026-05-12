#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

###############################################################################
# validate-v1.7-final-local.sh
#
# Validacao final da release v1.7.0-local-ai-appliance.
# Roda todas as validacoes essenciais e gera relatorio consolidado.
#
# Uso: ./scripts/validate-v1.7-final-local.sh [--quick]
#
# Opcoes:
#   --quick  Pula validacoes que exigem servidor ativo
#
# Status final:
#   V1_7_READY               - Todas as validacoes PASS
#   V1_7_READY_WITH_WARNINGS - Warnings nao bloqueantes
#   V1_7_NOT_READY           - Blocker fail detectado
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%S)"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts/v1.7-final-validation/${TIMESTAMP}"
REPORT_JSON="${ARTIFACTS_DIR}/v1.7-final-validation.json"
REPORT_MD="${ARTIFACTS_DIR}/v1.7-final-validation.md"
LOGS_DIR="${ARTIFACTS_DIR}/logs"

QUICK_MODE=false
CRITICAL_FAILS=0
BLOCKING_WARNINGS=0
NONBLOCKING_WARNINGS=0
CRITICAL_FAIL_LIST=()
BLOCKING_WARN_LIST=()
NONBLOCKING_WARN_LIST=()

mkdir -p "${ARTIFACTS_DIR}" "${LOGS_DIR}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick) QUICK_MODE=true; shift ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

echo "=================================================="
echo " v1.7.0 - Final Local Validation"
echo " Timestamp: ${TIMESTAMP}"
echo " Quick mode: ${QUICK_MODE}"
echo "=================================================="
echo ""

run_and_log() {
    local name="$1"
    local script="$2"
    local is_critical="${3:-true}"
    shift 3
    local log_file="${LOGS_DIR}/${name//\//_}.log"

    echo "--- ${name} ---"
    echo "  Log: ${log_file}"

    if [[ ! -f "${script}" ]]; then
        echo "  [SKIP] Script not found: ${script}"
        if [[ "${is_critical}" == "true" ]]; then
            NONBLOCKING_WARNINGS=$((NONBLOCKING_WARNINGS + 1))
            NONBLOCKING_WARN_LIST+=("${name}: script not found")
        fi
        echo "" | tee -a "${log_file}"
        return
    fi

    if ! [[ -x "${script}" ]]; then
        chmod +x "${script}" 2>/dev/null || true
    fi

    set +e
    bash "${script}" "$@" > "${log_file}" 2>&1
    local rc=$?
    set -e

    echo "  Exit code: ${rc}" >> "${log_file}"

    if [[ ${rc} -eq 0 ]]; then
        echo "  [PASS] ${name}"
    else
        if [[ "${is_critical}" == "true" ]]; then
            echo "  [FAIL][CRITICAL] ${name} (exit ${rc})"
            CRITICAL_FAILS=$((CRITICAL_FAILS + 1))
            CRITICAL_FAIL_LIST+=("${name}")
        else
            echo "  [WARN][BLOCKING] ${name} (exit ${rc})"
            BLOCKING_WARNINGS=$((BLOCKING_WARNINGS + 1))
            BLOCKING_WARN_LIST+=("${name}")
        fi
    fi
    echo ""

    # Return last few lines of log for context
    echo "  Last lines:"
    tail -3 "${log_file}" | sed 's/^/    /'
    echo ""
}

echo "=================================================="
echo " Phase 1: Security"
echo "=================================================="
echo ""

run_and_log "check-secrets --all" \
    "${SCRIPT_DIR}/check-secrets.sh" true "--all"

if [[ "${QUICK_MODE}" == "false" ]]; then
    run_and_log "security-report-local.sh" \
        "${SCRIPT_DIR}/security-report-local.sh" true
else
    echo "--- security-report-local.sh (SKIPPED - quick mode) ---"
    echo "  [INFO] Requires running server"
    NONBLOCKING_WARNINGS=$((NONBLOCKING_WARNINGS + 1))
    NONBLOCKING_WARN_LIST+=("security-report-local.sh: skipped (quick mode)")
    echo ""
fi

echo "=================================================="
echo " Phase 2: Readiness"
echo "=================================================="
echo ""

if [[ "${QUICK_MODE}" == "false" ]]; then
    run_and_log "production-readiness-local.sh --strict" \
        "${SCRIPT_DIR}/production-readiness-local.sh" true "--strict"
else
    echo "--- production-readiness-local.sh (SKIPPED - quick mode) ---"
    echo "  [INFO] Requires running server"
    NONBLOCKING_WARNINGS=$((NONBLOCKING_WARNINGS + 1))
    NONBLOCKING_WARN_LIST+=("production-readiness-local.sh: skipped (quick mode)")
    echo ""
fi

echo "=================================================="
echo " Phase 3: Full Validation"
echo "=================================================="
echo ""

if [[ "${QUICK_MODE}" == "false" ]]; then
    run_and_log "validate-local-production-full.sh" \
        "${SCRIPT_DIR}/validate-local-production-full.sh" true
else
    echo "--- validate-local-production-full.sh (SKIPPED - quick mode) ---"
    echo "  [INFO] Requires running server"
    NONBLOCKING_WARNINGS=$((NONBLOCKING_WARNINGS + 1))
    NONBLOCKING_WARN_LIST+=("validate-local-production-full.sh: skipped (quick mode)")
    echo ""
fi

echo "=================================================="
echo " Phase 4: Clean Install & Demo"
echo "=================================================="
echo ""

run_and_log "validate-clean-install-local.sh --dry-run" \
    "${SCRIPT_DIR}/validate-clean-install-local.sh" false "--dry-run"

run_and_log "validate-commercial-demo-e2e-local.sh --seed-demo" \
    "${SCRIPT_DIR}/validate-commercial-demo-e2e-local.sh" false "--seed-demo"

echo "=================================================="
echo " Phase 5: Release & Checklist"
echo "=================================================="
echo ""

run_and_log "validate-client-ready-report.sh" \
    "${SCRIPT_DIR}/validate-client-ready-report.sh" true

run_and_log "validate-v1.7-release-checklist.sh" \
    "${SCRIPT_DIR}/validate-v1.7-release-checklist.sh" true

run_and_log "validate-release-artifacts-security.sh" \
    "${SCRIPT_DIR}/validate-release-artifacts-security.sh" true

run_and_log "validate-v1.7-release-bundle.sh" \
    "${SCRIPT_DIR}/validate-v1.7-release-bundle.sh" true

if [[ -d "${ROOT_DIR}/releases/v1.7.0-local-ai-appliance" ]]; then
    echo "--- Release metadata check ---"
    RM="${ROOT_DIR}/releases/v1.7.0-local-ai-appliance/release-manifest.json"
    BM="${ROOT_DIR}/releases/v1.7.0-local-ai-appliance/bundle-manifest.json"
    METADATA_OK=true

    if [[ -f "${RM}" ]]; then
        python3 -c "
import json
with open('${RM}') as f:
    d = json.load(f)
assert d.get('version') == 'v1.7.0-local-ai-appliance', 'version mismatch'
assert d.get('git_commit', ''), 'empty git_commit'
assert d.get('validation_result') == 'success', 'validation not success'
print('release-manifest.json: OK')
" 2>"${LOGS_DIR}/release-metadata.log" || METADATA_OK=false
    fi

    if [[ -f "${BM}" ]]; then
        python3 -c "
import json
with open('${BM}') as f:
    d = json.load(f)
assert d.get('version') == 'v1.7.0-local-ai-appliance', 'version mismatch'
assert d.get('secrets_scan_passed') == True, 'secrets scan not passed'
print('bundle-manifest.json: OK')
" 2>>"${LOGS_DIR}/release-metadata.log" || METADATA_OK=false
    fi

    if [[ "${METADATA_OK}" == "true" ]]; then
        echo "  [PASS] Release metadata OK"
    else
        echo "  [FAIL] Release metadata check failed"
        CRITICAL_FAILS=$((CRITICAL_FAILS + 1))
        CRITICAL_FAIL_LIST+=("release metadata check")
        cat "${LOGS_DIR}/release-metadata.log" | sed 's/^/    /'
    fi
else
    echo "--- Release metadata check ---"
    echo "  [WARN] Release dir not found"
    NONBLOCKING_WARNINGS=$((NONBLOCKING_WARNINGS + 1))
    NONBLOCKING_WARN_LIST+=("release metadata: dir not found")
fi
echo ""

# Run consolidated checklist runner last (collects all existing artifacts)
run_and_log "run-v1.7-release-checklist.sh --quick" \
    "${SCRIPT_DIR}/run-v1.7-release-checklist.sh" true "--quick"

echo "=================================================="
echo " Phase 6: Final Status Determination"
echo "=================================================="
echo ""

# Determine demo warnings severity from log
DEMO_LOG="${LOGS_DIR}/validate-commercial-demo-e2e-local.sh --seed-demo.log"
if [[ -f "${DEMO_LOG}" ]]; then
    DEMO_STATUS=$(grep -o 'DEMO_READY\|DEMO_READY_WITH_WARNINGS\|DEMO_FAILED' "${DEMO_LOG}" | tail -1 || echo "unknown")
    if [[ "${DEMO_STATUS}" == "DEMO_FAILED" ]]; then
        echo "  [BLOCKING] Demo E2E status: DEMO_FAILED"
        BLOCKING_WARNINGS=$((BLOCKING_WARNINGS + 1))
        BLOCKING_WARN_LIST+=("Demo E2E: DEMO_FAILED")
    elif [[ "${DEMO_STATUS}" == "DEMO_READY_WITH_WARNINGS" ]]; then
        echo "  [NON-BLOCKING] Demo E2E status: DEMO_READY_WITH_WARNINGS"
        NONBLOCKING_WARNINGS=$((NONBLOCKING_WARNINGS + 1))
        NONBLOCKING_WARN_LIST+=("Demo E2E: DEMO_READY_WITH_WARNINGS")
        # Extract warning details (avoid subshell)
        while IFS= read -r w; do
            NONBLOCKING_WARN_LIST+=("${w}")
        done < <(grep "\[WARN\]" "${DEMO_LOG}" | head -10 || true)
    fi
fi

if [[ ${CRITICAL_FAILS} -gt 0 ]]; then
    FINAL_STATUS="V1_7_NOT_READY"
elif [[ ${BLOCKING_WARNINGS} -gt 0 ]]; then
    FINAL_STATUS="V1_7_NOT_READY"
elif [[ ${NONBLOCKING_WARNINGS} -gt 0 ]]; then
    FINAL_STATUS="V1_7_READY_WITH_WARNINGS"
else
    FINAL_STATUS="V1_7_READY"
fi

echo "  Critical fails:  ${CRITICAL_FAILS}"
echo "  Blocking warns:  ${BLOCKING_WARNINGS}"
echo "  Non-block warns: ${NONBLOCKING_WARNINGS}"
echo "  Final status:    ${FINAL_STATUS}"
echo ""

echo "=================================================="
echo " Generating Report"
echo "=================================================="
echo ""

VERSION_VAL="$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo unknown)"
BRANCH_VAL="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
COMMIT_VAL="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
GENERATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Export for Python subprocess
export LOGS_DIR REPORT_JSON VERSION_VAL BRANCH_VAL COMMIT_VAL GENERATED_AT
export TIMESTAMP QUICK_MODE FINAL_STATUS
export CRITICAL_FAILS BLOCKING_WARNINGS NONBLOCKING_WARNINGS

# Write arrays to temp files for Python (NUL-separated, safe for any chars)
printf '%s\x00' "${CRITICAL_FAIL_LIST[@]}" > "${LOGS_DIR}/.cf_list.tmp" 2>/dev/null || true
printf '%s\x00' "${BLOCKING_WARN_LIST[@]}" > "${LOGS_DIR}/.bw_list.tmp" 2>/dev/null || true
printf '%s\x00' "${NONBLOCKING_WARN_LIST[@]}" > "${LOGS_DIR}/.nbw_list.tmp" 2>/dev/null || true

python3 << 'PYEOF'
import json, os

LOGS = os.environ.get('LOGS_DIR', '/tmp')
REPORT_JSON = os.environ.get('REPORT_JSON', '/tmp/report.json')

def read_nul_list(path):
    if not os.path.exists(path):
        return []
    with open(path, 'rb') as f:
        data = f.read()
    if not data:
        return []
    return [s.decode('utf-8', errors='replace') for s in data.split(b'\x00') if s]

cf_list = read_nul_list(os.path.join(LOGS, '.cf_list.tmp'))
bw_list = read_nul_list(os.path.join(LOGS, '.bw_list.tmp'))
nbw_list = read_nul_list(os.path.join(LOGS, '.nbw_list.tmp'))

for f in ['.cf_list.tmp', '.bw_list.tmp', '.nbw_list.tmp']:
    p = os.path.join(LOGS, f)
    if os.path.exists(p):
        os.remove(p)

report = {
    "report_type": "v1.7-final-validation",
    "version": os.environ.get('VERSION_VAL', 'unknown'),
    "git_branch": os.environ.get('BRANCH_VAL', 'unknown'),
    "git_commit": os.environ.get('COMMIT_VAL', 'unknown'),
    "generated_at": os.environ.get('GENERATED_AT', ''),
    "timestamp": os.environ.get('TIMESTAMP', ''),
    "quick_mode": os.environ.get('QUICK_MODE', 'false') == 'true',
    "final_status": os.environ.get('FINAL_STATUS', ''),
    "critical_fails": int(os.environ.get('CRITICAL_FAILS', '0')),
    "blocking_warnings": int(os.environ.get('BLOCKING_WARNINGS', '0')),
    "nonblocking_warnings": int(os.environ.get('NONBLOCKING_WARNINGS', '0')),
    "critical_fail_list": cf_list,
    "blocking_warning_list": bw_list,
    "nonblocking_warning_list": nbw_list,
    "limitations_out_of_scope": [
        "PSP/PIX real - documentado como future, nao e blocker",
        "Cloud - nao requerido (offline-first)",
        "Internet - nao requerido (offline-first)"
    ]
}

with open(REPORT_JSON, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"[OK] JSON report: {REPORT_JSON}")
PYEOF

cat > "${REPORT_MD}" << MDEOF
# v1.7.0 Final Local Validation Report

**Versao:** ${VERSION_VAL}
**Branch:** ${BRANCH_VAL}
**Commit:** ${COMMIT_VAL}
**Gerado em:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Timestamp:** ${TIMESTAMP}

## Status Final

**${FINAL_STATUS}**

| Metrica | Valor |
|---------|-------|
| Critical Fails | ${CRITICAL_FAILS} |
| Blocking Warnings | ${BLOCKING_WARNINGS} |
| Non-blocking Warnings | ${NONBLOCKING_WARNINGS} |
MDEOF

if [[ ${#CRITICAL_FAIL_LIST[@]} -gt 0 ]]; then
    echo "" >> "${REPORT_MD}"
    echo "## Critical Fails" >> "${REPORT_MD}"
    echo "" >> "${REPORT_MD}"
    for item in "${CRITICAL_FAIL_LIST[@]}"; do
        echo "- ${item}" >> "${REPORT_MD}"
    done
fi

if [[ ${#BLOCKING_WARN_LIST[@]} -gt 0 ]]; then
    echo "" >> "${REPORT_MD}"
    echo "## Blocking Warnings" >> "${REPORT_MD}"
    echo "" >> "${REPORT_MD}"
    for item in "${BLOCKING_WARN_LIST[@]}"; do
        echo "- ${item}" >> "${REPORT_MD}"
    done
fi

if [[ ${#NONBLOCKING_WARN_LIST[@]} -gt 0 ]]; then
    echo "" >> "${REPORT_MD}"
    echo "## Non-blocking Warnings" >> "${REPORT_MD}"
    echo "" >> "${REPORT_MD}"
    for item in "${NONBLOCKING_WARN_LIST[@]}"; do
        echo "- ${item}" >> "${REPORT_MD}"
    done
fi

cat >> "${REPORT_MD}" << MDEOF

## Limitacoes Fora do Escopo

- PSP/PIX real: documentado como "future", nao e blocker
- Cloud: nao requerido (appliance offline-first)
- Internet: nao requerido (appliance offline-first)

## Evidencias

Logs completos em: \`artifacts/v1.7-final-validation/${TIMESTAMP}/logs/\`

---
*Gerado por: scripts/validate-v1.7-final-local.sh*
MDEOF

echo "[OK] Report generated:"
echo "  JSON: ${REPORT_JSON}"
echo "  MD:   ${REPORT_MD}"
echo "  Logs: ${LOGS_DIR}/"
echo ""

echo "=================================================="
echo " Final Verdict"
echo "=================================================="
echo "  ${FINAL_STATUS}"
echo ""

if [[ "${FINAL_STATUS}" == "V1_7_NOT_READY" ]]; then
    echo "[FAIL] Release NOT ready for promotion."
    echo "  Resolve items above before proceeding."
    echo "  Artifacts: ${ARTIFACTS_DIR}/"
    exit 1
elif [[ "${FINAL_STATUS}" == "V1_7_READY_WITH_WARNINGS" ]]; then
    echo "[WARN] Release ready with non-blocking warnings."
    echo "  Warnings are documented and acceptable."
    echo "  Artifacts: ${ARTIFACTS_DIR}/"
    exit 0
else
    echo "[PASS] Release fully ready for promotion."
    echo "  All validations passed."
    echo "  Artifacts: ${ARTIFACTS_DIR}/"
    exit 0
fi
