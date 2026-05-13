# Hybrid AI Platform (formerly Local AI Appliance)

**OpenAI-compatible hybrid AI infrastructure — local + cloud, multi-provider, multi-tenant, white-label ready.**

> Current build: `v1.8.0-hybrid-ai-platform`  
> Previous stable: [`v1.7.1-post-release-polish`](releases/v1.7.1-post-release-polish)  
> Hybrid AI docs: [`docs/HYBRID_AI_PLATFORM.md`](docs/HYBRID_AI_PLATFORM.md)

---

## O que é

O **Local AI Appliance** é uma stack completa de infraestrutura de IA on-premise, compatível com a API OpenAI. Ela roda inteiramente em hardware local (Linux ou WSL2), sem dependência de nuvem, fornecendo:

- Proxy de inferência OpenAI-compatible (`/v1/chat/completions`, streaming SSE)
- Portal de administração com dashboard, clientes, API keys, planos e billing manual
- RAG (busca semântica em documentos)
- TTS (text-to-speech local)
- Gestão de múltiplos modelos GGUF via Admin Lab
- Relatórios de segurança, readiness e produção

## Para quem serve

- **Empresas** que precisam de soberania de dados e não podem enviar dados para APIs externas
- **Integradores** que implantam soluções de IA on-premise para clientes finais
- **Operadores** que gerenciam múltiplos tenants com quotas, rate limiting e faturamento
- **Equipes de vendas** que precisam demonstrar o produto em reuniões offline

## Principais recursos

| Recurso | Descrição |
|---------|-----------|
| API OpenAI-compatible | `/v1/chat/completions`, `/v1/models`, streaming SSE |
| Multi-Provider | Local, LMStudio, OpenAI, Anthropic, DeepSeek, OpenRouter |
| Admin Dashboard | Gestão de clientes, API keys, uso, billing, providers |
| Admin Lab | Gestão de modelos, backends, testes de prompt |
| Client Portal | Interface do cliente com uso e consumo |
| RAG | Upload de documentos (.pdf, .txt, .md) e busca semântica |
| TTS | Text-to-speech local com pocket-tts |
| Billing manual | Invoices, ciclos, suspensão automática |
| Múltiplos modelos | Suporte a GGUF via llama.cpp, backends HTTP, cloud APIs |
| Segurança | Rate limiting, quotas, API keys hasheadas, circuit breaker |
| Observabilidade | Métricas Prometheus, health/ready endpoints, provider health |

## Quick start

```bash
# 1. Pré-requisitos: Docker, docker compose, git, curl, jq, python3
# 2. Configure o ambiente
cp .env.example .env.local
# Edite ADMIN_TOKEN, POSTGRES_PASSWORD, MODEL_FILE

# 3. Instale o appliance com dados de demonstração
make install-local

# 4. Valide a instalação
make validate
make security
make readiness
```

A stack sobe em `http://localhost:18080` com:
- Admin Dashboard: `/admin-dashboard` (token: `ADMIN_TOKEN`)
- Client Portal: `/client-portal`
- Admin Lab: `/admin-lab`
- API OpenAI: `/v1/chat/completions`

> Para validar uma máquina nova antes de instalar: `make fresh-machine-check` — consulte [FRESH_MACHINE_VALIDATION.md](docs/FRESH_MACHINE_VALIDATION.md).

## Customer demo

```bash
# Demo rápida (valida sem recriar dados)
make customer-demo

# Demo completa (seed de dados, reset, validação)
make customer-demo-full
```

Relatório gerado em `artifacts/customer-demo/<timestamp>/`.

### Documentos de apoio para reuniões

- [Guia de Configuração da Demo](docs/LOCAL_DEMO_GUIDE.md)
- [Roteiro de Apresentação (15/30/60 min)](docs/CLIENT_PRESENTATION_SCRIPT.md)
- [Talk Track — Falas Prontas](docs/CLIENT_DEMO_TALK_TRACK.md)
- [FAQ da Demo Comercial](docs/CLIENT_DEMO_FAQ.md)
- [Objeções Comuns e Respostas](docs/CLIENT_DEMO_OBJECTIONS.md)

### Guia Visual de Demonstração

Storyboard, screenshots e plano de captura: [docs/demo-visual-guide/README.md](docs/demo-visual-guide/README.md)

## Screenshots / Visual Guide

| Interface | Descrição |
|-----------|-----------|
| Landing Page | `http://localhost:18080/` |
| Admin Dashboard | `http://localhost:18080/admin-dashboard` |
| Admin Lab | `http://localhost:18080/admin-lab` |
| Client Portal | `http://localhost:18080/client-portal` |
| Pricing | `http://localhost:18080/pricing` |

Consulte o [Guia Visual de Demonstração](docs/demo-visual-guide/README.md) para screenshots e fluxo de navegação.

## Instalação em cliente

Documentação simplificada para clientes finais que desejam instalar o sistema sem se aprofundar na arquitetura interna:

- [Guia de Requisitos do Sistema](docs/CUSTOMER_REQUIREMENTS.md)
- [Guia de Instalação](docs/CUSTOMER_INSTALL_GUIDE.md)
- [Quickstart (Caminho Curto)](docs/CUSTOMER_QUICKSTART.md)
- [Solução de Problemas (Troubleshooting)](docs/CUSTOMER_TROUBLESHOOTING.md)
- [Paid Implementation Checklist](docs/PAID_IMPLEMENTATION_CHECKLIST.md)

### Integração via API

```bash
# Listar modelos
curl -fsS http://localhost:18080/v1/models \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool

# Chat completion
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Olá!"}],
    "stream": false
  }'
```

Cliente Python SDK: [README_CLIENT.md](README_CLIENT.md)  
Exemplos completos: [`examples/`](examples/)  
Integrações (Open WebUI, n8n, LangChain): [`docs/integrations/`](docs/integrations/)

## Operação diária

```bash
# Subir/descer a stack
./scripts/up.sh
./scripts/down.sh

# Validar saúde
make health

# Validar produção
make validate

# Backup e restore
make backup
make rollback
make upgrade

# Ver logs
docker compose logs -f control-plane

# Métricas
curl -fsS http://localhost:18080/metrics
```

Documentação operacional detalhada:
- [Local Production Runbook](docs/LOCAL_PRODUCTION_RUNBOOK.md)
- [Operator Commands](docs/OPERATOR_COMMANDS.md)
- [Operator Error Codes](docs/OPERATOR_ERROR_CODES.md)
- [Guia de Validação](docs/LOCAL_PRODUCTION_VALIDATION.md)
- [White-Label / Branding](docs/WHITE_LABEL_LOCAL.md)

## Segurança / Readiness

```bash
# Relatório de segurança
make security

# Readiness check
make readiness

# Verificar health
make health

# Fresh machine validation (máquina nova)
make fresh-machine-check

# Escanear secrets no código
./scripts/check-secrets.sh --all
```

- [Security Report](docs/SECURITY_LOCAL.md)
- [Production Readiness](docs/PRODUCTION_READINESS_LOCAL.md)
- [Disaster Recovery](docs/DISASTER_RECOVERY_LOCAL.md)
- [Retention Policy](docs/RETENTION_LOCAL.md)

## Limitações

- **PSP real está fora do escopo.** O sistema simula faturamento com invoices e ciclos, mas não processa pagamentos reais.
- **PIX real está fora do escopo.** Não há integração com gateways de pagamento brasileiros.
- **Cloud gerenciada está fora do escopo.** O appliance é on-premise; não oferecemos versão SaaS gerenciada neste repositório.
- **Modelos dependem do hardware local.** Desempenho varia conforme GPU, RAM e quantização. Consulte [docs/MODEL_BENCHMARK_LOCAL.md](docs/MODEL_BENCHMARK_LOCAL.md).
- **Recursos opcionais dependem de configuração.** RAG, TTS, observabilidade e cache requerem ativação explícita em `.env.local`.
- **Troca de modelo GGUF exige reinício do container data plane.**
- **Cálculo de tokens é estimado**, não usa tokenizer oficial.
- **Cancelamento de geração** depende do encerramento da conexão HTTP do stream.

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [Release Notes v1.7.0](docs/V1_7_RELEASE_NOTES.md) | Novidades e mudanças da release |
| [Client Ready Final Report](docs/CLIENT_READY_FINAL_REPORT.md) | Status consolidado de prontidão |
| [Go/No-Go Summary](docs/V1_7_GO_NO_GO_SUMMARY.md) | Resumo da decisão de release |
| [Fresh Machine Validation](docs/FRESH_MACHINE_VALIDATION.md) | Roteiro para máquina nova/WSL limpo |
| [Customer Install Guide](docs/CUSTOMER_INSTALL_GUIDE.md) | Instalação para cliente final |
| [Customer Troubleshooting](docs/CUSTOMER_TROUBLESHOOTING.md) | Solução de problemas |
| [Local Demo Guide](docs/LOCAL_DEMO_GUIDE.md) | Preparação de demonstração |
| [Local Production Runbook](docs/LOCAL_PRODUCTION_RUNBOOK.md) | Operação diária |
| [Capability Matrix](docs/CAPABILITY_MATRIX.md) | Matriz de capacidades |
| [Security Local](docs/SECURITY_LOCAL.md) | Segurança e hardening |
| [Production Readiness](docs/PRODUCTION_READINESS_LOCAL.md) | Readiness de produção |
| [OpenAI Compatibility](docs/OPENAI_COMPATIBILITY.md) | Detalhes da API compatível |
| [Release History](docs/RELEASE_HISTORY.md) | Histórico consolidado de versões |
| [API Sales](docs/API_SALES.md) | Fluxo comercial e onboarding |

## Release History

Consulte [docs/RELEASE_HISTORY.md](docs/RELEASE_HISTORY.md) para o histórico consolidado de versões.

- [v1.7.0 Release Checklist](docs/V1_7_RELEASE_CHECKLIST.md) — Checklist formal de promoção
- [v1.6 Audit Summary](docs/V1_6_AUDIT_SUMMARY.md) — Auditoria da linha anterior

## Roadmap

- Autenticação administrativa com RBAC e rotação de credenciais
- Configuração dinâmica persistida com cache invalidation
- Fila distribuída e workers externos para múltiplos data planes
- Tokenizer real para contabilidade de tokens
- Tracing distribuído e retenção externa de métricas/logs

---

*Local AI Appliance — v1.7.1-post-release-polish — [docs/RELEASE_HISTORY.md](docs/RELEASE_HISTORY.md)*
