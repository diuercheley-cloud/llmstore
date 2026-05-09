#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
BASE_URL="${BASE_URL:-$(default_base_url)}"
curl_base_url "${BASE_URL}/health" -fsS | python3 -m json.tool
curl_base_url "${BASE_URL}/ready" -fsS | python3 -m json.tool
curl_base_url "${BASE_URL}/metrics" -fsS | head -n 20
if [[ -n "${ADMIN_TOKEN:-}" ]]; then
  curl_base_url "${BASE_URL}/admin/health/deep" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" | \
    python3 -c 'import json, sys; data=json.load(sys.stdin); print(json.dumps(data.get("tts", {}), indent=2))'
fi
