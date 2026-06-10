---
owner: platform-ops
status: consolidated
---

# Upgrade e Rollback Local

Este documento descreve os procedimentos para atualizar e reverter versões da stack `llm-inference-stack` em ambiente de produção local.

## Upgrade Local

O script `scripts/deploy/upgrade-local.sh` automatiza o processo de atualização.

### Pré-requisitos
- Working tree limpa (sem alterações não commitadas).
- Git configurado com acesso às tags/branches alvo.

### Como executar
```bash
./scripts/deploy/upgrade-local.sh --to-version v1.5.6
```

### O que o script faz:
1. Valida se o ambiente está limpo e sem segredos expostos.
2. Cria um backup completo (Banco de dados e arquivos RAG) em `artifacts/backups-local/`.
3. Troca o código para a versão desejada (`git checkout`).
4. Reconstrói as imagens Docker (se necessário).
5. Valida a integridade das migrations do Alembic (`validate-migrations-local.sh`).
6. Sobe a stack e aplica migrations do banco de dados.
7. Valida novamente o status das migrations após o upgrade.
8. Executa testes de fumaça (smoke tests) para validar a saúde da aplicação.
9. Gera um relatório em `artifacts/upgrades/`.

---

## Validação de Migrations

Para garantir que as migrations não quebrem o banco de dados, existem dois scripts dedicados:

### Validação Estática e Local
```bash
# Verifica heads duplicadas, conflitos e imports
./scripts/validators/validate-migrations-local.sh
```

### Validação com Banco Temporário (Isolado)
Este modo sobe um container Postgres limpo, aplica todas as migrations do zero e valida o schema final.
```bash
./scripts/validators/validate-migrations-local.sh --temp-db
```

### Simulação Completa de Upgrade
Valida o fluxo completo: backup -> validação -> upgrade -> health check -> smoke test.
```bash
./scripts/validators/validate-upgrade-migrations-local.sh
```

### Opções úteis
- `--dry-run`: Simula o processo sem alterar arquivos ou estado.
- `--skip-backup`: Pula a criação do backup automático. NÃO RECOMENDADO. Requer o uso da flag explícita de confirmação `--yes`.
- `--no-build`: Pula a reconstrução das imagens.

---

## Smoke Test Pós-Upgrade

Após qualquer operação de alteração de versão (upgrade ou rollback), a stack é validada automaticamente pelo script `scripts/validators/post-upgrade-smoke-local.sh`.

Este teste valida:
- Saúde básica de todos os endpoints (`/health`, `/ready`).
- Status dos containers Docker.
- Listagem de modelos e chat completion simples (unary e stream).
- Acesso administrativo e planos de faturamento.
- Funcionalidade de RAG e TTS (se habilitados).

Você pode rodar este teste manualmente a qualquer momento:
```bash
make post-upgrade-smoke
```

Os relatórios detalhados são salvos em `artifacts/post-upgrade-smoke/<timestamp>/`.

### Validacao de Restore e Rollback (Ambiente Controlado)

Para validar o fluxo completo de restore/rollback sem risco ao ambiente real:

```bash
# Dry-run (seguro, apenas verifica scripts existentes e requisitos)
./scripts/validators/validate-real-restore-rollback-local.sh --dry-run

# Validacao completa com backup, upgrade simulado e rollback
./scripts/validators/validate-real-restore-rollback-local.sh --yes

# Executar testes
.venv/bin/python -m pytest tests/test_real_restore_rollback_validator.py tests/test_real_restore_rollback_safety.py tests/test_real_restore_rollback_report.py -q
```

Relatorio gerado em `artifacts/restore-rollback-test/<timestamp>/`.

---

## Rollback Local

Caso ocorra um erro após o upgrade, use o script `scripts/dev/rollback-local.sh`.

### Como executar
```bash
./scripts/dev/rollback-local.sh --to-version v1.5.5 --backup-id artifacts/backups-local/20260509T120000
```

### O que o script faz:
1. Exige uma confirmação forte digitando `ROLLBACK LOCAL <version>`.
2. Para os serviços atuais.
3. Retorna o código para a versão anterior.
4. Restaura o banco de dados e arquivos a partir do `backup-id` informado.
5. Sobe a stack e valida com smoke tests.
6. Gera um relatório em `artifacts/rollbacks/`.

---

## Garantias de Segurança

- **Backup Mandatório:** O upgrade exige backup por padrão.
- **Validação de Segredos:** O script impede o upgrade se detectar segredos no código.
- **Confirmação Forte:** O rollback exige digitação manual do comando de confirmação.
- **Integridade de Dados:** Pastas como `models/` e `data/rag_uploads/` são preservadas ou manipuladas via scripts oficiais de backup/restore.
- **Relatórios:** Todas as operações geram logs e relatórios JSON/Markdown para auditoria.

---

## Validação de Scripts

Para validar que os scripts de upgrade/rollback estão funcionando corretamente (sem realizar uma troca real):
```bash
./scripts/validators/validate-upgrade-rollback-local.sh
```
a troca real):
```bash
./scripts/validators/validate-upgrade-rollback-local.sh
```
