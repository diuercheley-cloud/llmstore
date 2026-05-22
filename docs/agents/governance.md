# Agent Governance

A governança de agentes é centralizada através de um motor de políticas baseado em código (Policy-as-Code), permitindo a aplicação consistente de regras de segurança, custo e conformidade.

## Motor de Políticas

O `AgentPolicyEngine` avalia cada ação pretendida pelo agente antes de sua execução real. Ele integra dados do agente, do inquilino (tenant) e do ambiente para tomar decisões.

### Decisões Possíveis

- `allow`: Ação permitida.
- `deny`: Ação bloqueada permanentemente.
- `require_approval`: Ação permitida apenas após aprovação humana explicita.
- `require_dry_run`: Ação permitida apenas em modo de simulação.

## Políticas Implementadas

| Política | Descrição |
|----------|-----------|
| `max_steps_by_risk` | Limita o número de passos de execução com base no score de risco do agente. |
| `block_destructive_tools` | Bloqueia ou exige aprovação para ferramentas que deletam ou alteram dados críticos. |
| `no_shell_tool_by_default` | Proíbe o uso de ferramentas de terminal/shell por padrão. |
| `sovereign_isolation` | Impede chamadas para APIs externas quando o sistema opera em modo soberano. |
| `baseline_required` | Impede que agentes sejam ativados em produção sem um baseline de avaliação bem-sucedido. |

## Auditoria e Simulação

Todas as decisões do motor de políticas são registradas para auditoria. Operadores podem usar o endpoint de simulação para testar como novas políticas afetariam agentes existentes sem risco de interrupção.
