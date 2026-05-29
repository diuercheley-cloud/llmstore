# Multi-Agent Arbitration Engine

> Owner: agent-platform | Status: Active

The Multi-Agent Arbitration Engine resolves output conflicts between agents and synthesizes final governed responses using critic reviewer agents, structured scoring, and receipt tracking.

## Architecture

The arbitration engine takes candidate responses from multiple agents, subjects them to structured criteria evaluation (with optional critic review), scores them, selects a winning candidate (or fails if all are disqualified), and generates a final synthesis with a decision receipt.

```
                  Specialists / Proposers (Candidates)
                                  │
                                  ▼
                          ArbitrationEngine
                                  ├─ Candidate Parsing
                                  ├─ Critic Review (Mock or LLM-based)
                                  ├─ Structured Scoring (8 criteria)
                                  ├─ Safety & Evidence Verification
                                  └─ Receipt Generation (UUID + scores)
                                  │
                                  ▼
                           Final Synthesis
                    (Citations + Receipt Tracking)
```

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `AGENT_MULTI_AGENT_ARBITRATION_ENABLED` | `false` | Master toggle to enable arbitration engine. |
| `AGENT_MULTI_AGENT_CRITIC_REVIEW_ENABLED` | `false` | Enable calling critic reviewer LLMs via the model provider. |
| `AGENT_MULTI_AGENT_MOCK_ARBITRATION` | `false` | Bypass real LLM calls and return structured mock scores for testing. |

> [!IMPORTANT]
> Simple heuristic-only arbitration is disabled in production by default. When the flags are off, attempting to call the arbitrator will raise a `PermissionError` unless mock mode is explicitly enabled.

## Structured Scoring

Every candidate is evaluated against 8 criteria on a scale of `0.0` to `1.0`:
1. **Correctness**: Semantic accuracy of the generated result.
2. **Completeness**: Addressing all facets of the query.
3. **Tool Evidence**: Presence and quality of tool executions supporting the claim.
4. **Policy Compliance**: Adherence to system and tenant policies.
5. **Cost**: Budget optimization.
6. **Latency**: Responsiveness of the agent.
7. **Confidence**: Self-reported or evaluated confidence.
8. **Safety**: Risk and security audit pass rate.

The overall score is a weighted sum:
$$\text{Score} = 0.2 \times \text{Correctness} + 0.15 \times \text{Completeness} + 0.15 \times \text{Tool Evidence} + 0.1 \times \text{Policy Compliance} + 0.1 \times \text{Cost} + 0.1 \times \text{Latency} + 0.1 \times \text{Confidence} + 0.1 \times \text{Safety}$$

### Governance and Disqualification Rules

* **Safety Disqualification**: If a candidate fails safety validation (`safety_passed=False` or safety score `< 0.5`), its final score is set to `0.0` immediately.
* **Tool Evidence Disqualification**: If there is at least one candidate in the arbitration case that has tool evidence (tool calls or evidence text), any candidate without tool evidence is immediately disqualified (score is set to `0.0`).

## Decision Receipts

Every arbitration decision generates a rich, cryptographically traceable receipt including:
- `receipt_id`: Unique transaction identifier.
- `case_id`: The ID of the specific arbitration case.
- `timestamp`: Execution time.
- `scores`: Individual candidate final scores.
- `conflicts`: Detected conflicts.
- `reasoning`: The explanation of why the winner was chosen.

## Testing

Verify the arbitration functionality with:
```bash
pytest control_plane/tests/test_arbitration_engine.py -v
```
