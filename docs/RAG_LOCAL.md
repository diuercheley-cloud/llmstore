# RAG Local

## Enterprise RAG

O sistema agora possui RAG Empresarial com suporte a múltiplos formatos.

### Formatos Suportados

- **Sempre disponíveis**: `.txt`, `.md`, `.csv`
- **Com dependência opcional**: `.pdf` (pymupdf), `.docx` (python-docx), `.xlsx` (openpyxl)

### Estratégias de Chunking

- `fixed`: Tamanho fixo com overlap configurável
- `heading`: Divisão por cabeçalhos
- `semantic_placeholder`: Divisão por parágrafos

### Armazenamento Local

- Uploads salvos em `{RAG_STORAGE_DIR}/{client_id}/enterprise/`
- Embeddings locais via sentence-transformers ou mock SHA-256
- Cloud embeddings desabilitado por padrão (LGPD)

### Uso

```bash
# Upload
curl -X POST http://localhost:8000/v1/rag/documents \
  -H "Authorization: Bearer sk-..." \
  -F "file=@documento.txt"

# Query
curl -X POST http://localhost:8000/v1/rag/query \
  -H "Authorization: Bearer sk-..." \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual o valor do contrato?"}'
```

### Validação

```bash
make validate-enterprise-rag
```

## RAG MVP (Original)

O RAG original (MVP) permanece funcional nos endpoints `/v1/rag/files` e `/client/rag/documents`. Nenhuma quebra de compatibilidade foi introduzida.
