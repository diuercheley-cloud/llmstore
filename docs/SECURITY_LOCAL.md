# SECURITY LOCAL - Appliance Local de IA

## Enterprise RAG Security

### Isolamento Multi-Tenant

Cada documento e chunk RAG é vinculado a um `client_id`:

- `rag_documents.client_id` — FK para clients
- `rag_document_chunks.client_id` — FK para clients
- `rag_document_chunks.metadata_json.tenant_id` — Metadado de auditoria

### Busca com Isolamento

Toda consulta RAG filtra por `client_id`:

```sql
SELECT ... FROM rag_document_chunks WHERE client_id = :client_id
```

### Proteção de Dados

- Uploads são armazenados em diretórios tenant-isolated: `{RAG_STORAGE_DIR}/{client_id}/enterprise/`
- Conteúdo RAG nunca é exposto em logs
- Nomes de arquivos internos usam UUIDs
- Cloud embeddings desabilitado por padrão
- Documentos e chunks são deletados em cascade

### LGPD e Retenção

- retention_days pode ser configurado por política
- Delete remove chunks + arquivo + registro ORM
- Nenhum dado é enviado para cloud sem autorização explícita

### Abuse Detection

O sistema de detecção de abuso opera localmente com 11 sinais:

- `requests_per_minute_above_plan` — requests acima do plano
- `tokens_per_minute_above_plan` — tokens acima da cota
- `repeated_auth_errors` — 5+ erros 401/403 em 5min
- `repeated_giant_prompts` — 3+ prompts gigantes repetidos
- `request_loop` — 5+ mesma request exata
- `high_cache_miss_repetitive` — cache miss率高 com padrão repetitivo
- `cloud_without_balance` — tentativa de usar cloud sem saldo
- `high_estimated_cost` — custo > R$5 em período curto
- `repeated_streaming_abort` — streaming abortado repetidamente
- `excessive_rag_upload` — 5+ uploads RAG em 5min
- `excessive_tts_chars` — caracteres TTS acima do limite

Auto-suspensão é **desligada por padrão** e **dry-run** é ativado.

### Validação de Segurança

```bash
./scripts/check-secrets.sh --all
./scripts/validate-enterprise-rag-local.sh
./scripts/validate-hybrid-abuse-detection-local.sh
```

### Dependências Críticas

| Pacote | Função | Obrigatório |
|--------|--------|-------------|
| pymupdf | Parse PDF | Não (fallback) |
| python-docx | Parse DOCX | Não (fallback) |
| openpyxl | Parse XLSX | Não (fallback) |

Serviços externos: **Nenhum obrigatório**.
