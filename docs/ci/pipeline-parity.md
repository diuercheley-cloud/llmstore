---
owner: platform-ops
status: consolidated
---

# Paridade de Pipelines (GitHub vs GitLab)

Mantemos paridade funcional entre as duas plataformas para garantir que a stack possa ser operada em qualquer ecossistema enterprise.

| Job / Funcionalidade | GitHub Action | GitLab CI Job |
| :--- | :--- | :--- |
| Testes Backend | `test-backend` | `backend:test` |
| Build Frontend | `test-frontend` | `frontend:test` |
| Scan de Segredos | `secrets-check` | `security:scan` |
| Build Docker | `docker-build.yml` | `docker:build` |
| Readiness Check | `release-validation.yml` | `release:validate` |
| Cache de Dependências | `actions/setup-*` | `cache:paths` |

## Mocks e Hardware

Ambas as pipelines são configuradas para rodar em ambientes **Commodity Hardware**:
- Sem dependência de GPU.
- Sem dependência de segredos reais para Pull Requests / Merge Requests.
- Uso intensivo de serviços locais (Dockerized Services).
