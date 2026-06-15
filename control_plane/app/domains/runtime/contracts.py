"""Lightweight contract for the runtime domain."""


class RuntimeDomainContract:
    """Defines the stable contract surface for runtime modularization."""

    allowed_inputs = (
        "runtime execution requests",
        "routing decisions",
        "provider capability metadata",
        "workflow scheduling instructions",
        "local cache state",
    )
    emitted_events = (
        "runtime.execution.accepted",
        "runtime.execution.started",
        "runtime.execution.completed",
        "runtime.execution.failed",
        "runtime.capacity.updated",
    )
    forbidden_dependencies = (
        "app.domains.financial",
        "app.domains.sovereign",
    )
    deterministic_requirements = (
        "must operate without mandatory online control dependencies",
        "must keep replay-sensitive execution paths deterministic",
        "must not require direct imports from other domain contracts",
        "must preserve existing app.* imports while modularization is incremental",
    )
