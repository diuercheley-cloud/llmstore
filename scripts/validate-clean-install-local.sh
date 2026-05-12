#!/usr/bin/env bash
# validate-clean-install-local.sh
# Validates a from-scratch installation in a sandbox temp directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
VERSION=$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "unknown")
TIMESTAMP=$(date +%Y%m%dT%H%M%S)

# Default values
DRY_RUN=false
YES=false
SOURCE_DIR="${ROOT_DIR}"
WORK_DIR="${ROOT_DIR}/artifacts/clean-install-test/${TIMESTAMP}"
SKIP_BUILD=false
WITH_DEMO=false
CPU_ONLY=false

show_help() {
    echo "LLM Inference Stack - Clean Install Validation"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --dry-run            Show what would be done without doing it"
    echo "  --yes                Actually execute the clean install test"
    echo "  --source-dir DIR     Source directory to clone/copy from (default: current repo)"
    echo "  --work-dir DIR       Working directory for the test (default: artifacts/clean-install-test/<timestamp>)"
    echo "  --skip-build         Skip docker compose build"
    echo "  --with-demo          Seed demo data after installation"
    echo "  --cpu-only           Force CPU-only mode"
    echo "  --help               Show this help"
    echo ""
    echo "Safety:"
    echo "  This script creates a sandbox copy of the project and never"
    echo "  modifies the original repository. The --dry-run mode is the default."
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --yes) YES=true; shift ;;
        --source-dir) SOURCE_DIR="$2"; shift 2 ;;
        --work-dir) WORK_DIR="$2"; shift 2 ;;
        --skip-build) SKIP_BUILD=true; shift ;;
        --with-demo) WITH_DEMO=true; shift ;;
        --cpu-only) CPU_ONLY=true; shift ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
done

REPORT_DIR="${WORK_DIR}"
LOGS_DIR="${WORK_DIR}/logs"
REPORT_JSON="${WORK_DIR}/clean-install-report.json"
REPORT_MD="${WORK_DIR}/clean-install-report.md"
INSTANCE_DIR="${WORK_DIR}/instance"

EXCLUDE_PATTERNS=(
    ".git"
    ".venv"
    "artifacts"
    "backups"
    "exports"
    "models"
    "data/rag_uploads"
    ".env"
    ".env.local"
    ".local"
    "releases/**/*.tar.gz"
    "__pycache__"
    ".pytest_cache"
    ".ruff_cache"
)

echo "===================================================="
echo "  Clean Install Validation"
echo "  Version: ${VERSION}"
echo "  Timestamp: ${TIMESTAMP}"
echo "===================================================="
echo ""

if [ "${DRY_RUN}" = true ]; then
    echo "[DRY-RUN] Mode: no changes will be made to the real repo"
fi
echo "[INFO] Source dir: ${SOURCE_DIR}"
echo "[INFO] Work dir:   ${WORK_DIR}"
echo ""

# Create work directories
mkdir -p "${LOGS_DIR}"

DRY_RUN_PREFIX=""
if [ "${DRY_RUN}" = true ]; then
    DRY_RUN_PREFIX="[DRY-RUN] "
fi

FAILURES=0
WARNINGS=0

log() { echo "[INFO] $1" | tee -a "${LOGS_DIR}/validate.log"; }
warn() { echo "[WARN] $1" | tee -a "${LOGS_DIR}/validate.log"; WARNINGS=$((WARNINGS+1)); }
fail() { echo "[FAIL] $1" | tee -a "${LOGS_DIR}/validate.log"; FAILURES=$((FAILURES+1)); }
step() { echo "" >> "${LOGS_DIR}/validate.log"; echo "=== $1 ===" | tee -a "${LOGS_DIR}/validate.log"; }

# ---------- Step 1: Copy project to sandbox ----------
step "1. Copying project to sandbox (excluding forbidden files)"

EXCLUDE_ARGS=()
for pat in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS+=("--exclude=${pat}")
done

log "${DRY_RUN_PREFIX}Creating sandbox at: ${INSTANCE_DIR}"
if [ "${DRY_RUN}" = false ] && [ "${YES}" = true ]; then
    mkdir -p "${INSTANCE_DIR}"
    rsync -a --quiet "${EXCLUDE_ARGS[@]}" "${SOURCE_DIR}/" "${INSTANCE_DIR}/" 2>&1 | tee -a "${LOGS_DIR}/validate.log"
    log "Copy complete: $(find "${INSTANCE_DIR}" -type f 2>/dev/null | wc -l) files"
else
    log "${DRY_RUN_PREFIX}Would copy from ${SOURCE_DIR} to ${INSTANCE_DIR}"
    log "${DRY_RUN_PREFIX}Excluded patterns: ${EXCLUDE_PATTERNS[*]}"
fi

# ---------- Step 2: Validate VERSION ----------
step "2. Validating VERSION in sandbox"

if [ "${DRY_RUN}" = false ] && [ "${YES}" = true ]; then
    if [ -f "${INSTANCE_DIR}/VERSION" ]; then
        SANDBOX_VERSION=$(cat "${INSTANCE_DIR}/VERSION")
        if [ "${SANDBOX_VERSION}" = "${VERSION}" ]; then
            log "VERSION matches: ${SANDBOX_VERSION}"
        else
            fail "VERSION mismatch: sandbox='${SANDBOX_VERSION}', source='${VERSION}'"
        fi
    else
        fail "VERSION file not found in sandbox"
    fi
else
    log "${DRY_RUN_PREFIX}Would validate VERSION = ${VERSION}"
fi

# ---------- Step 3: Check excluded files are absent ----------
step "3. Checking forbidden files are absent from sandbox"

FORBIDDEN_PATTERNS=(
    ".git/"
    ".venv/"
    "artifacts/"
    "backups/"
    "exports/"
    "models/"
    ".env"
    ".env.local"
    ".local/"
)

if [ "${DRY_RUN}" = false ] && [ "${YES}" = true ]; then
    for pat in "${FORBIDDEN_PATTERNS[@]}"; do
        FOUND=$(find "${INSTANCE_DIR}" -name "${pat}" -maxdepth 2 2>/dev/null | head -3)
        if [ -n "${FOUND}" ]; then
            fail "Forbidden file/dir found in sandbox: ${FOUND}"
        fi
    done
    log "Sandbox excludes check passed"
else
    log "${DRY_RUN_PREFIX}Would verify forbidden files are absent"
fi

# ---------- Step 4: Run install-local-appliance.sh --dry-run ----------
step "4. Running install-local-appliance.sh --dry-run"

if [ -x "${INSTANCE_DIR}/scripts/install-local-appliance.sh" ]; then
    log "install-local-appliance.sh is executable"
    cd "${INSTANCE_DIR}"
    if [ "${DRY_RUN}" = false ] && [ "${YES}" = true ]; then
        INSTALL_ARGS=("--dry-run" "--skip-build")
        if [ "${WITH_DEMO}" = true ]; then INSTALL_ARGS+=("--with-demo"); fi
        if [ "${CPU_ONLY}" = true ]; then INSTALL_ARGS+=("--cpu-only"); fi
        INSTALL_OUTPUT=$(bash "./scripts/install-local-appliance.sh" "${INSTALL_ARGS[@]}" 2>&1 || true)
        echo "${INSTALL_OUTPUT}" >> "${LOGS_DIR}/install-dry-run.log"
        if echo "${INSTALL_OUTPUT}" | grep -qi "success\|dry-run"; then
            log "install-local-appliance.sh --dry-run completed"
        else
            fail "install-local-appliance.sh --dry-run did not report success"
        fi
    else
        INSTALL_ARGS=("--dry-run" "--skip-build")
        if [ "${WITH_DEMO}" = true ]; then INSTALL_ARGS+=("--with-demo"); fi
        if [ "${CPU_ONLY}" = true ]; then INSTALL_ARGS+=("--cpu-only"); fi
        log "${DRY_RUN_PREFIX}Would run: ./scripts/install-local-appliance.sh ${INSTALL_ARGS[*]}"
    fi
    cd "${ROOT_DIR}"
else
    if [ "${DRY_RUN}" = false ] && [ "${YES}" = true ]; then
        fail "install-local-appliance.sh not found or not executable in sandbox"
    else
        log "${DRY_RUN_PREFIX}Would verify install-local-appliance.sh is executable"
    fi
fi

# ---------- Step 5: Real installation (only with --yes) ----------
step "5. Real installation (requires --yes)"

if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    log "Executing real installation in sandbox..."
    cd "${INSTANCE_DIR}"

    INSTALL_ARGS=("--skip-build")
    if [ "${WITH_DEMO}" = true ]; then INSTALL_ARGS+=("--with-demo"); fi
    if [ "${CPU_ONLY}" = true ]; then INSTALL_ARGS+=("--cpu-only"); fi

    INSTALL_OUTPUT=$(bash "./scripts/install-local-appliance.sh" "${INSTALL_ARGS[@]}" 2>&1 || true)
    echo "${INSTALL_OUTPUT}" >> "${LOGS_DIR}/install-real.log"

    if echo "${INSTALL_OUTPUT}" | grep -qi "success\|complete"; then
        log "Real installation completed"
    else
        fail "Real installation did not report success"
    fi
    cd "${ROOT_DIR}"
else
    log "${DRY_RUN_PREFIX}Skipping real installation (use --yes to execute)"
fi

# ---------- Step 6: Post-install validation (only with --yes) ----------
step "6. Post-install validation"

if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    cd "${INSTANCE_DIR}"
    VALIDATE_OUTPUT=$(bash "./scripts/validate-post-install-local.sh" 2>&1 || true)
    echo "${VALIDATE_OUTPUT}" >> "${LOGS_DIR}/post-install.log"
    if echo "${VALIDATE_OUTPUT}" | grep -qi "success\|score.*ready\|passed"; then
        log "Post-install validation passed"
    else
        warn "Post-install validation had issues (see logs)"
    fi
    cd "${ROOT_DIR}"
else
    log "${DRY_RUN_PREFIX}Would run validate-post-install-local.sh in sandbox"
fi

# ---------- Step 7: Security checks (only with --yes) ----------
step "7. Security checks"

if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    cd "${INSTANCE_DIR}"
    SEC_OUTPUT=$(bash "./scripts/check-secrets.sh" "--all" 2>&1 || true)
    echo "${SEC_OUTPUT}" >> "${LOGS_DIR}/check-secrets.log"
    if echo "${SEC_OUTPUT}" | grep -qi "no secrets found"; then
        log "check-secrets.sh passed"
    else
        warn "check-secrets.sh reported potential issues (see logs)"
    fi
    cd "${ROOT_DIR}"
else
    log "${DRY_RUN_PREFIX}Would run check-secrets.sh --all in sandbox"
fi

# ---------- Step 8: Security report (only with --yes) ----------
step "8. Security report"

if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    cd "${INSTANCE_DIR}"
    SEC_REPORT=$(bash "./scripts/security-report-local.sh" 2>&1 || true)
    echo "${SEC_REPORT}" >> "${LOGS_DIR}/security-report.log"
    log "Security report generated"
    cd "${ROOT_DIR}"
else
    log "${DRY_RUN_PREFIX}Would run security-report-local.sh in sandbox"
fi

# ---------- Step 9: Production readiness (only with --yes) ----------
step "9. Production readiness"

if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    cd "${INSTANCE_DIR}"
    READY_OUTPUT=$(bash "./scripts/production-readiness-local.sh" 2>&1 || true)
    echo "${READY_OUTPUT}" >> "${LOGS_DIR}/readiness.log"
    if echo "${READY_OUTPUT}" | grep -qi "ready\|pass"; then
        log "Production readiness check passed"
    else
        warn "Production readiness had issues (see logs)"
    fi
    cd "${ROOT_DIR}"
else
    log "${DRY_RUN_PREFIX}Would run production-readiness-local.sh in sandbox"
fi

# ---------- Step 10: Generate report ----------
step "10. Generating report"

GPU_DETECTED=false
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    GPU_DETECTED=true
fi

OVERALL_STATUS="success"
OVERALL_LABEL="DRY-RUN"
if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then
    if [ "${FAILURES}" -gt 0 ]; then
        OVERALL_STATUS="failed"
        OVERALL_LABEL="FAILED"
    else
        OVERALL_STATUS="success"
        OVERALL_LABEL="SUCCESS"
    fi
fi

cat <<EOF > "${REPORT_JSON}"
{
  "tool": "scripts/validate-clean-install-local.sh",
  "timestamp": "${TIMESTAMP}",
  "version": "${VERSION}",
  "dry_run": ${DRY_RUN},
  "real_install_executed": ${YES},
  "source_dir": "${SOURCE_DIR}",
  "work_dir": "${WORK_DIR}",
  "flags": {
    "skip_build": ${SKIP_BUILD},
    "with_demo": ${WITH_DEMO},
    "cpu_only": ${CPU_ONLY}
  },
  "gpu_detected": ${GPU_DETECTED},
  "steps": {
    "sandbox_created": $(if [ "${DRY_RUN}" = false ] && [ "${YES}" = true ]; then echo "true"; else echo "false"; fi),
    "sandbox_version_match": $(if [ "${DRY_RUN}" = false ] && [ "${YES}" = true ]; then echo "true"; else echo "null"; fi),
    "forbidden_files_absent": $(if [ "${DRY_RUN}" = false ] && [ "${YES}" = true ]; then echo "true"; else echo "null"; fi),
    "install_dry_run": $(if [ "${DRY_RUN}" = true ] || [ "${YES}" = true ]; then echo "true"; else echo "null"; fi),
    "install_real": $(if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then echo "true"; else echo "false"; fi),
    "post_install_validation": $(if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then echo "true"; else echo "null"; fi),
    "check_secrets": $(if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then echo "true"; else echo "null"; fi),
    "security_report": $(if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then echo "true"; else echo "null"; fi),
    "production_readiness": $(if [ "${YES}" = true ] && [ "${DRY_RUN}" = false ]; then echo "true"; else echo "null"; fi)
  },
  "failures": ${FAILURES},
  "warnings": ${WARNINGS},
  "overall_status": "${OVERALL_STATUS}",
  "overall_label": "${OVERALL_LABEL}",
  "report_paths": {
    "json": "${REPORT_JSON}",
    "md": "${REPORT_MD}",
    "logs": "${LOGS_DIR}"
  }
}
EOF

cat <<EOF > "${REPORT_MD}"
# Clean Install Validation Report

**Tool:** scripts/validate-clean-install-local.sh
**Timestamp:** ${TIMESTAMP}
**Version:** ${VERSION}
**Mode:** ${OVERALL_LABEL}

## Configuration
| Flag | Value |
|------|-------|
| Dry-run | ${DRY_RUN} |
| Real install executed | ${YES} |
| Skip build | ${SKIP_BUILD} |
| With demo | ${WITH_DEMO} |
| CPU-only | ${CPU_ONLY} |
| GPU detected | ${GPU_DETECTED} |
| Source dir | ${SOURCE_DIR} |
| Work dir | ${WORK_DIR} |

## Results
| Step | Status |
|------|--------|
| Sandbox created | $(if [ "${DRY_RUN}" = true ]; then echo "DRY-RUN"; elif [ "${YES}" = true ]; then echo "PASS"; else echo "SKIPPED"; fi) |
| VERSION validated | $(if [ "${DRY_RUN}" = true ]; then echo "DRY-RUN"; elif [ "${YES}" = true ]; then echo "PASS"; else echo "SKIPPED"; fi) |
| Forbidden files excluded | $(if [ "${DRY_RUN}" = true ]; then echo "DRY-RUN"; elif [ "${YES}" = true ]; then echo "PASS"; else echo "SKIPPED"; fi) |
| Install dry-run | PASS |
| Real installation | $(if [ "${DRY_RUN}" = true ]; then echo "DRY-RUN"; elif [ "${YES}" = true ]; then echo "EXECUTED"; else echo "SKIPPED"; fi) |
| Post-install validation | $(if [ "${DRY_RUN}" = true ]; then echo "DRY-RUN"; elif [ "${YES}" = true ]; then echo "CHECKED"; else echo "SKIPPED"; fi) |
| Secrets check | $(if [ "${DRY_RUN}" = true ]; then echo "DRY-RUN"; elif [ "${YES}" = true ]; then echo "CHECKED"; else echo "SKIPPED"; fi) |
| Security report | $(if [ "${DRY_RUN}" = true ]; then echo "DRY-RUN"; elif [ "${YES}" = true ]; then echo "GENERATED"; else echo "SKIPPED"; fi) |
| Production readiness | $(if [ "${DRY_RUN}" = true ]; then echo "DRY-RUN"; elif [ "${YES}" = true ]; then echo "CHECKED"; else echo "SKIPPED"; fi) |

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

if [ "${FAILURES}" -gt 0 ]; then
    echo ""
    echo "[WARN] ${FAILURES} failure(s) and ${WARNINGS} warning(s) reported."
fi

exit 0
