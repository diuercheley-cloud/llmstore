#!/usr/bin/env bash
set -euo pipefail

# Script to reset quota for a client based on an API Key prefix
# Usage: ./scripts/reset-client-quota.sh <API_KEY_OR_PREFIX>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

INPUT_KEY="${1:?Usage: $0 <API_KEY_OR_PREFIX>}"
# Extract prefix (sk-local-XXXX)
PREFIX="${INPUT_KEY:0:12}"

printf "[quota] Pesquisando cliente para a chave com prefixo: %s...\n" "${PREFIX}"

# Find client_id
CLIENT_INFO=$(docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "
    SELECT c.id, c.name 
    FROM clients c 
    JOIN api_keys k ON c.id = k.client_id 
    WHERE k.key_prefix = '${PREFIX}' 
    LIMIT 1;
")

if [[ -z "${CLIENT_INFO}" ]]; then
    printf "[error] Nenhum cliente encontrado para a chave fornecida.\n"
    exit 1
fi

CLIENT_ID=$(echo "${CLIENT_INFO}" | cut -d'|' -f1)
CLIENT_NAME=$(echo "${CLIENT_INFO}" | cut -d'|' -f2)

printf "[quota] Resetando quota para o cliente: %s (ID: %s)\n" "${CLIENT_NAME}" "${CLIENT_ID}"

# Execute reset
docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "
    DELETE FROM quota_counters WHERE client_id = '${CLIENT_ID}';
" > /dev/null

printf "[success] Quota para '%s' foi resetada com sucesso!\n" "${CLIENT_NAME}"
