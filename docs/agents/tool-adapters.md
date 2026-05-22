# Tool Adapters

Tool Adapters provide a standardized layer for real, versioned, and executable tools in the agentic runtime.

## Overview

Unlike simulated tools that only return mock responses, Tool Adapters implement the `ToolAdapterContract` to perform real-world operations such as HTTP requests, database reads, or RAG searches.

## Configuration

Tool adapters are governed by several feature flags:

- `AGENT_TOOL_ADAPTERS_ENABLED`: Global toggle for all tool adapters.
- `AGENT_HTTP_TOOL_ENABLED`: Specifically enables the `http_get_tool`.
- `AGENT_DB_READ_TOOL_ENABLED`: Specifically enables the `database_read_tool`.
- `AGENT_SHELL_TOOL_ENABLED`: Specifically enables the `shell_command_tool`.

## Registration

Adapters are registered during application startup in `app.main.lifespan` via `register_all_adapters()`.

```python
from app.services.agents.tool_adapter_registry import adapter_registry
from app.services.agents.tool_adapters.echo_tool import EchoToolAdapter

adapter_registry.register(EchoToolAdapter())
```

## Security & Governance

- **Sandbox**: Executions can be restricted to a secure sandbox.
- **Approval**: Destructive or write-level tools require explicit human approval by default.
- **Dry Run**: All write/destructive tools must implement a `dry_run` method for safe simulation.
- **Audit**: Every tool invocation, whether via adapter or simulation, is logged in the audit trail.
