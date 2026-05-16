# ADR 0006: Placeholder Attestation Policy

## Status

Accepted

## Context

O produto referencia atestacao, integridade e receipts assinados em varios pontos, mas nem todos os ambientes possuem base material para claims fortes sobre attestation real. Era necessario registrar um limite formal para documentacao e implementacao incremental.

## Decision

A plataforma deve tratar attestation atual como politica placeholder e estrutura de integracao, nao como claim de attestation de hardware real. Campos, receipts e workflows podem carregar metadata preparatoria, desde que a documentacao deixe claro o carater nao definitivo.

## Consequences

Evita promessas excessivas e mantem espaco para evolucao futura. Tambem exige disciplina editorial para nao converter placeholders em claims fortes sem suporte tecnico e operacional correspondente.

## Security Notes

Placeholders ajudam na organizacao de evidencias e contratos, mas nao equivalem a raiz de confianca material, certificacao formal ou validacao independente por si so.

## Offline Compatibility

Compativel com ambientes offline-first porque placeholders e metadata podem ser avaliados localmente, sem dependencia obrigatoria de serviços externos.

## Determinism Impact

Impacto neutro a positivo. Estruturas placeholder podem ser mantidas deterministicas desde que formatos e campos de metadata sejam estaveis.

