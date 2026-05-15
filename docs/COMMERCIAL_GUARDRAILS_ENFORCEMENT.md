# Commercial Guardrails Enforcement

Integra os commercial guardrails ao roteamento híbrido real, com enforcement controlado apenas para providers cloud e fallback local-first preservado.

## Objetivo

- bloquear uso cloud quando houver risco financeiro ou operacional configurado
- nunca bloquear providers locais ou `mock`
- sempre tentar fallback local antes de falhar
- manter compatibilidade com os endpoints OpenAI-compatible
- manter cloud desabilitada por padrão

## Modos Operacionais

- `disabled`: não aplica guardrails no runtime
- `report_only`: avalia candidatos cloud, registra eventos e warnings, mas não bloqueia requests
- `enforce_cloud_only`: remove apenas candidatos cloud bloqueados; se houver rota local, faz fallback; se não houver, retorna erro estruturado

## Variáveis de Ambiente

```env
COMMERCIAL_GUARDRAILS_ENABLED=false
MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL=0
MAX_PROVIDER_COST_PER_DAY_BRL=0
MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL=0
MARGIN_WARNING_PERCENT=20
NEGATIVE_MARGIN_BLOCK_MODE=report_only
GLOBAL_CLOUD_KILL_SWITCH=false
```

Regras:

- `0` em limites de custo significa desabilitado.
- `GLOBAL_CLOUD_KILL_SWITCH=true` bloqueia somente cloud.
- `NEGATIVE_MARGIN_BLOCK_MODE=enforce_cloud_only` nunca impede fallback local.
- Nenhuma dessas flags ativa cloud real por padrão.

## Fallback Local-First

Fluxo efetivo:

1. request entra em `/v1/chat/completions`, `/v1/responses` ou `/v1/completions`
2. o modelo resolve as rotas candidatas
3. guardrails avaliam apenas providers cloud
4. se cloud puder ser usado, a rota segue normalmente
5. se cloud for bloqueado, o roteador tenta a próxima rota local
6. se não houver rota local, retorna erro OpenAI-compatible sanitizado

## Kill Switch Cloud

Quando `GLOBAL_CLOUD_KILL_SWITCH=true`:

- nenhum provider cloud é usado
- requests locais continuam funcionando
- o admin dashboard mostra `CLOUD DISABLED`
- `runtime-status` expõe o kill switch ativo

## Erro Estruturado

Sem fallback local disponível, a resposta é:

```json
{
  "error": {
    "message": "Cloud provider temporarily unavailable due to operational guardrails.",
    "type": "commercial_guardrail_block",
    "code": "cloud_provider_blocked"
  }
}
```

O payload não expõe custos internos, margens, limites, prompts, respostas completas ou secrets.

## Runtime Status

`GET /admin/commercial-guardrails/runtime-status`

Retorna:

- `enforcement_mode`
- `cloud_kill_switch`
- `local_fallback_enabled`
- `blocked_cloud_requests_today`
- `successful_local_fallbacks_today`
- `report_only_events_today`
- `providers_blocked`
- `clients_affected`
- `top_fallback_providers`

## Exemplos de Fallback

- cloud bloqueado por kill switch + rota `llama.cpp` disponível: request segue local com `X-Fallback-Used: true`
- cloud bloqueado por limite diário + rota `mock` disponível: request segue local
- somente rota cloud disponível: retorna `commercial_guardrail_block`

## Smart Router

A integração real acontece antes da seleção final da rota em `model_policy.plan_routing_order(...)`.

- a classificação local/cloud é centralizada em `provider_classification.py`
- o runtime constrói contexto financeiro por request sem chamadas externas
- o filtro remove somente candidatos cloud bloqueados em `enforce_cloud_only`

## Troubleshooting

- `mode=disabled`: verifique `COMMERCIAL_GUARDRAILS_ENABLED`
- cloud continua passando em `report_only`: comportamento esperado
- fallback não ocorreu: confira se o modelo tem rota local ativa
- erro `cloud_provider_blocked`: não havia fallback local disponível
- `make validate-commercial-guardrails` retornando `404`: a stack HTTP em execução pode estar desatualizada

## SaaS vs Appliance

- SaaS: use `report_only` primeiro, depois `enforce_cloud_only` com rollout controlado
- Appliance/local-only: pode manter guardrails só para observabilidade admin-only, com cloud desligada

## Como Validar

```bash
./venv/bin/pytest -q \
  tests/test_commercial_guardrails_admin_api.py \
  tests/test_commercial_guardrails_enforcement.py \
  tests/test_margin_dashboard_admin_api.py

bash -n scripts/validate-commercial-enforcement.sh
bash -n scripts/validate-commercial-guardrails.sh
bash -n scripts/validate-margin-dashboard.sh
make validate-commercial-enforcement
```

## Limitações Atuais

- o status runtime é mantido em memória do processo
- o enforcement atua apenas no roteamento cloud/local, não recalcula billing já persistido
- a classificação de providers depende da taxonomia conhecida em `provider_classification.py`

## Próxima Fase

Roteamento inteligente por margem/lucro com seleção automática de provider.
