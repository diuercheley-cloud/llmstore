# Agent Step Caching

## Overview
Step caching allows the platform to reuse results from previous agent steps (specifically LLM decisions) when the same input context is encountered. This significantly reduces operational costs by avoiding redundant model calls.

## How it works
1. **Context Hashing**: The executor generates a SHA-256 hash of the current context, which includes:
   - Agent instructions
   - User input
   - Current step count (to ensure context awareness)
2. **Lookup**: Before calling the LLM, the executor checks the `agent_step_cache_entries` table for a valid, non-expired entry matching the hash, `agent_id`, `tenant_id`, and `model_version`.
3. **Execution**:
   - **Cache Hit**: The cached decision is returned immediately, skipping the LLM provider call.
   - **Cache Miss**: The LLM is called normally, and the result is stored in the cache.

## Cacheability Rules
To ensure safety and correctness, not all steps are cached:
- **Side Effects**: Decisions to call tools with side effects (write, destructive, external) are only cached for the decision itself, not the tool result.
- **Explicit Exclusions**: `memory_write` and `handoff` operations are never cached.
- **TTL**: Cache entries have a default TTL of 24 hours.

## Database Model
Stored in `agent_step_cache_entries`:
- `agent_id`
- `tenant_id`
- `step_type`
- `input_hash`
- `output_data` (JSON)
- `expires_at`
