#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"
GEMMA_CONTAINER=""
GEMMA_PAUSED="false"
FALLBACK_BACKEND_ID=""
DEFAULT_MODEL_ID=""

log() {
  printf '[fallback] %s\n' "$*"
}

fail() {
  printf '[fallback][error] %s\n' "$*" >&2
  exit 1
}

cleanup() {
  set +e
  if [[ "${GEMMA_PAUSED}" == "true" && -n "${GEMMA_CONTAINER}" ]]; then
    docker unpause "${GEMMA_CONTAINER}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FALLBACK_BACKEND_ID}" ]]; then
    curl -fsS "${BASE_URL}/admin/backends/${FALLBACK_BACKEND_ID}" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -X PATCH \
      -d '{"is_active": false, "status": "test-disabled"}' >/dev/null 2>&1 || true
  fi
  if [[ -n "${DEFAULT_MODEL_ID}" && -n "${FALLBACK_BACKEND_ID}" ]]; then
    curl -fsS "${BASE_URL}/admin/models/${DEFAULT_MODEL_ID}/routes/${FALLBACK_BACKEND_ID}" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -X PATCH \
      -d '{"state": "disabled", "priority": 2, "weight": 100}' >/dev/null 2>&1 || true
  fi
  curl -fsS "${BASE_URL}/admin/backends/circuit-breaker/reset" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -X POST >/dev/null 2>&1 || true
  COMPOSE_PROFILES=fallback-test dc stop data-plane-mock >/dev/null 2>&1 || true
  COMPOSE_PROFILES=fallback-test dc rm -f -s data-plane-mock >/dev/null 2>&1 || true
}

trap cleanup EXIT

log "starting fallback-test profile"
COMPOSE_PROFILES=fallback-test dc rm -f -s data-plane-mock >/dev/null 2>&1 || true
COMPOSE_PROFILES=fallback-test dc up -d data-plane-mock

log "waiting for mock data plane"
for _ in $(seq 1 30); do
  if dc ps data-plane-mock --format json | grep -qi '"Health":"healthy"\|"Status":"healthy"'; then
    break
  fi
  # Fallback check for older docker compose versions
  if dc ps data-plane-mock | grep -qi "healthy"; then
    break
  fi
  sleep 2
done

log "checking routing table"
routing_json="$(curl -fsS "${BASE_URL}/admin/backends/routing" -H "X-Admin-Token: ${ADMIN_TOKEN}")"
# printf '%s\n' "${routing_json}" | python3 -m json.tool

DEFAULT_MODEL_ID="$(printf '%s\n' "${routing_json}" | python3 -c 'import json, sys; d=json.load(sys.stdin); m=next(item for item in d["models"] if item.get("is_default")); print(m["id"])')"
FALLBACK_BACKEND_ID="$(printf '%s\n' "${routing_json}" | python3 -c 'import json, sys; d=json.load(sys.stdin); r=next(route for model in d["models"] for route in model["routes"] if route["backend_name"] == "fallback-local"); print(r["backend_id"])')"

log "enabling fallback-local for this test run"
curl -fsS "${BASE_URL}/admin/backends/${FALLBACK_BACKEND_ID}" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d '{"is_active": true, "status": "test-active"}' >/dev/null
curl -fsS "${BASE_URL}/admin/models/${DEFAULT_MODEL_ID}/routes/${FALLBACK_BACKEND_ID}" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d '{"state": "healthy", "priority": 2, "weight": 100}' >/dev/null
curl -fsS "${BASE_URL}/admin/backends/circuit-breaker/reset" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -X POST >/dev/null

routing_json="$(curl -fsS "${BASE_URL}/admin/backends/routing" -H "X-Admin-Token: ${ADMIN_TOKEN}")"

route_count=$(printf '%s\n' "${routing_json}" | python3 -c 'import json, sys; d=json.load(sys.stdin); m=next(item for item in d["models"] if item.get("is_default")); print(len(m["routes"]))')
log "found ${route_count} routes"

if [[ "${route_count}" -lt 2 ]]; then
  fail "expected at least 2 routes, found ${route_count}"
fi

API_KEY="$(issue_demo_api_key "${BASE_URL}" "fallback-test")"

log "validating gemma-local is healthy"
gemma_status=$(printf '%s\n' "${routing_json}" | python3 -c 'import json, sys; d=json.load(sys.stdin); m=next(item for item in d["models"] if item.get("is_default")); r=[r for r in m["routes"] if r["backend_name"] == "gemma-local"][0]; print(r["state"])')
if [[ "${gemma_status}" != "healthy" ]]; then
  fail "gemma-local is not healthy: ${gemma_status}"
fi

log "simulating failure of gemma-local (pausing container)"
# Identify the container name dynamically if possible, or use standard name
GEMMA_CONTAINER=$(dc ps -q data-plane-gemma)
docker pause "${GEMMA_CONTAINER}"
GEMMA_PAUSED="true"

log "executing chat request (should fallback)"
chat_response="$(curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "hi"}],
    "stream": false
  }')"

# printf '%s\n' "${chat_response}" | python3 -m json.tool

log "unpausing gemma-local"
docker unpause "${GEMMA_CONTAINER}"
GEMMA_PAUSED="false"

log "checking request logs for fallback verification"
# Wait a bit for logs to be written
sleep 2
request_logs="$(curl -fsS "${BASE_URL}/admin/requests?limit=5" -H "X-Admin-Token: ${ADMIN_TOKEN}")"
# printf '%s\n' "${request_logs}" | python3 -m json.tool

# Find the request we just made
verification="$(printf '%s\n' "${request_logs}" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for req in d:
    if req.get("backend_name") == "fallback-local" and req.get("fallback_used") is True:
        print(json.dumps({"ok": True, "backend": req["backend_name"], "fallback": req["fallback_used"]}))
        sys.exit(0)
print(json.dumps({"ok": False}))
')"

ok=$(printf '%s\n' "${verification}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["ok"])')

if [[ "${ok}" != "True" ]]; then
  fail "fallback was not detected in logs"
fi

log "fallback validation success!"
log "resetting fallback-local and circuit breaker"
cleanup
trap - EXIT

log "verifying normal routing after cleanup"
routing_after_cleanup="$(curl -fsS "${BASE_URL}/admin/backends/routing" -H "X-Admin-Token: ${ADMIN_TOKEN}")"
normal_check="$(printf '%s\n' "${routing_after_cleanup}" | python3 -c '
import json, sys
d=json.load(sys.stdin)
m=next(item for item in d["models"] if item.get("is_default"))
routes=m["routes"]
gemma=[r for r in routes if r["backend_name"] == "gemma-local"][0]
fallback=[r for r in routes if r["backend_name"] == "fallback-local"][0]
print(json.dumps({
  "gemma_eligible": gemma["eligible_for_routing"],
  "fallback_eligible": fallback["eligible_for_routing"],
  "fallback_state": fallback["state"],
  "fallback_backend_is_active": fallback["backend_is_active"]
}))
')"
printf '%s\n' "${normal_check}" | python3 -m json.tool

log "running post-fallback normal chat"
normal_chat=""
for _ in $(seq 1 5); do
  if normal_chat="$(curl --max-time 90 -fsS "${BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "unsloth/gemma-4-E4B-it-GGUF",
      "messages": [{"role": "user", "content": "normal post-fallback chat"}],
      "stream": false
    }' 2>/dev/null)"; then
    break
  fi
  sleep 2
done
[[ -n "${normal_chat}" ]] || fail "post-fallback normal chat did not recover"
printf '%s\n' "${normal_chat}" >/dev/null
log "post-fallback normal chat succeeded"
