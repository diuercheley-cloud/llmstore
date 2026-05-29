---
owner: platform-ops
status: consolidated
---

# Pipelines de Deploy

O `llm-inference-stack` utiliza pipelines de deploy controladas para garantir que nenhuma mudança chegue em ambientes críticos sem validação e aprovação explícita.

## Fluxo de Deploy

1.  **Gatilho**: Apenas tags `v*` (releases oficiais) são elegíveis para deploy. O disparo é estritamente manual (`workflow_dispatch` no GitHub ou `manual` no GitLab).
2.  **Ambientes**: O deploy é isolado por ambientes (Staging, Production, Enterprise Pilots), protegidos por regras de aprovação.
3.  **Validação**: Antes do deploy, a pipeline executa checks de `preflight`. Após o deploy, executa `post-deploy-validate`.
4.  **Rollback**: Se a validação pós-deploy falhar, o sistema tenta um rollback automático para a versão anterior.

## Tipos de Target

- **Appliance**: Deploy em servidores locais ou edge através de scripts de automação.
- **Kubernetes**: Deploy orquestrado via Helm.
- **Enterprise Pilot**: Fluxo especializado para ativação de novos clientes piloto com geração de Handover Pack.
