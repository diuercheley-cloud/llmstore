# Local Production Runbook

Este documento descreve como operar o sistema `llm-inference-stack` em ambiente local (`localhost`) com todas as funcionalidades da camada SaaS habilitadas. Para setup automatizado numa máquina nova, veja o [First Run Local](./FIRST_RUN_LOCAL.md).

## 1. Visão Geral

O modo `local-production` simula o comportamento de um ambiente de produção completo, incluindo landing page, pricing, portal do cliente e admin dashboard, mas rodando inteiramente na sua máquina.

- **Base URL padrão:** `http://localhost:18080`
- **Escopo:**
    - Autenticação e API Keys
    - Gestão de Clientes e Planos
    - Inferência de LLM (OpenAI-compatible)
    - RAG Local (Upload e Query)
    - Billing Manual (Simulação de faturas e pagamentos)
    - Observabilidade (Métricas e Dashboards)
- **Fora de Escopo:**
    - Gateway de pagamento real (PSP)
    - Sem PIX real nesta versão (apenas simulação manual)
    - Domínio público (acesso apenas via localhost)
    - HTTPS obrigatório (uso de HTTP em localhost)

## 2. Pré-requisitos

Certifique-se de ter as seguintes ferramentas instaladas:

- **Docker & Docker Compose:** Recomendado Docker Desktop com integração WSL2 no Windows.
- **Python 3.10+:** Com `venv` para scripts auxiliares e testes.
- **Ferramentas de CLI:** `curl`, `jq`, `git`, `make`.
- **WSL2 (Windows):** Necessário para melhor performance de GPU.

## 3. Como Subir o Sistema

### Via Scripts (Recomendado)
Para subir a stack otimizada para produção local:
```bash
./scripts/local-production-up.sh
```

### Via Makefile
```bash
make up
```

### Via Docker Compose
```bash
docker compose up -d --build
```

## 4. Como Validar o Sistema

Para garantir que todos os serviços estão operando corretamente, execute a suíte de validação completa:

### Via Makefile
```bash
make validate-local-production
make validate-runtime-health
make production-readiness
```

### Via Script
```bash
./scripts/validate-local-production-full.sh
./scripts/validate-runtime-health-local.sh
./scripts/production-readiness-local.sh
./scripts/post-upgrade-smoke-local.sh
```

### Benchmark de Modelos Real
Para medir a performance real de modelos e obter recomendações de planos (Free/Basic/Premium), utilize a ferramenta de benchmark aprimorada:
```bash
make benchmark-quick
# ou modo padrão
./scripts/benchmark-model-local.sh --model "gemma-2b" --standard
# ou modo stress (requer confirmação)
./scripts/benchmark-model-local.sh --model "gemma-2b" --stress
```
Os resultados incluem TTFT P95, Latência P95, métricas de sistema (GPU/CPU/RAM) e são expostos via Admin API (`/admin/benchmarks`).
Para mais detalhes, consulte o [Documento de Benchmark Local](./MODEL_BENCHMARK_LOCAL.md).

O relatório de readiness gera artefatos em:

```text
artifacts/production-readiness/<timestamp>/
  report.md
  report.json
  logs/
```

O score final do relatório é um destes valores:

- `READY`
- `READY_WITH_WARNINGS`
- `NOT_READY`

## 5. URLs Principais

### API e Status
- **Health Check:** `http://localhost:18080/health`
- **Ready Check:** `http://localhost:18080/ready`
- **Status Geral:** `http://localhost:18080/status`
- **Runtime Summary:** `http://localhost:18080/admin/runtime/summary` (Requer token admin)
- **Latest Readiness:** `http://localhost:18080/admin/readiness/latest` (Requer token admin)
- **Latest Security:** `http://localhost:18080/admin/security/latest` (Requer token admin)
- **Deep Health Check:** `http://localhost:18080/admin/health/deep` (Requer token admin)
- **Métricas (Prometheus):** `http://localhost:18080/metrics`

### Interfaces (UIs)
- **Landing Page:** `http://localhost:18080/`
- **Portal do Cliente:** `http://localhost:18080/client-portal`
- **Admin Dashboard:** `http://localhost:18080/admin-dashboard` (Inclui cards de Runtime/Readiness/Security)
- **Admin Lab (Gestão Operacional):** `http://localhost:18080/admin-lab`

### Chat Completions
- **Listar Modelos:** `GET http://localhost:18080/v1/models`
- **Chat Completions:** `POST http://localhost:18080/v1/chat/completions`
- **Responses (Simplificado):** `POST http://localhost:18080/v1/responses`

Exemplo básico de `responses`:
```bash
curl -X POST http://localhost:18080/v1/responses \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "instructions": "Seja direto.",
    "input": "Responda apenas OK."
  }'
```

### Embeddings (Novo v1.6.0)
- **Gerar Embeddings:** `POST http://localhost:18080/v1/embeddings`
- **Exemplo de uso:**
```bash
curl -X POST http://localhost:18080/v1/embeddings \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": "test string"
  }'
```

## 6. Como Criar Cliente Local

### Via Script
Use o script auxiliar para criar um cliente e já associá-lo a um plano:
```bash
./scripts/create-customer-demo.sh nome-do-cliente "Descrição do Cliente" free
```

### Via Admin API
```bash
curl -fsS http://localhost:18080/admin/clients \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cliente-x",
    "description": "novo cliente local",
    "rate_limit_per_minute": 10
  }'
```

## 7. Como Criar API Key Local

### Via Admin API
1. Obtenha o `client_id` do cliente criado.
2. Gere a chave:
```bash
curl -fsS http://localhost:18080/admin/api-keys \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"UUID_DO_CLIENTE","name":"minha-chave"}'
```
**Atenção:** A API Key é exibida apenas uma vez em texto claro. **Nunca commite API Keys no repositório.**

## 8. Como Testar Chat

### Teste Simples (Sem Stream)
```bash
curl -X POST http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Olá, quem é você?"}]
  }'
```

### Teste de Streaming
```bash
./scripts/test-stream.sh
```
Ou via curl:
```bash
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Conte uma piada longa."}],
    "stream": true
  }'
```

### Teste de Responses
```bash
./scripts/validate-responses-api-local.sh
```

Notas do endpoint `/v1/responses` nesta versão:
- Suporta `input` string e array textual simples.
- `instructions` vira mensagem `system`.
- `tools`, `tool_choice` e `stream: true` retornam `501` estruturado nesta fase.

## 9. Como usar LM Studio

O sistema pode atuar como um proxy para o LM Studio se você quiser usar outros modelos localmente.

1. Configure o LM Studio para ouvir em `0.0.0.0`.
2. No `.env.local`, defina:
   `LM_STUDIO_BASE_URL=http://192.168.101.1:1234/v1` (ajuste o IP do host).
3. Reinicie a stack.
4. Valide a conexão:
   ```bash
   ./scripts/test-lmstudio.sh
   ```
**Comportamento Offline:** Se o LM Studio estiver offline, as requisições para backends roteados para ele falharão com 503 Service Unavailable.

## 10. Como Usar RAG Local

### Upload de Documento
```bash
curl -X POST http://localhost:18080/v1/rag/files \
  -H "Authorization: Bearer ${API_KEY}" \
  -F "file=@meu_documento.pdf"
```

### Consultar (Query)
```bash
curl -X POST http://localhost:18080/v1/rag/query \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "O que o documento diz sobre X?",
    "file_ids": ["UUID_DO_ARQUIVO"]
  }'
```

### Limpeza Segura
O isolamento por cliente garante que um cliente não veja os dados de outro. Para apagar tudo:
```bash
docker compose down -v
```

## 11. Como Usar Billing Local/Manual

Como não há PSP real, o fluxo de faturamento é manual.

1. **Gerar Invoice:** `./scripts/generate-invoices.sh`
2. **Simular Overdue:** As faturas vencem automaticamente após `BILLING_DUE_DAYS`.
3. **Suspender Cliente:** `./scripts/suspend-client.sh UUID_DO_CLIENTE`
4. **Marcar como Pago:** `./scripts/mark-invoice-paid.sh UUID_DA_FATURA ref-pagamento`
5. **Desbloquear Cliente:** `./scripts/unsuspend-client.sh UUID_DO_CLIENTE`

## 12. Como Acessar Logs

### Todos os serviços
```bash
docker compose logs -f
```

### Serviço específico
```bash
docker compose logs -f control-plane
docker compose logs -f data-plane-gemma
```

### Artefatos de Validação
Após rodar `validate-local-production-full.sh`, os logs detalhados ficam em:
`artifacts/local-production-validation/<timestamp>/`

Após rodar `production-readiness-local.sh`, o relatório operacional fica em:
`artifacts/production-readiness/<timestamp>/`

## 13. Backup e Restore

### Backup
Gera um dump do banco de dados e salva o estado atual:
```bash
./scripts/backup-local.sh
```

### Restore
Restaura o banco a partir de um dump:
```bash
./scripts/restore-local.sh artifacts/backups/postgres_latest.dump
```

## 14. Como Criar Release Local

Para gerar um manifesto da versão atual para deploy:
```bash
./scripts/release-local-production.sh
```
Isso gerará os arquivos em `releases/v<VERSION>/`.

## 15. Como Criar Bundle de Release Distribuível

Para gerar um arquivo `.tar.gz` seguro (sem secrets ou modelos) para instalar em outra máquina:

```bash
make release-bundle
```

Isso gerará:
- `releases/v<VERSION>/llm-inference-stack-v<VERSION>.tar.gz`
- `releases/v<VERSION>/bundle-manifest.json`
- `releases/v<VERSION>/bundle-checksums.sha256`

Para validar a integridade e segurança do bundle:
```bash
./scripts/validate-release-bundle.sh
```

Consulte [docs/RELEASE_BUNDLE_LOCAL.md](RELEASE_BUNDLE_LOCAL.md) para detalhes.

## 16. Exportação, Deleção e Anonimização de Tenant

Para suporte, auditoria ou offboarding de clientes:

### Exportação Segura
Gera um snapshot dos metadados, faturas e arquivos do cliente.
```bash
./scripts/export-client-local.sh --client-id UUID --include-rag-files --include-tts-files
```

### Deleção e Purge
Remove dados do banco e limpa arquivos físicos com confirmação forte.
```bash
./scripts/delete-client-local.sh --client-id UUID --delete-rag-files --delete-tts-files
```

### Anonimização (GDPR/LGPD-like)
Mantém registros financeiros mas remove PII.
```bash
./scripts/delete-client-local.sh --client-id UUID --anonymize-instead
```

Consulte [docs/TENANT_EXPORT_DELETE_LOCAL.md](TENANT_EXPORT_DELETE_LOCAL.md) para detalhes completos.

## 15. Governança e Cotas de TTS Local

O serviço de TTS (Text-to-Speech) é monitorado e limitado por plano:

- **Monitoramento:** Use o Admin Dashboard para visualizar `total_tts_chars_month` e `usage_by_client`.
- **Cotas:** Clientes que excederem o limite de caracteres receberão `429 Too Many Requests`.
- **Isolamento:** Cada áudio gerado é vinculado ao `client_id` e auditado no banco de dados.
- **Retenção:** Os arquivos `.wav` são removidos conforme a política de `tts_audio_retention_days`.

## 17. Upgrade e Rollback Local

Para manter a stack atualizada ou reverter para uma versão estável em caso de falha:

### Upgrade
```bash
# Simular primeiro
./scripts/upgrade-local.sh --to-version v1.5.6 --dry-run
# Executar de verdade (faz backup automático)
./scripts/upgrade-local.sh --to-version v1.5.6
```

### Rollback
Exige o ID do backup gerado durante o upgrade (ou manualmente).
```bash
./scripts/rollback-local.sh --to-version v1.5.5 --backup-id artifacts/backups-local/20260509T120000
```

Consulte [docs/UPGRADE_ROLLBACK_LOCAL.md](UPGRADE_ROLLBACK_LOCAL.md) para detalhes completos e garantias de segurança.

## 18. Troubleshooting

| Problema | Causa Provável | Solução |
| :--- | :--- | :--- |
| Porta 18080 ocupada | Outro processo usando a porta | `lsof -i :18080` e mate o processo ou mude `HOST_PORT` no `.env` |
| Redis/Postgres Offline | Erro no startup do Docker | `docker compose logs redis` ou `postgres` |
| LM Studio Offline | LM Studio não iniciado no host | Inicie o LM Studio e verifique o IP/Porta |
| Modelo Offline | Data plane não carregou GGUF | Verifique `MODEL_FILE` e `docker compose logs data-plane-gemma` |
| Erro 401 | API Key inválida ou ausente | Verifique o header `Authorization: Bearer sk-...` |
| Erro 402/403 | Cliente suspenso/inadimplente | Verifique o `billing_status` no Admin Dashboard e pague a fatura |
| RAG não indexa | Worker offline ou PDF corrompido | Verifique `docker compose logs control-plane-worker` |
| Admin Lab vazio | Falha na comunicação com API | Verifique o console do navegador e o `ADMIN_TOKEN` |

## 16. Limpeza e Retenção de Dados Locais

O sistema acumula logs, artefatos de validação, áudios TTS e uploads RAG. Para manter o ambiente limpo e otimizado, utilize a política de retenção local.

### Política Geral (Recomendado)
Use o script central de retenção para aplicar todas as regras de limpeza segura:

```bash
# Simular limpeza (Dry Run)
./scripts/retention-local.sh --dry-run --section all

# Executar limpeza de logs e artefatos antigos
./scripts/retention-local.sh --yes --section all
```

Consulte [docs/RETENTION_LOCAL.md](RETENTION_LOCAL.md) para detalhes sobre as regras e proteções.

### Limpeza Específica de RAG
Se precisar de controle granular sobre apenas os dados RAG:
```bash
./scripts/clean-rag-local-data.sh --older-than-days 7 --yes
```

**Importante:** Ambos os scripts protegem automaticamente diretórios críticos como `models/`, `scripts/`, `docs/` e arquivos `.gguf`.
