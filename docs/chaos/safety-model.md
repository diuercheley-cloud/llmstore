# Modelo de Segurança de Chaos

O modelo de segurança do `llm-inference-stack` chaos framework é baseado em camadas de proteção:

## Camada 1: Configuração de Ambiente
O sistema verifica `CHAOS_ENVIRONMENT`. Se for diferente de `test` ou `staging`, a execução é bloqueada preventivamente.

## Camada 2: Blast Radius
Cada experimento possui um `blast_radius` definido:
- **Low**: Impacta apenas uma única requisição ou processo efêmero.
- **Medium**: Impacta um serviço auxiliar (ex: Redis Cache).
- **High**: Impacta o fluxo principal de inferência ou o Control Plane.

## Camada 3: Timeouts e Rollbacks
Nenhuma injeção de falha pode ser eterna. O `timeout_seconds` é obrigatório e a lógica de rollback é testada antes de cada ativação.
