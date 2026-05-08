# Production Readiness Local

Este relatório avalia se a stack está pronta para operar em `local-production` com base em evidências locais e artefatos reproduzíveis.

## Comando

Via Makefile:

```bash
make production-readiness
```

Via script:

```bash
./scripts/production-readiness-local.sh --base-url http://localhost:18080
```

## Opções

```bash
./scripts/production-readiness-local.sh --help
```

Parâmetros suportados:

- `--base-url http://localhost:18080`
- `--output-dir artifacts/production-readiness`
- `--json-only`
- `--strict`
- `--skip-heavy`

## Artefatos

Cada execução gera:

```text
artifacts/production-readiness/<timestamp>/
  report.md
  report.json
  logs/
```

Campos principais do `report.json`:

- `generated_at`
- `version`
- `git_branch`
- `git_commit`
- `git_status_clean`
- `base_url`
- `score`
- `totals`
- `checks`
- `artifacts`

## Categorias avaliadas

- Git/release
- Ambiente
- Serviços
- APIs
- SaaS
- RAG
- TTS
- Segurança
- DR
- Observabilidade
- Modelos

## Regras de score

- Qualquer `fail` com severidade `critical` resulta em `NOT_READY`.
- Falhas `high`, warnings ou falhas não críticas resultam em `READY_WITH_WARNINGS`.
- Apenas `pass`, com skips estritamente opcionais, resulta em `READY`.

## Fora do escopo

- PSP real
- PIX real
- DNS externo
- HTTPS obrigatório
- cloud obrigatória

## Notas operacionais

- O relatório não integra PSP real.
- O relatório não gera PIX real.
- O relatório não exige domínio público.
- O relatório não exige HTTPS.
- O relatório sanitiza logs para não persistir secrets em artifacts.
- Modelos locais, `.gguf`, `.env`, `.local/`, `data/rag_uploads/`, `backups/` e `exports/` devem permanecer fora do Git.
