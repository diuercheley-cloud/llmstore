# Weaviate Operations

Instruções para configurar e operar o Weaviate com o LLM Inference Stack.

## Instalação

```bash
docker run -p 8080:8080 -p 50051:50051 \
    -e QUERY_DEFAULTS_LIMIT=25 \
    -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
    -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
    semitechnologies/weaviate:1.21.2
```

## Configuração no Control Plane

No seu arquivo `.env`:

```env
VECTOR_DB_PROVIDER=weaviate
WEAVIATE_ENABLED=true
WEAVIATE_URL=http://localhost:8080
```

## Monitoramento

- `GET /admin/vectorstores/health`

## Recursos

O Weaviate permite buscas híbridas e possui um sistema de busca vetorial muito robusto.
