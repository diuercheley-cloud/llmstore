---
owner: platform-ops
status: consolidated
---

# Core Runtime Spec

## Objetivo

Esta especificacao formaliza o contrato central do runtime deterministico da stack. Ela define lifecycles, estados observaveis e restricoes operacionais para execucao, workflows, receipts, governanca e reparo.

Este documento:

- nao introduz novas features de produto
- nao implementa hardware attestation real
- nao faz claim de certificacao formal
- preserva operacao offline-first

## Escopo

O contrato cobre:

- runtime execution state machine
- workflow state machine
- receipt lifecycle minimo
- governance decision lifecycle
- repair and replay lifecycle

## Execution Lifecycle

### Estados obrigatorios

- `submitted`
- `validated`
- `policy_checked`
- `scheduled`
- `executing`
- `checkpointed`
- `completed`
- `failed`
- `repaired`
- `replayed`

### Semantica dos estados

- `submitted`: a requisicao ou execucao foi aceita pelo runtime e recebeu identidade rastreavel.
- `validated`: schema, tenant scope, invariants basicos e precondicoes locais foram validados.
- `policy_checked`: policy gates foram avaliados em modo advisory, dry run ou enforcement.
- `scheduled`: a execucao recebeu decisao de fila, lease ou slot de runtime.
- `executing`: o runtime iniciou mutacoes e/ou chamadas de provider previstas pelo contrato.
- `checkpointed`: um snapshot reproduzivel foi persistido sem invalidar a hash chain da execucao.
- `completed`: a execucao terminou sem violacao material conhecida.
- `failed`: a execucao terminou com erro terminal ou bloqueio governado.
- `repaired`: uma falha previa foi tratada por recovery deterministico ou healing controlado.
- `replayed`: uma nova execucao ou sessao de replay confirmou ou refutou a consistencia da execucao original.

### Transicoes permitidas

- `submitted -> validated`
- `validated -> policy_checked`
- `policy_checked -> scheduled`
- `scheduled -> executing`
- `executing -> checkpointed`
- `checkpointed -> executing`
- `executing -> completed`
- `executing -> failed`
- `failed -> repaired`
- `failed -> replayed`
- `repaired -> replayed`
- `replayed -> completed`
- `replayed -> failed`

### Transicoes proibidas

- `submitted -> executing` sem `validated` e `policy_checked`
- `completed -> executing`
- `completed -> repaired`
- `failed -> completed` sem `repaired` ou `replayed`

## Workflow Lifecycle

### DAG creation

- o workflow deve nascer como DAG explicito
- nodes, edges e stage metadata devem ser serializaveis de forma canonica
- o DAG nao pode conter dependencia ciclica materializavel

### DAG hashing

- cada definicao deve produzir `dag_hash` deterministico
- hashing deve usar serializacao canonica estavel
- alteracao de node, edge, gate ou input material deve alterar o hash

### Policy gates

- gates devem ser aplicados antes de mutacoes irreversiveis
- cada gate deve registrar decisao, modo e evidencia minima
- `approval_required` deve bloquear progressao ate decisao valida

### Checkpoint creation

- checkpoints devem capturar estado reproduzivel
- cada checkpoint deve ser encadeado ao anterior quando aplicavel
- checkpoint nao pode incluir plaintext sensivel quando hash ou redacao forem suficientes

### Pause/resume

- `pause` deve congelar progressao sem perder identidade de execucao
- `resume` deve retomar a partir de checkpoint ou estado consistente equivalente
- `resume` nao pode pular gates ainda nao satisfeitos

### Rollback

- rollback deve apontar para checkpoint valido e tenant-scoped
- rollback deve preservar trilha append-only de tentativa, erro e reversao
- rollback nao implica apagar receipts ou evidencias anteriores

### Replay validation

- replay deve comparar contexto, hashes e saidas observaveis relevantes
- diferenca de metadados efemeros isoladamente nao caracteriza drift material
- replay deve resultar em `replayed` com status verificavel de match, mismatch ou partial

## Receipt Lifecycle

### Receipt creation

- todo receipt deve possuir identidade unica, timestamp local e escopo de tenant quando aplicavel
- receipt deve ser emitido sem depender de SaaS externo

### immutable_hash

- cada receipt deve possuir `immutable_hash` ou campo equivalente com digest do payload canonico
- o hash deve ser calculado com `SHA-256`

### SHA-256 chaining

- quando chaining estiver habilitado, cada novo receipt deve referenciar `previous_receipt_hash`
- quebra de qualquer elo invalida a verificacao integral da cadeia subsequente

### Signature placeholder

- assinatura destacada placeholder e permitida
- placeholder atual nao implica PKI formal, nao implica non-repudiation legal e nao implica certificacao

### Verification

- verificacao deve considerar integridade do hash, cadeia, assinatura placeholder quando presente e consistencia de replay/runtime quando disponivel
- verificacao deve produzir resultado rastreavel: `valid`, `invalid` ou `partial`

### Export restrictions

- export deve respeitar tenant scope
- export deve omitir plaintext sensivel por padrao
- export em ambientes soberanos/offline pode exigir politicas adicionais de chain of custody

## Governance Lifecycle

### policy match

- o runtime deve registrar quando uma policy aplicavel foi encontrada e qual snapshot foi usado

### advisory mode

- em `advisory`, a execucao segue adiante, mas a decisao fica registrada para observacao

### dry_run mode

- em `dry_run`, efeitos de enforcement sao simulados ou registrados sem bloquear a progressao normal, salvo regra mais restritiva local

### approval required

- quando `approval_required` existir, a execucao deve parar antes da mutacao protegida
- aprovacoes e overrides devem ser append-only

### enforcement

- em `enforcement`, deny ou falta de precondicao obrigatoria deve impedir a acao governada

### incident creation

- violacoes materiais, drift critico ou override emergencial podem gerar incidente rastreavel
- incidente nao substitui a trilha governanca original; ele a referencia

## Repair Lifecycle

### failure detection

- falha pode ser detectada por erro terminal, drift, timeout, inconsistencia de chain ou violacao de policy/runtime

### recovery plan

- o plano de recovery deve ser explicitado antes de acao corretiva material
- o plano deve incluir escopo, blast radius pretendido e modo de execucao

### deterministic repair

- repair deve preferir a menor mutacao necessaria
- repair deve ser replay-safe, idempotente quando aplicavel e consistente com checkpoints persistidos

### signed healing receipt

- toda healing action relevante deve gerar receipt encadeado
- assinatura placeholder e aceitavel, desde que o recibo deixe isso explicito

### replay verification

- apos repair relevante, replay verification deve confirmar se a execucao voltou a um estado aceitavel
- repair sem verificacao posterior e incompleto do ponto de vista contratual

## Limitacoes Explicitadas

- nao ha hardware attestation real neste contrato
- nao ha claim de FIPS, HSM certificado, TSA formal ou certificacao equivalente
- placeholders criptograficos permanecem placeholders ate implementacao concreta
- determinismo e operacional e verificavel, nao prova formal matematica completa
