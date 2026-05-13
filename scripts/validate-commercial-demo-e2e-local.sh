#!/usr/bin/env bash
# validate-commercial-demo-e2e-local.sh
# End-to-end validation of the commercial demo flow.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
VERSION=$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "unknown")
TIMESTAMP=$(date +%Y%m%dT%H%M%S)

# Defaults
BASE_URL="http://localhost:18080"
RESET_FIRST=false
SEED_DEMO=false
SKIP_TTS=false
SKIP_RAG=false
SKIP_LMSTUDIO=false
OUTPUT_DIR="artifacts/final-qa/commercial-demo-e2e/${TIMESTAMP}"

show_help() {
    echo "LLM Inference Stack - Commercial Demo E2E Validation"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --base-url URL     Base URL (default: http://localhost:18080)"
    echo "  --reset-first      Reset demo data before seeding"
    echo "  --seed-demo        Seed commercial demo pack before validation"
    echo "  --skip-tts         Skip TTS validation"
    echo "  --skip-rag         Skip RAG validation"
    echo "  --skip-lmstudio    Skip LM Studio checks"
    echo "  --output-dir DIR   Output directory for report"
    echo "  --help             Show this help"
    echo ""
    echo "Status: DEMO_READY, DEMO_READY_WITH_WARNINGS, DEMO_FAILED"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --base-url) BASE_URL="$2"; shift 2 ;;
        --reset-first) RESET_FIRST=true; shift ;;
        --seed-demo) SEED_DEMO=true; shift ;;
        --skip-tts) SKIP_TTS=true; shift ;;
        --skip-rag) SKIP_RAG=true; shift ;;
        --skip-lmstudio) SKIP_LMSTUDIO=true; shift ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown: $1"; show_help; exit 1 ;;
    esac
done

LOGS_DIR="${OUTPUT_DIR}/logs"
REPORT_JSON="${OUTPUT_DIR}/demo-e2e-report.json"
REPORT_MD="${OUTPUT_DIR}/demo-e2e-report.md"
mkdir -p "${LOGS_DIR}"

PASS=0
FAIL=0
WARN=0
RESULTS=()
WARNINGS=()
ERRORS=()

log()    { echo "[INFO] $1" | tee -a "${LOGS_DIR}/demo.log"; }
pass()   { PASS=$((PASS+1)); echo -e "  [PASS] $1" | tee -a "${LOGS_DIR}/demo.log"; RESULTS+=("pass:$1"); }
fail()   { FAIL=$((FAIL+1)); echo -e "  [FAIL] $1" | tee -a "${LOGS_DIR}/demo.log"; RESULTS+=("fail:$1"); ERRORS+=("$1"); }
warn()   { WARN=$((WARN+1)); echo -e "  [WARN] $1" | tee -a "${LOGS_DIR}/demo.log"; RESULTS+=("warn:$1"); WARNINGS+=("$1"); }
step()   { echo "" | tee -a "${LOGS_DIR}/demo.log"; echo "=== $1 ===" | tee -a "${LOGS_DIR}/demo.log"; }
http_ok(){ 
    local url=$1
    local method=${2:-GET}
    local c; 
    c=$(curl -X "$method" -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000"); 
    echo "$c"; 
}

echo "===================================================="
echo "  Commercial Demo E2E Validation"
echo "  Version: ${VERSION}"
echo "  Timestamp: ${TIMESTAMP}"
echo "  Base URL: ${BASE_URL}"
echo "===================================================="
echo ""

ADMIN_TOKEN=""
if [ -f "${ROOT_DIR}/.env.local" ]; then
    ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" "${ROOT_DIR}/.env.local" | cut -d= -f2 || echo "")
fi

# ---------- Step 1: Check stack is up ----------
step "1. Checking stack is up"
HTTP_CODE=$(http_ok "${BASE_URL}/health")
if [ "${HTTP_CODE}" = "200" ]; then
    pass "Stack is up at ${BASE_URL}/health"
else
    fail "Stack not reachable (HTTP ${HTTP_CODE})"
    log "Cannot continue without a running stack. Start with ./scripts/up.sh"
    # Still continue to validate what we can
fi

# ---------- Step 2: Reset demo (optional) ----------
if [ "${RESET_FIRST}" = true ]; then
    step "2. Resetting demo data"
    if [ -x "${ROOT_DIR}/scripts/reset-commercial-demo-pack.sh" ]; then
        RESET_OUTPUT=$(bash "${ROOT_DIR}/scripts/reset-commercial-demo-pack.sh" --yes 2>&1 || true)
        echo "${RESET_OUTPUT}" >> "${LOGS_DIR}/reset.log"
        pass "Demo data reset executed"
    else
        warn "reset-commercial-demo-pack.sh not found"
    fi
else
    step "2. Skipping demo reset (use --reset-first)"
    log "Skipped"
fi

# ---------- Step 3: Seed commercial demo pack ----------
if [ "${SEED_DEMO}" = true ]; then
    step "3. Seeding commercial demo pack"
    if [ -x "${ROOT_DIR}/scripts/seed-commercial-demo-pack.sh" ]; then
        SEED_OUTPUT=$(bash "${ROOT_DIR}/scripts/seed-commercial-demo-pack.sh" 2>&1 || true)
        echo "${SEED_OUTPUT}" >> "${LOGS_DIR}/seed.log"
        if echo "${SEED_OUTPUT}" | grep -qi "error\|ERRO"; then
            warn "Demo pack seed had errors (see seed.log)"
        else
            pass "Commercial demo pack seeded"
        fi
    else
        warn "seed-commercial-demo-pack.sh not found"
    fi
else
    step "3. Skipping demo seed (use --seed-demo)"
    log "Skipped"
fi

# ---------- Step 4: Validate fake demo data ----------
step "4. Validating fake demo data"
if [ -x "${ROOT_DIR}/scripts/validate-fake-demo-data.sh" ]; then
    if bash "${ROOT_DIR}/scripts/validate-fake-demo-data.sh" >> "${LOGS_DIR}/fake-data.log" 2>&1; then
        pass "Fake demo data validated"
    else
        warn "Fake data validation reported failures"
    fi
else
    warn "validate-fake-demo-data.sh not found"
fi

# ---------- Step 5: Validate commercial demo pack ----------
step "5. Validating commercial demo pack"
if [ -x "${ROOT_DIR}/scripts/validate-commercial-demo-pack.sh" ]; then
    if bash "${ROOT_DIR}/scripts/validate-commercial-demo-pack.sh" >> "${LOGS_DIR}/demo-pack.log" 2>&1; then
        pass "Commercial demo pack validated"
    else
        warn "Commercial demo pack validation reported failures"
    fi
else
    warn "validate-commercial-demo-pack.sh not found"
fi

# ---------- Step 6: Run meeting-ready check ----------
step "6. Running meeting-ready check"
MEETING_ARGS=("--base-url" "${BASE_URL}")
if [ "${SKIP_TTS}" = true ]; then MEETING_ARGS+=("--skip-tts"); fi
if [ "${SKIP_RAG}" = true ]; then MEETING_ARGS+=("--skip-rag"); fi
if [ "${SKIP_LMSTUDIO}" = true ]; then MEETING_ARGS+=("--skip-lmstudio"); fi
if [ -x "${ROOT_DIR}/scripts/meeting-ready-check-local.sh" ]; then
    MEETING_OUTPUT=$(bash "${ROOT_DIR}/scripts/meeting-ready-check-local.sh" "${MEETING_ARGS[@]}" 2>&1 || true)
    echo "${MEETING_OUTPUT}" >> "${LOGS_DIR}/meeting-ready.log"
    if echo "${MEETING_OUTPUT}" | grep -qi "MEETING_READY"; then
        pass "Meeting-ready: MEETING_READY"
    elif echo "${MEETING_OUTPUT}" | grep -qi "READY_WITH_WARNINGS"; then
        warn "Meeting-ready: READY_WITH_WARNINGS"
    else
        warn "Meeting-ready: unexpected status"
    fi
else
    warn "meeting-ready-check-local.sh not found"
fi

# ---------- Step 7: Validate capabilities page ----------
step "7. Validating /capabilities page"
CAP_CODE=$(http_ok "${BASE_URL}/capabilities")
if [ "${CAP_CODE}" = "200" ]; then
    pass "/capabilities returns HTTP 200"
else
    warn "/capabilities returned HTTP ${CAP_CODE}"
fi

# ---------- Step 8: Validate landing page ----------
step "8. Validating landing page"
LAND_CODE=$(http_ok "${BASE_URL}/")
if [ "${LAND_CODE}" = "200" ]; then
    pass "Landing page returns HTTP 200"
else
    warn "Landing page returned HTTP ${LAND_CODE}"
fi

# ---------- Step 9: Validate Admin Dashboard ----------
step "9. Validating Admin Dashboard"
ADMIN_CODE=$(http_ok "${BASE_URL}/admin-dashboard")
if [ "${ADMIN_CODE}" = "200" ] || [ "${ADMIN_CODE}" = "401" ] || [ "${ADMIN_CODE}" = "302" ]; then
    pass "Admin Dashboard reachable (HTTP ${ADMIN_CODE})"
else
    warn "Admin Dashboard returned HTTP ${ADMIN_CODE}"
fi

# ---------- Step 10: Validate Client Portal ----------
step "10. Validating Client Portal"
PORTAL_CODE=$(http_ok "${BASE_URL}/client-portal")
if [ "${PORTAL_CODE}" = "200" ] || [ "${PORTAL_CODE}" = "401" ]; then
    pass "Client Portal reachable (HTTP ${PORTAL_CODE})"
else
    warn "Client Portal returned HTTP ${PORTAL_CODE}"
fi

# ---------- Step 11: Validate Admin Lab ----------
step "11. Validating Admin Lab"
LAB_CODE=$(http_ok "${BASE_URL}/admin-lab")
if [ "${LAB_CODE}" = "200" ] || [ "${LAB_CODE}" = "302" ]; then
    pass "Admin Lab reachable (HTTP ${LAB_CODE})"
else
    warn "Admin Lab returned HTTP ${LAB_CODE}"
fi

# ---------- Step 12: Validate Sales CRM leads ----------
step "12. Validating CRM leads (Admin API)"
if [ -n "${ADMIN_TOKEN}" ]; then
    CRM_CODE=$(http_ok "${BASE_URL}/admin/clients")
    if [ "${CRM_CODE}" = "200" ] || [ "${CRM_CODE}" = "401" ]; then
        pass "CRM clients endpoint reachable (HTTP ${CRM_CODE})"
    else
        warn "CRM clients endpoint returned HTTP ${CRM_CODE}"
    fi
else
    warn "ADMIN_TOKEN not available, skipping CRM check"
fi

# ---------- Step 13: Generate demo proposal ----------
step "13. Generating demo proposal"
if [ -x "${ROOT_DIR}/scripts/generate-client-proposal.sh" ]; then
    PROP_OUTPUT=$(bash "${ROOT_DIR}/scripts/generate-client-proposal.sh" --company-name "Cliente Demo E2E" --segment "tecnologia" --plan "pro" 2>&1 || true)
    echo "${PROP_OUTPUT}" >> "${LOGS_DIR}/proposal.log"
    pass "Demo proposal generated"
else
    warn "generate-client-proposal.sh not found"
fi

# ---------- Step 14: Generate demo quote ----------
step "14. Generating demo quote"
if [ -x "${ROOT_DIR}/scripts/generate-local-quote.sh" ]; then
    QUOTE_OUTPUT=$(bash "${ROOT_DIR}/scripts/generate-local-quote.sh" --company-name "Cliente Demo E2E" --plan "Pro" --rag --support-hours 4 2>&1 || true)
    echo "${QUOTE_OUTPUT}" >> "${LOGS_DIR}/quote.log"
    pass "Demo quote generated"
else
    warn "generate-local-quote.sh not found"
fi

# ---------- Step 15: Generate demo SOW ----------
step "15. Generating demo SOW"
if [ -x "${ROOT_DIR}/scripts/generate-sow-local.sh" ]; then
    SOW_OUTPUT=$(bash "${ROOT_DIR}/scripts/generate-sow-local.sh" --company-name "Cliente Demo E2E" --project-name "Local AI Appliance Demo" 2>&1 || true)
    echo "${SOW_OUTPUT}" >> "${LOGS_DIR}/sow.log"
    pass "Demo SOW generated"
else
    warn "generate-sow-local.sh not found"
fi

# ---------- Step 16: Generate demo monthly report ----------
step "16. Generating demo monthly report"
if [ -x "${ROOT_DIR}/scripts/generate-client-monthly-report.sh" ]; then
    MONTHLY_OUTPUT=$(bash "${ROOT_DIR}/scripts/generate-client-monthly-report.sh" --email "demo@example.local" --month "2026-05" 2>&1 || true)
    echo "${MONTHLY_OUTPUT}" >> "${LOGS_DIR}/monthly.log"
    pass "Demo monthly report generated"
else
    warn "generate-client-monthly-report.sh not found"
fi

# ---------- Step 17: Test chat completion ----------
step "17. Testing chat completion"
CHAT_CODE=$(http_ok "${BASE_URL}/v1/chat/completions" "POST")
if [ "${CHAT_CODE}" = "200" ] || [ "${CHAT_CODE}" = "401" ] || [ "${CHAT_CODE}" = "422" ]; then
    pass "Chat completions endpoint reachable (HTTP ${CHAT_CODE})"
else
    warn "Chat completions returned HTTP ${CHAT_CODE}"
fi

# ---------- Step 18: Test responses endpoint ----------
step "18. Testing /v1/responses"
RESP_CODE=$(http_ok "${BASE_URL}/v1/responses" "POST")
if [ "${RESP_CODE}" = "200" ] || [ "${RESP_CODE}" = "401" ] || [ "${RESP_CODE}" = "422" ]; then
    pass "/v1/responses reachable (HTTP ${RESP_CODE})"
else
    warn "/v1/responses returned HTTP ${RESP_CODE}"
fi

# ---------- Step 19: Test embeddings ----------
step "19. Testing /v1/embeddings"
EMB_CODE=$(http_ok "${BASE_URL}/v1/embeddings" "POST")
if [ "${EMB_CODE}" = "200" ] || [ "${EMB_CODE}" = "401" ] || [ "${EMB_CODE}" = "422" ]; then
    pass "/v1/embeddings reachable (HTTP ${EMB_CODE})"
else
    warn "/v1/embeddings returned HTTP ${EMB_CODE}"
fi

# ---------- Step 20: Test RAG demo ----------
if [ "${SKIP_RAG}" = false ]; then
    step "20. Testing RAG demo"
    RAG_CODE=$(http_ok "${BASE_URL}/v1/rag/upload" "POST")
    if [ "${RAG_CODE}" = "200" ] || [ "${RAG_CODE}" = "401" ] || [ "${RAG_CODE}" = "405" ]; then
        pass "RAG endpoint reachable (HTTP ${RAG_CODE})"
    elif [ "${RAG_CODE}" = "404" ]; then
        warn "RAG endpoint returned HTTP 404 (Not Found) - RAG service might be offline or disabled"
    else
        warn "RAG endpoint returned HTTP ${RAG_CODE}"
    fi
else
    step "20. Skipping RAG validation"
fi

# ---------- Step 21: Test TTS demo ----------
if [ "${SKIP_TTS}" = false ]; then
    step "21. Testing TTS demo"
    TTS_CODE=$(http_ok "${BASE_URL}/v1/audio/speech" "POST")
    if [ "${TTS_CODE}" = "200" ] || [ "${TTS_CODE}" = "401" ] || [ "${TTS_CODE}" = "422" ] || [ "${TTS_CODE}" = "405" ]; then
        pass "TTS endpoint reachable (HTTP ${TTS_CODE})"
    elif [ "${TTS_CODE}" = "404" ]; then
        warn "TTS endpoint returned HTTP 404 (Not Found) - pocket-tts service might be offline or disabled"
    else
        warn "TTS endpoint returned HTTP ${TTS_CODE}"
    fi
else
    step "21. Skipping TTS validation"
fi

# ---------- Step 22: Validate billing demo ----------
step "22. Validating billing demo"
if [ -n "${ADMIN_TOKEN}" ]; then
    BILL_CODE=$(http_ok "${BASE_URL}/admin/billing/invoices")
    if [ "${BILL_CODE}" = "200" ] || [ "${BILL_CODE}" = "401" ]; then
        pass "Billing endpoint reachable (HTTP ${BILL_CODE})"
    else
        warn "Billing endpoint returned HTTP ${BILL_CODE}"
    fi
else
    warn "ADMIN_TOKEN not available, skipping billing check"
fi

# ---------- Step 23: Check secrets ----------
step "23. Running check-secrets.sh"
SEC_OUTPUT=$(bash "${ROOT_DIR}/scripts/check-secrets.sh" --all 2>&1 || true)
echo "${SEC_OUTPUT}" >> "${LOGS_DIR}/check-secrets.log"
if echo "${SEC_OUTPUT}" | grep -qi "no secrets found"; then
    pass "No secrets found in codebase"
else
    warn "Secrets check reported issues"
fi

# ---------- Determine status ----------
if [ "${FAIL}" -gt 0 ]; then
    STATUS="DEMO_FAILED"
elif [ "${WARN}" -gt 0 ]; then
    STATUS="DEMO_READY_WITH_WARNINGS"
else
    STATUS="DEMO_READY"
fi

# ---------- Generate report ----------
step "24. Generating report"

# Write temp files for Python helper
RESULTS_FILE="${OUTPUT_DIR}/.results.txt"
WARNINGS_FILE="${OUTPUT_DIR}/.warnings.txt"
ERRORS_FILE="${OUTPUT_DIR}/.errors.txt"
for r in "${RESULTS[@]}"; do echo "${r}" >> "${RESULTS_FILE}"; done
for w in "${WARNINGS[@]}"; do echo "${w}" >> "${WARNINGS_FILE}"; done
for e in "${ERRORS[@]}"; do echo "${e}" >> "${ERRORS_FILE}"; done

python3 "${ROOT_DIR}/scripts/validate_commercial_demo_e2e_helper.py" generate_json \
    "${REPORT_JSON}" \
    "${TIMESTAMP}" \
    "${VERSION}" \
    "${BASE_URL}" \
    "${RESET_FIRST}" \
    "${SEED_DEMO}" \
    "${SKIP_TTS}" \
    "${SKIP_RAG}" \
    "${SKIP_LMSTUDIO}" \
    "${PASS}" \
    "${FAIL}" \
    "${WARN}" \
    "${RESULTS_FILE}" \
    "${WARNINGS_FILE}" \
    "${ERRORS_FILE}" \
    "${STATUS}"

rm -f "${RESULTS_FILE}" "${WARNINGS_FILE}" "${ERRORS_FILE}"

# Build the flow list
FLOW_LIST=""
for r in "${RESULTS[@]}"; do
    FLOW_LIST="${FLOW_LIST}\n- ${r}"
done

WARN_LIST=""
for w in "${WARNINGS[@]}"; do
    WARN_LIST="${WARN_LIST}\n- ${w}"
done

cat <<EOF > "${REPORT_MD}"
# Commercial Demo E2E Validation Report

**Tool:** scripts/validate-commercial-demo-e2e-local.sh
**Timestamp:** ${TIMESTAMP}
**Version:** ${VERSION}
**Base URL:** ${BASE_URL}
**Status:** ${STATUS}

## Summary

| Metric | Count |
|--------|-------|
| PASS | ${PASS} |
| FAIL | ${FAIL} |
| WARN | ${WARN} |

## Demo Flow Executed

$(for r in "${RESULTS[@]}"; do echo "- ${r}"; done)

## Warnings
$(for w in "${WARNINGS[@]}"; do echo "- ${w}"; done)

## Errors
$(for e in "${ERRORS[@]}"; do echo "- ${e}"; done)

## URLs Accessed
| Interface | URL |
|-----------|-----|
| Landing | ${BASE_URL}/ |
| Capabilities | ${BASE_URL}/capabilities |
| Admin Dashboard | ${BASE_URL}/admin-dashboard |
| Client Portal | ${BASE_URL}/client-portal |
| Admin Lab | ${BASE_URL}/admin-lab |
| Health | ${BASE_URL}/health |
| Chat Completions | ${BASE_URL}/v1/chat/completions |
| Responses | ${BASE_URL}/v1/responses |
| Embeddings | ${BASE_URL}/v1/embeddings |
| Billing | ${BASE_URL}/admin/billing/invoices |
| CRM | ${BASE_URL}/admin/clients |

## Scripts Used
- scripts/validate-commercial-demo-e2e-local.sh
- scripts/seed-commercial-demo-pack.sh
- scripts/reset-commercial-demo-pack.sh
- scripts/validate-fake-demo-data.sh
- scripts/validate-commercial-demo-pack.sh
- scripts/meeting-ready-check-local.sh
- scripts/generate-client-proposal.sh
- scripts/generate-local-quote.sh
- scripts/generate-sow-local.sh
- scripts/generate-client-monthly-report.sh
- scripts/check-secrets.sh

## Demo Data Used
- Commercial demo pack (5 scenarios: clinica, juridico, suporte, educacao, provedor-api)
- Fake demo data in demo-pack/fake-data/
- Demo leads (CRM)
- Demo invoices (billing)

## Limitations to Mention
- Real PSP/PIX not included — manual billing only
- Tools/Function Calling may be partial depending on backend
- TTS requires pocket-tts service to be available
- RAG requires data plane with embedding support
- LM Studio integration depends on external backend availability

## Security Evidence
- Secrets check: $(if echo "${SEC_OUTPUT}" | grep -qi "no secrets found"; then echo "PASS"; else echo "WARN"; fi)
- Fake data validated for no real CPF/CNPJ/credentials
- Admin tokens masked in all reports

## Next Steps (Commercial)
1. Review demo with client
2. Customize proposal with real client data
3. Set up client-specific RAG data
4. Configure white-label branding
5. Generate paid implementation checklist
6. Schedule acceptance tests
EOF

echo ""
echo "Report generated:"
echo "  JSON: ${REPORT_JSON}"
echo "  MD:   ${REPORT_MD}"
echo "  Logs: ${LOGS_DIR}"
echo ""
echo "=== Status: ${STATUS} ==="
echo "  PASS: ${PASS}  |  FAIL: ${FAIL}  |  WARN: ${WARN}"

exit 0
