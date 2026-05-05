# RAG (Retrieval-Augmented Generation) MVP

Este módulo permite que os clientes façam upload de documentos PDF e realizem consultas baseadas no conteúdo desses documentos.

## Fluxo de Funcionamento

1. **Upload**: O cliente envia um arquivo PDF via API ou Portal.
2. **Processamento**: Um worker extrai o texto, divide em chunks e gera embeddings usando um modelo local (`all-MiniLM-L6-v2`).
3. **Armazenamento**: Chunks e embeddings são salvos no Postgres (com suporte a pgvector ou fallback JSONB).
4. **Query**: Ao perguntar, o sistema gera o embedding da pergunta, busca os chunks mais similares e usa-os como contexto para o modelo de linguagem.

## Endpoints da API

Todos os endpoints requerem autenticação via API Key (`Authorization: Bearer sk-...`).

### Upload de Arquivo
`POST /v1/rag/files` (multipart/form-data)
- Campo: `file` (apenas .pdf)
- Retorno: `file_id`, `status`

### Listar Arquivos
`GET /v1/rag/files`

### Remover Arquivo
`DELETE /v1/rag/files/{file_id}`

### Consulta (Query)
`POST /v1/rag/query`
```json
{
  "question": "Qual é a multa por rescisão?",
  "file_ids": ["uuid"],
  "model": "gemma",
  "top_k": 5
}
```

## Configurações (Variáveis de Ambiente)

- `RAG_ENABLED`: true/false
- `RAG_STORAGE_DIR`: Diretório para salvar PDFs
- `RAG_MAX_FILE_MB`: Tamanho máximo do arquivo (default 25)
- `RAG_EMBEDDING_PROVIDER`: local (atualmente suporta apenas local)
- `RAG_EMBEDDING_MODEL`: Modelo sentence-transformers

## Segurança e Isolamento

- Cada documento e chunk é vinculado a um `client_id`.
- Um cliente nunca tem acesso aos documentos de outro.
- Nomes de arquivos são gerados internamente de forma segura.

## Validação

Use o script `scripts/validate-rag.sh` para testar o fluxo completo:

```bash
export CLIENT_API_KEY=sk-your-key
./scripts/validate-rag.sh
```
