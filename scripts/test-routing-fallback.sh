#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

for _ in $(seq 1 30); do
  if curl --max-time 5 -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl --max-time 5 -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  printf '[routing][error] control plane is not reachable at %s\n' "${BASE_URL}" >&2
  printf '[routing][error] suggested-command=./scripts/validate-e2e.sh\n' >&2
  exit 1
fi

printf '[routing] fetching routing table\n'
curl --max-time 10 -fsS "${BASE_URL}/admin/backends/routing" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${tmp_dir}/routing.json"
python3 -m json.tool "${tmp_dir}/routing.json"

route_count="$(python3 - "${tmp_dir}/routing.json" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
counts = [len(item.get("routes", [])) for item in data.get("models", []) if item.get("is_default")]
print(max(counts) if counts else 0)
PY
)"

if [[ "${route_count}" -lt 2 ]]; then
  printf '[routing] default model has %s route(s); fallback path is configured but not exercisable yet\n' "${route_count}"
  printf '[routing] suggestion: register a secondary backend and attach it to the default model\n'
  exit 0
fi

API_KEY="$(require_api_key "${BASE_URL}" "routing-fallback")"
if [[ -z "${API_KEY}" ]]; then
  printf '[routing][error] demo API key could not be issued via admin API\n' >&2
  exit 1
fi

printf '[routing] exercising chat request and recent request logs\n'
curl -fsS "${BASE_URL}/v1/chat/completions" \
  --max-time 30 \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Responda com uma frase curta sobre fallback."}],
    "max_tokens": 48,
    "stream": false
  }' >"${tmp_dir}/chat.json"

curl --max-time 10 -fsS "${BASE_URL}/admin/requests" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${tmp_dir}/requests.json"
python3 - "${tmp_dir}/requests.json" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
if not data:
    raise SystemExit("no requests found")
latest = data[0]
print(json.dumps({
    "backend_name": latest.get("backend_name"),
    "attempts": latest.get("attempts"),
    "fallback_used": latest.get("fallback_used"),
    "backend_errors": latest.get("backend_errors"),
}, indent=2))
PY
