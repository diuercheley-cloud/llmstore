# Vector Databases

## Overview
Expanding agent memory backends beyond Postgres/SQLite.

## Supported Providers
- **Milvus**
- **Qdrant**
- **Weaviate**

## Governance
The default remains local DB (SQLite/Postgres). The new providers are strictly opt-in via environment flags (`MILVUS_ENABLED`, etc.).
