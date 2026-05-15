# Commercial Infrastructure Execution (Phase 22)

Allows the LLM Inference Stack to execute real infrastructure actions (like scaling) on Kubernetes and Nomad clusters after approval.

## Execution Modes

Controlled by `COMMERCIAL_INFRA_EXECUTION_MODE`:

1.  **`simulation_only` (Default)**: No real actions are executed. Only simulations are recorded.
2.  **`approval_required`**: Real actions are allowed but ONLY if they have a corresponding `CommercialApprovalRecord` with `status="approved"`.
3.  **`execute_opt_in`**: Real actions are allowed if they pass safety gates or have manual approval.

## Preconditions for Real Execution

For an action to be executed on real infrastructure (`dry_run=false`):

1.  `COMMERCIAL_INFRA_EXECUTION_ENABLED=true`
2.  `COMMERCIAL_INFRA_EXECUTION_MODE` must not be `simulation_only`.
3.  If `COMMERCIAL_INFRA_REQUIRE_APPROVAL=true`, an approved record is mandatory.
4.  If `COMMERCIAL_INFRA_REQUIRE_LEADER=true`, the node must be the current cluster leader.
5.  If `COMMERCIAL_INFRA_REQUIRE_FENCING=true`, a valid fencing token (lease ID) must be provided.
6.  `dry_run=false` must be explicitly passed in the request.
7.  `confirm=true` must be explicitly passed in the request.

## Adapters

### Mock Adapter
- Used for testing and validation.
- Always returns success.
- Simulates both execution and rollback.

### Kubernetes Adapter
- Supports scaling `Deployments` and `StatefulSets`.
- Requires `kubernetes` python library.
- Configuration:
    - `COMMERCIAL_K8S_EXECUTION_ENABLED=true`
    - `COMMERCIAL_K8S_NAMESPACE=default`
    - `COMMERCIAL_K8S_CONTEXT` (optional)

### Nomad Adapter
- Supports scaling jobs/task groups.
- Communicates via Nomad HTTP API.
- Configuration:
    - `COMMERCIAL_NOMAD_EXECUTION_ENABLED=true`
    - `COMMERCIAL_NOMAD_ADDR` (e.g., http://127.0.0.1:4646)
    - `COMMERCIAL_NOMAD_TOKEN` (optional)

## Rollback

Rollback can be initiated via `POST /admin/routing/infra/executions/{id}/rollback`.
- Mock adapter: Fully supports rollback.
- Kubernetes/Nomad: Basic support, may require manual intervention if the previous state is complex.

## Security

- **Secrets**: No tokens or kubeconfigs are logged.
- **Audit**: All actions are recorded in `AdminActionLog` with sanitized payloads.
- **Blast Radius**: Executions are checked against blast radius policies.

## Troubleshooting

- **Blocked Execution**: Check safety gate status, approval status, and leader election.
- **Adapter Unavailable**: Verify library installation and environment variables.
- **Dry Run Default**: Remember that `dry_run=true` is the default for all adapters unless explicitly overridden.
