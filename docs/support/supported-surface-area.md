# Supported Surface Area - Agentic AI Platform

## Graduate Capabilities (v2.2.0-GA-Hardening)

The following capabilities have been hardened and promoted to higher support tiers.

| Capability | Status | Support Level | Readiness |
|------------|--------|---------------|-----------|
| Agent Code Sandbox | production_optional | production | GA Hardening |
| Agent Memory (RTBF) | production_core | production | Production |
| Agent Marketplace | production_core | production | Supply Chain GA |
| MCP client/server | beta | pilot | Policy Enforcement |
| Multi-Agent Topologies| beta | pilot | Governance GA |

## Readiness Criteria for production_core
1. **No Mocking**: Simulated success paths are blocked in production environments.
2. **Policy Enforcement**: Comprehensive tenant isolation and RBAC.
3. **Audit Trail**: Every critical action generates a persistent audit event.
4. **Verified Logic**: Automated test suites (`make *-ga-test`) covering compliance and security.
5. **Documentation**: Clear operational and security guides.

Refer to `config/supported-surface.yaml` for the complete list of capabilities and their current status.
