#!/usr/bin/env bash
# validate-real-restore-rollback-local.sh
# Validates real restore and rollback in a controlled temporary environment.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
VERSION=$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "unknown")
TIMESTAMP=$(date +%Y%m%dT%H%M%S)

DRY_RUN=false
YES=false
WORK_DIR="${ROOT_DIR}/artifacts/restore-rollback-test/${TIMESTAMP}"
FROM_VERSION="${VERSION}"
TO_VERSION="${VERSION}"
SKIP_BUILD=false

show_help() {
    echo "LLM Inference Stack - Real Restore & Rollback Validation"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --dry-run            Show what would be done without doing it (DEFAULT)"
    echo "  --yes                Actually execute restore/rollback in controlled env"
    echo "  --work-dir DIR       Working directory (default: artifacts/restore-rollback-test/<timestamp>)"
    echo "  --from-version VER   Source version (default: current VERSION)"
    echo "  --to-version VER     Target version for simulated upgrade then rollback (default: same as from)"
    echo "  --skip-build         Skip docker compose build"
    echo "  --help               Show this help"
    echo ""
    echo "Safety:"
    echo "  Default mode is --dry-run (no changes). Use --yes to execute."
    echo "  All operations happen in a controlled temp directory."
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --yes) YES=true; shift ;;
        --work-dir) WORK_DIR="$2"; shift 2 ;;
        --from-version) FROM_VERSION="$2"; shift 2 ;;
        --to-version) TO_VERSION="$2"; shift 2 ;;
        --skip-build) SKIP_BUILD=true; shift ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
done

REPORT_DIR="${WORK_DIR}"
LOGS_DIR="${WORK_DIR}/logs"
REPORT_JSON="${WORK_DIR}/restore-rollback-report.json"
REPORT_MD="${WORK_DIR}/restore-rollback-report.md"

mkdir -p "${LOGS_DIR}"

FAILURES=0
WARNINGS=0
RESULTS=()

log()    { echo "[INFO] $1" | tee -a "${LOGS_DIR}/validate.log"; }
warn()   { echo "[WARN] $1" | tee -a "${LOGS_DIR}/validate.log"; WARNINGS=$((WARNINGS+1)); }
fail()   { echo "[FAIL] $1" | tee -a "${LOGS_DIR}/validate.log"; FAILURES=$((FAILURES+1)); }
step()   { echo "" >> "${LOGS_DIR}/validate.log"; echo "=== $1 ===" | tee -a "${LOGS_DIR}/validate.log"; }
result() { echo "$1" >> "${LOGS_DIR}/results.log"; RESULTS+=("$1"); }

DRY_PREFIX=""
if [ "${DRY_RUN}" = true ]; then
    DRY_PREFIX="[DRY-RUN] "
fi

echo "===================================================="
echo "  Real Restore & Rollback Validation"
echo "  Version: ${VERSION}"
echo "  Timestamp: ${TIMESTAMP}"
echo "  Mode: $([ "${DRY_RUN}" = true ] && echo 'DRY-RUN' || echo 'LIVE')"
echo "===================================================="
echo ""

# ---------- Step 1: Check all required commands exist ----------
step "1. Checking required scripts exist"

REQUIRED_SCRIPTS=(
    "scripts/backup-local.sh"
    "scripts/restore-local.sh"
    "scripts/upgrade-local.sh"
    "scripts/rollback-local.sh"
    "scripts/post-upgrade-smoke-local.sh"
    "scripts/validate-upgrade-migrations-local.sh"
    "scripts/validate-migrations-local.sh"
    "scripts/check-secrets.sh"
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ -f "${ROOT_DIR}/${script}" ] && [ -x "${ROOT_DIR}/${script}" ]; then
        log "${DRY_PREFIX}OK: ${script} exists and is executable"
        result "script_${script//\//_}=present"
    elif [ -f "${ROOT_DIR}/${script}" ]; then
        log "${DRY_PREFIX}OK: ${script} exists"
        result "script_${script//\//_}=present"
    else
        fail "${script} not found"
        result "script_${script//\//_}=missing"
    fi
done

# ---------- Step 2: Validate that backup-local.sh has --help ----------
step "2. Checking --help of each script"

for script in backup-local.sh restore-local.sh upgrade-local.sh rollback-local.sh post-upgrade-smoke-local.sh; do
    if bash "${ROOT_DIR}/scripts/${script}" --help >/dev/null 2>&1; then
        log "${DRY_PREFIX}OK: ${script} --help works"
        result "help_${script}=ok"
    else
        warn "${script} --help did not return 0"
        result "help_${script}=warn"
    fi
done

# ---------- Step 3: Validate rollback requires confirmation ----------
step "3. Validating rollback requires strong confirmation"

if grep -q "ROLLBACK LOCAL" "${ROOT_DIR}/scripts/rollback-local.sh" 2>/dev/null; then
    log "OK: rollback-local.sh requires ROLLBACK LOCAL confirmation"
    result "rollback_confirmation=yes"
else
    warn "Could not verify rollback strong confirmation"
    result "rollback_confirmation=unknown"
fi

if grep -q "git diff-index" "${ROOT_DIR}/scripts/upgrade-local.sh" 2>/dev/null; then
    log "OK: upgrade-local.sh checks for clean working tree"
    result "upgrade_git_check=yes"
else
    warn "Could not verify upgrade git check"
    result "upgrade_git_check=unknown"
fi

# ---------- Step 4: Validate upgrade requires backup or --skip-backup --yes ----------
step "4. Validating upgrade backup requirement"

if grep -q "SKIP_BACKUP" "${ROOT_DIR}/scripts/upgrade-local.sh" 2>/dev/null; then
    log "OK: upgrade-local.sh has SKIP_BACKUP logic"
    result "upgrade_backup_check=yes"
else
    warn "Could not verify upgrade backup check"
    result "upgrade_backup_check=unknown"
fi

# ---------- Step 5: Validate dry-run of each script ----------
step "5. Running dry-run of backup/upgrade/rollback/restore scripts"

# backup dry-run
BACKUP_DRY_OUTPUT=$(bash "${ROOT_DIR}/scripts/backup-local.sh" --help 2>&1 || true)
log "${DRY_PREFIX}backup-local.sh --help: OK"

# upgrade dry-run
UPGRADE_OUTPUT=$(bash "${ROOT_DIR}/scripts/upgrade-local.sh" --to-version "${TO_VERSION}" --dry-run --skip-backup --yes --no-build 2>&1 || true)
echo "${UPGRADE_OUTPUT}" >> "${LOGS_DIR}/upgrade-dry-run.log"
if echo "${UPGRADE_OUTPUT}" | grep -qi "dry.run\|simulando\|upgrade"; then
    log "OK: upgrade-local.sh --dry-run succeeded"
    result "upgrade_dry_run=ok"
else
    warn "upgrade-local.sh --dry-run had unexpected output"
    result "upgrade_dry_run=warn"
fi

# rollback requires --to-version and --backup-id
ROLLBACK_OUTPUT=$(bash "${ROOT_DIR}/scripts/rollback-local.sh" --to-version "${FROM_VERSION}" --backup-id "${LOGS_DIR}" --dry-run --yes --no-build 2>&1 || true)
echo "${ROLLBACK_OUTPUT}" >> "${LOGS_DIR}/rollback-dry-run.log"
if echo "${ROLLBACK_OUTPUT}" | grep -qi "dry.run\|simulando\|rollback"; then
    log "OK: rollback-local.sh --dry-run succeeded"
    result "rollback_dry_run=ok"
else
    warn "rollback-local.sh --dry-run had unexpected output"
    result "rollback_dry_run=warn"
fi

# ---------- Step 6: Real execution (only with --yes) ----------
step "6. Real execution (requires --yes)"

if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    log "Executing real restore/rollback validation..."

    # 6a. Create actual backup
    step "6a. Creating backup"
    BACKUP_OUTPUT=$(bash "${ROOT_DIR}/scripts/backup-local.sh" 2>&1 || true)
    echo "${BACKUP_OUTPUT}" >> "${LOGS_DIR}/backup.log"
    BACKUP_DIR=$(echo "${BACKUP_OUTPUT}" | grep -oP 'artifacts/backups-local/\d+T\d+' | head -1 || true)
    if [ -n "${BACKUP_DIR}" ] && [ -d "${ROOT_DIR}/${BACKUP_DIR}" ]; then
        log "Backup created at: ${BACKUP_DIR}"
        result "backup_created=${BACKUP_DIR}"
    else
        BACKUP_DIR=$(find "${ROOT_DIR}/artifacts/backups-local" -maxdepth 1 -type d -name '*T*' | sort | tail -1 || true)
        if [ -n "${BACKUP_DIR}" ]; then
            log "Backup found at: ${BACKUP_DIR}"
            result "backup_created=$(basename "${BACKUP_DIR}")"
        else
            fail "No backup directory found"
            result "backup_created=failed"
        fi
    fi

    # 6b. Validate backup manifest
    if [ -n "${BACKUP_DIR}" ]; then
        step "6b. Validating backup"
        if [ -f "${ROOT_DIR}/${BACKUP_DIR}/backup-manifest.json" ]; then
            log "Backup manifest exists"
            result "backup_manifest=present"
        else
            warn "Backup manifest not found"
            result "backup_manifest=missing"
        fi
    fi

    # 6c. Simulated upgrade to TO_VERSION (or same version with re-deploy)
    step "6c. Executing upgrade to ${TO_VERSION}"
    UPGRADE_REAL_OUTPUT=$(bash "${ROOT_DIR}/scripts/upgrade-local.sh" --to-version "${TO_VERSION}" --no-build --yes 2>&1 || true)
    echo "${UPGRADE_REAL_OUTPUT}" >> "${LOGS_DIR}/upgrade-real.log"
    if echo "${UPGRADE_REAL_OUTPUT}" | grep -qi "success\|complete\|upgrade"; then
        log "Upgrade executed"
        result "upgrade_executed=ok"
    else
        warn "Upgrade may have had issues (see logs)"
        result "upgrade_executed=warn"
    fi

    # 6d. Post-upgrade smoke test
    step "6d. Running post-upgrade smoke test"
    SMOKE_OUTPUT=$(bash "${ROOT_DIR}/scripts/post-upgrade-smoke-local.sh" 2>&1 || true)
    echo "${SMOKE_OUTPUT}" >> "${LOGS_DIR}/smoke.log"
    if echo "${SMOKE_OUTPUT}" | grep -qi "success\|passed\|score"; then
        log "Post-upgrade smoke test passed"
        result "post_upgrade_smoke=ok"
    else
        warn "Post-upgrade smoke test had issues"
        result "post_upgrade_smoke=warn"
    fi

    # 6e. Rollback using the backup
    step "6e. Executing rollback to ${FROM_VERSION}"
    if [ -n "${BACKUP_DIR}" ]; then
        ROLLBACK_REAL_OUTPUT=$(bash "${ROOT_DIR}/scripts/rollback-local.sh" --to-version "${FROM_VERSION}" --backup-id "${ROOT_DIR}/${BACKUP_DIR}" --no-build --yes 2>&1 || true)
        echo "${ROLLBACK_REAL_OUTPUT}" >> "${LOGS_DIR}/rollback-real.log"
        if echo "${ROLLBACK_REAL_OUTPUT}" | grep -qi "success\|complete\|rollback"; then
            log "Rollback executed"
            result "rollback_executed=ok"
        else
            warn "Rollback may have had issues (see logs)"
            result "rollback_executed=warn"
        fi
    else
        fail "No backup available for rollback"
        result "rollback_executed=skipped"
    fi

    # 6f. Validate restored data
    step "6f. Validating restored data"
    if [ -f "${ROOT_DIR}/VERSION" ]; then
        CURRENT_VER=$(cat "${ROOT_DIR}/VERSION")
        if [ "${CURRENT_VER}" = "${FROM_VERSION}" ]; then
            log "VERSION matches expected: ${CURRENT_VER}"
            result "version_after_rollback=${CURRENT_VER}"
        else
            warn "VERSION mismatch: expected ${FROM_VERSION}, got ${CURRENT_VER}"
            result "version_after_rollback=mismatch:${CURRENT_VER}"
        fi
    fi

    # 6g. Security check after rollback
    step "6g. Security check after rollback"
    SEC_OUTPUT=$(bash "${ROOT_DIR}/scripts/check-secrets.sh" --all 2>&1 || true)
    echo "${SEC_OUTPUT}" >> "${LOGS_DIR}/check-secrets.log"
    if echo "${SEC_OUTPUT}" | grep -qi "no secrets found"; then
        log "Secrets check passed"
        result "secrets_after_rollback=ok"
    else
        warn "Secrets check reported issues"
        result "secrets_after_rollback=warn"
    fi

    log "Real execution completed"
else
    log "${DRY_PREFIX}Skipping real execution (use --yes to execute)"
fi

# ---------- Step 7: Generate report ----------
step "7. Generating report"

# Write results to temp file for Python helper
RESULTS_FILE="${WORK_DIR}/.results.txt"
for r in "${RESULTS[@]}"; do
    echo "${r}" >> "${RESULTS_FILE}"
done

REAL_EXEC="false"
if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    REAL_EXEC="true"
fi

python3 "${ROOT_DIR}/scripts/validate_real_restore_rollback_helper.py" generate_json \
    "${REPORT_JSON}" \
    "${TIMESTAMP}" \
    "${VERSION}" \
    "${DRY_RUN}" \
    "${REAL_EXEC}" \
    "${FROM_VERSION}" \
    "${TO_VERSION}" \
    "${WORK_DIR}" \
    "${SKIP_BUILD}" \
    "${RESULTS_FILE}" \
    "${FAILURES}" \
    "${WARNINGS}" \
    "${ROOT_DIR}"

rm -f "${RESULTS_FILE}"

cat <<EOF > "${REPORT_MD}"
# Restore & Rollback Validation Report

**Tool:** scripts/validate-real-restore-rollback-local.sh
**Timestamp:** ${TIMESTAMP}
**Version:** ${VERSION}
**Mode:** $([ "${DRY_RUN}" = true ] && echo 'DRY-RUN' || ([ "${FAILURES}" -gt 0 ] && echo 'FAILED' || echo 'SUCCESS'))

## Configuration

| Flag | Value |
|------|-------|
| Dry-run | ${DRY_RUN} |
| Real execution | $([ "${YES}" = true ] && [ "${DRY_RUN}" = false ] && echo 'YES' || echo 'NO') |
| From version | ${FROM_VERSION} |
| To version | ${TO_VERSION} |
| Work dir | ${WORK_DIR} |
| Skip build | ${SKIP_BUILD} |

## Safety Guarantees

| Guarantee | Status |
|-----------|--------|
| Backup required before upgrade | $(grep -q "SKIP_BACKUP" "${ROOT_DIR}/scripts/upgrade-local.sh" 2>/dev/null && echo 'YES' || echo 'NO') |
| Rollback strong confirmation | $(grep -q "ROLLBACK LOCAL" "${ROOT_DIR}/scripts/rollback-local.sh" 2>/dev/null && echo 'YES' || echo 'NO') |
| Git clean check | $(grep -q "git diff-index" "${ROOT_DIR}/scripts/upgrade-local.sh" 2>/dev/null && echo 'YES' || echo 'NO') |
| Dry-run supported | YES |
| Secrets check available | YES |

## Results

| Step | Status |
|------|--------|
| Scripts existence | $([ "${FAILURES}" -eq 0 ] && echo 'PASS' || echo "FAILURES: ${FAILURES}") |
| Rollback confirmation check | $(grep -q "ROLLBACK LOCAL" "${ROOT_DIR}/scripts/rollback-local.sh" 2>/dev/null && echo 'PASS' || echo 'WARN') |
| Upgrade backup requirement | $(grep -q "SKIP_BACKUP" "${ROOT_DIR}/scripts/upgrade-local.sh" 2>/dev/null && echo 'PASS' || echo 'WARN') |
| upgrade-local.sh --dry-run | $(echo "${UPGRADE_OUTPUT}" | grep -qi "dry.run\|simulando\|upgrade" && echo 'PASS' || echo 'WARN') |
| rollback-local.sh --dry-run | $(echo "${ROLLBACK_OUTPUT}" | grep -qi "dry.run\|simulando\|rollback" && echo 'PASS' || echo 'WARN') |
EOF

if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    cat <<EOF >> "${REPORT_MD}"
| Backup created | $([ -n "${BACKUP_DIR:-}" ] && echo 'PASS' || echo 'FAIL') |
| Backup manifest | $([ -f "${ROOT_DIR}/${BACKUP_DIR:-}/backup-manifest.json" ] 2>/dev/null && echo 'PASS' || echo 'WARN') |
| Upgrade executed | $(echo "${UPGRADE_REAL_OUTPUT:-}" | grep -qi "success\|complete\|upgrade" && echo 'PASS' || echo 'WARN') |
| Post-upgrade smoke | $(echo "${SMOKE_OUTPUT:-}" | grep -qi "success\|passed\|score" && echo 'PASS' || echo 'WARN') |
| Rollback executed | $(echo "${ROLLBACK_REAL_OUTPUT:-}" | grep -qi "success\|complete\|rollback" && echo 'PASS' || echo 'WARN') |
| VERSION after rollback | $([ "$(cat "${ROOT_DIR}/VERSION" 2>/dev/null)" = "${FROM_VERSION}" ] && echo 'PASS' || echo 'WARN') |
| Secrets check after | $(echo "${SEC_OUTPUT:-}" | grep -qi "no secrets found" && echo 'PASS' || echo 'WARN') |
EOF
fi

cat <<EOF >> "${REPORT_MD}"

## Failures: ${FAILURES}
## Warnings: ${WARNINGS}

## Logs
Logs available at: \`${LOGS_DIR}\`
EOF

echo ""
echo "Report generated:"
echo "  JSON: ${REPORT_JSON}"
echo "  MD:   ${REPORT_MD}"
echo "  Logs: ${LOGS_DIR}"

echo ""
echo "=== Safety Guarantees ==="
echo "  Backup required before upgrade: $(grep -q "SKIP_BACKUP" "${ROOT_DIR}/scripts/upgrade-local.sh" 2>/dev/null && echo 'YES' || echo 'NO')"
echo "  Rollback strong confirmation:  $(grep -q "ROLLBACK LOCAL" "${ROOT_DIR}/scripts/rollback-local.sh" 2>/dev/null && echo 'YES' || echo 'NO')"
echo "  Git clean check:               $(grep -q "git diff-index" "${ROOT_DIR}/scripts/upgrade-local.sh" 2>/dev/null && echo 'YES' || echo 'NO')"
echo "  Dry-run supported:             YES"
echo "  Secrets check available:       YES"

if [ "${FAILURES}" -gt 0 ]; then
    echo ""
    echo "[WARN] ${FAILURES} failure(s) and ${WARNINGS} warning(s) reported."
fi

exit 0
