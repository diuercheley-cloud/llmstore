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
Manage agent bundles for marketplace publication.

#### `bundle init`
Creates a new bundle skeleton.
```bash
agentctl bundle init my-agent [directory]
```

#### `bundle validate`
Performs integrity and schema checks on a bundle.
```bash
agentctl bundle validate [directory]
```

#### `bundle test`
Runs eval suites and unit tests for the bundle.
```bash
agentctl bundle test [directory]
```

#### `bundle sign`
Digitally signs the bundle with Ed25519.
```bash
agentctl bundle sign [directory] [--key path/to/key.pem]
```

#### `bundle publish`
Publishes the bundle to the marketplace as a draft.
```bash
agentctl bundle publish [directory]
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
