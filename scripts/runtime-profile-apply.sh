#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${ROOT_DIR}/scripts/common.sh"
init_stack_env

DRY_RUN="true"
ROLLBACK="false"
PROFILE_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --live)
      DRY_RUN="false"
      shift
      ;;
    --rollback)
      ROLLBACK="true"
      shift
      ;;
    *)
      if [[ -z "${PROFILE_ID}" ]]; then
        PROFILE_ID="$1"
      else
        echo "Error: Unexpected argument '$1'"
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ "${ROLLBACK}" == "false" && -z "${PROFILE_ID}" ]]; then
  echo "Error: profile_id is required unless --rollback is specified."
  echo "Usage: $0 [--live] <profile_id>"
  echo "       $0 [--live] --rollback"
  exit 1
fi

BASE_URL=$(default_base_url)

if [[ "${ROLLBACK}" == "true" ]]; then
  echo "### Applying Rollback (dry_run: ${DRY_RUN}) ###"
  payload="{\"rollback\": true, \"dry_run\": ${DRY_RUN}}"
else
  echo "### Applying Runtime Profile: ${PROFILE_ID} (dry_run: ${DRY_RUN}) ###"
  payload="{\"profile_id\": \"${PROFILE_ID}\", \"rollback\": false, \"dry_run\": ${DRY_RUN}}"
fi

curl_base_url "${BASE_URL}/admin/runtime-profiles/apply" \
  -s \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -d "${payload}" | python3 -m json.tool

if [[ "${DRY_RUN}" == "true" ]]; then
  echo ""
  echo "Nota: Esta ação foi executada em modo DRY-RUN (simulação)."
  echo "Para aplicar de verdade as alterações, use o argumento --live."
  echo "Além disso, a variável de ambiente RUNTIME_PROFILE_APPLY_ENABLED=true deve estar configurada no servidor."
fi
