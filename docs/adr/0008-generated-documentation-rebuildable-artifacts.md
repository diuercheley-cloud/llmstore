---
owner: platform-ops
status: accepted
date: 2026-06-11
---

# ADR 0008: Generated Documentation as Rebuildable Artifacts

## Status

Accepted

## Data

2026-06-11

## Contexto

O repositorio possui documentacao derivada de codigo e configuracao, como inventarios de API surface, feature flags, storage backends, backup capabilities e product surface. Esses documentos sao uteis como referencia operacional, mas so sao confiaveis quando podem ser regenerados de forma deterministica a partir das fontes canonicas. Sem uma decisao formal, documentos gerados tendem a ser tratados como editaveis manualmente, o que cria drift entre implementacao e claims.

## Decisao

Documentacao gerada passa a ser tratada como artefato reconstruivel, nunca como fonte primaria editada manualmente.

- arquivos em `docs/generated/` e demais saidas explicitamente marcadas como auto-generated devem ser reconstruiveis por script
- a verdade canonica permanece em codigo, configuracao versionada e manifests governados
- toda geracao deve ser deterministica o suficiente para produzir diffs semanticamente estaveis
- alteracoes na fonte exigem regeneracao e validacao do artefato no mesmo ciclo de mudanca
- revisao humana continua obrigatoria para o conteudo resultante, mas nao para edicao manual direta do artefato

## Alternativas Consideradas

- manter os documentos gerados somente fora do repositorio: reduz ruido de diff, mas piora auditabilidade e uso offline
- editar documentos gerados manualmente quando conveniente: agiliza correcoes pontuais, mas destrói rastreabilidade
- substituir artefatos gerados por narrativa manual: melhora legibilidade, mas perde cobertura sistematica do estado real

## Consequencias

- o repositorio preserva referencia offline e auditavel do estado documentado
- a manutencao exige scripts de geracao e validadores confiaveis
- diffs passam a refletir mudancas estruturais da plataforma, nao apenas texto editorial
- a equipe precisa distinguir claramente documentacao canonica, referencia derivada e historico

## Validacoes Obrigatorias

- executar geradores oficiais dos documentos marcados como auto-generated
- validar que os artefatos versionados batem com a saida atual dos scripts
- proibir edicao manual de arquivos gerados quando o pipeline indicar drift
- verificar que cada artefato gerado aponta para sua fonte de verdade ou mecanismo de reconstrucao
- incluir esses validadores nas suites smoke ou full adequadas, sem dependencia de servicos externos
