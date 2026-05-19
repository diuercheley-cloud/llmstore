PLUGIN_TYPES = frozenset({
    "provider_adapter",
    "billing_adapter",
    "rag_processor",
    "observability_exporter",
    "auth_provider",
    "compliance_policy",
    "ui_extension",
})

ALLOWED_PERMISSIONS = frozenset({
    "read_data",
    "write_data",
    "network_out",
    "execute_sandbox",
    "read_config",
    "write_config",
    "read_logs",
    "write_logs",
    "read_metrics",
    "write_metrics",
    "access_secrets",
    "access_audit",
})

PLUGIN_PERMISSION_DESCRIPTIONS = {
    "read_data": "Read inference request/response data",
    "write_data": "Write inference request/response data",
    "network_out": "Make outbound network requests",
    "execute_sandbox": "Execute code within sandbox",
    "read_config": "Read system configuration",
    "write_config": "Write system configuration",
    "read_logs": "Read system logs",
    "write_logs": "Write system logs",
    "read_metrics": "Read system metrics",
    "write_metrics": "Write system metrics",
    "access_secrets": "Access secret/credential storage",
    "access_audit": "Access audit trail",
}
