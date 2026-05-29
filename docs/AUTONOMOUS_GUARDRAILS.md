---
owner: platform-ops
status: consolidated
---

# Autonomous Guardrails

O módulo de Autonomous Guardrails impede ações autônomas perigosas antes de qualquer execução material. O fluxo é determinístico e offline-capable:

`approval -> execute -> receipt -> verify`

## Componentes

- `CommercialAutonomousExecutionPolicy`: política ativa por tipo de ação, tenant e janela guardada.
- `CommercialExecutionBlastRadius`: cálculo reproduzível do impacto potencial.
- `CommercialHumanApprovalCheckpoint`: checkpoints multi-stage com segregação e trilha auditável.
- `CommercialExecutionGuardrailEvent`: decisão bloqueada, pendente ou permitida com hash imutável.
- `CommercialAutonomousExecutionReceipt`: receipt encadeado com `previous_receipt_hash`.

## Enforcement

Toda ação automática valida:

- bundle de policy ativo
- approval chain
- runtime trust state
- restrições sovereign
- tenant isolation
- quorum do runtime fabric
- hardware attestation
- confidential runtime
- assinatura de model promotion

Bloqueios automáticos:

- `destructive_replay`
- `unrestricted_tenant_quarantine`
- `unrestricted_federation_sync`
- `unsafe_rollback`
- `confidential_runtime_bypass`
- `model_promotion` sem assinatura

## Trust Graph

Os guardrails entram no Trust Graph com nós derivados para:

- políticas autônomas
- blast radius
- approval checkpoints
- guardrail events
- receipts autônomos

As arestas registram `approval_chain`, `governance_binding`, `receipt_chain`, `dependency_integrity`, `runtime_trust_propagation` e `lineage`.

## APIs

- `/admin/guardrails/status`
- `/admin/guardrails/checkpoints`
- `/admin/guardrails/blast-radius`
- `/admin/guardrails/violations`
- `/admin/guardrails/receipts`

## Restrições

- nenhuma ação destrutiva automática
- sem auto-delete
- sem bypass manual oculto
- toda ação precisa de receipt auditável
- sem dependência SaaS
- compatível com air-gap e operação 100% offline
