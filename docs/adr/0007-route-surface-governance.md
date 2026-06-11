---
owner: platform-ops
status: accepted
date: 2026-06-11
---

# ADR 0007: Route Surface Governance

## Status

Accepted

## Data

2026-06-11

## Contexto

A superficie HTTP da plataforma cresceu com routers administrativos, operacionais e de agentes. Sem uma governanca central, novos endpoints podem surgir por registro implicito, divergir da classificacao de suporte e quebrar a previsibilidade entre codigo, inventario gerado e claims documentais. Ja existe documentacao que exige manifesto central de routers e ha referencia gerada da API surface, mas a decisao arquitetural ainda nao estava registrada como ADR.

## Decisao

Toda exposicao de rota deve ser governada por manifesto explicito e por classificacao associada da superficie suportada.

- routers novos so podem ser publicados quando registrados no manifesto central de bootstrap
- cada registro deve declarar modulo, router, prefixo, tags e status de suporte
- descoberta automatica de routers por convention over configuration fica proibida
- a documentacao gerada da API surface deve ser derivada desse cadastro governado e validada em CI
- rotas `legacy`, `beta` ou `deprecated` exigem plano de migracao ou justificativa de permanencia

## Alternativas Consideradas

- autodiscovery de routers por import scan: reduz atrito inicial, mas torna a superficie opaca e sujeita a exposicao acidental
- governanca apenas por documentacao manual: simples no curto prazo, mas diverge facilmente do runtime real
- permitir registro livre e classificar depois: acelera entrega local, mas aumenta debt de compatibilidade e auditoria

## Consequencias

- a superficie publicada passa a ser revisavel e rastreavel
- endpoints nao registrados deixam de ser considerados parte do contrato suportado
- o custo de adicionar rotas aumenta ligeiramente, mas esse custo substitui risco operacional
- geracao de inventario e validadores de superficie tornam-se gates obrigatorios de mudanca

## Validacoes Obrigatorias

- validar que todo router publicado esta declarado no manifesto central
- validar que nao existem rotas ativas sem classificacao de suporte
- regenerar e validar `docs/generated/API_SURFACE.md`
- executar testes de governanca de rotas e de carregamento de routers
- bloquear merge quando houver divergencia entre manifesto, runtime e documentacao gerada
