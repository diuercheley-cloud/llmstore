---
owner: platform-ops
status: consolidated
---

# Commercial Compliance Controls

Fase 31 adiciona controles financeiros internos auditáveis inspirados em SOX para ações administrativas críticas. O objetivo é aumentar rastreabilidade, segregação de funções e evidência operacional. Não é certificação SOX oficial nem declaração de compliance regulatório.

## Objetivo

- criar trilha auditável para ações financeiras e operacionais críticas
- separar solicitante de aprovador quando exigido
- exigir múltiplos aprovadores quando a policy definir quorum
- gerar evidence packages sanitizados com before/after, actor, timestamp, related IDs e hash imutável
- suportar attestation mensal, trimestral ou anual
- registrar exceptions, aceite de risco e remediação
- exportar audit reports em `json`, `csv` e `html`

## Controles

Os controles são configurados via `CommercialControlPolicy` e cobrem estas áreas:

- `billing`
- `wallet`
- `qos_billing`
- `disputes`
- `reconciliation`
- `revenue_protection`
- `infra_execution`

Cada policy pode exigir:

- approval chain
- segregação de funções
- evidence package
- frequência de review

## Approval Chains

Quando uma policy exige aprovação, o sistema cria `CommercialApprovalChain`.

- Em `COMMERCIAL_COMPLIANCE_MODE=report_only`, a execução continua, mas a chain e a evidence são registradas.
- Em `COMMERCIAL_COMPLIANCE_MODE=enforce`, a ação retorna `pending_approval` e a execução direta é bloqueada até a aprovação.

Regras:

- o requester não pode ser o único aprovador
- se `segregation_required=true`, `requester != approver`
- se `required_approver_count > 1`, a chain só fecha como `approved` após N aprovadores distintos

## Segregation Of Duties

Segregação de funções foi aplicada nos fluxos críticos:

- manual credit
- QoS wallet debit manual
- dispute com crédito
- reconciliation resolved
- revenue protection apply
- infra execution real
- report email real send

## Evidence Packages

Os evidence packages incluem:

- before state
- after state
- actor
- timestamp
- related IDs
- payload sanitizado
- immutable hash

Nunca são persistidos:

- API keys
- prompts
- responses
- provider secrets
- SMTP secrets

## Attestations

Endpoints administrativos permitem:

- listar controles que precisam review
- criar attestation mensal, trimestral ou anual
- anexar evidence package
- marcar failure/exception e abrir exception automaticamente

## Exceptions

`CommercialControlException` suporta:

- abertura manual
- aceite de risco
- remediation plan
- remediação
- export via audit report

## Modos

- `disabled`: desliga os controles
- `report_only`: observa e registra sem bloquear o fluxo
- `enforce`: exige approval chain quando a policy pedir aprovação

Default:

- `report_only`

## Limites

- não substitui revisão jurídica, auditoria externa ou programa formal SOX
- não depende de fornecedor externo
- não deve expor segredos em evidence, export ou email
- não tenta declarar conformidade SOX oficial
