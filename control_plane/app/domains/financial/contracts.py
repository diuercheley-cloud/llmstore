PUBLIC_CONTRACTS = (
    "financial_control_contract",
    "billing_governance_contract",
)


class FinancialDomainContract:
    allowed_inputs = (
        "billing policy inputs",
        "chargeback records",
        "financial reconciliation requests",
        "invoice governance status",
    )
    emitted_events = (
        "financial.control.evaluated",
        "financial.chargeback.recorded",
        "financial.reconciliation.updated",
        "financial.governance.blocked",
    )
    forbidden_dependencies = (
        "app.domains.governance",
        "app.domains.operations",
        "app.domains.sovereign",
    )
    deterministic_requirements = (
        "must preserve tenant isolation",
        "must keep financial policy evaluations deterministic",
        "must avoid direct runtime orchestration dependencies",
        "must keep modular boundaries explicit",
    )
