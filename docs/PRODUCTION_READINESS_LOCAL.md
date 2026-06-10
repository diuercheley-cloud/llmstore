---
owner: platform-ops
status: consolidated
---

# Production Readiness Local

Este relatório avalia se a stack está pronta para operar em `local-production` com base em evidências locais e artefatos reproduzíveis.

## Comando

Via Makefile:

```bash
make production-readiness
```

Via script:

```bash
./scripts/dev/production-readiness-local.sh --base-url http://localhost:18080
```

## Opções

```bash
./scripts/dev/production-readiness-local.sh --help
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

O último relatório gerado pode ser visualizado diretamente no **Admin Dashboard** através do card "Production Readiness" ou via API:
- `GET /admin/readiness/latest`

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
- APIs (incluindo `/admin/health/deep`)
- SaaS
- RAG
- TTS
- Segurança
- DR
- Observabilidade
- Modelos

## Probe Rate Limit

O readiness local utiliza uma prova segura de rate limit que não estressa o ambiente:

- O probe usa o script dedicado: `./scripts/validators/validate-rate-limit-readiness-local.sh`.
- Cria um plano temporário `readiness-rate-limit-test` com limite estrito de **2 RPM**.
- Cria um cliente temporário associado a este plano e uma API key.
- Executa 4 requisições leves (ex: `/portal/me`).
- Valida se pelo menos uma requisição retornou `429 Too Many Requests`.
- Garante que o sistema permanece saudável (`/health` OK) após o estouro do limite.
- Limpa o cliente temporário ao final.
- Se Redis ou Rate Limit estiverem desabilitados, o check falha com orientação para ajuste de infraestrutura.

Validação dedicada:

```bash
./scripts/validators/validate-rate-limit-readiness-local.sh
```

## Probe TTS

O readiness local agora trata TTS como capacidade opcional:

- Se `TTS_ENABLED=false`, o check `tts_generate_wav` fica em `SKIP` com `optional=true`.
- Se `TTS_ENABLED=true`, o probe usa um cliente temporário de readiness com plano `tts_enabled=true`, API key Bearer válida e input curto.
- O endpoint validado é `POST /pocket-tts/tts`.
- O uso gerado é conferido via `GET /admin/usage/{client_id}/summary` e também aparece em `GET /portal/usage` e `GET /portal/usage-stats`.
- Respostas `401`, `402` e `403` recebem remediação específica no relatório, sem warning genérico.
- O arquivo de áudio temporário é apagado ao fim da validação e `.wav` continua fora do Git.

Validação dedicada:

```bash
./scripts/validators/validate-tts-readiness-local.sh
```

## Validação de Modelos

O relatório de prontidão utiliza o endpoint `/v1/models` para identificar modelos utilizáveis e executa probes dedicados via `scripts/validators/validate-chat-sse-readiness-local.sh`.

- **Modelo de Chat**: Exige `capabilities.chat == true`.
- **Status de Prontidão**: Considera `local_ready` (ambiente local) ou `production_ready` (produção).
- **Fallback Mock**: Se `MOCK_BACKEND_ENABLED=true`, modelos podem ser considerados `local_ready` mesmo sem backend real online.
- **Probe de Chat (Non-streaming)**: Valida se o modelo responde "OK" (ou similar) em tempo hábil.
- **Probe SSE (Streaming)**:
    - Se o modelo reporta `capabilities.streaming == true`, o probe é **obrigatório**.
    - Se falhar, emite um `FAIL` (high/critical dependendo do contexto).
    - Se o modelo não reporta suporte a streaming, o probe é classificado como `SKIP` (justificado), sem impacto no score.
    - A validação SSE agora utiliza um parser real para garantir que chunks `data:` sejam recebidos e o stream termine corretamente com `[DONE]`.

Se nenhum modelo de chat for encontrado ou se o probe de `/v1/chat/completions` falhar, o relatório emitirá um `WARN` ou `FAIL` com orientações de remediação claras.


## Score Rules

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
- O readiness não exige TTS quando o recurso estiver desabilitado no ambiente.
- Modelos locais, `.gguf`, `.env`, `.local/`, `data/rag_uploads/`, `backups/` e `exports/` devem permanecer fora do Git.
