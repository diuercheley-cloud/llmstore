---
owner: platform-ops
status: consolidated
---

# Local Production Runbook

This document describes the steps to set up, validate, and maintain the local production environment.

## Release Bundle (v1.7.0+)

A partir da v1.7.0-local-ai-appliance, o release bundle e gerado via:

```bash
# Preparar bundle completo (validacao + tar.gz + manifests + security)
./scripts/prepare-v1.7-release-bundle.sh --version v1.7.0-local-ai-appliance

# Validar diretorio de release
./scripts/validate-v1.7-release-bundle.sh
```

O bundle gerado em `releases/v1.7.0-local-ai-appliance/` contem:
- `release-manifest.json` - Metadados da release
- `summary.json` / `summary.md` - Resumo da validacao
- `bundle-manifest.json` - Manifesto do bundle (comprova exclusoes seguras)
- `bundle-checksums.sha256` - Checksums do arquivo .tar.gz

Importante: o arquivo `.tar.gz` e removido do diretorio versionavel (git).
Apenas manifests e checksums seguros sao versionados.

## Billing BRL (v1.8.0)

A v1.8.0 adiciona contabilidade financeira por request via `RequestFinancial` (tabela `request_financials`).

### Configuração

1. Editar `config/provider-pricing.example.json` com custos reais dos providers
2. Editar `config/customer-pricing.example.json` com markup e preços por plano
3. Definir `USD_BRL_RATE` no `.env.local` (default: 5.00)
4. A taxa de câmbio é manual (nenhuma chamada externa por padrão)

### Verificação

```bash
# Simular precificação
curl -X POST http://localhost:8080/admin/billing/pricing/simulate \
  -H "X-Admin-Token: seu-token" \
  -d '{"provider":"local","prompt_tokens":1000,"completion_tokens":500,"plan_code":"basic"}'

# Verificar custos dos providers
curl http://localhost:8080/admin/billing/provider-costs \
  -H "X-Admin-Token: seu-token"

# Verificar margens
curl http://localhost:8080/admin/billing/margins/summary \
  -H "X-Admin-Token: seu-token"

# Verificar registros financeiros
curl http://localhost:8080/admin/billing/usage-financials \
  -H "X-Admin-Token: seu-token"
```

### Validação

```bash
make validate-billing-brl
```

## 1. Setup

O método recomendado para configurar o ambiente de produção local é através do instalador de appliance:

\`\`\`bash
# Instalação completa com validações
make install-local
\`\`\`

## Referências Rápidas

- Endpoint padrão: `localhost:18080`
- Validação principal: `./scripts/validate-local-production-full.sh`
- Fora de Escopo: integração com gateway de pagamento real (PSP)
- Gateway de pagamento real (PSP): permanece desativado nesta edição
- Sem PIX real nesta versão: o fluxo de cobrança continua local e determinístico

## Pre-Deployment Validation
Antes de finalizar a instalação no cliente, rode o checklist de produção:

```bash
make pre-client-check
```

Verifique o relatório em `artifacts/pre-client-checklists/` e garanta o status **GO**.

> **Dica para Operadores:** Em caso de erro em qualquer script de manutenção ou validação, consulte o [Catálogo de Códigos de Erro](OPERATOR_ERROR_CODES.md) para diagnósticos rápidos e ações corretivas padronizadas.
>
> Para validar uma instalação limpa do zero em ambiente isolado (sandbox), use:
> ```bash
> ./scripts/validate-clean-install-local.sh --dry-run
> ```

Este script realiza:
- Verificação de dependências (Docker, Python, Git, etc).
- Configuração segura de segredos em \`.env.local\`.
- Detecção de GPU e modelos GGUF.
- Inicialização da stack via Docker Compose.
- Execução de migrações de banco de dados.
- Validação completa de produção, segurança e readiness.
- Geração de relatório detalhado em \`artifacts/install-local-appliance/\`.

## Fresh Machine Validation

Antes de implantar em uma máquina nova, valide os pré-requisitos:

```bash
# Validacao de readiness de maquina limpa
./scripts/fresh-machine-readiness-check.sh --dry-run

# Validacao completa dos docs e scripts
./scripts/validate-fresh-machine-docs.sh

# Testes automaticos
python -m pytest tests/test_fresh_machine_validation_docs.py tests/test_fresh_machine_readiness_check.py tests/test_fresh_machine_security.py -q
```

Consulte [FRESH_MACHINE_VALIDATION.md](FRESH_MACHINE_VALIDATION.md) para o roteiro completo e checklist de aceite.

## Validation Steps

### 1. Post-Installation Validation
Execute a validação final que consolida o status da instalação e gera o relatório oficial:
```bash
make validate-post-install
```

### 2. Health Check
```bash
make health
```

### 3. Standard Validation
```bash
make validate
```

### 3. Security Report
```bash
make security
```

### 4. Commercial Plans Validation
Initialize and verify the plan matrix:
```bash
./scripts/seed-commercial-plans-local.sh
./scripts/validate-commercial-plans-local.sh
```

### 5. System Control Center Validation
```bash
make validate-control-center
```

### 6. Capability Matrix Validation
Verify the feature matrix and backend readiness:
```bash
./scripts/validate-capability-matrix-local.sh
```

### 7. Validate Abuse Protection
Before finalizing the production environment, ensure it can handle abuse without crashing:
```bash
make validate-abuse
```
Check the generated report in `artifacts/abuse-protection/<timestamp>/abuse-report.md`.

### 8. Paid Implementation Checklist (Client Deployment)

For paid/full-client deployments, generate and fill the implementation checklist:
```bash
make implementation-checklist
make validate-implementation-checklist
```

This checklist covers hardware, access, responsibilities, backup, installation, configuration, models, security, acceptance tests, operator training, and final delivery.

### 9. Client Monthly Report

Generate monthly usage reports for each client with consumption, billing, and recommendations:
```bash
make monthly-report-demo
make validate-monthly-report
```

Reports are generated in `artifacts/monthly-reports/` and include: chat tokens, requests, responses, embeddings, RAG, TTS, errors, rate limit events, local/manual billing, payment status, and upgrade/downgrade suggestions.

## Maintenance

### Upgrades

Realize upgrades utilizando o script de automação, que força a criação de backups para garantir pontos de restauração e aborta caso o backup falhe:
```bash
./scripts/upgrade-local.sh --to-version <nova-versao>
```
Em caso de falhas documentadas nos smoke tests gerados após o upgrade, restaure o estado usando:
```bash
./scripts/rollback-local.sh --to-version <versao-anterior> --backup-id <path-do-backup>
```

### Validacao de Restore e Rollback

Para validar o fluxo completo de backup, upgrade, restore e rollback em ambiente controlado:
```bash
# Modo dry-run (seguro)
./scripts/validate-real-restore-rollback-local.sh --dry-run

# Modo real (exige --yes, executa backup, upgrade, rollback)
./scripts/validate-real-restore-rollback-local.sh --yes
```

## Hybrid Admin Dashboard (v1.8.0)

O Admin Dashboard foi atualizado com cards específicos para a plataforma híbrida:

- **Hybrid AI Platform** — Overview: cloud enabled/disabled, requests, custos, margem, wallets, cache
- **Providers** — Status, capacidades, API key mascarada
- **Provider Health** — Saúde de cada provider
- **Routing Decisions** — Últimas decisões com estratégia, cloud vs local
- **Provider Costs** — Custos configurados USD/1K tokens
- **Revenue & Margin** — Receita, custo, margem (admin apenas)
- **Wallet Balances** — Saldo BRL das carteiras
- **Cache Stats** — Status e hits do cache exato/semântico
- **Enterprise RAG** — Overview: documentos, chunks, coleções, storage

### Hybrid Admin Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /admin/hybrid/summary | Agregador completo |
| GET | /admin/hybrid/providers | Providers com API key mascarada |
| GET | /admin/hybrid/routing | Políticas e últimas decisões |
| GET | /admin/hybrid/financials | Custos, receita e margem por provider |
| GET | /admin/hybrid/cache | Estatísticas do cache |
| GET | /admin/hybrid/wallets | Saldos das carteiras |
| GET | /admin/hybrid/rag | Overview RAG empresarial |

### Validação

```bash
make validate-hybrid-admin

# Testes automatizados
.venv/bin/python -m pytest \
  tests/test_hybrid_admin_summary_api.py \
  tests/test_hybrid_admin_dashboard_ui.py \
  tests/test_hybrid_admin_sanitization.py \
  tests/test_client_portal_no_internal_margin.py \
  -q
```

### Sanitização

- API keys de providers são mascaradas
- Prompts e respostas não expostos
- Documentos RAG não expostos (apenas metadados agregados)
- Margem interna visível apenas no admin dashboard
```
