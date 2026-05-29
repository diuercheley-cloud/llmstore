---
owner: platform-ops
status: consolidated
---

# Upgrades e Rollbacks

Garantir que atualizações sejam seguras e reversíveis é uma prioridade do LLM Inference Stack.

## Upgrade de Release

O processo de upgrade é projetado para minimizar o downtime e garantir a integridade dos dados.

### Etapas do Upgrade:
1.  **Check de Segurança**: Garante que não há mudanças pendentes no repositório.
2.  **Backup Automático**: Realiza um backup completo do banco de dados e configurações.
3.  **Registro de Ponto de Restauração**: Salva o hash da versão atual em `.rollback_version`.
4.  **Migração de DB**: Executa `alembic upgrade head`.
5.  **Atualização de Imagens**: Reconstrói e reinicia os containers com a nova versão.
6.  **Smoke Tests**: Valida funcionalidades básicas após o reinício.

```bash
make upgrade-release
```

## Rollback de Release

Em caso de falha nos smoke tests ou instabilidade detectada após o upgrade, utilize o comando de rollback.

### Etapas do Rollback:
1.  Identifica a versão anterior no arquivo `.rollback_version`.
2.  Realiza o `git checkout` da versão estável.
3.  Tenta reverter migrações de banco de dados (se suportado).
4.  Reinicia a stack na versão anterior.
5.  Executa validação de sanidade.

```bash
make rollback-release
```

> [!WARNING]
> Rollbacks de banco de dados podem ser complexos se novas migrações incluíram deleção de dados. Sempre revise os logs de backup em caso de falha crítica.
