# Web Search Governance and Safety

The Web Search Tool implements layered governance controls to ensure agents can access
external information safely without compromising compliance, security boundaries, or system
integrity.

## Safe Search & Domain Allowlist/Blocklist

Search results are filtered using strict domain rules:
*   **Domain Filtering**: If `AGENT_WEB_SEARCH_ALLOWLIST_ENABLED` is active, results from domains
    not present in the system's allowlist are automatically discarded before being returned to
    the agent.
*   **SafeSearch Hook**: A SafeSearch and content filtering mechanism is triggered for each
    query and result snippet to prevent retrieving harmful, toxic, or out-of-bounds content.

## Rate Limiting

To prevent abuse, resource exhaustion, or financial overhead from external API usage, the system
enforces strict rate limiting:
*   Limits are defined per tenant and agent context.
*   Rate limit policies are enforced at the database level before execution. Exceeding limits
    will log a policy exception event and block the search request.

## Prompt Injection Mitigation

External web pages may contain malicious instruction payloads designed to hijack the executing
agent. The safety engine implements:
*   **Sanitization Hooks**: Result titles and snippets are scanned for potential prompt injection
    heuristics or forbidden directives.
*   **Content Redaction**: Detected injection attempts are redacted, replaced with a safe warning,
    and logged as policy security events (e.g. `prompt_injection_sanitized`).

## Auditing and Policy Events

All web search requests write detailed historical records to the database for security compliance:
*   **Queries (`agent_web_search_queries`)**: Logs the query text, its hash, tenant ID, and
    provider mode.
*   **Results (`agent_web_search_results`)**: Logs every returned search result, linking back
    to the query.
*   **Policy Events (`agent_web_search_policy_events`)**: Logs security events, including
    when the tool is disabled, when domain blocks occur, and when prompt injections are sanitized.
