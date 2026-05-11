#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

# Script para validar a disponibilidade de um modelo de chat utilizável
# Uso: ./scripts/validate-usable-chat-model-local.sh

BASE_URL="${BASE_URL:-http://localhost:18080}"
init_stack_env

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}✓ $1${NC}"; }
log_error() { echo -e "${RED}✗ $1${NC}"; }
log_warn() { echo -e "${YELLOW}! $1${NC}"; }

log_info() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] [validate-usable-chat-model-local.sh] INFO: $*"
}

CLIENT_API_KEY="$(require_api_key "${BASE_URL}" "usable-chat-validation")"
if [ -z "$CLIENT_API_KEY" ]; then
    log_error "CLIENT_API_KEY não encontrada. Defina a variável de ambiente ou execute em um ambiente configurado (demo-client precisa existir)."
    exit 1
fi
API_KEY="${CLIENT_API_KEY}"

echo "Verificando modelos em $BASE_URL/v1/models..."

MODELS_JSON=$(curl -s -f --connect-timeout 5 --max-time 15 -H "Authorization: Bearer $API_KEY" "$BASE_URL/v1/models") || true

if [ -z "$MODELS_JSON" ]; then
    log_error "Falha ao obter lista de modelos ou resposta vazia."
    exit 1
fi

# Validar se é JSON válido e tem data
if ! echo "$MODELS_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); exit(0 if 'data' in data else 1)" 2>/dev/null; then
    log_error "Resposta de /v1/models não é um JSON válido da OpenAI."
    exit 1
fi

log_ok "/v1/models retornou JSON válido"

# Verificar se existe pelo menos um modelo de chat pronto
CHATS=$(echo "$MODELS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin).get('data', [])
chats = [m for m in data if m.get('capabilities', {}).get('chat') is True]
ready_chats = [m for m in chats if m.get('local_ready') is True or m.get('production_ready') is True]
print(json.dumps(ready_chats))
")

CHAT_COUNT=$(echo "$CHATS" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))")

if [ "$CHAT_COUNT" -gt 0 ]; then
    MODEL_ID=$(echo "$CHATS" | python3 -c "import json, sys; print(json.load(sys.stdin)[0]['id'])")
    BACKEND=$(echo "$CHATS" | python3 -c "import json, sys; print(json.load(sys.stdin)[0].get('backend_status', 'unknown'))")
    log_ok "Encontrado(s) $CHAT_COUNT modelo(s) de chat prontos. Exemplo: $MODEL_ID (backend: $BACKEND)"
else
    log_error "Nenhum modelo de chat utilizável/pronto encontrado em /v1/models."
    echo "Modelos disponíveis:"
    echo "$MODELS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin).get('data', [])
for m in data:
    cap = m.get('capabilities', {})
    ready = m.get('local_ready') or m.get('production_ready')
    print(f' - {m.get(\"id\")}: chat={cap.get(\"chat\")}, ready={ready}, status={m.get(\"backend_status\")}, reason={m.get(\"reason\")}')
"
    exit 1
fi

# Validar que embeddings-only não passa como chat
EMBEDDINGS_ONLY=$(echo "$MODELS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin).get('data', [])
bad = [m for m in data if m.get('capabilities', {}).get('embeddings') is True and m.get('capabilities', {}).get('chat') is True]
print(len(bad))
")

if [ "$EMBEDDINGS_ONLY" -eq 0 ]; then
    log_ok "Filtro de capabilities está correto (sem overlap chat/embeddings indevido)"
else
    log_warn "Atenção: $EMBEDDINGS_ONLY modelos marcados como chat E embeddings. Verifique se isso é intencional."
fi

# Validar que modelo disabled não passa
DISABLED_READY=$(echo "$MODELS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin).get('data', [])
bad = [m for m in data if m.get('enabled') is False and (m.get('local_ready') is True or m.get('production_ready') is True)]
print(len(bad))
")

if [ "$DISABLED_READY" -eq 0 ]; then
    log_ok "Modelos desabilitados não são considerados prontos"
else
    log_error "ERRO: Modelos desabilitados estão marcados como prontos!"
    exit 1
fi

# Validar que não vaza paths
SENSITIVE_LEAK=$(echo "$MODELS_JSON" | grep -E "/home/|/Users/|/mnt/|/opt/|/var/|secret|key" || true)
if [ -z "$SENSITIVE_LEAK" ]; then
    log_ok "Nenhum path ou segredo sensível detectado no output"
else
    log_error "ALERTA DE SEGURANÇA: Possível vazamento de informação sensível no JSON de modelos!"
    echo "$SENSITIVE_LEAK"
    exit 1
fi

echo -e "\n${GREEN}Validação de modelo de chat concluída com sucesso!${NC}"
