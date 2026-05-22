# Memory Redaction

Before any agent memory is stored in the database, the system executes redaction protocols (if enabled by the corresponding retention policy).

## Supported Mechanisms
- **Secrets Block**: The platform includes a heuristic heuristic `SecretFoundError` block for highly sensitive material (e.g. `sk-`, `api_`). If the platform detects these patterns, the write is aborted entirely.
- **PII Scrubbing**: `MemoryRedactionService` actively scrubs text to replace emails and predefined tokens (e.g., `email@`, `secret-`) with `[REDACTED]` tokens. 

## Tracking
Whenever a redaction happens, an `AgentMemoryRedactionEvent` is recorded to help operators understand how often user data is triggering redaction filters. This enables the fine-tuning of redaction patterns over time without accessing raw PII.
