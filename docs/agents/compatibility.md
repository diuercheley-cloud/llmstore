---
owner: platform-ops
status: consolidated
---

# Compatibility Policy

Para garantir a estabilidade do `llm-inference-stack`, especialmente em ambientes de missão crítica e multi-tenant, seguimos uma política rigorosa de compatibilidade para contratos de agentes.

## Níveis de Compatibilidade

### backward (Retroativa)
- **Regra**: O sistema novo deve aceitar payloads no formato antigo.
- **Ação**: Adição de campos opcionais é permitida. Remoção de campos ou alteração de tipos obrigatórios exige nova versão major do contrato.

### strict (Estrita)
- **Regra**: O payload deve casar exatamente com o schema da versão solicitada.
- **Uso**: Operações financeiras, assinaturas de recibos ou auditorias de alta segurança.

## Ciclo de Vida de Depreciação

1. **Introdução**: Nova versão do contrato é lançada (ex: v2). v1 entra em status `supported`.
2. **Depreciação**: v1 entra em status `deprecated`. Headers `X-Deprecated-Endpoint` ou avisos em logs são emitidos.
3. **Fim de Vida (EOL)**: v1 é removido do codebase. Requisições falham com erro de versão.

## Version Mismatch

Quando uma versão incompatível é detectada (ex: um worker v1 tentando processar um job que exige v2), o sistema deve:
- Rejeitar a execução imediatamente.
- Registrar um evento `contract_version_mismatch` na timeline da run.
- Retornar uma `ContractValidationError` clara indicando a versão esperada vs. recebida.
