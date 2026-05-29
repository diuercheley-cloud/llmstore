---
owner: platform-ops
status: consolidated
---

# Deployment como Local Appliance

O modo *Appliance* é ideal para instalações *on-premises* ou máquinas dedicadas onde o controle total da infraestrutura é necessário.

## Pré-requisitos

1.  Ter executado o `make preflight` com sucesso.
2.  Configurar as variáveis de ambiente no arquivo `.env.local`.

## Fluxo de Instalação

O comando de deploy automatiza as seguintes etapas:
- Carregamento de variáveis de ambiente.
- Inicialização de diretórios de dados e modelos.
- Aplicação de migrações de banco de dados (Alembic).
- Inicialização dos containers via Docker Compose.
- Aguarda a disponibilidade dos serviços (`/health`, `/ready`).
- Executa o checklist de prontidão operacional.

## Como Executar

```bash
make deploy-appliance
```

## Pós-instalação

Após o deploy, você pode validar a instalação completa com:

```bash
make post-deploy-validate
```

O sumário do deploy estará disponível em:
`artifacts/deployments/<timestamp>/deploy-summary.md`
