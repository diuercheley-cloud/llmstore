# Canary Rollout Strategy

Agents support gradual traffic shifting between different definition versions (Canaries).

## Traffic Distribution

The `CanaryRunner` handles request-level routing decisions.

| Mode | Traffic % | Description |
| :--- | :--- | :--- |
| Initial | 5% | Baseline safety observation. |
| Observation | 25% | Performance and cost metrics aggregation. |
| Promotion | 100% | Full migration after approval. |

## Automatic Termination

The rollout is automatically terminated and rolled back if:
1.  **Safety Failure:** Any detected safety violation (e.g. data leak attempt).
2.  **Cost Breach:** Average cost increase exceeds 20% compared to baseline.
3.  **Latency Breach:** p95 latency increase exceeds 50%.
4.  **Policy Denial:** Spike in unauthorized tool access attempts.

## Evidence Collection

Every canary run generates a comprehensive evidence report including:
*   Differential trace logs.
*   Token usage distribution.
*   Tool invocation success/failure heatmap.
