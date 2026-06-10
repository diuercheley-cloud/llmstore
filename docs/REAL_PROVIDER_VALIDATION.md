---
owner: platform-ops
status: consolidated
---

# Real Provider Validation — v1.8.1

## Visão Geral

A validação de **providers reais** (OpenAI, DeepSeek, Anthropic) permite testar
chaves e conectividade com provedores cloud reais, com segurança e controle de
custos.

Toda chamada de saída para um provider real é **opt-in** e protegida por:

- `REAL_PROVIDER_VALIDATION_ENABLED=true` — gatekeeper global
- `*_PROVIDER_ENABLED=true` — gatekeeper por provider
- `REAL_PROVIDER_MAX_COST_BRL` — limite de custo por requisição
- `REAL_PROVIDER_TIMEOUT_SECONDS` — timeout de rede

Nenhum provider real é obrigatório. O sistema funciona 100% local sem nenhuma
chave de API.

---

## Como Configurar `.env.local`

1. Copie o template:

```bash
cp .env.example .env.local
```

2. Edite `.env.local` com suas chaves reais:

```env
# Habilita validação real (gatekeeper global)
REAL_PROVIDER_VALIDATION_ENABLED=true

# Limite de custo por requisição (BRL)
REAL_PROVIDER_MAX_COST_BRL=2.00

# OpenAI
OPENAI_PROVIDER_ENABLED=true
OPENAI_API_KEY=sk-proj-xxxxx...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_MODEL=gpt-4o-mini

# DeepSeek
DEEPSEEK_PROVIDER_ENABLED=true
DEEPSEEK_API_KEY=sk-xxxxx...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_MODEL=deepseek-chat

# Anthropic
ANTHROPIC_PROVIDER_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-xxxxx...
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

3. Proteja o arquivo:

```bash
chmod 600 .env.local
```

---

## Como Habilitar Provider Individualmente

Cada provider tem uma chave `*_PROVIDER_ENABLED` independente:

| Provider   | Variável                    | Chave                |
|------------|-----------------------------|----------------------|
| OpenAI     | `OPENAI_PROVIDER_ENABLED`   | `OPENAI_API_KEY`     |
| DeepSeek   | `DEEPSEEK_PROVIDER_ENABLED` | `DEEPSEEK_API_KEY`   |
| Anthropic  | `ANTHROPIC_PROVIDER_ENABLED`| `ANTHROPIC_API_KEY`  |

Para habilitar **apenas um** provider, deixe os outros como `false`.

---

## Como Limitar Custo

```env
REAL_PROVIDER_MAX_COST_BRL=2.00
```

O limite é aplicado por requisição. Se o custo estimado da requisição exceder
esse valor, a chamada é bloqueada antes de atingir o provider.

`REAL_PROVIDER_TIMEOUT_SECONDS=30` controla o timeout total da requisição.

---

## Como Rodar Validação

### 1. Validar ambiente local

```bash
make validate-real-provider-env
```

Verifica `.env.local`, permissões, gitignore, e configuração de cada provider.

### 2. Rodar testes unitários

```bash
.venv/bin/python -m pytest \
  tests/test_real_provider_env.py \
  tests/test_real_provider_env_security.py \
  tests/test_real_provider_env_example.py \
  -q
```

Testes nunca chamam internet. Providers não configurados geram
`SKIP_PROVIDER_NOT_CONFIGURED`.

### 3. Validar secrets

```bash
./scripts/validators/check-secrets.sh --all
```

Garante que nenhuma chave real vazou para arquivos versionados.

---

## Como Interpretar SKIP / PASS / FAIL

| Status  | Significado                                                                 |
|---------|-----------------------------------------------------------------------------|
| `SKIP`  | Provider desabilitado ou sem chave — ignorado com segurança.                |
| `PASS`  | Provider configurado com chave presente — pronto para teste real.           |
| `FAIL`  | Provider habilitado mas com chave ausente ou configuração inválida.         |

SKIP não é erro — significa "não configurado, nada a testar".

---

## Como Garantir que Chaves Não Entram no Git

- `.env.local` está em `.gitignore` (padrão `!.env.example` `!.env.local.example`)
- `check-secrets.sh` detecta chaves reais em arquivos versionados
- O script `validate-real-provider-env-local.sh` verifica que:
  - `.env.example` não contém valores reais de chave
  - `artifacts/` não contém chaves reais
  - Permissões de `.env.local` são restritivas
- O Makefile expõe `make validate-real-provider-env`

---

## Nenhum Provider Real é Obrigatório

A stack funciona 100% local sem nenhuma chave. Providers cloud são opcionais:

- Se `REAL_PROVIDER_VALIDATION_ENABLED=false` → zero chamadas de saída
- Se `OPENAI_PROVIDER_ENABLED=false` → OpenAI ignorado
- Se chave ausente → provider tratado como não configurado

---

## Custo Real

Requisições reais para OpenAI, DeepSeek ou Anthropic **geram custo** na conta
do provider. Use com responsabilidade:

- Prefira modelos baratos para teste (`gpt-4o-mini`, `deepseek-chat`, `claude-3-haiku`)
- Configure `REAL_PROVIDER_MAX_COST_BRL` com valor baixo
- Monitore o console do provider para evitar surpresas
- Desabilite `REAL_PROVIDER_VALIDATION_ENABLED` quando não estiver testando

---

## Proteções de Segurança

| Proteção                           | Descrição                                                   |
|------------------------------------|-------------------------------------------------------------|
| Opt-in duplo                       | `REAL_PROVIDER_VALIDATION_ENABLED` + `*_PROVIDER_ENABLED`   |
| Chave mascarada em logs            | `mask_provider_key()` mostra apenas `sk-p****abcd`          |
| Cost cap por requisição            | Bloqueia antes de enviar se custo estimado exceder limite   |
| Timeout configurável               | Evita hangs em providers offline                            |
| Sem chaves em .env.example         | Apenas nomes de variáveis, nunca valores reais              |
| Sem chaves em artifacts            | Verificado por `assert_no_provider_key_leak()`              |
| Permissão 600 recomendada          | `chmod 600 .env.local`                                      |
| check-secrets.sh no pre-commit     | Detecta vazamento de chaves antes do commit                 |

---

## Validação OpenAI Real

### Pré-requisitos

```env
# .env.local
REAL_PROVIDER_VALIDATION_ENABLED=true
OPENAI_PROVIDER_ENABLED=true
OPENAI_API_KEY=sk-proj-...
```

### Dry-run (sem chamadas reais)

```bash
make validate-openai-real-dry
```

Verifica env, chave, guards — sem custo.

### Real (com chamadas reais)

```bash
make validate-openai-real
```

Faz chamadas reais para:
- `GET /v1/models` — health check
- `POST /v1/responses` — `"Responda apenas: OK"` (modelo configurável)
- `POST /v1/embeddings` — `"teste de embedding"`

Gera relatório em `artifacts/real-provider-validation/openai/<timestamp>/`.

### Limitar custo

```bash
./scripts/validators/validate-openai-real-provider.sh --real --max-cost-brl 1.00 --model gpt-4o-mini
```

### Segurança

- `REAL_PROVIDER_LOG_PROMPTS=false` (padrão) — prompt não aparece em logs
- `REAL_PROVIDER_STORE_RESPONSES=false` (padrão) — resposta não é salva
- Chave mascarada em todos os outputs
- Testes unitários não chamam internet (usam mocks)

## Validação DeepSeek Real

### Pré-requisitos

```env
# .env.local
REAL_PROVIDER_VALIDATION_ENABLED=true
DEEPSEEK_PROVIDER_ENABLED=true
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### Dry-run (sem chamadas reais)

```bash
make validate-deepseek-real-dry
```

Verifica env, chave, guards — sem custo.

### Real (com chamadas reais)

```bash
make validate-deepseek-real
```

Faz chamadas reais para:
- `GET /v1/models` — health check
- `POST /v1/chat/completions` — `"Responda apenas: OK"` (modelo configurável)
- `responses` e `embeddings` — SKIP_UNSUPPORTED_CAPABILITY (DeepSeek não suporta)

Gera relatório em `artifacts/real-provider-validation/deepseek/<timestamp>/`.

### Limitar custo

```bash
./scripts/validators/validate-deepseek-real-provider.sh --real --max-cost-brl 1.00 --model deepseek-chat
```

### Segurança

- `DEEPSEEK_API_KEY` mascarada em todos os outputs
- Prompt nunca aparece em logs (padrão)
- DeepSeek não possui Responses API nem Embeddings API — validado como SKIP
- Testes unitários não chamam internet (usam mocks)

## Validação Fallback Local-to-Cloud

### Pré-requisitos

```env
# .env.local
REAL_PROVIDER_VALIDATION_ENABLED=true
# Pelo menos um provider cloud configurado:
OPENAI_PROVIDER_ENABLED=true
OPENAI_API_KEY=sk-proj-...
# ou ANTHROPIC_API_KEY, DEEPSEEK_API_KEY
```

### Mecanismo de Simulação de Falha Local

Controlado pela env `ROUTING_TEST_FORCE_LOCAL_FAILURE=false` (padrão).
Quando `=true`, o smart router trata providers locais (`local`, `lmstudio`) como
indisponíveis, forçando fallback para cloud (se configurado) ou mock.

Também exposto como endpoint admin (apenas em validation mode):

```bash
# Verificar status atual
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:8080/admin/routing/test/force-local-failure

# Ativar falha local
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}' \
  http://localhost:8080/admin/routing/test/force-local-failure

# Desativar
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}' \
  http://localhost:8080/admin/routing/test/force-local-failure
```

### Dry-run (sem chamadas reais)

```bash
make validate-real-fallback-dry
```

Simula decisões de roteamento:
- Modo normal: local selecionado
- Com falha local forçada: cloud selecionado (se configurado)
- Valida `fallback_chain`, `cloud_used`, `fallback_used`
- Nenhuma chamada real a provider

### Real (com chamadas reais para cloud)

```bash
make validate-real-fallback
```

ou customizado:

```bash
./scripts/validators/validate-real-fallback-local-to-cloud.sh --real --provider openai
```

Fluxo:
1. Ativa `ROUTING_TEST_FORCE_LOCAL_FAILURE=true`
2. Simula roteamento — cloud deve ser selecionado
3. Executa request mínimo `"Responda apenas: OK"` no cloud provider
4. Valida resposta, latência, custo
5. Restaura flag de falha local para `false`
6. Valida que local volta ao normal na simulação

Gera relatório em `artifacts/real-provider-validation/fallback/<timestamp>/`.

### Segurança

- Falha local nunca afeta ambiente real — apenas simulação em memória
- Flag `ROUTING_TEST_FORCE_LOCAL_FAILURE` sempre restaurada ao final
- Endpoint admin protegido por `X-Admin-Token` e requer `REAL_PROVIDER_VALIDATION_ENABLED=true`
- Nenhuma chave ou prompt aparece nos relatórios
- Cost cap `REAL_PROVIDER_MAX_COST_BRL` respeitado
- Wallet balance verificado antes de rotear para cloud

## Validação Anthropic Real

### Pré-requisitos

```env
# .env.local
REAL_PROVIDER_VALIDATION_ENABLED=true
ANTHROPIC_PROVIDER_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_BASE_URL=https://api.anthropic.com
```

### Dry-run (sem chamadas reais)

```bash
make validate-anthropic-real-dry
```

Verifica env, chave, guards — sem custo.

### Real (com chamadas reais)

```bash
make validate-anthropic-real
```

Faz chamadas reais para:
- `GET /v1/models` — health check
- `POST /v1/messages` — `"Responda apenas: OK"` (Messages API)
- `responses` e `embeddings` — SKIP_UNSUPPORTED_CAPABILITY (Anthropic não suporta)

Gera relatório em `artifacts/real-provider-validation/anthropic/<timestamp>/`.

### Limitar custo

```bash
./scripts/validators/validate-anthropic-real-provider.sh --real --max-cost-brl 1.00 --model claude-3-haiku-20240307
```

### Segurança

- `ANTHROPIC_API_KEY` mascarada em todos os outputs
- Prompt nunca aparece em logs (padrão)
- Anthropic não possui Responses API nem Embeddings API — validado como SKIP
- Testes unitários não chamam internet (usam mocks)
- O adapter usa Messages API (`POST /v1/messages`), mapeando `system` do formato interno
  para o parâmetro `system` da Anthropic, e os demais messages para `messages`

### Message Mapping

O adapter Anthropic converte automaticamente:

| Formato Interno | Anthropic Messages API |
|----------------|----------------------|
| `messages[role=system].content` | `system` (parâmetro separado) |
| `messages[role=user].content` | `messages[role=user].content` |
| `messages[role=assistant].content` | `messages[role=assistant].content` |
| `image_url` content blocks | `image` content blocks (base64) |
| OpenAI usage format | `input_tokens` / `output_tokens` |

## Exemplo de Uso

```bash
# 1. Configurar .env.local com chave OpenAI
REAL_PROVIDER_VALIDATION_ENABLED=true
OPENAI_PROVIDER_ENABLED=true
OPENAI_API_KEY=sk-proj-...

# 2. Validar ambiente
make validate-real-provider-env

# 3. Rodar dry-run
make validate-openai-real-dry

# 4. Rodar testes
.venv/bin/python -m pytest tests/test_real_provider_env.py -q

# 5. Rodar testes OpenAI
.venv/bin/python -m pytest \
  tests/test_openai_real_provider_validator.py \
  tests/test_openai_provider_sanitization.py \
  tests/test_openai_provider_billing_mapping.py \
  -q

# 6. Rodar dry-run DeepSeek
make validate-deepseek-real-dry

# 7. Rodar testes DeepSeek
.venv/bin/python -m pytest \
  tests/test_deepseek_real_provider_validator.py \
  tests/test_deepseek_provider_sanitization.py \
  tests/test_deepseek_provider_billing_mapping.py \
  -q

# 8. Rodar dry-run Anthropic
make validate-anthropic-real-dry

# 9. Rodar testes Anthropic
.venv/bin/python -m pytest \
  tests/test_anthropic_real_provider_validator.py \
  tests/test_anthropic_provider_message_mapping.py \
  tests/test_anthropic_provider_sanitization.py \
  tests/test_anthropic_provider_billing_mapping.py \
  -q

# 10. Rodar dry-run Fallback Local-to-Cloud
make validate-real-fallback-dry

# 11. Rodar testes Fallback
.venv/bin/python -m pytest \
  tests/test_real_fallback_routing.py \
  tests/test_real_fallback_safety.py \
  tests/test_real_fallback_billing.py \
  tests/test_real_fallback_sanitization.py \
  -q

---

## Medição de Custos Reais (v1.8.1)

### Visão Geral

O script `scripts/dev/measure-real-provider-costs.sh` mede custo real/estimado por provider
usando requests reais mínimos. Resultados são registrados em BRL.

### Como Rodar

```bash
# Dry-run (sem chamadas reais)
make measure-provider-costs-dry

# Real (com chamadas reais mínimas)
make measure-provider-costs

# Com parâmetros customizados
./scripts/dev/measure-real-provider-costs.sh \
  --real \
  --providers openai,deepseek,anthropic \
  --max-cost-brl 2.00 \
  --runs 1 \
  --output-dir artifacts/real-provider-validation/costs

# Ajuda
./scripts/dev/measure-real-provider-costs.sh --help
```

### Opções

| Opção | Descrição |
|-------|-----------|
| `--dry-run` | Verifica env sem chamadas reais |
| `--real` | Faz chamadas reais mínimas |
| `--providers` | Lista de providers separada por vírgula |
| `--max-cost-brl` | Limite de custo por request (default: 2.00) |
| `--runs` | Número de execuções (default: 1) |
| `--output-dir` | Diretório de saída |
| `--help` | Mostra ajuda |

### Fluxo

1. Carrega provider pricing config (`config/provider-pricing.example.json`)
2. Para cada provider configurado:
   - Se disabled/missing key → SKIP
   - Se `--real`: faz request mínimo ("Responda apenas: OK")
   - Coleta usage tokens da resposta
   - Calcula `provider_cost_usd` usando pricing config
   - Converte para BRL usando `USD_BRL_RATE`
   - Calcula `customer_price_brl` (plano Pro)
   - Calcula `gross_profit_brl` e `margin_percent`
   - Registra `latency_ms` e `cache_hit=false`
3. Gera relatório em `artifacts/real-provider-validation/costs/<timestamp>/`

### Campos do Relatório

| Campo | Descrição |
|-------|-----------|
| `provider` | Nome do provider |
| `model` | Modelo usado |
| `endpoint_type` | Tipo de endpoint (chat) |
| `input_tokens` | Tokens de input |
| `output_tokens` | Tokens de output |
| `total_tokens` | Total de tokens |
| `latency_ms` | Latência em ms |
| `provider_cost_usd` | Custo do provider em USD |
| `provider_cost_brl` | Custo do provider em BRL |
| `customer_price_brl` | Preço cobrado do cliente |
| `gross_profit_brl` | Lucro bruto |
| `margin_percent` | Margem percentual |
| `pricing_source` | Fonte do pricing |
| `status` | PASS, SKIP ou FAIL |

### Admin Endpoint

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:8080/admin/providers/cost-validation/latest
```

Retorna o relatório mais recente de medição de custos, sanitizado (sem chaves).

### Testes

```bash
.venv/bin/python -m pytest \
  tests/test_measure_real_provider_costs.py \
  tests/test_provider_cost_report.py \
  tests/test_provider_cost_sanitization.py \
  -q
```

### Segurança

- Chaves mascaradas em todos os outputs (`mask_provider_key()`)
- Prompt "Responda apenas: OK" — sem dados sensíveis
- `REAL_PROVIDER_MAX_COST_BRL` respeitado por requisição
- `REAL_PROVIDER_LOG_PROMPTS=false` (padrão) — prompt não aparece em logs
- `cache_hit=false` para todas as medições (requests frescos)
- Admin endpoint sanitiza chaves antes de retornar
- Testes 100% offline — sem chamadas reais a providers
```

## Real Provider Validation
For accurate billing and cost margin calculations in BRL, run `make measure-provider-costs` to validate provider API costs. Ensure you respect `REAL_PROVIDER_MAX_COST_BRL`.

## Real Billing Margin Validation
Margins are validated using real configurations but minimal requests to avoid cost. Check `make validate-real-billing-margin`.

## Artifact Sanitization
We run `scripts/dev/scan-real-provider-artifacts.sh` after validations to ensure no secrets or prompts are exposed in artifacts.

## Real Providers E2E Validation
For a full, safe run across all configured providers including billing, margin, cost, and sanitization, run `make validate-real-providers-e2e`.
