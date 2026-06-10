# Terraform Provider for LLM Stack

Allows managing LLM Stack resources (Tenants, Agents, Policies, Routes) via Terraform.

## Development

Requires Go 1.21+ and Terraform 1.0+.

```bash
make build
make test
```

## Resources

- `llmstack_tenant`
- `llmstack_agent`
- `llmstack_policy`
- `llmstack_model_route`
