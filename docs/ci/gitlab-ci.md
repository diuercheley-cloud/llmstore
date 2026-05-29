---
owner: platform-ops
status: consolidated
---

# GitLab CI/CD

O `llm-inference-stack` fornece suporte nativo ao GitLab CI através do arquivo `.gitlab-ci.yml`. A configuração é modular e segue os mesmos princípios de segurança e qualidade do GitHub Actions.

## Estrutura de Stages

1. **preflight**: Validações rápidas de integridade do repositório.
2. **test**: Execução de suites de teste backend (Python) e frontend (Node).
3. **security**: Scans de segredos e auditoria de vulnerabilidades.
4. **build**: Construção de imagens Docker.
5. **validate**: Execução do Operational Readiness Pack.
6. **package**: Consolidação de artefatos de release.

## Cache e Performance

- **Pip Cache**: Armazenado em `.cache/pip` e compartilhado entre jobs do mesmo estágio.
- **Npm Cache**: Armazenado em `frontend/admin/node_modules/`.

## Deployment

O deploy real é estritamente **manual**. Utilize a interface do GitLab para disparar o deploy em ambientes de staging ou produção após a validação bem-sucedida da pipeline.
