# Local Production Runbook

This document describes the steps to set up, validate, and maintain the local production environment.

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

Este script realiza:
- Verificação de dependências (Docker, Python, Git, etc).
- Configuração segura de segredos em \`.env.local\`.
- Detecção de GPU e modelos GGUF.
- Inicialização da stack via Docker Compose.
- Execução de migrações de banco de dados.
- Validação completa de produção, segurança e readiness.
- Geração de relatório detalhado em \`artifacts/install-local-appliance/\`.

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
