# Context Compression

As conversations grow, they may exceed the LLM's context window (token limit). The platform implements automatic context compression to maintain continuity.

## Mechanism

- **Threshold Detection**: Compression is triggered when estimated tokens exceed `max_tokens_threshold`.
- **Selective Preservation**:
  - System prompts and core instructions are always preserved.
  - The latest N messages are kept intact.
  - Key events like tool results, approvals, and citations are prioritized.
  - The "middle" part of the conversation is summarized into a concise block.

## Security

The `ContextCompressor` automatically redacts potential secrets (keys, tokens, passwords) before sending summarized content back to the LLM.

- `AGENT_CONTEXT_COMPRESSION_ENABLED`: Global toggle.
