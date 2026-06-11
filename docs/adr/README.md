---
owner: platform-ops
status: consolidated
---

# ADRs

Este diretorio centraliza Architectural Decision Records da plataforma.

## Objetivo

- registrar decisoes arquiteturais de forma rastreavel
- explicitar trade-offs de seguranca, offline compatibility e determinismo
- apoiar modularizacao e evolucao sem depender de memoria implita

## Convencao

Cada ADR usa numeracao sequencial.

ADRs legados `0001` a `0006` preservam a estrutura original:

- `Status`
- `Context`
- `Decision`
- `Consequences`
- `Security Notes`
- `Offline Compatibility`
- `Determinism Impact`

ADRs atuais a partir de `0007` devem conter:

- `Status`
- `Data`
- `Contexto`
- `Decisao`
- `Alternativas Consideradas`
- `Consequencias`
- `Validacoes Obrigatorias`

E devem manter no front matter:

- `owner`
- `status`
- `date` no formato `YYYY-MM-DD`

O valor de `date` no front matter deve coincidir com a secao `Data`.
O valor de `status` no front matter deve coincidir com a secao `Status`.
O valor de `owner` no front matter deve pertencer a allowlist valida do validador.

## ADRs Atuais

- `0001-deterministic-runtime.md`
- `0002-offline-first-sovereign-mode.md`
- `0003-cryptographic-receipts.md`
- `0004-governance-policy-gates.md`
- `0005-no-mandatory-saas.md`
- `0006-placeholder-attestation-policy.md`
- `0007-route-surface-governance.md`
- `0008-generated-documentation-rebuildable-artifacts.md`
- `0009-backup-restore-component-architecture.md`
- `0010-domain-persistence-contracts.md`
- `0011-disaster-recovery-test-matrix.md`
