# Sovereign AI Appliance Pack

## Scope
Turnkey hardware+software solution for maximum data sovereignty and air-gapped capabilities.

## Requirements
- Certified Hardware Appliance (provided or specified)
- Physical security for the device
- Air-gap compatible update mechanism

## Inclusions
- Pre-installed LLM Inference Stack
- Optimized Model Weights (Local)
- Local PKI and Root of Trust
- Offline Tokenizer and RAG capabilities
- Physical Security Tamper Detection (Advisory)

## Exclusions
- Cloud connectivity (by design)
- External model API access (unless bridged)

## Prerequisites
- Physical space in secure datacenter
- Dedicated power and cooling

## SLA/SLO (Suggested)
- Hardware Availability: 99.95% (Hardware vendor backed)
- Software Availability: 99.9%

## Checklist de Entrega
- [ ] Hardware Physical Inspection
- [ ] Secure Boot Validation
- [ ] Local Model Loading Speed Test
- [ ] Air-gap Sync Verification

## Critérios de Aceitação
- Zero external network calls detected
- Successful inference from local-only weights
- Secure vault encryption verified

## Riscos
- Supply chain for hardware
- Physical access security

## Matriz RACI
- Physical Security: Customer (R)
- Software Stack: Provider (R)
- Model Updates: Provider (R/C)
