# Qdrant Operations

Instruções para configurar e operar o Qdrant com o LLM Inference Stack.

## Instalação

A forma mais simples de rodar o Qdrant localmente é via Docker:

```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

## Configuração no Control Plane

No seu arquivo `.env`:

```env
VECTOR_DB_PROVIDER=qdrant
QDRANT_ENABLED=true
QDRANT_URL=http://localhost:6333
```

## Monitoramento

O Control Plane oferece um endpoint de saúde para o Qdrant:

- `GET /admin/vectorstores/health`

## Isolamento de Tenants

O isolamento é garantido através do uso de `collection_name` por cliente ou namespace, garantindo que os dados de um cliente não sejam acessíveis por outro.
