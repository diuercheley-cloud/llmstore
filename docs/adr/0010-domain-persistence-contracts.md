---
owner: platform-ops
status: accepted
date: 2026-06-11
---

# ADR 0010: Domain Persistence Contracts

## Status

Accepted

## Data

2026-06-11

## Contexto

Partes criticas da aplicacao ainda convivem com acesso direto a ORM espalhado por servicos e APIs. Isso enfraquece limites de dominio, dificulta testes deterministas e aumenta acoplamento com a tecnologia de persistencia. Ja existe documentacao de contratos de repositorio por dominio e inventario de debt remanescente, mas faltava registrar a decisao arquitetural que proibe a expansao do acesso direto como padrao.

## Decisao

Servicos de dominio devem depender de contratos de persistencia explicitos, e nao de modelos ORM concretos.

- cada dominio critico deve expor protocolos ou contratos de repositorio em `contracts.py`
- implementacoes concretas de persistencia ficam encapsuladas em repositorios adaptadores
- APIs, services e orchestration layers devem consumir contratos, nao sessao ORM ou models como dependencia principal
- acesso direto a ORM existente pode permanecer apenas como debt mapeado e com plano de migracao
- contratos devem declarar limites de dependencia, requisitos de determinismo e expectativas de erro observavel

## Alternativas Consideradas

- manter acesso direto ao ORM em toda a aplicacao: reduz ceremony, mas amplia acoplamento e dificulta modularizacao
- migrar tudo para event sourcing imediatamente: aumenta isolamento semantico, mas e desproporcional ao estado atual do stack
- encapsular somente novos dominios e ignorar os legados: reduz esforco imediato, mas preserva a parte mais arriscada do debt

## Consequencias

- testes de unidade e integracao ficam mais simples de isolar
- a troca futura de backend de persistencia ou extracao de modulos se torna mais viavel
- o ritmo de entrega de mudancas de dados pode cair no curto prazo devido a camada adicional de contrato
- debt legado fica explicitamente visivel e revisavel, em vez de se expandir silenciosamente

## Validacoes Obrigatorias

- executar validadores de contratos de dominio e suites de teste correspondentes
- verificar que novos services nao introduzem acesso direto a models fora dos repositorios
- revisar debt remanescente de ORM direto e impedir regressao em dominios ja migrados
- validar que implementacoes concretas respeitam os protocolos declarados
- manter documentacao de dominio e persistencia alinhada com o estado real do codigo
