# Security Appendix

## 1. Shared Responsibility Model
- **Provider:** Responsible for the security OF the software (vulnerabilities, encryption logic).
- **Customer:** Responsible for the security IN the software (user access, network perimeter, hardware security).

## 2. Security Controls
- **Encryption:** All data in transit is encrypted via TLS 1.3+.
- **Authentication:** Mandatory RBAC for all administrative actions.
- **Auditing:** Immutable audit logs generated for all API calls.

## 3. Vulnerability Management
- Critical patches will be released within [N] hours of disclosure.
- Customer must apply patches within [N] days to maintain SLA.
