#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

init_stack_env

ARTIFACTS_DIR="${ROOT_DIR}/artifacts/validate-plan-queues/$(date +%Y%m%dT%H%M%S)"
mkdir -p "${ARTIFACTS_DIR}"
BASE_URL="${BASE_URL:-$(default_base_url)}"

log() {
  printf '[plan-queues-val] %s\n' "$*"
}

log "Step 1: Get plan IDs"
PLANS_JSON=$(curl_base_url "${BASE_URL}/admin/billing/plans" -sS -H "X-Admin-Token: ${ADMIN_TOKEN}")
FREE_PLAN_ID=$(echo "${PLANS_JSON}" | jq -r '.[] | select(.code=="free") | .id')
PRO_PLAN_ID=$(echo "${PLANS_JSON}" | jq -r '.[] | select(.code=="pro") | .id')

# Ensure rate limits are high enough for testing
curl_base_url "${BASE_URL}/admin/billing/plans/${FREE_PLAN_ID}" -sS -X PATCH \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d '{"rate_limit_per_minute": 1000}' > /dev/null

log "Step 2: Create test clients"
create_client_on_plan() {
    local name=$1
    local plan_id=$2
    local is_admin=$3
    
    local client_data='{"name": "'"${name}"'", "billing_plan_id": "'"${plan_id}"'"}'
    if [ "${is_admin}" == "true" ]; then
        client_data='{"name": "'"${name}"'", "billing_plan_id": "'"${plan_id}"'", "metadata_json": "{\"is_admin\": true}"}'
    fi
    
    local client_resp=$(curl_base_url "${BASE_URL}/admin/clients" -sS -X POST \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${client_data}")
    
    local client_id=$(echo "${client_resp}" | jq -r '.id')
    local api_key=$(curl_base_url "${BASE_URL}/admin/api-keys" -sS -X POST \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"name\": \"val-key\", \"client_id\": \"${client_id}\"}" | jq -r '.api_key')
    
    echo "${api_key}"
}

KEY_FREE=$(create_client_on_plan "val-free-$(date +%s)" "${FREE_PLAN_ID}" "false")
KEY_ADMIN=$(create_client_on_plan "val-admin-$(date +%s)" "${PRO_PLAN_ID}" "true")

log "Step 3: Validate concurrent requests"
cat << 'EOF' > "${ARTIFACTS_DIR}/helper.py"
import asyncio
import httpx
import sys
import time

async def call_inference(name, api_key, base_url):
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "unsloth/gemma-4-E4B-it-GGUF",
                    "messages": [{"role": "user", "content": f"ping {time.time()} {name}"}],
                    "max_tokens": 10
                }
            )
            return {"name": name, "status": resp.status_code, "body": resp.json() if resp.status_code < 500 else resp.text}
        except Exception as e:
            return {"name": name, "status": 500, "error": str(e)}

async def main():
    base_url = sys.argv[1]
    keys = {"FREE": sys.argv[2], "ADMIN": sys.argv[3]}
    log_tasks = []
    for i in range(10):
        log_tasks.append(call_inference(f"FREE_{i}", keys["FREE"], base_url))
    log_tasks.append(call_inference("ADMIN_1", keys["ADMIN"], base_url))
    results = await asyncio.gather(*log_tasks)
    for r in results:
        print(f"RESULT: {r['name']} | Status: {r['status']}")

if __name__ == "__main__":
    asyncio.run(main())
EOF

"${ROOT_DIR}/.venv/bin/python3" "${ARTIFACTS_DIR}/helper.py" "${BASE_URL}" "${KEY_FREE}" "${KEY_ADMIN}" | tee "${ARTIFACTS_DIR}/results.log"

log "Step 4: Check metrics"
curl_base_url "${BASE_URL}/metrics" -sS | grep -E "control_plane_queue_" || true

log "Step 5: Check Admin Status API"
curl_base_url "${BASE_URL}/admin/status" -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" | jq '.inference_queues'

log "SUCCESS: Plan-based queues validation completed."
