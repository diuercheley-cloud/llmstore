# Critic Review System

> Owner: agent-platform | Status: Active

The Critic Review system coordinates specialized critic agents to review proposals, candidate responses, and synthesized outputs for safety, alignment, and quality before they are finalized.

## Critic Topology

Critics are integrated into topologies like the **Debate Runtime** (Proposers -> Critics -> Synthesizer) or as an overlay on the **Hierarchical Runtime** (Manager -> Specialists -> Critics -> Manager Synthesis).

During execution, the arbitrator invokes critic agents, evaluates their critiques, and computes structured criteria scores for candidate proposals.

```
       Proposers / Specialists
                  │
                  ├───────────► Critic Reviews ──┐
                  ▼                              ▼
          Arbitration Case ───────────────► Decision Logic ──► Synthesized Output
```

## Critic Review Policies and Budgets

To ensure safety and resource control, critics operate under strict policy guidelines:

### 1. Critic Budget Limits
Every critic review runs against a dedicated budget limit defined in the run context:
* Default critic budget is set to `0.05` BRL.
* Exceeding the budget limits prompts a warning or rejects model invocation to prevent run cost escalation.

### 2. Privacy & Raw Prompt Redaction
To protect sensitive tenant details and instructions:
* Critic agents are governed by the `allow_raw_prompt` context rule.
* If `allow_raw_prompt = False`, the raw system goal/query is automatically redacted and replaced with a generic identifier (`[REDACTED: Input contains sensitive parameters]`) before reaching the reviewer agent.

## Execution Modes

### Mock Critic Reviews
When `AGENT_MULTI_AGENT_MOCK_ARBITRATION=true`, the engine generates deterministic scores and reviews based on candidate metadata fields like `safety_passed` and latency.

### Real Critic Reviews via LLM
When `AGENT_MULTI_AGENT_CRITIC_REVIEW_ENABLED=true` and mock mode is off, the engine constructs structured prompts and queries the active LLM provider (using `GatewayAgentLLMProvider`).

The LLM is prompted to return a raw JSON payload following this schema:
```json
{
  "correctness": 0.95,
  "completeness": 0.90,
  "tool_evidence": 0.85,
  "policy_compliance": 1.0,
  "cost": 0.95,
  "latency": 0.90,
  "confidence": 0.90,
  "safety": 1.0,
  "reasoning": "Explanation of scores and observations.",
  "recommendation": "approve"
}
```

## Final Quality Check

Synthesized final answers undergo a final safety validation step via `run_critic_review`. The system checks if any critic rejected the response or if the final aggregated safety/quality score drops below a minimum threshold (`0.50`). Rejected syntheses are marked with a `[REJECTED]` suffix in the trace log.
