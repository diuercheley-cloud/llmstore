# LLM Inference Stack — Complete Documentation

## Overview

The LLM Inference Stack is a production-grade AI Agentic Platform that enables you to build, deploy, monitor, and scale AI agents across 18+ LLM providers. It provides a complete runtime for agent execution with built-in guardrails, memory, tools, multi-agent orchestration, and enterprise governance.

---

## Quick Start

### Installation

```bash
# Install the Python SDK
pip install kleberai

# Or use the CLI directly
agentctl --help
```

### Create Your First Agent

```bash
# Scaffold from template
agentctl scaffold hello-world --name my-first-agent

# Deploy to the platform
agentctl create ./my-first-agent/agent.json
```

### Run an Agent

```bash
agentctl run <agent-id> --input "Hello! What can you do?"
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Admin UI / CLI                        │
├──────────────────────────────────────────────────────────┤
│                     API Gateway                           │
├────────┬────────┬────────┬────────┬────────┬─────────────┤
│ Agent  │ Multi- │ Guard- │ Mem-   │ Tool   │ MCP         │
│Runtime │Agent   │rails   │ory     │Registry│ Protocol    │
├────────┼────────┼────────┼────────┼────────┼─────────────┤
│  18 LLM Providers (OpenAI, Anthropic, Gemini, ...)       │
├────────┼────────┼────────┼────────┼────────┼─────────────┤
│  Deployments │ Canary │ Rollback │ Autoscaling │ Backup  │
├────────┼────────┼────────┼────────┼────────┼─────────────┤
│  Monitoring (Grafana) │ Alerting (PagerDuty/OpsGenie)    │
├────────┼────────┼────────┼────────┼────────┼─────────────┤
│  Auth (SSO/RBAC)  │  Rate Limiting  │  Tenant Isolation  │
└────────┴────────┴────────┴────────┴────────┴─────────────┘
```

---

## Core Concepts

### Agents
Agents are the fundamental building block. Each agent has a system prompt, a model assignment, tool access, and memory configuration. Agents can be versioned, deployed, and monitored.

```yaml
# agent.yaml
name: my-agent
version: 1.0.0
model: gpt-4o
system_prompt: "You are a helpful assistant specialized in data analysis."
tools:
  - database_read
  - rag_search
memory: long_term
```

### Multi-Agent Orchestration
Agents can be composed into teams using patterns:
- **Specialist Routing**: A dispatcher agent routes tasks to specialist agents
- **Workflow DAG**: Define directed acyclic graphs of agent tasks with conditional branching
- **A2A Protocol**: Inter-agent communication using the Google A2A standard

### Guardrails
Every agent run passes through multiple safety layers:
1. **Prompt Injection Detection**: 15+ regex patterns for jailbreak attempts
2. **Content Moderation**: Toxicity scoring with configurable thresholds
3. **PII Redaction**: Email, phone, credit card detection and redaction
4. **Secret Detection**: API keys, tokens, and credentials in input/output
5. **Output Validation**: Refusal detection, secret leak prevention

### Memory System
Agents have comprehensive memory capabilities:
- **Working Memory**: Short-term, TTL-scoped context
- **Episodic Memory**: Conversation history
- **Semantic Memory**: Long-term knowledge with vector search
- **Federated Memory**: Cross-cluster memory synchronization

### Tool Registry
Tools are centrally managed with governance controls:
- **Categories**: retrieval, database, filesystem, shell, external_api, admin
- **Risk Levels**: low, medium, high, critical
- **Approval**: Write/destructive tools require human approval
- **Sandboxing**: Code execution in isolated environments (Firecracker microVMs)

---

## Providers

18 LLM providers supported with unified interface:

| Provider | Models | Vision | JSON Mode | Streaming |
|----------|--------|--------|-----------|-----------|
| OpenAI | gpt-4o, gpt-4o-mini, o3 | ✓ | ✓ | ✓ |
| Anthropic | claude-3.5-sonnet, claude-3-haiku | ✓ | ✓ | ✓ |
| Google Gemini | gemini-2.0-flash, gemini-2.0-pro | ✓ | ✓ | ✓ |
| AWS Bedrock | claude, llama, mistral | ✓ | ✓ | ✓ |
| Azure OpenAI | gpt-4o, gpt-4o-mini | ✓ | ✓ | ✓ |
| DeepSeek | deepseek-chat, deepseek-reasoner | ✗ | ✓ | ✓ |
| Mistral | mistral-large, mistral-small | ✓ | ✓ | ✓ |
| Groq | llama-3.3-70b, mixtral | ✓ | ✓ | ✓ |
| Together AI | llama-3.3-70b, deepseek | ✓ | ✓ | ✓ |
| Perplexity | sonar-pro, sonar-reasoning | ✓ | ✓ | ✓ |
| Replicate | llama-3.3-70b | ✓ | ✓ | ✓ |
| xAI | grok-2, grok-2-mini | ✓ | ✓ | ✓ |
| Fireworks | llama-3.3-70b, deepseek | ✓ | ✓ | ✓ |
| AI21 | jamba-1.5 | ✓ | ✓ | ✓ |
| OpenRouter | multi-provider routing | ✓ | ✓ | ✓ |
| Cohere | command-r-plus | ✗ | ✓ | ✓ |
| LM Studio | local models | ✗ | ✓ | ✓ |
| Local | custom endpoints | ✗ | ✓ | ✓ |

---

## Deployment & CI/CD

### Blue/Green Deployments
Zero-downtime deployments with traffic weight shifting:
```bash
# Start deployment
agentctl deploy start <agent-id> --strategy blue-green

# Shift traffic gradually
agentctl deploy shift <deployment-id> --weight 0.5
agentctl deploy shift <deployment-id> --weight 1.0
```

### Canary Deployments
Progressive rollout with shadow testing:
```bash
# Start canary
agentctl canary start <agent-id> --percentage 10

# Compare results
agentctl canary compare <canary-id>

# Promote if safe
agentctl canary promote <canary-id>
```

### Automatic Rollback
When SLO breaches are detected:
- Latency > 50% increase → auto-rollback
- Error rate > 5% drop → auto-rollback
- Manual rollback available via CLI

### Promotion Gates
Before promoting from staging to production:
1. **Regression Suite**: basic_sanity + guardrails suites must pass
2. **Eval Baseline**: Latest eval score must meet threshold
3. **Security Check**: No critical incidents open
4. **Prompt Freshness**: System prompt matches baseline

---

## Guardrails & Safety

### Configuration
```bash
# Environment variables
export CONTENT_MODERATION_ENABLED=true
export CONTENT_MODERATION_TOXICITY_THRESHOLD=0.8
```

### Detection Capabilities
| Category | Method | Sensitivity |
|----------|--------|-------------|
| Prompt Injection | 15 regex patterns | Configurable |
| Toxicity | Weighted pattern scoring | Threshold-based |
| PII (email, phone, CC) | Regex with redaction | Automatic |
| Secrets (API keys, tokens) | Pattern detection | Automatic |
| Refusal Detection | Output scanning | Flag on match |

---

## Alerting & Monitoring

### Grafana Dashboards
Three pre-built dashboards:
1. **Agent Runtime Overview**: Active agents, error rate, latency, top agents
2. **Agent Step Latency**: p50/p95/p99 latency, step distribution
3. **Agent Cost & Usage**: Cost per agent, token usage, provider distribution

### Alert Integrations
- **PagerDuty**: Automatic incident creation on SLO breaches
- **OpsGenie**: Alert routing with priority-based escalation
- **Grafana Webhook**: Custom webhook receiver for any alert manager

Configuration:
```bash
export PAGERDUTY_ROUTING_KEY=your-pd-key
export OPSGENIE_API_KEY=your-og-key
```

---

## Secrets Management

Integrated with HashiCorp Vault and AWS Secrets Manager:

```bash
# Configure backend
export SECRETS_MANAGER_PROVIDER=vault   # or 'aws'
export VAULT_ADDR=http://vault:8200
export VAULT_TOKEN=your-token

# Store agent credentials
agentctl secrets set <agent-id> --key OPENAI_API_KEY --value sk-...

# Retrieve for runtime use
agentctl secrets get <agent-id> --key OPENAI_API_KEY
```

---

## Data Residency

Enforce data storage location per tenant:

```yaml
# Residency policy example
tenant_id: acme-corp
allowed_regions:
  - us-east-1
  - eu-west-1
data_classification: confidential
require_sovereign_processing: true
allow_cross_region_backup: false
```

Configuration:
```bash
export DATA_RESIDENCY_ENABLED=true
export CLUSTER_REGION=us-east-1
```

---

## Disaster Recovery

Automated backup and restore for agent configurations:

```bash
# Full backup
agentctl backup <agent-id-1> <agent-id-2> --include-memory --include-runs

# List backups
agentctl backup-list

# Restore
agentctl restore backup-abc123
```

Scheduled backups run automatically:
```bash
export DISASTER_RECOVERY_ENABLED=true
export DISASTER_RECOVERY_SCHEDULE_HOURS=24
```

---

## Marketplace Governance

Publishing agents to the marketplace requires:
1. **Security Scan**: Automated scanning for dangerous tools, prompt quality, data privacy
2. **Review**: Manual approval by marketplace admin
3. **Publishing**: Only approved agents are published

```bash
# Submit agent for marketplace review
agentctl marketplace submit <agent-id> --version 1.0.0

# Review (admin)
agentctl marketplace review <submission-id> --action approve

# Publish
agentctl marketplace publish <submission-id>
```

---

## A2A Protocol (Agent-to-Agent)

The platform implements Google's A2A specification for inter-agent communication:

```bash
# Enable A2A
export A2A_ENABLED=true

# Register an agent as A2A server
curl -X POST /api/v1/a2a/register-server \
  -d '{"agent_id": "...", "name": "my-agent", "description": "..."}'

# Discover capabilities
curl /api/v1/a2a/discover/<agent-id>

# Send task to remote agent
curl -X POST /api/v1/a2a/send \
  -d '{"target_url": "...", "message": "Analyze this data", "metadata": {}}'
```

---

## SDKs

### Python SDK
```python
from kleberai import Client

client = Client(api_key="your-key", base_url="http://localhost:18080")

# List agents
agents = client.agents.list()

# Run agent
result = client.agents.run("agent-id", {"prompt": "Hello!"})

# Agent evals
report = client.agent_evals.run("agent-id", suite_id="basic_sanity")
```

### Go SDK
```go
import "github.com/llm-inference-stack/sdk-go"

client := sdkgo.NewClient("your-api-key", "http://localhost:18080")

// List agents
agents, _ := client.Agents.List()

// Run agent
result, _ := client.Agents.Run("agent-id", map[string]any{"prompt": "Hello!"})
```

### CLI (`agentctl`)
```bash
# List templates
agentctl list-templates

# Scaffold agent
agentctl scaffold hello-world --name my-agent --output ./agents

# List agents
agentctl list

# Run agent
agentctl run <agent-id> --input "Hello"

# Run evals
agentctl eval run <agent-id> --suite basic_sanity

# Backup/restore
agentctl backup <agent-id>
agentctl restore <backup-id>

# Benchmarks
agentctl benchmark run <agent-id>
```

---

## Configuration Reference

### Core Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_RUNTIME_ENABLED` | false | Enable agent runtime |
| `AGENT_EXECUTION_ENABLED` | false | Enable agent execution |
| `AGENT_WEBSOCKET_STREAMING_ENABLED` | false | Enable WebSocket streaming |
| `A2A_ENABLED` | false | Enable A2A protocol |

### Guardrails
| Variable | Default | Description |
|----------|---------|-------------|
| `CONTENT_MODERATION_ENABLED` | true | Enable content moderation |
| `CONTENT_MODERATION_TOXICITY_THRESHOLD` | 0.7 | Toxicity threshold (0-1) |

### Secrets Management
| Variable | Default | Description |
|----------|---------|-------------|
| `SECRETS_MANAGER_PROVIDER` | vault | Backend: vault or aws |
| `VAULT_ADDR` | http://localhost:8200 | Vault server address |
| `VAULT_TOKEN` | "" | Vault authentication token |

### Alerting
| Variable | Default | Description |
|----------|---------|-------------|
| `PAGERDUTY_ROUTING_KEY` | "" | PagerDuty Events API key |
| `OPSGENIE_API_KEY` | "" | OpsGenie API key |
| `OPSGENIE_API_URL` | https://api.opsgenie.com/v2/alerts | OpsGenie endpoint |

### Disaster Recovery
| Variable | Default | Description |
|----------|---------|-------------|
| `DISASTER_RECOVERY_ENABLED` | false | Enable automated backups |
| `DISASTER_RECOVERY_BACKUP_DIR` | /tmp/agent-backups | Backup storage path |
| `DISASTER_RECOVERY_SCHEDULE_HOURS` | 24 | Backup interval in hours |

### Data Residency
| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_RESIDENCY_ENABLED` | false | Enable data residency enforcement |
| `CLUSTER_REGION` | default | Current cluster region identifier |

### Fine-tuning
| Variable | Default | Description |
|----------|---------|-------------|
| `FINE_TUNING_ENABLED` | false | Enable fine-tuning features |
| `FINE_TUNING_GPU_PROVIDER_ENABLED` | false | Enable GPU training executor |
| `MLOPS_DATASET_STORAGE_PATH` | "" | Path to training datasets |

### Autoscaling
| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOYMENT_AUTOSCALE_ENABLED` | true | Enable deployment autoscaling |
| `DEPLOYMENT_AUTOSCALE_WINDOW_SEC` | 60 | Traffic analysis window |

---

## API Reference

### Agent Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/agents` | List all agents |
| POST | `/api/v1/admin/agents` | Create agent |
| GET | `/api/v1/admin/agents/{id}` | Get agent details |
| PATCH | `/api/v1/admin/agents/{id}` | Update agent |
| DELETE | `/api/v1/admin/agents/{id}` | Delete agent |
| POST | `/api/v1/admin/agents/{id}/run` | Run agent |

### Agent Deployments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/agents/deployments` | Create deployment |
| GET | `/api/v1/admin/agents/deployments` | List deployments |
| POST | `/api/v1/admin/agents/deployments/{id}/rollback` | Rollback deployment |
| POST | `/api/v1/admin/agents/deployments/{id}/promote` | Promote deployment |

### Evaluations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/agents/evals/run` | Run eval suite |
| GET | `/api/v1/admin/agents/evals/reports` | List eval reports |
| GET | `/api/v1/admin/agents/evals/suites` | List eval suites |

### Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/agents/memory` | List agent memories |
| POST | `/api/v1/admin/agents/memory` | Write memory |
| DELETE | `/api/v1/admin/agents/memory/{id}` | Delete memory |
| GET | `/api/v1/admin/agents/memory/search` | Semantic memory search |

### Tools
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/agents/tools` | List tools |
| POST | `/api/v1/admin/agents/tools` | Register tool |
| POST | `/api/v1/admin/agents/tools/{name}/grant` | Grant tool permission |

### MCP (Model Context Protocol)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/agents/mcp/servers` | List MCP servers |
| POST | `/api/v1/admin/agents/mcp/servers` | Register MCP server |
| POST | `/api/v1/admin/agents/mcp/servers/{id}/discover` | Trigger discovery |
| GET | `/api/v1/admin/agents/mcp/tools` | List discovered tools |

### A2A Protocol
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/a2a/jsonrpc` | A2A JSON-RPC handler |
| GET | `/api/v1/a2a/discover/{agent_id}` | Discover agent capabilities |
| POST | `/api/v1/a2a/send` | Send task to remote agent |
| POST | `/api/v1/a2a/register-server` | Register A2A server |

### Alerting
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/alerts/grafana-webhook` | Grafana alert webhook |
| POST | `/api/v1/alerts/test-pagerduty` | Test PagerDuty connectivity |
| POST | `/api/v1/alerts/resolve` | Resolve alert by dedup key |

### Prompt Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/prompts/templates` | List prompt templates |
| POST | `/api/v1/admin/prompts/templates` | Create prompt template |
| POST | `/api/v1/admin/prompts/templates/{id}/versions` | Add version |
| POST | `/api/v1/admin/prompts/templates/{id}/playground` | Test prompt |

### Fine-tuning
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/mlops/fine-tuning/jobs` | Start fine-tuning job |
| GET | `/api/v1/admin/mlops/fine-tuning/jobs/{id}` | Get job status |

### Backup & Restore
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/disaster-recovery/backup` | Create backup |
| POST | `/api/v1/admin/disaster-recovery/restore` | Restore backup |
| GET | `/api/v1/admin/disaster-recovery/backups` | List backups |

### Marketplace
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/marketplace/submit` | Submit agent for publishing |
| POST | `/api/v1/admin/marketplace/review` | Review submission |
| POST | `/api/v1/admin/marketplace/publish` | Publish approved agent |

### Streaming
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/agents/runs/{run_id}/events` | SSE event stream |
| WS | `/api/v1/agents/runs/{run_id}/stream` | WebSocket stream |

---

## Benchmarking

Systematic benchmarking compares agent providers/models:

```bash
agentctl benchmark run <agent-id>

agentctl benchmark compare <agent-id> --providers openai anthropic gemini
```

Available scenarios: basic_qa, math_reasoning, code_generation, summarization, instruction_following, long_context, guardrail_jailbreak, multi_turn

---

## Rate Limiting

Three-layer rate limiting:
| Layer | Default | Description |
|-------|---------|-------------|
| Global | 1000 req/min | Platform-wide limit |
| Tenant | 500 req/min | Per-tenant limit |
| IP | 60 req/min | Per-IP limit |

---

## Authentication

- **API Keys**: Admin and client API keys with scoped permissions
- **OAuth2/SSO**: Google and GitHub login for admin UI
- **RBAC**: Role-based access control for team management

---

## Deployment Options

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes (Helm)
```bash
helm install llm-inference-stack ./deploy/helm/llm-inference-stack
```

### Environment Variables
See [Configuration Reference](#configuration-reference) for all settings.

---

## Troubleshooting

### Common Issues

**Agent run fails with provider error**
- Check provider API key in secrets manager
- Verify provider is enabled: `PROVIDER_ENABLED=true`
- Check rate limits

**Memory not persisting**
- Verify `AGENT_LONG_TERM_MEMORY_ENABLED=true`
- Check vector store configuration
- Verify consent settings

**WebSocket streaming not working**
- Set `AGENT_WEBSOCKET_STREAMING_ENABLED=true`
- Check reverse proxy WebSocket support
- Verify firewall allows WS connections

**Promotion gate blocked**
- Run regression suite: `agentctl eval run <id> --suite basic_sanity`
- Check eval baseline score
- Verify no critical incidents open

---

## Support

- GitHub Issues: https://github.com/llm-inference-stack/issues
- Documentation: https://docs.llm-inference-stack.dev
- API Reference: https://api.llm-inference-stack.dev/docs
