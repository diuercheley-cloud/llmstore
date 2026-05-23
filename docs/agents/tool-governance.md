# Agentic Tool Governance

O `llm-inference-stack` impõe uma governança rigorosa sobre todas as ferramentas (tools) executáveis por agentes. Nenhuma ferramenta pode ser registrada ou executada sem metadados de segurança, limites operacionais e políticas de aprovação claros.

## Princípios de Governança

### 1. Registro Obrigatório
Toda ferramenta deve declarar explicitamente:
- **`risk_level`**: Nível de risco (`low`, `medium`, `high`, `critical`). Ferramentas sem nível de risco não são registradas.
- **`side_effect_level`**: Impacto da execução (`none`, `read`, `write`, `destructive`, `external`).
- **`timeout_seconds`**: Tempo máximo de execução. Obrigatório para evitar travamentos do runtime.
- **`data_boundary`**: Obrigatório para ferramentas de categoria `external_api` ou side-effect `external`. Define o limite de circulação de dados.

### 2. Políticas de Execução e Aprovação
- **Aprovação Humana**: Ferramentas com `side_effect` do tipo `write` ou `destructive` exigem obrigatoriamente uma `approval_policy`. A execução é pausada até que um humano ou política automática superior valide a ação.
- **Desativação por Padrão**: Categorias sensíveis como `shell_command`, `external_api` e `database_write` são registradas como `disabled` por padrão, exigindo ativação manual administrativa.

### 3. Limites Operacionais (Budgets)
- **`max_cost_brl`**: Orçamento financeiro por execução de ferramenta.
- **`max_calls_per_run`**: Limite de invocações de uma mesma ferramenta dentro de uma única Run de agente para evitar loops infinitos ou exaustão de quota.
- **Conservative Default**: Ferramentas sem orçamento explícito recebem um budget conservador de 0.50 BRL.

### 4. Idempotência e Retentativas
O runtime suporta retentativas automáticas (`retry_policy`) apenas para ferramentas **idempotentes** (side-effect `none` ou `read`). 
- Ferramentas que causam mutações (`write`, `destructive`) nunca são retentadas automaticamente para evitar efeitos colaterais duplicados em caso de timeout parcial.

## Ciclo de Vida de Segurança
1.  **Validation**: Verificação de schemas e metadados no `tool_registry`.
2.  **Policy Check**: Validação de RBAC e permissões de tenant no `tool_policy`.
3.  **Audit**: Cada tentativa, sucesso ou falha é registrada com hashes de payload no `tool_audit`.
4.  **Sandbox**: Execução em ambiente isolado (se habilitado) com monitoramento de recursos.
