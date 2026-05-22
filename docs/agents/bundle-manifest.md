# Agent Bundle Manifest

O arquivo `manifest.json` é o coração de um Agent Bundle. Ele segue o seguinte esquema:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `name` | string | ID único do bundle. |
| `version` | string | Versão semântica (ex: 1.0.0). |
| `description` | string | Breve resumo das capacidades do agente. |
| `author` | string | Criador do bundle. |
| `min_platform_version` | string | Versão mínima do stack necessária. |
| `agent_definition` | object | Configuração base da tabela `agent_definitions`. |
| `tool_requirements` | list | Ferramentas que devem estar registradas no tenant. |
| `memory_policy` | object | Política de retenção sugerida. |
| `eval_suite` | object | Casos de teste iniciais. |
| `signature` | string | Assinatura digital do manifest (opcional). |

## Exemplo

```json
{
  "name": "example-agent",
  "version": "1.0.0",
  "agent_definition": {
    "instructions": "Be helpful.",
    "model_id": "gpt-4o"
  }
}
```
