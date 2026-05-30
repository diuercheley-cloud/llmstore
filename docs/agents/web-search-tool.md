# Web Search Tool for Agents

The Web Search Tool allows agents executing within the `llm-inference-stack` to retrieve
real-time information from the internet or simulated environments. Execution is governed by strict
security policies, caching, rate limiting, and audit trails.

## Feature Flags

The behavior of the Web Search Tool is governed by the following environment feature flags:

*   `AGENT_WEB_SEARCH_ENABLED` (Default: `false`): Enables or disables the web search tool adapter.
    If disabled, attempts by agents to execute searches are blocked.
*   `AGENT_WEB_SEARCH_EXTERNAL_NETWORK_ENABLED` (Default: `false`): Governs whether real HTTP
    requests can be sent to external networks. When set to `false`, the real provider raises an
    exception, forcing offline/mock mode or rejection.
*   `AGENT_WEB_SEARCH_ALLOWLIST_ENABLED` (Default: `true`): Determines whether target domains
    returned by search providers are filtered using the configured domain allowlist.

## Search Providers

The Web Search Tool supports two provider backends:

1.  **Mock Provider (`mock`)**: Default offline provider. Returns deterministic mock results,
    simulating search queries. It also simulates prompt injection payloads to test safety hooks.
2.  **HTTP Provider (`http`)**: Sends external search requests via HTTP clients. Only works if
    `AGENT_WEB_SEARCH_EXTERNAL_NETWORK_ENABLED` is set to `true`.

## Caching

To optimize execution speed and control network egress, search queries are cached with a
configurable TTL:
*   A unique hash of the query is computed.
*   Upon cache hit, the cached results are re-filtered and sanitized (ensuring domain updates and
    safety logic are applied to cached content).
*   Upon cache miss, the provider fetches fresh results, which are then stored in the cache.

## Registry Integration

The Web Search Tool adapter is registered with the platform's `ToolRegistry` with the following
governance attributes:
*   **Risk Level**: `medium`
*   **Side Effect Level**: `external_read`
*   **Approval**: Configurable via tool policy (optional human or administrative approval).

## Execution Outputs

The tool returns structured metadata that can be parsed by agent executors:
*   `query_hash`: Unique SHA-256 hash of the search query.
*   `results`: List of sanitized results, containing `title`, `snippet`, `url`, `provider`,
    `retrieved_at`, and `confidence`.
*   `citation`: Text representation of citations/provenance for inclusion in agent context.
*   `audit_event_id`: UUID reference to the recorded audit event.
*   `result_ids`: UUID list of individual database result logs.
