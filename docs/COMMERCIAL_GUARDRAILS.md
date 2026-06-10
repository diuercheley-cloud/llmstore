---
owner: platform-ops
status: consolidated
---

# Commercial Guardrails

Camada admin-only para observabilidade financeira/comercial da operação híbrida, sem chamadas externas e sem bloquear tráfego real nesta fase.

## Objetivo

Permitir que o operador visualize risco de custo diário por provider, custo por cliente/tenant e risco de margem negativa antes de integrar enforcement real ao roteamento.

## Modos

- `disabled`: guardrails desligados. A API continua disponível para mostrar snapshot neutro.
- `report_only`: calcula warnings e `would_block`, mas não interfere em requests reais.
- `enforcing_ready`: ainda não bloqueia nesta fase, mas sinaliza que as regras estão prontas para futura integração controlada ao smart router.

## Variáveis de Ambiente

```env
COMMERCIAL_GUARDRAILS_ENABLED=false
MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL=0
MAX_PROVIDER_COST_PER_DAY_BRL=0
MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL=0
MARGIN_WARNING_PERCENT=20
NEGATIVE_MARGIN_BLOCK_MODE=report_only
```

Regras:

- `0` em limites de custo significa "desabilitado".
- Defaults são conservadores e seguros para modo local/offline.
- Nenhuma variável ativa cloud real por padrão.

## Endpoints

### `GET /admin/commercial-guardrails/overview`

Retorna snapshot consolidado com:

- `generated_at_utc`
- `mode`
- `global_limits`
- `global_usage_today`
- `providers`
- `clients`
- `warnings`
- `would_block`
- `recommendations`

### `POST /admin/commercial-guardrails/simulate`

Payload:

```json
{
  "client_id": "00000000-0000-0000-0000-000000000001",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "estimated_cost_brl": 1.25,
  "estimated_revenue_brl": 2.00
}
```

Resposta:

```json
{
  "allowed_in_report_only": true,
  "would_allow_if_enforced": true,
  "estimated_margin_brl": 0.75,
  "estimated_margin_percent": 37.5,
  "reasons": [],
  "recommendations": []
}
```

## Como Validar

```bash
./scripts/validators/validate-commercial-guardrails.sh
make validate-commercial-guardrails
./venv/bin/pytest -q tests/test_commercial_guardrails_admin_api.py
```

## Limitações Atuais

- Não bloqueia requests reais.
- Não altera smart router, billing core ou fluxo OpenAI-compatible.
- Não faz chamada cloud real e não mede custo em tempo de request.
- A classificação `cloud` vs `local` é inferida por `provider` conhecido, apenas para observabilidade.

## Próxima Fase

Integrar guardrails ao smart router em modo enforcing controlado, com opt-in explícito, rollout gradual e fallback local-first preservado.
