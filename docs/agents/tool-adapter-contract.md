---
owner: platform-ops
status: consolidated
---

# Tool Adapter Contract

All tool adapters must implement the `ToolAdapterContract` abstract base class.

## Interface

### Properties

- `name`: The canonical name of the tool (e.g., `echo_tool`).
- `version`: Semantic version (e.g., `1.2.0`).
- `input_schema`: JSON Schema for input parameters.
- `output_schema`: JSON Schema for the output dictionary.
- `side_effect_level`: One of `none`, `read`, `write`, `destructive`, `external`.

### Methods

- `execute(**kwargs)`: Performs the actual operation.
- `dry_run(**kwargs)`: Simulates the operation. Mandatory for tools with side effects.
- `rollback(invocation_id, **kwargs)`: Attempts to undo changes from a previous execution.
- `healthcheck()`: Returns `True` if the tool is ready for use (e.g., dependencies are up).

## Example Implementation

```python
from app.services.agents.tool_adapter_contract import ToolAdapterContract

class MyToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    # ... schemas and side_effect_level ...

    async def execute(self, **kwargs):
        # Implementation logic
        return {"status": "ok"}

    async def dry_run(self, **kwargs):
        return {"status": "dry_run"}

    async def rollback(self, invocation_id, **kwargs):
        return {"status": "reverted"}

    async def healthcheck(self):
        return True
```
