---
owner: platform-ops
status: consolidated
---

# Multi-Agent Runtime Governed

Este documento detalha o framework de orquestração multi-agente do LLM Inference Stack, focando em segurança, governança e rastreabilidade.

## Princípios de Governança

Diferente de sistemas multi-agente "livres", nossa implementação exige autorização explícita para qualquer interação entre agentes.

### 1. Políticas de Delegação (Delegation)

Um agente (Source) só pode delegar uma tarefa para outro agente (Target) se existir uma `AgentDelegationPolicy` ativa.

- **Cross-Tenant Blocking**: Delegação entre diferentes tenants é bloqueada no nível do banco de dados e do serviço.
- **Max Depth**: O sistema impõe um limite de profundidade na cadeia de delegação (padrão: 10).
- **Loop Detection**: Ciclos de delegação (A -> B -> A) são detectados e interrompidos automaticamente para evitar consumo infinito de recursos.

### 2. Memória Compartilhada (Shared Memory)

Agentes operam em silos de memória por padrão. O acesso a memórias de outros agentes exige uma `AgentSharedMemoryPolicy`.

- **Grupos de Agentes**: Memória pode ser compartilhada dentro de um `agent_group_id`.
- **Controle Fino**: Permissões explícitas de `can_read` e `can_write`.

### 3. Sessões de Colaboração e Tracing

Toda cadeia de delegação iniciada por uma run raiz é agrupada em uma `AgentCollaborationSession`.

- **Trace Completo**: É possível visualizar toda a árvore de execução, desde o agente inicial até o último sub-agente acionado.
- **Audit Log**: Handoffs e acessos a memórias compartilhadas geram eventos de auditoria.

## Limites e Segurança

| Recurso | Regra | Ação em Violação |
|---------|-------|------------------|
| Delegação | Sem política ativa | Bloqueio imediato |
| Cross-Tenant | IDs de tenant diferentes | Erro de segurança (403) |
| Ciclo (Loop) | Agente já presente na cadeia | Falha na run com `loop_detected` |
| Profundidade | Excede `max_depth` | Falha na run com `max_depth_exceeded` |
| Memória | Sem permissão no grupo | Retorno vazio ou erro de acesso |

## API de Administração

- `POST /admin/agents/delegation-policies`: Cria novas permissões de delegação.
- `GET /admin/agents/collaboration-sessions`: Lista sessões ativas.
- `GET /admin/agents/collaboration-sessions/{id}/trace`: Retorna a árvore de execução completa da sessão.
