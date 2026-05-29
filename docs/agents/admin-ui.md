---
owner: platform-ops
status: consolidated
---

# Agentic Admin UI

A interface administrativa (Admin v2) fornece um painel de controle centralizado para operar e governar o ecossistema de agentes inteligentes.

## Rotas Disponíveis

Todas as rotas estão agrupadas sob o namespace `/agents`.

| Rota | Descrição |
|------|-----------|
| `/agents` | Overview e métricas de alto nível (runs ativas, aprovações pendentes, alertas). |
| `/agents/registry` | Catálogo de agentes definidos no sistema, mostrando versão, risco e dono. |
| `/agents/runs` | Lista histórica de todas as execuções iniciadas. |
| `/agents/runs/:id` | Timeline detalhada de uma execução específica, com steps e eventos de observabilidade. |
| `/agents/tools` | Monitoramento de ferramentas invocadas, latência e bloqueios por política. |
| `/agents/memory` | Visualização da memória isolada dos agentes. Conteúdo é redigido por padrão. |
| `/agents/approvals` | Fila de requisições pendentes para o Human-In-The-Loop (HITL). |
| `/agents/evals` | Resultados do Agent Evaluation Framework (Score, Pass Rate, Baselines). |
| `/agents/policies` | Visualização de regras de governança aplicadas ativamente e ferramenta de simulação (Dry Run). |
| `/agents/marketplace` | Catálogo de pacotes de agentes instaláveis. |

## Segurança e Governança na UI

A interface foi projetada seguindo o princípio de *Security by Design*:

- **Prompts Ocultos**: Prompts brutos e payloads completos não são exibidos por padrão na timeline. A expansão de payloads requer cliques explícitos e pode ser bloqueada via RBAC.
- **Ações Destrutivas**: Toda ação classificada como `critical` (ex: `delete_database`) que exija aprovação apresentará um modal de confirmação vermelho com obrigatoriedade de preenchimento de justificativa de auditoria.
- **Read-Only Safeties**: Visualizações de memória ou execuções passadas não possuem efeitos colaterais.

## Feature Flags

A UI adapta-se dinamicamente às configurações do Control Plane:

- Se `AGENT_EVALS_ENABLED=false`, a tela de Evals exibirá um *empty state* indicativo.
- Se `AGENT_MARKETPLACE_ENABLED=false`, a aba pode ser ocultada ou exibir um aviso de funcionalidade desativada.
