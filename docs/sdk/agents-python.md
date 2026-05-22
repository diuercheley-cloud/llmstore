# Agentic SDK - Python

## Usage

```python
from kleberai import Client

client = Client(api_key="your-key")

# List agents
agents = client.agents.list()

# Create agent from manifest
manifest = {...}
agent = client.agents.create(manifest)

# Run agent
run = client.agents.run(agent_id="agent-uuid", input_data={"task": "help"})

# Get run status
status = client.agents.get_run(run["id"])

# Run evaluations
eval_run = client.agent_evals.run(agent_id="agent-uuid")
```
