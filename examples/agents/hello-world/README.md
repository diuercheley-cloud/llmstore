# Hello World Agent

A minimal starter agent. Use this as a template for building more complex agents.

## Usage

Deploy this agent and send it a message:

```bash
curl -X POST http://localhost:18080/v1/agents/hello-world/run \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, agent!"}'
```
