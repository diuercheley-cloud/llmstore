# SOC 2 Readiness Guide

O `llm-inference-stack` auxilia na prontidão para o SOC 2 (Type 1 e Type 2) através dos seguintes pilares:

## Security (Common Criteria)
- **Acesso Lógico**: Protegido por RBAC. *Nota: O recurso de PKI Attestation opera em modo advisory-only por padrão e não é considerado um controle obrigatório certificado.*
- **Operações**: Monitoradas via Dashboards de Observabilidade Visual.
- **Mudanças**: Protegidas por Release Gates e CI/CD hardening.

## Confidentiality
- **Data Boundaries**: Restrição de fluxo de dados sensíveis entre clusters.
- **Sanitização**: Filtros automáticos de PII e segredos em logs e evidências.

## Availability
- **Resiliência**: Validada via Chaos Engineering.
- **Backups**: Automatizados e testados.

> [!IMPORTANT]
> Controles classificados como **advisory** (como PKI, Attestation e Hardware Trust) ou **placeholder** são estritamente informativos. Para fins de auditorias SOC 2, eles não devem ser tratados como controles certificados (certified) ou aplicados obrigatoriamente (enforced).
