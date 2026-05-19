# Deployment Automation

Este diretório contém configurações e metadados para a automação de deployment da stack.

## Estrutura de Scripts

Os scripts de execução principal estão localizados em `scripts/` para manter a compatibilidade com o padrão de execução do repositório:

- `scripts/preflight-check.sh`: Validação de pré-requisitos.
- `scripts/deploy-appliance.sh`: Deployment local/on-prem.
- `scripts/deploy-kubernetes.sh`: Deployment via Helm.
- `scripts/upgrade-release.sh`: Fluxo de upgrade com backup.
- `scripts/rollback-release.sh`: Fluxo de reversão de versão.
- `scripts/post-deploy-validate.sh`: Validação pós-deploy.

## Artefatos de Execução

Cada execução gera logs e sumários auditáveis em:
`artifacts/deployments/<timestamp>/`

## Uso via Makefile

```bash
make preflight
make deploy-appliance
make deploy-k8s
make upgrade-release
make rollback-release
make post-deploy-validate
```
