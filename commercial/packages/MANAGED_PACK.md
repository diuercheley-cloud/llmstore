# Managed Control Plane Pack

## Scope
SaaS-style control plane managed by the provider, with Data Planes running in the customer environment.

## Requirements
- Network connectivity to Provider's Control Plane API
- Customer-managed Data Plane nodes (GPU)

## Inclusions
- Hosted Management Dashboard
- Global Routing and Policy Engine
- Aggregated Analytics
- Automatic Updates for Control Plane
- Multi-region support

## Exclusions
- Data Plane infrastructure management
- Data Plane local security configuration

## Prerequisites
- Outbound HTTPS access to Provider API
- API Keys/mTLS certs for Data Plane

## SLA/SLO (Suggested)
- Control Plane API Availability: 99.95%
- Data Plane Latency: Impacted by network connectivity

## Checklist de Entrega
- [ ] Tenant Account Provisioned
- [ ] API Key Rotation Policy Set
- [ ] Data Plane Connection Established
- [ ] Regional Routing Rules Applied

## Critérios de Aceitação
- Successful cross-region failover test
- Dashboard displaying real-time Data Plane telemetry

## Riscos
- Internet connectivity dependency
- Shared control plane (Multi-tenant)

## Matriz RACI
- Control Plane Ops: Provider (R)
- Data Plane Ops: Customer (R)
- Policy Definition: Customer (R)
