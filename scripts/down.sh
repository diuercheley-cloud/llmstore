#!/usr/bin/env bash
set -euo pipefail

# down.sh - Stop the LLM Inference Stack and all its profiles
# Adequado para v2.x Agentic AI Platform

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

cd "${ROOT_DIR}"

REMOVE_VOLUMES=""
for arg in "$@"; do
  if [[ "${arg}" == "-v" ]] || [[ "${arg}" == "--volumes" ]]; then
    REMOVE_VOLUMES="--volumes"
    break
  fi
done

printf '[down] Stopping all stack services (all profiles)...\n'
# We use --profile "*" to ensure all services in any profile are stopped.
# We also use --remove-orphans to clean up services that might have been removed from the compose file.
dc --profile "*" down --remove-orphans ${REMOVE_VOLUMES} "$@"

printf '[down] Stack stopped successfully.\n'
if [[ -n "${REMOVE_VOLUMES}" ]]; then
  printf '[down] Volumes removed.\n'
fi
