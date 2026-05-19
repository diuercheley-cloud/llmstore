# Security Questionnaire (Common Responses)

## Data Privacy
- **Does the system store prompt data?** Only if Audit Logging/Retention is enabled. Default is transient processing.
- **Is data encrypted in transit?** Yes, via mTLS between Control and Data planes.

## Infrastructure
- **Does it require internet access?** Optional. Can be air-gapped in Sovereign mode.
- **What OS permissions are needed?** Docker/K8s privileges for container management.

## Authentication
- **Does it support SSO?** Yes, via OIDC/LDAP integration in Enterprise mode.
- **How are API keys managed?** Encrypted in the Control Plane database; rotatable.

## Compliance
- **Is it SOC2/ISO compliant?** The software is designed to meet these controls, but compliance depends on the customer's deployment environment.
