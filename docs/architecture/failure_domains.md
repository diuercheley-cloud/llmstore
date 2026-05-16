# Failure Domains

## Objetivo

Este documento define failure domains, blast radius esperado e restricoes de reparo deterministico para os seis planes estabilizados.

## Runtime Fabric

Failure domain:
- execucao de inferencia, routing, cache, filas, workflows e recovery loops

Blast radius:
- degradacao de throughput, latency spikes, retries excessivos, replay parcial de workflows

Recovery expectations:
- recuperacao automatica preferencial
- isolamento por tenant, node, workflow ou backend
- rollback local antes de qualquer acao global

Deterministic repair constraints:
- replay deve ser idempotente
- healing nao pode duplicar cobranca
- mutacoes devem ser registradas com contexto suficiente para reproduzir decisao

## Governance Plane

Failure domain:
- avaliacao de policy, explainability, approval gates e consistencia de bundles

Blast radius:
- decisoes conservadoras, bloqueios administrativos, fallback para politica mais segura conhecida

Recovery expectations:
- fail-closed para acoes sensiveis
- uso de ultima policy valida assinada
- ability to reconcile drift sem reconfiguracao manual ampla

Deterministic repair constraints:
- nenhuma policy pode ser parcialmente ativada
- snapshots de policy devem ser versionados
- autoremediation precisa ser replay-safe e auditavel

## Trust Plane

Failure domain:
- assinatura, verificacao, atestacao, encryption e evidence chain

Blast radius:
- perda temporaria de capacidade de emitir provas, verificacoes falhando, degrade para modos auditaveis mais restritos

Recovery expectations:
- fail-closed para verificacoes criticas
- degradacao controlada para modos locais/offline permitidos
- possibilidade de revalidar evidencias de forma deterministica apos restauracao

Deterministic repair constraints:
- nunca regenerar prova com material nao reprodutivel
- rotacao de chave nao pode invalidar historico auditavel
- reparo nao pode reescrever trilha imutavel anterior

## Financial Plane

Failure domain:
- wallet, billing, reconciliation, disputes e revenue safeguards

Blast radius:
- divergencia de chargeback, atraso em conciliacao, bloqueio temporario de cobranca automatica

Recovery expectations:
- ledger-first recovery
- reconciliacao posterior deve ser suportada sem perda de trilha
- degradacao deve favorecer subcobranca temporaria em vez de cobranca duplicada

Deterministic repair constraints:
- debit/credit precisam ser idempotentes
- recomputacao financeira deve usar inputs persistidos e versionados
- correcoes manuais precisam deixar rastro auditavel

## Sovereign Plane

Failure domain:
- airgap sync, appliance restrictions, sovereign mesh e particionamento regional

Blast radius:
- atraso de sincronizacao, particao entre clusters, congelamento de import/export offline

Recovery expectations:
- preferencia por continuidade local
- nenhuma dependencia mandatoria de cloud/SaaS
- resync controlado via manifests e evidencias assinadas

Deterministic repair constraints:
- manifests devem ser reaplicaveis sem efeitos colaterais
- import/export deve ser order-preserving
- repair nao pode bypassar restricoes de chain-of-custody

## Operations Plane

Failure domain:
- portais administrativos, exportacao de relatorios, observabilidade operacional e controles de operador

Blast radius:
- perda de visibilidade, atraso em exportacoes, UX administrativa degradada

Recovery expectations:
- plano de dados e plano de execucao continuam operando sem o plano operacional
- leitura posterior de evidencias persistidas deve ser possivel
- automacoes operacionais podem ser reexecutadas a partir de estado persistido

Deterministic repair constraints:
- exportacoes devem ser reproduziveis a partir dos mesmos filtros e snapshots
- acoes de operador devem permanecer auditaveis
- reexecucao nao pode introduzir mutacoes invisiveis
