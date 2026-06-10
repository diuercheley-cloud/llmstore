#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"

case "${1:-}" in
  "generate")
    shift
    curl -X POST "${BASE_URL}/pocket-tts/tts" -F "text=$*" -o output.wav
    echo "Audio gerado em output.wav"
    ;;
  "health")
    curl -s "${BASE_URL}/pocket-tts/health"
    ;;
  *)
    echo "Usage: ./pocket-tts.sh [generate TEXT | health]"
    exit 1
    ;;
esac
