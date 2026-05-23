# Ubiquitous Policy Enforcement

O `llm-inference-stack` impõe a avaliação de políticas de governança antes de qualquer ação que possa causar efeitos colaterais ou expor dados sensíveis. O `AgentPolicyEngine` atua como um "sentinela" onipresente no runtime agentic.

## Fluxo Obrigatório de Decisão

Nenhuma ação (tool call, memória, handoff, planner) pode ser executada sem seguir este fluxo:

1.  **PolicyRequest**: O serviço solicitante constrói um objeto contendo o tipo de ação, o sujeito (ex: nome da ferramenta), tenant, agente e contexto.
2.  **Evaluation**: O `AgentPolicyEngine` avalia o pedido contra regras globais e específicas do agente/tenant.
3.  **PolicyDecision**: A decisão é registrada obrigatoriamente no banco de dados (`agent_policy_decisions`) para auditoria.
4.  **Enforcement**: O resultado (`allow`, `deny`, `require_approval`, `require_dry_run`) é retornado e deve ser estritamente respeitado pelo serviço.

## Ações Governamentais

### 1. Chamadas de Ferramentas (`tool_call`)
- Valida allowlists de ferramentas por agente.
- Bloqueia categorias restritas (ex: `shell_command`).
- Exige aprovação humana para ferramentas destrutivas (delete, drop, etc.).

### 2. Acesso à Memória (`memory_write`, `memory_read`)
- Garante que persistências só ocorram se houver uma política de retenção ativa para o tenant/tipo de memória.
- Protege contra vazamento de segredos no armazenamento.

### 3. Transições entre Agentes (`handoff`)
- Controla o fluxo de colaboração entre agentes.
- Restringe handoffs de agentes de alto risco para agentes não homologados (não-production).

### 4. Orquestração do Planner (`planner_exec`)
- Valida a intenção inicial do agente antes de iniciar o ciclo de raciocínio.
- Pode limitar a complexidade da execução baseado no nível de risco do agente.

## Auditabilidade

Todas as decisões de política contêm:
- `decision_id`: Identificador único da avaliação.
- `result`: O veredito final.
- `reason`: Justificativa técnica ou de conformidade para a decisão.
- `risk_level`: Risco calculado do agente no momento da decisão.
- `policy_version`: Versão do conjunto de regras aplicado.
