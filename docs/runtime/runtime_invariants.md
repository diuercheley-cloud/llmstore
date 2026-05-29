---
owner: platform-ops
status: consolidated
---

# Runtime Invariants

## Objetivo

Este documento define invariants que devem permanecer verdadeiros para que o `Core Runtime Spec` seja considerado respeitado.

## Invariants Globais

- toda execucao deve possuir identidade rastreavel
- toda transicao de estado deve ser observavel ou reconstruivel por evidencias persistidas
- nenhuma mutacao protegida por policy pode ocorrer antes de `policy_checked`
- nenhuma execucao `completed` pode voltar a `executing`
- tenant scope nao pode ser cruzado em replay, export, rollback ou verificacao

## Invariants de Execucao

- `submitted` e o unico estado inicial valido
- `completed` e `failed` sao estados terminais originais; `repaired` e `replayed` sao estados derivados de recuperacao
- `scheduled` deve preceder `executing`
- `checkpointed` nao encerra a execucao por si so

## Invariants de Workflow

- todo DAG materializado deve ser aciclico
- `dag_hash` deve ser estavel para o mesmo conteudo canonico
- rollback so pode apontar para checkpoint valido
- resume nao pode saltar gates pendentes

## Invariants de Receipts

- hashes devem usar `SHA-256`
- receipts exportados nao devem expor plaintext sensivel por padrao
- chaining, quando habilitado, deve preservar ordem append-only
- assinatura placeholder nao pode ser documentada como garantia formal

## Invariants de Governanca

- `approval_required` deve bloquear a progressao protegida ate decisao valida
- overrides devem ser explicitamente marcados e auditaveis
- advisory e dry run nao podem ser descritos como enforcement efetivo

## Invariants de Repair

- repair deve minimizar blast radius
- repair nao pode gerar cobranca duplicada por replay
- replay verification deve ocorrer apos repair material
- healing receipts devem preservar rastreabilidade do repair
