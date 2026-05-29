---
owner: platform-ops
status: consolidated
---

# A/B Testing for Prompts

## Overview

The tournament framework supports A/B testing of prompt variants by treating each variant as a candidate. Prompts are evaluated against the same eval suite, and statistical scoring determines the winner.

## A/B Testing Workflow

### 1. Create Prompt Variants

Generate multiple prompt candidates using the existing optimizer:

```python
from app.services.agents.optimization.prompt_optimizer import PromptOptimizer
optimizer = PromptOptimizer()
variant_a = optimizer.optimize_prompt(original_instructions, failures)
variant_b = optimizer.optimize_prompt(original_instructions, failures, style="concise")
```

### 2. Create Tournament Candidates

Submit each variant as an `AgentOptimizationCandidate` with `candidate_type="prompt"`.

### 3. Run Tournament

The tournament evaluates all variants in parallel using the same eval suite and computes pairwise comparisons.

### 4. Analyze Results

The `confidence_score` indicates how confident the system is that the winner is statistically superior. A score above 0.75 suggests strong evidence.

## Pairwise Comparison

Each pair of candidates is compared directly:

```
score = success_rate * 10
      - latency_p50 / 1000
      - latency_p95 / 1000
      - cost * 5
      - tool_error_rate * 8
      - policy_denial_rate * 8
      - safety_failure_rate * 20
```

## Best Practices

- Run at least 3 candidates for meaningful comparisons
- Ensure eval suite has sufficient coverage to detect regressions
- Review pairwise results to understand tradeoffs between candidates
- Always approve the winner manually before applying
- Use the captured rollback point for safe revert if needed

## Limitations

- Statistical significance depends on eval suite quality and size
- Parallel execution may stress the eval infrastructure
- Confidence score is a heuristic, not a formal p-value
