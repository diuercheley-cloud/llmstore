---
owner: platform-ops
status: accepted
date: 2026-06-11
---

# ADR 0011: Disaster Recovery Test Matrix

## Status

Accepted

## Data

2026-06-11

## Contexto

Backup e restore so sao confiaveis quando exercitados contra combinacoes reais de escopo, modo de execucao, integridade, schema e componentes opcionais como RAG e modelos locais. O repositorio ja diferencia validacoes smoke e full e possui fluxos locais de DR, mas sem uma matriz arquitetural obrigatoria existe risco de cobrir apenas o caminho feliz e publicar claims de recuperacao sem evidencia suficiente.

## Decisao

A plataforma deve manter uma matriz formal de testes de disaster recovery como contrato de validacao, cobrindo cenarios minimos obrigatorios antes de promover mudancas relevantes.

- a matriz deve separar cenarios smoke e full, preservando a regra de que smoke e subconjunto estrito de full
- cada escopo de backup suportado deve ter pelo menos um teste de criacao, verificacao e restore dry-run
- restores com promocao ou rollback devem ser validados em suites full apropriadas
- a matriz deve cobrir falhas de checksum, incompatibilidade de schema, ausencia de chave, conflitos de RAG e artefatos opcionais faltantes
- resultados devem gerar evidencia auditavel e nao apenas logs efemeros

## Alternativas Consideradas

- confiar em testes ad hoc executados manualmente por release: flexivel, mas inconsistente e pouco auditavel
- validar apenas o backup e nao o restore: mais barato, mas insuficiente para confianca operacional
- usar uma unica suite pesada para tudo: maximiza cobertura, mas reduz frequencia de execucao e feedback rapido

## Consequencias

- mudancas em backup, restore, manifestos e contratos de criptografia passam a ter gate mais rigoroso
- o custo de CI sobe, mas de forma controlada pela separacao smoke/full
- evidencias de recuperacao ficam mais defensaveis para operacao, auditoria e handoff
- gaps de cobertura deixam de ser implicitos e passam a ser visiveis como faltas na matriz

## Validacoes Obrigatorias

- definir e manter matriz versionada com cenarios, escopos, pre-condicoes e expected outcomes
- executar suites smoke em desenvolvimento continuo e suites full antes de merge ou release
- validar restore dry-run e restore com rollback seguro quando aplicavel
- verificar preservacao de checksums, assinatura, key id e compatibilidade de schema
- publicar relatorios ou artefatos de evidencia para cada execucao relevante de DR
