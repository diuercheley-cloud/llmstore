# MCP Trust Model

## Security Architecture
The MCP client acts as an intermediary for large language models to interact with real-world infrastructure safely.
- **Tenant Isolation**: Registry records encapsulate `tenant_id`. Executions check this identity prior to resolving transport streams.
- **Tool Whitelists**: Execution of tools is fundamentally deny-by-default. Tools must be appended to the `approved_tools` map by an authorized operation.
- **Sanitization**: Tool descriptions (the surface area exposed to agents) are scrubbed for potential prompt injections. `<system>` blocks and known escape signatures are explicitly removed.
- **Production Exclusivity**: Implicit simulation states are disabled when `app_env == 'production'`.
