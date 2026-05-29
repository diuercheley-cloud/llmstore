---
owner: platform-ops
status: consolidated
---

# Configuração de GitLab Runners

Para rodar a pipeline do `llm-inference-stack` de forma eficiente:

## Runner Requerido
- **Executor**: `docker` (Recomendado).
- **Recursos**: Mínimo 2 vCPU e 4GB RAM.
- **Docker-in-Docker (dind)**: Necessário para jobs de `build`.

## Variáveis de Ambiente Recomendadas
- `DATABASE_URL`: Se quiser usar um banco externo ao invés do service.
- `REGISTRY_USER` / `REGISTRY_PASSWORD`: Para push de imagens em modo manual.

## Modo Air-gapped
Se o runner estiver em um ambiente isolado, garanta que as imagens base (`python:3.10`, `node:20`, `postgres:15`, `redis:7`) estejam disponíveis no cache local ou registry interno.
