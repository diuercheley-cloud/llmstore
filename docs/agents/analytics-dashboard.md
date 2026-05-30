# Agent Analytics Dashboard

The Agent Analytics Dashboard provides real-time visibility into the performance, cost, and reliability of your agentic ecosystem.

## Key Metrics

### 1. Run Success Rate
Percentage of agent runs that reached the `completed` status without fatal errors or safety blocks.

### 2. Financial Metrics
- **Total Cost (BRL)**: Aggregated estimated cost of LLM calls and tool execution.
- **Token Consumption**: Breakdown of prompt and completion tokens used across all agents.

### 3. Operational Health
- **Tool Failure Rate**: Percentage of tool calls that resulted in errors.
- **Eval Pass Rate**: Average pass rate for agents executed within evaluation suites.
- **SLO Breaches**: Number of times agents exceeded their configured max runtime or step limits.

### 4. Security & Compliance
- **Policy Denials**: Count of actions blocked by the Guardrail or Policy Engine.
- **Guardrail Violations**: (Coming Soon) Detailed breakdown of jailbreak or PII detection events.

## Using the Dashboard

1. **Access**: Navigate to **Agents > Analytics** in the Admin Portal.
2. **Filters**: Use the time-range dropdown (24h, 7d, 30d) to analyze trends.
3. **Drill-down**: Click on specific metrics (future feature) to see which agents are contributing most to costs or failures.

## Backend Implementation

Metrics are aggregated from the following database tables:
- `agent_run_metrics`
- `agent_run_costs`
- `agent_policy_decisions`
- `agent_eval_results`

Tenant isolation is strictly enforced at the query level to ensure data privacy.
