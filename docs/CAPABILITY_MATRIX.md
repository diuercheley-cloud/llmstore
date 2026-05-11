# Capability Matrix

Esta matriz detalha as capacidades do sistema `llm-inference-stack` por ambiente e backend.

| Feature | Mock | Local Real | Production Local | Status | Limitações | Validador |
|---------|------|------------|------------------|--------|------------|-----------|
| `/v1/chat/completions` | ✅ | ✅ | ✅ | GA | - | `scripts/test-chat.sh`, `scripts/validate-chat-sse-readiness-local.sh` |
| streaming | ✅ | ✅ | ✅ | GA | - | `scripts/test-stream.sh`, `scripts/validate-chat-sse-readiness-local.sh` |
| `/v1/models` | ✅ | ✅ | ✅ | GA | - | `curl /v1/models` (Includes capabilities, status and readiness flags) |
| `/v1/embeddings` | ✅ (Deterministic) | ❌ | ⚠️ (Mock) | Partial | Mock por padrão | `scripts/test-embeddings.sh` |
| `/v1/responses` | ✅ | ✅ | ✅ | Beta | Sem streaming | `scripts/test-responses.sh` |
| tools/function calling | ❌ | ⚠️ (Partial) | ❌ | Unsupported | Depende do backend | - |
| RAG | ⚠️ (Partial) | ✅ | ✅ | GA | Requer embeddings | `scripts/test-rag.sh` |
| TTS | ❌ | ✅ | ✅ | GA | Via pocket-tts | `scripts/pocket-tts.sh` |
| billing manual/local | ✅ | ✅ | ✅ | GA | - | `scripts/run-billing-cycle.sh` |
| PSP/PIX real | ❌ | ❌ | ❌ | Future | Não implementado | - |
| Client Portal | ✅ | ✅ | ✅ | GA | - | `scripts/ui-health.sh` |
| Admin Dashboard | ✅ | ✅ | ✅ | GA | - | `scripts/ui-health.sh` |
| Admin Lab | ✅ | ✅ | ✅ | GA | - | `scripts/ui-health.sh` |
| DR/backup/restore | ✅ | ✅ | ✅ | GA | - | `scripts/dr-test-local.sh` |
| upgrade/rollback | ✅ | ✅ | ✅ | GA | - | `scripts/upgrade-test.sh` |
| tenant export/delete | ✅ | ✅ | ✅ | GA | - | `scripts/export-client-local.sh` |
| security report | ✅ | ✅ | ✅ | GA | - | `scripts/security-report-local.sh` |
| readiness report | ✅ | ✅ | ✅ | GA | - | `scripts/production-readiness-local.sh` |

## Legenda

- ✅ **Supported**: Funcionalidade completa e testada.
- ⚠️ **Partial/Warning**: Funcionalidade implementada com limitações ou via mock em produção.
- ❌ **Not Supported**: Funcionalidade não disponível ou não planejada para este backend.
- **GA**: General Availability (Estável).
- **Beta**: Funcionalidade em testes, sujeita a alterações.
- **Future**: Planejado para versões futuras.
