---
owner: platform-ops
status: consolidated
---

# Tenant Agentic Readiness

Este documento descreve o processo de validação de prontidão (readiness) para agentes em um ambiente multi-tenant. Cada tenant no LLM Inference Stack possui seu próprio relatório de prontidão, garantindo isolamento e conformidade antes da execução de cargas de trabalho agentic.

## Pilares de Prontidão

Para que um tenant seja considerado "Ready", ele deve atender aos seguintes critérios:

### 1. Isolamento de Memória (Memory Readiness)
- **Consentimento (Consent)**: O tenant deve possuir registros ativos de consentimento de usuário para persistência de memória. Sem consentimento, o acesso à memória é **BLOQUEADO**.
- **Política (Policy)**: Deve existir pelo menos uma política de retenção e redação configurada. Se ausente, um **AVISO (Warning)** é gerado.

### 2. Governança Financeira (Budget Policy)
- O tenant deve possuir limites de custo (`max_cost_brl`) e tokens configurados para seus agentes.
- Tenants sem políticas de orçamento operam com um aviso de risco financeiro.

### 3. Validação de Performance (Eval Baselines)
- Para promover agentes ao estado de `production`, o tenant deve possuir datasets de avaliação (`eval_dataset`) no catálogo.
- A ausência de baselines impede a promoção automática.

### 4. Isolamento de Observabilidade
- Verificação se as métricas do Prometheus e traces do OpenTelemetry estão corretamente tageados com o `tenant_id`.
- Garante que um operador de um tenant não consiga visualizar performance de agentes de outros tenants.

### 5. Ferramentas e Permissões
- Validação se o `Allowed Tools` registry está configurado corretamente para o tenant.

## API de Consulta

O relatório completo pode ser obtido via:

`GET /admin/tenants/{tenant_id}/agentic-readiness`

### Exemplo de Resposta:

```json
{
  "tenant_id": "tenant-123",
  "overall_status": "warning",
  "checks": {
    "memory_readiness": {
      "status": "ready",
      "message": "Memory consent and policy check.",
      "details": { "has_consent": true, "has_policy": true }
    },
    "budget_policy": {
      "status": "warning",
      "message": "Budget policy check (no agents with limits).",
      "details": { "has_limits": false }
    }
  }
}
```

## CLI de Diagnóstico

Administradores podem rodar o diagnóstico via terminal:

```bash
./scripts/dev/tenant-agentic-readiness.sh <tenant_id>
```
