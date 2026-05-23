# Mock vs Dry-Run Execution Modes

When operating the Agent Platform, it is crucial to understand the difference between **Mock Mode** and **Dry-Run Mode**.

## Mock Mode
**Configuration**: `AGENT_TASK_MOCK_MODE=true`

Mock mode bypasses execution logic entirely. When a task is evaluated in Mock Mode, the system does not attempt to instantiate providers, build arguments, or call tools. It immediately returns a fast, deterministic static placeholder object.

- **Primary use case**: Fast unit testing of orchestration logic and state machines where the actual tool behaviors and dependencies are irrelevant.
- **Output Characteristics**: Outputs will explicitly contain `{"status": "mock", "mock": true, "execution_mode": "mock"}`.
- **Side effects**: None. No actual tool logic is reached.

## Dry-Run Mode
**Configuration**: `AGENT_TASK_DRY_RUN_MODE=true`

Dry-run mode deeply traverses the execution paths. It retrieves real configurations, evaluates security policies, prepares parameters, and calls the tool executor. The tool executor runs in a state that explicitly forbids mutations or external destructive side effects, but it may evaluate read-only paths to generate simulated outputs that reflect real schemas and behaviors.

- **Primary use case**: Pre-execution validation, policy auditing, and integration testing without risking destructive side effects.
- **Output Characteristics**: Outputs will explicitly contain `{"status": "simulated", "dry_run": true, "execution_mode": "dry_run"}`.
- **Side effects**: Blocked at the execution layer. Tools explicitly handle `is_dry_run=True` to simulate success without performing actual writes.