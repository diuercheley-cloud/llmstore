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

- `./scripts/backup/backup-local.sh`
- `./scripts/backup/restore-local.sh [OPÇÕES] <backup_dir>`
- `./scripts/dev/dr-test-local.sh [--strict-rag]`

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
./scripts/backup/backup-local.sh --include-rag-files
```

Exemplo incluindo também os blobs de modelo:

```bash
./scripts/backup/backup-local.sh --include-rag-files --include-models
```

O backup gera:

- `db/postgres.dump`
- `config/config.env`
- `manifest.json`
- `checksums.sha256`

## Restore

O restore foi desenhado para funcionar em ambiente limpo:

```bash
./scripts/backup/restore-local.sh artifacts/backups-local/20260507T120000
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
./scripts/backup/restore-local.sh --dry-run artifacts/backups-local/20260507T120000
```

Se o diretório RAG de destino já estiver populado, o restore agora exige:

```bash
./scripts/backup/restore-local.sh --force-rag-overwrite artifacts/backups-local/20260507T120000
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
./scripts/dev/dr-test-local.sh
```

Para validação estrita de RAG:

```bash
RAG_INDEX_TIMEOUT_SECONDS=180 ./scripts/dev/dr-test-local.sh --strict-rag
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

## Criptografia e Rotação de Chaves

O stack de disaster recovery exige configuração explícita de chaves criptográficas para garantir a segurança dos backups. Os fallbacks antigos para segredos compartilhados (`JWT_SECRET` / `ADMIN_TOKEN`) foram totalmente removidos.

### Chaves Necessárias

As seguintes variáveis de ambiente devem estar configuradas no ambiente de execução:

* **`BACKUP_ENCRYPTION_KEY`**: Chave de criptografia dos arquivos (mínimo de 32 caracteres).
* **`BACKUP_SIGNING_KEY`**: Chave secreta de assinatura HMAC (mínimo de 32 caracteres).
* **`BACKUP_KEY_ID`**: (Opcional) Identificador da chave. Se omitido, é derivado a partir do hash da chave de criptografia.

### Rotação de Chaves

Para efetuar a rotação de chaves:
1. Gere novas chaves criptográficas com pelo menos 32 caracteres.
2. Defina as novas chaves nas variáveis `BACKUP_ENCRYPTION_KEY` e `BACKUP_SIGNING_KEY`, opcionalmente configurando um novo `BACKUP_KEY_ID`.
3. Backups futuros utilizarão automaticamente a nova chave e registrarão o novo identificador no manifesto.

### Recuperação de Backups Antigos

Ao verificar ou restaurar um backup:
1. O manifesto do backup traz informações sobre qual `key_id` foi utilizado.
2. Caso o `key_id` atual no ambiente seja diferente do registrado no backup, um aviso de segurança é gerado nos logs e no relatório de verificação para prevenir erros operacionais.
3. Se a chave correspondente ao `key_id` do manifesto não estiver ativa no ambiente, o restore falhará na descriptografia. É necessário restabelecer temporariamente as chaves corretas para processar a restauração.

## Exclusão de Segredos e Recuperação em Produção (Vault / KMS / .env Externo)

Por motivos de segurança e conformidade, os arquivos `.env` e `.env.local` na raiz do repositório **são completamente excluídos do backup padrão**, e quaisquer chaves ou segredos em arquivos de configuração YAML/JSON são **redigidos** (substituídos por `"REDACTED"`) se corresponderem a chaves contendo `token`, `secret`, `password`, `key` ou `credential`.

Para restabelecer e restaurar as configurações sensíveis da stack após um restore de desastre:

### 1. Injeção dinâmica via Secret Manager (Recomendado)
Configure as credenciais e segredos em um gerenciador externo, como:
- HashiCorp Vault
- AWS Secrets Manager
- Google Secret Manager

Ao provisionar e subir o contêiner ou processo do control plane pós-restore, configure o entrypoint do contêiner para ler esses segredos do gerenciador e injetá-los diretamente no ambiente operacional do processo.

### 2. Restauração via Arquivo .env Externo Seguro
Caso não use um Secret Manager:
1. Mantenha uma cópia de segurança segura e criptografada do arquivo `.env` fora do repositório da stack.
2. Execute o restore normal do backup utilizando o script `./scripts/backup/restore-local.sh`.
3. Copie manualmente a cópia segura de volta para a raiz do stack restaurado:
   ```bash
   cp /caminho/seguro/para/backup.env /home/kleber/llm-inference-stack/.env
   ```
4. Reinicie os serviços da stack.

