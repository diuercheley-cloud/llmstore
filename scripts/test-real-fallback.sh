#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

log() {
  printf '[fallback] %s\n' "$*"
}

fail() {
  printf '[fallback][error] %s\n' "$*" >&2
  exit 1
}

log "starting fallback-test profile"
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

route_count=$(printf '%s\n' "${routing_json}" | python3 -c 'import json, sys; d=json.load(sys.stdin); print(len(d["models"][0]["routes"]))')
log "found ${route_count} routes"

if [[ "${route_count}" -lt 2 ]]; then
  fail "expected at least 2 routes, found ${route_count}"
fi

API_KEY="$(issue_demo_api_key "${BASE_URL}" "fallback-test")"

log "validating gemma-local is healthy"
gemma_status=$(printf '%s\n' "${routing_json}" | python3 -c 'import json, sys; d=json.load(sys.stdin); r=[r for r in d["models"][0]["routes"] if r["backend_name"] == "gemma-local"][0]; print(r["state"])')
if [[ "${gemma_status}" != "healthy" ]]; then
  fail "gemma-local is not healthy: ${gemma_status}"
fi

log "simulating failure of gemma-local (pausing container)"
# Identify the container name dynamically if possible, or use standard name
GEMMA_CONTAINER=$(dc ps -q data-plane-gemma)
docker pause "${GEMMA_CONTAINER}"

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
log "stopping fallback-test profile"
COMPOSE_PROFILES=fallback-test dc stop data-plane-mock
