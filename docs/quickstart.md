# Agentic Platform Quickstart

Build your first agent in 5 minutes.

## 1. Start the Platform

```bash
docker compose up -d
```

## 2. Get Your API Key

```bash
curl -s http://localhost:18080/public/plans | jq .
```

Then sign up or use the admin dashboard to create an API key.

## 3. Create Your First Agent

### Python

```python
from kleberai import Client

client = Client(api_key="your-key", base_url="http://localhost:18080")

agent = client.agents.create({
    "name": "my-first-agent",
    "description": "A helpful assistant",
    "model": "default",
    "system_prompt": "You are a helpful assistant.",
    "tools": ["web_search"],
})
print(f"Agent created: {agent['id']}")
```

### JavaScript/TypeScript

```typescript
import { Client } from '@llm-inference-stack/sdk';

const client = new Client({ apiKey: 'your-key' });

const agent = await client.agents.create({
  name: 'my-first-agent',
  systemPrompt: 'You are a helpful assistant.',
  tools: ['web_search'],
});
console.log(`Agent created: ${agent.id}`);
```

### Go

```go
import "github.com/llm-inference-stack/sdk-go"

client := kleberai.NewClient("your-key", "http://localhost:18080", 30*time.Second)

agent, _ := client.Agents.Create(map[string]interface{}{
    "name": "my-first-agent",
    "system_prompt": "You are a helpful assistant.",
})
```

### cURL

```bash
curl -X POST http://localhost:18080/v1/agents \
  -H "Authorization: Bearer your-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-first-agent","system_prompt":"You are a helpful assistant.","tools":["web_search"]}'
```

## 4. Run Your Agent

```python
# Python
run = client.agents.run(agent["id"], {
    "input": "What is the capital of France?"
})
print(run["output"])
```

## 5. Add Memory

```python
agent = client.agents.create({
    "name": "memory-agent",
    "memory_enabled": True,
    "memory_type": "semantic",
})

# The agent now remembers past conversations
client.agents.run(agent["id"], {"input": "My name is Alice."})
run2 = client.agents.run(agent["id"], {"input": "What is my name?"})
print(run2["output"])  # "Alice"
```

## 6. Add Tools

```python
agent = client.agents.create({
    "name": "tool-agent",
    "tools": [
        {"type": "web_search"},
        {"type": "http_request"},
        {"type": "code_interpreter"},
    ],
})

run = client.agents.run(agent["id"], {
    "input": "Search the web and summarize the latest AI news."
})
```

## 7. Deploy to Production

```python
deployment = client.deployments.create({
    "agent_id": agent["id"],
    "environment": "production",
    "auto_scaling": True,
    "max_concurrency": 10,
})
print(f"Deployment active: {deployment['status']}")
```

## Next Steps

- [Agent Studio Guide](agents/agent-studio.md) - Visual flow builder
- [Tool Development](agents/tool-adapters.md) - Custom tool creation
- [Agent Memory](agents/memory.md) - Memory configuration
- [Production Deployment](agents/agentic-deployment.md) - Scaling and monitoring
- [API Reference](API_REFERENCE.md) - Full API documentation
