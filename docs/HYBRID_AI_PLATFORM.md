---
owner: platform-ops
status: consolidated
---

# Hybrid AI Platform

## Visão Geral

Este documento descreve a plataforma híbrida que combina inferência local com serviços cloud, incluindo RAG Empresarial.

## Componentes

### 1. Inferência Local
- Modelos rodam localmente via Control Plane + Data Plane
- Suporte a Gemma, Llama, Mistral e outros modelos open-source

### 2. RAG Empresarial
- Pipeline completo: Parse -> Chunk -> Embed -> Retrieve -> Generate
- Múltiplos formatos: TXT, MD, CSV, PDF, DOCX, XLSX
- Chunking estratégico: fixed, heading, semantic
- Embeddings locais (sentence-transformers) com fallback mock
- Isolamento multi-tenant por client_id

### 3. Modos de Operação

#### Local-Only (padrão)
- Tudo roda localmente
- Embeddings mock ou sentence-transformers
- Sem dependência de cloud
- LGPD compliant

#### Híbrido (cloud_allowed)
- Embeddings podem usar API cloud se tenant permite
- Providers configuráveis por cliente

### 4. Arquitetura

```
┌─────────────────────────────────────────────────┐
│                   Control Plane                  │
│  ┌───────────────────────────────────────────┐  │
│  │         Enterprise RAG Pipeline            │  │
│  │  ┌──────┐ ┌───────┐ ┌─────────┐ ┌──────┐ │  │
│  │  │Parse │ │Chunk  │ │Embedding│ │Search│ │  │
│  │  └──────┘ └───────┘ └─────────┘ └──────┘ │  │
│  └───────────────────────────────────────────┘  │
│                  │                               │
│                  ▼                               │
│  ┌───────────────────────────────────────────┐  │
│  │         Multi-Tenant Isolation             │  │
│  │  Client A ── rag_documents (client_id)    │  │
│  │  Client B ── rag_documents (client_id)    │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 5. Endpoints Híbridos

| Endpoint | Descrição | Tenant Isolated |
|----------|-----------|-----------------|
| POST /v1/rag/documents | Upload documento | Sim |
| GET /v1/rag/documents | Listar documentos | Sim |
| DELETE /v1/rag/documents/{id} | Remover documento | Sim |
| POST /v1/rag/query | Consulta RAG | Sim |
| POST /v1/rag/collections | Criar coleção | Sim |
| GET /admin/rag/overview | Admin overview | Apenas admin |

### 6. Admin Dashboard - Hybrid Platform

O Admin Dashboard (`/admin-dashboard`) agora inclui cards específicos para monitorar
a plataforma híbrida:

| Card | Descrição |
|------|-----------|
| **Hybrid AI Platform** | Overview com cloud enabled/disabled, requests local/cloud, custos, margem |
| **Providers** | Status de cada provider (enabled, configured, API key mascarada) |
| **Provider Health** | Saúde de cada provider (healthy/down/unknown) |
| **Routing Decisions** | Últimas decisões de roteamento com estratégia, cloud vs local, custo |
| **Provider Costs** | Custos configurados por provider (USD/1K tokens) |
| **Revenue & Margin** | Receita, custo, margem por provider (admin apenas) |
| **Wallet Balances** | Saldo das carteiras pré-pagas por cliente |
| **Cache Stats** | Status do cache exato e semântico, hits/entries |
| **Enterprise RAG** | Overview: documentos, chunks, coleções, storage |

### 7. Admin Hybrid API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /admin/hybrid/summary | Agregador completo da plataforma híbrida |
| GET | /admin/hybrid/providers | Lista providers com status e API key mascarada |
| GET | /admin/hybrid/routing | Políticas de roteamento e últimas decisões |
| GET | /admin/hybrid/financials | Custos, receita e margem por provider |
| GET | /admin/hybrid/cache | Estatísticas do cache |
| GET | /admin/hybrid/wallets | Saldos das carteiras |
| GET | /admin/hybrid/rag | Overview do RAG empresarial |

Protegidos por admin token (`X-Admin-Token`).

### 8. Sanitização

Os endpoints híbridos aplicam sanitização automática:
- API keys de providers são mascaradas (`sk-****abcd`)
- Prompts e respostas não são expostos
- Documentos RAG não são expostos (apenas metadados)
- Paths sensíveis são mascarados
- Margem interna só aparece no admin, nunca no client portal

### 9. Abuse Detection

O sistema de detecção de abuso protege custos, provedores cloud e recursos locais:

- 11 sinais de abuso monitorados (requests, tokens, auth errors, loops, cache miss, cost spike, etc.)
- Ações configuráveis: log_only, warn, throttle, captcha, suspensão
- Modo dry-run seguro (padrão) - não afeta clientes reais
- Auto-suspend desligado por padrão
- Zero dependência de cloud, zero carga pesada
- Nenhum prompt completo ou API key é logado

Config:

```env
ABUSE_DETECTION_ENABLED=true
ABUSE_AUTO_SUSPEND_ENABLED=false
ABUSE_DRY_RUN=true
```

Admin endpoints:

| Método | Rota |
|--------|------|
| GET | `/admin/security/abuse/events` |
| GET | `/admin/security/abuse/summary` |
| POST | `/admin/security/abuse/actions/{id}/ack` |
| POST | `/admin/security/abuse/clients/{id}/suspend` |
| POST | `/admin/security/abuse/clients/{id}/unsuspend` |

### 10. Validação

```bash
# E2E Validation (v1.8.0)
make validate-hybrid-e2e

# Individual component validation
make validate-hybrid-admin
make validate-hybrid-abuse

# Report validation
./scripts/validate-hybrid-platform-report.sh

# Testes específicos
.venv/bin/python -m pytest \
  tests/test_hybrid_admin_summary_api.py \
  tests/test_hybrid_admin_dashboard_ui.py \
  tests/test_hybrid_admin_sanitization.py \
  tests/test_client_portal_no_internal_margin.py \
  tests/test_hybrid_abuse_detection.py \
  tests/test_abuse_detection_dry_run.py \
  tests/test_abuse_admin_api.py \
  tests/test_abuse_detection_security.py \
  tests/test_hybrid_platform_e2e_script.py \
  tests/test_hybrid_platform_e2e_report.py \
  tests/test_hybrid_platform_security.py \
  -q
```

### 11. E2E Validation Report

The E2E validation generates a comprehensive report in `artifacts/hybrid-platform-e2e/<timestamp>/`:

| File | Description |
|------|-------------|
| `hybrid-e2e.json` | Full structured report (machine-readable) |
| `hybrid-e2e.md` | Human-readable summary |
| `logs/` | Detailed logs per validation step |

**Status values:**
- `HYBRID_READY` — All checks passed
- `HYBRID_READY_WITH_WARNINGS` — All critical checks passed, warnings present
- `HYBRID_FAILED` — Critical failures detected

**Validated components:**
- Provider Registry (local enabled, cloud disabled)
- Smart Routing (local-first strategy)
- Chat, Responses, Embeddings (local/mock)
- Intelligent Cache (exact MISS/HIT)
- Billing BRL (price calculation, margin)
- Prepaid Wallet (credit/debit simulation)
- Enterprise RAG (parsers, chunking, embeddings, policies, deletion)
- Admin Hybrid Dashboard (summary, providers, routing, financials)
- Abuse Detection (dry-run mode, no real impact)
- Client Portal (no internal margin exposure)
- Security Report (`PASS`)
- Production Readiness (`READY`)
- Full Local Production Validation

**Out of scope:**
- Real PSP/PIX integration
- Real GPU stress testing
- Real SSL/DNS validation

### 12. Real Provider Validation (v1.8.1)

A validação de providers reais (OpenAI, DeepSeek, Anthropic) permite testar
chaves e conectividade com segurança, sem comprometer secrets:

- **Opt-in obrigatório:** `REAL_PROVIDER_VALIDATION_ENABLED=true` + `*_PROVIDER_ENABLED=true`
- **Cost cap:** `REAL_PROVIDER_MAX_COST_BRL` limita custo por requisição
- **Chaves mascaradas:** `mask_provider_key()` exibe apenas `sk-p****abcd`
- **Sem internet nos testes:** testes unitários não dependem de rede
- **SKIP_PROVIDER_NOT_CONFIGURED:** providers sem chave são ignorados

Documentação completa: [REAL_PROVIDER_VALIDATION.md](REAL_PROVIDER_VALIDATION.md)

```bash
# Validar ambiente
make validate-real-provider-env

# Rodar testes (sem internet)
.venv/bin/python -m pytest \
  tests/test_real_provider_env.py \
  tests/test_real_provider_env_security.py \
  tests/test_real_provider_env_example.py \
  -q
```

**Segurança:**
- `.env.local` em `.gitignore` — chaves nunca versionadas
- `check-secrets.sh` detecta vazamentos
- Permissão 600 recomendada em `.env.local`
- Nenhum provider real é obrigatório — stack funciona 100% local

### Fallback Local-to-Cloud Validation (v1.8.1)

A validação de fallback garante que o roteamento híbrido funcione corretamente:
- Local é tentado primeiro
- Se local falhar, cloud configurado assume (se autorizado)
- Se cloud não autorizado, fallback para local/mock
- Billing registra `fallback_used` e `cloud_used`

Mecanismo: `ROUTING_TEST_FORCE_LOCAL_FAILURE` — quando `=true`, providers locais
são tratados como indisponíveis pelo smart router. Totalmente em memória, sem
afetar containers ou ambiente real.

```bash
# Dry-run (simulação de roteamento)
make validate-real-fallback-dry

# Real (com chamada para cloud)
make validate-real-fallback

# Testes unitários
.venv/bin/python -m pytest tests/test_real_fallback_*.py -q
```

Documentação: [SMART_ROUTING.md](SMART_ROUTING.md), [REAL_PROVIDER_VALIDATION.md](REAL_PROVIDER_VALIDATION.md)
