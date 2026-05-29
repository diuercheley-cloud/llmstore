---
owner: platform-ops
status: consolidated
---

# CI/CD com GitHub Actions

O `llm-inference-stack` utiliza GitHub Actions para garantir a qualidade, segurança e reprodutibilidade de cada mudança na plataforma.

## Workflows

| Workflow | Frequência | Objetivo |
| :--- | :--- | :--- |
| `ci.yml` | PR / Push | Lint, Testes Backend/Frontend, Integridade Alembic. |
| `security.yml` | Diário / PR | Scan de segredos, Auditoria de Dependências (Pip/Npm). |
| `release-validation.yml` | Tags `v*` | Smoke tests, Chaos tests, Operational Readiness. |
| `docker-build.yml` | Push `main` | Validação de build das imagens Docker. |
| `docs-validation.yml` | PR | Links quebrados, Changelog, Release Notes. |

## Hardening de Segurança

- **Permissões Mínimas**: Cada workflow define apenas as permissões necessárias (`contents: read`).
- **Secret Management**: Segredos reais nunca são usados em CI de forks.
- **Pinning**: Actions oficiais são fixadas por versão major ou SHA.
- **Isolamento**: O CI roda sem acesso a GPUs reais ou clouds públicas, usando mocks e serviços locais (Docker).

## Gates de Release

Para que uma versão seja considerada estável (tag `v*`), ela deve passar pelo `release-validation.yml`, que executa o **Operational Readiness Pack**.
