#!/usr/bin/env bash
set -euo pipefail

# Script to ACTIVATE an LLM model and load into memory (VRAM)
# Usage: ./scripts/activate-model.sh <MODEL_ID_OR_ALIAS>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

MODEL_INPUT="${1:?Usage: $0 <MODEL_ID_OR_ALIAS>}"

printf "[model] Ativando modelo: %s...\n" "${MODEL_INPUT}"

# 1. Identificar o backend e o serviço docker
BACKEND_INFO=$(docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "
    SELECT b.name, b.id 
    FROM model_registry m 
    JOIN inference_backends b ON m.inference_backend_id = b.id 
    WHERE m.model_id = '${MODEL_INPUT}' OR m.model_alias = '${MODEL_INPUT}'
    LIMIT 1;
")

if [[ -z "${BACKEND_INFO}" ]]; then
    printf "[error] Modelo não encontrado ou sem backend associado.\n"
    exit 1
fi

BACKEND_NAME=$(echo "${BACKEND_INFO}" | cut -d'|' -f1)
BACKEND_ID=$(echo "${BACKEND_INFO}" | cut -d'|' -f2)

# Mapeamento de Backend -> Serviço Docker
case "${BACKEND_NAME}" in
    "gemma-local")  DOCKER_SERVICE="data-plane-gemma" ;;
    "ollama-local") DOCKER_SERVICE="data-plane-ollama" ;;
    *)              DOCKER_SERVICE="" ;;
esac

# 2. Atualizar Banco de Dados (Marcar como ativo)
printf "[db] Marcando backend %s como ativo...\n" "${BACKEND_NAME}"
docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "
    UPDATE inference_backends SET is_active = true WHERE id = '${BACKEND_ID}';
    UPDATE model_backend_routes SET state = 'healthy' WHERE inference_backend_id = '${BACKEND_ID}';
" > /dev/null

# 3. Iniciar Container (Carregar VRAM)
if [[ -n "${DOCKER_SERVICE}" ]]; then
    printf "[docker] Iniciando serviço %s (carregando modelo na VRAM)...\n" "${DOCKER_SERVICE}"
    docker compose up -d "${DOCKER_SERVICE}"
else
    printf "[warn] Nenhum serviço docker específico mapeado para o backend %s.\n" "${BACKEND_NAME}"
fi

printf "[success] Modelo '%s' ativado e em processo de carregamento.\n" "${MODEL_INPUT}"
