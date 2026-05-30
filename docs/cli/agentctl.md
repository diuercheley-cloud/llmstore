# Agent Control CLI (`agentctl`)

`agentctl` is the command-line companion for agent developers.

## Commands

### `init`
Initializes a new agent project from a template.
```bash
agentctl init my-agent --template support-triage
```

### `validate`
Performs static analysis and schema validation on `agent.yaml`.
```bash
agentctl validate .
```

### `bundle`
Packages the agent project into a distribution bundle.
```bash
agentctl bundle . -o my-agent.zip
```

### `register`
Registers the agent definition with the platform (requires API Key).
```bash
agentctl register --key $API_KEY
```

### `run`
Starts a local execution of the agent for debugging.
```bash
agentctl run --input "Hello"
```
