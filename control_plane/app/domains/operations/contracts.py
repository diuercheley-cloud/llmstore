PUBLIC_CONTRACTS = (
    "deterministic_event_contract",
    "recovery_plan_contract",
)


class OperationsDomainContract:
    allowed_inputs = (
        "deterministic operational events",
        "observability records",
        "recovery planning inputs",
        "replay verification requests",
    )
    emitted_events = (
        "operations.event.recorded",
        "operations.timeline.built",
        "operations.recovery.verified",
        "operations.observability.sanitized",
    )
    forbidden_dependencies = (
        "app.domains.governance",
        "app.domains.sovereign",
    )
    deterministic_requirements = (
        "must keep event lineage deterministic",
        "must not require external brokers",
        "must remain safe for offline replay verification",
        "must not introduce real recovery execution in Phase 82",
    )
