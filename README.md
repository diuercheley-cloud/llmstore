# Local LLM Inference Stack for WSL2 and SaaS Packaging

Stack local e portátil para servir `unsloth/gemma-4-E4B-it-GGUF` com separação explícita entre control plane e data plane. O foco é simplicidade operacional, isolamento do runtime de inferência e defaults conservadores para uma NVIDIA RTX 4050 Laptop GPU com 6 GB de VRAM.

Na versão `1.0.0-beta`, o repositório também inclui a camada mínima para venda como SaaS: landing page, pricing, signup self-serve, geração automática de API key, plano free limitado, client portal e deploy com Caddy + HTTPS.

## Arquitetura

```text
Clientes externos
  |
  v
Control Plane (FastAPI)
  |- auth + API keys hashed
  |- admin API
  |- rate limit em Redis
  |- quotas e auditoria em PostgreSQL
  |- health/ready/metrics
  |- fila + timeout + circuit breaker
  |- proxy OpenAI-compatible
  |
  v
Data Plane interno (llama.cpp server)
  |- carrega GGUF
  |- executa inferência
  |- streaming SSE
  |- batching contínuo
  |- uso parcial GPU/CPU
```

### Separação de responsabilidades

- Control plane: autenticação, autorização, clientes, API keys, quotas, rate limit, logs, métricas, health, ready, histórico, registry de modelos, fila e políticas de proteção.
- Data plane: apenas inferência e lifecycle do modelo. Não fica exposto para clientes externos.

## Estrutura

- `control_plane/`: app FastAPI, models SQLAlchemy, Alembic, seed e serviços.
- `docker/`: Dockerfiles do control plane e data plane.
- `scripts/`: instalação, download do modelo, subida, teardown e testes.
- `models/`: volume dos arquivos GGUF.
- `monitoring/`: Prometheus e provisioning do Grafana.
- `docs/SALES.md`: fluxo comercial e onboarding self-serve.

## Superfície SaaS incluída

- Landing page pública em `/`
- Pricing público em `/pricing`
- Signup público em `/signup`
- Endpoint de onboarding em `POST /public/signup`
- Portal do cliente em `/client-portal`
- Deploy de produção em VPS via `scripts/deploy-vps.sh`

## Modelo e defaults para RTX 4050 6 GB

- Repositório obrigatório: `unsloth/gemma-4-E4B-it-GGUF`
- Default recomendado: `gemma-4-E4B-it-Q4_0.gguf`
- `LLAMA_N_GPU_LAYERS=20`
- `LLAMA_CTX_SIZE=2048`
- `MAX_CONCURRENT_GENERATIONS=1`
- `DEFAULT_MAX_TOKENS=512`
- `MAX_COMPLETION_TOKENS=1024`
- `REQUEST_TIMEOUT_SECONDS=180`
- `QUEUE_TIMEOUT_SECONDS=30`

Esses valores são conservadores. Dependendo do build do `llama.cpp`, do driver no WSL2 e do quant escolhido, pode ser necessário reduzir `LLAMA_N_GPU_LAYERS`, `LLAMA_CTX_SIZE` ou ambos.

## Instalação no WSL2

1. Verifique Docker e GPU:

```bash
./scripts/install-wsl-deps.sh
```

## Instalação como appliance local

O instalador principal configura o sistema completo para uso local, com validação de produção, relatórios de segurança e readiness.

```bash
# Recomendado: instalação completa com demo data
make install-local

# Ou execute o script diretamente com opções
./scripts/install-local-appliance.sh --with-demo --gpu
```

Opções suportadas:
- `--yes`: Pula confirmações.
- `--dry-run`: Apenas mostra o que seria feito.
- `--with-demo`: Carrega dados de exemplo.
- `--gpu`: Tenta configurar aceleração NVIDIA.
- `--base-url`: Define a URL pública (padrão: http://localhost:18080).

Após a instalação, um relatório detalhado é gerado em `artifacts/install-local-appliance/<timestamp>/`.

## Instalação para cliente final

Para clientes finais que desejam instalar o sistema sem se aprofundar na arquitetura interna, criamos um conjunto de documentos simplificados:
- [Guia de Requisitos do Sistema](docs/CUSTOMER_REQUIREMENTS.md)
- [Guia de Instalação](docs/CUSTOMER_INSTALL_GUIDE.md)
- [Quickstart (Caminho Curto)](docs/CUSTOMER_QUICKSTART.md)
- [Solução de Problemas (Troubleshooting)](docs/CUSTOMER_TROUBLESHOOTING.md)

## Escolha o arquivo de ambiente

```bash
vi .env.local
# ou vi .env.prod para a camada com reverse proxy
```

3. Ajuste no mínimo:

- `ADMIN_TOKEN`
- `POSTGRES_PASSWORD`
- `MODEL_FILE`
- `LLAMA_N_GPU_LAYERS`
- `LLAMA_CTX_SIZE`

Arquivos de ambiente:

- `.env.local`: defaults locais para validação e operação diária no WSL2.
- `.env.prod`: overlay para uso com `docker-compose.prod.yml`, proxy e TLS opcional.
- `.env.example`: referência neutra para novos ambientes.

## Verificar GPU no WSL2

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Se o segundo comando falhar, o runtime NVIDIA do Docker no WSL2 ainda não está funcional.

## Baixar o modelo

```bash
export HF_TOKEN=seu_token
./scripts/download-model.sh
```

O script salva em `./models/${MODEL_FILE}`.

## Subir o ambiente

Local:

```bash
./scripts/up.sh
```

Camada de produção local com reverse proxy:

```bash
STACK_MODE=prod ./scripts/up.sh
```

Serviços:

- Control plane: `http://localhost:18080`
- Dashboard admin local: `http://localhost:18080/admin-dashboard`
- Admin Lab (Testes & Financeiro): `http://localhost:18080/admin-lab`
- Client portal: `http://localhost:18080/client-portal`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Prometheus: `http://localhost:9090` se usar profile `observability`
- Grafana: `http://localhost:3001` se usar profile `observability`

Na camada `prod`, o acesso externo passa pelo Caddy com HTTPS automático:

- HTTP de validação ACME: `http://SEU_DOMINIO`
- HTTPS público: `https://SEU_DOMINIO`

## Rodando como produção local

Para uma experiência que simula o comportamento de produção (com interface amigável, landing page e portal completo) em `localhost:18080`:

1. Inicie a stack:
```bash
./scripts/local-production-up.sh
```

2. Valide as interfaces:
```bash
./scripts/ui-health.sh
```

3. Teste o fluxo completo (opcionalmente passe uma API Key):
```bash
./scripts/local-production-smoke.sh [API_KEY]
```

Documentação Adicional:
- [Guia Rápido (Quickstart)](docs/LOCAL_PRODUCTION_QUICKSTART.md)
- [Runbook de Produção Local](docs/LOCAL_PRODUCTION_RUNBOOK.md)
- [Guia de Validação](docs/LOCAL_PRODUCTION_VALIDATION.md)
- [Integrações (Open WebUI, n8n, LangChain, etc.)](docs/integrations/LANGCHAIN.md)

Acesse:
- Landing Page: http://localhost:18080/
- Portal do Cliente: http://localhost:18080/client-portal
- Admin Dashboard: http://localhost:18080/admin-dashboard
- Matriz de Capacidades: [docs/CAPABILITY_MATRIX.md](docs/CAPABILITY_MATRIX.md)

## Demonstração Local

Para demonstrações do produto em ambiente local (offline, notebooks, reuniões com clientes):

- [Guia de Configuração da Demo](docs/LOCAL_DEMO_GUIDE.md): Como preparar o ambiente e carregar dados.
- [Roteiro de Apresentação](docs/LOCAL_DEMO_SCRIPT.md): Sequência sugerida para a demo comercial/técnica.
- [FAQ da Demo Local](docs/LOCAL_DEMO_FAQ.md): Perguntas frequentes sobre o uso local e privacidade.

## Health, readiness e conectividade

```bash
./scripts/test-health.sh
```

Readiness falha se PostgreSQL, Redis ou data plane estiverem indisponíveis.

Health profundo protegido por admin token:

```bash
curl -fsS http://localhost:18080/admin/health/deep \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool
```

## Seed inicial

Na primeira subida, o control plane cria:

- cliente demo `demo-client`
- API key demo `demo-default`

A API key demo não é exposta em logs. Para emitir uma nova chave via Admin API:

```bash
DEMO_CLIENT_ID="$(curl -fsS http://localhost:18080/admin/clients \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c '
import json, sys
for item in json.load(sys.stdin):
    if item["name"] == "demo-client":
        print(item["id"])
        break
')"

curl -fsS http://localhost:18080/admin/api-keys \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${DEMO_CLIENT_ID}\",\"name\":\"manual-demo\"}" | python3 -m json.tool
```

## Admin API

Header obrigatório:

```text
X-Admin-Token: seu ADMIN_TOKEN
```

## Gerenciamento de modelos pelo Admin Lab

O Admin Lab em `/admin-lab`, aba `Modelos`, agora expõe gestão operacional de modelos sem depender de shell Linux para o fluxo normal de registro:

- listar modelos com alias, arquivo GGUF, arquitetura detectada, backend, status, default, rotas, contexto e template
- listar arquivos disponíveis em `/models`
- adicionar ou editar modelo pela UI
- associar backend existente ou registrar novo backend HTTP
- habilitar, desabilitar e trocar o modelo default
- testar prompt por modelo
- remover modelo com segurança sem apagar o arquivo GGUF
- consultar health, status de backend e logs recentes

Fluxo recomendado:

1. copie o arquivo `.gguf` para `./models` no host; dentro do data plane ele aparece em `/models`
2. abra `http://localhost:18080/admin-lab`
3. entre em `Modelos` e use `Adicionar modelo`
4. selecione o arquivo GGUF detectado, alias, backend e template
5. salve e valide com `Testar prompt`

Regras importantes:

- `llama.cpp` aceita apenas arquivo `.gguf` dentro de `/models`
- o Admin Lab bloqueia alias e `model_id` duplicados
- a remoção pela UI nunca apaga o arquivo GGUF
- remoção de modelo default é bloqueada
- modelos com histórico podem ser arquivados por soft delete para preservar auditoria

Limitações desta versão:

- a UI não cria serviços Docker arbitrários
- para novos containers, use um serviço já definido em `docker-compose.yml` ou cadastre um backend HTTP existente
- ações `start/stop/restart/logs` de backend só funcionam quando `TEST_TOOLS_ENABLED=true` e `PUBLIC_EXPOSURE=false`

Criar cliente:

```bash
curl -fsS http://localhost:18080/admin/clients \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "client-a",
    "description": "tenant local",
    "rate_limit_per_minute": 5,
    "daily_token_quota": 20000,
    "monthly_token_quota": 300000,
    "max_context_tokens": 4096,
    "max_output_tokens": 1024
  }'
```

Gerar API key:

```bash
curl -fsS http://localhost:18080/admin/api-keys \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "UUID_DO_CLIENTE",
    "name": "default"
  }'
```

Rotacionar API key existente:

```bash
curl -fsS -X POST http://localhost:18080/admin/api-keys/UUID_DA_KEY/rotate \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool
```

O endpoint devolve a nova chave em plaintext apenas na resposta de rotação. `GET /admin/api-keys` expõe apenas `key_prefix`.

Consultar uso, requests e health profundo:

```bash
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/usage | python3 -m json.tool
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/usage/summary | python3 -m json.tool
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/requests | python3 -m json.tool
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/api-keys | python3 -m json.tool
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/health/deep | python3 -m json.tool
```

Bloquear e desbloquear cliente:

```bash
curl -fsS -X POST http://localhost:18080/admin/clients/UUID_DO_CLIENTE/block \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool

curl -fsS -X POST http://localhost:18080/admin/clients/UUID_DO_CLIENTE/unblock \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool
```

Criar cliente e chave com script:

```bash
./scripts/create-client.sh cliente-real "tenant de teste"
./scripts/create-customer-demo.sh cliente-portal-demo "cliente demo do portal" basic
./scripts/set-client-plan.sh UUID_DO_CLIENTE basic
./scripts/create-plan.sh premium-local "Premium Local" 20 100000 1000000 1024 true "plano custom"
./scripts/generate-invoices.sh
./scripts/mark-invoice-paid.sh UUID_DA_FATURA local-ref-001
```

Cache de respostas:

- `RESPONSE_CACHE_ENABLED=true`: habilita cache exato para requests sem stream.
- `RESPONSE_CACHE_TTL_SECONDS=3600`: TTL padrão do cache exato.
- `SEMANTIC_CACHE_ENABLED=false`: reservado para embeddings futuramente; permanece desligado por padrão.
- O cache nunca guarda `stream=true` nem respostas com erro.
- `request_logs.cache_hit` indica quando a resposta foi servida do cache.

Operação de cache:

```bash
./scripts/cache-stats.sh
./scripts/cache-clear.sh
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/cache/stats | python3 -m json.tool
curl -fsS -X DELETE -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/cache/responses | python3 -m json.tool
```

Billing local/manual:

- `GET /admin/billing/invoices/preview`: previsão agregada do mês corrente.
- `POST /admin/billing/invoices/generate`: materializa invoices reais no banco.
- `GET /admin/billing/invoices`: lista invoices e pagamentos registrados.
- `PATCH /admin/billing/invoices/{id}/mark-paid`: confirma pagamento manual/local.
- `PATCH /admin/billing/invoices/{id}/cancel`: cancela invoice aberta.
- `billing_status` do cliente:
  - `active`: operação normal
  - `past_due`: existe invoice vencida
  - `suspended`: acesso do cliente bloqueado na API

Fluxo diário recomendado:

```bash
./scripts/invoice-preview.sh
./scripts/generate-invoices.sh
./scripts/run-billing-cycle.sh
curl -fsS http://localhost:18080/admin/billing/invoices -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool
./scripts/mark-invoice-paid.sh UUID_DA_FATURA local-ref-001
```

Ciclo mensal automático:

- `BILLING_INVOICE_DAY=1`: dia do mês em que o ciclo tenta gerar invoices.
- `BILLING_DUE_DAYS=7`: vencimento contado a partir da geração.
- `BILLING_SUSPEND_AFTER_DAYS=15`: após esse atraso, cliente muda para `suspended`.
- O scheduler interno roda no control plane e também pode ser acionado manualmente:

```bash
./scripts/run-billing-cycle.sh
curl -fsS http://localhost:18080/admin/billing/run-cycle \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -X POST | python3 -m json.tool
```

Transições automáticas:

- invoice `pending` vencida vira `overdue`
- cliente com invoice vencida vira `past_due`
- cliente acima do atraso configurado vira `suspended`
- após `mark-paid`, o cliente volta para `active` se não houver outras invoices vencidas

## API compatível com OpenAI

Header obrigatório:

```text
Authorization: Bearer API_KEY
```

Listar modelos:

```bash
curl -fsS http://localhost:18080/v1/models \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool
```

Chat completion:

```bash
./scripts/test-chat.sh
```

Streaming SSE:

```bash
./scripts/test-stream.sh
```

Exemplo `curl` direto:

```bash
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Explique WSL2 em 3 linhas."}],
    "temperature": 0.7,
    "top_p": 0.95,
    "max_tokens": 256,
    "stream": true,
    "include_reasoning": false
  }'
```

`include_reasoning` é opcional e `false` por padrão. Quando não for enviado, o control plane remove `reasoning_content` e entrega a resposta em formato compatível com OpenAI. Se você precisar desse campo para debug local, envie `include_reasoning: true`.

Teste rápido com chave de cliente real:

```bash
API_KEY=sk-local-... ./scripts/smoke-client.sh
```

## Dashboard Admin

Interface local simples:

```text
http://localhost:18080/admin-dashboard
```

O HTML é servido pelo control plane e usa `X-Admin-Token` no navegador para consultar:

- clientes
- chaves
- plano do cliente
- uso agregado
- consumo diário e mensal
- limite restante
- erros recentes
- latência
- status do modelo
- health profundo

## Observabilidade

Métricas:

```bash
curl -fsS http://localhost:18080/metrics
```

## Operação diária

Subir e validar:

```bash
./scripts/up.sh
./scripts/validate-e2e.sh
```

Criar cliente:

```bash
./scripts/create-client.sh cliente-a "cliente operacional"
```

Testar uma chave real:

```bash
API_KEY=sk-local-... ./scripts/smoke-client.sh
```

Inspecionar uso:

```bash
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/usage/summary | python3 -m json.tool
```

Inspecionar requests recentes:

```bash
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/requests | python3 -m json.tool
```

Bloquear um cliente:

```bash
curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  http://localhost:18080/admin/clients/UUID_DO_CLIENTE/block | python3 -m json.tool
```

Seguir logs:

```bash
docker compose --env-file .env.local logs -f control-plane
docker compose --env-file .env.local logs -f data-plane-gemma
```

Subir com Prometheus e Grafana:

```bash
docker compose --profile observability up -d
```

Backup e restore:

```bash
./scripts/backup.sh
./scripts/restore.sh /caminho/para/postgres.dump
```

Camada de produção local:

```bash
STACK_MODE=prod ./scripts/up.sh
STACK_MODE=prod ./scripts/backup.sh
STACK_MODE=prod ./scripts/down.sh
```

## Fluxo comercial

1. Criar ou ajustar o plano:

```bash
./scripts/create-plan.sh startup-local "Startup Local" 12 60000 600000 768 true "plano comercial inicial"
```

2. Criar o cliente:

```bash
./scripts/create-client.sh cliente-acme "tenant comercial ACME"
```

3. Gerar e entregar a API key:

```bash
curl -fsS http://localhost:18080/admin/api-keys \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"UUID_DO_CLIENTE","name":"acme-default"}' | python3 -m json.tool
```

4. Cliente acessa o portal público:

```text
http://localhost:18080/client-portal
```

O portal usa apenas a API key do cliente em `Authorization: Bearer ...`. O `ADMIN_TOKEN` nunca deve ser exposto nele.

5. Cliente usa a API OpenAI-compatible:

```bash
curl -fsS http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY_DO_CLIENTE}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Responda em uma frase curta: o ambiente está pronto?"}],
    "max_tokens": 96,
    "stream": false,
    "include_reasoning": false
  }' | python3 -m json.tool
```

Atalho para provisionar demo comercial já com plano, API key e URL do portal:

```bash
./scripts/create-customer-demo.sh cliente-demo "cliente piloto" basic
```

Deploy publico com Caddy:

```bash
export SERVER_NAME=api.seudominio.com
export LETSENCRYPT_EMAIL=ops@seudominio.com
sudo ./scripts/deploy-vps.sh
```

## Validação recomendada

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r control_plane/requirements.txt
PYTHONPATH=control_plane pytest -q tests
PYTHONPATH=control_plane ruff check control_plane/app tests
docker compose config
./scripts/up.sh
./scripts/validate-e2e.sh
```

## Troubleshooting RTX 4050 6 GB

- Se houver OOM na GPU: reduza `LLAMA_N_GPU_LAYERS` para `12`, `8` ou `0`.
- Se ainda falhar: reduza `LLAMA_CTX_SIZE` para `3072` ou `2048`.
- Se houver swap ou latência alta: mantenha `MAX_CONCURRENT_GENERATIONS=1`.
- Se a VRAM não comportar o Q4 desejado: use uma quantização menor disponível no repositório.
- Não assuma 100% do modelo em VRAM no WSL2; o projeto já aceita fallback CPU/GPU parcial via `--n-gpu-layers`.

## Troubleshooting Docker + NVIDIA no WSL2

- Verifique se o Docker Desktop está com integração WSL2 habilitada.
- Confirme `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`.
- Se `deploy.resources` não for honrado pelo seu Compose, use Docker Desktop recente com suporte a GPU ou ajuste para runtime NVIDIA conforme sua instalação.
- Se usar `STACK_MODE=prod`, confirme que apenas o reverse proxy está exposto externamente.

## Gestão de Contexto e Otimização

O sistema inclui uma camada de gestão de contexto para garantir a qualidade das respostas e evitar que o modelo perca o foco, especialmente em modelos locais menores.

### Configurações de Otimização

As seguintes variáveis de ambiente (em `.env`) controlam os limites automáticos:

- `INFERENCE_MAX_CONTEXT_TOKENS`: Limite máximo de tokens de contexto (default: 4096).
- `INFERENCE_MAX_COMPLETION_TOKENS`: Limite para tokens de resposta e teto (cap) para requests (default: 512).
- `INFERENCE_MAX_SYSTEM_CHARS`: Tamanho máximo do system prompt (default: 2500).
- `INFERENCE_MAX_HISTORY_MESSAGES`: Número máximo de mensagens do histórico preservadas (default: 8).

### Comportamento Automático

- **Consolidação de System Prompt:** Múltiplas mensagens de sistema são unificadas e truncadas se necessário.
- **Truncamento Inteligente:** Preserva sempre a mensagem de sistema e a última pergunta do usuário, descartando histórico intermediário antigo.
- **Capping de max_tokens:** Requests com `max_tokens` excessivo são capadas automaticamente para o limite de segurança.
- **Defaults Estáveis:** Aplica `temperature: 0.4` e `top_p: 0.9` para modelos locais (`llama.cpp`, `ollama`) se não especificados na request.

## Limitações conhecidas

- `POST /admin/models/reload` atualiza o registry e revalida o data plane, mas troca física de modelo ainda exige reiniciar o container do data plane.
- O cálculo de tokens é estimado, não usa tokenizer oficial.
- Cancelamento de geração depende do encerramento da conexão HTTP do stream; não há endpoint explícito de cancel no `llama.cpp`.

## Próximos passos para produção

- Adicionar autenticação administrativa com usuários, RBAC e rotação de credenciais.
- Persistir configuração dinâmica em tabela dedicada com cache invalidation.
- Implementar fila distribuída e workers externos para múltiplos data planes.
- Adicionar tokenizer real para contabilidade de tokens.
- Adicionar autenticação administrativa com usuários, RBAC e rotação de credenciais.
- Persistir configuração dinâmica em tabela dedicada com cache invalidation.
- Implementar fila distribuída e workers externos para múltiplos data planes.
- Adicionar tokenizer real para contabilidade de tokens.
- Incluir tracing distribuído e retenção externa de métricas/logs.
# llmstore

## Pocket TTS (Text-to-Speech)

O sistema inclui integração com o `pocket-tts` para geração de áudio local.

- **Endpoint de Saúde:** `GET http://localhost:18080/pocket-tts/health`
- **Endpoint de Geração:** `POST http://localhost:18080/pocket-tts/tts`

Exemplo de uso:
```bash
./scripts/pocket-tts.sh generate "Olá, esta é uma mensagem de voz do sistema."
```
