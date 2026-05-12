#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

###############################################################################
# run-v1.7-release-checklist.sh
#
# Script consolidado que executa todas as validacoes essenciais da v1.7.0,
# coleta resultados existentes, gera status Go/No-Go e persiste artefatos.
#
# Uso: ./scripts/run-v1.7-release-checklist.sh [--quick]
#
# Opcoes:
#   --quick  Pula validacoes que exigem servidor ativo
#
# Regras:
#   - Falha (exit code 1) se houver blocker fail
#   - Warnings nao bloqueantes sao permitidos com justificativa
#   - Nao exige PSP/PIX real, cloud ou internet
#   - Nao commita artifacts brutos
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%S)"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts/v1.7-release-checklist/${TIMESTAMP}"
SUMMARY_JSON="${ARTIFACTS_DIR}/v1.7-checklist-status.json"
SUMMARY_MD="${ARTIFACTS_DIR}/v1.7-checklist-status.md"

QUICK_MODE=false
BLOCKER_FAILS=0
BLOCKER_WARNS=0
NONBLOCKER_WARNS=0
BLOCKER_FAIL_LIST=()
WARNING_LIST=()

mkdir -p "${ARTIFACTS_DIR}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick) QUICK_MODE=true; shift ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

echo "============================================"
echo " v1.7.0 Release Checklist - Consolidated Run"
echo " Timestamp: ${TIMESTAMP}"
echo " Quick mode: ${QUICK_MODE}"
echo "============================================"
echo ""

run_check() {
    local name="$1"
    local script="$2"
    local is_blocker="${3:-true}"
    local script_args=()

    case "$name" in
        *" --all"|*"--seed-demo"|*"--dry-run")
            local arg="${name##* }"
            script_args=("$arg")
            ;;
    esac

    echo "--- ${name} ---"

    if [[ ! -f "${script}" ]]; then
        echo "  [WARN] Script not found: ${script}"
        if [[ "${is_blocker}" == "true" ]]; then
            BLOCKER_WARNS=$((BLOCKER_WARNS + 1))
        else
            NONBLOCKER_WARNS=$((NONBLOCKER_WARNS + 1))
        fi
        WARNING_LIST+=("${name}: script not found")
        echo ""
        return
    fi

    if ! [[ -x "${script}" ]]; then
        chmod +x "${script}" 2>/dev/null || true
    fi

    set +e
    bash "${script}" "${script_args[@]}" 2>&1
    local rc=$?
    set -e

    if [[ ${rc} -eq 0 ]]; then
        echo "  [PASS] ${name}"
    else
        if [[ "${is_blocker}" == "true" ]]; then
            echo "  [FAIL][BLOCKER] ${name} (exit code ${rc})"
            BLOCKER_FAILS=$((BLOCKER_FAILS + 1))
            BLOCKER_FAIL_LIST+=("${name}")
        else
            echo "  [WARN][NON-BLOCKER] ${name} (exit code ${rc})"
            NONBLOCKER_WARNS=$((NONBLOCKER_WARNS + 1))
            WARNING_LIST+=("${name}: exit code ${rc}")
        fi
    fi
    echo ""
}

run_check_with_args() {
    local name="$1"
    local script="$2"
    local is_blocker="${3:-true}"
    shift 3
    local script_args=("$@")

    echo "--- ${name} ---"

    if [[ ! -f "${script}" ]]; then
        echo "  [SKIP] Script not found: ${script}"
        echo ""
        return
    fi

    if ! [[ -x "${script}" ]]; then
        chmod +x "${script}" 2>/dev/null || true
    fi

    set +e
    bash "${script}" "${script_args[@]}" 2>&1
    local rc=$?
    set -e

    if [[ ${rc} -eq 0 ]]; then
        echo "  [PASS] ${name}"
    else
        if [[ "${is_blocker}" == "true" ]]; then
            echo "  [FAIL][BLOCKER] ${name} (exit code ${rc})"
            BLOCKER_FAILS=$((BLOCKER_FAILS + 1))
            BLOCKER_FAIL_LIST+=("${name}")
        else
            echo "  [WARN][NON-BLOCKER] ${name} (exit code ${rc})"
            NONBLOCKER_WARNS=$((NONBLOCKER_WARNS + 1))
            WARNING_LIST+=("${name}: exit code ${rc}")
        fi
    fi
    echo ""
}

echo "============================================"
echo " Phase 1: Essential Security Validations"
echo "============================================"
echo ""

run_check_with_args "check-secrets --all" \
    "${SCRIPT_DIR}/check-secrets.sh" true "--all"

if [[ "${QUICK_MODE}" == "false" ]]; then
    run_check "security-report-local.sh" \
        "${SCRIPT_DIR}/security-report-local.sh" true

    run_check "production-readiness-local.sh" \
        "${SCRIPT_DIR}/production-readiness-local.sh" true
else
    echo "--- security-report-local.sh (SKIPPED - quick mode) ---"
    echo "  [INFO] Requires running server; skipped in quick mode"
    NONBLOCKER_WARNS=$((NONBLOCKER_WARNS + 1))
    WARNING_LIST+=("security-report-local.sh: skipped (quick mode)")
    echo ""

    echo "--- production-readiness-local.sh (SKIPPED - quick mode) ---"
    echo "  [INFO] Requires running server; skipped in quick mode"
    NONBLOCKER_WARNS=$((NONBLOCKER_WARNS + 1))
    WARNING_LIST+=("production-readiness-local.sh: skipped (quick mode)")
    echo ""
fi

echo "============================================"
echo " Phase 2: Core Release Validations"
echo "============================================"
echo ""

if [[ "${QUICK_MODE}" == "false" ]]; then
    run_check "validate-local-production-full.sh" \
        "${SCRIPT_DIR}/validate-local-production-full.sh" true
else
    echo "--- validate-local-production-full.sh (SKIPPED - quick mode) ---"
    echo "  [INFO] Requires running server; skipped in quick mode"
    NONBLOCKER_WARNS=$((NONBLOCKER_WARNS + 1))
    WARNING_LIST+=("validate-local-production-full.sh: skipped (quick mode)")
    echo ""
fi

run_check "validate-release-artifacts-security.sh" \
    "${SCRIPT_DIR}/validate-release-artifacts-security.sh" true

run_check "validate-v1.7-release-checklist.sh" \
    "${SCRIPT_DIR}/validate-v1.7-release-checklist.sh" true

run_check "generate-v1.7-release-checklist-status.sh" \
    "${SCRIPT_DIR}/generate-v1.7-release-checklist-status.sh" true

if [[ "${QUICK_MODE}" == "false" ]]; then
    run_check "validate-client-ready-report.sh" \
        "${SCRIPT_DIR}/validate-client-ready-report.sh" true
else
    echo "--- validate-client-ready-report.sh (SKIPPED - quick mode) ---"
    echo "  [INFO] Requires server reports; skipped in quick mode"
    NONBLOCKER_WARNS=$((NONBLOCKER_WARNS + 1))
    WARNING_LIST+=("validate-client-ready-report.sh: skipped (quick mode)")
    echo ""
fi

echo "============================================"
echo " Phase 3: Optional Environment Validations"
echo "============================================"
echo ""

run_check_with_args "validate-commercial-demo-e2e-local.sh --seed-demo" \
    "${SCRIPT_DIR}/validate-commercial-demo-e2e-local.sh" false "--seed-demo"

run_check_with_args "validate-clean-install-local.sh --dry-run" \
    "${SCRIPT_DIR}/validate-clean-install-local.sh" false "--dry-run"

run_check_with_args "validate-real-restore-rollback-local.sh --dry-run" \
    "${SCRIPT_DIR}/validate-real-restore-rollback-local.sh" false "--dry-run"

echo "============================================"
echo " Phase 4: Artifact Collection"
echo "============================================"
echo ""

SUMMARY_JSON_CONTENT="{
  \"report_type\": \"v1.7-consolidated-checklist\",
  \"generated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
  \"timestamp\": \"${TIMESTAMP}\",
  \"version\": \"$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo unknown)\",
  \"git_branch\": \"$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",
  \"git_commit\": \"$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)\",
  \"quick_mode\": ${QUICK_MODE},
  \"blocker_fails\": ${BLOCKER_FAILS},
  \"blocker_warns\": ${BLOCKER_WARNS},
  \"nonblocker_warns\": ${NONBLOCKER_WARNS},
  \"blocker_fail_list\": ["

for item in "${BLOCKER_FAIL_LIST[@]}"; do
    SUMMARY_JSON_CONTENT+="\"${item}\","
done
SUMMARY_JSON_CONTENT="${SUMMARY_JSON_CONTENT%,}]"
SUMMARY_JSON_CONTENT+=",
  \"warning_list\": ["
for item in "${WARNING_LIST[@]}"; do
    SUMMARY_JSON_CONTENT+="\"${item}\","
done
SUMMARY_JSON_CONTENT="${SUMMARY_JSON_CONTENT%,}]"

if [[ ${BLOCKER_FAILS} -gt 0 ]]; then
    GO_DECISION="NO_GO"
elif [[ ${BLOCKER_WARNS} -gt 0 ]] || [[ ${NONBLOCKER_WARNS} -gt 0 ]]; then
    GO_DECISION="GO_WITH_WARNINGS"
else
    GO_DECISION="GO"
fi

SUMMARY_JSON_CONTENT+=",
  \"go_decision\": \"${GO_DECISION}\",
  \"limitations_out_of_scope\": [
    \"PSP/PIX real - documentado como future\",
    \"Cloud - nao requerido (offline-first)\",
    \"Internet - nao requerido (offline-first)\"
  ]
}"

echo "${SUMMARY_JSON_CONTENT}" > "${SUMMARY_JSON}"
echo "[OK] JSON artifact: ${SUMMARY_JSON}"

VERSION_VAL="$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo unknown)"
BRANCH_VAL="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
COMMIT_VAL="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
cat > "${SUMMARY_MD}" << MDEOF
# v1.7.0 Consolidated Checklist Status

**Gerado em:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Timestamp:** ${TIMESTAMP}
**Versao:** ${VERSION_VAL}
**Branch:** ${BRANCH_VAL}
**Commit:** ${COMMIT_VAL}

## Resumo

| Metrica | Valor |
|---------|-------|
| Blocker Fails | ${BLOCKER_FAILS} |
| Blocker Warnings | ${BLOCKER_WARNS} |
| Non-blocker Warnings | ${NONBLOCKER_WARNS} |
| **Decisao** | **${GO_DECISION}** |

## Validacoes Executadas

| Fase | Validacao | Tipo | Resultado |
|------|-----------|------|-----------|
MDEOF

for item in "${BLOCKER_FAIL_LIST[@]}"; do
    echo "| ${item} | Blocker | FAIL |" >> "${SUMMARY_MD}"
done
for item in "${WARNING_LIST[@]}"; do
    echo "| ${item} | Warning | WARN |" >> "${SUMMARY_MD}"
done

cat >> "${SUMMARY_MD}" << MDEOF

## Limitacoes Fora do Escopo

- PSP/PIX real: documentado como "future", nao e blocker
- Cloud: nao requerido (appliance offline-first)
- Internet: nao requerido (appliance offline-first)

## Evidencias

Os artifacts completos estao em:
  artifacts/v1.7-release-checklist/${TIMESTAMP}/

Para detalhes, consulte:
  - \`artifacts/v1.7-release-checklist/${TIMESTAMP}/v1.7-checklist-status.json\`
  - \`docs/V1_7_RELEASE_CHECKLIST.md\`
  - \`docs/V1_7_GO_NO_GO_SUMMARY.md\`

---
*Gerado por: scripts/run-v1.7-release-checklist.sh*
MDEOF

echo "[OK] MD artifact: ${SUMMARY_MD}"

echo "============================================"
echo " Results"
echo "============================================"
echo "  Blocker fails:   ${BLOCKER_FAILS}"
echo "  Blocker warns:   ${BLOCKER_WARNS}"
echo "  Non-block warns: ${NONBLOCKER_WARNS}"
echo ""

if [[ ${#BLOCKER_FAIL_LIST[@]} -gt 0 ]]; then
    echo " Blockers:"
    for item in "${BLOCKER_FAIL_LIST[@]}"; do
        echo "   - ${item}"
    done
    echo ""
fi

if [[ ${#WARNING_LIST[@]} -gt 0 ]]; then
    echo " Warnings:"
    for item in "${WARNING_LIST[@]}"; do
        echo "   - ${item}"
    done
    echo ""
fi

if [[ ${BLOCKER_FAILS} -gt 0 ]]; then
    echo "[FAIL] BLOCKER FAILS DETECTED - Release status: NO_GO"
    echo "  Artifacts: ${ARTIFACTS_DIR}/"
    exit 1
elif [[ ${BLOCKER_WARNS} -gt 0 ]] || [[ ${NONBLOCKER_WARNS} -gt 0 ]]; then
    echo "[WARN] Warnings detected - Release status: GO_WITH_WARNINGS"
    echo "  Artifacts: ${ARTIFACTS_DIR}/"
    exit 0
else
    echo "[PASS] All validations passed - Release status: GO"
    echo "  Artifacts: ${ARTIFACTS_DIR}/"
    exit 0
fi
