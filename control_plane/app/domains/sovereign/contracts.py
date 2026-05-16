PUBLIC_CONTRACTS = (
    "sovereign_boundary_contract",
    "airgap_control_contract",
)


class SovereignDomainContract:
    allowed_inputs = (
        "airgap package intents",
        "sovereign export policies",
        "locality governance constraints",
        "regional sovereignty declarations",
    )
    emitted_events = (
        "sovereign.boundary.confirmed",
        "sovereign.airgap.export.blocked",
        "sovereign.locality.reviewed",
        "sovereign.governance.snapshot.recorded",
    )
    forbidden_dependencies = (
        "app.domains.financial",
        "app.domains.operations",
    )
    deterministic_requirements = (
        "must remain offline-first",
        "must not claim hardware-backed trust",
        "must avoid mandatory cloud dependencies",
        "must keep sovereignty controls explicit and deterministic",
    )
