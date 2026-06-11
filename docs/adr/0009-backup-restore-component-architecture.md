---
owner: platform-ops
status: accepted
date: 2026-06-11
---

# ADR 0009: Backup/Restore Component Architecture

## Status

Accepted

## Data

2026-06-11

## Contexto

O stack possui multiplos mecanismos de backup e restore: servico principal via API, staging restore, scripts offline e componentes legados de agent backup. Sem uma arquitetura por componentes claramente definida, implementacoes paralelas podem divergir em cobertura, seguranca, approvals e comportamento de recovery. A documentacao atual ja indica precedencia do `BackupService`, uso de `RestoreStagingService` para restauracao segura e papel complementar dos scripts shell em cenarios de emergencia.

## Decisao

A arquitetura de backup/restore passa a ser organizada por componentes com responsabilidades explicitas e hierarquia de precedencia.

- `BackupService` e o componente oficial para criar, listar, verificar e iniciar restore logicamente governado
- `RestoreStagingService` e o componente oficial para validar, ensaiar, promover e reverter restauracoes com seguranca
- scripts em `scripts/backup/` sao componentes auxiliares de operacao offline e emergencia, nao fonte primaria de regra de negocio
- componentes legados de agent-only backup ficam formalmente deprecated e nao devem receber nova evolucao funcional
- pedidos de restore com impacto operacional relevante devem passar por fluxo de approval e trilha de auditoria
- cobertura por escopo deve ser declarada em manifestos e documentos gerados, nao inferida informalmente

## Alternativas Consideradas

- manter um unico script shell como mecanismo principal: simples para operadores experientes, mas fraco em auditabilidade e governanca
- permitir servicos independentes por dominio sem coordenacao central: aumenta autonomia local, mas fragmenta contratos de restore
- remover scripts offline e depender so da API: reduz variacao, mas falha no objetivo offline-first e em cenarios de desastre do control plane

## Consequencias

- a plataforma ganha separacao clara entre orquestracao, staging seguro e operacao de emergencia
- fluxos de backup e restore passam a ter contratos mais previsiveis para testes e compliance
- cenarios legados exigem migracao progressiva para o caminho oficial
- a documentacao de cobertura e limites de cada escopo se torna obrigatoria para evitar falsas expectativas de recuperacao

## Validacoes Obrigatorias

- testar criacao, verificacao e restore dry-run pelo componente oficial
- validar staging restore com checagem de manifest, checksums, schema e rollback de seguranca
- validar que scripts offline respeitam o mesmo contrato de manifest e verificacao de integridade
- verificar que componentes deprecated nao sao o caminho padrao nem aparecem como recomendacao oficial
- regenerar e validar o inventario de capacidades de backup e restore quando houver mudanca estrutural
