# Painel Executivo de Lucratividade e Drift (Fase 10)

O Painel Executivo fornece uma visão consolidada e de alto nível sobre a saúde financeira e operacional do stack de inferência. Ele foca em métricas de lucro real vs. estimado, detecção de drifts (desvios) e anomalias proativas.

## Objetivo
Permitir que gestores e administradores identifiquem rapidamente:
1. Se a operação está sendo lucrativa em tempo real.
2. Onde existem desvios de custo, margem ou latência que exigem atenção.
3. Quais clientes estão operando com prejuízo.
4. Recomendações automáticas para estabilizar a margem.

## Métricas Principais

### Lucratividade
- **Receita Real (BRL)**: Soma do `actual_revenue_brl` de todos os eventos no período.
- **Custo Real (BRL)**: Soma do `actual_cost_brl` (pago aos providers).
- **Margem Real (BRL/%)**: Lucro líquido e percentual de margem sobre a receita.
- **Erro de Estimativa (%)**: Diferença percentual entre o lucro que o sistema previu e o lucro que realmente ocorreu.

### Drifts (Desvios)
Calculados comparando o período atual (ex: últimas 24h) com o período imediatamente anterior (ex: 24h-48h atrás).
- **Drift de Custo**: Aumento ou redução percentual no custo médio por requisição.
- **Drift de Margem**: Queda ou subida na margem média.
- **Drift de Latência**: Aumento no tempo médio de resposta (pode indicar degradação de provider).

## Anomalias Detectadas
O sistema gera alertas automáticos para:
- **Cost Drift**: Quando o custo sobe acima do limite configurado (padrão 20%).
- **Margin Drift**: Quando a margem cai abaixo do limite (padrão 15%).
- **Latency Drift**: Quando a latência sobe acima do limite (padrão 25%).
- **Negative Margin**: Qualquer requisição que tenha custado mais do que a receita gerada.
- **Estimation Error**: Quando o erro entre estimado e real ultrapassa 20%.

## Configurações

As seguintes variáveis de ambiente controlam o comportamento do dashboard:

```env
COMMERCIAL_EXECUTIVE_DASHBOARD_ENABLED=true
COMMERCIAL_COST_DRIFT_ALERT_PERCENT=20
COMMERCIAL_MARGIN_DRIFT_ALERT_PERCENT=15
COMMERCIAL_LATENCY_DRIFT_ALERT_PERCENT=25
COMMERCIAL_NEGATIVE_MARGIN_ALERT=true
COMMERCIAL_ANOMALY_LOOKBACK_HOURS=24
```

## Endpoints Admin

### Overview Geral
`GET /admin/routing/executive-dashboard/overview?hours=24`
Retorna o resumo completo de lucratividade, drifts, clientes, providers, canaries e anomalias.

### Apenas Anomalias
`GET /admin/routing/executive-dashboard/anomalies`
Retorna uma lista de anomalias detectadas no período.

### Recomendações
`GET /admin/routing/executive-dashboard/recommendations`
Retorna ações sugeridas baseadas nas anomalias atuais.

## Recomendações Executivas (Exemplos)
- "Aumentar cost_multiplier do provider X" (se houver drift de custo alto).
- "Rollback do canary Z recomendado" (se o canary estiver falhando nos SLOs).
- "Cliente A está operando com margem negativa" (exige revisão de pricing).
- "Latência p95 do provider X subiu 35%" (sugere reduzir tráfego para este provider).

## Troubleshooting
- **Métricas zeradas**: Verifique se os providers estão enviando `actual_cost_brl` via `update_actual_financials`.
- **Drift zerado**: O drift exige que existam dados no período anterior para comparação.
- **Muitos alertas de margem negativa**: Considere ativar o `NEGATIVE_MARGIN_BLOCK_MODE` nos Guardrails.
