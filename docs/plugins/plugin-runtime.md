# Plugin Runtime

The Plugin Runtime provides a secure environment for executing third-party code.

## Security
- **Mandatory Sandbox**: All plugins must execute within a MicroVM or gVisor sandbox.
- **Explicit Permissions**: Permissions must be declared in the manifest and granted upon installation.
- **No Network by Default**: Plugins are isolated from the network unless explicitly permitted.
- **Resource Limits**: CPU, memory, and timeout limits are enforced per execution.

## Audit
Every plugin execution generates an audit receipt for traceability.
