# Knowledge Graph

The default knowledge graph provider is `internal_sql`.

- `AGENT_KNOWLEDGE_GRAPH_ENABLED=false`
- `AGENT_KG_PROVIDER=internal_sql`
- `AGENT_KG_WRITE_ENABLED=false`

The graph is tenant-scoped and blocks cross-tenant access. Secret-like content is redacted before persistence.
