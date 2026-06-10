#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

printf '[reset-dev] this will stop containers, remove compose volumes, local validation artifacts and download venvs.\n'
printf '[reset-dev] models are preserved by default.\n'
printf '[reset-dev] continue? type RESET: '
read -r confirmation

if [[ "${confirmation}" != "RESET" ]]; then
  printf '[reset-dev] aborted\n'
  exit 1
fi

cd "${ROOT_DIR}"
dc down -v --remove-orphans
rm -rf "${ROOT_DIR}/artifacts/validation" "${ROOT_DIR}/.venv-download"

printf '[reset-dev] remove local env file %s? type ENV to confirm, anything else to keep: ' "${STACK_ENV_FILE}"
read -r env_confirmation
if [[ "${env_confirmation}" == "ENV" ]]; then
  rm -f "${ROOT_DIR}/${STACK_ENV_FILE}"
  printf '[reset-dev] removed %s\n' "${STACK_ENV_FILE}"
fi

printf '[reset-dev] remove models directory contents? type MODELS to confirm, anything else to keep: '
read -r models_confirmation
if [[ "${models_confirmation}" == "MODELS" ]]; then
  rm -rf "${ROOT_DIR}/models"/*
  printf '[reset-dev] removed model files\n'
fi

printf '[reset-dev] complete\n'
