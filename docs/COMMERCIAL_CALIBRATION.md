# Commercial Routing Calibration

## Objetivo
O objetivo da calibração automática é reduzir o erro entre a margem estimada (usada no roteamento) e a margem real (observada após a execução). Isso permite que o `commercial_profit` router tome decisões mais precisas e evite rotas que parecem lucrativas mas que, na prática, resultam em prejuízo ou margem baixa.

## Funcionamento
O serviço de calibração analisa os eventos persistidos em `commercial_routing_events` e compara:
- `estimated_cost_brl` vs `actual_cost_brl`
- `estimated_revenue_brl` vs `actual_revenue_brl`

### Modo `recommend_only`
Nesta fase, a calibração opera exclusivamente em modo **recomendação**. Nenhuma alteração é aplicada automaticamente às configurações de roteamento ou multiplicadores de custo reais.

### Cálculo de Multiplicador de Custo
Se um provedor/modelo tem um custo real consistentemente maior que o estimado, recomendamos um multiplicador para ajustar o custo estimado futuro.

#### Robustez e Outliers
Para evitar que eventos extremos (outliers) distorçam as recomendações, o sistema utiliza:
- **Trimmed Mean (Média Aparada):** Remove os top/bottom X% (default 5%) das amostras antes de calcular a média, garantindo estabilidade.
- **Percentis:** O relatório inclui Mediana e P95 para análise de dispersão.
- **Limites de Mudança:** Mesmo com erro alto, a recomendação individual é limitada por `COMMERCIAL_CALIBRATION_MAX_RECOMMENDED_CHANGE_PERCENT` (default 25%) por ciclo de calibração.

Fórmula base:
`multiplier = actual_cost / estimated_cost`

Exemplo:
- Custo estimado: R$ 1,00
- Custo real: R$ 1,20
- Multiplicador recomendado: 1.20

### Ajustes de Pesos
Além dos custos, o sistema pode recomendar ajustes nos pesos de roteamento:
- **Aumentar peso de margem:** Quando o erro de custo global está alto, sugerimos priorizar ainda mais a margem para garantir segurança.
- **Aumentar peso de latência:** Se um provedor apresenta latência real muito superior à estimada.
- **Reduzir bônus de provedor:** Para provedores que entregam margem real consistentemente baixa.

## Confidence Levels
- **Low:** Menos de `min_samples` (default: 20). Recomendações não confiáveis.
- **Medium:** Dados suficientes para identificar tendências.
- **High:** Volume significativo de dados (5x min_samples).

## API Admin
### Relatório de Calibração
`GET /admin/commercial-routing/calibration/report?days=7`

Retorna um resumo global, por provedor e por modelo, com multiplicadores e ajustes recomendados.

### Simulação de Calibração
`POST /admin/commercial-routing/calibration/simulate`

Permite simular o impacto de um multiplicador recomendado em um custo específico.

## Configuração
```bash
COMMERCIAL_CALIBRATION_ENABLED=true
COMMERCIAL_CALIBRATION_MODE=recommend_only
COMMERCIAL_CALIBRATION_MIN_SAMPLES=20
COMMERCIAL_CALIBRATION_LOOKBACK_DAYS=7
COMMERCIAL_CALIBRATION_MAX_MULTIPLIER=3.0
COMMERCIAL_CALIBRATION_MIN_MULTIPLIER=0.5
COMMERCIAL_CALIBRATION_USE_TRIMMED_MEAN=true
COMMERCIAL_CALIBRATION_OUTLIER_TRIM_PERCENT=5
COMMERCIAL_CALIBRATION_MAX_RECOMMENDED_CHANGE_PERCENT=25
```

## Riscos e Mitigações
- **Auto-tuning Agressivo:** Multiplicadores muito altos podem excluir provedores bons por causa de alguns outliers. Mitigado por `MAX_MULTIPLIER` e `min_samples`.
- **Dados Obsoletos:** Custos de provedores podem mudar. Mitigado por `LOOKBACK_DAYS`.
- **Feedback Loop:** Se um provedor é penalizado e para de receber tráfego, não teremos novos dados para recalibrar. Mitigado por manter uma exploração mínima ou revisão manual.

## Próximos Passos
1. **Apply Manual:** Recomendações geradas podem ser aplicadas manualmente via [Commercial Config Apply system](./COMMERCIAL_CONFIG_APPLY.md).
2. **Auto Apply (Phase 8):** O sistema agora pode aplicar ajustes pequenos (ex: < 10%) automaticamente via canary se a confiança for `high`. Veja [Auto Apply Canary](./COMMERCIAL_AUTO_APPLY_CANARY.md).
