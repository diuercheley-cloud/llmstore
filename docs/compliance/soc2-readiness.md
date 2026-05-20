# SOC 2 Readiness Guide

O `llm-inference-stack` auxilia na prontidão para o SOC 2 (Type 1 e Type 2) através dos seguintes pilares:

## Security (Common Criteria)
- **Acesso Lógico**: Protegido por RBAC e PKI Attestation.
- **Operações**: Monitoradas via Dashboards de Observabilidade Visual.
- **Mudanças**: Protegidas por Release Gates e CI/CD hardening.

## Confidentiality
- **Data Boundaries**: Restrição de fluxo de dados sensíveis entre clusters.
- **Sanitização**: Filtros automáticos de PII e segredos em logs e evidências.

## Availability
- **Resiliência**: Validada via Chaos Engineering.
- **Backups**: Automatizados e testados.
