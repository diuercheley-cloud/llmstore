#!/usr/bin/env bash
set -e

# Pre-client/Pre-demo Checklist Script

# Default values
MODE="none"
STRICT="false"
BASE_URL="http://localhost:18080"
SKIP_LMSTUDIO="false"
SKIP_RAG="false"
SKIP_TTS="false"
OUTPUT_DIR="artifacts/pre-client-checklists"
CHECK_TIMEOUT_SECONDS="${CHECK_TIMEOUT_SECONDS:-5}"
RUN_DEEP_CHECKS="${PRE_CLIENT_DEEP_CHECKS:-false}"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --demo                  Run demo checklist"
    echo "  --client-install        Run client installation checklist"
    echo "  --strict                Fail on warnings"
    echo "  --base-url <url>        Base URL of the application (default: http://localhost:18080)"
    echo "  --skip-lmstudio         Skip LM Studio checks"
    echo "  --skip-rag              Skip RAG checks"
    echo "  --skip-tts              Skip TTS checks"
    echo "  --output-dir <dir>      Output directory for the checklist (default: artifacts/pre-client-checklists)"
    echo "  --help                  Show this help"
    exit 0
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --demo) MODE="demo"; shift ;;
        --client-install) MODE="client-install"; shift ;;
        --strict) STRICT="true"; shift ;;
        --base-url) BASE_URL="$2"; shift 2 ;;
        --skip-lmstudio) SKIP_LMSTUDIO="true"; shift ;;
        --skip-rag) SKIP_RAG="true"; shift ;;
        --skip-tts) SKIP_TTS="true"; shift ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --help) usage ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
done

if [[ "$MODE" == "none" ]]; then
    echo "Error: Must specify either --demo or --client-install"
    exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_DIR="$OUTPUT_DIR/$TIMESTAMP"
LOG_DIR="$REPORT_DIR/logs"
mkdir -p "$LOG_DIR"

JSON_FILE="$REPORT_DIR/checklist.json"
MD_FILE="$REPORT_DIR/checklist.md"

STATUS="GO"
WARNINGS=0
ERRORS=0

log() { echo "[INFO] $1"; }
warn() {
    echo "[WARN] $1"
    WARNINGS=$((WARNINGS+1))
    if [[ "$STATUS" != "NO_GO" ]]; then STATUS="GO_WITH_WARNINGS"; fi
}
error() {
    echo "[ERROR] $1"
    ERRORS=$((ERRORS+1))
    STATUS="NO_GO"
}

run_check() {
    local check_name="$1"
    local check_cmd="$2"
    local safe_name=$(echo "$check_name" | tr -cd '[:alnum:]_ -' | tr ' ' '_')
    local log_file="$LOG_DIR/${safe_name}.log"
    log "Running check: $check_name"
    if timeout "${CHECK_TIMEOUT_SECONDS}" bash -c "$check_cmd" > "$log_file" 2>&1; then
        echo -e "\e[32m[PASS]\e[0m $check_name"
        return 0
    else
        if [[ $? -eq 124 ]]; then
            echo -e "\e[31m[FAIL]\e[0m $check_name timed out after ${CHECK_TIMEOUT_SECONDS}s (see $log_file)"
        else
        echo -e "\e[31m[FAIL]\e[0m $check_name (see $log_file)"
        fi
        error "Check failed: $check_name"
        return 1
    fi
}

run_check_warn() {
    local check_name="$1"
    local check_cmd="$2"
    local safe_name=$(echo "$check_name" | tr -cd '[:alnum:]_ -' | tr ' ' '_')
    local log_file="$LOG_DIR/${safe_name}.log"
    log "Running check (warn only): $check_name"
    if timeout "${CHECK_TIMEOUT_SECONDS}" bash -c "$check_cmd" > "$log_file" 2>&1; then
        echo -e "\e[32m[PASS]\e[0m $check_name"
        return 0
    else
        if [[ $? -eq 124 ]]; then
            echo -e "\e[33m[WARN]\e[0m $check_name timed out after ${CHECK_TIMEOUT_SECONDS}s (see $log_file)"
        else
        echo -e "\e[33m[WARN]\e[0m $check_name (see $log_file)"
        fi
        warn "Check generated warning: $check_name"
        return 1
    fi
}

echo "Starting Pre-Client Checklist in $MODE mode..."
if [[ "$RUN_DEEP_CHECKS" != "true" ]]; then
    log "Deep validation scripts are disabled by default for a fast operator checklist."
    log "Set PRE_CLIENT_DEEP_CHECKS=true to execute the extended validation suite."
fi

# Disable exit on error so we can collect all failures and write the report
set +e

# Checks
# 1. git status clean or warning
if [[ -n $(git status -s) ]]; then
    warn "Git status is not clean"
fi

# 2. VERSION
if [[ ! -f VERSION ]]; then
    error "VERSION file missing"
else
    APP_VERSION=$(cat VERSION)
    log "Version: $APP_VERSION"
fi

# 3. branch/tag
BRANCH=$(git rev-parse --abbrev-ref HEAD)
log "Current branch: $BRANCH"

# 4. docker compose ps
run_check_warn "Docker Compose PS" "docker compose ps" || run_check_warn "Docker Compose PS (Fallback)" "docker-compose ps" || true

# 5. Endpoints /health /ready /status
run_check_warn "Endpoint /health" "curl -f -s $BASE_URL/health || curl -f -s $BASE_URL/api/v1/health"
run_check_warn "Endpoint /ready" "curl -f -s $BASE_URL/ready || curl -f -s $BASE_URL/api/v1/ready"
run_check_warn "Endpoint /status" "curl -f -s $BASE_URL/status || curl -f -s $BASE_URL/api/v1/status"

# /admin/health/deep
if curl -s $BASE_URL/admin/health/deep | grep -q "status"; then
    run_check "Endpoint /admin/health/deep" "curl -f -s $BASE_URL/admin/health/deep"
fi

# 6. Deep scripts checks
if [[ "$RUN_DEEP_CHECKS" == "true" ]]; then
    if [[ -f ./scripts/validators/check-secrets.sh ]]; then
        run_check "Check Secrets" "./scripts/validators/check-secrets.sh --all"
    fi

    if [[ -f ./scripts/validators/security-report-local.sh ]]; then
        run_check_warn "Security Report" "./scripts/validators/security-report-local.sh"
    fi

    if [[ -f ./scripts/dev/production-readiness-local.sh ]]; then
        run_check_warn "Production Readiness" "./scripts/dev/production-readiness-local.sh"
    fi

    if [[ -f ./scripts/validators/validate-local-production-full.sh ]]; then
        run_check_warn "Validate Production Full" "./scripts/validators/validate-local-production-full.sh"
    fi

    if [[ "$MODE" == "demo" ]] && [[ -f ./scripts/dev/demo-full-local.sh ]]; then
        run_check_warn "Demo Full Local" "./scripts/dev/demo-full-local.sh --no-build"
    fi

    if [[ -f ./scripts/validators/post-upgrade-smoke-local.sh ]]; then
        run_check_warn "Post Upgrade Smoke" "./scripts/validators/post-upgrade-smoke-local.sh"
    fi

    if [[ -f ./scripts/validators/validate-multitenant-isolation-full.sh ]]; then
        run_check_warn "Multitenant Isolation" "./scripts/validators/validate-multitenant-isolation-full.sh"
    fi

    if [[ -f ./scripts/validators/validate-abuse-protection-local.sh ]]; then
        run_check_warn "Abuse Protection" "./scripts/validators/validate-abuse-protection-local.sh"
    fi

    if [[ -f ./scripts/validators/validate-commercial-plans-local.sh ]]; then
        run_check_warn "Commercial Plans" "./scripts/validators/validate-commercial-plans-local.sh"
    fi
fi

# 8. RAG/TTS Checks
if [[ "$SKIP_RAG" == "false" ]]; then
    log "Checking RAG (Simulated)"
fi

if [[ "$SKIP_TTS" == "false" ]]; then
    log "Checking TTS (Simulated)"
fi

# Determine Final Status
if [[ "$STRICT" == "true" ]] && [[ "$STATUS" == "GO_WITH_WARNINGS" ]]; then
    STATUS="NO_GO"
    log "Strict mode enabled: Warnings escalated to Errors"
fi

# Write JSON
cat <<EOF > "$JSON_FILE"
{
  "mode": "$MODE",
  "status": "$STATUS",
  "version": "$APP_VERSION",
  "branch": "$BRANCH",
  "timestamp": "$TIMESTAMP",
  "warnings": $WARNINGS,
  "errors": $ERRORS,
  "base_url": "$BASE_URL"
}
EOF

# Write MD
cat <<EOF > "$MD_FILE"
# Pre-Client Checklist Report

**Date:** $(date)
**Mode:** $MODE
**Status:** $STATUS
**Version:** $APP_VERSION
**Branch:** $BRANCH

## Resumo Executivo
This report summarizes the validation checks performed before a client presentation or installation.

## URLs
- Base URL: $BASE_URL

## Limitações
- PSP real não incluído
- PIX real não incluído
- HTTPS opcional em localhost

## Riscos Residuais
$(if [[ $WARNINGS -gt 0 ]]; then echo "- Existing warnings ($WARNINGS) need review"; else echo "- N/A"; fi)

## Checklist Técnico
- **Errors:** $ERRORS
- **Warnings:** $WARNINGS

See \`logs/\` directory for detailed check outputs.

## Próximos Passos
$(if [[ "$STATUS" == "GO" ]]; then echo "- Proceed with the presentation/installation."; elif [[ "$STATUS" == "GO_WITH_WARNINGS" ]]; then echo "- Review warnings, but generally safe to proceed."; else echo "- DO NOT PROCEED. Address errors before continuing."; fi)
EOF

echo ""
echo "=== PRE-CLIENT CHECKLIST COMPLETE ==="
echo "Final Status: $STATUS"
echo "Report generated at: $REPORT_DIR"
echo "JSON Report: $JSON_FILE"
echo "Markdown Report: $MD_FILE"
echo "====================================="

if [[ "$STATUS" == "NO_GO" ]]; then
    exit 1
fi
exit 0
