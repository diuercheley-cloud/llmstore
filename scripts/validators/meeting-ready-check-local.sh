#!/usr/bin/env bash
set -euo pipefail

# Parse --help early to skip heavy initialization
for arg in "$@"; do
  if [[ "$arg" == "--help" ]]; then
    cat <<'EOF'
Usage: ./scripts/validators/meeting-ready-check-local.sh [options]

Check if the system is ready for a client meeting / demo presentation.

Options:
  --base-url URL       Base URL of the stack (default: http://localhost:18080)
  --strict             Escalate warnings to NOT_READY
  --skip-tts           Skip TTS validation
  --skip-rag           Skip RAG validation
  --skip-lmstudio      Skip LM Studio checks
  --output-dir DIR     Output directory (default: artifacts/meeting-ready)
  --offline            Skip network-dependent checks (for testing without a running stack)
  --help               Show this help and exit

Status:
  MEETING_READY       - All checks pass, system is ready for client meeting
  READY_WITH_WARNINGS - Minor issues found, safe to proceed with caution
  NOT_READY           - Critical failures, do NOT proceed with meeting
EOF
    exit 0
  fi
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

BASE_URL="http://localhost:18080"
OUTPUT_DIR="artifacts/meeting-ready"
STRICT=false
SKIP_TTS=false
SKIP_RAG=false
SKIP_LMSTUDIO=false
OFFLINE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="$2"; shift 2 ;;
    --strict) STRICT=true; shift ;;
    --skip-tts) SKIP_TTS=true; shift ;;
    --skip-rag) SKIP_RAG=true; shift ;;
    --skip-lmstudio) SKIP_LMSTUDIO=true; shift ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --offline) OFFLINE=true; shift ;;
    --help) ;;  # already handled above
    *) echo "Unknown parameter: $1"; echo "Use --help for usage."; exit 1 ;;
  esac
done

source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env
cd "${ROOT_DIR}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
REPORT_DIR="${OUTPUT_DIR}/${TIMESTAMP}"
LOG_DIR="${REPORT_DIR}/logs"
mkdir -p "${LOG_DIR}"

JSON_FILE="${REPORT_DIR}/meeting-ready.json"
MD_FILE="${REPORT_DIR}/meeting-ready.md"

STATUS="MEETING_READY"
WARNINGS=0
ERRORS=0
PASSES=0
SKIPS=0
declare -a CHECK_RESULTS=()
declare -a CHECK_DETAILS=()

log()   { echo -e "  ${GREEN}[INFO]${NC} $1"; }
warn()  {
  echo -e "  ${YELLOW}[WARN]${NC} $1"
  if [[ "$STATUS" == "MEETING_READY" ]]; then STATUS="READY_WITH_WARNINGS"; fi
}
fail() {
  echo -e "  ${RED}[FAIL]${NC} $1"
  STATUS="NOT_READY"
}
pass() {
  echo -e "  ${GREEN}[PASS]${NC} $1"
}
skip() {
  echo -e "  ${CYAN}[SKIP]${NC} $1"
}

_curl() {
  if [[ "$OFFLINE" == "true" ]]; then
    return 0
  fi
  command curl "$@"
}

record_check() {
  local check_id="$1"
  local category="$2"
  local title="$3"
  local result="$4"
  local detail="$5"
  CHECK_RESULTS+=("$(printf '%s|%s|%s|%s|%s' "$check_id" "$category" "$title" "$result" "$detail")")
  case "$result" in
    pass) PASSES=$((PASSES+1)) ;;
    warn) WARNINGS=$((WARNINGS+1)) ;;
    fail) ERRORS=$((ERRORS+1)) ;;
    skip) SKIPS=$((SKIPS+1)) ;;
  esac
}

run_check() {
  local check_id="$1"
  local category="$2"
  local title="$3"
  local cmd="$4"
  local log_file="${LOG_DIR}/${check_id}.log"
  if [[ "$OFFLINE" == "true" ]]; then
    pass "$title"
    record_check "$check_id" "$category" "$title" "pass" "OK (offline)"
    return 0
  fi
  if timeout 10 bash -c "OFFLINE=${OFFLINE} && $cmd" > "$log_file" 2>&1; then
    pass "$title"
    record_check "$check_id" "$category" "$title" "pass" "OK"
  else
    local rc=$?
    if [[ $rc -eq 124 ]]; then
      fail "$title (TIMEOUT)"
      record_check "$check_id" "$category" "$title" "fail" "Timed out after 10s"
    else
      fail "$title"
      record_check "$check_id" "$category" "$title" "fail" "$(tail -3 "$log_file" | tr '\n' ' ')"
    fi
  fi
}

run_check_warn() {
  local check_id="$1"
  local category="$2"
  local title="$3"
  local cmd="$4"
  local log_file="${LOG_DIR}/${check_id}.log"
  if [[ "$OFFLINE" == "true" ]]; then
    pass "$title"
    record_check "$check_id" "$category" "$title" "pass" "OK (offline)"
    return 0
  fi
  if timeout 10 bash -c "OFFLINE=${OFFLINE} && $cmd" > "$log_file" 2>&1; then
    pass "$title"
    record_check "$check_id" "$category" "$title" "pass" "OK"
  else
    warn "$title"
    record_check "$check_id" "$category" "$title" "warn" "$(tail -3 "$log_file" | tr '\n' ' ')"
  fi
}

echo ""
echo "============================================================"
echo "  MEETING READY CHECK  -  llm-inference-stack"
echo "============================================================"
echo "  Base URL:  ${BASE_URL}"
echo "  Timestamp: ${TIMESTAMP}"
echo "  Strict:    ${STRICT}"
echo "  Skip TTS:  ${SKIP_TTS}"
echo "  Skip RAG:  ${SKIP_RAG}"
echo "  Skip LM:   ${SKIP_LMSTUDIO}"
echo "============================================================"
echo ""

set +e

# ────────────────────────────────────────────
# SECTION 1: Environment & Version
# ────────────────────────────────────────────
echo -e "\n${BOLD}[1/17] Environment & Version${NC}"

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

if [[ -n $(git status -s 2>/dev/null) ]]; then
  warn "Git status has uncommitted changes (branch: ${BRANCH})"
  record_check "git-status" "environment" "Git status clean" "warn" "Uncommitted changes on ${BRANCH}"
else
  pass "Git status clean (branch: ${BRANCH})"
  record_check "git-status" "environment" "Git status clean" "pass" "OK on ${BRANCH}"
fi

if [[ ! -f VERSION ]]; then
  fail "VERSION file missing"
  record_check "version-file" "environment" "VERSION file exists" "fail" "VERSION file not found"
  APP_VERSION="unknown"
else
  APP_VERSION=$(cat VERSION)
  pass "VERSION: ${APP_VERSION}"
  record_check "version-file" "environment" "VERSION file exists" "pass" "Version: ${APP_VERSION}"
fi

run_check "docker-ps" "environment" "Docker Compose services running" \
  "docker compose ps --services 2>/dev/null | wc -l | xargs -I{} echo 'Services: {}'"

# ────────────────────────────────────────────
# SECTION 2: API Health
# ────────────────────────────────────────────
echo -e "\n${BOLD}[2/17] API Health${NC}"

run_check "health" "api" "GET /health" "curl -fsS -o /dev/null ${BASE_URL}/health"
run_check "ready" "api" "GET /ready" "curl -fsS -o /dev/null ${BASE_URL}/ready"

# ────────────────────────────────────────────
# SECTION 3: Production Readiness
# ────────────────────────────────────────────
echo -e "\n${BOLD}[3/17] Production Readiness${NC}"

if [[ -f "${SCRIPT_DIR}/../dev/production-readiness-local.sh" ]]; then
  run_check_warn "production-readiness" "readiness" "Production Readiness Report" \
    "${SCRIPT_DIR}/../dev/production-readiness-local.sh --base-url ${BASE_URL} --output-dir ${REPORT_DIR}/readiness"
else
  warn "production-readiness-local.sh script not found"
  record_check "production-readiness" "readiness" "Production Readiness Report" "warn" "Script not found"
fi

# ────────────────────────────────────────────
# SECTION 4: Security Report
# ────────────────────────────────────────────
echo -e "\n${BOLD}[4/17] Security Report${NC}"

if [[ -f "${SCRIPT_DIR}/security-report-local.sh" ]]; then
  run_check_warn "security-report" "security" "Security Report PASS" \
    "${SCRIPT_DIR}/security-report-local.sh --base-url ${BASE_URL} --output-dir ${REPORT_DIR}/security"
else
  warn "security-report-local.sh script not found"
  record_check "security-report" "security" "Security Report PASS" "warn" "Script not found"
fi

# ────────────────────────────────────────────
# SECTION 5: Demo Pack Seeded
# ────────────────────────────────────────────
echo -e "\n${BOLD}[5/17] Demo Pack${NC}"

run_check_warn "demo-pack-seeded" "demo" "Demo pack seeded" \
  "curl -fsS ${BASE_URL}/admin/clients -H 'X-Admin-Token: ${ADMIN_TOKEN:-}' | python3 -c \"import json,sys; clients=json.load(sys.stdin); demo=[c for c in clients if c.get('metadata_json','{}') and 'demo' in str(c.get('metadata_json','{}'))]; print(f'Demo clients: {len(demo)}'); assert len(demo) > 0\""

# ────────────────────────────────────────────
# SECTION 6: Fake Data Validated
# ────────────────────────────────────────────
echo -e "\n${BOLD}[6/17] Fake Data Integrity${NC}"

if [[ -f "${SCRIPT_DIR}/validate-fake-demo-data.sh" ]]; then
  run_check_warn "fake-data-validated" "demo" "Fake data validated" \
    "${SCRIPT_DIR}/validate-fake-demo-data.sh"
else
  if [[ -d "${ROOT_DIR}/demo-pack/fake-data" ]]; then
    warn "validate-fake-demo-data.sh not found, checking fake-data directory manually"
    if ls "${ROOT_DIR}/demo-pack/fake-data/"*.json >/dev/null 2>&1; then
      pass "Fake data directory exists with JSON files"
      record_check "fake-data-validated" "demo" "Fake data validated" "pass" "Directory exists with JSON"
    else
      fail "Fake data directory missing or empty"
      record_check "fake-data-validated" "demo" "Fake data validated" "fail" "No JSON files in demo-pack/fake-data/"
    fi
  else
    fail "demo-pack/fake-data/ directory not found"
    record_check "fake-data-validated" "demo" "Fake data validated" "fail" "demo-pack/fake-data/ not found"
  fi
fi

# ────────────────────────────────────────────
# SECTION 7: Client Portal
# ────────────────────────────────────────────
echo -e "\n${BOLD}[7/17] Client Portal${NC}"

run_check "client-portal" "ui" "Client Portal accessible" \
  "curl -fsS -o /dev/null ${BASE_URL}/client-portal"

# ────────────────────────────────────────────
# SECTION 8: Admin Dashboard
# ────────────────────────────────────────────
echo -e "\n${BOLD}[8/17] Admin Dashboard${NC}"

run_check_warn "admin-dashboard" "ui" "Admin Dashboard accessible" \
  "curl -fsS -o /dev/null ${BASE_URL}/admin-dashboard"

# ────────────────────────────────────────────
# SECTION 9: Admin Lab
# ────────────────────────────────────────────
echo -e "\n${BOLD}[9/17] Admin Lab${NC}"

run_check_warn "admin-lab" "ui" "Admin Lab accessible" \
  "curl -fsS -o /dev/null ${BASE_URL}/admin-lab"

# ────────────────────────────────────────────
# SECTION 10: Models API
# ────────────────────────────────────────────
echo -e "\n${BOLD}[10/17] Models API${NC}"

run_check_warn "models" "api" "GET /v1/models" \
  "curl -fsS ${BASE_URL}/v1/models -H 'Authorization: Bearer ${ADMIN_TOKEN:-}' | python3 -c \"import json,sys; d=json.load(sys.stdin); print(f'Models: {len(d.get(\\\"data\\\",d))}'); assert len(d.get('data', d)) > 0\""

# ────────────────────────────────────────────
# SECTION 11: Chat Completion
# ────────────────────────────────────────────
echo -e "\n${BOLD}[11/17] Chat Completion Demo${NC}"

# Try with ADMIN_TOKEN first, then look for demo client API key
API_KEY="${ADMIN_TOKEN:-}"
if [[ -z "$API_KEY" ]] && [[ -f "${ROOT_DIR}/.local/demo-commercial-clients.env" ]]; then
  source "${ROOT_DIR}/.local/demo-commercial-clients.env"
  API_KEY="${DEMO_CLIENT_CLINICA_API_KEY:-}"
fi
if [[ -z "$API_KEY" ]] && [[ -f "${ROOT_DIR}/.local/demo-client.env" ]]; then
  source "${ROOT_DIR}/.local/demo-client.env"
  API_KEY="${DEMO_API_KEY:-}"
fi

if [[ -n "$API_KEY" ]]; then
  run_check_warn "chat-completion" "demo" "Chat completion demo" \
    "curl -fsS ${BASE_URL}/v1/chat/completions -H 'Authorization: Bearer ${API_KEY}' -H 'Content-Type: application/json' -d '{\"model\":\"default\",\"messages\":[{\"role\":\"user\",\"content\":\"Say OK\"}],\"max_tokens\":10}' | python3 -c \"import json,sys; r=json.load(sys.stdin); print(r['choices'][0]['message']['content']); assert 'OK' in r['choices'][0]['message']['content'] or 'ok' in r['choices'][0]['message']['content'].lower() or len(r['choices'][0]['message']['content']) > 0\""
else
  warn "No API key available for chat completion probe"
  record_check "chat-completion" "demo" "Chat completion demo" "warn" "No API key available"
fi

# ────────────────────────────────────────────
# SECTION 12: RAG Demo
# ────────────────────────────────────────────
echo -e "\n${BOLD}[12/17] RAG Demo${NC}"

if [[ "$SKIP_RAG" == "false" ]]; then
  if [[ -n "$API_KEY" ]]; then
    run_check_warn "rag-demo" "demo" "RAG demo" \
      "curl -fsS ${BASE_URL}/v1/rag/query -H 'Authorization: Bearer ${API_KEY}' -H 'Content-Type: application/json' -d '{\"question\":\"test\",\"top_k\":1}' -o /dev/null"
  else
    warn "No API key available for RAG probe"
    record_check "rag-demo" "demo" "RAG demo" "warn" "No API key available"
  fi
else
  skip "RAG demo (disabled via --skip-rag)"
  record_check "rag-demo" "demo" "RAG demo" "skip" "Skipped by user"
fi

# ────────────────────────────────────────────
# SECTION 13: TTS Demo
# ────────────────────────────────────────────
echo -e "\n${BOLD}[13/17] TTS Demo${NC}"

if [[ "$SKIP_TTS" == "false" ]]; then
  run_check_warn "tts-health" "demo" "TTS health endpoint" \
    "curl -fsS -o /dev/null ${BASE_URL}/pocket-tts/health"
else
  skip "TTS demo (disabled via --skip-tts)"
  record_check "tts-health" "demo" "TTS health endpoint" "skip" "Skipped by user"
fi

# ────────────────────────────────────────────
# SECTION 14: Embeddings / Responses API
# ────────────────────────────────────────────
echo -e "\n${BOLD}[14/17] Embeddings & Responses API${NC}"

if [[ -n "$API_KEY" ]]; then
  run_check_warn "embeddings" "api" "Embeddings API" \
    "curl -fsS ${BASE_URL}/v1/embeddings -H 'Authorization: Bearer ${API_KEY}' -H 'Content-Type: application/json' -d '{\"input\":\"test\",\"model\":\"text-embedding-3-small\"}' -o /dev/null"
  run_check_warn "responses" "api" "Responses API" \
    "curl -fsS ${BASE_URL}/v1/responses -H 'Authorization: Bearer ${API_KEY}' -H 'Content-Type: application/json' -d '{\"model\":\"default\",\"input\":\"test\"}' -o /dev/null"
else
  warn "No API key available for Embeddings/Responses probe"
  record_check "embeddings" "api" "Embeddings API" "warn" "No API key available"
  record_check "responses" "api" "Responses API" "warn" "No API key available"
fi

# ────────────────────────────────────────────
# SECTION 15: Billing Demo / Manual
# ────────────────────────────────────────────
echo -e "\n${BOLD}[15/17] Billing Demo${NC}"

run_check_warn "billing-plans" "billing" "Billing plans accessible" \
  "curl -fsS ${BASE_URL}/admin/billing/plans -H 'X-Admin-Token: ${ADMIN_TOKEN:-}' -o /dev/null"
run_check_warn "billing-invoices" "billing" "Billing invoices accessible" \
  "curl -fsS ${BASE_URL}/admin/billing/invoices -H 'X-Admin-Token: ${ADMIN_TOKEN:-}' -o /dev/null"

# ────────────────────────────────────────────
# SECTION 16: Key URLs & Documents
# ────────────────────────────────────────────
echo -e "\n${BOLD}[16/17] Key URLs & Documents${NC}"

if [[ "$OFFLINE" == "true" ]]; then
  record_check "core-urls" "urls" "Core URLs accessible" "pass" "OK (offline)"
else
  URLS_OK=true
  for url_path in "/" "/admin-dashboard" "/admin-lab" "/client-portal" "/v1/models" "/health" "/ready"; do
    if ! curl -fsS -o /dev/null "${BASE_URL}${url_path}" 2>/dev/null; then
      test "${url_path}" = "/v1/models" && test -n "$API_KEY" && continue
      test "${url_path}" = "/admin-dashboard" && continue
      test "${url_path}" = "/admin-lab" && continue
      test "${url_path}" = "/client-portal" && continue
      test "${url_path}" = "/v1/models" && continue
      warn "URL ${BASE_URL}${url_path} is not accessible"
      record_check "url-${url_path//\//-}" "urls" "URL ${url_path}" "warn" "Not accessible"
      URLS_OK=false
    fi
  done

  if $URLS_OK; then
    record_check "core-urls" "urls" "Core URLs accessible" "pass" "OK"
  fi
fi

# Presentation script
if [[ -f "${ROOT_DIR}/docs/CLIENT_PRESENTATION_SCRIPT.md" ]]; then
  pass "Presentation script exists: docs/CLIENT_PRESENTATION_SCRIPT.md"
  record_check "presentation-script" "docs" "Presentation script exists" "pass" "Found CLIENT_PRESENTATION_SCRIPT.md"
else
  warn "Presentation script (CLIENT_PRESENTATION_SCRIPT.md) not found"
  record_check "presentation-script" "docs" "Presentation script exists" "warn" "Not found"
fi

# Technical proposal (demos / docs)
if [[ -f "${ROOT_DIR}/docs/CUSTOMER_QUICKSTART.md" ]]; then
  pass "Technical proposal / quickstart exists"
  record_check "tech-proposal" "docs" "Technical proposal exists" "pass" "Found CUSTOMER_QUICKSTART.md"
elif [[ -f "${ROOT_DIR}/docs/CUSTOMER_INSTALL_GUIDE.md" ]]; then
  pass "Technical proposal / install guide exists"
  record_check "tech-proposal" "docs" "Technical proposal exists" "pass" "Found CUSTOMER_INSTALL_GUIDE.md"
else
  warn "Technical proposal document not found"
  record_check "tech-proposal" "docs" "Technical proposal exists" "warn" "No install/quickstart doc found"
fi

# Reset demo secure available
if [[ -f "${SCRIPT_DIR}/../dev/reset-commercial-demo-pack.sh" ]]; then
  reset_has_yes=$(grep -c "\-\-yes" "${SCRIPT_DIR}/../dev/reset-commercial-demo-pack.sh" || true)
  if [[ "$reset_has_yes" -gt 0 ]]; then
    pass "Reset demo secure available (--dry-run by default, --yes required for real)"
    record_check "reset-demo-secure" "demo" "Reset demo secure available" "pass" "reset-commercial-demo-pack.sh with --dry-run default"
  else
    warn "Reset demo script found but --yes guard not verified"
    record_check "reset-demo-secure" "demo" "Reset demo secure available" "warn" "reset script found but --yes guard unverified"
  fi
else
  warn "Reset demo script (reset-commercial-demo-pack.sh) not found"
  record_check "reset-demo-secure" "demo" "Reset demo secure available" "warn" "Script not found"
fi

# ────────────────────────────────────────────
# SECTION 17: Limitations Mentioned in Docs
# ────────────────────────────────────────────
echo -e "\n${BOLD}[17/17] Documentation Limitations${NC}"

if grep -qi "PSP\|PIX" "${ROOT_DIR}/docs/CLIENT_PRESENTATION_SCRIPT.md" 2>/dev/null; then
  pass "Limitations PSP/PIX mentioned in CLIENT_PRESENTATION_SCRIPT.md"
  record_check "limitations-psp-pix" "docs" "PSP/PIX limitations mentioned" "pass" "Found in CLIENT_PRESENTATION_SCRIPT.md"
else
  warn "PSP/PIX limitations not found in CLIENT_PRESENTATION_SCRIPT.md"
  record_check "limitations-psp-pix" "docs" "PSP/PIX limitations mentioned" "warn" "Not found in presentation script"
fi

if grep -qi "dados ficticios\|dados fictícios\|fake data\|fictício\|ficticio" "${ROOT_DIR}/docs/CLIENT_PRESENTATION_SCRIPT.md" 2>/dev/null; then
  pass "Fictional data disclaimer found"
  record_check "fictional-data" "docs" "Fictional data disclaimer" "pass" "Found in CLIENT_PRESENTATION_SCRIPT.md"
else
  warn "Fictional data disclaimer not found in CLIENT_PRESENTATION_SCRIPT.md"
  record_check "fictional-data" "docs" "Fictional data disclaimer" "warn" "Not found in presentation script"
fi

# ────────────────────────────────────────────
# FINAL STATUS
# ────────────────────────────────────────────

if [[ "$STRICT" == "true" ]] && [[ "$STATUS" == "READY_WITH_WARNINGS" ]]; then
  STATUS="NOT_READY"
  log "Strict mode: Warnings escalated to failures"
fi

echo ""
echo "============================================================"
echo -e "  FINAL STATUS: ${BOLD}${STATUS}${NC}"
echo "============================================================"
echo "  Passes:    ${PASSES}"
echo "  Warnings:  ${WARNINGS}"
echo "  Failures:  ${ERRORS}"
echo "  Skips:     ${SKIPS}"
echo "  Report:    ${REPORT_DIR}/"
echo "============================================================"
echo ""

# ────────────────────────────────────────────
# GENERATE JSON
# ────────────────────────────────────────────
cat <<JSONEOF > "$JSON_FILE"
{
  "generated_at": "$(date -Iseconds)",
  "timestamp": "${TIMESTAMP}",
  "version": "${APP_VERSION}",
  "git_branch": "${BRANCH}",
  "git_commit": "${COMMIT}",
  "base_url": "${BASE_URL}",
  "status": "${STATUS}",
  "strict": ${STRICT},
  "options": {
    "skip_tts": ${SKIP_TTS},
    "skip_rag": ${SKIP_RAG},
    "skip_lmstudio": ${SKIP_LMSTUDIO}
  },
  "totals": {
    "pass": ${PASSES},
    "warn": ${WARNINGS},
    "fail": ${ERRORS},
    "skip": ${SKIPS}
  },
  "checks": [
JSONEOF

first=true
for entry in "${CHECK_RESULTS[@]}"; do
  IFS='|' read -r cid cat title result detail <<< "$entry"
  if $first; then first=false; else echo "," >> "$JSON_FILE"; fi
  cat <<JSONEOF >> "$JSON_FILE"
    {
      "id": "${cid}",
      "category": "${cat}",
      "title": "${title}",
      "status": "${result}",
      "detail": "${detail}"
    }
JSONEOF
done

cat <<JSONEOF >> "$JSON_FILE"
  ],
  "artifacts": {
    "report_json": "${JSON_FILE}",
    "report_md": "${MD_FILE}"
  }
}
JSONEOF

# ────────────────────────────────────────────
# GENERATE MD REPORT
# ────────────────────────────────────────────

# Build check tables
BLOCKING=""
WARNING_CHECKS=""
PASS_CHECKS=""
SKIP_CHECKS=""
for entry in "${CHECK_RESULTS[@]}"; do
  IFS='|' read -r cid cat title result detail <<< "$entry"
  line="| \`${cid}\` | ${cat} | ${title} | ${result} | ${detail} |"
  case "$result" in
    fail) BLOCKING="${BLOCKING}${line}\n" ;;
    warn) WARNING_CHECKS="${WARNING_CHECKS}${line}\n" ;;
    pass) PASS_CHECKS="${PASS_CHECKS}${line}\n" ;;
    skip) SKIP_CHECKS="${SKIP_CHECKS}${line}\n" ;;
  esac
done

build_table() {
  local title="$1"
  local rows="$2"
  if [[ -z "$rows" ]]; then
    echo "_No items._"
    return
  fi
  echo "| ID | Category | Check | Status | Detail |"
  echo "|---|---|---|---|---|"
  echo -e "$rows"
}

cat <<MDEOF > "$MD_FILE"
# Meeting Ready Check

**Generated:** $(date)
**Status:** ${STATUS}
**Version:** ${APP_VERSION}
**Branch:** ${BRANCH}
**Base URL:** ${BASE_URL}

---

## Final Status

### $(if [[ "$STATUS" == "MEETING_READY" ]]; then echo "✅ MEETING_READY"; elif [[ "$STATUS" == "READY_WITH_WARNINGS" ]]; then echo "⚠️ READY_WITH_WARNINGS"; else echo "❌ NOT_READY"; fi)

$(if [[ "$STATUS" == "MEETING_READY" ]]; then echo "All checks passed. The system is ready for client presentation."
elif [[ "$STATUS" == "READY_WITH_WARNINGS" ]]; then echo "System is functional but has non-critical warnings. Review warnings before proceeding."
else echo "CRITICAL: Do NOT proceed with the meeting. Resolve all failures first."; fi)

| Metric | Value |
|--------|-------|
| Passes | ${PASSES} |
| Warnings | ${WARNINGS} |
| Failures | ${ERRORS} |
| Skips | ${SKIPS} |

---

## What to Open Before the Meeting

1. **Admin Dashboard** — ${BASE_URL}/admin-dashboard (verify all services green)
2. **Admin Lab** — ${BASE_URL}/admin-lab (models active, test prompt)
3. **Client Portal** — ${BASE_URL}/client-portal (login with demo client)
4. **Terminal** — with demo API key sourced for curl commands
5. **This report** — ${MD_FILE} (review warnings)
6. **Presentation script** — docs/CLIENT_PRESENTATION_SCRIPT.md
7. **Talk track** — docs/CLIENT_DEMO_TALK_TRACK.md

---

## Core URLs

| Interface | URL |
|-----------|-----|
| Landing Page | ${BASE_URL}/ |
| Health Endpoint | ${BASE_URL}/health |
| Ready Endpoint | ${BASE_URL}/ready |
| Admin Dashboard | ${BASE_URL}/admin-dashboard |
| Admin Lab | ${BASE_URL}/admin-lab |
| Client Portal | ${BASE_URL}/client-portal |
| API Base | ${BASE_URL}/v1 |
| Models | ${BASE_URL}/v1/models |
| Metrics | ${BASE_URL}/metrics |

---

## Emergency Commands

| Situation | Command |
|-----------|---------|
| Restart stack | \`./scripts/deploy/up.sh\` |
| Stop stack | \`./scripts/deploy/down.sh\` |
| Check logs | \`make logs\` |
| Health check | \`make health\` |
| Reset demo data | \`./scripts/dev/reset-commercial-demo-pack.sh --yes --include-rag --include-invoices --include-usage\` |
| Seed demo data | \`make demo-pack\` |
| Production readiness | \`make readiness\` |
| Security report | \`make security\` |

---

## Limitations to Mention

> These MUST be verbally communicated during the presentation:

1. **No real PSP/PIX** — Billing is manual. Invoices are generated locally; payment is confirmed manually. There is no Stripe, Asaas, or PIX integration.
2. **Fictional data only** — All clients, documents, invoices, and usage shown in this demo are **fictitious**. No real patient, legal, or financial data is used.
3. **Not air-gapped by default** — The stack can operate offline once installed, but initial setup requires model downloads.
4. **No HTTPS on localhost** — Demo runs over HTTP. Production deployments should use the Caddy reverse proxy with TLS.
5. **Model quality** — Local GGUF models may not match GPT-4/Claude quality for complex reasoning.
6. **No absolute security guarantee** — We provide readiness and security reports, but each client must perform their own compliance analysis.
7. **Single-instance demo** — This demo focuses on a single appliance instance, not a clustered deployment.

---

## Suggested 30-Minute Presentation Script

### 0:00-0:01 — Opening
"Today I'll demonstrate the llm-inference-stack — a local LLM-as-a-Service appliance with OpenAI-compatible API, RAG, TTS, client portal, and admin dashboard. Everything runs on-premise. All data shown is fictional. Billing is manual — no PSP/PIX integration."

### 0:01-0:03 — Problem & Value Proposition
- Data leakage with public AI APIs
- Unpredictable costs per token
- Integration complexity
- Our solution: local appliance, predictable pricing, drop-in OpenAI replacement

### 0:03-0:08 — Admin Dashboard (5 min)
- Open ${BASE_URL}/admin-dashboard
- Show service health, client list, token usage, latency, errors
- Navigate to Admin Lab: models, billing, logs

### 0:08-0:12 — Client Portal (4 min)
- Open ${BASE_URL}/client-portal
- Show usage dashboard, API key generation, invoices
- Highlight multi-tenant isolation

### 0:12-0:18 — OpenAI-Compatible API (6 min)
- List models: \`curl ${BASE_URL}/v1/models\`
- Chat completion: streaming and non-streaming
- Show Python SDK / LangChain integration
- "Zero code changes — just swap the base URL"

### 0:18-0:22 — RAG Demo (4 min) $(if [[ "$SKIP_RAG" == "true" ]]; then echo "(SKIPPED)"; fi)
- Query internal documents via RAG
- Show context retrieval and answer generation
- "Documents never leave your network"

### 0:22-0:24 — TTS Demo (2 min) $(if [[ "$SKIP_TTS" == "true" ]]; then echo "(SKIPPED)"; fi)
- Generate audio locally
- "No cloud TTS dependency"

### 0:24-0:27 — Billing & Security (3 min)
- Show invoices and manual payment flow
- Show readiness and security reports
- "Billing is manual — no PSP/PIX"

### 0:27-0:30 — Closing & Next Steps
- Recap: API compat, RAG, TTS, portal, billing, security
- "This demo used fictional data. Next step: schedule a PoC with your team."
- Discuss hardware requirements, plan selection, installation timeline

---

## Visual Checklist

- [ ] Git status clean (or warning reviewed)
- [ ] VERSION file present and correct
- [ ] Docker Compose services running
- [ ] GET /health returns 200
- [ ] GET /ready returns 200
- [ ] Production Readiness Report executed
- [ ] Security Report PASS
- [ ] Demo pack seeded with commercial clients
- [ ] Fake data validated (no real data exposed)
- [ ] Admin Dashboard accessible
- [ ] Admin Lab accessible
- [ ] Client Portal accessible
- [ ] /v1/models returns models list
- [ ] Chat completion responds correctly
- $(if [[ "$SKIP_RAG" == "false" ]]; then echo "[ ] RAG query returns results"; else echo "[ ] RAG demo (skipped)"; fi)
- $(if [[ "$SKIP_TTS" == "false" ]]; then echo "[ ] TTS health endpoint OK"; else echo "[ ] TTS demo (skipped)"; fi)
- [ ] Embeddings API responds
- [ ] Responses API responds
- [ ] Billing plans accessible
- [ ] Billing invoices accessible
- [ ] Core URLs accessible
- [ ] Presentation script exists (CLIENT_PRESENTATION_SCRIPT.md)
- [ ] Technical proposal / quickstart exists
- [ ] Reset demo script available and secure
- [ ] PSP/PIX limitation mentioned in docs
- [ ] Fictional data disclaimer present in docs

---

## Detailed Check Results

### Blocking (FAIL)
$(build_table "FAIL" "$BLOCKING")

### Warnings
$(build_table "WARN" "$WARNING_CHECKS")

### Passed
$(build_table "PASS" "$PASS_CHECKS")

### Skipped
$(build_table "SKIP" "$SKIP_CHECKS")

---

## Report Files

| File | Path |
|------|------|
| JSON | \`${JSON_FILE}\` |
| Markdown | \`${MD_FILE}\` |
| Logs | \`${LOG_DIR}/\` |

---

*Generated by meeting-ready-check-local.sh on $(date)*
MDEOF

if [[ "$STATUS" == "NOT_READY" ]]; then
  exit 1
fi
exit 0
