# Memory Context Injection

## Overview

Memory context injection retrieves semantically relevant memories and injects them into the LLM's system prompt before each `model_call` step. This allows the agent to reason with past knowledge without requiring explicit `memory_read` tool calls.

## Flow

```
execute_step() called
    |
    v
Build memory context (MemoryContextBuilder)
    |
    ├── Retrieve relevant memories (MemoryRetriever)
    ├── Build "Relevant Memory" block
    ├── Track memory_ids
    └── Enforce max_tokens limit
    |
    v
Augment agent_def.instructions with context block
    |
    v
LLM generate() ← sees memory in system prompt
    |
    v
Restore original instructions
    |
    v
Log memory_ids in step_metadata
```

## Context Block Format

```
## Relevant Memory
The following information was retrieved from the agent's long-term memory:
- Summary: content
- Another memory: content
```

Positioned at the end of the system instructions before the user message.

## Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MEMORY_CONTEXT_INJECTION_ENABLED` | `false` | Enables memory injection before model_call |
| `AGENT_MEMORY_SEMANTIC_SEARCH_ENABLED` | `false` | Required for semantic (vector) retrieval |
| `AGENT_MEMORY_ENABLED` | `false` | Master switch for all memory features |

## Token Budget

The context block is limited to `max_tokens` (default 1024). Memories are added in score order until the budget is exhausted.

```python
for mem in sorted_memories:
    mem_tokens = estimate_tokens(content) + estimate_tokens(summary)
    if total_tokens + mem_tokens > max_tokens:
        continue
    lines.append(f"- {summary}: {content}")
    memory_ids.append(str(mem.item.id))
    total_tokens += mem_tokens
```

`estimate_tokens` uses a simple heuristic: `len(text) // 4`.

## Security

- **No secrets**: Memories containing secret patterns (`sk-`, `api_`, `key_`, `password`, etc.) are excluded
- **No cross-tenant**: All queries filter by `tenant_id`
- **Redaction**: PII patterns are redacted before injection
- **Consent**: Long-term memories require active user consent

## Observability

After injection, the model_call step records `memory_ids` in its metadata:

```json
{
    "step_type": "model_call",
    "metadata": {
        "memory_ids": ["uuid-1", "uuid-2"],
        ...
    }
}
```

Each injected memory also gets a `memory_read` access event logged.

## Testing

- `test_context_injection_builds_block` — verifies block is built with "Relevant Memory" header
- `test_context_token_limit_is_respected` — verifies token budget enforcement
- `test_secret_like_memory_not_reinjected` — secrets are excluded
- `test_memory_ids_appear_in_step_metadata` — memory_ids tracked
- `test_context_injection_disabled_by_default` — feature flag off returns empty
