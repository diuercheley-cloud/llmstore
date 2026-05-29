---
owner: platform-ops
status: consolidated
---

# Chaos Engineering

O `llm-inference-stack` adota o **Chaos Engineering** como uma prática formal para validar e melhorar a resiliência da plataforma frente a falhas inevitáveis em ambientes distribuídos.

## Princípios de Operação

1. **Hipótese**: Definimos o que esperamos que aconteça quando uma falha ocorre (ex: "O tráfego deve ser roteado para o standby se o provider X falhar").
2. **Injeção**: Introduzimos a falha de forma controlada.
3. **Observação**: Monitoramos o impacto nos SLOs e o comportamento do sistema.
4. **Rollback**: A falha deve ser revertida automaticamente ou manualmente após o tempo definido.
5. **Aprendizado**: Geramos relatórios de resiliência para guiar melhorias na infraestrutura.

## Segurança (Safety First)

- **Opt-in**: O framework de chaos é desativado por padrão (`CHAOS_ENABLED=false`).
- **Isolamento**: Experimentos são restritos ao ambiente de `test` por padrão.
- **Mocks**: No CI, utilizamos injeções baseadas em mocks de rede e banco, sem afetar hardware real ou custos.
- **Abort Switch**: Todos os experimentos podem ser abortados instantaneamente via Admin UI ou CLI.

> [!WARNING]
> Nunca execute experimentos de chaos em produção sem a aprovação explícita e a configuração `CHAOS_ALLOW_PRODUCTION=true`.
