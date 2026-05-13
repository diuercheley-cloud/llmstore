# v1.8.1 Real Provider Validation

## Objetivo

Fechar a release `v1.8.1-real-provider-validation` com validação real opcional
de providers cloud, sem tornar nenhum provider obrigatório para operação local
ou para o fechamento da release.

Esta release adiciona uma trilha segura para:

- validar OpenAI real via `.env.local`
- validar DeepSeek real via `.env.local`
- validar Anthropic real via `.env.local`
- testar fallback real `local -> cloud`
- medir custo real por provider
- confirmar billing em BRL e margem com requests reais opcionais
- impedir vazamento de secrets, prompts, respostas e logs reais

## Providers Reais Suportados

- OpenAI
- DeepSeek
- Anthropic

Todos os providers reais são `opt-in`. O produto continua funcional em modo
local-first sem nenhuma chave cloud configurada.

## Como Configurar `.env.local`

1. Copie o template:

```bash
cp .env.example .env.local
chmod 600 .env.local
```

2. Habilite apenas o que for realmente testar:

```env
REAL_PROVIDER_VALIDATION_ENABLED=true
REAL_PROVIDER_MAX_COST_BRL=2.00
REAL_PROVIDER_TIMEOUT_SECONDS=30
REAL_PROVIDER_LOG_PROMPTS=false
REAL_PROVIDER_STORE_RESPONSES=false

OPENAI_PROVIDER_ENABLED=true
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small

DEEPSEEK_PROVIDER_ENABLED=false
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_MODEL=deepseek-chat

ANTHROPIC_PROVIDER_ENABLED=false
ANTHROPIC_API_KEY=
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

3. Preencha somente as chaves dos providers que serão usados.

Política obrigatória:

- não versionar `.env.local`
- não versionar API keys
- não usar valores reais em `.env.example`

## Como Rodar Dry-Run

Validação de ambiente:

```bash
./scripts/validate-real-provider-env-local.sh
```

Validação por provider:

```bash
./scripts/validate-openai-real-provider.sh --dry-run
./scripts/validate-deepseek-real-provider.sh --dry-run
./scripts/validate-anthropic-real-provider.sh --dry-run
```

Fallback, custos, billing e E2E:

```bash
./scripts/validate-real-fallback-local-to-cloud.sh --dry-run
./scripts/measure-real-provider-costs.sh --dry-run
./scripts/validate-real-billing-margin.sh --dry-run
./scripts/validate-real-providers-e2e.sh --dry-run
```

## Como Rodar Real

Execução real não roda automaticamente nesta release.

Se o operador tiver `.env.local` configurado, os comandos manuais são:

```bash
./scripts/validate-openai-real-provider.sh --real
./scripts/validate-deepseek-real-provider.sh --real
./scripts/validate-anthropic-real-provider.sh --real
./scripts/validate-real-fallback-local-to-cloud.sh --real
./scripts/measure-real-provider-costs.sh --real
./scripts/validate-real-billing-margin.sh --real
./scripts/validate-real-providers-e2e.sh --real --max-cost-brl 2.00
```

## Política de Custo

- Cloud real permanece opt-in.
- O teto padrão é `REAL_PROVIDER_MAX_COST_BRL=2.00`.
- Dry-run não deve gerar custo real.
- Requests reais devem usar payloads mínimos e modelos baratos quando possível.
- A validação E2E real recomendada para operador é:

```bash
./scripts/validate-real-providers-e2e.sh --real --max-cost-brl 2.00
```

## Política de Sanitização

- Não commitar `.env.local`.
- Não commitar provider API keys.
- Não commitar `artifacts/real-provider-validation/`.
- Não commitar logs reais.
- Não commitar prompts/respostas reais.
- Não commitar `.tar.gz`.
- Rodar scanner e secrets check antes de stage/finalização.

## SKIP vs PASS vs FAIL

- `SKIP`: provider real desabilitado, gate global desligado ou chave ausente.
  Esse é o comportamento esperado quando o ambiente real não está configurado.
- `PASS`: validação concluída dentro das regras de custo, segurança e
  sanitização.
- `FAIL`: configuração inválida, vazamento detectado, custo acima do limite ou
  erro real de validação.

## Critérios de Fechamento

- `Security Report`: `PASS`
- `Production Readiness`: `READY`
- Providers reais não podem ser exigidos para fechar a release.
- Validators devem retornar `SKIP` controlado quando não houver providers reais
  configurados.

## Limitações

- cloud real continua opt-in
- PIX/PSP real continuam fora do escopo
- sem chaves versionadas
