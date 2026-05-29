---
owner: platform-ops
status: consolidated
---

# Commercial Canary Auto-Promotion (Phase 9)

## Visão Geral

A Fase 9 introduz a promoção automática e gradual de configurações canary baseada em Service Level Objectives (SLOs). Isso permite que novas configurações de roteamento comercial sejam testadas com tráfego real de forma segura, expandindo sua participação apenas se os indicadores de saúde (margem, erro, latência) estiverem dentro dos limites esperados.

## Configurações

As seguintes variáveis de ambiente controlam o comportamento da auto-promoção:

| Variável | Padrão | Descrição |
|----------|---------|-----------|
| `COMMERCIAL_CANARY_AUTO_PROMOTION_ENABLED` | `false` | Ativa o serviço de auto-promoção |
| `COMMERCIAL_CANARY_AUTO_PROMOTION_MODE` | `dry_run` | Modos: `disabled`, `dry_run`, `promote` |
| `COMMERCIAL_CANARY_PROMOTION_STEPS` | `5,10,25,50,100` | Passos de percentual para promoção |
| `COMMERCIAL_CANARY_MIN_OBSERVATION_MINUTES` | `60` | Tempo mínimo em cada passo |
| `COMMERCIAL_CANARY_MIN_REQUESTS_PER_STEP` | `100` | Requisições mínimas em cada passo |
| `COMMERCIAL_CANARY_MIN_MARGIN_PERCENT` | `20.0` | Margem real mínima exigida (SLO) |
| `COMMERCIAL_CANARY_MAX_ERROR_RATE_PERCENT` | `2.0` | Taxa de erro máxima permitida (SLO) |
| `COMMERCIAL_CANARY_MAX_LATENCY_REGRESSION_PERCENT` | `20.0` | Regressão de latência máx vs stable (SLO) |
| `COMMERCIAL_CANARY_AUTO_ROLLBACK_ENABLED` | `true` | Ativa rollback automático em caso de violação crítica |

## Regras de Promoção (SLOs)

Uma configuração canary é promovida para o próximo passo se:
1. **Janela de Tempo**: Atingiu o tempo mínimo de observação.
2. **Volume de Tráfego**: Atingiu o número mínimo de requisições.
3. **Lucratividade**: Margem real média >= `COMMERCIAL_CANARY_MIN_MARGIN_PERCENT`.
4. **Taxa de Erro**: Taxa de erro <= `COMMERCIAL_CANARY_MAX_ERROR_RATE_PERCENT`.
5. **Latência**: Latência média não piorou mais que `COMMERCIAL_CANARY_MAX_LATENCY_REGRESSION_PERCENT` em relação à config estável.
6. **Erro de Estimativa**: O erro entre margem estimada e real está sob controle.

## Auto-Rollback

O sistema monitora continuamente os canaries ativos. Se uma violação **crítica** for detectada, o canary é imediatamente desativado:
- Taxa de erro > 10%
- Margem real negativa

A ação é registrada no `AdminActionLog` com o motivo da falha.

## Fluxo de Promoção

1. Configuração é criada como `canary_enabled=true` com `canary_percent=5`.
2. O serviço avalia periodicamente os eventos em `commercial_routing_events`.
3. Se todos os SLOs passarem, sobe para 10% → 25% → 50%.
4. Ao atingir o passo final (ex: 100%), a configuração canary é convertida em **Stable**:
   - A configuração estável anterior para aquele escopo é desativada.
   - `canary_enabled` torna-se `false`.
   - `canary_promotion_status` torna-se `completed`.

## Endpoints Admin

- `GET /admin/routing/commercial-configs/canary-promotions`: Lista canaries ativos e status SLO.
- `GET /admin/routing/commercial-configs/{id}/canary/slo`: Detalhes dos checks de SLO.
- `POST /admin/routing/commercial-configs/canary/promotions/dry-run`: Simula promoções.
- `POST /admin/routing/commercial-configs/{id}/canary/promote-step`: Promove manualmente para o próximo passo.
- `POST /admin/routing/commercial-configs/{id}/canary/auto-rollback`: Força avaliação de rollback.

## Troubleshooting

### Por que meu canary não promove?
Verifique o endpoint `/canary/slo`. Os motivos comuns são:
- Volume de tráfego insuficiente (< 100 reqs).
- Tempo de observação insuficiente (< 60 min).
- Regressão de latência em relação à config estável.

### Como ver o histórico?
Consulte o log de ações admin para eventos do tipo:
- `canary_step_promoted`
- `canary_auto_rollback`
- `canary_completed_to_stable`
