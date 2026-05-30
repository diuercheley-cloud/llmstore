#!/bin/bash
set -e

# LLM Inference Stack - Release Gate Validator
# Runs all mandatory gates and generates release artifacts.

VERSION=$(cat VERSION 2>/dev/null || echo "v0.0.0")
TAG=$1

if [ -z "$TAG" ]; then
    echo "=========================================="
    echo "  Release Gate: FAILED"
    echo "=========================================="
    echo "Erro: Tag de release não fornecida."
    echo "Uso: make release-gate TAG=vX.Y.Z"
    exit 1
fi

echo "=========================================="
echo "  Release Gate: $TAG"
echo "=========================================="

ARTIFACT_DIR="artifacts/releases/$TAG"
mkdir -p "$ARTIFACT_DIR"

GATES_PASSED=0
GATES_FAILED=0
FAILED_GATES=""
GATE_RESULTS=""

run_gate() {
    local name=$1
    shift
    echo ""
    echo "━━━ Gate: $name ━━━"
    if "$@"; then
        echo "━━━ [PASS] $name ━━━"
        GATES_PASSED=$((GATES_PASSED+1))
        GATE_RESULTS="${GATE_RESULTS}| $name | PASS |\n"
    else
        local rc=$?
        echo "━━━ [FAIL] $name (exit code: $rc) ━━━"
        GATES_FAILED=$((GATES_FAILED+1))
        FAILED_GATES="$FAILED_GATES $name"
        GATE_RESULTS="${GATE_RESULTS}| $name | FAIL |\n"
    fi
}

# ---------------------------------------------------------------------------
# 1. Tag Validation
# ---------------------------------------------------------------------------
echo ""
echo "━━━ Gate: tag-format ━━━"
if [[ ! $TAG =~ ^v[0-9]+\.[0-9]+\.[0-9]+.*$ ]]; then
    echo "Erro: Tag '$TAG' não segue o padrão vX.Y.Z-name"
    exit 1
fi
echo "[PASS] Tag format: $TAG"
GATES_PASSED=$((GATES_PASSED+1))
GATE_RESULTS="${GATE_RESULTS}| tag-format | PASS |\n"

# ---------------------------------------------------------------------------
# 2. CHANGELOG
# ---------------------------------------------------------------------------
echo ""
echo "━━━ Gate: changelog ━━━"
if ! grep -q "$TAG" CHANGELOG.md; then
    echo "Erro: CHANGELOG.md não contém a versão $TAG"
    GATES_FAILED=$((GATES_FAILED+1))
    FAILED_GATES="$FAILED_GATES changelog"
    GATE_RESULTS="${GATE_RESULTS}| changelog | FAIL |\n"
else
    echo "[PASS] CHANGELOG.md contém entrada para $TAG"
    GATES_PASSED=$((GATES_PASSED+1))
    GATE_RESULTS="${GATE_RESULTS}| changelog | PASS |\n"
fi

# ---------------------------------------------------------------------------
# 3. Release Notes
# ---------------------------------------------------------------------------
echo ""
echo "━━━ Gate: release-notes ━━━"
RELEASE_NOTE_PATH="docs/releases/$(echo "$TAG" | sed 's/\./_/g' | tr '-' '_').md"
RELEASE_NOTE_ALT_PATH="docs/releases/$(echo "$TAG" | tr '[:lower:]' '[:upper:]' | sed 's/\./_/g' | tr '-' '_').md"
if [ -f "$RELEASE_NOTE_PATH" ]; then
    echo "[PASS] Release notes: $RELEASE_NOTE_PATH"
    GATES_PASSED=$((GATES_PASSED+1))
    GATE_RESULTS="${GATE_RESULTS}| release-notes | PASS |\n"
elif [ -f "$RELEASE_NOTE_ALT_PATH" ]; then
    echo "[PASS] Release notes: $RELEASE_NOTE_ALT_PATH"
    GATES_PASSED=$((GATES_PASSED+1))
    GATE_RESULTS="${GATE_RESULTS}| release-notes | PASS |\n"
else
    echo "Erro: Release notes não encontradas para $TAG"
    echo "  Procurou: $RELEASE_NOTE_PATH"
    echo "  Procurou: $RELEASE_NOTE_ALT_PATH"
    GATES_FAILED=$((GATES_FAILED+1))
    FAILED_GATES="$FAILED_GATES release-notes"
    GATE_RESULTS="${GATE_RESULTS}| release-notes | FAIL |\n"
fi

# ---------------------------------------------------------------------------
# 4. Feature Flags Governance
# ---------------------------------------------------------------------------
run_gate "feature-flags" bash scripts/check-feature-flags.sh

# ---------------------------------------------------------------------------
# 4a. Working Tree Certification
# ---------------------------------------------------------------------------
run_gate "working-tree-certification" bash scripts/working-tree-certification.sh

# ---------------------------------------------------------------------------
# 5. check-secrets
# ---------------------------------------------------------------------------
run_gate "check-secrets" bash scripts/check-secrets.sh --all

# ---------------------------------------------------------------------------
# 6. check-alembic-integrity
# ---------------------------------------------------------------------------
run_gate "check-alembic-integrity" bash scripts/check-alembic-integrity.sh

# ---------------------------------------------------------------------------
# 7. platform-freeze-check
# ---------------------------------------------------------------------------
run_gate "platform-freeze-check" bash scripts/platform-freeze-check.sh

# ---------------------------------------------------------------------------
# 8. complexity-report
# ---------------------------------------------------------------------------
run_gate "complexity-report" bash scripts/complexity-report.sh

# ---------------------------------------------------------------------------
# 9. security
# ---------------------------------------------------------------------------
run_gate "security" bash scripts/security-report-local.sh

# ---------------------------------------------------------------------------
# 10. validate-quick
# ---------------------------------------------------------------------------
echo ""
echo "━━━ Gate: validate-quick ━━━"
if VALIDATION_MODE=quick bash scripts/validate-local-production-full.sh; then
    echo "━━━ [PASS] validate-quick ━━━"
    GATES_PASSED=$((GATES_PASSED+1))
    GATE_RESULTS="${GATE_RESULTS}| validate-quick | PASS |\n"
else
    rc=$?
    echo "━━━ [FAIL] validate-quick (exit code: $rc) ━━━"
    GATES_FAILED=$((GATES_FAILED+1))
    FAILED_GATES="$FAILED_GATES validate-quick"
    GATE_RESULTS="${GATE_RESULTS}| validate-quick | FAIL |\n"
fi

# ---------------------------------------------------------------------------
# 11. operational-readiness
# ---------------------------------------------------------------------------
echo ""
echo "━━━ Gate: operational-readiness ━━━"
READINESS_OUTPUT=$(bash scripts/operational-readiness-pack.sh 2>&1)
READINESS_RC=$?
if [ $READINESS_RC -eq 0 ] || echo "$READINESS_OUTPUT" | grep -q "production_blocked"; then
    if [ $READINESS_RC -ne 0 ]; then
        echo "$READINESS_OUTPUT"
        echo "━━━ [FAIL] operational-readiness (production_blocked) ━━━"
        GATES_FAILED=$((GATES_FAILED+1))
        FAILED_GATES="$FAILED_GATES operational-readiness"
        GATE_RESULTS="${GATE_RESULTS}| operational-readiness | FAIL |\n"
    else
        echo "$READINESS_OUTPUT"
        echo "━━━ [PASS] operational-readiness ━━━"
        GATES_PASSED=$((GATES_PASSED+1))
        GATE_RESULTS="${GATE_RESULTS}| operational-readiness | PASS |\n"
    fi
else
    echo "$READINESS_OUTPUT"
    echo "━━━ [FAIL] operational-readiness (exit code: $READINESS_RC) ━━━"
    GATES_FAILED=$((GATES_FAILED+1))
    FAILED_GATES="$FAILED_GATES operational-readiness"
    GATE_RESULTS="${GATE_RESULTS}| operational-readiness | FAIL |\n"
fi

# ---------------------------------------------------------------------------
# 12. agentic-readiness
# ---------------------------------------------------------------------------
echo ""
echo "━━━ Gate: agentic-readiness ━━━"
AGENTIC_OUTPUT=$(bash scripts/agentic-readiness.sh 2>&1)
AGENTIC_RC=$?
echo "$AGENTIC_OUTPUT"

IS_PRODUCTION_GATE=false
if [[ "$TAG" =~ "agentic" || "$TAG" =~ "platform" || "$TAG" =~ "production" ]]; then
    IS_PRODUCTION_GATE=true
fi

AGENTIC_STATUS=$(echo "$AGENTIC_OUTPUT" | grep -oP 'Status:\s*\K\S+' || echo "unknown")
if echo "$AGENTIC_OUTPUT" | grep -q "disabled" || [ "$AGENTIC_STATUS" = "disabled" ]; then
    if [ "$IS_PRODUCTION_GATE" = "true" ]; then
        echo "━━━ [FAIL] agentic-readiness (disabled NOT_VALID_FOR_PRODUCTION) ━━━"
        GATES_FAILED=$((GATES_FAILED+1))
        FAILED_GATES="$FAILED_GATES agentic-readiness"
        GATE_RESULTS="${GATE_RESULTS}| agentic-readiness | disabled NOT_VALID_FOR_PRODUCTION |\n"
    else
        echo "━━━ [PASS] agentic-readiness (safe-default PASS) ━━━"
        GATES_PASSED=$((GATES_PASSED+1))
        GATE_RESULTS="${GATE_RESULTS}| agentic-readiness | safe-default PASS |\n"
    fi
elif [ $AGENTIC_RC -eq 0 ]; then
    echo "━━━ [PASS] agentic-readiness (production-on PASS) ━━━"
    GATES_PASSED=$((GATES_PASSED+1))
    GATE_RESULTS="${GATE_RESULTS}| agentic-readiness | production-on PASS |\n"
else
    echo "━━━ [FAIL] agentic-readiness (status: $AGENTIC_STATUS) ━━━"
    GATES_FAILED=$((GATES_FAILED+1))
    FAILED_GATES="$FAILED_GATES agentic-readiness"
    GATE_RESULTS="${GATE_RESULTS}| agentic-readiness | FAIL (status: $AGENTIC_STATUS) |\n"
fi

if [ "$IS_PRODUCTION_GATE" = "true" ]; then
    run_gate "real-execution-readiness" make real-execution-readiness TAG="$TAG"
    run_gate "production-agentic-e2e" make production-agentic-e2e TAG="$TAG"
    run_gate "working-tree-certification" make working-tree-certification TAG="$TAG"
    run_gate "agentic-production-on-readiness" make agentic-production-on-readiness TAG="$TAG"
fi

# ---------------------------------------------------------------------------
# 13. compliance-check (se aplicável)
# ---------------------------------------------------------------------------
if [ -f scripts/compliance-check.sh ]; then
    run_gate "compliance-check" bash scripts/compliance-check.sh
fi

# ---------------------------------------------------------------------------
# Generate Release Artifacts
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "  Generating Release Artifacts"
echo "=========================================="

TIMESTAMP_NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# summary.md
cat > "$ARTIFACT_DIR/summary.md" << EOF
# $TAG Release Summary

**Generated at**: $TIMESTAMP_NOW
**Gates passed**: $GATES_PASSED
**Gates failed**: $GATES_FAILED

## Result
EOF

if [ $GATES_FAILED -gt 0 ]; then
    echo "**Status**: BLOCKED" >> "$ARTIFACT_DIR/summary.md"
    echo "**Failed gates**:$FAILED_GATES" >> "$ARTIFACT_DIR/summary.md"
else
    echo "**Status**: PASS" >> "$ARTIFACT_DIR/summary.md"
fi

cat >> "$ARTIFACT_DIR/summary.md" << EOF

## Gate Results
| Gate | Result |
|------|--------|
$(echo -e "$GATE_RESULTS")
EOF

# validation.md
cat > "$ARTIFACT_DIR/validation.md" << EOF
# $TAG Validation

**Generated at**: $TIMESTAMP_NOW

| Gate | Result |
|------|--------|
$(echo -e "$GATE_RESULTS")
EOF

if [ "$IS_PRODUCTION_GATE" = "true" ]; then
    real_execution_status=$(echo -e "$GATE_RESULTS" | grep "real-execution-readiness" | awk -F'|' '{print $3}' | xargs || echo "FAIL")
    production_e2e_status=$(echo -e "$GATE_RESULTS" | grep "production-agentic-e2e" | awk -F'|' '{print $3}' | xargs || echo "FAIL")
    working_tree_status=$(echo -e "$GATE_RESULTS" | grep "working-tree-certification" | awk -F'|' '{print $3}' | xargs || echo "FAIL")
    prod_on_status=$(echo -e "$GATE_RESULTS" | grep "agentic-production-on-readiness" | awk -F'|' '{print $3}' | xargs || echo "FAIL")
    agentic_readiness_status=$(echo -e "$GATE_RESULTS" | grep "agentic-readiness" | awk -F'|' '{print $3}' | xargs || echo "FAIL")

    production_gate_overall="PASS"
    if [ $GATES_FAILED -gt 0 ]; then
        production_gate_overall="BLOCKED"
    fi

    cat > "$ARTIFACT_DIR/production-gate.md" << EOF
# Production Release Gate Report

**Tag:** $TAG
**Timestamp:** $TIMESTAMP_NOW
**Overall Status:** $production_gate_overall

## Production Gate Checks
- **real-execution-readiness**: $real_execution_status
- **production-agentic-e2e**: $production_e2e_status
- **working-tree-certification**: $working_tree_status
- **agentic-production-on-readiness**: $prod_on_status
- **agentic-readiness**: $agentic_readiness_status
EOF
fi

if [ -f artifacts/platform/ga-readiness.md ]; then
    cp artifacts/platform/ga-readiness.md "$ARTIFACT_DIR/ga-readiness.md"
fi

if [ -f artifacts/platform/feature-flag-audit.md ]; then
    cp artifacts/platform/feature-flag-audit.md "$ARTIFACT_DIR/feature-flags.md"
elif [ -f control_plane/artifacts/platform/feature-flag-audit.md ]; then
    cp control_plane/artifacts/platform/feature-flag-audit.md "$ARTIFACT_DIR/feature-flags.md"
fi

if [ -f artifacts/platform/surface-audit.md ]; then
    cp artifacts/platform/surface-audit.md "$ARTIFACT_DIR/surface-audit.md"
elif [ -f control_plane/artifacts/platform/surface-audit.md ]; then
    cp control_plane/artifacts/platform/surface-audit.md "$ARTIFACT_DIR/surface-audit.md"
fi

if [ -f artifacts/security/security-cleanup.md ]; then
    cp artifacts/security/security-cleanup.md "$ARTIFACT_DIR/security-cleanup.md"
else
    latest_security_report=$(ls -td artifacts/security-reports/* 2>/dev/null | head -n 1 || true)
    if [ -n "$latest_security_report" ] && [ -f "$latest_security_report/security-report.md" ]; then
        cp "$latest_security_report/security-report.md" "$ARTIFACT_DIR/security-cleanup.md"
    fi
fi

# agentic-readiness.md
if echo "$AGENTIC_OUTPUT" | grep -q "disabled"; then
    AGENTIC_ARTIFACT_STATUS="disabled"
elif echo "$AGENTIC_OUTPUT" | grep -q "ready"; then
    AGENTIC_ARTIFACT_STATUS="ready"
elif echo "$AGENTIC_OUTPUT" | grep -q "degraded"; then
    AGENTIC_ARTIFACT_STATUS="degraded"
elif echo "$AGENTIC_OUTPUT" | grep -q "BLOCKED\|blocked"; then
    AGENTIC_ARTIFACT_STATUS="blocked"
else
    AGENTIC_ARTIFACT_STATUS="$([ $AGENTIC_RC -eq 0 ] && echo 'passed' || echo 'failed')"
fi

cat > "$ARTIFACT_DIR/agentic-readiness.md" << EOF
# Agentic Readiness

**Generated at**: $TIMESTAMP_NOW
**Status**: $AGENTIC_ARTIFACT_STATUS
**Runtime enabled**: ${AGENT_RUNTIME_ENABLED:-false}
**Worker enabled**: ${AGENT_WORKER_ENABLED:-false}
EOF

if [ -n "$AGENTIC_OUTPUT" ]; then
    echo "" >> "$ARTIFACT_DIR/agentic-readiness.md"
    echo '```' >> "$ARTIFACT_DIR/agentic-readiness.md"
    echo "$AGENTIC_OUTPUT" >> "$ARTIFACT_DIR/agentic-readiness.md"
    echo '```' >> "$ARTIFACT_DIR/agentic-readiness.md"
fi

# security.md
SECURITY_STATUS="passed"
if [ $GATES_FAILED -gt 0 ]; then
    case "$FAILED_GATES" in
        *security*) SECURITY_STATUS="failed" ;;
    esac
fi
cat > "$ARTIFACT_DIR/security.md" << EOF
# Security

**Generated at**: $TIMESTAMP_NOW
**Status**: $SECURITY_STATUS

## Gates
- check-secrets: $(echo "$GATE_RESULTS" | grep "check-secrets" | awk -F'|' '{print $3}')
- security: $(echo "$GATE_RESULTS" | grep "security" | awk -F'|' '{print $3}')
EOF

# evals.md
EVALS_STATUS="not_run"
cat > "$ARTIFACT_DIR/evals.md" << EOF
# Agent Evals

**Generated at**: $TIMESTAMP_NOW
**Status**: $EVALS_STATUS

This artifact is produced by the agentic evaluation pipeline.
EOF

# slo.md
cat > "$ARTIFACT_DIR/slo.md" << EOF
# Agentic SLO

**Generated at**: $TIMESTAMP_NOW
**Status**: DOCUMENTED

SLO governance is defined in \`config/agent-slo-classes.yaml\`.
EOF

# Copy operational readiness artifacts if available
if [ -f artifacts/operational-readiness/latest/checks.json ]; then
    cp artifacts/operational-readiness/latest/checks.json "$ARTIFACT_DIR/operational-readiness-checks.json" 2>/dev/null || true
fi

echo "Artifacts written to $ARTIFACT_DIR/"

# ---------------------------------------------------------------------------
# Final Result
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "  Release Gate Results"
echo "=========================================="
echo "  Gates passed : $GATES_PASSED"
echo "  Gates failed : $GATES_FAILED"
if [ $GATES_FAILED -gt 0 ]; then
    echo "  Failed gates :$FAILED_GATES"
    echo ""
    echo "=========================================="
    echo "  Release Gate: FAILED"
    echo "=========================================="
    echo ""
    echo "Os seguintes gates falharam e precisam ser resolvidos antes do tag:"
    for gate in $FAILED_GATES; do
        echo "  - $gate"
    done
    exit 1
else
    echo ""
    echo "=========================================="
    echo "  Release Gate: PASS"
    echo "=========================================="
    exit 0
fi
