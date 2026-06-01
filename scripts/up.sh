#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

cd "${ROOT_DIR}"

# Scaffolding: ensure a local env file exists before initializing
if [[ -z "${ENV_FILE:-}" ]]; then
  if [[ "${STACK_MODE:-local}" == "prod" ]]; then
    TARGET_ENV=".env.prod"
  else
    TARGET_ENV=".env.local"
  fi
  # If the target file doesn't exist and there's no generic .env, create it
  if [[ ! -f "${ROOT_DIR}/${TARGET_ENV}" && ! -f "${ROOT_DIR}/.env" ]]; then
    cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/${TARGET_ENV}"
    echo "${TARGET_ENV} created from .env.example; review tokens, passwords and ports before use."
  fi
fi

init_stack_env

dc up -d --build --remove-orphans "$@"
