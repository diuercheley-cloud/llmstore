# Agent Planning

O planejamento permite que agentes decomponham objetivos complexos em uma série de tarefas estruturadas antes da execução.

## Conceitos

- **Plan**: Uma sequência de tarefas destinadas a atingir um objetivo específico.
- **Goal**: O objetivo final do agente (armazenado como hash para privacidade).
- **Draft Plan**: Um plano gerado que ainda não foi aprovado para execução.

## Workflow de Planejamento

1. **Decomposição**: O agente recebe um objetivo e gera uma lista de tarefas.
2. **Dependências**: Tarefas podem depender da conclusão de outras (DAG - Directed Acyclic Graph).
3. **Análise de Risco**: Cada plano recebe um `risk_score` baseado nas ferramentas e ações propostas.
4. **Revisão Humana**: Planos de alto risco podem ser editados ou aprovados por um operador antes de iniciar a execução.

## Vantagens

- **Transparência**: O operador vê o que o agente pretende fazer antes de acontecer.
- **Segurança**: Bloqueio de ações perigosas no nível do plano.
- **Eficiência**: Reutilização de planos bem-sucedidos para objetivos similares.
