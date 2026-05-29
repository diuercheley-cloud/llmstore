# Continuous Promotion Pipeline

The Continuous Promotion Pipeline ensures that agentic optimizations (prompts, tool selection, etc.) are deployed to production safely and predictably.

## Workflow

1.  **Candidate Creation:** The `Optimizer` service generates a new agent definition candidate based on performance data.
2.  **Evaluation Phase:** The candidate is automatically run through the `AgentEvalService` suite.
    *   **Threshold:** Minimum 95% pass rate required.
3.  **Security Scan:** Automated checks for policy compliance and safety guardrails.
4.  **Canary Rollout:** Traffic is gradually shifted to the candidate definition (starting at 5%).
    *   **Metrics:** Success rate, Latency (p95), Cost per Run.
5.  **Human Approval:** Production promotion **always** requires manual approval from an authorized role (admin/tech-lead).
6.  **Gradual Promotion:** Traffic increases to 100% after successful canary observation.
7.  **Auto-Rollback:** If any SLO breach is detected (e.g., 50% latency increase), the `RollbackController` reverts to the previous stable state.

## Configuration

Promotion policies are defined in `config/agentic-promotion-policy.yaml`.

```yaml
promotion_thresholds:
  min_confidence_score: 0.85
  min_eval_pass_rate: 0.95
  max_cost_increase_percent: 10.0
```

## Rollback Points

Every promotion automatically creates a immutable snapshot of the previous state to ensure immediate and reliable rollback capability.
