---
owner: platform-ops
status: consolidated
---

# Memory Poisoning Playbook

## Descrição
Acionado quando o histórico de memória do agente contém dados maliciosos, instruções conflitantes ou informações sensíveis que não deveriam ter sido persistidas.

## Sintomas
- Agente apresentando comportamento errático (alucinações ou recusa de ordens válidas).
- Detecção de segredos ou PII em itens de memória.
- Falhas de segurança disparadas por conteúdo injetado.

## Procedimento de Resposta
1. **Isolamento**: Identifique os itens de memória suspeitos.
2. **Quarentena**: Execute `scripts/agent-quarantine-memory.sh`. Isso moverá os itens para uma tabela de `tombstone` sem excluí-los permanentemente.
3. **Limpeza**: Limpe o cache de contexto do agente.
4. **Verificação**: Teste o agente em ambiente de sandbox para garantir que o comportamento voltou ao normal.

## Ação Destrutiva
- **Quarantine Memory**: Remove itens do contexto ativo. Requer backup automático antes da movimentação.
