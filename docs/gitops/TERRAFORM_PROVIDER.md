# Terraform Provider: LLM Stack

Este provider permite gerenciar recursos do `llm-inference-stack` via Infraestrutura como Código (IaC).

## Recursos Suportados

- `llmstack_tenant`: Gerencia tenants/clientes.
- `llmstack_agent`: Gerencia definições de agentes.
- `llmstack_policy`: Gerencia políticas de segurança Rego.
- `llmstack_model_route`: Configura o roteamento de modelos para backends.

## Exemplo de Uso

```hcl
provider "llmstack" {
  api_url = "http://llm-stack.local"
  api_key = "admin-secret-token"
}

resource "llmstack_tenant" "engineering" {
  name        = "Engineering"
  description = "Engineering department cluster"
}

resource "llmstack_agent" "support" {
  name          = "Support Bot"
  model         = "gpt-4-local"
  system_prompt = "You are a helpful support agent."
}
```

## Como Compilar (Futuro)

```bash
go build -o terraform-provider-llmstack
```
