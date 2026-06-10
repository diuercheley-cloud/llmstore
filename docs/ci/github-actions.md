---
owner: platform-ops
status: consolidated
---

# CI/CD com GitHub Actions

O `llm-inference-stack` utiliza GitHub Actions para garantir a qualidade, segurança e reprodutibilidade de cada mudança na plataforma.

## Workflows

| Workflow | Frequência | Objetivo |
| :--- | :--- | :--- |
| `ci.yml` | PR / Push | Workflow principal com matrix para API, Frontends, SDK, E2E, Chaos, Security, LLM-Harness, Agent-Evals e Compliance. |
| `release.yml` | Tags `v*` | Publicação de SDK (PyPI), Imagens Docker e criação de Release no GitHub. |
| `security-scheduled.yml` | Diário | Scan de segurança e vulnerabilidades agendado. |
| `docs-validation.yml` | PR | Links quebrados, Changelog, Release Notes. |

## Estrutura Matrix (ci.yml)

O workflow principal (`ci.yml`) utiliza uma matrix para paralelizar os testes por domínio:

- **api**: Backend lint, unit tests, integration tests e integridade do banco.
- **frontend-admin**: Build e testes do Admin UI.
- **frontend-client**: Build e testes do Client UI.
- **sdk**: Testes e build do SDK Python.
- **e2e**: Testes de ponta-a-ponta com Playwright.
- **chaos**: Experimentos de engenharia de caos.
- **security**: Scans de segurança síncronos.
- **llm-harness**: Validação do harness de LLM.
- **agent-evals**: Avaliação automática de agentes.
- **compliance**: Auditoria de conformidade contínua.

## Hardening de Segurança

- **Permissões Mínimas**: Cada workflow define apenas as permissões necessárias (`contents: read`).
- **Secret Management**: Segredos reais nunca são usados em CI de forks.
- **Pinning**: Actions oficiais são fixadas por versão major ou SHA.
- **Isolamento**: O CI roda sem acesso a GPUs reais ou clouds públicas, usando mocks e serviços locais (Docker).

## Gates de Release

Para que uma versão seja considerada estável (tag `v*`), ela deve passar pelo `release-validation.yml`, que executa o **Operational Readiness Pack**.
