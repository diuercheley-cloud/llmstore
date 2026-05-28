# Agent Tool Synthesis

The Tool Synthesis system allows agents to dynamically generate Python-based tools based on a provided schema and natural language prompt.

## Components
- **ToolSynthesizer**: Interface for generating Python code from `GeneratedToolSchema`.
- **GeneratedToolRegistry**: Manages the lifecycle of generated tools, including versioning and approval workflows.
- **GeneratedToolValidator**: Performs AST-based static analysis to ensure generated code adheres to security policies.

## Workflow
1. Agent requests a tool via `/admin/agents/tool-synthesis/generate`.
2. Code is generated and registered as an unapproved version.
3. Code is validated against blocked modules (e.g., `os`, `subprocess`).
4. (Optional) Admin approves the tool version via `/approve`.
