# Memory Retention Policies

Políticas de retenção garantem que a memória do agente não cresça indefinidamente e respeite regulamentações de privacidade (como LGPD/GDPR).

## Funcionamento

Cada item de memória é gravado com uma data `retention_until`. Esta data é calculada com base na `AgentMemoryPolicy` aplicável no momento da escrita.

### Níveis de Política

1. **Agent-Specific**: Uma política definida explicitamente para um `agent_id`.
2. **Tenant-Default**: Uma política geral para o `tenant_id` que se aplica a todos os seus agentes.

## Ciclo de Vida de Limpeza

O job de retenção (`AgentMemoryRetentionJob`) executa periodicamente (geralmente uma vez por dia) e realiza as seguintes operações:

1. Identifica itens onde `retention_until < AGORA`.
2. Deleta fisicamente os registros da tabela `agent_memory_items`.
3. Registra um evento de auditoria resumindo a quantidade de itens removidos.

## Exemplos de Retenção

- **Short-term**: Geralmente 24h a 7 dias. Foca no contexto imediato.
- **Long-term**: 30 dias a 1 ano (conforme contrato com o cliente).
- **Episodic**: Retenção variável baseada na relevância da tarefa realizada.
