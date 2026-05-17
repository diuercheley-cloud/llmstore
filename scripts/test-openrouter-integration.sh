#!/bin/bash

# Configurações
API_URL="http://localhost:18080/v1/chat/completions"
CLIENT_KEY="TEST_OPENROUTER_API_KEY"
MODEL="openrouter-test"
OPENROUTER_MODEL_ID="qwen/qwen3.5-flash-02-23"

echo "------------------------------------------------------------"
echo "🚀 INICIANDO TESTE INTEGRADO: CLIENTE -> GATEWAY -> OPENROUTER"
echo "------------------------------------------------------------"

echo "🧩 0. Garantindo alias local para modelo OpenRouter válido..."
docker compose exec -T control-plane python3 - <<PY
import asyncio
import json
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry

MODEL_ALIAS = "$MODEL"
MODEL_ID = "$OPENROUTER_MODEL_ID"

async def run():
    async with SessionLocal() as db:
        backend = (
            await db.execute(
                select(InferenceBackend).where(
                    InferenceBackend.provider == "openrouter",
                    InferenceBackend.is_active.is_(True),
                )
            )
        ).scalars().first()
        if not backend:
            raise RuntimeError("Nenhum backend OpenRouter ativo encontrado.")

        model = (
            await db.execute(
                select(ModelRegistry).where(ModelRegistry.model_alias == MODEL_ALIAS)
            )
        ).scalars().first()
        metadata = json.dumps({
            "backend": "openrouter",
            "backend_name": backend.name,
        })
        if not model:
            model = ModelRegistry(
                model_id=MODEL_ID,
                model_alias=MODEL_ALIAS,
                inference_backend_id=backend.id,
                provider="openrouter",
                model_file="",
                context_length=131072,
                is_active=True,
                is_default=False,
                status="configured",
                prompt_template="qwen",
                metadata_json=metadata,
            )
            db.add(model)
            await db.flush()
        else:
            model.model_id = MODEL_ID
            model.inference_backend_id = backend.id
            model.provider = "openrouter"
            model.model_file = ""
            model.context_length = 131072
            model.is_active = True
            model.status = "configured"
            model.prompt_template = "qwen"
            model.metadata_json = metadata

        route = (
            await db.execute(
                select(ModelBackendRoute).where(
                    ModelBackendRoute.model_registry_id == model.id,
                    ModelBackendRoute.inference_backend_id == backend.id,
                )
            )
        ).scalars().first()
        if not route:
            route = ModelBackendRoute(
                model_registry_id=model.id,
                inference_backend_id=backend.id,
                priority=1,
                weight=100,
                state="healthy",
            )
            db.add(route)
        else:
            route.priority = 1
            route.weight = 100
            route.state = "healthy"
        await db.commit()
        print(f"✅ Alias {MODEL_ALIAS} -> {MODEL_ID} ({backend.name})")

asyncio.run(run())
PY

# 1. Teste de Inferência
echo "📡 1. Enviando requisição de chat..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
  -H "Authorization: Bearer $CLIENT_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Teste de integração. Responda apenas: OK\"}],
    \"temperature\": 0.7
  }")

HTTP_STATUS=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "✅ Sucesso! Resposta 200 OK recebida."
    MODEL_OUTPUT=$(printf '%s' "$BODY" | jq -r '.choices[0].message.content // empty')
    if [ -z "$MODEL_OUTPUT" ]; then
        echo "❌ Erro! OpenRouter respondeu sem message.content"
        echo "📄 Detalhes: $BODY"
        exit 1
    fi
    echo "📄 Resposta do Modelo: $MODEL_OUTPUT"
else
    echo "❌ Erro! Status HTTP: $HTTP_STATUS"
    echo "📄 Detalhes: $BODY"
    exit 1
fi

echo ""
echo "------------------------------------------------------------"
echo "📊 2. VERIFICANDO FATURAMENTO (BILLING) NO BANCO DE DADOS"
echo "------------------------------------------------------------"

# Busca o ID do cliente baseado no nome conhecido
CLIENT_NAME="val-admin-1778335649"

docker compose exec -T control-plane python3 -c "
import asyncio
from app.db.session import SessionLocal
from app.models.request_log import RequestLog
from app.models.client import Client
from sqlalchemy import select, desc

async def run():
    async with SessionLocal() as db:
        # Busca o cliente
        res_c = await db.execute(select(Client).filter(Client.name == '$CLIENT_NAME'))
        client = res_c.scalars().first()
        
        if not client:
            print('❌ Cliente não encontrado no banco.')
            return

        # Busca o último log de requisição
        res_l = await db.execute(
            select(RequestLog)
            .filter(RequestLog.client_id == client.id)
            .order_by(desc(RequestLog.created_at))
            .limit(1)
        )
        log = res_l.scalars().first()
        
        if log:
            print(f'✅ Log de Billing encontrado!')
            print(f'   ID da Requisição: {log.id}')
            print(f'   Modelo: {log.model}')
            print(f'   Backend: {log.backend_name}')
            print(f'   Tokens (Prompt/Comp): {log.prompt_tokens_estimated}/{log.completion_tokens_estimated}')
            print(f'   Status HTTP: {log.http_status}')
            print(f'   Timestamp: {log.created_at}')
        else:
            print('❌ Nenhum log de uso encontrado para este cliente.')

if __name__ == \"__main__\":
    asyncio.run(run())
"

echo "------------------------------------------------------------"
echo "🏁 TESTE FINALIZADO"
echo "------------------------------------------------------------"
