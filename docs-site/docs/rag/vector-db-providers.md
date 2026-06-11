<!-- synced_from: docs/rag/vector-db-providers.md -->

> Source of truth: `docs/rag/vector-db-providers.md`

# Vector DB Providers

O LLM Inference Stack suporta múltiplos provedores de Vector DB para armazenamento de embeddings e recuperação (RAG).

## Provedores Suportados

- **pgvector**: (Padrão) Utiliza a extensão `vector` do PostgreSQL. Ideal para deployments simples e integrados.
- **Qdrant**: Vector DB de alta performance escrito em Rust. Suporta filtragem avançada e escalabilidade horizontal.
- **Milvus**: Provedor focado em nuvem e grandes escalas.
- **Weaviate**: Vector DB rico em recursos com suporte a esquemas complexos.

## Configuração

A escolha do provedor é feita através de feature flags no arquivo `.env` ou variáveis de ambiente.

```env
VECTOR_DB_PROVIDER=pgvector # Opções: pgvector, qdrant, milvus, weaviate

# Qdrant
QDRANT_ENABLED=false
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-api-key

# Milvus
MILVUS_ENABLED=false
MILVUS_URL=http://localhost:19530
MILVUS_TOKEN=your-token

# Weaviate
WEAVIATE_ENABLED=false
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=your-api-key
```

## Escolha do Provedor

O provedor pode ser alterado a qualquer momento, mas lembre-se que os dados não são migrados automaticamente entre provedores.

Para ambientes de produção com milhões de documentos, recomenda-se o uso de **Qdrant** ou **Milvus**.
Para aplicações menores ou que já utilizam PostgreSQL, o **pgvector** é a escolha mais simples e eficiente.
