# Model Canary Deployments

Canary deployments permitem a introdução gradual de um novo modelo ou backend, minimizando o risco de falhas em produção.

## Configuração

Habilite o recurso no arquivo `.env`:

```env
MODEL_CANARY_ENABLED=true
```

## Estratégia Canary

1. **Início**: O novo modelo recebe uma pequena fração do tráfego (ex: 5%).
2. **Monitoramento**: O sistema monitora SLOs de latência e taxa de erro.
3. **Rollback Automático**: Se os SLOs forem violados, o tráfego é automaticamente revertido para o modelo de controle.
4. **Progressão**: O tráfego é incrementado gradualmente (ex: 5% -> 10% -> 25% -> 50%) se os critérios de sucesso forem mantidos.
5. **Finalização**: Após atingir 100% e estabilidade, o novo modelo é promovido.

## Métricas de Segurança

O controlador Canary monitora:
- **Taxa de Erro**: Aumento súbito de erros 5xx.
- **Latência P99**: Degradação significativa da experiência do usuário.
- **Custo**: Desvios inesperados no consumo de tokens/créditos.
