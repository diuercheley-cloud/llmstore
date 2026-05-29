---
owner: platform-ops
status: consolidated
---

# Auto-Optimization and Optimizer Coordination

The Auto-Optimization service utilizes historical execution runs and evaluation failures to generate candidate optimizations for agents, evaluates them against baselines, and presents recommendations to administrators for approval.

## Feature Flags

Auto-optimization is strictly opt-in and is disabled by default. Configure the following flags in your environment/config:

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_AUTO_OPTIMIZATION_ENABLED` | `false` | Enables the general auto-optimization lifecycle and evaluation. |
| `AGENT_DSPY_OPTIMIZER_ENABLED` | `false` | Enables candidate generation using a DSPy-like optimizer module. |
| `AGENT_AUTO_PROMOTE_OPTIMIZATIONS` | `false` | If enabled, attempts auto-promotion (still blocked by safety checks). |
| `AGENT_OPTIMIZATION_APPLY_ENABLED` | `false` | Enables the promotion/application of candidates to active agent definitions. |

## End-to-End Optimization Flow

The optimization system follows a strict structured pipeline:

1. **Failure Collection**: Scans past evaluation suites and agent runs for failures (e.g. tool exceptions, safety policy denials, prompt formatting issues).
2. **Candidate Generation**: Generates refined candidates across three areas:
   - **Prompts**: Refines instructions to include constraints targeting observed failures.
   - **Tool Selection**: Prunes/adjusts tool permissions based on tool errors.
   - **Policies**: Proposes rule updates to circumvent security denials gracefully.
3. **Candidate Evaluation**: Runs the evaluation suite on the candidate definitions.
4. **Baseline Comparison**: Compares candidate runs against the active agent baseline.
5. **Gate Verification**: Validates safety constraints and tracks delta improvements.
6. **Promotion Approval**: Candidates are never applied to production without explicit administrator approval.

## Key Metrics Evaluated

Every optimization experiment calculates the following delta metrics (`candidate - baseline`):

* **`eval_pass_rate_delta`**: The change in percentage of evaluation cases passing (higher is better).
* **`cost_delta`**: The estimated execution/token cost change (lower/negative is better).
* **`latency_delta`**: The change in response latency (lower/negative is better).
* **`tool_error_delta`**: Change in count of tool invocation exceptions (lower/negative is better).
* **`policy_denial_delta`**: Change in security rule block events.
* **`safety_failure_delta`**: Regressions in safety or leak validations. If `safety_failure_delta > 0`, the candidate is immediately blocked.

## API Administration Endpoints

The control plane exposes the following REST endpoints under the `/admin/agents` prefix:

### 1. Trigger Optimization Experiment
`POST /admin/agents/{id}/optimization/experiments`
- Analyzes agent runs and evaluation failures.
- Generates prompt, tool selection, and policy candidates.

### 2. List Optimization Candidates
`GET /admin/agents/{id}/optimization/candidates`
- Retrieves all candidates generated for a given agent.

### 3. Evaluate Candidate
`POST /admin/agents/{id}/optimization/candidates/{candidate_id}/eval`
- Triggers the evaluation suite for a candidate.
- Compares results with baseline and computes delta metrics.

### 4. Approve Candidate
`POST /admin/agents/{id}/optimization/candidates/{candidate_id}/approve`
- Manually approves a candidate, transitioning its status to `approved`.
- Required step before applying any candidate.

### 5. Apply Candidate (Promote)
`POST /admin/agents/{id}/optimization/candidates/{candidate_id}/apply`
- Promotes the candidate's changes to the active agent definition in production.
- Strictly validates that the candidate is approved and doesn't trigger safety regressions.
