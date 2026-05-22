# Policy-as-Code para Agentes

A plataforma utiliza o paradigma de Policy-as-Code para definir o comportamento aceitável de agentes inteligentes.

## Estrutura de Definição

As políticas são definidas em arquivos YAML no diretório `config/agent-policies/`.

```yaml
global_policies:
  - name: max_steps_by_risk
    description: "Limits execution steps based on agent risk score"
    rules:
      - if: "risk_score < 10"
        then: { max_steps: 50 }
```

## Score de Risco

O `AgentRiskEngine` calcula dinamicamente o risco de cada operação considerando:

1. **Nível do Agente**: Definido no registro (low, medium, high, critical).
2. **Capacidades**: Quantidade e tipo de ferramentas permitidas.
3. **Ação Específica**: Se a tarefa envolve gravação de memória, acesso externo ou deleção de dados.

## Integração com HITL (Human-in-the-loop)

Quando o motor de políticas retorna `require_approval`, a execução do agente é pausada e uma solicitação de aprovação é gerada no dashboard administrativo. A corrida só prossegue após a intervenção humana.
