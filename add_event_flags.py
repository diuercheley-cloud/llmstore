import yaml

with open('config/feature-flags.yaml', 'r') as f:
    flags = yaml.safe_load(f)

new_flags = [
    {
        "name": "AGENT_EVENT_DRIVEN_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "medium",
        "dependencies": [],
        "conflicts": [],
        "safe_default_reason": "Event-driven agents disabled by default."
    },
    {
        "name": "AGENT_EVENT_HOOKS_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "medium",
        "dependencies": ["AGENT_EVENT_DRIVEN_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Event hooks disabled by default."
    },
    {
        "name": "AGENT_CRON_TRIGGERS_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "medium",
        "dependencies": ["AGENT_EVENT_DRIVEN_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Cron triggers disabled by default."
    },
    {
        "name": "AGENT_PUBSUB_TRIGGERS_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "medium",
        "dependencies": ["AGENT_EVENT_DRIVEN_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "PubSub triggers disabled by default."
    },
    {
        "name": "AGENT_EXTERNAL_WEBHOOK_TRIGGERS_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "active",
        "introduced_in": "v2.0.0-agentic-ai-platform",
        "risk_level": "high",
        "dependencies": ["AGENT_EVENT_DRIVEN_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "External webhook triggers disabled by default due to exposure risk."
    }
]

existing_names = {f['name'] for f in flags}
for nf in new_flags:
    if nf['name'] not in existing_names:
        flags.append(nf)

with open('config/feature-flags.yaml', 'w') as f:
    yaml.dump(flags, f, default_flow_style=False, sort_keys=False)
