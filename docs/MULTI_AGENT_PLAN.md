# Plano de Evolução para Sistema Multi-Agente (MAS)

Este documento descreve o estado atual e o plano para transformar o LLM Harness em um sistema multi-agente completo e robusto.

## 1. Estado Atual

Atualmente, o sistema possui uma implementação básica de multi-agente (`planner-coder-reviewer`):
- **Fluxo Fixo**: Segue uma sequência linear de Planejamento -> Execução (Coder) -> Revisão.
- **Memória Compartilhada**: Utiliza um `Blackboard` para manter o estado da tarefa, plano e mensagens entre agentes.
- **Roteamento de Modelos**: Permite usar diferentes perfis de modelo para diferentes tipos de tarefa (`planner`, `coder`, `reviewer`).
- **Limitações**:
    - Não há um registro formal de agentes com personalidades e ferramentas específicas.
    - O orquestrador é rígido e não permite decisões dinâmicas sobre qual agente chamar em seguida.
    - Todos os agentes têm acesso às mesmas ferramentas (através do Coder).

## 2. O que falta para ser um Sistema Multi-Agente Completo

1.  **Registro de Agentes (Agent Registry)**: Definição formal de papéis, prompts de sistema, ferramentas permitidas e modelos preferenciais para cada agente.
2.  **Orquestração Dinâmica (Supervisor)**: Um agente "Supervisor" que analisa o estado do Blackboard e decide dinamicamente qual agente especializado deve agir em seguida.
3.  **Gating de Ferramentas por Agente**: Restringir quais ferramentas cada agente pode usar (ex: um Testador não deve poder deletar arquivos de código).
4.  **Colaboração Estruturada**: Protocolos de comunicação mais ricos entre agentes (ex: requisição de revisão, pedido de ajuda, delegação de sub-tarefas).
5.  **Hierarquia de Metas**: Capacidade de decompor tarefas complexas em sub-metas rastreáveis no Blackboard.

## 3. Plano de Ação

### Fase 1: Infraestrutura e Definições
- [ ] **Formalizar `config/agent-registry.yaml`**:
    - Adicionar definições de agentes: `architect`, `developer`, `tester`, `security_reviewer`, `doc_writer`.
    - Especificar `system_prompt`, `tools_allowed` e `model_profile` para cada um.
- [ ] **Expandir `HarnessConfig`**:
    - Implementar o carregamento e validação dessas novas definições de agentes.

### Fase 2: Orquestrador Inteligente
- [ ] **Implementar `SupervisorOrchestrator`**:
    - Criar um novo modo de execução (`--agent-mode supervisor`).
    - O Supervisor usa o histórico do Blackboard para escolher o próximo agente do registro.
- [ ] **Aprimorar o `Blackboard`**:
    - Adicionar suporte para estados de sub-tarefas e árvore de decisões.
    - Melhorar a sumarização para fornecer contexto otimizado para o Supervisor.

### Fase 3: Especialização e Segurança
- [ ] **Implementar Agentes Especializados**:
    - **Architect**: Focado em design e planejamento de alto nível.
    - **Developer**: Focado em implementação e refatoração.
    - **Tester**: Especializado em criar e executar suítes de teste.
    - **Security Reviewer**: Focado em análise de vulnerabilidades e conformidade.
- [ ] **Controle de Ferramentas (RBAC para Agentes)**:
    - Integrar o `PolicyEngine` com o registro de agentes para bloquear ferramentas não autorizadas por papel.

### Fase 4: Validação e Demonstração
- [ ] **Criar Suite de Avaliação Multi-Agente**:
    - Cenários complexos que exijam a colaboração de pelo menos 3 agentes diferentes.
- [ ] **Dashboard de Orquestração**:
    - Gerar visualizações (Markdown/JSON) que mostrem claramente a "conversa" e as transições entre agentes.

## 4. Configuração Recomendada (Exemplo)

```yaml
# config/agent-registry.yaml (Proposto)
agents:
  architect:
    role: "System Architect"
    model_profile: "high-reasoning"
    tools: ["read_file", "list_dir", "index_query"]
    prompt: "Você é um arquiteto de sistemas. Planeje a solução considerando escalabilidade e padrões de projeto..."
  
  developer:
    role: "Senior Developer"
    model_profile: "coding-optimized"
    tools: ["read_file", "write_file", "apply_patch", "run_shell"]
    prompt: "Você é um desenvolvedor sênior. Implemente as mudanças planejadas seguindo as melhores práticas..."

  tester:
    role: "QA Engineer"
    model_profile: "balanced"
    tools: ["read_file", "run_shell", "run_tests"]
    prompt: "Você é um engenheiro de QA. Garanta que o código funcione e não tenha regressões..."
```
