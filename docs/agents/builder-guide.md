# Agent Builder Guide

## Overview

The Kleber AI Platform allows developers to build, test, and deploy autonomous agents using a manifest-driven workflow.

## Getting Started

1.  **Install the SDK**: Use the Python or Node.js SDK to interact with the platform.
2.  **Initialize an Agent**: Use `agentctl init` to scaffold a new agent directory.
3.  **Define the Manifest**: Edit `agent.yaml` to specify the agent's name, version, tools, and model.
4.  **Write Instructions**: Use Markdown to define the agent's behavior in the specified `instructions_file`.
5.  **Validate**: Run `agentctl validate` to check for errors or secrets.
6.  **Register**: Run `agentctl register` to upload the agent to the platform.
7.  **Run & Eval**: Use `agentctl run` and `agentctl eval` to test your agent.

## Workflow

- **Development**: Agents start in the `dev` environment with `draft` status.
- **Testing**: Promote to `staging` and run full evaluation suites.
- **Production**: Requires a passed evaluation baseline and security approval.
