# Milvus Operations

Instruções para configurar e operar o Milvus com o LLM Inference Stack.

## Instalação

Recomenda-se o uso do Milvus Standalone via Docker Compose:

```bash
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

## Configuração no Control Plane

No seu arquivo `.env`:

```env
VECTOR_DB_PROVIDER=milvus
MILVUS_ENABLED=true
MILVUS_URL=http://localhost:19530
```

## Monitoramento

Verifique a conectividade via:

- `GET /admin/vectorstores/health`

## Considerações

O Milvus é ideal para deployments de larga escala com necessidade de alta disponibilidade.
