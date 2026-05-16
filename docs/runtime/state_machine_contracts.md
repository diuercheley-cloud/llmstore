# State Machine Contracts

## Execution State Machine

### Estados

- `submitted`
- `validated`
- `policy_checked`
- `scheduled`
- `executing`
- `checkpointed`
- `completed`
- `failed`
- `repaired`
- `replayed`

### Contrato

Estado inicial:
- `submitted`

Estados terminais:
- `completed`
- `failed`

Estados de recuperacao:
- `repaired`
- `replayed`

Transicoes validas:
- `submitted -> validated`
- `validated -> policy_checked`
- `policy_checked -> scheduled`
- `scheduled -> executing`
- `executing -> checkpointed`
- `checkpointed -> executing`
- `executing -> completed`
- `executing -> failed`
- `failed -> repaired`
- `failed -> replayed`
- `repaired -> replayed`
- `replayed -> completed`
- `replayed -> failed`

## Workflow State Machine

### Estados logicos

- `dag_created`
- `dag_hashed`
- `policy_gated`
- `checkpoint_created`
- `paused`
- `resumed`
- `rolled_back`
- `replay_validated`

### Contrato

- `dag_created -> dag_hashed`
- `dag_hashed -> policy_gated`
- `policy_gated -> checkpoint_created`
- `checkpoint_created -> paused`
- `paused -> resumed`
- `checkpoint_created -> rolled_back`
- `rolled_back -> replay_validated`
- `resumed -> replay_validated`

## Receipt State Machine

### Estados logicos

- `receipt_created`
- `immutable_hash_computed`
- `sha256_chained`
- `signature_placeholder_attached`
- `verified`
- `export_restricted`

### Contrato

- `receipt_created -> immutable_hash_computed`
- `immutable_hash_computed -> sha256_chained`
- `sha256_chained -> signature_placeholder_attached`
- `signature_placeholder_attached -> verified`
- `verified -> export_restricted`

Observacao:
- `signature_placeholder_attached` nao representa assinatura formal certificada

## Governance State Machine

### Estados logicos

- `policy_matched`
- `advisory_mode`
- `dry_run_mode`
- `approval_required`
- `enforcement`
- `incident_created`

### Contrato

- `policy_matched -> advisory_mode`
- `policy_matched -> dry_run_mode`
- `policy_matched -> approval_required`
- `approval_required -> enforcement`
- `enforcement -> incident_created`

Observacao:
- `incident_created` e derivado; nao substitui o ledger de governanca

## Repair State Machine

### Estados logicos

- `failure_detected`
- `recovery_plan_created`
- `deterministic_repair_started`
- `signed_healing_receipt_emitted`
- `replay_verified`

### Contrato

- `failure_detected -> recovery_plan_created`
- `recovery_plan_created -> deterministic_repair_started`
- `deterministic_repair_started -> signed_healing_receipt_emitted`
- `signed_healing_receipt_emitted -> replay_verified`

## Limitacoes

- estes contratos descrevem comportamento normativo e esperado
- eles nao constituem prova formal de corretude
- nenhuma secao deve ser interpretada como claim de certificacao formal ou hardware attestation real
