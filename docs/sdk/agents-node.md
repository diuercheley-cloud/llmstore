# Agentic SDK - Node.js

## Usage

```typescript
import { Client } from '@kleberai/sdk';

const client = new Client({ apiKey: 'your-key' });

// List agents
const agents = await client.agents.list();

// Create agent from manifest
const manifest = { ... };
const agent = await client.agents.create(manifest);

// Run agent
const run = await client.agents.run('agent-uuid', { task: 'help' });

// Get run status
const status = await client.agents.getRun(run.id);

// Run evaluations
const evalRun = await client.agentEvals.run('agent-uuid');
```
