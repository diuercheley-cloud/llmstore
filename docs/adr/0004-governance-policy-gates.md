---
owner: platform-ops
status: consolidated
---

# ADR 0004: Governance Policy Gates

## Status

Accepted

## Context

Workflows de runtime, billing, trust e operacao precisam de pontos claros de avaliacao de politica. Sem gates explicitados, aprovacoes, dry-run e enforcement podem ficar dispersos e inconsistentes.

## Decision

A plataforma deve usar policy gates de governanca como pontos declarados de avaliacao, com suporte a modos advisory, dry_run e enforcement controlado. Dry-run continua sem mutacao persistente obrigatoria.

## Consequences

Facilita auditoria de decisoes e reduz divergencia entre areas da plataforma. Exige que novos fluxos exponham contexto suficiente para avaliacao de politica e justificativa.

## Security Notes

Policy gates aumentam consistencia de decisao e reduzem bypass acidental, mas dependem de cobertura adequada de contexto, explainability e logs de auditoria minimamente confiaveis.

## Offline Compatibility

Compativel. Gates devem preferir policy bundles e contexto local sempre que possivel, evitando dependencia mandatoria de resolucao remota para caminhos basicos.

## Determinism Impact

Impacto positivo quando politicas e entradas forem canonicas. Gates mal definidos podem reintroduzir variabilidade, entao a avaliacao deve evitar fontes externas nao controladas.

