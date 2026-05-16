# ADR 0002: Offline-First Sovereign Mode

## Status

Accepted

## Context

O produto precisa suportar ambientes soberanos, locais e air-gapped onde conectividade externa pode ser ausente, restrita ou politicamente indesejada. Sem uma decisao formal, recursos cloud podem se tornar acoplamentos implícitos.

## Decision

Modo sovereign deve ser projetado como offline-first. Replicacao, exportacao, importacao e sincronizacao local devem permanecer possiveis sem dependencia mandatoria de SaaS externo. Integracoes remotas continuam opcionais e degradam sem interromper o nucleo local.

## Consequences

Melhora soberania operacional e previsibilidade de implantacao. Exige mais disciplina na separacao entre funcionalidades centrais e integracoes opcionais, incluindo bundles exportados e fluxos de sincronizacao.

## Security Notes

Operacao offline reduz superficie externa imediata, mas nao elimina necessidade de sanitizacao, controle de bundles exportados, trilha de auditoria e validacao de integridade antes de importacao.

## Offline Compatibility

Impacto central. Esta decisao existe para garantir compatibilidade com cenarios offline-first, desconectados e de appliance local.

## Determinism Impact

Impacto positivo. Reduz dependencia de variaveis externas de rede em fluxos soberanos e melhora repetibilidade de sincronizacao e export/import sob entradas equivalentes.

