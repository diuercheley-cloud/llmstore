# Capability Matrix

Esta matriz detalha as capacidades do sistema `llm-inference-stack` por ambiente e backend.

| Feature | Mock | Local Real | Production Local | Cloud (OpenAI) | Cloud (Anthropic) | Cloud (DeepSeek) | Status | Limitações | Validador |
|---------|------|------------|------------------|----------------|-------------------|------------------|--------|------------|-----------|
| `/v1/chat/completions` | ✅ | ✅ | ✅ | ✅ (adapter) | ✅ (adapter) | ✅ (adapter) | GA | - | `scripts/test-chat.sh` |
| streaming | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | GA | - | `scripts/test-stream.sh` |
| `/v1/models` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | GA | Inclui provider_info | `curl /v1/models` |
| `/v1/embeddings` | ✅ (Deterministic) | ❌ | ⚠️ (Mock) | ✅ | ❌ | ✅ | Partial | Mock por padrão | `scripts/test-embeddings.sh` |
| `/v1/responses` | ✅ | ✅ | ✅ | ✅ | ⚠️ (via chat) | ✅ | Beta | Sem streaming; tools seguem capability do provider/modelo | `scripts/test-responses.sh` |
| tools/function calling | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | Partial | `llama.cpp` e `openai_compatible` recebem payload OpenAI nativo; `ollama`/`vllm` retornam `capability_not_supported`; logs persistem preview sanitizado | - |
| Smart Routing | ✅ | ✅ | ✅ | ✅ (adapter) | ✅ (adapter) | ✅ (adapter) | GA (v1.8) | Cloud disabled por padrão | `scripts/validate-smart-routing-local.sh` |
| Multi-Provider | ✅ | ✅ | ✅ | ⚠️ (disabled default) | ⚠️ (disabled default) | ⚠️ (disabled default) | GA (v1.8) | Cloud disabled por padrão | `scripts/validate-providers-local.sh` |
| Provider Registry | ✅ | ✅ | ✅ | ⚠️ (disabled default) | ⚠️ (disabled default) | ⚠️ (disabled default) | GA (v1.8) | Cloud disabled por padrão | `scripts/validate-providers-local.sh` |
| Billing BRL | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | GA (v1.8) | FX rate via env, sem chamada externa | `scripts/validate-billing-brl-local.sh` |
| Prepaid Wallet BRL | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | GA (v1.8) | Topup mock local; PSP real opt-in | `scripts/validate-prepaid-wallet-local.sh` |
| Enterprise RAG | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | GA (v1.8) | PDF/DOCX/XLSX opcionais | `scripts/validate-enterprise-rag-local.sh` |
| Intelligent Cache (exact) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | GA (v1.8) | - | `scripts/validate-intelligent-cache-local.sh` |
| Intelligent Cache (semantic) | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | Beta (v1.8) | Requer sentence-transformers | `scripts/validate-intelligent-cache-local.sh` |
| Admin Hybrid Dashboard | ✅ | ✅ | ✅ | ⚠️ (cloud disabled) | ⚠️ (cloud disabled) | ⚠️ (cloud disabled) | GA (v1.8) | API keys mascaradas | `scripts/validate-hybrid-admin-dashboard-local.sh` |
| Abuse Detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | GA (v1.8) | Dry-run por padrão | `scripts/validate-abuse-protection-local.sh` |
| Hybrid E2E Validation | ✅ | ✅ | ✅ | ⚠️ (no real calls) | ⚠️ (no real calls) | ⚠️ (no real calls) | GA (v1.8) | Sem cloud real | `scripts/validate-hybrid-platform-e2e-local.sh` |
| RAG | ⚠️ (Partial) | ✅ | ✅ | ❌ | ❌ | ❌ | GA | Requer embeddings | `scripts/test-rag.sh` |
| TTS | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | GA | Via pocket-tts | `scripts/pocket-tts.sh` |
| billing manual/local | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | GA | - | `scripts/run-billing-cycle.sh` |
| PSP/PIX real | ✅ (mock) | ⚠️ (opt-in) | ⚠️ (opt-in) | ❌ | ❌ | ❌ | Partial | `PAYMENT_REAL_ENABLED=false` por padrão; adapter real placeholder | - |
| Client Portal | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | GA | - | `scripts/ui-health.sh` |
| Admin Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | GA | Inclui providers view | `scripts/ui-health.sh` |
| Admin Lab | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | GA | - | `scripts/ui-health.sh` |
| DR/backup/restore | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | GA | - | `scripts/dr-test-local.sh` |
| upgrade/rollback | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | GA | - | `scripts/upgrade-test.sh` |
| tenant export/delete | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | GA | - | `scripts/export-client-local.sh` |
| security report | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | GA | Não vaza secrets | `scripts/security-report-local.sh` |
| readiness report | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | GA | - | `scripts/production-readiness-local.sh` |

## Pagina de Capacidades (/capabilities)

O sistema expoe uma pagina publica de capacidades em `GET /capabilities` com versao, lista de recursos, status e limitacoes.

Endpoint JSON: `GET /public/capabilities` — retorna `version`, `features`, `limitations`, `local_appliance_mode`. Sem secrets expostos.

```bash
# Visualizar pagina
open http://localhost:18080/capabilities

# Visualizar JSON
curl -s http://localhost:18080/public/capabilities | python3 -m json.tool
```

A pagina e atualizada automaticamente com a versao atual do sistema via JS. As limitacoes de PSP/PIX real, tools/function calling parcial, streaming em `/v1/responses` e dependencia de hardware local sao exibidas explicitamente.

## Function Calling

Resumo rapido por provider/modelo:

| Provider/modelo registrado | `/v1/chat/completions` | `/v1/responses` | Observacoes |
|---|---|---|---|
| `openai_compatible` | Supported | Supported | Payload OpenAI encaminhado nativamente, com validacao local e logs sanitizados |
| `llama.cpp` | Supported | Supported | Payload OpenAI encaminhado ao backend com validacao local e logs sanitizados |
| `ollama` | Not Supported | Not Supported | Retorna erro `capability_not_supported` quando `tools` e enviado |
| `vllm` | Not Supported | Not Supported | Retorna erro `capability_not_supported` quando `tools` e enviado |

Regras de seguranca local-first:

- Maximo de `tools` por request: `16`
- Schema por tool: `24 KiB`
- Profundidade maxima de schema: `8`
- Propriedades maximas por schema: `256`
- Argumentos de tool retornados pelo provider: `16 KiB`
- `RequestLog` persiste apenas `tool_call_count` e preview sanitizado, nunca os argumentos completos

## Legenda

- ✅ **Supported**: Funcionalidade completa e testada.
- ⚠️ **Partial/Warning**: Funcionalidade implementada com limitações ou via mock em produção.
- ❌ **Not Supported**: Funcionalidade não disponível ou não planejada para este backend.
- **GA**: General Availability (Estável).
- **Beta**: Funcionalidade em testes, sujeita a alterações.
- **Future**: Planejado para versões futuras.
