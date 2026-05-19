# Pilot Pack

## Scope
Limited duration evaluation (typically 30-90 days) of the LLM Inference Stack in a non-production or sandbox environment.

## Requirements
- 1x GPU Node (minimum 24GB VRAM for 7B models)
- Linux (Ubuntu 22.04+ recommended)
- Docker & Docker Compose
- Network access for control plane (internal or external)

## Inclusions
- Control Plane (Sandbox license)
- Up to 2 Data Plane instances
- Access to Model Inventory (Standard)
- Basic Onboarding Support (4 hours)
- Standard documentation

## Exclusions
- Production usage rights
- High Availability (HA) configuration
- Hardware Attestation (unless specifically requested/available)
- 24/7 Support
- Custom model fine-tuning

## Prerequisites
- Customer provided infrastructure
- Security clearance for software installation

## SLA/SLO (Suggested)
- Availability: 95% (Best effort)
- Response Time: NBD (Next Business Day)

## Checklist de Entrega
- [ ] Environment Provisioned
- [ ] Control Plane Installed
- [ ] Data Plane Connected
- [ ] Hello World Model Inference Validated
- [ ] Dashboard Access Granted

## Critérios de Aceitação
- System up and running
- At least one model performing inference
- Latency within 2x of baseline

## Riscos
- Infrastructure instability
- Network latency to external providers (if used)

## Matriz RACI
- Provisioning: Customer (R), Provider (A)
- Installation: Provider (R), Customer (A)
- Testing: Customer (R), Provider (A)
