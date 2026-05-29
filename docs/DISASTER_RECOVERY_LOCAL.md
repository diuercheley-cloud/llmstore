---
owner: platform-ops
status: consolidated
---

# Disaster Recovery Local

Este fluxo cobre backup, restore e teste de desastre para o `llm-inference-stack` em ambiente local.

## O Que Entra No Backup

- Dump completo do Postgres.
- Configuração relevante em texto, com segredos mascarados.
- Registry de modelos, clientes, invoices, payments e metadados RAG, via dump do banco.
- Uploads RAG em disco, quando `--include-rag-files` for usado.
- Blobs GGUF e demais arquivos de modelo, quando `--include-models` for usado.
- Redis snapshot não é incluído por padrão.

## O Que Fica Fora Por Padrão

- Arquivos GGUF grandes.
- Snapshots de Redis.
- Segredos em claro.

## Scripts

- `./scripts/backup-local.sh`
- `./scripts/restore-local.sh [OPÇÕES] <backup_dir>`
- `./scripts/dr-test-local.sh [--strict-rag]`

### Opções do Restore Local

- `--force-rag-overwrite`: Sobrescreve arquivos RAG existentes se houver conflito.
- `--dry-run`: Valida o backup e mostra o resumo do manifest, sem alterar nada no sistema.
- `-y, --yes`: Pula a confirmação interativa de destruição de dados.

## Backup

Por padrão, o backup vai para:

```text
artifacts/backups-local/<timestamp>
```

Exemplo com uploads RAG incluídos:

```bash
./scripts/backup-local.sh --include-rag-files
```

Exemplo incluindo também os blobs de modelo:

```bash
./scripts/backup-local.sh --include-rag-files --include-models
```

O backup gera:

- `db/postgres.dump`
- `config/config.env`
- `manifest.json`
- `checksums.sha256`

## Restore

O restore foi desenhado para funcionar em ambiente limpo:

```bash
./scripts/restore-local.sh artifacts/backups-local/20260507T120000
```

O script:

1. Valida checksums de todos os arquivos do backup.
2. Mostra um resumo do Manifest e pede confirmação (a menos que `-y` seja usado).
3. Sobe `postgres` e `redis` se necessário.
4. Valida compatibilidade de versão/schema.
5. Restaura o dump do Postgres.
6. Restaura uploads RAG e/ou modelos, se esses artefatos estiverem presentes no backup.

Dica: Use `--dry-run` primeiro para validar a integridade do backup sem riscos:

```bash
./scripts/restore-local.sh --dry-run artifacts/backups-local/20260507T120000
```

Se o diretório RAG de destino já estiver populado, o restore agora exige:

```bash
./scripts/restore-local.sh --force-rag-overwrite artifacts/backups-local/20260507T120000
```

Sem a flag, o script apenas registra um aviso e preserva o conteúdo existente.

## DR Test Local

O teste local executa o fluxo completo:

1. Sobe uma stack temporária isolada.
2. Cria cliente.
3. Cria API key.
4. Faz chamada de inferência.
5. Cria documento RAG, se RAG estiver habilitado.
6. Gera invoice local e registra payment.
7. Faz backup com uploads RAG incluídos.
8. Destrói a stack temporária.
9. Sobe um ambiente limpo.
10. Restaura o backup.
11. Valida cliente, API key, invoice e RAG após o restore.
12. Gera um relatório detalhado em `artifacts/dr-tests/<timestamp>/summary.txt`.

Executar:

```bash
./scripts/dr-test-local.sh
```

Para validação estrita de RAG:

```bash
RAG_INDEX_TIMEOUT_SECONDS=180 ./scripts/dr-test-local.sh --strict-rag
```

No modo padrão, se o documento RAG não indexar a tempo, o summary reporta:

- `RAG_INDEXING_STATUS=not_ready`
- `RAG_VALIDATION_MODE=persistence_only`
- `DR_RESULT=success_with_rag_warning`

No modo estrito, o timeout vira falha real:

- `RAG_INDEXING_STATUS=failed_timeout`
- `RAG_VALIDATION_MODE=strict`
- `DR_RESULT=failed`

## Observações

- O fluxo assume que a pasta `models/` continua disponível no host para o backend de inferência local.
- Se o host não tiver GPU ou o backend local de modelo não subir, a validação de inferência vai falhar.
- O arquivo `config/config.env` é um snapshot para auditoria; ele não é suficiente para reconstruir segredos.
