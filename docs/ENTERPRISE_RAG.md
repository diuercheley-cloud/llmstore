---
owner: platform-ops
status: consolidated
---

# Enterprise RAG

## Visão Geral

O Enterprise RAG é a evolução do RAG MVP para uso empresarial com suporte a múltiplos formatos de documento, chunking avançado, embeddings locais e isolamento multi-tenant.

## Formatos Suportados

| Formato | Suporte | Dependência |
|---------|---------|-------------|
| .txt    | Sempre  | Nenhuma     |
| .md     | Sempre  | Nenhuma     |
| .csv    | Sempre  | Nenhuma     |
| .pdf    | Opcional| pymupdf     |
| .docx   | Opcional| python-docx |
| .xlsx   | Opcional| openpyxl    |

Se uma dependência não estiver instalada, o parser informa erro claro com remediation.

## Pipeline

```
Upload -> Parse -> Chunk -> Embed -> Store -> Retrieve -> Rerank -> Generate
```

### 1. Parsers (`services/rag_enterprise/parsers.py`)
- Texto simples (.txt, .md, .csv): Sempre suportado
- PDF: Usa PyMuPDF (fitz) — opcional
- DOCX: Usa python-docx — opcional
- XLSX: Usa openpyxl — opcional

### 2. Chunking (`services/rag_enterprise/chunking.py`)
- `fixed`: Divide em tamanho fixo com overlap
- `heading`: Divide por cabeçalhos (markdown, headings)
- `semantic_placeholder`: Divide por parágrafos/linhas em branco

### 3. Embeddings (`services/rag_enterprise/embeddings.py`)
- `local`: Usa sentence-transformers localmente
- `mock`: Fallback determinístico baseado em SHA-256
- Cloud embeddings desabilitado por padrão

### 4. Retrieval (`services/rag_enterprise/retrieval.py`)
- Busca por similaridade de cosseno
- Filtros por tenant/document/collection
- Score threshold configurável

### 5. Reranking (`services/rag_enterprise/reranking.py`)
- `position`: Ordena por score + posição
- `recency`: Ordena por score + data
- `diversity`: MMR para diversificar resultados

## Endpoints

### Cliente
- `POST /v1/rag/documents` — Upload de documento
- `GET /v1/rag/documents` — Listar documentos
- `GET /v1/rag/documents/{id}` — Obter documento
- `DELETE /v1/rag/documents/{id}` — Remover documento
- `POST /v1/rag/query` — Consulta RAG
- `POST /v1/rag/collections` — Criar coleção
- `GET /v1/rag/collections` — Listar coleções

### Admin
- `GET /admin/rag/overview` — Visão geral
- `GET /admin/rag/clients/{client_id}/documents` — Docs por cliente
- `POST /admin/rag/reindex` — Reindexar documentos

## Políticas por Tenant

- `rag_enabled`: Habilita/desabilita RAG
- `max_documents`: Limite de documentos
- `max_storage_mb`: Limite de armazenamento
- `max_pages_per_month`: Limite mensal de páginas
- `allowed_file_types`: Tipos de arquivo permitidos
- `cloud_embeddings_allowed`: Permite embeddings em nuvem
- `retention_days`: Dias de retenção (futuro)

## Segurança

- Uploads são tenant-isolated (diretório por client_id)
- Conteúdo RAG nunca é exposto em logs
- Chunks armazenam tenant_id no metadata_json
- Busca sempre filtra por client_id
- Cloud embeddings desabilitado por padrão
- Documentos são deletados com chunks em cascade

## Validação

```bash
make validate-enterprise-rag
# ou
./scripts/validators/validate-enterprise-rag-local.sh
```
