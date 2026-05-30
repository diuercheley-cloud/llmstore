# Agent Templates and Blueprints

Templates provide a fast and reliable way to create specialized agents for common business tasks without starting from scratch.

## Available Blueprints

| Template | Description | Use Cases |
|----------|-------------|-----------|
| `support-triage` | Classifies and routes support tickets. | Customer support, IT helpdesk. |
| `github-issue-triage` | Manages labels, milestones, and priority. | Open source projects, DevOps. |
| `compliance-evidence` | Collects SOC2/ISO27001 audit artifacts. | Security, Governance, Compliance. |
| `rag-research` | Performs deep research using internal docs. | Knowledge management, Analysis. |
| `incident-response` | Automates runbook steps during outages. | SRE, On-call operations. |
| `billing-review` | Analyzes invoices for anomalies/disputes. | Finance, FinOps. |
| `devops-runbook` | Executes infrastructure automation steps. | Platform engineering. |
| `salesforce-account-summary` | Summarizes CRM data for sales reps. | Sales, Account Management. |

## Template Structure

Each blueprint is a directory containing:
- `agent.yaml`: Configuration (model, tools, memory, risk).
- `instructions.md`: The core reasoning and prompt logic.
- `eval_suite.json`: Pre-defined tests to verify quality.
- `README.md`: Documentation on how to use the agent.
- `sample_input.json`: Example request.

## Using Templates in Studio

1.  **Open Template Gallery**: Browse available blueprints.
2.  **Preview**: Inspect instructions and tool requirements.
3.  **Create from Template**: Instantiates a new agent in `draft` mode.
4.  **Customize**: Tailor the instructions and tools to your specific environment.
5.  **Dry-run**: Test the agent using the provided sample input.
