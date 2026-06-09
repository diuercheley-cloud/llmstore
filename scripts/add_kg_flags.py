import yaml

with open('config/feature-flags.yaml', 'r') as f:
    flags = yaml.safe_load(f)

new_flags = [
    {
        "name": "AGENT_KNOWLEDGE_GRAPH_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "medium",
        "dependencies": [],
        "conflicts": [],
        "safe_default_reason": "Knowledge graph disabled by default until explicitly enabled by operator."
    },
    {
        "name": "AGENT_GRAPH_RAG_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "medium",
        "dependencies": ["AGENT_KNOWLEDGE_GRAPH_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Graph RAG disabled by default."
    },
    {
        "name": "AGENT_GRAPH_WRITE_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "high",
        "dependencies": ["AGENT_KNOWLEDGE_GRAPH_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Graph writing disabled by default to prevent uncontrolled data ingestion."
    },
    {
        "name": "AGENT_GRAPH_EXTERNAL_DB_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "high",
        "dependencies": ["AGENT_KNOWLEDGE_GRAPH_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "External DB connection disabled by default."
    }
]

# Ensure we don't add duplicates
existing_names = {f['name'] for f in flags}
for nf in new_flags:
    if nf['name'] not in existing_names:
        flags.append(nf)

with open('config/feature-flags.yaml', 'w') as f:
    yaml.dump(flags, f, default_flow_style=False, sort_keys=False)
