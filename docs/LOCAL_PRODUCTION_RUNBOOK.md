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

## 1. Setup

O método recomendado para configurar o ambiente de produção local é através do instalador de appliance:

\`\`\`bash
# Instalação completa com validações
make install-local
\`\`\`

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
