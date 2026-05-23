# Debate Agents

Debate orchestration uses the power of conflicting perspectives to improve the quality of agentic solutions.

## Roles

- **Proposer**: Generates initial solutions or drafts.
- **Critic**: Analyzes proposals and identifies flaws, risks, or improvements.
- **Synthesizer**: Collects all proposals and critiques to produce a final, balanced output.

## Iteration

The debate process can run for multiple rounds (configured via `max_rounds`). In each round, proposers can refine their suggestions based on previous critiques.

## Governance

Tracing ensures that the entire reasoning process (who said what and when) is auditable.
Raw internal "criticisms" are usually sanitized before being presented to the final user.
