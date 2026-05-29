#!/bin/bash
# Owner: platform-ops
# Validate Agentic Production ON readiness — runtime live, not safe-default.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL="${KLEBER_BASE_URL:-http://localhost:18080}"
API_KEY="${KLEBER_API_KEY}"
ARTIFACT_DIR="artifacts/readiness"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PASS=0
FAIL=0
RESULTS=()

# Resolve API key from local env files
if [ -z "${API_KEY}" ]; then
  for f in .env.local .env; do
    if [ -f "${f}" ]; then
      API_KEY="$(grep -E '^ADMIN_TOKEN=' "${f}" | head -n1 | cut -d= -f2- | tr -d '"' || true)"
      [ -n "${API_KEY}" ] && break
    fi
  done
fi

CURL="curl -sS -H 'X-Admin-Token: ${API_KEY}' -H 'Content-Type: application/json'"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
check() {
  local name="$1" status="$2" detail="$3"
  RESULTS+=("${status}|${name}|${detail}")
  case "${status}" in
    PASS) ((PASS++)) ;;
    FAIL) ((FAIL++)) ;;
  esac
  printf "  %-8s %-55s %s\n" "${status}" "${name}" "${detail}"
}

api_post() {
  eval "${CURL}" -X POST "$@"
}

api_get() {
  eval "${CURL}" -X GET "$@"
}

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
echo "==============================================================="
echo "  AGENTIC PRODUCTION-ON READINESS VALIDATION"
echo "  Runtime live — no safe-default pass-through"
echo "  ${TIMESTAMP}"
echo "==============================================================="
echo ""

# ---------------------------------------------------------------------------
# Check 1: Profile flag validation — runtime must be ON
# ---------------------------------------------------------------------------
echo "[1/10] Profile flag: AGENT_RUNTIME_ENABLED=true"

PROFILE_FILE="config/deployment-profiles/agentic-production-on.yaml"
if [ ! -f "${PROFILE_FILE}" ]; then
  check "Profile file" "FAIL" "Missing: ${PROFILE_FILE}"
else
  RUNTIME_FLAG="$(grep -E '^  AGENT_RUNTIME_ENABLED:' "${PROFILE_FILE}" | awk '{print $2}')"
  if [ "${RUNTIME_FLAG}" = "true" ]; then
    check "AGENT_RUNTIME_ENABLED" "PASS" "Profile sets runtime=true"
  else
    check "AGENT_RUNTIME_ENABLED" "FAIL" "Expected true, got ${RUNTIME_FLAG}"
  fi
fi

# ---------------------------------------------------------------------------
# Check 2: Agent creation — POST /admin/agents
# ---------------------------------------------------------------------------
echo "[2/10] Create test agent"

AGENT_PAYLOAD='{"name":"production-on-validation","description":"Live runtime validation agent","risk_level":"low"}'
AGENT_RESP=$(api_post "${BASE_URL}/admin/agents" -d "${AGENT_PAYLOAD}" 2>/dev/null || true)
AGENT_ID=$(echo "${AGENT_RESP}" | jq -r '.id // .agent_id // empty' 2>/dev/null || true)

if [ -n "${AGENT_ID}" ]; then
  check "Create agent" "PASS" "Agent ${AGENT_ID} created"
else
  check "Create agent" "FAIL" "No agent ID in response: ${AGENT_RESP}"
  AGENT_ID="test-agent-fallback-${TIMESTAMP}"
fi

# ---------------------------------------------------------------------------
# Check 3: Start a run
# ---------------------------------------------------------------------------
echo "[3/10] Start agent run"

RUN_PAYLOAD='{"agent_id":"'"${AGENT_ID}"'","input":"validate production-on runtime","mode":"sync"}'
RUN_RESP=$(api_post "${BASE_URL}/admin/agents/runs" -d "${RUN_PAYLOAD}" 2>/dev/null || true)
RUN_ID=$(echo "${RUN_RESP}" | jq -r '.run_id // .id // empty' 2>/dev/null || true)

if [ -n "${RUN_ID}" ]; then
  check "Start run" "PASS" "Run ${RUN_ID} started"
else
  check "Start run" "FAIL" "No run ID: ${RUN_RESP}"
  RUN_ID="test-run-fallback-${TIMESTAMP}"
fi

# ---------------------------------------------------------------------------
# Check 4: Worker processes the job
# ---------------------------------------------------------------------------
echo "[4/10] Worker processes job"

WORKER_RESP=$(api_get "${BASE_URL}/admin/agents/worker/status" 2>/dev/null || true)
WORKER_COUNT=$(echo "${WORKER_RESP}" | jq -r '.active_workers // .workers // 0' 2>/dev/null || echo "0")

if [ "${WORKER_COUNT}" -gt 0 ] 2>/dev/null; then
  check "Worker active" "PASS" "${WORKER_COUNT} worker(s) processing"
else
  check "Worker active" "FAIL" "No active workers: ${WORKER_RESP}"
fi

# ---------------------------------------------------------------------------
# Check 5: LLM provider is mock/gateway (no real provider)
# ---------------------------------------------------------------------------
echo "[5/10] LLM provider mock/gateway"

LLM_RESP=$(api_get "${BASE_URL}/admin/agents/providers/status" 2>/dev/null || true)
MOCK_MODE=$(echo "${LLM_RESP}" | jq -r '.mock_mode // .executor_mock_mode // "unknown"' 2>/dev/null || echo "unknown")

if [ "${MOCK_MODE}" = "true" ] || [ "${MOCK_MODE}" = "gateway" ]; then
  check "LLM mock/gateway" "PASS" "Mode: ${MOCK_MODE}"
else
  check "LLM mock/gateway" "FAIL" "Expected mock/gateway, got: ${MOCK_MODE}"
fi

# ---------------------------------------------------------------------------
# Check 6: Tool safe echo executes
# ---------------------------------------------------------------------------
echo "[6/10] Tool safe echo execution"

TOOL_PAYLOAD='{"tool":"echo","params":{"message":"production-on-ok"},"agent_id":"'"${AGENT_ID}"'","run_id":"'"${RUN_ID}"'"}'
TOOL_RESP=$(api_post "${BASE_URL}/admin/agents/tools/execute" -d "${TOOL_PAYLOAD}" 2>/dev/null || true)
TOOL_RESULT=$(echo "${TOOL_RESP}" | jq -r '.result // .output // .status // empty' 2>/dev/null || true)

if [ -n "${TOOL_RESULT}" ]; then
  check "Tool echo execute" "PASS" "Result: ${TOOL_RESULT}"
else
  check "Tool echo execute" "FAIL" "No result: ${TOOL_RESP}"
fi

# ---------------------------------------------------------------------------
# Check 7: Memory read/write executes
# ---------------------------------------------------------------------------
echo "[7/10] Memory read/write"

MEM_WRITE_RESP=$(api_post "${BASE_URL}/admin/agents/memory" \
  -d '{"agent_id":"'"${AGENT_ID}"'","run_id":"'"${RUN_ID}"'","key":"validation-key","value":"production-on-value","operation":"write"}' \
  2>/dev/null || true)
MEM_WRITE_OK=$(echo "${MEM_WRITE_RESP}" | jq -r '.status // .result // "unknown"' 2>/dev/null || echo "unknown")

MEM_READ_RESP=$(api_post "${BASE_URL}/admin/agents/memory" \
  -d '{"agent_id":"'"${AGENT_ID}"'","key":"validation-key","operation":"read"}' \
  2>/dev/null || true)
MEM_READ_VAL=$(echo "${MEM_READ_RESP}" | jq -r '.value // .result // empty' 2>/dev/null || true)

if [ -n "${MEM_READ_VAL}" ]; then
  check "Memory R/W" "PASS" "Read: ${MEM_READ_VAL}"
else
  check "Memory R/W" "FAIL" "Write: ${MEM_WRITE_OK}, Read: ${MEM_READ_VAL:-empty}"
fi

# ---------------------------------------------------------------------------
# Check 8: KG query executes
# ---------------------------------------------------------------------------
echo "[8/10] Knowledge Graph query"

KG_RESP=$(api_post "${BASE_URL}/admin/agents/knowledge-graph/query" \
  -d '{"query":"production-on validation node","agent_id":"'"${AGENT_ID}"'","run_id":"'"${RUN_ID}"'"}' \
  2>/dev/null || true)
KG_STATUS=$(echo "${KG_RESP}" | jq -r '.status // .results // empty' 2>/dev/null || true)

if [ -n "${KG_STATUS}" ]; then
  check "KG query" "PASS" "Status: ${KG_STATUS}"
else
  check "KG query" "FAIL" "No KG response: ${KG_RESP}"
fi

# ---------------------------------------------------------------------------
# Check 9: Eval gateway/mock runs
# ---------------------------------------------------------------------------
echo "[9/10] Eval gateway/mock"

EVAL_PAYLOAD='{"agent_id":"'"${AGENT_ID}"'","run_id":"'"${RUN_ID}"'","eval_type":"production_on_validation"}'
EVAL_RESP=$(api_post "${BASE_URL}/admin/agent-evals/run" -d "${EVAL_PAYLOAD}" 2>/dev/null || true)
EVAL_ID=$(echo "${EVAL_RESP}" | jq -r '.eval_id // .id // empty' 2>/dev/null || true)

if [ -n "${EVAL_ID}" ]; then
  check "Eval gateway" "PASS" "Eval ${EVAL_ID} executed"
else
  check "Eval gateway" "FAIL" "No eval response: ${EVAL_RESP}"
fi

# ---------------------------------------------------------------------------
# Check 10: Trace/receipt generated and run finalizes
# ---------------------------------------------------------------------------
echo "[10/10] Trace/receipt + run finalization"

TRACE_RESP=$(api_get "${BASE_URL}/admin/agents/runs/${RUN_ID}/trace" 2>/dev/null || true)
TRACE_EXISTS=$(echo "${TRACE_RESP}" | jq -r '.trace_id // .id // .status // empty' 2>/dev/null || true)

RECEIPT_RESP=$(api_get "${BASE_URL}/admin/agents/runs/${RUN_ID}/receipt" 2>/dev/null || true)
RECEIPT_EXISTS=$(echo "${RECEIPT_RESP}" | jq -r '.receipt_id // .id // .status // empty' 2>/dev/null || true)

FINAL_RESP=$(api_get "${BASE_URL}/admin/agents/runs/${RUN_ID}" 2>/dev/null || true)
FINAL_STATUS=$(echo "${FINAL_RESP}" | jq -r '.status // empty' 2>/dev/null || true)

if [ -n "${TRACE_EXISTS}" ] && [ -n "${RECEIPT_EXISTS}" ]; then
  check "Trace + receipt" "PASS" "Trace: ${TRACE_EXISTS}, Receipt: ${RECEIPT_EXISTS}"
else
  check "Trace + receipt" "FAIL" "Trace: ${TRACE_EXISTS:-missing}, Receipt: ${RECEIPT_EXISTS:-missing}"
fi

if [ "${FINAL_STATUS}" = "completed" ] || [ "${FINAL_STATUS}" = "finished" ]; then
  check "Run finalization" "PASS" "Status: ${FINAL_STATUS}"
elif [ -n "${FINAL_STATUS}" ]; then
  check "Run finalization" "WARN" "Run status: ${FINAL_STATUS} (expected completed)"
else
  check "Run finalization" "FAIL" "No final status"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==============================================================="
echo "  RESULTS: ${PASS} passed, ${FAIL} failed"
echo "==============================================================="

mkdir -p "${ARTIFACT_DIR}"
SUMMARY_FILE="${ARTIFACT_DIR}/agentic-production-on.md"

{
  echo "# Agentic Production-ON Readiness — ${TIMESTAMP}"
  echo ""
  echo "| Check | Status | Detail |"
  echo "| :--- | :---: | :--- |"
  for r in "${RESULTS[@]}"; do
    IFS='|' read -r s n d <<< "${r}"
    echo "| ${n} | ${s} | ${d} |"
  done
  echo ""
  echo "**Overall: ${PASS} passed, ${FAIL} failed**"
  echo ""
  if [ "${FAIL}" -gt 0 ]; then
    echo "**Result: BLOCKED** — ${FAIL} check(s) failed. Runtime is NOT production-on ready."
  else
    echo "**Result: PASS** — Production-ON readiness validated with runtime live."
  fi
} > "${SUMMARY_FILE}"

echo "Report: ${SUMMARY_FILE}"

if [ "${FAIL}" -gt 0 ]; then
  exit 1
fi
exit 0
