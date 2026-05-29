---
owner: platform-ops
status: consolidated
---

# Enterprise Policy-as-Code Governance

This framework provides a declarative way to manage governance across the LLM inference stack. It allows administrators to define, version, simulate, and enforce policies for routing, billing, QoS, and more.

## Architecture

The governance framework consists of:
- **Policy Registry**: Manages the lifecycle of policy bundles (draft, published, active, deprecated).
- **Policy Engine**: Evaluates rules, simulates impact, and detects drift between declared policies and runtime state.
- **Rule Bundles**: JSON-based declarative configurations for different aspects of the system.
- **Signed Artifacts**: Immutable snapshots of policies and their evaluation results.

## Policy Lifecycle

1. **Draft**: Create a new policy bundle.
2. **Published**: Mark a bundle as ready for review. This generates a signature.
3. **Active**: Activate the bundle. This replaces any previous active bundle of the same type.
4. **Deprecated**: Automatically set when a newer bundle is activated.
5. **Rolled Back**: Revert to a previous stable version.

## Rule Bundle Format

```json
{
  "routing": {
    "force_local_only": true,
    "restricted_models": ["gpt-5-ultra"],
    "max_cost_per_request_brl": 0.50
  },
  "billing": {
    "wallet_debit_enabled": false
  },
  "qos": {
    "max_priority": 3
  }
}
```

## Modes

- **Disabled**: Policy is ignored.
- **Dry Run**: Rules are evaluated and logged, but not enforced at runtime.
- **Enforce**: Rules are strictly enforced.

## Drift Detection

The system periodically checks if the runtime configuration matches the active policy bundle. If a discrepancy is found, a `CommercialPolicyDriftEvent` is generated.

Possible drift types:
- `config_drift`: Runtime config differs from policy.
- `runtime_override`: Manual override detected.
- `missing_rule`: Active policy missing required rules.
- `stale_bundle`: Active bundle is outdated.

## Security & Integrity

All published bundles are signed using a SHA256 hash of the rules and an internal secret. This ensures that policies cannot be tampered with outside the registry workflow.

## API Reference

### List Policies
`GET /admin/governance/policies`

### Create Policy
`POST /admin/governance/policies`

### Publish Policy
`POST /admin/governance/policies/{id}/publish`

### Activate Policy
`POST /admin/governance/policies/{id}/activate`

### Simulate Policy
`POST /admin/governance/policies/{id}/simulate`

### Detect Drift
`POST /admin/governance/policies/drift/detect`
