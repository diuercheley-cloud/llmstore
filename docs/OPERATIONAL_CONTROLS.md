---
owner: platform-ops
status: consolidated
---

# Operational Controls

Os `Operational Controls` adicionam governança operacional auditável inspirada em controles SOC2-style, sem declarar certificação oficial. O objetivo é manter biblioteca de controles, ownership, revisões periódicas, SLA de evidências, score de efetividade, linkage de exceções e trilha auditável para operação contínua.

## Control Library

- `CommercialOperationalControl` mantém `control_code`, categoria, owner, frequência de revisão, SLA de evidência, score e status de efetividade.
- Categorias suportadas: `security`, `availability`, `processing_integrity`, `confidentiality`, `privacy`, `financial`, `operational`.
- Todos os campos textuais e `metadata_json` são sanitizados para evitar secrets, prompts ou respostas brutas.

## Effectiveness Scoring

O score é calculado em `control_plane/app/services/compliance/operational_controls.py` a partir de cinco sinais:

- reviews fora do prazo
- evidence freshness (`fresh`, `stale`, `expired`)
- open exceptions e repeated exceptions vinculadas
- failed attestations globais
- unresolved financial mismatches

Faixas:

- `>= 90`: `effective`
- `50-89`: `partially_effective`
- `< 50`: `ineffective`

Esse score é operacional, não certificatório.

## Evidence Freshness

- `fresh`: evidência dentro do SLA
- `stale`: evidência perto do vencimento do SLA
- `expired`: SLA vencido ou `expires_at` passado

`refresh_evidence_status(...)` recalcula o status usando `evidence_sla_days` do controle.

## Reviews

- Cada controle gera revisão pendente automática na criação.
- Revisões seguem `monthly`, `quarterly`, `semiannual` ou `annual`.
- Revisões podem ser atribuídas a reviewer e concluídas com findings, recommendations e referência opcional a evidence package.
- Revisões vencidas mudam para `overdue`.

## Escalation

Controles operacionais integram com o mecanismo de escalations dry-run existente para:

- `stale_evidence`
- `overdue_review`
- `ineffective_control`
- `repeated_exceptions`

Saídas:

- internal escalation via audit log
- webhook dry-run
- email dry-run

Não há dependência de SaaS externo para o fluxo base.

## Exception Linkage

`CommercialOperationalExceptionLink` conecta `CommercialControlException` a `CommercialOperationalControl` e expõe:

- remediation progress
- linkage reason
- unresolved exception impact no effectiveness score

No portal enterprise, a visibilidade é tenant-scoped pela cadeia `CommercialOperationalExceptionLink -> CommercialControlException.client_id`.

## Enterprise Portal

O portal enterprise agora pode expor:

- controles operacionais visíveis ao tenant
- evidências operacionais do tenant
- revisões operacionais do tenant
- score/status de efetividade
- linked exceptions

Tudo permanece sanitizado e sem secrets.

## Limitations

- Isso não representa certificação SOC2 oficial.
- Os controles são inspirados em práticas operacionais auditáveis, não em uma opinião formal de auditoria.
- O portal enterprise só mostra controles operacionais vinculados a exceções do tenant para preservar escopo.
