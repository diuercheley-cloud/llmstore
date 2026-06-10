# MCP Real Client

> Owner: agent-platform | Status: beta

## Overview

The MCP client implements the [Model Context Protocol](https://modelcontextprotocol.io) to discover and execute tools from external MCP servers.

Previous behavior (hardcoded mock tool list) is **completely removed**. Discovery is now:
1. **Real**: contacts the MCP server via HTTP or stdio transport
2. **Flagged-mock**: returns a marked-mock catalogue ONLY when `AGENT_MCP_MOCK_MODE=true`
3. **Blocked**: raises `PermissionError` when neither is permitted

---

## Architecture

```
Admin API
  POST /admin/agents/mcp/servers          → register server
  POST /admin/agents/mcp/servers/{id}/discover  → trigger discovery
  POST /admin/agents/mcp/servers/{id}/approve-tool
  POST /admin/agents/mcp/tools/{name}/call
  GET  /admin/agents/mcp/audit
      │
      ▼
  MCPClient
    ├─ MCPRegistry   (server config store)
    ├─ MCPSecurity   (flag gates, sanitization, trust)
    ├─ MCPTransport  (HTTP or stdio)
    │     ├─ HttpTransport   (streamable_http / http)
    │     └─ StdioTransport  (stdio — local subprocess)
    ├─ MCPToolAdapter
    ├─ MCPResourceAdapter
    ├─ MCPPromptAdapter
    └─ MCPAuditLog
```

---

## Discovery Flow

```
discover(server_id)
  │
  ├─ require_client_enabled()          # AGENT_MCP_CLIENT_ENABLED
  ├─ mock mode? → _mock_discover()     # AGENT_MCP_MOCK_MODE=true
  ├─ require_real_discovery()          # AGENT_MCP_REAL_DISCOVERY_ENABLED
  ├─ validate_external_network()       # AGENT_MCP_EXTERNAL_NETWORK_ENABLED
  ├─ build_transport(type, endpoint)
  ├─ transport.initialize()            # MCP handshake
  ├─ validate_sampling(caps)           # block if server wants sampling
  ├─ tools/list  → sanitize each tool
  ├─ resources/list
  ├─ prompts/list
  └─ MCPAuditLog.record(mcp_discover)
```

---

## Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MCP_ENABLED` | `false` | Master MCP toggle |
| `AGENT_MCP_CLIENT_ENABLED` | `false` | Client-side discovery and call |
| `AGENT_MCP_REAL_DISCOVERY_ENABLED` | `false` | Enable real protocol discovery |
| `AGENT_MCP_MOCK_MODE` | `false` | Mock catalogue (test/staging ONLY) |
| `AGENT_MCP_EXTERNAL_NETWORK_ENABLED` | `false` | Allow non-localhost HTTP |
| `AGENT_MCP_SAMPLING_ENABLED` | `false` | Allow servers that request sampling |
| `AGENT_MCP_CALL_TIMEOUT_MS` | `10000` | Per-call timeout |
| `AGENT_MCP_CALL_MAX_RETRIES` | `2` | Retries on transient errors |

> [!CAUTION]
> `AGENT_MCP_MOCK_MODE=true` **must never be set in production**.
> Mock tools carry `mock=true` so callers can detect them, but real tool execution will never be attempted.

---

## Tool Approval

Every tool must be explicitly approved before `call_tool()` will execute it:

```bash
curl -X POST /admin/agents/mcp/servers/{id}/approve-tool \
  -H 'Authorization: Bearer $ADMIN_TOKEN' \
  -d '{"tool_name": "echo"}'
```

Unapproved calls raise `PermissionError` with:
> *MCP tool 'echo' is not in the approved list for this server.*

---

## Tool Call

```bash
# Via admin API
curl -X POST /admin/agents/mcp/tools/echo/call \
  -H 'Authorization: Bearer $ADMIN_TOKEN' \
  -d '{"tool_name": "echo", "arguments": {"__server_id": "<server-id>", "text": "hello"}}'
```

Every call generates three audit events:
- `mcp_call_attempt` (always, before execution)
- `mcp_call_success` (on success)
- `mcp_call_error` (on failure — exception is re-raised)

---

## Transport Types

| transport | Value | Description |
|-----------|-------|-------------|
| HTTP | `streamable_http` or `http` | POST JSON-RPC to endpoint |
| stdio | `stdio` | Launch subprocess, read/write JSON-RPC lines |

```bash
# Register an HTTP server
curl -X POST /admin/agents/mcp/servers \
  -d '{"tenant_id": "acme", "name": "my-server",
       "transport": "streamable_http",
       "endpoint": "https://api.example.com/mcp",
       "trust_level": "low"}'

# Register a local stdio server
curl -X POST /admin/agents/mcp/servers \
  -d '{"tenant_id": "acme", "name": "local-kg",
       "transport": "stdio",
       "endpoint": "/usr/local/bin/kg-mcp-server",
       "trust_level": "medium"}'
```

---

## Audit Log

```bash
# All events
GET /admin/agents/mcp/audit

# Filtered
GET /admin/agents/mcp/audit?event_type=mcp_call_success&server_id=<id>&limit=50
```

Audit fields: `event_type`, `timestamp`, `tenant_id`, `server_id`, `tool_name`, `elapsed_ms`, `mock`.

---

## Testing

```bash
pytest tests/unit/services/test_mcp_client.py -v
```

Key test cases:

| Test | What it verifies |
|------|------------------|
| `test_real_discovery_returns_server_tools` | Fake server tools discovered correctly |
| `test_hardcoded_mock_not_returned_by_default` | No mock list without flag |
| `test_mock_mode_returns_mock_flag` | Mock tools carry mock=true |
| `test_unapproved_tool_blocks_call` | Approval gate enforced |
| `test_external_network_disabled_blocks_real_endpoint` | Network flag enforced |
| `test_malicious_tool_description_sanitized` | Injection patterns removed |
| `test_sampling_advertised_by_server_blocks_discover` | Sampling blocked |
| `test_call_tool_records_attempt_and_success_audit` | Full audit trail |
