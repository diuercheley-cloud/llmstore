---
owner: platform-ops
status: consolidated
---

# Optimizer Tournaments

## Overview

The tournament system enables parallel evaluation of multiple prompt/policy/tool-selection candidates using a structured competition framework. Candidates are evaluated head-to-head with statistical scoring to determine the optimal configuration.

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `AGENT_OPTIMIZER_TOURNAMENTS_ENABLED` | `false` | Master toggle for tournament system |
| `AGENT_OPTIMIZER_PARALLEL_EVALS_ENABLED` | `false` | Enables concurrent candidate evaluation |
| `AGENT_OPTIMIZER_APPLY_WINNER_ENABLED` | `false` | Enables winner application to agent |

## Workflow

1. **Create Tournament** — Submit N candidates (prompt/policy/tool-selection)
2. **Run Tournament** — Evaluate all candidates in parallel (respecting concurrency limit)
3. **Review Results** — Inspect pairwise comparisons, scores, rankings, and confidence
4. **Approve Winner** — Explicit human approval required
5. **Apply Winner** — Promote winning candidate to the active agent definition

## Metrics Collected

- `success_rate` — Eval pass rate
- `latency_p50` / `latency_p95` — Median and tail latency
- `cost` — Execution cost
- `tool_error_rate` — Tool call failure rate
- `policy_denial_rate` — Policy denial occurrences
- `safety_failure_rate` — Safety regression detections

## Scoring & Penalties

The ranking algorithm applies penalties for regressions:

| Regression | Penalty |
|------------|---------|
| Safety failure | -0.50 |
| Cost spike (>10%) | -0.25 |
| Latency spike (>100ms) | -0.20 |
| Tool misuse (>5% error rate) | -0.15 |

## Safety Guards

- Winner never applies automatically
- Approval gate blocks promotion without explicit authorization
- Rollback point is captured before any changes
- Candidates with safety failures are automatically deprioritized

## API Endpoints

```
POST /admin/agents/{id}/optimization/tournaments
GET  /admin/agents/optimization/tournaments/{id}
POST /admin/agents/optimization/tournaments/{id}/run
POST /admin/agents/optimization/tournaments/{id}/approve-winner
POST /admin/agents/optimization/tournaments/{id}/apply-winner
```

## Database Tables

- `agent_optimization_tournaments` — Tournament metadata and status
- `agent_optimization_tournament_candidates` — Participants in each tournament
- `agent_optimization_tournament_results` — Aggregated scores and ranks
- `agent_optimization_pairwise_results` — Head-to-head comparison results
