# Plano de Evolução para Sistema Multi-Agente (MAS)

Este documento descreve o estado atual e o plano para transformar o LLM Harness em um sistema multi-agente completo e robusto.

## 1. Estado Atual

O sistema possui uma infraestrutura completa para times de agentes e agentes autônomos:
- **Agent Teams**: Definição declarativa de times, membros, papéis e topologias (Linear, Supervisor).
- **Blackboard Avançado**: Memória compartilhada com auditoria completa (Timeline), registro de decisões e artefatos.
- **Governança por Papel**: Restrição de ferramentas baseada em `roles` e avaliação de risco por side-effect.
- **Autonomous Runtime**: Ciclo autônomo de longa duração com suporte a checkpoints, budgets e triggers.

## 2. O que foi implementado

1.  **Registro de Agentes (Agent Registry)**: Definição formal de papéis, prompts, ferramentas e modelos.
2.  **TeamOrchestrator**: Gerenciamento de colaboração entre múltiplos agentes especializados.
3.  **AutonomousAgentRuntime**: Execução autônoma com controle de ciclo (Observe-Decide-Act-Validate).
4.  **Enforcement de Políticas**: Bloqueio de ferramentas inseguras ou não autorizadas.
5.  **Audit Trail**: Timeline detalhada de todas as interações e chamadas de ferramentas.

## 3. Plano de Ação

### Fase 1: Infraestrutura e Definições (CONCLUÍDO)
- [x] Formalizar `config/agent-registry.yaml`.
- [x] Expandir `HarnessConfig`.
- [x] CLI de Times (`llm-harness teams list/inspect/validate`).

### Fase 2: Orquestrador de Times (CONCLUÍDO)
- [x] Implementar `TeamOrchestrator` com topologias Linear e Supervisor.
- [x] Blackboard com auditoria e timeline.
- [x] Governança por papel e side-effects.

### Fase 3: Agentes Autônomos (CONCLUÍDO)
- [x] Implementar `AutonomousAgentRuntime`.
- [x] Suporte a Checkpoints (Pause/Resume).
- [x] Governança de Budget e Cooldown.
- [x] CLI de Autonomia (`llm-harness autonomous run/list/inspect/pause/resume`).

### Fase 4: Especialização e Evals (EM ANDAMENTO)
- [ ] Implementar Agentes Especializados (Architect, Developer, Tester, Security).
- [ ] **Criar Suite de Avaliação Multi-Agente**:
    - Colaboração entre 3+ agentes.
    - Conflito de decisão entre papéis.
    - Recuperação de falha autônoma.
- [ ] **Dashboard de Orquestração**:
    - Visualizações Markdown/JSON ricas.

## 4. Configuração de Agente Autônomo (Exemplo)

```yaml
# config/agent-registry.yaml
agents:
  maintainer:
    role: "System Maintainer"
    model_profile: "high-reasoning"
    tools: ["read_file", "list_dir", "run_tests", "run_shell"]
    prompt: "Você é um mantenedor autônomo. Monitore o código e corrija erros..."

autonomous_settings:
  max_steps: 100
  budget_brl: 5.00
  cooldown_seconds: 300
  checkpoint_every_step: true
```

## 5. CLI de Autonomia

```bash
# Iniciar uma meta autônoma
llm-harness autonomous run --agent maintainer --goal "Corrigir todos os warnings do ruff no diretório scripts/" --budget 2.00

# Listar execuções
llm-harness autonomous list

# Inspecionar uma execução pausada
llm-harness autonomous inspect auto-123456789

# Retomar execução
llm-harness autonomous resume auto-123456789
```

## 6. Métricas e KPIs

O sistema rastreia:
- `task_completion_rate`: Sucesso das metas autônomas.
- `policy_block_rate`: Frequência de ferramentas bloqueadas por governança.
- `token_cost_per_team`: Custo total da colaboração.
- `time_to_resolution_ms`: Tempo total para atingir a meta.
- `checkpoint_count`: Quantidade de estados salvos.
