# Multi-Agent Systems and Collaboration

A plataforma permite que múltiplos agentes trabalhem em conjunto através de sessões de colaboração controladas e deleguem tarefas uns aos outros (handoffs).

## Sessões de Colaboração

Uma sessão de colaboração (`AgentCollaborationSession`) é iniciada quando um agente realiza seu primeiro handoff. Ela vincula uma árvore de execuções relacionadas a um objetivo inicial, permitindo rastrear o fluxo de trabalho entre diferentes especialistas.

## Governança Multi-Agente

A colaboração não é irrestrita. Ela segue regras rigorosas para evitar execuções descontroladas ou loops infinitos:

1. **Ativação Requerida**: Tanto `AGENT_MULTI_AGENT_ENABLED` quanto `AGENT_HANDOFFS_ENABLED` devem ser `true`.
2. **Políticas de Handoff**: Cada delegação deve ser permitida por uma `AgentHandoffPolicy` explícita definindo a origem e o destino.
3. **Limites de Ciclo**: O número máximo de handoffs em uma mesma sessão é limitado para evitar loops.
4. **Isolamento de Tenant**: Handoffs entre inquilinos diferentes são bloqueados por padrão.

## Workflow

1. **Decisão do Agente**: Um agente decide que não possui as ferramentas ou conhecimento necessários e solicita um `handoff`.
2. **Avaliação de Política**: O sistema verifica se existe uma política permitindo que o `Agente A` delegue para o `Agente B` para aquele `tenant_id`.
3. **Criação de Sub-Run**: Uma nova corrida de agente é iniciada para o alvo, com contexto sanitizado.
4. **Finalização da Origem**: A corrida original é marcada como completa (com status de delegada).
