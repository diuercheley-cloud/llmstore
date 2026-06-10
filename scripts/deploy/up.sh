#!/usr/bin/env bash
set -euo pipefail

# up.sh - Start the LLM Inference Stack with automatic profile detection
# Adequado para v2.x Agentic AI Platform

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"

cd "${ROOT_DIR}"

# 1. Scaffolding: ensure a local env file exists before initializing
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

# 2. Initialize environment
# Allow environment variables to override env file values for testing/flexibility
export STACK_ENV_PRESERVE_EXISTING="${STACK_ENV_PRESERVE_EXISTING:-true}"
init_stack_env

# 3. Automatic Profile Detection
PROFILES=()

# --- Agentic Profile ---
# Enabled if PLATFORM_PROFILE is agentic-* or enterprise-* or if worker/runtime is explicitly enabled
if [[ "${PLATFORM_PROFILE:-}" == agentic-* ]] || \
   [[ "${PLATFORM_PROFILE:-}" == enterprise-* ]] || \
   [[ "${AGENT_RUNTIME_ENABLED:-}" == "true" ]] || \
   [[ "${AGENT_WORKER_ENABLED:-}" == "true" ]] || \
   [[ "${AGENT_AS_API_ENABLED:-}" == "true" ]] || \
   [[ "${AGENT_EXECUTION_PLANE_ENABLED:-}" == "true" ]]; then
  PROFILES+=(--profile agentic)
  printf '[up] Agentic AI Platform profile detected: enabling "agentic" compose profile.\n'
fi

# --- Observability Profile ---
# Enabled if any observability flag is true or in production agentic profiles
if [[ "${OBSERVABILITY_ENABLED:-}" == "true" ]] || \
   [[ "${AGENT_OBSERVABILITY_ENABLED:-}" == "true" ]] || \
   [[ "${AGENT_ENTERPRISE_OBSERVABILITY_ENABLED:-}" == "true" ]] || \
   [[ "${VISUAL_OBSERVABILITY_ENABLED:-}" == "true" ]] || \
   [[ "${PLATFORM_PROFILE:-}" == "agentic-production" ]]; then
  PROFILES+=(--profile observability)
  printf '[up] Observability/Monitoring detected: enabling "observability" compose profile.\n'
fi

# --- Ollama Profile ---
if [[ "${OLLAMA_ENABLED:-}" == "true" ]] || [[ "${DATA_PLANE_BASE_URL:-}" == *"ollama"* ]]; then
  PROFILES+=(--profile ollama)
  printf '[up] Ollama data-plane detected: enabling "ollama" compose profile.\n'
fi

# --- Fallback Test Profile ---
if [[ "${FALLBACK_TEST_ENABLED:-}" == "true" ]]; then
  PROFILES+=(--profile fallback-test)
  printf '[up] Fallback test mode enabled: enabling "fallback-test" compose profile.\n'
fi

# --- Additional profiles from env ---
if [[ -n "${UP_PROFILES:-}" ]]; then
  for p in ${UP_PROFILES}; do
    PROFILES+=(--profile "${p}")
  done
fi

# 4. Start Stack
# Filter out internal flags like --quick or --no-wait from dc up call
DC_UP_ARGS=()
SKIP_WAIT=false
for arg in "$@"; do
  if [[ "${arg}" == "--quick" ]] || [[ "${arg}" == "--no-wait" ]]; then
    SKIP_WAIT=true
  else
    DC_UP_ARGS+=("${arg}")
  fi
done

printf '[up] Starting stack with: dc %s up -d --build --remove-orphans %s\n' "${PROFILES[*]}" "${DC_UP_ARGS[*]}"
dc "${PROFILES[@]}" up -d --build --remove-orphans "${DC_UP_ARGS[@]}"

# 5. Post-start Readiness Check
if [[ "${SKIP_WAIT}" == "false" ]]; then
  printf '[up] Waiting for services to be ready...\n'
  BASE_URL="$(default_base_url)"
  wait_for_ready() {
    local max_retries="$1"
    local retry_count=0
    until http_get_ok "${BASE_URL}/ready"; do
      retry_count=$((retry_count + 1))
      if [[ ${retry_count} -ge ${max_retries} ]]; then
        return 1
      fi
      printf '.'
      sleep 2
    done
    return 0
  }

  if wait_for_ready 45; then
    printf ' OK\n'
  else
    printf '\n[up] /ready did not stabilize in time. Checking whether the database needs a fresh bootstrap...\n'
    if "${SCRIPT_DIR}/bootstrap-empty-db.sh" --quiet; then
      printf '[up] Empty database detected and bootstrapped. Restarting control-plane services...\n'
      dc restart control-plane control-plane-worker rag-worker >/dev/null 2>&1 || true
      printf '[up] Waiting for services after bootstrap...\n'
      if wait_for_ready 45; then
        printf ' OK\n'
      else
        printf '\n[up] WARNING: Timeout waiting for /ready even after bootstrap. Check logs with: make logs\n'
      fi
    else
      bootstrap_status=$?
      if [[ ${bootstrap_status} -eq 20 ]]; then
        printf '[up] Database already contains schema/data; no bootstrap applied.\n'
      else
        printf '[up] Bootstrap helper failed with exit code %s.\n' "${bootstrap_status}"
      fi
      printf '[up] WARNING: Timeout waiting for /ready. Check logs with: make logs\n'
    fi
  fi
fi

# 6. Summary
printf '\n--- LLM INFERENCE STACK READY ---\n'
printf 'Profile: %s\n' "${PLATFORM_PROFILE:-appliance}"
printf 'Mode:    %s\n' "${STACK_MODE:-local}"
printf 'URL:     %s\n' "$(default_base_url)"
printf 'Admin:   %s/admin\n' "$(default_base_url)"
printf 'Docs:    %s/docs\n' "$(default_base_url)"
if [[ "${PLATFORM_PROFILE:-}" == agentic-* ]]; then
  printf 'Agentic: ENABLED (Worker active via "agentic" profile)\n'
fi
printf '%s\n' "---------------------------------"
