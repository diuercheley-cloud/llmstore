---
owner: platform-ops
status: consolidated
---

# ADR 0003: Cryptographic Receipts

## Status

Accepted

## Context

Receipts sao parte importante da rastreabilidade de execucao, verificacao e auditoria. Sem registro arquitetural claro, o formato pode derivar para artefatos inconsistentes ou dificeis de validar em replay local.

## Decision

A plataforma deve emitir receipts com hash imutavel do payload canonico e placeholder de metadata de assinatura quando assinatura real nao estiver habilitada. O formato deve favorecer verificacao local e encadeamento simples de integridade.

## Consequences

Melhora rastreabilidade e prepara evolucao de validacao criptografica sem exigir enforcement completo imediato. Introduz custo de manter payloads mais estruturados e consistentes.

## Security Notes

Receipts criptograficos melhoram integridade observavel, mas nao devem ser interpretados como certificacao formal. Placeholders de assinatura existem para compatibilidade e transicao gradual, nao como prova final por si so.

## Offline Compatibility

Compatibilidade alta. O modelo foi escolhido para permitir verificacao local de hash e inspeção de metadata sem servicos remotos obrigatorios.

## Determinism Impact

Impacto alto. Receipts dependem de serializacao canonica e campos estaveis para manter reprodutibilidade de hash e comparacao entre execucoes equivalentes.

