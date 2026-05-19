# On-Prem Enterprise Pack

## Scope
Full production deployment of the LLM Inference Stack within customer-managed infrastructure.

## Requirements
- Multi-node GPU Cluster (High Availability)
- Kubernetes or Docker Swarm environment
- Persistent Storage (S3-compatible or local NVMe)
- Enterprise Linux OS

## Inclusions
- Unlimited Data Plane nodes
- High Availability Control Plane
- Enterprise RBAC & Audit Logs
- Hardware Attestation Support
- Advanced Routing & Load Balancing
- Training for Admin Team

## Exclusions
- Hardware procurement
- OS-level maintenance
- Data migration from legacy systems

## Prerequisites
- Signed Master Service Agreement (MSA)
- Dedicated Technical Account Manager (TAM) assigned

## SLA/SLO (Suggested)
- Availability: 99.9%
- P1 Response: 1 Hour
- P2 Response: 4 Hours

## Checklist de Entrega
- [ ] HA Cluster Validation
- [ ] HSM/TPM Integration (if applicable)
- [ ] LDAP/OIDC Integration
- [ ] Disaster Recovery Plan Verified
- [ ] Performance Benchmark Report

## Critérios de Aceitação
- Uptime sustained over 72 hours
- Sub-100ms overhead on routing
- Audit logs capturing all admin actions

## Riscos
- Internal network complexity
- Resource contention on shared hardware

## Matriz RACI
- Infra Maintenance: Customer (R)
- Software Updates: Provider (R)
- Security Audit: Customer/Provider (C)
