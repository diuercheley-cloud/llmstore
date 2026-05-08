#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
BASE_URL="${BASE_URL:-$(default_base_url)}"
curl -fsS "${BASE_URL}/health" | python3 -m json.tool
curl -fsS "${BASE_URL}/ready" | python3 -m json.tool
curl -fsS "${BASE_URL}/metrics" | head -n 20
curl -fsS "${BASE_URL}/pocket-tts/health" | python3 -m json.tool
