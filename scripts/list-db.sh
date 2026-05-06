#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

POSTGRES_TABLES=(
  clients
  api_keys
  request_logs
  usage_records
  model_registry
  quota_counters
  billing_plans
  pricing_rules
  billing_invoices
  customer_payments
  inference_backends
  model_backend_routes
  generation_jobs
  response_cache
  security_events
  rag_documents
  rag_document_chunks
  rag_usage_events
  client_feature_blocks
)

sep="────────────────────────────────────────────────────────────────────────────────"

printf '\n%s\n  POSTGRES  ·  %s@%s\n%s\n\n' \
  "${sep}" "${POSTGRES_USER}" "${POSTGRES_DB}" "${sep}"

for table in "${POSTGRES_TABLES[@]}"; do
  count=$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT COUNT(*) FROM ${table};" 2>/dev/null || echo "0")
  if [[ "${count}" -gt 0 ]]; then
    printf '  %-30s %s rows\n' "${table}" "${count}"
    dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT * FROM ${table};" 2>/dev/null || true
    printf '\n'
  else
    printf '  %-30s (empty)\n' "${table}"
  fi
done

printf '\n%s\n  REDIS  ·  %s\n%s\n\n' "${sep}" "${REDIS_URL}" "${sep}"

redis_keys=$(dc exec -T redis redis-cli KEYS '*' 2>/dev/null | tr -d '\r' | grep -v '^$' || true)

if [[ -z "${redis_keys}" ]]; then
  printf '  (no keys)\n'
else
  while IFS= read -r key; do
    [[ -z "${key}" ]] && continue
    key_type=$(dc exec -T redis redis-cli TYPE "${key}" 2>/dev/null | tr -d '\r')
    ttl=$(dc exec -T redis redis-cli TTL "${key}" 2>/dev/null | tr -d '\r')

    printf '  %-50s type=%-8s ttl=%ss\n' "${key}" "${key_type}" "${ttl}"

    case "${key_type}" in
      string)
        val=$(dc exec -T redis redis-cli GET "${key}" 2>/dev/null | tr -d '\r')
        printf '    → %s\n' "${val}"
        ;;
      list)
        len=$(dc exec -T redis redis-cli LLEN "${key}" 2>/dev/null | tr -d '\r')
        printf '    → length=%s\n' "${len}"
        if [[ "${len}" -le 20 ]]; then
          dc exec -T redis redis-cli LRANGE "${key}" 0 -1 2>/dev/null | sed 's/^/    │ /'
        else
          dc exec -T redis redis-cli LRANGE "${key}" 0 4 2>/dev/null | sed 's/^/    │ /'
          printf '    │ ... (%d more)\n' "$((len - 5))"
        fi
        ;;
      set)
        scard=$(dc exec -T redis redis-cli SCARD "${key}" 2>/dev/null | tr -d '\r')
        printf '    → members=%s\n' "${scard}"
        if [[ "${scard}" -le 20 ]]; then
          dc exec -T redis redis-cli SMEMBERS "${key}" 2>/dev/null | sed 's/^/    │ /'
        else
          dc exec -T redis redis-cli SRANDMEMBER "${key}" 5 2>/dev/null | sed 's/^/    │ /'
          printf '    │ ... (%d more)\n' "$((scard - 5))"
        fi
        ;;
      hash)
        dc exec -T redis redis-cli HGETALL "${key}" 2>/dev/null | sed 's/^/    │ /'
        ;;
      zset)
        zcard=$(dc exec -T redis redis-cli ZCARD "${key}" 2>/dev/null | tr -d '\r')
        printf '    → members=%s\n' "${zcard}"
        if [[ "${zcard}" -le 20 ]]; then
          dc exec -T redis redis-cli ZRANGE "${key}" 0 -1 WITHSCORES 2>/dev/null | sed 's/^/    │ /'
        else
          dc exec -T redis redis-cli ZRANGE "${key}" 0 4 WITHSCORES 2>/dev/null | sed 's/^/    │ /'
          printf '    │ ... (%d more)\n' "$((zcard - 5))"
        fi
        ;;
    esac
    printf '\n'
  done <<< "${redis_keys}"
fi

printf '%s\n  Done.\n%s\n\n' "${sep}" "${sep}"
