# Agent Evaluation Framework

Avalia agentes automaticamente usando benchmarks padronizados.

## Benchmarks Suportados

| Benchmark | Descrição | Tarefas |
|-----------|-----------|---------|
| **AgentBench** | Avalia capacidades gerais do agente: tool use, planejamento, execução de código, análise de dados | 8 |
| **GAIA** | Assistente geral com raciocínio multi-step, pesquisa web, ambiguidade e síntese | 8 |
| **BFCL** | Berkeley Function Calling Leaderboard: chamadas simples, múltiplas, paralelas, aninhadas | 8 |

## Métricas

| Métrica | Descrição |
|---------|-----------|
| `success_rate` | Proporção de tarefas concluídas com sucesso |
| `tool_efficiency` | Proporção de chamadas de ferramenta que resultaram em sucesso |
| `latency_ms` | Latência média por tarefa (ms) |
| `token_cost` | Custo estimado em USD (baseado em $0.0000025/token) |
| `hallucination_score` | Score de alucinação (0 = nenhuma, 1 = totalmente alucinado) |

## Serviço

O `AgentEvaluationService` (`control_plane/app/services/agents/agent_evaluation_framework.py`) é o core do framework.

### Uso básico

```python
from app.services.agents.agent_evaluation_framework import AgentEvaluationService

svc = AgentEvaluationService(db)

# Listar benchmarks disponíveis
benchmarks = svc.list_benchmarks()

# Executar benchmark (modo simulado)
report = await svc.run_benchmark(agent_id, "gpt-4", "AgentBench")

# Executar com LLM Harness como backend
report = await svc.run_with_llm_harness(agent_id, "gpt-4", "BFCL", {
    "provider": "openai",
    "max_steps": 10,
})

# Métricas
print(report.metrics["success_rate"])       # 0.875
print(report.metrics["tool_efficiency"])     # 0.92
print(report.metrics["latency_ms"])          # 195.0
print(report.metrics["token_cost"])          # 0.000025
print(report.metrics["hallucination_score"]) # 0.15
```

### Relatórios exportáveis

O framework persiste automaticamente relatórios em 4 formatos:

```python
# CSV
csv_data = svc.export_csv(report)

# Markdown
md = svc.export_markdown(report)

# HTML
html = svc.export_html(report)

# JSON (via to_dict())
json_data = report.to_dict()
```

Os relatórios são salvos em `artifacts/agent-evaluations/<benchmark>/<run_id>/`.

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/admin/evaluation/agent-evaluation/benchmarks` | Lista benchmarks disponíveis |
| `POST` | `/admin/evaluation/agent-evaluation/runs` | Executa benchmark |
| `GET` | `/admin/evaluation/agent-evaluation/runs` | Lista relatórios |
| `GET` | `/admin/evaluation/agent-evaluation/runs/{run_id}/export` | Exporta relatório (json/csv/md) |

### Exemplo via curl

```bash
# Executar benchmark
curl -X POST "http://localhost:8000/admin/evaluation/agent-evaluation/runs?agent_id=<uuid>&model_name=gpt-4&benchmark=GAIA"

# Exportar relatório
curl "http://localhost:8000/admin/evaluation/agent-evaluation/runs/<run_id>/export?benchmark=GAIA&format=md"
```

## CI

### GitHub Actions

O workflow `agent-benchmarks.yml` executa os benchmarks via `workflow_dispatch`:

```yaml
inputs:
  benchmark:  # AgentBench, GAIA, BFCL, ou all
  agent_id:   # UUID do agente
  model_name: # Nome do modelo
```

Acionar manualmente:
```
gh workflow run agent-benchmarks.yml \
  -f benchmark=all \
  -f model_name=gpt-4
```

### Make target

```bash
make run-agent-benchmarks
# ou com variáveis de ambiente:
AGENT_EVAL_BENCHMARK=GAIA AGENT_EVAL_MODEL=gpt-4 make run-agent-benchmarks
```

## Dashboard

O Grafana dashboard "Agent Evaluation" (`monitoring/grafana/dashboards/agent-evaluation.json`) exibe:

- Success rate, tool efficiency, hallucination score (stats)
- Latência e success rate por benchmark (bar gauges)
- Runs over time (graph)
- Task result breakdown (pie chart)
- Latency heatmap
- Benchmark comparison

### Prometheus metrics

O framework expõe as seguintes métricas (quando configurado):

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `LLM_AGENT_EVAL_RUNS_TOTAL` | Counter | Total de runs |
| `LLM_AGENT_EVAL_TASKS_TOTAL{status}` | Counter | Total de tarefas por status |
| `LLM_AGENT_EVAL_SUCCESS_RATE` | Gauge | Taxa de sucesso |
| `LLM_AGENT_EVAL_TOOL_EFFICIENCY` | Gauge | Eficiência de tools |
| `LLM_AGENT_EVAL_LATENCY_MS` | Gauge | Latência média |
| `LLM_AGENT_EVAL_TOKEN_COST` | Gauge | Custo de tokens |
| `LLM_AGENT_EVAL_HALLUCINATION_SCORE` | Gauge | Score de alucinação |

## Testes

```bash
pytest tests/unit/services/test_agent_evaluation_framework.py -v
pytest tests/unit/api/test_agent_evaluation_api.py -v
```

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Evaluation                      │
├─────────────────────────────────────────────────────────┤
│  AgentEvaluationService                                  │
│  ├── list_benchmarks()    → Benchmarks disponíveis       │
│  ├── run_benchmark()      → Executa benchmark            │
│  ├── run_with_llm_harness() → Com LLM Harness            │
│  ├── _compute_metrics()   → Métricas                     │
│  └── _persist_report()    → Exporta relatórios           │
├─────────────────────────────────────────────────────────┤
│  BENCHMARK_TASKS                                         │
│  ├── AgentBench (8 tasks)                                │
│  ├── GAIA (8 tasks)                                      │
│  └── BFCL (8 tasks)                                      │
├─────────────────────────────────────────────────────────┤
│  API (admin_evaluation.py)                               │
│  └── /admin/evaluation/agent-evaluation/*                │
├─────────────────────────────────────────────────────────┤
│  Frontend (AgentEvaluation.tsx)                          │
│  └── /agents/evaluation                                  │
├─────────────────────────────────────────────────────────┤
│  Grafana Dashboard                                       │
│  └── agent-evaluation.json                               │
├─────────────────────────────────────────────────────────┤
│  CI (.github/workflows/agent-benchmarks.yml)             │
│  └── run-agent-benchmarks (make target)                  │
└─────────────────────────────────────────────────────────┘
```
