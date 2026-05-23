# SLOs e Budgets por Classe de Agente

Este documento descreve como o LLM Inference Stack gerencia Service Level Objectives (SLOs) e orçamentos operacionais para diferentes classes de agentes.

## Classes de Agentes

Cada agente deve ser associado a uma classe que define seus limites e alvos de performance. As classes suportadas são:

-   **support**: Otimizado para suporte ao cliente, com alta taxa de sucesso e latência baixa.
-   **ops**: Agentes de operações com limites moderados.
-   **compliance**: Limites altos para tarefas complexas, mas com alvo de 100% de sucesso.
-   **billing**: Agentes financeiros com regras rígidas.
-   **rag_research**: Focado em pesquisa extensiva, permitindo muitos passos e alto consumo de tokens.
-   **deployment**: Agentes de deploy.
-   **security**: Classe mais restrita, com latência mínima e limites severos para evitar abuso.
-   **custom**: Para casos de uso genéricos.
-   **default**: Configuração conservadora aplicada a agentes sem classe definida.

## Configuração (YAML)

A configuração reside em `config/agent-slo-classes.yaml`.

Exemplo de limites por classe:

| Parâmetro | Security | RAG Research | Default |
|-----------|----------|--------------|---------|
| `run_success_rate_target` | 1.0 (100%) | 0.90 | 0.95 |
| `p95_latency_seconds` | 15s | 300s | 60s |
| `max_cost_brl_per_run` | R$ 1.00 | R$ 15.00 | R$ 5.00 |
| `max_steps` | 5 | 100 | 10 |
| `max_tokens_per_run` | 25.000 | 500.000 | 100.000 |

## Execução e Enforce

O `AgentExecutor` valida o orçamento do agente em cada passo da execução. Se um limite (custo, tokens ou passos) for excedido, a execução é interrompida imediatamente com o status `failed` e o motivo detalhado.

### SLO Breaches

O `AgentSLOService` calcula periodicamente (ou sob demanda) a aderência aos SLOs. Se a taxa de sucesso cair abaixo do alvo da classe, um evento de "SLO Breach" é registrado, incrementando as métricas no Prometheus e podendo disparar incidentes.

## API de Administração

-   `GET /admin/agents/slo/classes`: Lista as definições de todas as classes.
-   `GET /admin/agents/slo/report`: Relatório de conformidade de SLO.
-   `GET /admin/agents/budgets`: Consulta orçamentos por classe.
-   `POST /admin/agents/budgets/validate`: Valida manualmente se uma execução específica está dentro do orçamento.

## Segurança

A classe **security** é projetada para ser a mais "mão de ferro" do sistema, garantindo que agentes com privilégios de segurança operem de forma extremamente previsível e barata, minimizando riscos de loops infinitos ou exfiltração massiva de dados.
