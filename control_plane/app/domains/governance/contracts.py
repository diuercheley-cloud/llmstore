PUBLIC_CONTRACTS = (
    "deterministic_policy_contract",
    "governance_workflow_contract",
)


class GovernanceDomainContract:
    allowed_inputs = (
        "deterministic policy definitions",
        "approval workflow intents",
        "governance review requests",
        "compliance evidence metadata",
    )
    emitted_events = (
        "governance.policy.published",
        "governance.review.requested",
        "governance.approval.recorded",
        "governance.conflict.detected",
    )
    forbidden_dependencies = (
        "app.domains.financial",
        "app.domains.operations",
    )
    deterministic_requirements = (
        "must remain replay-safe",
        "must not use eval or exec",
        "must support offline-first governance decisions",
        "must expose cross-domain access through contracts and events only",
    )
