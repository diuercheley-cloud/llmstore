# Shared Workspace

The Shared Workspace allows agents within a multi-agent team to collaborate by sharing structured data.

## Features

- **Key-Value Store**: Agents can `put` and `get` JSON objects using specific keys.
- **Run Isolation**: Each team run has its own workspace. Data is not shared between different runs or different teams.
- **Tenant Boundary**: Strict enforcement of tenant isolation for all shared data.

## Usage

Agents can use the workspace to store intermediate results, shared state, or shared configuration that is too large for prompt injection.
Raw workspace data is also captured in the team trace for debugging.
