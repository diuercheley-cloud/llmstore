#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

cd "${ROOT_DIR}"

if [[ ! -f "${ROOT_DIR}/${STACK_ENV_FILE}" ]]; then
  cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/${STACK_ENV_FILE}"
  echo "${STACK_ENV_FILE} created from .env.example; review tokens, passwords and ports before use."
fi

dc up -d --build
