# Commercial Profit Routing (Phase 4)

## Objetivo
O **Commercial Profit Routing** é um sistema de roteamento inteligente que seleciona automaticamente a melhor rota (provider/modelo) para cada requisição, priorizando a lucratividade e a qualidade, respeitando as políticas do plano do cliente e os guardrails comerciais.

## Diferença entre Guardrails e Routing
- **Commercial Guardrails:** Atuam como um filtro de segurança (pass/fail) para bloquear rotas que excedam custos ou tenham margem negativa.
- **Commercial Profit Routing:** Atua como um selecionador ativo (ranking) que escolhe a rota com o melhor custo-benefício comercial.

## Configuração (Variáveis de Ambiente)
```bash
COMMERCIAL_ROUTING_ENABLED=false
COMMERCIAL_ROUTING_DEFAULT_POLICY=disabled
COMMERCIAL_MIN_MARGIN_PERCENT=20
COMMERCIAL_LOCAL_ROUTE_BONUS=10
COMMERCIAL_LATENCY_WEIGHT=0.15
COMMERCIAL_MARGIN_WEIGHT=0.60
COMMERCIAL_QUALITY_WEIGHT=0.25
```

## Fórmula de Score
O score de cada rota é calculado por:
`score = (margin_score * margin_weight) + (quality_score * quality_weight) - (latency_penalty * latency_weight) + bonuses - penalties`

- **Margin Score (0-100):** Escala a margem percentual (ex: 66% margem = 100 pontos).
- **Quality Score (0-100):** Representa a capacidade do modelo (ex: GPT-4 = 95, Local = 70).
- **Latency Penalty:** Penalidade baseada na latência estimada (ms).
- **Bonuses:**
  - `local_bonus`: Adicionado para rotas locais (+10 por padrão).
  - `policy_bonus`: Adicionado conforme o plano do cliente (ex: Basic ganha bônus em rotas locais).
- **Penalties:**
  - `health_penalty`: Aplicado se o provider estiver em estado "degraded".

## Comportamento por Plano
- **Basic:** Prioriza rotas locais e menor custo. Ganha bônus extra (+20) em rotas locais.
- **Pro:** Equilibra margem e qualidade. Ganha bônus (+15) se a margem for > 40%.
- **Premium:** Aceita custos maiores se a margem for positiva e a qualidade for superior. Ganha bônus (+25) para modelos top-tier.
- **Coding:** Prioriza modelos marcados como excelentes para coding (ex: Claude 3.5 Sonnet), respeitando a margem mínima.

## Simulação Admin
Acesse o endpoint `POST /admin/routing/commercial-profit/simulate` para visualizar o ranking de rotas sem realizar chamadas reais.

### Exemplo de Ranking
```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "score": 87.5,
  "estimated_cost_brl": 0.12,
  "estimated_revenue_brl": 0.30,
  "estimated_margin_brl": 0.18,
  "estimated_margin_percent": 60,
  "latency_penalty": 5,
  "health_penalty": 0,
  "local_bonus": 0,
  "policy_bonus": 15,
  "rejection_reasons": []
}
```

## Troubleshooting
- **Cloud bloqueada:** Verifique se `GLOBAL_CLOUD_KILL_SWITCH` está `true` ou se `COMMERCIAL_ROUTING_ENABLED` está `false`.
- **Nenhuma rota encontrada:** Se todas as rotas (incluindo locais) forem rejeitadas por guardrails, o sistema retornará erro. Verifique os `rejection_reasons` na simulação.
- **Margem baixa:** Se a margem estimada for menor que `COMMERCIAL_MIN_MARGIN_PERCENT`, os providers cloud serão rejeitados.
